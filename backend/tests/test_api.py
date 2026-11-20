import pytest


@pytest.fixture(scope="module")
def lote(client):
    r = client.post("/api/lotes/simular", json={"escenario": "industrial", "filtros": ["HEPA-H13", "CAT-CO"], "duracion_min": 20})
    assert r.status_code == 201, r.text
    return r.json()


def test_simulacion_cierra_y_calcula(lote):
    L = lote["lote"]
    assert L["estado"] == "cerrado" and L["clasificacion"]
    ent = [p for p in lote["puntos"] if p["etapa"] == "entrada"]
    sal = [p for p in lote["puntos"] if p["etapa"] == "salida"]
    assert len(ent) == 3 and len(sal) == 3
    assert sum(p["pm25"] for p in sal) < sum(p["pm25"] for p in ent) * 0.2  # HEPA 20 min
    assert L["isr_salida"] < L["isr_entrada"]


def test_filtro_inexistente_422(client):
    r = client.post("/api/lotes/simular", json={"escenario": "industrial", "filtros": ["NOPE"], "duracion_min": 10})
    assert r.status_code == 422


def test_ingesta_manual_de_sensores(client):
    L = client.post("/api/lotes", json={"filtros": ["HEPA-H13"], "duracion_min": 10}).json()
    base = {"pm25": 90, "pm10": 140, "co2": 800, "co": 3, "tvoc": 0}
    lect = [{"etapa": "entrada", "t_seg": -40 + 20 * i, **base} for i in range(3)]
    lect += [{"etapa": "proceso", "t_seg": 60 * i, **{**base, "pm25": 90 * 0.7**i, "pm10": 140 * 0.7**i}} for i in range(1, 8)]
    lect += [{"etapa": "salida", "t_seg": 440 + 20 * i, **{**base, "pm25": 8, "pm10": 11}} for i in range(3)]
    assert client.post(f"/api/lotes/{L['id']}/lecturas", json=lect).status_code == 201
    r = client.post(f"/api/lotes/{L['id']}/cerrar")
    assert r.status_code == 200 and r.json()["lote"]["estado"] == "cerrado"
    assert client.post(f"/api/lotes/{L['id']}/cerrar").status_code == 409
    assert client.post(f"/api/lotes/{L['id']}/lecturas", json=lect[:1]).status_code == 409


def test_cierre_sin_salida_falla_limpio(client):
    L = client.post("/api/lotes", json={"filtros": ["HEPA-H13"]}).json()
    assert client.post(f"/api/lotes/{L['id']}/cerrar").status_code == 422


def test_recomendacion_y_kpis(client, lote):
    r = client.post("/api/recomendacion", json={"pm25": 120, "pm10": 200, "co2": 1500, "co": 12, "tvoc": 700}).json()
    assert "HEPA-H13" in r["filtros"] and r["duracion_sugerida_min"] >= 5
    k = client.get("/api/kpis").json()
    assert k["lotes"] >= 1 and k["pm25"]["reduccion"] > 50
    assert client.get("/api/lotes/9999").status_code == 404
    assert client.get("/api/reportes/lotes.csv").text.startswith("lote_id")
