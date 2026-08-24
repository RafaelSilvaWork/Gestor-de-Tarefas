from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt5.QtChart import QChart, QChartView, QPieSeries
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtGui import QPainter, QColor, QFont

from services.theme import COMPLETA as COLOR_SUCCESS, LARANJA as COLOR_WARNING, TEXT_PRIMARY as COLOR_TEXT, TEXT_MUTED as COLOR_MUTED, CARD_BG_A as COLOR_SURFACE

CARD_HEIGHT = 74


class DashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl_titulo = QLabel("VISÃO GERAL")
        lbl_titulo.setObjectName("SectionTitle")
        layout.addWidget(lbl_titulo)

        self.chart_container = QVBoxLayout()
        self.chart_container.setSpacing(0)
        layout.addLayout(self.chart_container)

        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(12)
        layout.addLayout(self.kpi_row)

        self.atualizar_dados([])

    def _criar_metric_card(self, valor, rotulo, cor_valor=COLOR_TEXT):
        card = QFrame()
        card.setObjectName("MetricCard")
        card.setFixedHeight(CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(2)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setStyleSheet(
            f"color: {cor_valor}; font-family: 'Poppins', 'Segoe UI', sans-serif;"
            f"font-size: 24px; font-weight: 700; background: transparent;"
        )

        lbl_rotulo = QLabel(rotulo)
        lbl_rotulo.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; background: transparent;")

        card_layout.addWidget(lbl_valor)
        card_layout.addWidget(lbl_rotulo)
        return card

    def atualizar_dados(self, tarefas):
        # setParent(None) remove o widget da tela imediatamente; deleteLater()
        # sozinho só libera a memória no próximo ciclo do loop de eventos, o que
        # pode deixar o widget antigo visível por um instante em atualizações rápidas.
        while self.chart_container.count():
            widget = self.chart_container.takeAt(0).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        while self.kpi_row.count():
            widget = self.kpi_row.takeAt(0).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        total = len(tarefas)
        concluidas = sum(1 for t in tarefas if t.get("status") == "Concluído")
        pendentes = total - concluidas
        taxa = (concluidas / total * 100) if total > 0 else 0

        series = QPieSeries()
        series.setHoleSize(0.62)

        slice_conc = series.append("Concluídas", concluidas)
        slice_conc.setColor(QColor(COLOR_SUCCESS))
        slice_conc.setBorderColor(QColor(COLOR_SURFACE))
        slice_conc.setBorderWidth(2)

        slice_pend = series.append("Pendentes", pendentes)
        slice_pend.setColor(QColor(COLOR_WARNING))
        slice_pend.setBorderColor(QColor(COLOR_SURFACE))
        slice_pend.setBorderWidth(2)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.legend().setLabelColor(QColor(COLOR_MUTED))
        chart.legend().setFont(QFont("Inter", 9))
        chart.setBackgroundBrush(QColor(COLOR_SURFACE))
        chart.setBackgroundRoundness(0)
        chart.setMargins(QMargins(0, 0, 0, 0))
        chart.setTitle("")

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setFixedHeight(190)
        chart_view.setStyleSheet("background: transparent; border: none;")

        self.chart_container.addWidget(chart_view)

        self.kpi_row.addWidget(self._criar_metric_card(total, "TOTAL DE TAREFAS"))
        self.kpi_row.addWidget(self._criar_metric_card(concluidas, "CONCLUÍDAS", COLOR_SUCCESS))
        self.kpi_row.addWidget(self._criar_metric_card(f"{taxa:.0f}%", "TAXA DE CONCLUSÃO"))
