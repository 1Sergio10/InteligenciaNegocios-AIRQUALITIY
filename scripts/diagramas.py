"""Genera los diagramas del informe (SVG + PNG). Estilo: plano de ductos sobre papel."""
import glob, random, pathlib, base64
from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "diagramas"
FONTS = {p.split("/")[-1]: p for p in glob.glob(str(pathlib.Path(__file__).resolve().parents[1] / "frontend/dist/assets/*.woff2"))}
def font(prefix):
    path = next(v for k, v in FONTS.items() if k.startswith(prefix))
    return "data:font/woff2;base64," + base64.b64encode(open(path, "rb").read()).decode()
CSS = f"""
@font-face {{ font-family: Fr; src: url('{font("fraunces-latin-wght-normal")}'); font-weight: 100 900; }}
@font-face {{ font-family: FrI; src: url('{font("fraunces-latin-wght-italic")}'); font-weight: 100 900; }}
@font-face {{ font-family: Mono; src: url('{font("ibm-plex-mono-latin-400")}'); font-weight: 400; }}
@font-face {{ font-family: Mono; src: url('{font("ibm-plex-mono-latin-500")}'); font-weight: 500; }}
body {{ margin:0; background:#efe9dc; }}
.ti {{ font: 600 30px Fr; fill:#182a3f; }} .sub {{ font: italic 400 17px FrI; fill:#4a5568; }}
.h {{ font: 600 19px Fr; fill:#182a3f; }} .hh {{ font: 600 19px Fr; fill:#efe9dc; }} .m {{ font: 400 13px Mono; fill:#182a3f; }} .mm {{ font: 500 13px Mono; fill:#182a3f; }}
.g {{ font: 400 12px Mono; fill:#6b6552; }} .oc {{ font: 500 13px Mono; fill:#b4532a; }} .vd {{ font: 500 13px Mono; fill:#2b7a69; }}
"""
INK, OCRE, VERDE, PAPEL, LIN = "#182a3f", "#b4532a", "#2b7a69", "#efe9dc", "#cfc6b0"

