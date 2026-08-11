import ctypes
import csv
from datetime import datetime
from html import escape

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QHeaderView, QStatusBar, QFrame,
    QScrollArea, QStackedWidget, QButtonGroup, QSystemTrayIcon, QMenu,
    QFileDialog
)
from PyQt5.QtCore import Qt, QSizeF
from PyQt5.QtGui import QColor, QBrush, QIcon, QPixmap, QPainter, QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrinter

from services.api_client import buscar_tarefas, criar_tarefa, atualizar_status_tarefa
from views.dashboard_widget import DashboardWidget

SIDEBAR_COLLAPSED_WIDTH = 56
SIDEBAR_EXPANDED_WIDTH = 200


class MainWindow(QMainWindow):
    def __init__(self, token):
        super().__init__()
        self.token = token  # Armazena o token JWT recebido no login
        self.sidebar_expanded = False
        self.tarefas_atuais = []  # Última lista carregada na tabela (respeitando filtros), usada na exportação

        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = int(self.winId())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1))
            )
        except Exception:
            pass

        self.setWindowTitle("Gestor de Tarefas")
        self.resize(980, 780)
        self.setMinimumSize(760, 560)

        self.app_icon = self._criar_icone_app()
        self.setWindowIcon(self.app_icon)
        self.tray_icon = None
        self._configurar_tray_icon()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._criar_sidebar())

        # --- Área de conteúdo (rolável, por segurança em janelas pequenas) ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll_area, stretch=1)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        self.page_titles = {0: ("Painel", "Visão geral das suas tarefas"), 1: ("Tarefas", "Cadastre e gerencie suas entregas")}

        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        self.page_title_label = QLabel()
        self.page_title_label.setObjectName("AppTitle")
        self.page_subtitle_label = QLabel()
        self.page_subtitle_label.setObjectName("AppSubtitle")
        header_text.addWidget(self.page_title_label)
        header_text.addWidget(self.page_subtitle_label)
        header_layout.addLayout(header_text)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, stretch=1)

        self.stack.addWidget(self._criar_pagina_painel())
        self.stack.addWidget(self._criar_pagina_tarefas())

        # --- Barra de Status Inferior ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.mudar_pagina(0)
        self.carregar_tabela()

    # ------------------------------------------------------------------
    # Bandeja do sistema
    # ------------------------------------------------------------------
    def _criar_icone_app(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#5468ff"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 30, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "T")
        painter.end()

        return QIcon(pixmap)

    def _configurar_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Gestor de Tarefas")

        tray_menu = QMenu()
        action_abrir = tray_menu.addAction("Abrir Gestor de Tarefas")
        action_abrir.triggered.connect(self._restaurar_janela)
        tray_menu.addSeparator()
        action_sair = tray_menu.addAction("Sair")
        action_sair.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restaurar_janela()

    def _restaurar_janela(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def notificar(self, titulo, mensagem, icone=QSystemTrayIcon.Information):
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(titulo, mensagem, icone, 4000)

    def closeEvent(self, event):
        if self.tray_icon:
            self.tray_icon.hide()
        event.accept()

    # ------------------------------------------------------------------
    # Construção da UI
    # ------------------------------------------------------------------
    def _criar_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.btn_toggle = QPushButton("☰")
        self.btn_toggle.setObjectName("BtnToggleMenu")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.alternar_sidebar)
        sidebar_layout.addWidget(self.btn_toggle)
        sidebar_layout.addSpacing(14)

        self.btn_nav_painel = QPushButton("📊")
        self.btn_nav_painel.setObjectName("NavButton")
        self.btn_nav_painel.setCheckable(True)
        self.btn_nav_painel.setCursor(Qt.PointingHandCursor)
        self.btn_nav_painel.clicked.connect(lambda: self.mudar_pagina(0))

        self.btn_nav_tarefas = QPushButton("✅")
        self.btn_nav_tarefas.setObjectName("NavButton")
        self.btn_nav_tarefas.setCheckable(True)
        self.btn_nav_tarefas.setCursor(Qt.PointingHandCursor)
        self.btn_nav_tarefas.clicked.connect(lambda: self.mudar_pagina(1))

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.addButton(self.btn_nav_painel, 0)
        self.nav_group.addButton(self.btn_nav_tarefas, 1)

        sidebar_layout.addWidget(self.btn_nav_painel)
        sidebar_layout.addWidget(self.btn_nav_tarefas)
        sidebar_layout.addStretch()

        return self.sidebar

    def _criar_pagina_painel(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        dashboard_card = QFrame()
        dashboard_card.setObjectName("Card")
        dashboard_card_layout = QVBoxLayout(dashboard_card)
        dashboard_card_layout.setContentsMargins(18, 16, 18, 16)
        self.dashboard = DashboardWidget()
        dashboard_card_layout.addWidget(self.dashboard)

        layout.addWidget(dashboard_card)
        layout.addStretch()
        return page

    def _criar_pagina_tarefas(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # --- Seção de Cadastro ---
        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(18, 16, 18, 16)
        form_layout.setSpacing(6)

        form_title = QLabel("NOVA TAREFA")
        form_title.setObjectName("SectionTitle")
        form_layout.addWidget(form_title)
        form_layout.addSpacing(4)

        lbl_titulo = QLabel("TÍTULO")
        lbl_titulo.setObjectName("FieldLabel")
        form_layout.addWidget(lbl_titulo)
        self.input_titulo = QLineEdit()
        self.input_titulo.setPlaceholderText("Ex: Otimizar rotina de automação...")
        self.input_titulo.returnPressed.connect(self.adicionar_tarefa)
        form_layout.addWidget(self.input_titulo)

        lbl_desc = QLabel("DESCRIÇÃO")
        lbl_desc.setObjectName("FieldLabel")
        form_layout.addWidget(lbl_desc)
        self.input_descricao = QTextEdit()
        self.input_descricao.setPlaceholderText("Detalhes opcionais sobre a tarefa...")
        self.input_descricao.setMaximumHeight(60)
        form_layout.addWidget(self.input_descricao)

        lbl_prio = QLabel("PRIORIDADE")
        lbl_prio.setObjectName("FieldLabel")
        form_layout.addWidget(lbl_prio)
        self.combo_prioridade = QComboBox()
        self.combo_prioridade.addItems(["Baixa", "Média", "Alta"])
        form_layout.addWidget(self.combo_prioridade)

        form_layout.addSpacing(4)
        self.btn_salvar = QPushButton("ADICIONAR TAREFA")
        self.btn_salvar.setObjectName("BtnSalvar")
        self.btn_salvar.setCursor(Qt.PointingHandCursor)
        self.btn_salvar.clicked.connect(self.adicionar_tarefa)
        form_layout.addWidget(self.btn_salvar)

        layout.addWidget(form_card)

        # --- Seção de Listagem ---
        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(18, 16, 18, 12)
        list_layout.setSpacing(10)

        list_header = QHBoxLayout()
        list_title = QLabel("TAREFAS")
        list_title.setObjectName("SectionTitle")
        list_header.addWidget(list_title)
        list_header.addStretch()

        list_header.addWidget(QLabel("Status:"))
        self.filtro_status = QComboBox()
        self.filtro_status.addItems(["Todos", "Pendente", "Concluído"])
        self.filtro_status.currentIndexChanged.connect(self.carregar_tabela)
        self.filtro_status.setFixedWidth(140)
        list_header.addWidget(self.filtro_status)

        list_header.addWidget(QLabel("Prioridade:"))
        self.filtro_prio = QComboBox()
        self.filtro_prio.addItems(["Todas", "Baixa", "Média", "Alta"])
        self.filtro_prio.currentIndexChanged.connect(self.carregar_tabela)
        self.filtro_prio.setFixedWidth(120)
        list_header.addWidget(self.filtro_prio)

        list_layout.addLayout(list_header)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(["ID", "Título", "Descrição", "Prioridade", "Status"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.verticalHeader().setDefaultSectionSize(38)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setCornerButtonEnabled(False)
        self.tabela.setShowGrid(False)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setMinimumHeight(260)
        list_layout.addWidget(self.tabela)

        # --- Botões de Ação ---
        actions_layout = QHBoxLayout()

        self.btn_exportar_csv = QPushButton("EXPORTAR CSV")
        self.btn_exportar_csv.setObjectName("BtnSecondary")
        self.btn_exportar_csv.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_csv.clicked.connect(self.exportar_csv)

        self.btn_exportar_pdf = QPushButton("EXPORTAR PDF")
        self.btn_exportar_pdf.setObjectName("BtnSecondary")
        self.btn_exportar_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_pdf.clicked.connect(self.exportar_pdf)

        actions_layout.addWidget(self.btn_exportar_csv)
        actions_layout.addWidget(self.btn_exportar_pdf)
        actions_layout.addStretch()

        self.btn_atualizar = QPushButton("ATUALIZAR LISTA")
        self.btn_atualizar.setCursor(Qt.PointingHandCursor)
        self.btn_atualizar.clicked.connect(self.carregar_tabela)

        self.btn_concluir = QPushButton("MARCAR COMO CONCLUÍDO")
        self.btn_concluir.setObjectName("BtnConcluir")
        self.btn_concluir.setCursor(Qt.PointingHandCursor)
        self.btn_concluir.clicked.connect(lambda: self.mudar_status("Concluído"))

        actions_layout.addWidget(self.btn_atualizar)
        actions_layout.addWidget(self.btn_concluir)
        list_layout.addLayout(actions_layout)

        layout.addWidget(list_card, stretch=1)
        return page

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def alternar_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded

        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(SIDEBAR_EXPANDED_WIDTH)
            self.btn_nav_painel.setText("📊  Painel")
            self.btn_nav_tarefas.setText("✅  Tarefas")
        else:
            self.sidebar.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)
            self.btn_nav_painel.setText("📊")
            self.btn_nav_tarefas.setText("✅")

        alignment = "left" if self.sidebar_expanded else "center"
        for btn in (self.btn_nav_painel, self.btn_nav_tarefas):
            btn.setProperty("expanded", self.sidebar_expanded)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def mudar_pagina(self, index):
        self.stack.setCurrentIndex(index)
        self.nav_group.button(index).setChecked(True)
        titulo, subtitulo = self.page_titles[index]
        self.page_title_label.setText(titulo)
        self.page_subtitle_label.setText(subtitulo)
        if index == 0:
            self.carregar_tabela()

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------
    def carregar_tabela(self):
        status_sel = self.filtro_status.currentText()
        prio_sel = self.filtro_prio.currentText()

        # Busca todas as tarefas do usuário para o gráfico geral e aplica os filtros visuais na tabela
        tarefas_gerais = buscar_tarefas(self.token)
        if tarefas_gerais is None:
            self.status_bar.showMessage("Erro: Falha na comunicação com a API do FastAPI.", 5000)
            return

        # Atualiza o dashboard com base em todas as tarefas do usuário
        self.dashboard.atualizar_dados(tarefas_gerais)

        # Filtra localmente ou busca filtrado para a tabela
        tarefas_filtradas = buscar_tarefas(self.token, status=status_sel, prioridade=prio_sel)
        self.tarefas_atuais = tarefas_filtradas

        self.tabela.setRowCount(len(tarefas_filtradas))

        for row, tarefa in enumerate(tarefas_filtradas):
            item_id = QTableWidgetItem(str(tarefa.get("id")))
            item_titulo = QTableWidgetItem(tarefa.get("titulo"))
            item_desc = QTableWidgetItem(tarefa.get("descricao") or "")
            item_prio = QTableWidgetItem(tarefa.get("prioridade"))

            status_texto = tarefa.get("status")

            if status_texto == "Concluído":
                item_status = QTableWidgetItem(f"●  {status_texto}")
                item_status.setForeground(QBrush(QColor("#3ddc84")))
            else:
                item_status = QTableWidgetItem(f"●  {status_texto}")
                item_status.setForeground(QBrush(QColor("#f2a93c")))

            item_status.setTextAlignment(Qt.AlignCenter)
            item_id.setTextAlignment(Qt.AlignCenter)
            item_prio.setTextAlignment(Qt.AlignCenter)

            self.tabela.setItem(row, 0, item_id)
            self.tabela.setItem(row, 1, item_titulo)
            self.tabela.setItem(row, 2, item_desc)
            self.tabela.setItem(row, 3, item_prio)
            self.tabela.setItem(row, 4, item_status)

        self.status_bar.showMessage(f"Exibindo {len(tarefas_filtradas)} tarefa(s).", 4000)

    def adicionar_tarefa(self):
        titulo = self.input_titulo.text().strip()
        descricao = self.input_descricao.toPlainText().strip()
        prioridade = self.combo_prioridade.currentText()

        if not titulo:
            QMessageBox.warning(self, "Aviso", "O título da tarefa não pode estar vazio!")
            return

        sucesso = criar_tarefa(self.token, titulo, descricao, prioridade)
        if sucesso:
            self.input_titulo.clear()
            self.input_descricao.clear()
            self.carregar_tabela()
            self.status_bar.showMessage("Tarefa adicionada com sucesso!", 4000)
            self.notificar("Tarefa criada", f'"{titulo}" foi adicionada com sucesso.')
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível conectar à API para salvar a tarefa.")

    def mudar_status(self, novo_status):
        selected_row = self.tabela.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione uma tarefa na tabela primeiro!")
            return

        tarefa_id = int(self.tabela.item(selected_row, 0).text())
        titulo_tarefa = self.tabela.item(selected_row, 1).text()
        sucesso = atualizar_status_tarefa(self.token, tarefa_id, novo_status)

        if sucesso:
            self.carregar_tabela()
            self.status_bar.showMessage(f"Tarefa #{tarefa_id} atualizada para '{novo_status}'.", 4000)
            if novo_status == "Concluído":
                self.notificar("Tarefa concluída", f'"{titulo_tarefa}" foi marcada como concluída.')
        else:
            QMessageBox.critical(self, "Erro", "Falha ao atualizar o status na API.")

    # ------------------------------------------------------------------
    # Exportação de relatórios
    # ------------------------------------------------------------------
    def exportar_csv(self):
        if not self.tarefas_atuais:
            QMessageBox.information(self, "Exportar CSV", "Não há tarefas para exportar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar para CSV", "tarefas.csv", "Arquivos CSV (*.csv)"
        )
        if not caminho:
            return

        try:
            # utf-8-sig + ';' para o Excel em locale pt-BR abrir acentos e colunas corretamente
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.writer(arquivo, delimiter=";")
                writer.writerow(["ID", "Título", "Descrição", "Prioridade", "Status"])
                for tarefa in self.tarefas_atuais:
                    writer.writerow([
                        tarefa.get("id"),
                        tarefa.get("titulo"),
                        tarefa.get("descricao") or "",
                        tarefa.get("prioridade"),
                        tarefa.get("status"),
                    ])
        except OSError as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar o arquivo:\n{e}")
            return

        self.status_bar.showMessage(f"CSV exportado para {caminho}", 5000)
        self.notificar("Exportação concluída", "O relatório CSV foi salvo com sucesso.")

    def exportar_pdf(self):
        if not self.tarefas_atuais:
            QMessageBox.information(self, "Exportar PDF", "Não há tarefas para exportar.")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar para PDF", "relatorio_tarefas.pdf", "Arquivos PDF (*.pdf)"
        )
        if not caminho:
            return
        if not caminho.lower().endswith(".pdf"):
            caminho += ".pdf"

        try:
            self._gerar_relatorio_pdf(caminho)
        except OSError as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar o arquivo:\n{e}")
            return

        self.status_bar.showMessage(f"PDF exportado para {caminho}", 5000)
        self.notificar("Exportação concluída", "O relatório PDF foi salvo com sucesso.")

    def _gerar_relatorio_pdf(self, caminho):
        total = len(self.tarefas_atuais)
        concluidas = sum(1 for t in self.tarefas_atuais if t.get("status") == "Concluído")
        pendentes = total - concluidas
        taxa = (concluidas / total * 100) if total else 0
        gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

        linhas_html = []
        for t in self.tarefas_atuais:
            concluida = t.get("status") == "Concluído"
            cor_status = "#1a8f4c" if concluida else "#b8720c"
            linhas_html.append(f"""
                <tr>
                    <td>{t.get('id')}</td>
                    <td>{escape(t.get('titulo') or '')}</td>
                    <td>{escape(t.get('descricao') or '')}</td>
                    <td align="center">{escape(t.get('prioridade') or '')}</td>
                    <td align="center" style="color:{cor_status}; font-weight:bold;">{escape(t.get('status') or '')}</td>
                </tr>
            """)

        html = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family:'Segoe UI', sans-serif; color:#1a1d25;">
            <h1 style="color:#5468ff; margin-bottom:2px;">Gestor de Tarefas</h1>
            <p style="color:#666666; margin-top:0;">Relatório de Tarefas &mdash; gerado em {gerado_em}</p>
            <hr style="border:none; border-top:1px solid #dddddd;">

            <table width="100%" cellspacing="0" cellpadding="8" style="margin-top:14px; margin-bottom:22px;">
                <tr>
                    <td width="25%" align="center" style="border:1px solid #dddddd; background:#f5f6fa;">
                        <div style="font-size:18pt; font-weight:bold;">{total}</div>
                        <div style="font-size:8pt; color:#666666;">TOTAL DE TAREFAS</div>
                    </td>
                    <td width="25%" align="center" style="border:1px solid #dddddd; background:#f5f6fa;">
                        <div style="font-size:18pt; font-weight:bold; color:#1a8f4c;">{concluidas}</div>
                        <div style="font-size:8pt; color:#666666;">CONCLUÍDAS</div>
                    </td>
                    <td width="25%" align="center" style="border:1px solid #dddddd; background:#f5f6fa;">
                        <div style="font-size:18pt; font-weight:bold; color:#b8720c;">{pendentes}</div>
                        <div style="font-size:8pt; color:#666666;">PENDENTES</div>
                    </td>
                    <td width="25%" align="center" style="border:1px solid #dddddd; background:#f5f6fa;">
                        <div style="font-size:18pt; font-weight:bold;">{taxa:.0f}%</div>
                        <div style="font-size:8pt; color:#666666;">TAXA DE CONCLUSÃO</div>
                    </td>
                </tr>
            </table>

            <table width="100%" cellspacing="0" cellpadding="6" border="1" style="border-collapse:collapse; border-color:#dddddd;">
                <tr style="background:#5468ff; color:#ffffff;">
                    <th align="left">ID</th>
                    <th align="left">Título</th>
                    <th align="left">Descrição</th>
                    <th>Prioridade</th>
                    <th>Status</th>
                </tr>
                {''.join(linhas_html)}
            </table>
        </body>
        </html>
        """

        documento = QTextDocument()
        documento.setHtml(html)

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(caminho)
        printer.setPageSize(QPrinter.A4)
        printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)

        documento.setPageSize(QSizeF(printer.pageRect().size()))
        documento.print_(printer)
