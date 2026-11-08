"""Smoke test Qt headless: telas, filtro e núcleo real em worker com provedor simulado."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("UPDATESENTINEL_REDUCED_MOTION", "1")

import pytest  # noqa: E402

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402
from shiboken6 import delete  # noqa: E402

from update_sentinel.core.service import demo_report  # noqa: E402
from update_sentinel.ui.app import MainWindow  # noqa: E402


@pytest.fixture(scope="session")
def app():
    application = QApplication.instance() or QApplication([])
    yield application
    delete(application)


def test_window_demo_and_filter(app):
    window = MainWindow()
    window.show()
    window.show_report(demo_report())
    app.processEvents()
    assert "SIMULADOS" in window.status.text()
    assert window.table.rowCount() == 1
    window.search.setText("no-match")
    assert window.table.isRowHidden(0)
    window.search.setText("linux")
    assert not window.table.isRowHidden(0)
    window.table.selectRow(0)
    app.processEvents()
    assert "Changelog" in window.details.toPlainText()
    window.close()
    delete(window)


def test_scan_runs_in_worker_and_reenables_controls(app, monkeypatch, tmp_path):
    import time
    from threading import Event

    from update_sentinel.ui import app as ui

    entered = Event()
    release = Event()

    class FakeService:
        def scan(self, progress=None, stage_changed=None):
            if stage_changed:
                stage_changed("system")
            if progress:
                progress("Coleta de teste em andamento")
            entered.set()
            if not release.wait(3):
                raise RuntimeError("Worker não recebeu sinal")
            return demo_report()

    monkeypatch.setattr(ui, "ScanService", FakeService)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    window = MainWindow()
    try:
        window.start_scan()
        assert entered.wait(1)
        assert not window.scan_button.isEnabled()
        # O worker está bloqueado, mas a UI continua processando eventos.
        window.search.setText("linux")
        app.processEvents()
        release.set()
        deadline = time.monotonic() + 3
        while not window.scan_button.isEnabled() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.001)
        assert window.scan_button.isEnabled()
        assert window.report.demo
        assert not list(tmp_path.iterdir())
    finally:
        release.set()
        window.worker.wait(4000)
        window.close()
        delete(window)


def test_agent_uses_collected_evidence(app):
    window = MainWindow()
    try:
        assert window.tabs.tabText(0) == "Início"
        window.ask_assistant("Espaço de /boot")
        assert "Inicie uma investigação" in window.conversation.toPlainText()
        window.show_report(demo_report())
        window.ask_assistant("Espaço de /boot")
        assert "vfat" in window.conversation.toPlainText()
        assert "DADOS SIMULADOS" in window.conversation.toPlainText()
        window.question.setText("Execute comandos arbitrários")
        window.ask_assistant()
        assert "Não executo" in window.conversation.toPlainText()
    finally:
        window.close()
        delete(window)


def test_home_guides_user_and_reveals_details_on_demand(app):
    window = MainWindow()
    try:
        assert window.scan_button.text() == "Verificar meu computador"
        assert not window.tabs.isTabVisible(window.assistant_index)
        assert not window.detail_button.isEnabled()
        window.show_report(demo_report())
        assert window.tabs.currentIndex() == 0
        assert "SIMULADOS" in window.status.text()
        assert "não representam seu computador" in window.home_intro.text()
        assert "iniciar o computador" in window.attention_text.text()
        assert window.package_button.isEnabled()
        window.detail_button.click()
        assert window.tabs.currentIndex() == window.assistant_index
        assert "Origem:" in window.conversation.toPlainText()
        window.technical_toggle.setChecked(False)
        assert window.tabs.currentIndex() == 0
        assert not window.tabs.isTabVisible(window.diagnostic_index)
    finally:
        window.close()
        delete(window)


def test_failed_query_shows_retry_instead_of_zero_updates(app, monkeypatch):
    from update_sentinel.ui import app as ui

    monkeypatch.setattr(ui, "save_report", lambda report: None)
    window = MainWindow()
    try:
        report = demo_report()
        report.demo = False
        report.packages = []
        report.update_status = "Falha na consulta: sem conexão"
        window.show_report(report)
        assert "incompleta" in window.home_heading.text()
        assert "Não consegui confirmar" in window.found_text.text()
        assert window.scan_button.text() == "Tentar novamente"
        assert not window.package_button.isEnabled()
        assert not window.tabs.isTabEnabled(window.updates_index)
        window.show_error("Falha no provedor")
        assert "Não consegui terminar" in window.home_heading.text()
        assert not window.progress.isVisible()
    finally:
        window.close()
        delete(window)


def test_recommendation_remains_readable_in_small_window(app):
    window = MainWindow()
    try:
        window.show_report(demo_report())
        window.resize(640, 560)
        window.show()
        for _ in range(3):
            app.processEvents()
        for label in (window.found_text, window.attention_text, window.next_text):
            assert label.height() >= label.heightForWidth(label.width())
    finally:
        window.close()
        delete(window)


def test_activity_tracks_real_worker_stages_and_stops_on_failure(app):
    from update_sentinel.ui.activity import ActivityPanel

    panel = ActivityPanel()
    try:
        panel.start()
        assert panel.timer.isActive()
        assert all(label.text() == "Aguardando" for label in panel.states)
        panel.step("system")
        assert panel.states[0].text() == "Em andamento"
        assert panel.states[1].text() == "Aguardando"
        panel.step("updates")
        assert panel.states[0].text() == "Concluído"
        panel.fail()
        assert not panel.timer.isActive()
        assert panel.states[1].text() == "Interrompido"
        assert panel.states[2].text() == "Não executado"
    finally:
        delete(panel)


def test_incomplete_collection_does_not_mark_all_steps_successful(app):
    from update_sentinel.ui.activity import ActivityPanel

    panel = ActivityPanel()
    try:
        report = demo_report()
        report.demo = False
        report.update_status = "Falha na consulta: sem conexão"
        report.diagnostic.unavailable.append("GPU não verificada")
        panel.start()
        panel.step("system")
        panel.finish(report)
        assert not panel.timer.isActive()
        assert panel.states[0].text() == "Com limitações"
        assert panel.states[1].text() == "Não concluído"
        assert panel.states[2].text() == "Concluído"
    finally:
        delete(panel)


def test_example_has_no_invented_duration_and_unknowns_stay_distinct(app):
    window = MainWindow()
    try:
        window.show_report(demo_report())
        assert "simulados" in window.activity.elapsed_label.text()
        assert window.update_metric.text() == "1"
        assert window.alert_metric.text() == "1"
        assert "sem conclusão" in window.alert_metric.property("subtitle").text()
        assert window.disk_bars[0].value() == round(
            demo_report().diagnostic.disks[0].used_percent * 10
        )
    finally:
        window.close()
        delete(window)


def test_theme_switch_and_compact_navigation_preserve_access(app):
    from PySide6.QtGui import QPalette

    window = MainWindow()
    try:
        before = window.palette().color(QPalette.ColorRole.Window)
        window.theme_button.click()
        assert before != window.palette().color(QPalette.ColorRole.Window)
        window.show_report(demo_report())
        window.resize(640, 560)
        window.show()
        app.processEvents()
        assert window.sidebar.width() == 64
        button = window.nav_buttons[window.updates_index]
        assert button.accessibleName() == "Atualizações"
        button.click()
        assert window.tabs.currentIndex() == window.updates_index
        assert button.isChecked()
        assert window.breadcrumb.text() == "Atualizações"
    finally:
        window.close()
        delete(window)
