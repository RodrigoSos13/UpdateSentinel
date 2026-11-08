"""Informações do computador em seções legíveis, sem JSON na navegação comum."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from update_sentinel.core.models import Diagnostic


class SystemView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.panel = QWidget()
        self.content = QVBoxLayout(self.panel)
        self.content.setContentsMargins(28, 24, 28, 24)
        self.content.setSpacing(16)
        self.setWidget(self.panel)
        self.clear()

    def clear(self) -> None:
        while self.content.count():
            item = self.content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content.addWidget(
            QLabel(self.tr("Verifique o computador para consultar as informações."))
        )
        self.content.addStretch()

    def show_diagnostic(self, info: Diagnostic) -> None:
        self.clear()
        while self.content.count():
            item = self.content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._section(
            "Sistema",
            [
                ("Distribuição", info.distribution),
                ("Kernel em uso", info.kernel),
                ("Ambiente gráfico", info.desktop),
            ],
        )
        self._section(
            "Hardware e drivers",
            [
                ("Processador", info.cpu),
                ("Placas de vídeo", "\n".join(info.gpus) or "Não identificadas"),
                ("Kernels encontrados", "\n".join(info.kernels) or "Não identificados"),
                ("Módulo NVIDIA", info.nvidia_loaded),
                ("Pacotes NVIDIA", "\n".join(info.nvidia_packages) or "Não identificados"),
            ],
        )
        self._section(
            "Inicialização e recuperação",
            [
                ("Bootloader", info.bootloader),
                ("Snapshots", info.snapper),
                (
                    "Limite de entradas Limine",
                    str(info.limine.get("retention", "Não identificado")),
                ),
                (
                    "Entradas de recuperação",
                    str(info.limine.get("recovery_entries", "Não verificadas")),
                ),
            ],
        )
        if info.unavailable:
            self._section(
                "Limitações da coleta",
                [("Não foi possível verificar", "\n".join(info.unavailable))],
            )
        self.content.addStretch()

    def _section(self, title: str, rows: list[tuple[str, str]]) -> None:
        card = QFrame()
        card.setObjectName("guidanceCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        heading = QLabel(self.tr(title))
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(16)
        for label, value in rows:
            caption = QLabel(self.tr(label))
            caption.setObjectName("muted")
            text = QLabel(value)
            text.setTextFormat(Qt.TextFormat.PlainText)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(caption, text)
        layout.addLayout(form)
        self.content.addWidget(card)
