"""Contratos independentes da interface e de ferramentas externas."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Severity(StrEnum):
    INFO = "Informativo"
    WARNING = "Atenção"
    HIGH = "Alto risco identificado"
    UNKNOWN = "Desconhecido / dados insuficientes"


@dataclass
class PackageUpdate:
    name: str
    installed: str
    available: str
    description: str = "Metadados indisponíveis."
    category: str = "Aplicações"
    dependencies: str = "Não verificadas"
    components: str = "Impacto não verificado"
    changes: str = "Changelog não consultado; mudanças entre versões não confirmadas."


@dataclass
class Disk:
    path: str
    mount: str
    filesystem: str
    total: int
    free: int

    @property
    def used_percent(self) -> float:
        return 100 * (1 - self.free / self.total) if self.total else 0


@dataclass
class Finding:
    category: str
    severity: Severity
    component: str
    evidence: str
    origin: str
    confidence: str
    recommendation: str
    limitations: str


@dataclass
class Diagnostic:
    distribution: str = "Desconhecida"
    supported: bool = False
    kernel: str = "Desconhecido"
    cpu: str = "Desconhecida"
    desktop: str = "Não identificado"
    gpus: list[str] = field(default_factory=list)
    kernels: list[str] = field(default_factory=list)
    nvidia_packages: list[str] = field(default_factory=list)
    nvidia_loaded: str = "Não verificado"
    disks: list[Disk] = field(default_factory=list)
    bootloader: str = "Não confirmado"
    snapper: str = "Não verificado"
    limine: dict[str, str | int] = field(default_factory=dict)
    unavailable: list[str] = field(default_factory=list)


@dataclass
class Report:
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    demo: bool = False
    update_status: str = "Não consultado"
    packages: list[PackageUpdate] = field(default_factory=list)
    diagnostic: Diagnostic = field(default_factory=Diagnostic)
    findings: list[Finding] = field(default_factory=list)
    limitations: list[str] = field(
        default_factory=lambda: [
            "Nenhuma análise garante que uma atualização seja segura.",
            "Regressões, changelogs e consistência kernel/NVIDIA não são verificados neste MVP.",
            "Snapshots e ferramentas instaladas não garantem recuperação do bootloader.",
        ]
    )

    def to_dict(self) -> dict:
        return asdict(self)
