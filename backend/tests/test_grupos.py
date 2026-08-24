def _obter_token(client, username, password="senha123"):
    client.post("/register", params={"username": username, "password": password})
    r = client.post("/token", data={"username": username, "password": password})
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_criar_grupo_vira_admin(client):
    token = _obter_token(client, "ana")
    r = client.post("/grupos", json={"nome": "Equipe Vendas"}, headers=_headers(token))
    assert r.status_code == 201
    grupo = r.json()
    assert grupo["nome"] == "Equipe Vendas"
    assert len(grupo["codigo_convite"]) == 8

    membros = client.get("/grupos/membros", headers=_headers(token)).json()
    assert len(membros) == 1
    assert membros[0]["papel"] == "admin"


def test_criar_grupo_falha_se_ja_tem_grupo(client):
    token = _obter_token(client, "bruno")
    client.post("/grupos", json={"nome": "Equipe A"}, headers=_headers(token))
    r = client.post("/grupos", json={"nome": "Equipe B"}, headers=_headers(token))
    assert r.status_code == 400


def test_entrar_no_grupo_com_codigo_valido(client):
    token_admin = _obter_token(client, "carla")
    grupo = client.post("/grupos", json={"nome": "Equipe Suporte"}, headers=_headers(token_admin)).json()

    token_func = _obter_token(client, "davi")
    r = client.post("/grupos/entrar", json={"codigo_convite": grupo["codigo_convite"]}, headers=_headers(token_func))
    assert r.status_code == 200
    assert r.json()["id"] == grupo["id"]

    membros = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    papeis = {m["username"]: m["papel"] for m in membros}
    assert papeis == {"carla": "admin", "davi": "funcionario"}


def test_entrar_com_codigo_invalido(client):
    token = _obter_token(client, "erica")
    r = client.post("/grupos/entrar", json={"codigo_convite": "XXXXXXXX"}, headers=_headers(token))
    assert r.status_code == 404


def test_entrar_falha_se_ja_tem_grupo(client):
    token_admin = _obter_token(client, "fabio")
    grupo = client.post("/grupos", json={"nome": "Equipe X"}, headers=_headers(token_admin)).json()

    token_outro = _obter_token(client, "gustavo")
    client.post("/grupos", json={"nome": "Equipe Y"}, headers=_headers(token_outro))

    r = client.post("/grupos/entrar", json={"codigo_convite": grupo["codigo_convite"]}, headers=_headers(token_outro))
    assert r.status_code == 400


def _montar_grupo_com_funcionario(client, admin_username, func_username):
    token_admin = _obter_token(client, admin_username)
    grupo = client.post("/grupos", json={"nome": "Equipe"}, headers=_headers(token_admin)).json()
    token_func = _obter_token(client, func_username)
    client.post("/grupos/entrar", json={"codigo_convite": grupo["codigo_convite"]}, headers=_headers(token_func))
    membros = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    id_func = next(m["id"] for m in membros if m["username"] == func_username)
    return token_admin, token_func, id_func


def test_admin_atribui_tarefa_a_funcionario(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "heitor", "iris")

    r = client.post(
        "/tarefas",
        json={"titulo": "Ligar para cliente", "prioridade": "Alta", "atribuido_a_id": id_func},
        headers=_headers(token_admin),
    )
    assert r.status_code == 200
    tarefa = r.json()
    assert tarefa["atribuido_a_id"] == id_func
    assert tarefa["atribuido_a_username"] == "iris"

    # o funcionário vê a tarefa atribuída a ele
    tarefas_func = client.get("/tarefas", headers=_headers(token_func)).json()
    assert len(tarefas_func) == 1
    assert tarefas_func[0]["titulo"] == "Ligar para cliente"


def test_admin_ve_todas_as_tarefas_do_grupo(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "joao", "karen")

    client.post("/tarefas", json={"titulo": "Tarefa do admin", "prioridade": "Baixa"}, headers=_headers(token_admin))
    client.post(
        "/tarefas",
        json={"titulo": "Tarefa da funcionaria", "prioridade": "Média", "atribuido_a_id": id_func},
        headers=_headers(token_func),
    )

    tarefas_admin = client.get("/tarefas", headers=_headers(token_admin)).json()
    assert len(tarefas_admin) == 2


