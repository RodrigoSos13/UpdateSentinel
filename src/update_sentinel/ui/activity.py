"""Atividade visível vinculada ao ciclo real do worker, sem progresso presumido."""

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from update_sentinel.core.models import Report


class ActivityPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activityCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        heading = QLabel(self.tr("Atividade da verificação"))
        heading.setObjectName("sectionTitle")
        header.addWidget(heading)
        header.addStretch()
        self.elapsed_label = QLabel(self.tr("Aguardando início"))
        self.elapsed_label.setObjectName("muted")
        header.addWidget(self.elapsed_label)
        layout.addLayout(header)
        self.states = []
        for number, name in enumerate(
            ("Conhecer o computador", "Consultar atualizações", "Avaliar os cuidados"), 1
        ):
            row = QHBoxLayout()
            label = QLabel(f"0{number}   {self.tr(name)}")
            row.addWidget(label, 1)
            state = QLabel(self.tr("Aguardando"))
            state.setObjectName("stepState")
            row.addWidget(state)
            self.states.append(state)
            layout.addLayout(row)
        self.clock = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._tick)
        self.current = -1

    @staticmethod
    def _state(label: QLabel, text: str, state: str) -> None:
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)

    def start(self) -> None:
        self.current = -1
        for label in self.states:
            self._state(label, self.tr("Aguardando"), "idle")
        self.clock.start()
        self.elapsed_label.setText(self.tr("Em andamento · 0 s"))
        self.timer.start()

    def _tick(self) -> None:
        if self.clock.isValid():
            self.elapsed_label.setText(
                self.tr("Em andamento · %1 s").replace("%1", str(self.clock.elapsed() // 1000))
            )

    def step(self, name: str) -> None:
        index = {"system": 0, "updates": 1, "analysis": 2}.get(name, -1)
        if not 0 <= index < len(self.states):
            return
        if self.current >= 0 and self.current != index:
            self._state(self.states[self.current], self.tr("Concluído"), "done")
        self.current = index
        self._state(self.states[index], self.tr("Em andamento"), "active")

    def finish(self, report: Report) -> None:
        running = self.timer.isActive()
        self.timer.stop()
        if report.demo:
            self.elapsed_label.setText(self.tr("Exemplo · dados simulados"))
        elif running:
            seconds = self.clock.elapsed() / 1000
            self.elapsed_label.setText(
                self.tr("Finalizado em %1 s").replace("%1", f"{seconds:.1f}")
            )
        else:
            self.elapsed_label.setText(self.tr("Resultado carregado"))
        for label in self.states:
            self._state(label, self.tr("Concluído"), "done")
        if report.diagnostic.unavailable:
            self._state(self.states[0], self.tr("Com limitações"), "error")
        if report.update_status.startswith(("Falha", "Distribuição não suportada")):
            self._state(self.states[1], self.tr("Não concluído"), "error")
        elif report.update_status == "Não consultado":
            self._state(self.states[1], self.tr("Não consultado"), "idle")

    def fail(self) -> None:
        self.timer.stop()
        self.elapsed_label.setText(self.tr("Interrompido"))
        if self.current >= 0:
            self._state(self.states[self.current], self.tr("Interrompido"), "error")
        for index in range(self.current + 1, len(self.states)):
            self._state(self.states[index], self.tr("Não executado"), "idle")
