"""Núcleo compartilhado por CLI e Qt; nenhuma dependência de interface."""

from collections.abc import Callable

from update_sentinel.analyzers.risk import RiskAnalyzer
from update_sentinel.core.models import Diagnostic, Disk, PackageUpdate, Report
from update_sentinel.providers.packages import ArchPackages, PackageProvider
from update_sentinel.providers.system import LinuxSystem
from update_sentinel.security.commands import CommandError, CommandRunner


class ScanService:
    def __init__(self, system=None, packages: PackageProvider | None = None, analyzer=None):
        runner = CommandRunner()
        self.system = system or LinuxSystem(runner)
        self.packages = packages or ArchPackages(runner)
        self.analyzer = analyzer or RiskAnalyzer()

    def scan(
        self,
        updates: bool = True,
        progress: Callable[[str], None] | None = None,
        stage_changed: Callable[[str], None] | None = None,
    ) -> Report:
        notify = progress or (lambda message: None)
        stage = stage_changed or (lambda name: None)
        stage("system")
        notify("Identificando sistema, hardware, espaço e mecanismos de recuperação…")
        report = Report(diagnostic=self.system.collect())
        if updates:
            if not report.diagnostic.supported:
                report.update_status = "Distribuição não suportada: apenas Arch Linux e CachyOS."
            else:
                try:
                    stage("updates")
                    notify("Consultando atualizações e metadados nos repositórios configurados…")
                    report.packages = self.packages.updates()
                    report.update_status = (
                        f"{len(report.packages)} atualizações disponíveis"
                        if report.packages
                        else "Nenhuma atualização disponível"
                    )
                except CommandError as exc:
                    report.update_status = f"Falha na consulta: {exc}"
        stage("analysis")
        notify("Avaliando evidências e priorizando recomendações com regras locais…")
        report.findings = self.analyzer.analyze(report.diagnostic)
        return report


def demo_report() -> Report:
    report = Report(
        demo=True,
        update_status="DEMONSTRAÇÃO — dados simulados",
        diagnostic=Diagnostic(
            distribution="CachyOS (simulado)",
            supported=True,
            kernel="kernel simulado",
            cpu="CPU simulada",
            gpus=["GPU simulada"],
            bootloader="Limine (simulado)",
            snapper="Snapshots simulados; recuperação não validada",
            disks=[Disk("/boot", "/boot", "vfat", 4 * 1024**3, 700 * 1024**2)],
            limine={"retention": "50 (simulado)", "recovery_entries": 50},
        ),
        packages=[PackageUpdate("linux", "exemplo-antigo", "exemplo-novo", category="Kernel")],
    )
    report.findings = RiskAnalyzer().analyze(report.diagnostic)
    return report
