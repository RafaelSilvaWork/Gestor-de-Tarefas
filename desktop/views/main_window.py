import ctypes
import csv
from datetime import datetime
from html import escape

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QStatusBar, QFrame,
    QScrollArea, QStackedWidget, QButtonGroup, QSystemTrayIcon, QMenu,
    QFileDialog
)
from PyQt5.QtCore import Qt, QSizeF
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter, QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrinter

from services.api_client import (
    buscar_tarefas, criar_tarefa, atualizar_status_tarefa,
    atualizar_tarefa, excluir_tarefa,
)
from views.dashboard_widget import DashboardWidget
from views.task_card import TaskCard
from views.task_modal import TaskModal
from views.filter_pill import FilterPill
from views.empty_state import EmptyState

SIDEBAR_COLLAPSED_WIDTH = 56
SIDEBAR_EXPANDED_WIDTH = 200

STATUS_PILLS = [("Todos", "Todos"), ("Pendentes", "Pendente"), ("Concluídas", "Concluído")]
PRIORIDADE_PILLS = [("Todas", "Todas"), ("Baixa", "Baixa"), ("Média", "Média"), ("Alta", "Alta"), ("Urgente", "Urgente")]


class MainWindow(QMainWindow):
    def __init__(self, token):
        super().__init__()
        self.token = token  # Armazena o token JWT recebido no login
        self.sidebar_expanded = False
        self.tarefas_atuais = []  # Última lista carregada (respeitando filtros), usada na exportação e nos cards
        self.filtro_status_atual = "Todos"
        self.filtro_prioridade_atual = "Todas"

        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = int(self.winId())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1))
            )
        except Exception:
            pass

        self.setWindowTitle("Gestor de Tarefas")
        self.resize(1040, 820)
        self.setMinimumSize(760, 560)

        self.app_icon = self._criar_icone_app()
        self.setWindowIcon(self.app_icon)
        self.tray_icon = None
        self._configurar_tray_icon()

        central_widget = QWidget()
        central_widget.setObjectName("ContentArea")
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
        content_widget.setObjectName("ContentArea")
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(32, 28, 32, 28)
        content_layout.setSpacing(20)

        self.page_titles = {0: ("Painel", "Visão geral das suas tarefas"), 1: ("Minhas Tarefas", "Cadastre e gerencie suas entregas")}

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

        self.btn_adicionar = QPushButton("+  Adicionar Tarefa")
        self.btn_adicionar.setObjectName("AddButton")
        self.btn_adicionar.setCursor(Qt.PointingHandCursor)
        self.btn_adicionar.clicked.connect(self.abrir_modal_nova_tarefa)
        header_layout.addWidget(self.btn_adicionar)

        content_layout.addLayout(header_layout)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, stretch=1)

        self.stack.addWidget(self._criar_pagina_painel())
        self.stack.addWidget(self._criar_pagina_tarefas())

        # --- Barra de Status Inferior ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.mudar_pagina(0)
        self.carregar_tarefas()

    # ------------------------------------------------------------------
    # Bandeja do sistema
    # ------------------------------------------------------------------
    def _criar_icone_app(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#6366f1"))
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

        # --- Filtros pill ---
        filtros_status_layout = QHBoxLayout()
        filtros_status_layout.setSpacing(8)
        self.grupo_status = QButtonGroup(self)
        self.grupo_status.setExclusive(True)
        for i, (rotulo, valor) in enumerate(STATUS_PILLS):
            pill = FilterPill(rotulo, valor=valor, ativo=(valor == self.filtro_status_atual))
            pill.clicked.connect(lambda _checked, v=valor: self._filtrar_status(v))
            self.grupo_status.addButton(pill, i)
            filtros_status_layout.addWidget(pill)
        filtros_status_layout.addStretch()
        layout.addLayout(filtros_status_layout)

        filtros_prio_layout = QHBoxLayout()
        filtros_prio_layout.setSpacing(8)
        self.grupo_prioridade = QButtonGroup(self)
        self.grupo_prioridade.setExclusive(True)
        for i, (rotulo, valor) in enumerate(PRIORIDADE_PILLS):
            pill = FilterPill(rotulo, valor=valor, ativo=(valor == self.filtro_prioridade_atual))
            pill.clicked.connect(lambda _checked, v=valor: self._filtrar_prioridade(v))
            self.grupo_prioridade.addButton(pill, i)
            filtros_prio_layout.addWidget(pill)
        filtros_prio_layout.addStretch()
        layout.addLayout(filtros_prio_layout)

        # --- Lista de tarefas (cards) ---
        self.lista_container = QVBoxLayout()
        self.lista_container.setSpacing(14)
        layout.addLayout(self.lista_container)
        layout.addStretch()

        # --- Ações inferiores (exportação) ---
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

        self.btn_atualizar = QPushButton("ATUALIZAR")
        self.btn_atualizar.setCursor(Qt.PointingHandCursor)
        self.btn_atualizar.clicked.connect(self.carregar_tarefas)
        actions_layout.addWidget(self.btn_atualizar)

        layout.addLayout(actions_layout)
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
        self.btn_adicionar.setVisible(index == 1)
        if index == 0:
            self.carregar_tarefas()

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------
    def _filtrar_status(self, valor):
        self.filtro_status_atual = valor
        self.carregar_tarefas()

    def _filtrar_prioridade(self, valor):
        self.filtro_prioridade_atual = valor
        self.carregar_tarefas()

    # ------------------------------------------------------------------
    # Dados / lista de cards
    # ------------------------------------------------------------------
    def _limpar_lista(self):
        while self.lista_container.count():
            item = self.lista_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def carregar_tarefas(self):
        # Busca todas as tarefas do usuário para o painel e aplica os filtros para a lista
        tarefas_gerais = buscar_tarefas(self.token)
        if tarefas_gerais is None:
            self.status_bar.showMessage("Erro: Falha na comunicação com a API.", 5000)
            return

        self.dashboard.atualizar_dados(tarefas_gerais)

        tarefas_filtradas = buscar_tarefas(
            self.token,
            status=self.filtro_status_atual,
            prioridade=self.filtro_prioridade_atual,
        )
        self.tarefas_atuais = tarefas_filtradas

        self._limpar_lista()

        if not tarefas_filtradas:
            self.lista_container.addWidget(EmptyState(
                "Nenhuma tarefa por aqui",
                "Ajuste os filtros ou adicione uma nova tarefa para começar a organizar seu trabalho.",
            ))
        else:
            for tarefa in tarefas_filtradas:
                card = TaskCard(tarefa)
                card.concluir_clicado.connect(self._alternar_conclusao)
                card.editar_clicado.connect(self._abrir_modal_editar)
                card.excluir_clicado.connect(self._excluir_tarefa)
                self.lista_container.addWidget(card)

        self.status_bar.showMessage(f"Exibindo {len(tarefas_filtradas)} tarefa(s).", 4000)

    def _tarefa_por_id(self, tarefa_id):
        return next((t for t in self.tarefas_atuais if t.get("id") == tarefa_id), None)

    # ------------------------------------------------------------------
    # CRUD de tarefas
    # ------------------------------------------------------------------
    def abrir_modal_nova_tarefa(self):
        modal = TaskModal(self)
        if modal.exec_() != TaskModal.Accepted:
            return

        dados = modal.dados()
        sucesso = criar_tarefa(
            self.token, dados["titulo"], dados["descricao"], dados["prioridade"],
            data_vencimento=dados["data_vencimento"], tags=dados["tags"],
        )
        if sucesso:
            self.carregar_tarefas()
            self.status_bar.showMessage("Tarefa adicionada com sucesso!", 4000)
            self.notificar("Tarefa criada", f'"{dados["titulo"]}" foi adicionada com sucesso.')
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível conectar à API para salvar a tarefa.")

    def _abrir_modal_editar(self, tarefa_id):
        tarefa = self._tarefa_por_id(tarefa_id)
        if tarefa is None:
            return

        modal = TaskModal(self, tarefa=tarefa)
        if modal.exec_() != TaskModal.Accepted:
            return

        dados = modal.dados()
        resultado = atualizar_tarefa(
            self.token, tarefa_id, dados["titulo"], dados["descricao"], dados["prioridade"],
            data_vencimento=dados["data_vencimento"], tags=dados["tags"],
        )
        if resultado:
            self.carregar_tarefas()
            self.status_bar.showMessage("Tarefa atualizada com sucesso!", 4000)
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível salvar as alterações na API.")

    def _alternar_conclusao(self, tarefa_id):
        tarefa = self._tarefa_por_id(tarefa_id)
        if tarefa is None:
            return

        novo_status = "Pendente" if tarefa.get("status") == "Concluído" else "Concluído"
        sucesso = atualizar_status_tarefa(self.token, tarefa_id, novo_status)

        if sucesso:
            self.carregar_tarefas()
            self.status_bar.showMessage(f"Tarefa atualizada para '{novo_status}'.", 4000)
            if novo_status == "Concluído":
                self.notificar("Tarefa concluída", f'"{tarefa.get("titulo")}" foi marcada como concluída.')
        else:
            QMessageBox.critical(self, "Erro", "Falha ao atualizar o status na API.")

    def _excluir_tarefa(self, tarefa_id):
        tarefa = self._tarefa_por_id(tarefa_id)
        titulo = tarefa.get("titulo") if tarefa else ""

        resposta = QMessageBox.question(
            self, "Excluir tarefa",
            f'Tem certeza que deseja excluir "{titulo}"? Essa ação não pode ser desfeita.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return

        sucesso = excluir_tarefa(self.token, tarefa_id)
        if sucesso:
            self.carregar_tarefas()
            self.status_bar.showMessage("Tarefa excluída.", 4000)
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível excluir a tarefa na API.")

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
            <h1 style="color:#6366f1; margin-bottom:2px;">Gestor de Tarefas</h1>
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
                <tr style="background:#6366f1; color:#ffffff;">
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
