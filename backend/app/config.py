"""Configuración de Alento. Todo se resuelve por variables de entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # PostgreSQL en producción:  postgresql+psycopg://alento:alento@db:5432/alento
    # SQLite por defecto para que el proyecto arranque sin infraestructura.
    database_url: str = os.getenv("ALENTO_DATABASE_URL", "sqlite:///./alento.db")
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("ALENTO_CORS", "http://localhost:5173").split(",") if o.strip()
    )
    static_dir: Path = Path(os.getenv("ALENTO_STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
    semilla: int = int(os.getenv("ALENTO_SEMILLA", "2026"))


settings = Settings()
