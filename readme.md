# 🖥️ Gestor de Tarefas Híbrido (Desktop + API)

[![Backend Tests](https://github.com/RafaelSilvaWork/Gestor-de-Tarefas/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/RafaelSilvaWork/Gestor-de-Tarefas/actions/workflows/backend-tests.yml)

> Uma aplicação full-stack de arquitetura desacoplada, combinando uma interface gráfica desktop nativa desenvolvida em **PyQt5** com um backend em **FastAPI** e banco de dados relacional.

---

## 🚀 Sobre o Projeto

Este projeto faz parte do meu portfólio de desenvolvimento de software e demonstra a capacidade de criar soluções **híbridas**, onde a interface gráfica (GUI) roda localmente na máquina do usuário e se comunica via requisições HTTP REST, autenticadas por JWT, com uma API centralizada.

---

## 📸 Screenshots

| Painel | Tarefas |
|---|---|
| ![Painel com gráfico e indicadores](docs/screenshot_painel.png) | ![Lista de tarefas com filtros](docs/screenshot_tarefas.png) |

---

## ✨ Funcionalidades

- **Autenticação JWT** — registro e login, com senhas armazenadas via hash `bcrypt`.
- **CRUD de tarefas** isolado por usuário (cada usuário só vê e altera suas próprias tarefas).
- **Filtros** por status e prioridade.
- **Painel analítico** com gráfico de rosca e indicadores (total, concluídas, taxa de conclusão).
- **Navegação lateral colapsável** (menu ☰), separando Painel e Tarefas.
- **Notificações na bandeja do sistema** (`QSystemTrayIcon`) ao criar ou concluir uma tarefa.
- **Exportação de relatórios** do histórico de tarefas em **CSV** e **PDF** formatado.
- **Tema visual profissional** (dark mode) via Qt Style Sheets.

---

## 🛠️ Tecnologias Utilizadas

### **Backend**
- **Python / FastAPI** — rotas assíncronas e documentação automática (Swagger em `/docs`).
- **SQLAlchemy + SQLite** — ORM e persistência local.
- **python-jose + passlib[bcrypt]** — emissão de JWT e hash de senhas.
- **Uvicorn** — servidor ASGI.
- **Pytest + httpx** — testes automatizados da API.

### **Frontend Desktop**
- **PyQt5** — interface gráfica nativa.
- **QSS (Qt Style Sheets)** — tema dark customizado.
- **QtChart** — gráfico de rosca do painel analítico.
- **QtPrintSupport** — geração de relatórios em PDF.
- **Requests** — comunicação com a API.

---

## 📂 Arquitetura do Repositório

```text
Gestor-de-Tarefas/
│
├── .github/workflows/        # CI (roda os testes do backend a cada push/PR)
│
├── docs/                     # Screenshots usadas neste README
│
├── backend/                  # API e Camada de Persistência
│   ├── app/
│   │   ├── main.py           # Endpoints e inicialização do FastAPI
│   │   ├── database.py       # Configuração do SQLAlchemy (engine, Session, Base)
│   │   ├── models.py         # Modelos ORM (Usuario, Tarefa)
│   │   ├── schemas.py        # Schemas Pydantic (request/response)
│   │   └── security.py       # Hash de senha, JWT e dependência de autenticação
│   ├── tests/                # Testes automatizados (pytest)
│   ├── .env.example          # Modelo de variáveis de ambiente
│   ├── requirements.txt
│   └── requirements-dev.txt  # Dependências de desenvolvimento (inclui pytest)
│
├── desktop/                  # Cliente Gráfico Nativo
│   ├── assets/                # Estilos QSS
│   ├── services/               # Integração HTTP com a API
│   ├── views/                   # Janelas e componentes em PyQt5
│   ├── main.py                # Ponto de entrada da GUI
│   └── requirements.txt
│
└── README.md
```

---

## ▶️ Como Executar

### 1. Backend (API)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Configure sua chave secreta (necessária para gerar os tokens JWT)
copy .env.example .env       # Windows (use "cp" no Linux/Mac)
# edite o .env e defina SECRET_KEY com um valor aleatório, por exemplo:
# python -c "import secrets; print(secrets.token_hex(32))"

uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000` (documentação interativa em `http://127.0.0.1:8000/docs`).

### 2. Desktop (GUI)

Com o backend rodando, em outro terminal:

```bash
cd desktop
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 3. Rodando os testes do backend

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
```

Os testes usam um banco SQLite em memória (isolado do `tarefas.db` real) e cobrem registro/login, CRUD de tarefas, filtros e isolamento de dados entre usuários.
