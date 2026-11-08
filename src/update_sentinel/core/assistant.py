"""Orientação determinística sobre evidências, sem execução de instruções livres."""

from update_sentinel.core.models import Report, Severity


def assessment(report: Report) -> str:
    """Prioriza achados sem transformar ausência de evidência em aprovação."""
    priority = {Severity.HIGH: 0, Severity.WARNING: 1, Severity.UNKNOWN: 2, Severity.INFO: 3}
    findings = sorted(report.findings, key=lambda finding: priority[finding.severity])
    prefix = "DEMONSTRAÇÃO — todas as informações abaixo são simuladas.\n\n" if report.demo else ""
    text = (
        f"{prefix}Concluí a coleta em {report.diagnostic.distribution}.\n"
        f"Resultado da consulta: {report.update_status}.\n\n"
    )
    if findings:
        first = findings[0]
        text += (
            f"Minha prioridade é revisar {first.component}.\n"
            f"[{first.severity}] {first.evidence}\n"
            f"Próximo passo: {first.recommendation}\n\n"
        )
    text += (
        "Posso detalhar o espaço de boot, explicar os pacotes e organizar as recomendações "
        "com base nesta coleta. Não verifiquei regressões nem compatibilidade futura "
        "kernel/NVIDIA; não posso concluir que a atualização é segura."
    )
    return text


def answer(report: Report, question: str) -> str:
    """Roteia assuntos limitados a fatos coletados; não interpreta comandos ou usa LLM."""
    query = question.casefold()
    marker = "DEMONSTRAÇÃO — DADOS SIMULADOS\n\n" if report.demo else ""
    if any(word in query for word in ("boot", "espaço", "limine")):
        parts = []
        for disk in report.diagnostic.disks:
            if disk.path == "/boot":
                parts.append(
                    f"/boot contém arquivos usados na inicialização. Nesta coleta pertence "
                    f"à montagem {disk.mount} ({disk.filesystem}): {disk.used_percent:.1f}% "
                    f"ocupado e {disk.free / 1024**3:.2f} GiB livres."
                )
        if not parts:
            parts.append("Não obtive uma medição válida de /boot nesta coleta.")
        parts.append(f"Bootloader: {report.diagnostic.bootloader}.")
        for key, value in report.diagnostic.limine.items():
            labels = {
                "retention": "Retenção configurada",
                "usage_limit": "Limite de uso",
                "recovery_entries": "Entradas de recuperação",
                "integrity": "Integridade",
            }
            if key in labels:
                parts.append(f"{labels[key]}: {value}.")
        parts.append(
            "Não medi os arquivos individuais nem estimei o espaço da próxima transação. "
            "Não vou remover arquivos ou sincronizar entradas."
        )
        return marker + "\n\n".join(parts)
    if any(word in query for word in ("pacote", "atualiza", "kernel", "nvidia")):
        if not report.packages:
            return (
                marker
                + f"Resultado registrado: {report.update_status}. Não há pacotes para detalhar."
            )
        lines = [f"Tenho {len(report.packages)} pacotes nesta coleta."]
        for package in report.packages:
            if package.name.casefold() in query:
                lines.extend(
                    [
                        f"{package.name}: {package.installed} → {package.available}",
                        package.description,
                        f"Componentes: {package.components}",
                        f"Dependências instaladas: {package.dependencies}",
                        package.changes,
                    ]
                )
        lines.append(
            "A lista completa está em Atualizações. As descrições explicam a versão instalada; "
            "não comprovam mudanças na versão disponível. Compatibilidade kernel/NVIDIA "
            "não foi validada."
        )
        return marker + "\n\n".join(lines)
    if any(word in query for word in ("recuper", "snapshot", "snapper")):
        return marker + (
            f"Situação observada: {report.diagnostic.snapper}.\n\n"
            f"Bootloader: {report.diagnostic.bootloader}.\n\n"
            "Não testei restauração ou inicialização. A existência de snapshots não garante "
            "recuperação do bootloader. Verifique um procedimento de recuperação e mídia externa."
        )
    if any(word in query for word in ("passo", "recomenda", "risco", "fazer", "evidência")):
        return (
            marker
            + "\n\n".join(
                f"[{finding.severity}] {finding.component}\n"
                f"Evidência: {finding.evidence}\nOrigem: {finding.origin}\n"
                f"Confiança: {finding.confidence}\n"
                f"Recomendação: {finding.recommendation}\nLimites: {finding.limitations}"
                for finding in report.findings
            )
            or "Não há achados registrados nesta coleta; isso não comprova segurança."
        )
    return (
        "Meu atendimento nesta versão usa assuntos predefinidos, sem modelo de linguagem. "
        "Posso explicar /boot, pacotes, recuperação e próximos passos com os dados coletados. "
        "Use um desses assuntos ou consulte o relatório. Não executo o texto digitado."
    )
