"""Testes isolados: nenhum comando real ou privilégio é necessário."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from update_sentinel.analyzers.risk import RiskAnalyzer, RiskPolicy
from update_sentinel.cli import main
from update_sentinel.core.models import Diagnostic, Disk, Severity
from update_sentinel.core.reports import load_report, save_report
from update_sentinel.core.service import ScanService, demo_report
from update_sentinel.providers.packages import ArchPackages, parse_metadata, parse_updates
from update_sentinel.providers.system import limine_diagnostic, parse_assignments, parse_mount
from update_sentinel.security.commands import CommandError, CommandResult, CommandRunner


class FakeRunner:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args[0] == "pacman":
            return CommandResult(0, "Description     : Kernel Linux\nDepends On      : core\n", "")
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_parse_fixture():
    packages = parse_updates((Path(__file__).parent / "fixtures/checkupdates.txt").read_text())
    assert len(packages) == 3
    assert packages[2].installed == "1:24.2-1"


@pytest.mark.parametrize("text", ["invalid", "linux 1 -> 2\nlinux 1 -> 2", "-bad 1 -> 2"])
def test_reject_partial_or_unsafe(text):
    with pytest.raises(CommandError):
        parse_updates(text)


def test_no_updates():
    runner = FakeRunner(CommandResult(2, "", ""))
    assert ArchPackages(runner).updates() == []
    assert runner.calls[0][1]["env"]["CHECKUPDATES_DB"].endswith("/db")
    assert not Path(runner.calls[0][1]["env"]["CHECKUPDATES_DB"]).parent.exists()


@pytest.mark.parametrize(
    "result",
    [
        CommandResult(1, "linux 1 -> 2", "network"),
        CommandResult(2, "linux 1 -> 2", ""),
        CommandResult(0, "", ""),
        CommandError("missing"),
    ],
)
def test_command_errors(result):
    with pytest.raises(CommandError):
        ArchPackages(FakeRunner(result)).updates()


def test_package_metadata():
    packages = ArchPackages(FakeRunner(CommandResult(0, "linux 1 -> 2", ""))).updates()
    assert packages[0].description == "Kernel Linux"
    assert "não confirmadas" in packages[0].changes
    assert parse_metadata("Depends On      : foo\n                  bar")["Depends On"] == "foo bar"


@pytest.mark.parametrize(
    "args",
    [
        ("pacman", "-Sy"),
        ("pacman", "-Syu"),
        ("sudo", "true"),
        ("snapper", "delete", "1"),
        ("checkupdates", "--download"),
        ("pacman", "-Qi", "--root"),
        ("sh", "-c", "id"),
        ("limine-snapper-sync",),
        ("pacman", "-Qi", "a;rm"),
    ],
)
def test_command_policy(args):
    assert not CommandRunner.allowed(args)
    with pytest.raises(CommandError):
        CommandRunner().run(*args)


def test_missing_dependency():
    with patch("os.geteuid", return_value=1000), patch("shutil.which", return_value=None):
        with pytest.raises(CommandError, match="indisponível"):
            CommandRunner().run("pacman", "-Q")


def test_root_refused():
    with patch("os.geteuid", return_value=0):
        with pytest.raises(CommandError, match="root"):
            CommandRunner().run("pacman", "-Q")


def test_timeout():
    import subprocess

    with patch("os.geteuid", return_value=1000), patch("shutil.which", return_value="/bin/pacman"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pacman", 1)):
            with pytest.raises(CommandError, match="Tempo"):
                CommandRunner().run("pacman", "-Q")


def test_mount_shared_boot():
    assert parse_mount('{"filesystems":[{"target":"/","fstype":"btrfs"}]}') == ("/", "btrfs")
    with pytest.raises(ValueError):
        parse_mount('{"filesystems":[]}')


@pytest.mark.parametrize(
    ("free", "level"), [(2, None), (0.7, Severity.WARNING), (0.1, Severity.HIGH)]
)
def test_space_rules(free, level):
    info = Diagnostic(disks=[Disk("/boot", "/boot", "vfat", 4 * 1024**3, int(free * 1024**3))])
    findings = [f for f in RiskAnalyzer().analyze(info) if f.category == "Espaço"]
    assert (findings[0].severity if findings else None) == level


def test_invalid_provider_data():
    info = Diagnostic(disks=[Disk("/boot", "/boot", "vfat", 10, 20)])
    assert RiskAnalyzer().analyze(info)[0].severity == Severity.UNKNOWN
    with pytest.raises(ValueError):
        RiskPolicy(95, 80)


def test_limine_literal_config():
    result = limine_diagnostic(
        "MAX_SNAPSHOT_ENTRIES=20\nLIMIT_USAGE_PERCENT=85", "/Snapshots\n//ID=1\n//ID=2\n//ID=2"
    )
    assert result["retention"] == "20"
    assert result["recovery_entries"] == 2
    assert "não contado" in limine_diagnostic("", "/Snapshots\n//unexpected")["recovery_entries"]
    assert "ESP_PATH" not in parse_assignments('ESP_PATH="$(touch /tmp/bad)"')


def test_offline_service():
    class System:
        def collect(self):
            return Diagnostic(distribution="Arch", supported=True)

    report = ScanService(System(), ArchPackages(FakeRunner(CommandError("offline")))).scan()
    assert report.update_status.startswith("Falha")
    assert report.findings


def test_unsupported_distribution():
    class System:
        def collect(self):
            return Diagnostic(distribution="Other")

    runner = FakeRunner(CommandResult(0, "linux 1 -> 2", ""))
    report = ScanService(System(), ArchPackages(runner)).scan()
    assert "não suportada" in report.update_status
    assert runner.calls == []


def test_report_roundtrip(tmp_path):
    target = tmp_path / "state" / "report.json"
    report = demo_report()
    save_report(report, target)
    assert load_report(target) == json.loads(json.dumps(report.to_dict()))
    assert target.stat().st_mode & 0o777 == 0o600


def test_demo_cli_does_not_save(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert main(["demo", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["demo"]
    assert not list(tmp_path.iterdir())


def test_core_without_qt():
    import subprocess
    import sys

    code = (
        "from update_sentinel.core.service import demo_report; import sys; "
        "assert not any(m.startswith('PySide6') for m in sys.modules); assert demo_report().demo"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_optional_tools_unavailable():
    from update_sentinel.providers.system import LinuxSystem

    runner = FakeRunner(CommandError("Ferramenta indisponível"))
    with patch("shutil.which", return_value=None):
        diagnostic = LinuxSystem(runner).collect()
    assert diagnostic.kernel
    assert diagnostic.disks == []
    assert diagnostic.snapper == "Ferramenta não instalada"
    assert diagnostic.unavailable


def test_limine_retention_survives_boot_permission_error():
    from update_sentinel.providers.system import LinuxSystem

    def read(path, *args):
        if str(path) == "/etc/limine-snapper-sync.conf":
            return "MAX_SNAPSHOT_ENTRIES=20\nLIMIT_USAGE_PERCENT=85"
        raise PermissionError()

    info = Diagnostic()
    with patch("update_sentinel.providers.system.read_text", side_effect=read):
        LinuxSystem(FakeRunner(None))._limine(info)
    assert info.limine["retention"] == "20"
    assert "não contado" in info.limine["recovery_entries"]
    assert info.unavailable


def test_snapper_count_excludes_current_state():
    from update_sentinel.providers.system import LinuxSystem

    class SnapperRunner:
        def run(self, *args, **kwargs):
            if args == ("snapper", "list-configs"):
                return CommandResult(0, "Config | Subvolume\nroot | /\n", "")
            return CommandResult(0, "0 | single |\n1 | single |\n2+ | pre |\n", "")

    info = Diagnostic()
    with patch("shutil.which", return_value="/usr/bin/snapper"):
        LinuxSystem(SnapperRunner())._snapper(info)
    assert info.snapper == "root: 2 snapshots"


def test_scan_emits_stages_only_for_operations_it_performs():
    class System:
        def collect(self):
            return Diagnostic(distribution="Arch", supported=True)

    stages = []
    report = ScanService(System(), ArchPackages(FakeRunner(CommandResult(2, "", "")))).scan(
        stage_changed=stages.append
    )
    assert stages == ["system", "updates", "analysis"]
    assert report.update_status == "Nenhuma atualização disponível"
    stages.clear()
    ScanService(System()).scan(updates=False, stage_changed=stages.append)
    assert stages == ["system", "analysis"]
