"""Testes herméticos do serviço de histórico (JSONL; tmp_path, sem rede)."""

import json
from datetime import datetime, timedelta

import pytest

from bot.services.historico_service import (
    CAMPOS,
    HistoricoCorrompido,
    RegistroHistorico,
    contar,
    ler_historico,
    registrar,
    ultimos,
)


@pytest.fixture
def caminho(tmp_path):
    return tmp_path / "history" / "historico.jsonl"


class TestRegistrar:
    def test_cria_arquivo_e_uma_linha(self, caminho):
        registrar(caminho, RegistroHistorico(acao="inserir", comunidade="GruPy Pará"))
        assert caminho.is_file()
        assert len(caminho.read_text(encoding="utf-8").strip().split("\n")) == 1

    def test_campos_e_ordem(self, caminho):
        registro = RegistroHistorico(acao="inserir", usuario_id=87681147, comunidade="Divas Digitais")
        registrar(caminho, registro)
        dados = json.loads(caminho.read_text(encoding="utf-8").strip())
        assert list(dados) == list(CAMPOS)
        assert dados["acao"] == "inserir"
        assert dados["usuario_id"] == 87681147

    def test_timestamp_automatico_belem(self, caminho):
        registrar(caminho, RegistroHistorico(acao="validar"))
        dados = json.loads(caminho.read_text(encoding="utf-8").strip())
        momento = datetime.fromisoformat(dados["timestamp"])
        assert momento.utcoffset() == timedelta(hours=-3)

    def test_timestamp_explicito_preservado(self, caminho):
        registrar(caminho, RegistroHistorico(acao="x", timestamp="2026-10-21T12:00:00-03:00"))
        assert ler_historico(caminho)[0].timestamp == "2026-10-21T12:00:00-03:00"

    def test_append_preserva_conteudo(self, caminho):
        registrar(caminho, RegistroHistorico(acao="um"))
        registrar(caminho, RegistroHistorico(acao="dois"))
        assert [r.acao for r in ler_historico(caminho)] == ["um", "dois"]

    def test_acentos_preservados(self, caminho):
        registrar(caminho, RegistroHistorico(acao="editar", comunidade="Açaí com Dados"))
        assert "Açaí com Dados" in caminho.read_text(encoding="utf-8")


class TestLer:
    def test_ausente_retorna_vazio(self, caminho):
        assert ler_historico(caminho) == []

    def test_round_trip_campos(self, caminho):
        original = RegistroHistorico(
            acao="editar",
            usuario_id=1,
            secao="Linguagens de Programação",
            comunidade="Elixir Carajás",
            antes="a",
            depois="b",
            backup_path="backup/README_20261021_150859.bak",
            commit="abc123",
        )
        registrar(caminho, original)
        lido = ler_historico(caminho)[0]
        assert lido.para_dict() == original.para_dict()

    def test_ignora_linhas_vazias(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text(
            json.dumps({"acao": "um"}) + "\n\n" + json.dumps({"acao": "dois"}) + "\n",
            encoding="utf-8",
        )
        assert [r.acao for r in ler_historico(caminho)] == ["um", "dois"]

    def test_linha_invalida(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text("{nao-json}\n", encoding="utf-8")
        with pytest.raises(HistoricoCorrompido):
            ler_historico(caminho)

    def test_linha_nao_objeto(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text("[1, 2, 3]\n", encoding="utf-8")
        with pytest.raises(HistoricoCorrompido):
            ler_historico(caminho)

    def test_registro_sem_acao(self, caminho):
        caminho.parent.mkdir(parents=True)
        caminho.write_text(json.dumps({"usuario_id": 1}) + "\n", encoding="utf-8")
        with pytest.raises(HistoricoCorrompido):
            ler_historico(caminho)


class TestUltimosContar:
    def test_ultimos_n(self, caminho):
        for acao in ("a", "b", "c", "d"):
            registrar(caminho, RegistroHistorico(acao=acao))
        assert [r.acao for r in ultimos(caminho, 2)] == ["c", "d"]

    def test_ultimos_zero(self, caminho):
        registrar(caminho, RegistroHistorico(acao="a"))
        assert ultimos(caminho, 0) == []

    def test_contar(self, caminho):
        assert contar(caminho) == 0
        registrar(caminho, RegistroHistorico(acao="a"))
        assert contar(caminho) == 1
