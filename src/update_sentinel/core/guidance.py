"""Resumo em linguagem simples; preserva as conclusões e incertezas do relatório."""

from dataclasses import dataclass

from update_sentinel.core.models import Report, Severity


@dataclass(frozen=True)
class Guidance:
    title: str
    found: str
    attention: str
    next_step: str
    incomplete: bool


def summarize(report: Report) -> Guidance:
    """Apresenta o achado prioritário sem realizar uma nova avaliação de risco."""
    incomplete = report.update_status.startswith(("Falha", "Distribuição não suportada")) or (
        report.update_status == "Não consultado"
    )
    found = (
        "Não consegui confirmar quais atualizações estão disponíveis."
        if incomplete
        else (
            (
                "1 atualização disponível para seu computador."
                if len(report.packages) == 1
                else f"{len(report.packages)} atualizações disponíveis para seu computador."
            )
            if report.packages
            else "Nenhuma atualização disponível nesta consulta."
        )
    )
    priority = {Severity.HIGH: 0, Severity.WARNING: 1, Severity.UNKNOWN: 2, Severity.INFO: 3}
    findings = sorted(report.findings, key=lambda finding: priority[finding.severity])
    primary = findings[0] if findings else None
    if primary and primary.severity in (Severity.HIGH, Severity.WARNING):
        title = "Há algo para revisar antes de atualizar"
        if primary.category == "Espaço":
            location = (
                "usado para iniciar o computador (/boot)"
                if primary.component == "/boot"
                else "do sistema"
            )
            attention = f"O espaço {location} atingiu o limite de atenção da verificação."
            next_step = (
                "Confira o espaço disponível e o que pode ser liberado antes de atualizar. "
                "Em ‘Entender este resultado’, você encontra a medição e os limites da análise."
            )
        else:
            attention = f"{primary.component}: {primary.evidence}"
            next_step = primary.recommendation
    elif primary and primary.severity == Severity.UNKNOWN:
        title = "Ainda há informações para conferir"
        if primary.category == "Recuperação":
            attention = (
                "Não foi possível confirmar se você conseguiria recuperar o computador "
                "caso uma atualização desse problema. Isso não indica uma falha confirmada."
            )
            next_step = (
                "Antes de atualizar, confira seu procedimento de recuperação e se tem um "
                "pendrive de recuperação disponível. Veja o que foi identificado em "
                "‘Entender este resultado’."
            )
        else:
            attention = f"Não foi possível concluir a verificação de {primary.component}."
            next_step = primary.recommendation
    else:
        title = "Verificação concluída"
        attention = (
            "As regras locais não identificaram alertas. Isso não garante que a atualização "
            "seja segura; problemas conhecidos das novas versões não foram pesquisados."
        )
        next_step = "Confira a lista de atualizações e as limitações antes de decidir atualizar."
    if report.diagnostic.unavailable:
        attention += " Algumas informações do computador ficaram indisponíveis."
    if incomplete:
        title = "A verificação ficou incompleta"
        attention = "A lista de atualizações não foi confirmada. " + attention
        next_step = (
            "Confira a conexão e se a consulta de pacotes está disponível neste sistema. "
            "Depois clique em ‘Tentar novamente’. Os detalhes mostram o motivo registrado. "
            + next_step
        )
    return Guidance(title, found, attention, next_step, incomplete)
