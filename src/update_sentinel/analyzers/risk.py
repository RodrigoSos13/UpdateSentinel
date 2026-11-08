"""Regras objetivas, sem probabilidades ou inferências de compatibilidade."""

from dataclasses import dataclass

from update_sentinel.core.models import Diagnostic, Finding, Severity


@dataclass(frozen=True)
class RiskPolicy:
    boot_warning_percent: float = 80
    boot_high_percent: float = 95
    minimum_free_bytes: int = 512 * 1024**2

    def __post_init__(self) -> None:
        if not 0 < self.boot_warning_percent < self.boot_high_percent <= 100:
            raise ValueError("Limiares de ocupação inválidos")
        if self.minimum_free_bytes < 0:
            raise ValueError("Reserva de espaço inválida")


class RiskAnalyzer:
    def __init__(self, policy: RiskPolicy | None = None):
        self.policy = policy or RiskPolicy()

    def analyze(self, info: Diagnostic) -> list[Finding]:
        findings = []
        for disk in info.disks:
            if disk.total <= 0 or disk.free < 0 or disk.free > disk.total:
                findings.append(
                    Finding(
                        "Dados",
                        Severity.UNKNOWN,
                        disk.path,
                        "Valores de disco inconsistentes",
                        "Provedor de sistema",
                        "Alta sobre a inconsistência",
                        "Repetir diagnóstico.",
                        "Não foi possível avaliar o espaço.",
                    )
                )
                continue
            if disk.used_percent >= self.policy.boot_high_percent:
                severity = Severity.HIGH
            elif (
                disk.used_percent >= self.policy.boot_warning_percent
                or disk.free < self.policy.minimum_free_bytes
            ):
                severity = Severity.WARNING
            else:
                continue
            findings.append(
                Finding(
                    "Espaço",
                    severity,
                    disk.path,
                    f"{disk.used_percent:.1f}% ocupado; {disk.free / 1024**3:.2f} GiB disponíveis; "
                    f"montagem {disk.mount} ({disk.filesystem}).",
                    "findmnt e psutil.disk_usage",
                    "Alta sobre a medição",
                    "Revisar uso do espaço antes de atualizar; investigar retenção se usar Limine.",
                    "Limiares conservadores configuráveis; "
                    "tamanho futuro de kernel/initramfs não estimado. "
                    "O espaço medido não prova que uma atualização falhará.",
                )
            )
        if not any(d.path == "/boot" for d in info.disks):
            findings.append(
                Finding(
                    "Espaço",
                    Severity.UNKNOWN,
                    "/boot",
                    "Espaço e montagem não disponíveis",
                    "Provedor de sistema",
                    "Insuficiente",
                    "Verificar montagem e permissões.",
                    "Não foi possível avaliar a partição de boot.",
                )
            )
        findings.append(
            Finding(
                "Recuperação",
                Severity.UNKNOWN,
                "Snapshots e bootloader",
                f"{info.snapper}; {info.bootloader}",
                "Consultas locais",
                "Insuficiente",
                "Verificar procedimento de recuperação e mídia externa "
                "antes de alterações críticas.",
                "Não foi realizado teste de restauração, boot ou integridade de arquivos.",
            )
        )
        return findings
