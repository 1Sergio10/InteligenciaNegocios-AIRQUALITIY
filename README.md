# Alento

Plataforma de inteligencia de negocios para la admisión, depuración y verificación del aire.
Proyecto de *Inteligencia de Negocios* (Universidad Manuela Beltrán, 2026) — actividad **Air Quality Intelligence**.

Autores: Sergio Martínez Castañeda · Diego Rojas Martínez · Joel Lancheros. Profesor: Juan José Osorio.

## Qué hace

1. **Monitoreo**: registra el aire que ingresa (PM2.5, PM10, CO₂, CO y COVT) y lo clasifica con un índice de severidad basado en la Resolución 2254 de 2017 y las guías OMS 2021.
2. **Depuración**: simula la filtración con un modelo físico de cámara de mezcla; se elige el tren de filtros y el tiempo.
3. **Validación**: mide de nuevo, calcula el % de reducción y clasifica el resultado.
4. **Inteligencia de negocios**: tablero, alertas, recomendador de filtros, control EWMA y modelo de tiempo de purificación.

Los datos son **simulados**. El puerto de sensores es reemplazable: `POST /api/lotes`, `POST /api/lotes/{id}/lecturas`, `POST /api/lotes/{id}/cerrar`.

## Ejecutar

Con Docker (PostgreSQL 16 + API + tablero):

```bash
docker compose up --build        # http://localhost:8000
```

Sin Docker (SQLite):

```bash
cd backend
pip install -r requirements.txt
python -m app.seed               # 320 lotes simulados, reproducible
cd ../frontend && npm install && npm run build && cd ../backend
uvicorn app.main:app --port 8000 # http://localhost:8000 · docs en /docs
```

Con PostgreSQL propio: `ALENTO_DATABASE_URL=postgresql+psycopg://usuario:clave@host:5432/alento`. El DDL está en `backend/sql/schema_postgres.sql`.

Desarrollo del tablero: `cd frontend && npm run dev` (proxy a la API en el puerto 8000).

## Pruebas

```bash
cd backend && pytest             # 14 pruebas de dominio y API
```

## Estructura

```
backend/app    norms · physics · intelligence · services · analytics · main · seed
backend/sql    schema_postgres.sql
frontend/src   App.jsx · charts.jsx (SVG propio) · styles.css
docs           diagramas · capturas · guion_video.md · Informe_Alento_2026.docx
scripts        diagramas.py (regenera los diagramas del informe)
```

## Supuestos que conviene recordar

- Las eficiencias del catálogo de filtros son estimaciones de ingeniería, no mediciones.
- La planta simulada tiene un factor de desviación oculto por filtro (`SESGO_PLANTA` en `physics.py`) que el modelo debe aprender.
- CO₂ no está regulado; 1 000 ppm es un umbral operativo.
