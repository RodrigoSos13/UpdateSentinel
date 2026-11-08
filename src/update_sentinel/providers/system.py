"""Diagnóstico Linux: informação indisponível permanece explicitamente desconhecida."""

import json
import os
import platform
import re
import shutil
from pathlib import Path

import psutil

from update_sentinel.core.models import Diagnostic, Disk
from update_sentinel.security.commands import CommandError, CommandRunner


def read_text(path: Path, limit: int = 2_000_000) -> str:
    with path.open(errors="replace") as stream:
        return stream.read(limit)


def parse_assignments(text: str) -> dict[str, str]:
    """Lê atribuições literais; nunca executa/source arquivos de configuração shell."""
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r'\s*([A-Z_]+)\s*=\s*(["\']?)([^\n]*?)\2\s*', line)
        if match:
            value = match[3]
            if not any(token in value for token in ("$", "`", ";")):
                values[match[1]] = value
    return values


def parse_mount(output: str) -> tuple[str, str]:
    mounts = json.loads(output)["filesystems"]
    if not mounts or not all(isinstance(mounts[0].get(k), str) for k in ("target", "fstype")):
        raise ValueError("Dados de montagem incompletos")
    return mounts[0]["target"], mounts[0]["fstype"]


def limine_diagnostic(config: str, boot_config: str) -> dict[str, str | int]:
    settings = parse_assignments(config)
    # Conta apenas IDs explícitos do gerador, sem supor que toda entrada seja recuperação.
    ids = set(re.findall(r"(?im)^\s*/+[^\n]*\bID=(\d+)\b", boot_config))
    return {
        "retention": settings.get("MAX_SNAPSHOT_ENTRIES", "Não explícita; padrão não presumido"),
        "usage_limit": settings.get("LIMIT_USAGE_PERCENT", "Não explícito"),
        "recovery_entries": len(ids) if ids else "Formato não reconhecido; não contado",
        "integrity": "Não verificada; existência de configuração não comprova boot funcional",
    }


class LinuxSystem:
    def __init__(self, runner: CommandRunner):
        self.runner = runner

    def collect(self) -> Diagnostic:
        info = Diagnostic(kernel=platform.release(), cpu=platform.machine())
        try:
            release = platform.freedesktop_os_release()
            info.distribution = release.get("PRETTY_NAME", release.get("ID", "Desconhecida"))
            info.supported = release.get("ID") in {"arch", "cachyos"}
        except OSError:
            info.unavailable.append("Identificação da distribuição indisponível")
        info.desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Não identificado")
        try:
            cpu = read_text(Path("/proc/cpuinfo"))
            model = re.search(r"^model name\s*:\s*(.+)$", cpu, re.M)
            info.cpu = (
                f"{model[1] if model else platform.machine()} · {psutil.cpu_count()} CPUs lógicas"
            )
        except OSError:
            info.unavailable.append("Modelo da CPU indisponível")
        for path in ("/", "/boot"):
            try:
                result = self.runner.run("findmnt", "-J", "-T", path, "-o", "TARGET,FSTYPE")
                if result.code:
                    raise ValueError("findmnt falhou")
                mount, filesystem = parse_mount(result.stdout)
                usage = psutil.disk_usage(path)
                info.disks.append(Disk(path, mount, filesystem, usage.total, usage.free))
            except (OSError, ValueError, KeyError, TypeError, CommandError):
                info.unavailable.append(f"Montagem e espaço de {path}: indisponíveis")
        try:
            gpu = self.runner.run("lspci", "-nnk")
            if gpu.code:
                raise CommandError("lspci falhou")
            info.gpus = [
                line.strip()
                for line in gpu.stdout.splitlines()
                if any(
                    name in line
                    for name in ("VGA compatible controller", "3D controller", "Display controller")
                )
            ]
            if not info.gpus:
                info.unavailable.append("Nenhuma GPU identificada pelo lspci")
        except CommandError as exc:
            info.unavailable.append(str(exc))
        try:
            installed = self.runner.run("pacman", "-Q")
            if installed.code:
                raise CommandError("Consulta de pacotes instalados falhou")
            # Kernels reconhecidos por pkgbase em diretórios de módulos, não só pelo nome.
            for base in Path("/usr/lib/modules").glob("*/pkgbase"):
                try:
                    info.kernels.append(f"{read_text(base).strip()} · módulos {base.parent.name}")
                except OSError:
                    continue
            info.nvidia_packages = [
                line
                for line in installed.stdout.splitlines()
                if line.split() and "nvidia" in line.split()[0]
            ]
            if any(line.startswith("limine ") for line in installed.stdout.splitlines()):
                info.bootloader = "Limine instalado; uso no boot atual não confirmado"
        except CommandError as exc:
            info.unavailable.append(str(exc))
        try:
            modules = read_text(Path("/proc/modules"))
            info.nvidia_loaded = (
                "Carregado" if re.search(r"^nvidia ", modules, re.M) else "Não carregado"
            )
        except OSError:
            info.unavailable.append("Módulos carregados indisponíveis")
        self._limine(info)
        self._snapper(info)
        return info

    def _limine(self, info: Diagnostic) -> None:
        try:
            sync = read_text(Path("/etc/limine-snapper-sync.conf"))
        except OSError:
            sync = ""
        if sync:
            info.limine = limine_diagnostic(sync, "")
        paths = []
        for file in ("/etc/default/limine", "/etc/limine-snapper-sync.conf"):
            try:
                candidate = parse_assignments(read_text(Path(file))).get("ESP_PATH", "")
                if candidate.startswith("/") and "$" not in candidate:
                    paths.append(Path(candidate))
            except OSError:
                continue
        paths.extend(Path(p) for p in ("/boot", "/efi", "/boot/efi", "/limine"))
        for folder in dict.fromkeys(paths):
            for relative in ("limine.conf", "limine/limine.conf"):
                try:
                    boot = read_text(folder / relative)
                except OSError:
                    continue
                info.bootloader = "Configuração Limine encontrada; boot atual não confirmado"
                info.limine = limine_diagnostic(sync, boot)
                # Não persiste cmdline, UUIDs ou conteúdo de configurações.
                info.limine["boot_path"] = str(folder)
                return
        info.unavailable.append(
            "Configuração Limine ausente ou sem acesso; integridade não verificada"
        )

    def _snapper(self, info: Diagnostic) -> None:
        if shutil.which("snapper") is None:
            info.snapper = "Ferramenta não instalada"
            return
        try:
            configs = self.runner.run("snapper", "list-configs")
            if configs.code:
                raise CommandError("Snapper instalado; consulta sem permissão ou indisponível")
            names = re.findall(r"^([A-Za-z0-9_-]+)\s*\|", configs.stdout, re.M)
            names = [name for name in names if name != "Config"]
            summaries = []
            for name in names:
                snapshots = self.runner.run("snapper", "-c", name, "list")
                count = sum(
                    bool(re.match(r"^\s*\d+[-+*]?\s*\|", line))
                    and not bool(re.match(r"^\s*0\s*\|", line))
                    for line in snapshots.stdout.splitlines()
                )
                summaries.append(
                    f"{name}: {count} snapshots"
                    if not snapshots.code
                    else f"{name}: contagem indisponível"
                )
            info.snapper = "; ".join(summaries) or "Instalado; nenhuma configuração legível"
        except CommandError as exc:
            info.snapper = str(exc)
