"""Schemas de entrada/saída para a comunidade."""

from pydantic import BaseModel, Field, HttpUrl, field_validator


class LinkSchema(BaseModel):
    """Link validado de uma comunidade."""

    tipo: str = Field(min_length=1)
    url: HttpUrl


class ComunidadeSchema(BaseModel):
    """Contrato de uma comunidade no cadastro."""

    nome: str = Field(min_length=1)
    links: list[LinkSchema] = Field(default_factory=list)

    @field_validator("nome")
    @classmethod
    def nome_sem_espacos_extras(cls, valor: str) -> str:
        limpo = valor.strip()
        if not limpo:
            raise ValueError("nome não pode ser vazio")
        return limpo
