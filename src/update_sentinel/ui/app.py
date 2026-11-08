"""Qt Widgets usa o mesmo núcleo da CLI; consultas executam em thread dedicada."""

import os
import sys
from datetime import datetime

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRect, Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent, QFont, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from update_sentinel.core.assistant import answer, assessment
from update_sentinel.core.guidance import summarize
from update_sentinel.core.models import Report, Severity
from update_sentinel.core.reports import render_report, save_report
from update_sentinel.core.service import ScanService, demo_report
from update_sentinel.ui.activity import ActivityPanel
from update_sentinel.ui.system_view import SystemView
from update_sentinel.ui.theme import palette, stylesheet


class WrappedLabel(QLabel):
    """Preserva a altura do texto quando o resultado ou a largura mudam."""

    def __init__(self, text: str):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _fit_height(self) -> None:
        margins = self.contentsMargins()
        bounds = self.fontMetrics().boundingRect(
            QRect(0, 0, max(1, self.contentsRect().width()), 100_000),
            Qt.TextFlag.TextWordWrap,
            self.text(),
        )
        self.setMinimumHeight(bounds.height() + margins.top() + margins.bottom())

    def setText(self, text: str) -> None:
        super().setText(text)
        self._fit_height()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_height()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fit_height()


class ScanWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)
    stage_changed = Signal(str)

    def run(self) -> None:
        try:
            self.completed.emit(
                ScanService().scan(
                    progress=self.progress.emit, stage_changed=self.stage_changed.emit
                )
            )
        except Exception as exc:
            self.failed.emit(f"Diagnóstico interrompido ({type(exc).__name__}).")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("UpdateSentinel · agente de diagnóstico"))
        self.resize(1240, 900)
        self.setMinimumSize(640, 560)
        self.worker = None
        self.report = None
        self.dark = self.palette().color(self.palette().ColorRole.Window).lightness() < 128
        self.reduced_motion = os.environ.get("UPDATESENTINEL_REDUCED_MOTION") == "1"
        self.animations = []
        self.nav_buttons = {}
        root = QWidget()
        self.shell = QHBoxLayout(root)
        self.shell.setContentsMargins(0, 0, 0, 0)
        self.shell.setSpacing(0)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.shell.addWidget(workspace, 1)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        header = QHBoxLayout(topbar)
        header.setContentsMargins(28, 14, 28, 14)
        self.breadcrumb = QLabel(self.tr("Visão geral"))
        self.breadcrumb.setObjectName("breadcrumb")
        header.addWidget(self.breadcrumb, 1)
        self.state_badge = QLabel(self.tr("PRONTO PARA VERIFICAR"))
        self.state_badge.setObjectName("stateBadge")
        header.addWidget(self.state_badge)
        self.theme_button = QPushButton()
        self.theme_button.setToolTip(self.tr("Alternar entre tema claro e escuro"))
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        layout.addWidget(topbar)
        self.status = WrappedLabel(self.tr("Nenhuma verificação realizada ainda."))
        self.status.setObjectName("statusLine")
        self.status.setContentsMargins(28, 10, 28, 10)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.status)
        self._build_home()
        self._build_assistant()
        updates = QWidget()
        updates_layout = QVBoxLayout(updates)
        updates_layout.setContentsMargins(28, 24, 28, 24)
        updates_layout.setSpacing(16)
        package_heading = QLabel(self.tr("Entenda suas atualizações"))
        package_heading.setObjectName("sectionTitle")
        updates_layout.addWidget(package_heading)
        package_hint = WrappedLabel(
            self.tr(
                "Selecione um pacote para entender sua função. "
                "A descrição da versão instalada não é um resumo das mudanças da nova versão."
            )
        )
        package_hint.setObjectName("muted")
        updates_layout.addWidget(package_hint)
        self.package_count = QLabel(self.tr("Nenhuma lista carregada"))
        self.package_count.setObjectName("muted")
        updates_layout.addWidget(self.package_count)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Pesquisar pacote ou descrição…"))
        self.search.textChanged.connect(self.filter_rows)
        filters.addWidget(self.search)
        self.category = QComboBox()
        self.category.addItem(self.tr("Todas as categorias"))
        self.category.currentTextChanged.connect(self.filter_rows)
        filters.addWidget(self.category)
        updates_layout.addLayout(filters)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Pacote"),
                self.tr("Instalada"),
                self.tr("Disponível"),
                self.tr("Categoria"),
                self.tr("Descrição geral"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.itemSelectionChanged.connect(self.show_package)
        updates_layout.addWidget(self.table)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(170)
        updates_layout.addWidget(self.details)
        self.updates_index = self.tabs.addTab(updates, self.tr("Atualizações"))
        self.tabs.setTabEnabled(self.updates_index, False)
        self.diagnostic = SystemView()
        self.diagnostic_index = self.tabs.addTab(self.diagnostic, self.tr("Meu computador"))
        self.full_report = QTextEdit()
        self.full_report.setReadOnly(True)
        self.report_index = self.tabs.addTab(self.full_report, self.tr("Relatório técnico"))
        settings = QLabel(
            self.tr(
                "Tema: começa com a preferência do sistema; alterne pelo botão no topo.\n\n"
                "IA e pesquisa de documentação: não implementadas nesta fase.\n"
                "A consulta checkupdates acessa os repositórios de pacotes configurados.\n"
                "Verificações são manuais; não há monitoramento em segundo plano.\n"
                "O último relatório real é armazenado localmente conforme XDG."
            )
        )
        settings.setAlignment(Qt.AlignmentFlag.AlignTop)
        settings.setMargin(20)
        self.about_index = self.tabs.addTab(settings, self.tr("Sobre a verificação"))
        self._build_navigation()
        self.toggle_details(False)
        self.tabs.currentChanged.connect(self.navigate)
        self.fade_effect = QGraphicsOpacityEffect(self.tabs)
        self.fade_effect.setOpacity(1.0)
        self.tabs.setGraphicsEffect(self.fade_effect)
        self.fade = QPropertyAnimation(self.fade_effect, b"opacity", self)
        self.fade.setDuration(170)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCentralWidget(root)
        self.apply_theme()
        self._compact_navigation(self.width() < 900)

    def _build_navigation(self) -> None:
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(214)
        nav = QVBoxLayout(self.sidebar)
        nav.setContentsMargins(16, 24, 16, 20)
        nav.setSpacing(8)
        self.brand = QLabel("UpdateSentinel")
        self.brand.setObjectName("brand")
        nav.addWidget(self.brand)
        self.brand_note = QLabel(self.tr("Cuidados antes de atualizar"))
        self.brand_note.setWordWrap(True)
        nav.addWidget(self.brand_note)
        nav.addSpacing(30)
        self.nav_caption = QLabel(self.tr("ESPAÇO DE TRABALHO"))
        self.nav_caption.setObjectName("navCaption")
        nav.addWidget(self.nav_caption)
        entries = (
            (0, "Visão geral", QStyle.StandardPixmap.SP_DirHomeIcon),
            (self.updates_index, "Atualizações", QStyle.StandardPixmap.SP_BrowserReload),
            (
                self.assistant_index,
                "Entender resultado",
                QStyle.StandardPixmap.SP_MessageBoxInformation,
            ),
            (self.diagnostic_index, "Meu computador", QStyle.StandardPixmap.SP_ComputerIcon),
            (self.report_index, "Relatório técnico", QStyle.StandardPixmap.SP_FileIcon),
            (self.about_index, "Sobre", QStyle.StandardPixmap.SP_FileDialogInfoView),
        )
        for index, title, icon in entries:
            button = QPushButton(self.tr(title))
            button.setCheckable(True)
            button.setProperty("navigationTitle", self.tr(title))
            button.setIcon(self.style().standardIcon(icon))
            button.setToolTip(self.tr(title))
            button.setAccessibleName(self.tr(title))
            button.clicked.connect(
                lambda checked=False, target=index: self.tabs.setCurrentIndex(target)
            )
            button.setChecked(index == 0)
            self.nav_buttons[index] = button
            nav.addWidget(button)
        self.nav_buttons[self.updates_index].setEnabled(False)
        nav.addStretch()
        self.sidebar_note = QLabel(
            self.tr(
                "DIAGNÓSTICO LOCAL\n\nVocê decide quando atualizar.\n"
                "Nenhuma alteração é feita aqui."
            )
        )
        self.sidebar_note.setWordWrap(True)
        nav.addWidget(self.sidebar_note)
        self.shell.insertWidget(0, self.sidebar)

    def _compact_navigation(self, compact: bool) -> None:
        self.sidebar.setFixedWidth(64 if compact else 214)
        self.brand.setText("US" if compact else "UpdateSentinel")
        for widget in (self.brand_note, self.nav_caption, self.sidebar_note):
            widget.setVisible(not compact)
        for button in self.nav_buttons.values():
            button.setText("" if compact else button.property("navigationTitle"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self._compact_navigation(self.width() < 900)

    def navigate(self, index: int) -> None:
        button = self.nav_buttons.get(index)
        if button:
            self.breadcrumb.setText(button.property("navigationTitle"))
        for target, navigation in self.nav_buttons.items():
            navigation.setChecked(index == target)
        if hasattr(self, "fade") and not self.reduced_motion:
            self.fade.stop()
            self.fade.setStartValue(0.55)
            self.fade.setEndValue(1.0)
            self.fade.start()

    def apply_theme(self) -> None:
        self.setPalette(palette(self.dark))
        self.setStyleSheet(stylesheet(self.dark))
        self.theme_button.setText(self.tr("Tema claro") if self.dark else self.tr("Tema escuro"))

    def toggle_theme(self) -> None:
        self.dark = not self.dark
        self.apply_theme()

    def set_badge(self, text: str, state: str) -> None:
        self.state_badge.setText(self.tr(text))
        self.state_badge.setProperty("state", state)
        self.state_badge.style().unpolish(self.state_badge)
        self.state_badge.style().polish(self.state_badge)

    def _update_metrics(self, report: Report) -> None:
        guidance = summarize(report)
        self.update_metric.setText("—" if guidance.incomplete else str(len(report.packages)))
        self.update_metric.property("subtitle").setText(
            self.tr("Consulta incompleta")
            if guidance.incomplete
            else self.tr("Pacotes disponíveis")
        )
        warnings = sum(f.severity in (Severity.HIGH, Severity.WARNING) for f in report.findings)
        unknown = sum(f.severity == Severity.UNKNOWN for f in report.findings)
        self.alert_metric.setText(str(warnings))
        self.alert_metric.property("subtitle").setText(
            self.tr("%1 sem conclusão").replace("%1", str(unknown))
            if unknown
            else self.tr("Ver detalhes da avaliação")
        )
        self.last_metric.setText(
            self.tr("Exemplo")
            if report.demo
            else datetime.fromisoformat(report.created_at).astimezone().strftime("%H:%M")
        )
        self.last_metric.property("subtitle").setText(
            self.tr("Dados simulados") if report.demo else report.diagnostic.distribution
        )
        self.set_badge(
            "DADOS SIMULADOS"
            if report.demo
            else (
                "COLETA INCOMPLETA"
                if guidance.incomplete
                else "REVISAR CUIDADOS"
                if warnings or unknown
                else "COLETA CONCLUÍDA"
            ),
            "attention" if guidance.incomplete or warnings else "idle",
        )

    def _show_disks(self, report: Report) -> None:
        for animation in self.animations:
            animation.stop()
            animation.deleteLater()
        self.animations.clear()
        while self.disk_layout.count():
            item = self.disk_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        heading = QLabel(self.tr("Espaço disponível"))
        heading.setObjectName("sectionTitle")
        self.disk_layout.addWidget(heading)
        self.disk_bars = []
        for disk in report.diagnostic.disks:
            if disk.total <= 0 or not 0 <= disk.free <= disk.total:
                continue
            row = QWidget()
            contents = QVBoxLayout(row)
            contents.setContentsMargins(0, 4, 0, 4)
            name = "Inicialização (/boot)" if disk.path == "/boot" else "Sistema (/)"
            label = WrappedLabel(
                f"{self.tr(name)} · {disk.free / 1024**3:.2f} GiB livres "
                f"de {disk.total / 1024**3:.2f} GiB · {disk.used_percent:.1f}% ocupado"
            )
            contents.addWidget(label)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            bar.setAccessibleName(label.text())
            value = round(disk.used_percent * 10)
            bar.setValue(value if self.reduced_motion else 0)
            if not self.reduced_motion:
                animation = QPropertyAnimation(bar, b"value", self)
                animation.setDuration(350)
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                animation.setStartValue(0)
                animation.setEndValue(value)
                animation.start()
                self.animations.append(animation)
            contents.addWidget(bar)
            self.disk_layout.addWidget(row)
            self.disk_bars.append(bar)
        self.disk_panel.setVisible(bool(self.disk_bars))

    def _build_home(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(12)
        eyebrow = QLabel(self.tr("SEU PRÓXIMO PASSO, COM MAIS CLAREZA"))
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)
        self.home_heading = WrappedLabel(self.tr("Antes de atualizar, vamos conferir."))
        self.home_heading.setObjectName("heroTitle")
        hero_layout.addWidget(self.home_heading)
        self.home_intro = WrappedLabel(
            self.tr(
                "Entenda o que vai mudar e os cuidados que seu computador precisa. "
                "Você continua no controle."
            )
        )
        self.home_intro.setObjectName("muted")
        hero_layout.addWidget(self.home_intro)
        self.found_text = WrappedLabel(
            self.tr("As atualizações disponíveis aparecerão aqui após a verificação.")
        )
        self.found_text.setObjectName("muted")
        hero_layout.addWidget(self.found_text)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.scan_button = QPushButton(self.tr("Verificar meu computador"))
        self.scan_button.setObjectName("primary")
        self.scan_button.setMinimumHeight(42)
        self.scan_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.scan_button.clicked.connect(self.start_scan)
        actions.addWidget(self.scan_button)
        self.demo_button = QPushButton(self.tr("Ver um exemplo"))
        self.demo_button.setMinimumHeight(42)
        self.demo_button.clicked.connect(lambda: self.show_report(demo_report()))
        actions.addWidget(self.demo_button)
        actions.addStretch()
        hero_layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setAccessibleName(self.tr("Verificação em andamento"))
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.hide()
        hero_layout.addWidget(self.progress)
        layout.addWidget(hero)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.update_metric = self._metric(metrics, "Atualizações", "—", "Aguardando consulta")
        self.alert_metric = self._metric(metrics, "Pontos de atenção", "—", "Ainda não avaliados")
        self.last_metric = self._metric(metrics, "Última verificação", "—", "Nenhuma até agora")
        layout.addLayout(metrics)
        self.activity_toggle = QPushButton(self.tr("Acompanhar verificação"))
        self.activity_toggle.setCheckable(True)
        self.activity_toggle.toggled.connect(self._toggle_activity)
        layout.addWidget(self.activity_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        self.activity = ActivityPanel()
        layout.addWidget(self.activity)
        self.activity.hide()
        self.attention_text = self._add_card(
            layout,
            "O que merece atenção",
            self.tr("Vou conferir o espaço e as informações de recuperação do sistema."),
            role="attention",
        )
        self.next_text = self._add_card(
            layout,
            "Seu próximo passo",
            self.tr("Comece pela verificação. Nada será instalado ou apagado."),
            role="next",
        )
        self.disk_panel = QFrame()
        self.disk_panel.setObjectName("activityCard")
        self.disk_layout = QVBoxLayout(self.disk_panel)
        self.disk_layout.setContentsMargins(20, 16, 20, 16)
        self.disk_panel.hide()
        layout.addWidget(self.disk_panel)
        links = QHBoxLayout()
        self.detail_button = QPushButton(self.tr("Entender este resultado"))
        self.detail_button.setEnabled(False)
        self.detail_button.clicked.connect(self.explain_result)
        links.addWidget(self.detail_button)
        self.package_button = QPushButton(self.tr("Ver lista de atualizações"))
        self.package_button.setEnabled(False)
        self.package_button.clicked.connect(lambda: self.tabs.setCurrentIndex(self.updates_index))
        links.addWidget(self.package_button)
        links.addStretch()
        layout.addLayout(links)
        self.technical_toggle = QPushButton(self.tr("Mostrar detalhes técnicos"))
        self.technical_toggle.setCheckable(True)
        self.technical_toggle.toggled.connect(self.toggle_details)
        layout.addWidget(self.technical_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        note = WrappedLabel(
            self.tr(
                "Somente diagnóstico. Esta verificação não garante uma atualização sem problemas."
            )
        )
        note.setObjectName("muted")
        layout.addWidget(note)
        layout.addStretch()
        scroll.setWidget(panel)
        self.tabs.addTab(scroll, self.tr("Início"))

    def _toggle_activity(self, visible: bool) -> None:
        if self.worker and self.worker.isRunning():
            self.activity.show()
        else:
            self.activity.setVisible(visible)

    def _metric(self, row: QHBoxLayout, title: str, value: str, detail: str) -> QLabel:
        card = QFrame()
        card.setObjectName("metricCard")
        contents = QVBoxLayout(card)
        contents.setContentsMargins(18, 14, 18, 14)
        caption = QLabel(self.tr(title))
        caption.setObjectName("muted")
        contents.addWidget(caption)
        number = QLabel(value)
        number.setObjectName("metricValue")
        contents.addWidget(number)
        subtitle = QLabel(self.tr(detail))
        subtitle.setTextFormat(Qt.TextFormat.PlainText)
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        contents.addWidget(subtitle)
        number.setProperty("subtitle", subtitle)
        row.addWidget(card, 1)
        return number

    def _add_card(
        self, layout: QVBoxLayout, title: str, text: str, role: str = "neutral"
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("guidanceCard")
        card.setProperty("role", role)
        contents = QVBoxLayout(card)
        contents.setContentsMargins(18, 14, 18, 14)
        heading = QLabel(self.tr(title))
        heading.setObjectName("sectionTitle")
        contents.addWidget(heading)
        body = WrappedLabel(text)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setWordWrap(True)
        body.setObjectName("muted")
        contents.addWidget(body)
        layout.addWidget(card)
        return body

    def toggle_details(self, visible: bool) -> None:
        for index in (
            self.assistant_index,
            self.diagnostic_index,
            self.report_index,
            self.about_index,
        ):
            self.tabs.setTabVisible(index, visible)
            if index in self.nav_buttons:
                self.nav_buttons[index].setVisible(visible)
        self.technical_toggle.setText(
            self.tr("Ocultar detalhes técnicos")
            if visible
            else self.tr("Mostrar detalhes técnicos")
        )
        if not visible:
            self.tabs.setCurrentIndex(0)

    def explain_result(self) -> None:
        self.technical_toggle.setChecked(True)
        self.tabs.setCurrentIndex(self.assistant_index)
        if self.report is not None:
            self.ask_assistant("Próximos passos")

    def _build_assistant(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        heading = QLabel(self.tr("Entenda o resultado, uma pergunta por vez."))
        heading.setStyleSheet("font-size: 22px; font-weight: 600; padding: 12px 0;")
        layout.addWidget(heading)
        explanation = QLabel(
            self.tr("Análise guiada por evidências locais · sem IA nesta versão · somente leitura")
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.stage = QLabel(self.tr("Pronto para iniciar uma investigação"))
        self.stage.setStyleSheet("padding: 10px; font-weight: 600;")
        layout.addWidget(self.stage)
        self.conversation = QTextEdit()
        self.conversation.setReadOnly(True)
        self.conversation.setStyleSheet("QTextEdit { font-size: 14px; padding: 16px; }")
        layout.addWidget(self.conversation, 1)
        self.append_message(
            "Sentinel",
            self.tr(
                "Posso investigar as atualizações disponíveis e explicar o que os dados permitem "
                "concluir. Comece em ‘Verificar meu computador’ ou explore a demonstração. "
                "Depois, consulte os assuntos abaixo para entender as evidências "
                "e os próximos passos."
            ),
        )
        topics = QHBoxLayout()
        for label in ("Espaço de /boot", "Explicar pacotes", "Recuperação", "Próximos passos"):
            button = QPushButton(self.tr(label))
            button.clicked.connect(lambda checked=False, topic=label: self.ask_assistant(topic))
            topics.addWidget(button)
        layout.addLayout(topics)
        entry = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText(
            self.tr("Assuntos: /boot, pacotes, recuperação ou próximos passos…")
        )
        self.question.returnPressed.connect(self.ask_assistant)
        entry.addWidget(self.question)
        send = QPushButton(self.tr("Consultar evidências"))
        send.clicked.connect(lambda: self.ask_assistant())
        entry.addWidget(send)
        layout.addLayout(entry)
        self.assistant_index = self.tabs.addTab(panel, self.tr("Perguntas guiadas"))

    def append_message(self, author: str, text: str) -> None:
        # Texto simples: metadados externos nunca são interpretados como HTML.
        cursor = self.conversation.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        author_format = QTextCharFormat()
        author_format.setFontWeight(QFont.Weight.DemiBold)
        body_format = QTextCharFormat()
        body_format.setFontWeight(QFont.Weight.Normal)
        cursor.insertText(f"{author}\n", author_format)
        cursor.insertText(f"{text}\n\n", body_format)
        self.conversation.setTextCursor(cursor)
        self.conversation.ensureCursorVisible()

    def show_progress(self, message: str) -> None:
        self.status.setText(message)
        self.stage.setText(message)
        self.found_text.setText(
            self.tr("A coleta está em andamento. Os resultados aparecerão aqui.")
        )
        self.append_message("Etapa", message)

    def ask_assistant(self, topic: str | None = None) -> None:
        question = (topic or self.question.text()).strip()
        if not question:
            return
        self.question.clear()
        self.append_message("Você", question)
        if self.worker and self.worker.isRunning():
            response = self.tr(
                "Estou coletando os dados. Aguarde a conclusão para consultar evidências."
            )
        elif self.report is None:
            response = self.tr(
                "Inicie uma investigação para que eu possa responder com dados coletados."
            )
        else:
            response = answer(self.report, question)
        self.append_message("Sentinel", response)

    def start_scan(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.status.setText(
            self.tr("Consultando sistema e repositórios… Isso pode levar alguns minutos.")
        )
        self.tabs.setCurrentIndex(0)
        self.conversation.clear()
        self.report = None
        self.append_message("Você", "Investigue minhas atualizações e o preparo do sistema.")
        self.append_message(
            "Sentinel",
            self.tr(
                "Vou identificar o sistema, consultar os pacotes disponíveis e avaliar os achados. "
                "A consulta acessa os repositórios configurados. "
                "Nenhuma atualização será instalada."
            ),
        )
        self.stage.setText(self.tr("Investigação em andamento"))
        self.activity_toggle.setChecked(True)
        self.activity_toggle.setEnabled(False)
        self.activity_toggle.setText(self.tr("Verificação em andamento"))
        self.activity.show()
        self.activity.start()
        self.set_badge("VERIFICANDO", "busy")
        for metric in (self.update_metric, self.alert_metric, self.last_metric):
            metric.setText("—")
            metric.property("subtitle").setText(self.tr("Coleta em andamento"))
        self.disk_panel.hide()
        self.search.clear()
        self.scan_button.setEnabled(False)
        self.scan_button.setText(self.tr("Verificando…"))
        self.home_heading.setText(self.tr("Estou verificando seu computador"))
        self.home_intro.setText(
            self.tr("Isso pode levar alguns minutos. Você pode acompanhar aqui.")
        )
        self.found_text.setText(self.tr("Consultando o sistema e as atualizações disponíveis…"))
        self.attention_text.setText(self.tr("Aguarde a avaliação dos dados coletados."))
        self.next_text.setText(
            self.tr("Nenhuma ação é necessária enquanto a verificação acontece.")
        )
        self.progress.setRange(0, 0)
        self.progress.show()
        self.detail_button.setEnabled(False)
        self.package_button.setEnabled(False)
        self.table.setRowCount(0)
        self.details.clear()
        self.diagnostic.clear()
        self.full_report.clear()
        self.tabs.setTabEnabled(self.updates_index, False)
        self.nav_buttons[self.updates_index].setEnabled(False)
        self.demo_button.setEnabled(False)
        self.worker = ScanWorker(self)
        self.worker.completed.connect(self.show_report)
        self.worker.failed.connect(self.show_error)
        self.worker.progress.connect(self.show_progress)
        self.worker.stage_changed.connect(self.activity.step)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()

    def scan_finished(self) -> None:
        self.scan_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.activity_toggle.setEnabled(True)

    def show_error(self, message: str) -> None:
        self.status.setText(message)
        self.activity.fail()
        self.set_badge("INTERROMPIDO", "attention")
        self.home_heading.setText(self.tr("Não consegui terminar a verificação"))
        self.home_intro.setText(self.tr("Tente novamente para obter um resultado atualizado."))
        self.found_text.setText(self.tr("Nenhum resultado completo foi obtido nesta tentativa."))
        self.attention_text.setText(message)
        self.next_text.setText(
            self.tr("Clique em ‘Tentar novamente’. Se continuar, consulte os detalhes.")
        )
        self.scan_button.setText(self.tr("Tentar novamente"))
        self.progress.hide()
        self.detail_button.setEnabled(True)
        self.stage.setText(self.tr("Investigação interrompida"))
        self.append_message("Sentinel", message)

    def show_report(self, report: Report) -> None:
        self.report = report
        self.activity_toggle.setEnabled(True)
        self.activity_toggle.setText(self.tr("Ver atividade desta verificação"))
        self.activity.finish(report)
        self.activity.setVisible(self.activity_toggle.isChecked())
        self._update_metrics(report)
        self._show_disks(report)
        incomplete = report.update_status.startswith(("Falha", "Distribuição não suportada"))
        self.stage.setText(
            self.tr("Coleta parcial · consulta de pacotes indisponível")
            if incomplete
            else self.tr("Coleta concluída · avaliação com limitações")
        )
        if report.demo:
            self.conversation.clear()
        self.append_message("Sentinel", assessment(report))
        self.status.setText(
            self.tr("DEMONSTRAÇÃO — DADOS SIMULADOS") if report.demo else report.update_status
        )
        guidance = summarize(report)
        self.home_heading.setText(guidance.title)
        self.found_text.setText(guidance.found)
        self.attention_text.setText(guidance.attention)
        self.next_text.setText(guidance.next_step)
        self.home_intro.setText(
            self.tr("EXEMPLO — dados simulados, não representam seu computador.")
            if report.demo
            else self.tr("Este é o resultado da sua última verificação.")
        )
        self.scan_button.setText(
            self.tr("Tentar novamente") if guidance.incomplete else self.tr("Verificar novamente")
        )
        self.progress.hide()
        self.detail_button.setEnabled(True)
        self.package_button.setEnabled(bool(report.packages))
        self.tabs.setTabEnabled(self.updates_index, bool(report.packages))
        self.nav_buttons[self.updates_index].setEnabled(bool(report.packages))
        self.nav_buttons[self.updates_index].setToolTip(
            self.tr("Abra a lista de pacotes desta verificação")
            if report.packages
            else self.tr("Nenhuma lista de pacotes disponível nesta verificação")
        )
        self.tabs.setCurrentIndex(0)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(report.packages))
        self.details.clear()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(self.tr("Todas as categorias"))
        self.category.addItems(sorted({p.category for p in report.packages}))
        self.category.blockSignals(False)
        for row, package in enumerate(report.packages):
            for column, value in enumerate(
                (
                    package.name,
                    package.installed,
                    package.available,
                    package.category,
                    package.description,
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.setSortingEnabled(True)
        self.filter_rows()
        self.diagnostic.show_diagnostic(report.diagnostic)
        self.full_report.setPlainText(render_report(report.to_dict()))
        if not report.demo:
            try:
                save_report(report)
            except OSError:
                self.status.setText(
                    self.status.text() + self.tr(" · Falha ao salvar relatório local")
                )

    def filter_rows(self, *_args) -> None:
        query = self.search.text().casefold()
        visible_count = 0
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, col).text() for col in range(5)]
            matched = query in " ".join(values).casefold()
            category = self.category.currentIndex() == 0 or values[3] == self.category.currentText()
            self.table.setRowHidden(row, not (matched and category))
            visible_count += bool(matched and category)
        self.package_count.setText(
            self.tr("%1 de %2 pacotes")
            .replace("%1", str(visible_count))
            .replace("%2", str(self.table.rowCount()))
        )

    def show_package(self) -> None:
        row = self.table.currentRow()
        if row < 0 or not self.report or not self.table.item(row, 0):
            return
        name = self.table.item(row, 0).text()
        package = next((p for p in self.report.packages if p.name == name), None)
        if package:
            self.details.setPlainText(
                f"{package.description}\nComponentes: {package.components}\n"
                f"Dependências instaladas: {package.dependencies}\n{package.changes}"
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self,
                self.tr("Consulta em andamento"),
                self.tr("Aguarde a consulta terminar antes de fechar a janela."),
            )
            event.ignore()
        else:
            event.accept()


def launch() -> int:
    app = QApplication(sys.argv[:1])
    app.setApplicationName("UpdateSentinel")
    window = MainWindow()
    window.show()
    return app.exec()