def test_funcionario_nao_consegue_atribuir_tarefa_a_outro(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "lucas", "marina")

    # marina tenta criar uma tarefa "atribuída" ao admin (id != id_func) — deve ser ignorado
    membros = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    id_admin = next(m["id"] for m in membros if m["username"] == "lucas")

    r = client.post(
        "/tarefas",
        json={"titulo": "Tentativa", "prioridade": "Baixa", "atribuido_a_id": id_admin},
        headers=_headers(token_func),
    )
    assert r.status_code == 200
    assert r.json()["atribuido_a_id"] == id_func  # ficou atribuída a ela mesma, não ao admin


def test_funcionario_pode_mudar_status_da_propria_tarefa(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "nadia", "otavio")

    r = client.post(
        "/tarefas",
        json={"titulo": "Fazer relatório", "prioridade": "Alta", "atribuido_a_id": id_func},
        headers=_headers(token_admin),
    )
    tarefa_id = r.json()["id"]

    r2 = client.patch(f"/tarefas/{tarefa_id}/status", params={"status": "Concluído"}, headers=_headers(token_func))
    assert r2.status_code == 200
    assert r2.json()["status"] == "Concluído"


def test_funcionario_nao_pode_excluir_tarefa(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "paulo", "quiteria")

    r = client.post(
        "/tarefas",
        json={"titulo": "Tarefa", "prioridade": "Alta", "atribuido_a_id": id_func},
        headers=_headers(token_admin),
    )
    tarefa_id = r.json()["id"]

    r2 = client.delete(f"/tarefas/{tarefa_id}", headers=_headers(token_func))
    assert r2.status_code == 404  # não autorizado (mesmo padrão 404 usado pro resto da API)

    r3 = client.delete(f"/tarefas/{tarefa_id}", headers=_headers(token_admin))
    assert r3.status_code == 204


def test_admin_altera_papel_de_membro(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "raquel", "samuel")

    r = client.patch(
        f"/grupos/membros/{id_func}/papel", json={"papel": "admin"}, headers=_headers(token_admin)
    )
    assert r.status_code == 200
    assert r.json()["papel"] == "admin"

    # agora samuel também consegue ver todas as tarefas do grupo (é admin)
    r2 = client.get("/tarefas", headers=_headers(token_func))
    assert r2.status_code == 200


def test_funcionario_nao_pode_alterar_papel(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "tania", "ursula")
    membros = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    id_admin = next(m["id"] for m in membros if m["username"] == "tania")

    r = client.patch(
        f"/grupos/membros/{id_admin}/papel", json={"papel": "funcionario"}, headers=_headers(token_func)
    )
    assert r.status_code == 403


def test_remover_membro_reatribui_tarefas(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "victor", "wanda")

    r = client.post(
        "/tarefas",
        json={"titulo": "Tarefa da Wanda", "prioridade": "Alta", "atribuido_a_id": id_func},
        headers=_headers(token_admin),
    )
    tarefa_id = r.json()["id"]

    r2 = client.delete(f"/grupos/membros/{id_func}", headers=_headers(token_admin))
    assert r2.status_code == 204

    # a tarefa volta para quem criou (o admin)
    tarefas_admin = client.get("/tarefas", headers=_headers(token_admin)).json()
    tarefa_atualizada = next(t for t in tarefas_admin if t["id"] == tarefa_id)
    membros_admin = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    assert len(membros_admin) == 1  # wanda saiu do grupo
    assert tarefa_atualizada["atribuido_a_username"] == "victor"


def test_sair_do_grupo(client):
    token_admin, token_func, id_func = _montar_grupo_com_funcionario(client, "xavier", "yolanda")

    r = client.post("/grupos/sair", headers=_headers(token_func))
    assert r.status_code == 204

    r2 = client.get("/grupos/membros", headers=_headers(token_admin)).json()
    assert len(r2) == 1

    # yolanda voltou a ser uma usuária solo, sem grupo
    r3 = client.get("/grupos/meu", headers=_headers(token_func))
    assert r3.status_code == 404


def test_usuario_solo_continua_funcionando_normalmente(client):
    token = _obter_token(client, "zeca")
    r = client.post("/tarefas", json={"titulo": "Tarefa pessoal", "prioridade": "Baixa"}, headers=_headers(token))
    assert r.status_code == 200
    tarefa = r.json()
    assert tarefa["grupo_id"] is None
    assert tarefa["atribuido_a_id"] == tarefa["usuario_id"]

    r2 = client.get("/tarefas", headers=_headers(token)).json()
    assert len(r2) == 1

    r3 = client.delete(f"/tarefas/{tarefa['id']}", headers=_headers(token))
    assert r3.status_code == 204
