import requests

BASE_URL = "http://127.0.0.1:8000"

def get_headers(token):
    return {"Authorization": f"Bearer {token}"}

def registrar_usuario(username, password):
    response = requests.post(f"{BASE_URL}/register?username={username}&password={password}")
    return response.status_code == 201

def buscar_tarefas(token, status=None, prioridade=None):
    params = {}
    if status and status != "Todos": params["status"] = status
    if prioridade and prioridade != "Todas": params["prioridade"] = prioridade
    
    response = requests.get(f"{BASE_URL}/tarefas", params=params, headers=get_headers(token))
    return response.json() if response.status_code == 200 else []

def criar_tarefa(token, titulo, descricao, prioridade, data_vencimento=None, tags=None, atribuido_a_id=None):
    payload = {
        "titulo": titulo,
        "descricao": descricao,
        "prioridade": prioridade,
        "data_vencimento": data_vencimento.isoformat() if data_vencimento else None,
        "tags": tags or None,
        "atribuido_a_id": atribuido_a_id,
    }
    response = requests.post(f"{BASE_URL}/tarefas", json=payload, headers=get_headers(token))
    return response.status_code == 200

def atualizar_status_tarefa(token, tarefa_id, novo_status):
    response = requests.patch(
        f"{BASE_URL}/tarefas/{tarefa_id}/status",
        params={"status": novo_status},
        headers=get_headers(token),
    )
    return response.status_code == 200


def atualizar_tarefa(token, tarefa_id, titulo, descricao, prioridade, data_vencimento=None, tags=None, atribuido_a_id=None):
    payload = {
        "titulo": titulo,
        "descricao": descricao,
        "prioridade": prioridade,
        "data_vencimento": data_vencimento.isoformat() if data_vencimento else None,
        "tags": tags or None,
        "atribuido_a_id": atribuido_a_id,
    }
    response = requests.put(f"{BASE_URL}/tarefas/{tarefa_id}", json=payload, headers=get_headers(token))
    return response.json() if response.status_code == 200 else None


def excluir_tarefa(token, tarefa_id):
    response = requests.delete(f"{BASE_URL}/tarefas/{tarefa_id}", headers=get_headers(token))
    return response.status_code == 204


# --- Usuário logado / grupos ---

def buscar_meu_usuario(token):
    response = requests.get(f"{BASE_URL}/me", headers=get_headers(token))
    return response.json() if response.status_code == 200 else None


def criar_grupo(token, nome):
    response = requests.post(f"{BASE_URL}/grupos", json={"nome": nome}, headers=get_headers(token))
    if response.status_code == 201:
        return response.json(), None
    return None, response.json().get("detail", "Não foi possível criar o grupo.")


def entrar_no_grupo(token, codigo_convite):
    response = requests.post(
        f"{BASE_URL}/grupos/entrar", json={"codigo_convite": codigo_convite}, headers=get_headers(token)
    )
    if response.status_code == 200:
        return response.json(), None
    return None, response.json().get("detail", "Não foi possível entrar no grupo.")


def sair_do_grupo(token):
    response = requests.post(f"{BASE_URL}/grupos/sair", headers=get_headers(token))
    return response.status_code == 204


def buscar_meu_grupo(token):
    response = requests.get(f"{BASE_URL}/grupos/meu", headers=get_headers(token))
    return response.json() if response.status_code == 200 else None


def buscar_membros(token):
    response = requests.get(f"{BASE_URL}/grupos/membros", headers=get_headers(token))
    return response.json() if response.status_code == 200 else []


def alterar_papel_membro(token, usuario_id, papel):
    response = requests.patch(
        f"{BASE_URL}/grupos/membros/{usuario_id}/papel", json={"papel": papel}, headers=get_headers(token)
    )
    return response.status_code == 200


def remover_membro(token, usuario_id):
    response = requests.delete(f"{BASE_URL}/grupos/membros/{usuario_id}", headers=get_headers(token))
    return response.status_code == 204