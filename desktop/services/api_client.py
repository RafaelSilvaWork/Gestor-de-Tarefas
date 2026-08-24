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

def criar_tarefa(token, titulo, descricao, prioridade, data_vencimento=None, tags=None):
    payload = {
        "titulo": titulo,
        "descricao": descricao,
        "prioridade": prioridade,
        "data_vencimento": data_vencimento.isoformat() if data_vencimento else None,
        "tags": tags or None,
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


def atualizar_tarefa(token, tarefa_id, titulo, descricao, prioridade, data_vencimento=None, tags=None):
    payload = {
        "titulo": titulo,
        "descricao": descricao,
        "prioridade": prioridade,
        "data_vencimento": data_vencimento.isoformat() if data_vencimento else None,
        "tags": tags or None,
    }
    response = requests.put(f"{BASE_URL}/tarefas/{tarefa_id}", json=payload, headers=get_headers(token))
    return response.json() if response.status_code == 200 else None


def excluir_tarefa(token, tarefa_id):
    response = requests.delete(f"{BASE_URL}/tarefas/{tarefa_id}", headers=get_headers(token))
    return response.status_code == 204