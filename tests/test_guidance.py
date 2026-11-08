"""Resumo inicial preserva erros, incertezas e prioridade dos achados."""

from update_sentinel.core.guidance import summarize
from update_sentinel.core.models import Report
from update_sentinel.core.service import demo_report


def test_warning_gets_plain_language_and_next_step():
    guidance = summarize(demo_report())
    assert "revisar" in guidance.title
    assert "iniciar o computador" in guidance.attention
    assert "espaço disponível" in guidance.next_step


def test_failed_query_is_never_presented_as_no_updates():
    report = demo_report()
    report.packages = []
    report.update_status = "Falha na consulta: ferramenta indisponível"
    guidance = summarize(report)
    assert guidance.incomplete
    assert "incompleta" in guidance.title
    assert "Não consegui confirmar" in guidance.found
    assert "Nenhuma atualização disponível" not in guidance.found
    assert "Tentar novamente" in guidance.next_step
    # A falha na rede não descarta o alerta de espaço coletado localmente.
    assert "limite de atenção" in guidance.attention


def test_no_updates_is_only_shown_after_successful_query():
    report = Report(update_status="Nenhuma atualização disponível")
    guidance = summarize(report)
    assert not guidance.incomplete
    assert "Nenhuma atualização disponível" in guidance.found
    assert "não garante" in guidance.attention


def test_missing_recovery_is_not_a_confirmed_failure():
    report = demo_report()
    report.findings = [finding for finding in report.findings if finding.category == "Recuperação"]
    guidance = summarize(report)
    assert "não indica uma falha confirmada" in guidance.attention
    assert "recuperação" in guidance.next_step


def test_unavailable_data_remains_visible():
    report = demo_report()
    report.diagnostic.unavailable.append("Sem acesso ao boot")
    assert "indisponíveis" in summarize(report).attention
