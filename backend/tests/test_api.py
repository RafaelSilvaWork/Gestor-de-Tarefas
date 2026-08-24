def _obter_token(client, username="carol", password="senha123"):
    client.post("/register", params={"username": username, "password": password})
    r = client.post("/token", data={"username": username, "password": password})
    return r.json()["access_token"]


def test_registrar_usuario(client):
    r = client.post("/register", params={"username": "alice", "password": "senha123"})
    assert r.status_code == 201


def test_registrar_usuario_duplicado(client):
    client.post("/register", params={"username": "alice", "password": "senha123"})
    r = client.post("/register", params={"username": "alice", "password": "outra"})
    assert r.status_code == 400


def test_login_sucesso(client):
    client.post("/register", params={"username": "bob", "password": "senha123"})
    r = client.post("/token", data={"username": "bob", "password": "senha123"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_senha_incorreta(client):
    client.post("/register", params={"username": "bob", "password": "senha123"})
    r = client.post("/token", data={"username": "bob", "password": "errada"})
    assert r.status_code == 401


def test_me_retorna_dados_do_usuario_logado(client):
    token = _obter_token(client, username="quenia")
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    dados = r.json()
    assert dados["username"] == "quenia"
    assert dados["papel"] is None
    assert dados["grupo_id"] is None


def test_tarefas_exige_autenticacao(client):
    r = client.get("/tarefas")
    assert r.status_code == 401


def test_criar_e_listar_tarefa(client):
    token = _obter_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/tarefas",
        json={"titulo": "Estudar FastAPI", "descricao": "Ler a documentação", "prioridade": "Alta"},
        headers=headers,
    )
    assert r.status_code == 200
    tarefa = r.json()
    assert tarefa["titulo"] == "Estudar FastAPI"
    assert tarefa["status"] == "Pendente"

    r2 = client.get("/tarefas", headers=headers)
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_atualizar_status_tarefa(client):
    token = _obter_token(client, username="dave")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/tarefas", json={"titulo": "Revisar PR", "prioridade": "Média"}, headers=headers)
    tarefa_id = r.json()["id"]

    r2 = client.patch(f"/tarefas/{tarefa_id}/status", params={"status": "Concluído"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "Concluído"


def test_atualizar_status_tarefa_inexistente(client):
    token = _obter_token(client, username="erin")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.patch("/tarefas/9999/status", params={"status": "Concluído"}, headers=headers)
    assert r.status_code == 404


def test_isolamento_de_tarefas_entre_usuarios(client):
    token_a = _obter_token(client, username="frank")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    r = client.post("/tarefas", json={"titulo": "Tarefa do Frank", "prioridade": "Baixa"}, headers=headers_a)
    tarefa_id = r.json()["id"]

    token_b = _obter_token(client, username="grace")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r2 = client.get("/tarefas", headers=headers_b)
    assert r2.json() == []

    # Grace não pode alterar uma tarefa que pertence ao Frank.
    r3 = client.patch(f"/tarefas/{tarefa_id}/status", params={"status": "Concluído"}, headers=headers_b)
    assert r3.status_code == 404


def test_editar_tarefa(client):
    token = _obter_token(client, username="ivan")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/tarefas", json={"titulo": "Rascunho", "prioridade": "Baixa"}, headers=headers)
    tarefa_id = r.json()["id"]

    r2 = client.put(
        f"/tarefas/{tarefa_id}",
        json={"titulo": "Versão final", "descricao": "Revisado", "prioridade": "Alta"},
        headers=headers,
    )
    assert r2.status_code == 200
    tarefa = r2.json()
    assert tarefa["titulo"] == "Versão final"
    assert tarefa["descricao"] == "Revisado"
    assert tarefa["prioridade"] == "Alta"
    assert tarefa["status"] == "Pendente"  # editar não deve mexer no status


def test_editar_tarefa_inexistente(client):
    token = _obter_token(client, username="judy")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.put(
        "/tarefas/9999",
        json={"titulo": "X", "prioridade": "Alta"},
        headers=headers,
    )
    assert r.status_code == 404


def test_excluir_tarefa(client):
    token = _obter_token(client, username="kevin")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/tarefas", json={"titulo": "Descartável", "prioridade": "Baixa"}, headers=headers)
    tarefa_id = r.json()["id"]

    r2 = client.delete(f"/tarefas/{tarefa_id}", headers=headers)
    assert r2.status_code == 204

    r3 = client.get("/tarefas", headers=headers)
    assert r3.json() == []


def test_excluir_tarefa_de_outro_usuario_falha(client):
    token_a = _obter_token(client, username="laura")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    r = client.post("/tarefas", json={"titulo": "Da Laura", "prioridade": "Média"}, headers=headers_a)
    tarefa_id = r.json()["id"]

    token_b = _obter_token(client, username="marco")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r2 = client.delete(f"/tarefas/{tarefa_id}", headers=headers_b)
    assert r2.status_code == 404

    r3 = client.get("/tarefas", headers=headers_a)
    assert len(r3.json()) == 1


def test_criar_tarefa_com_prazo_e_tags(client):
    token = _obter_token(client, username="nadia")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/tarefas",
        json={
            "titulo": "Fechar contrato",
            "prioridade": "Urgente",
            "data_vencimento": "2026-12-01T18:00:00",
            "tags": ["Vendas", "Cliente-X"],
        },
        headers=headers,
    )
    assert r.status_code == 200
    tarefa = r.json()
    assert tarefa["data_vencimento"].startswith("2026-12-01T18:00:00")
    assert tarefa["tags"] == ["Vendas", "Cliente-X"]


def test_criar_tarefa_sem_prazo_nem_tags(client):
    token = _obter_token(client, username="oscar")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/tarefas", json={"titulo": "Tarefa simples", "prioridade": "Baixa"}, headers=headers)
    assert r.status_code == 200
    tarefa = r.json()
    assert tarefa["data_vencimento"] is None
    assert tarefa["tags"] is None


def test_editar_tarefa_atualiza_prazo_e_tags(client):
    token = _obter_token(client, username="paula")
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/tarefas", json={"titulo": "Rascunho", "prioridade": "Baixa"}, headers=headers)
    tarefa_id = r.json()["id"]

    r2 = client.put(
        f"/tarefas/{tarefa_id}",
        json={
            "titulo": "Rascunho",
            "prioridade": "Alta",
            "data_vencimento": "2026-11-15T09:00:00",
            "tags": ["Urgente-Interno"],
        },
        headers=headers,
    )
    assert r2.status_code == 200
    tarefa = r2.json()
    assert tarefa["data_vencimento"].startswith("2026-11-15T09:00:00")
    assert tarefa["tags"] == ["Urgente-Interno"]


def test_filtro_por_status_e_prioridade(client):
    token = _obter_token(client, username="heidi")
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/tarefas", json={"titulo": "A", "prioridade": "Alta"}, headers=headers)
    r = client.post("/tarefas", json={"titulo": "B", "prioridade": "Baixa"}, headers=headers)
    client.patch(f"/tarefas/{r.json()['id']}/status", params={"status": "Concluído"}, headers=headers)

    r_pendentes = client.get("/tarefas", params={"status": "Pendente"}, headers=headers)
    assert [t["titulo"] for t in r_pendentes.json()] == ["A"]

    r_baixa = client.get("/tarefas", params={"prioridade": "Baixa"}, headers=headers)
    assert [t["titulo"] for t in r_baixa.json()] == ["B"]
