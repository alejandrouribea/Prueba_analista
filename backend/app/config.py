from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_prefix="CONCILIADOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_nombre: str = "Conciliador de Facturas y Retenciones"
    app_version: str = "1.0.0"

    cors_origenes: list[str] = Field(
        default=[
            "http://localhost:4200",
            "http://127.0.0.1:4200",
        ]
    )

    # Los valores de los CSV vienen redondeados a la unidad, con 1 peso alcanza
    # para absorber el redondeo sin tapar diferencias reales.
    tolerancia_pesos: Decimal = Decimal("1")

    @field_validator("cors_origenes", mode="before")
    @classmethod
    def _separar_origenes(cls, valor: object) -> object:
        if isinstance(valor, str) and not valor.strip().startswith("["):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor


@lru_cache
def get_settings() -> Settings:
    return Settings()