def wrap(w, h, body, title, sub):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><style>{CSS}</style>
<rect width="{w}" height="{h}" fill="{PAPEL}"/>
<text x="40" y="52" class="ti">{title}</text><text x="40" y="78" class="sub">{sub}</text>
<line x1="40" x2="{w-40}" y1="92" y2="92" stroke="{INK}" stroke-width="2"/>{body}</svg>"""

def duct(x, y, w, h, stroke=INK, fill="none", dash=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" stroke="{stroke}" stroke-width="2.2" stroke-dasharray="{dash}"/>'
            f'<rect x="{x+7}" y="{y+7}" width="{w-14}" height="{h-14}" rx="{(h-14)/2}" fill="none" stroke="{stroke}" stroke-width="0.8" opacity=".5"/>')

def arch():
    random.seed(7)
    b = []
    # lane aire
    b.append(f'<text x="40" y="112" class="g">CAMINO DEL AIRE</text>')
    X0, X1, Y, H = 60, 1540, 150, 150
    b.append(duct(X0, Y, X1 - X0, H, fill="#f6f1e4"))
    stations = [(150, "① Admisión", "PM2.5 · PM10 · CO₂ · CO · COVT", "3 lecturas, 20 s"),
                (520, "② Cámara de mezcla", "V = 12 m³ · Q = 180 m³/h", "recirculación"),
                (1030, "③ Tren de filtros", "G4 · HEPA · carbón · CAT · ABS", "η por paso, en serie"),
                (1360, "④ Verificación", "3 lecturas con ventilador detenido", "% de reducción")]
    # partículas: densidad decreciente
    for i in range(190):
        x = random.uniform(X0 + 40, X1 - 40)
        dens = max(0.03, 1 - (x - X0) / (X1 - X0) * 1.05)
        if random.random() < dens ** 1.5:
            y = random.uniform(Y + 18, Y + H - 18)
            col = OCRE if x < 1000 else (VERDE if x > 1250 else "#7a6a3a")
            b.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{random.choice([1.6,2.2,3])}" fill="{col}" opacity=".75"/>')
    # cartuchos
    cx = 1000
    for i, (nm, w) in enumerate([("G4", 22), ("HEPA", 46), ("C", 30), ("CAT", 30), ("ABS", 30)]):
        b.append(f'<rect x="{cx}" y="{Y+14}" width="{w}" height="{H-28}" fill="{PAPEL}" stroke="{INK}" stroke-width="2"/>')
        for k in range(int((H - 40) / 10)):
            b.append(f'<line x1="{cx+3}" x2="{cx+w-3}" y1="{Y+24+k*10}" y2="{Y+24+k*10}" stroke="{INK}" stroke-width=".7" opacity=".5"/>')
        b.append(f'<text x="{cx+w/2}" y="{Y+H+16}" text-anchor="middle" class="g">{nm}</text>')
        cx += w + 8
    b.append(f'<rect x="440" y="{Y+14}" width="250" height="{H-28}" rx="10" fill="none" stroke="{INK}" stroke-width="1.5" stroke-dasharray="6 5"/>')
    for x, t, l1, l2 in stations:
        b.append(f'<text x="{x}" y="{Y-14}" class="h">{t}</text>')
    b.append(f'<text x="150" y="{Y+H+34}" class="m">PMS-style láser · NDIR · electroquímico</text>')
    b.append(f'<text x="440" y="{Y+H+34}" class="m">dC/dt = −k·(C − C_fondo),  k = Q·η/V + k_dep</text>')
    b.append(f'<text x="1000" y="{Y+H+34}" class="m">η = 1 − Π(1 − η_j)</text>')
    b.append(f'<text x="1360" y="{Y+H+34}" class="m">reducción = 1 − C_sal / C_ent</text>')
    b.append(f'<text x="1330" y="{Y+75}" class="vd" text-anchor="end">aire depurado →</text>')
    b.append(f'<text x="96" y="{Y+H+60}" class="oc">aire contaminado entra →</text>')
    # lane datos
    b.append(f'<text x="40" y="428" class="g">CAMINO DEL DATO</text>')
    Y2, H2 = 456, 96
    b.append(duct(X0, Y2, X1 - X0, H2, stroke=VERDE, dash="2 0"))
    nodes = [(100, "Puerto de sensores", "simulado hoy,\nreal mañana (MQTT/HTTP)"), (390, "API  FastAPI", "lote · lecturas · cierre\nreglas y modelo"),
             (690, "PostgreSQL", "lote · medicion · alerta\nvw_eficiencia_lote"), (980, "Analítica  pandas", "KPIs · reloj 24 h\ntrenes · validación"),
             (1270, "Tablero  React", "SVG propio · alertas\nreportes CSV")]
    for x, t, d in nodes:
        b.append(f'<rect x="{x}" y="{Y2+14}" width="240" height="{H2-28}" rx="8" fill="{PAPEL}" stroke="{VERDE}" stroke-width="1.8"/>')
        b.append(f'<text x="{x+14}" y="{Y2+38}" class="mm">{t}</text>')
        for j, line in enumerate(d.split("\n")):
            b.append(f'<text x="{x+14}" y="{Y2+56+j*15}" class="g">{line}</text>')
    for a, c in [(340, 390), (630, 690), (920, 980), (1220, 1270)]:
        b.append(f'<path d="M{a} {Y2+48} H{c-6} M{c-14} {Y2+42} L{c-4} {Y2+48} L{c-14} {Y2+54}" stroke="{VERDE}" stroke-width="2" fill="none"/>')
    # conectores
    for x in (150, 1400):
        b.append(f'<path d="M{x} {Y+H+44} V{Y2-6}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="3 4"/>')
    b.append(f'<path d="M{1000+120} {Y+H+44} V{Y2-6}" stroke="{INK}" stroke-width="1.2" stroke-dasharray="3 4"/>')
    # módulos
    b.append(f'<text x="40" y="620" class="g">MÓDULOS DE LA GUÍA</text>')
    for i, (n, t, c) in enumerate([("1", "Monitoreo del aire contaminado", OCRE), ("2", "Proceso de descontaminación", INK), ("3", "Validación del aire purificado", VERDE), ("4", "Inteligencia de negocios", INK)]):
        x = 40 + i * 395
        b.append(f'<circle cx="{x+16}" cy="652" r="15" fill="none" stroke="{c}" stroke-width="2"/><text x="{x+16}" y="658" text-anchor="middle" class="h" fill="{c}">{n}</text>')
        b.append(f'<text x="{x+42}" y="657" class="m">{t}</text>')
    return wrap(1600, 700, "".join(b), "Alento · arquitectura de dos ductos", "El aire se depura por arriba; su rastro de datos fluye por abajo hasta el tablero.")

def er():
    b = []
    cards = {
        "filtro": (60, 130, ["id  PK", "codigo  único", "nombre · tecnologia", "eta_pm25 · eta_pm10", "eta_co2 · eta_co · eta_tvoc"], INK),
        "lote_filtro": (60, 420, ["lote_id  PK,FK", "filtro_id  PK,FK", "orden"], INK),
        "lote": (470, 250, ["id  PK", "codigo  único", "escenario · estado", "ingreso_ts · fin_ts", "duracion_min · volumen_m3 · caudal_m3h", "firma_tren", "isr_entrada · isr_salida", "clasificacion · reduccion_global", "t_meta_min · t_meta_pred_min"], OCRE),
        "medicion": (940, 130, ["id  PK", "lote_id  FK", "etapa  entrada|proceso|salida", "ts · t_seg", "pm25 · pm10 · co2 · co · tvoc"], VERDE),
        "tasa_decaimiento": (940, 380, ["lote_id  PK,FK", "contaminante  PK", "k_h · r2 · n_puntos"], VERDE),
        "alerta": (940, 560, ["id  PK", "lote_id  FK", "ts · tipo · severidad", "contaminante · valor · umbral", "mensaje"], VERDE),
        "vw_eficiencia_lote": (470, 600, ["vista: promedio de entrada y", "salida por lote para los", "cuatro contaminantes"], "#6b6552"),
    }
    pos = {}
    for k, (x, y, rows, col) in cards.items():
        w = 330 if k != "lote" else 380
        h = 46 + len(rows) * 21
        pos[k] = (x, y, w, h)
        dash = ' stroke-dasharray="6 4"' if k.startswith("vw") else ""
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f6f1e4" stroke="{col}" stroke-width="2"{dash}/>')
        b.append(f'<path d="M{x} {y} h{w} v34 h-{w}z" fill="{col}"/><text x="{x+14}" y="{y+23}" class="hh">{k}</text>')
        for i, r in enumerate(rows):
            b.append(f'<text x="{x+14}" y="{y+58+i*21}" class="m">{r}</text>')
    def link(a, c, la, lc, mid=None):
        xa, ya, wa, ha = pos[a]; xc, yc, wc, hc = pos[c]
        if a == "filtro":
            b.append(f'<path d="M{xa+wa/2} {ya+ha} V{yc}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
            b.append(f'<text x="{xa+wa/2+8}" y="{ya+ha+18}" class="oc">{la}</text><text x="{xa+wa/2+8}" y="{yc-8}" class="oc">{lc}</text>')
            return
        if xa < xc:
            x1, x2 = xa + wa, xc
        else:
            x1, x2 = xa, xc + wc
        y1, y2 = ya + ha / 2, yc + hc / 2
        mx = (x1 + x2) / 2
        b.append(f'<path d="M{x1} {y1} H{mx} V{y2} H{x2}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
        b.append(f'<text x="{x1 + (8 if x1 < x2 else -14)}" y="{y1-6}" class="oc">{la}</text><text x="{x2 + (-14 if x1 < x2 else 8)}" y="{y2-6}" class="oc">{lc}</text>')
    link("filtro", "lote_filtro", "1", "N")
    link("lote_filtro", "lote", "N", "1")
    link("lote", "medicion", "1", "N")
    link("lote", "tasa_decaimiento", "1", "N")
    link("lote", "alerta", "1", "N")
    b.append(f'<path d="M660 {pos["lote"][1]+pos["lote"][3]} V600" stroke="#6b6552" stroke-width="1.4" stroke-dasharray="4 4"/>')
    return wrap(1360, 800, "".join(b), "Alento · modelo de datos", "Tercera forma normal; las mediciones quedan en formato ancho porque los cinco contaminantes se comparan siempre entre sí.")

def timeline():
    b = []
    x0, x1, y = 90, 1510, 440
    bandas = [(90, 330, "ENTRADA", "t = −40, −20, 0 s", "3 lecturas, ventilador apagado", OCRE), (330, 1180, "PROCESO", "t = 30 s, 60 s, … , T", "1 lectura cada 30 s con el tren recirculando", INK), (1180, 1510, "SALIDA", "t = T+20, +40, +60 s", "3 lecturas, ventilador detenido", VERDE)]
    for a, c, t, tt, d, col in bandas:
        b.append(f'<rect x="{a}" y="{y-44}" width="{c-a-6}" height="88" fill="{col}" opacity=".10"/><rect x="{a}" y="{y-44}" width="{c-a-6}" height="5" fill="{col}"/>')
        b.append(f'<text x="{a+12}" y="{y-16}" class="h" fill="{col}">{t}</text><text x="{a+12}" y="{y+6}" class="m">{tt}</text><text x="{a+12}" y="{y+26}" class="g">{d}</text>')
    import math
    pts = []
    for i in range(40):
        t = i / 39
        xx = 345 + t * 820
        yy = y - 70 - (170 * math.exp(-4.2 * t)) * 0.75
        pts.append((xx, yy))
    b.append("<path d=\"M" + " L".join(f"{p[0]:.0f},{p[1]:.0f}" for p in pts) + f"\" fill=\"none\" stroke=\"{INK}\" stroke-width=\"2\"/>")
    for p in pts[::2]:
        b.append(f'<circle cx="{p[0]:.0f}" cy="{p[1]:.0f}" r="3" fill="{INK}"/>')
    for i in range(3):
        b.append(f'<circle cx="{150+i*60}" cy="{y-70-170*.75+(i-1)*3}" r="5" fill="{OCRE}"/><circle cx="{1220+i*60}" cy="{y-70+(i-1)*2}" r="5" fill="{VERDE}"/>')
    b.append(f'<text x="560" y="{y-215}" class="m">C(t) = C_fondo + (C₀ − C_fondo)·e^(−k t)</text>')
    # cálculos al cierre
    b.append(f'<text x="90" y="550" class="g">AL CERRAR EL LOTE</text>')
    items = [("Reducción", "% = 100·(1 − C_sal/C_ent) por contaminante"), ("Severidad", "ISR = máx(C_i / límite_i): Bajo · Moderado · Alto · Muy alto · Crítico"),
             ("Resultado", "CUMPLE_OMS · CUMPLE_NORMA · PARCIAL · INSUFICIENTE · SIN_NECESIDAD"), ("Tiempo a meta", "primer cruce bajo la norma (mediana móvil de 3)"),
             ("Aprendizaje", "k estimada por regresión de ln(C − C_fondo) contra t"), ("Alertas", "ingreso, salida, baja eficiencia, filtro no aplicable, anomalía EWMA")]
    for i, (a, d) in enumerate(items):
        x, yy = 90 + (i % 2) * 720, 575 + (i // 2) * 64
        b.append(f'<rect x="{x}" y="{yy}" width="690" height="50" fill="none" stroke="{LIN}" stroke-width="1.5"/><rect x="{x}" y="{yy}" width="6" height="50" fill="{INK}"/>')
        b.append(f'<text x="{x+20}" y="{yy+21}" class="mm">{a}</text><text x="{x+20}" y="{yy+39}" class="g">{d}</text>')
    return wrap(1600, 820, "".join(b), "Ciclo de vida de un lote", "Cada tratamiento deja tres tipos de lectura y se cierra con resultados calculados una sola vez.")

with sync_playwright() as p:
    br = p.chromium.launch()
    for name, fn, (w, h) in [("arquitectura", arch, (1600, 700)), ("modelo_datos", er, (1360, 800)), ("ciclo_lote", timeline, (1600, 820))]:
        svg = fn()
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        pg.close()
    br.close()
print("ok")
