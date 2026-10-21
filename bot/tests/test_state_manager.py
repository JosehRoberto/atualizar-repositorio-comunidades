"""Testes herméticos da máquina de estados (sem Telegram, sem I/O)."""

import pytest

from bot.handlers.state_manager import (
    CAMPO_AMBOS,
    CAMPO_LINKS,
    CAMPO_NOME,
    ORDEM_POR_ACAO,
    Acao,
    ConversaUsuario,
    EstadoConversa,
    GerenciadorEstado,
)
from bot.models.comunidade import Comunidade, Link


@pytest.fixture
def gerenciador():
    return GerenciadorEstado()


class TestConversaUsuario:
    def test_inicia_ocioso(self):
        conv = ConversaUsuario(user_id=1)
        assert conv.estado is EstadoConversa.IDLE
        assert conv.acao is None
        assert conv.ativa() is False

    def test_ativa_quando_em_fluxo(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        assert conv.ativa() is True

    def test_reset_limpa_tudo(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        conv.rascunho = Comunidade("X", [Link("Site", "https://x.com")])
        conv.nome_original = "X"
        conv.secao_alvo = "Linguagens"
        conv.campo_editar = CAMPO_NOME
        conv.reset()
        assert conv.estado is EstadoConversa.IDLE
        assert conv.acao is None
        assert conv.rascunho is None
        assert conv.nome_original is None
        assert conv.secao_alvo is None
        assert conv.campo_editar is None
        assert conv.iniciada_em is None


class TestGerenciadorBasico:
    def test_obter_cria_e_reutiliza(self, gerenciador):
        conv1 = gerenciador.obter(42)
        conv2 = gerenciador.obter(42)
        assert conv1 is conv2
        assert conv1.user_id == 42

    def test_usuarios_independentes(self, gerenciador):
        gerenciador.iniciar(1, Acao.NOVA)
        gerenciador.iniciar(2, Acao.REMOVER)
        assert gerenciador.obter(1).acao is Acao.NOVA
        assert gerenciador.obter(2).acao is Acao.REMOVER

    def test_iniciar_reinicia_estado_anterior(self, gerenciador):
        gerenciador.iniciar(1, Acao.NOVA)
        gerenciador.obter(1).estado = EstadoConversa.PREVIEW
        gerenciador.iniciar(1, Acao.EDITAR)
        assert gerenciador.obter(1).estado is EstadoConversa.EDITAR_NOME
        assert gerenciador.obter(1).acao is Acao.EDITAR

    def test_iniciar_com_rascunho(self, gerenciador):
        rascunho = Comunidade("GruPy Pará", [Link("Site", "https://grupy.pa")])
        conv = gerenciador.iniciar(1, Acao.NOVA, rascunho=rascunho)
        assert conv.rascunho is rascunho

    def test_encerrar_volta_a_idle(self, gerenciador):
        gerenciador.iniciar(1, Acao.NOVA)
        gerenciador.encerrar(1)
        assert gerenciador.obter(1).estado is EstadoConversa.IDLE
        assert gerenciador.obter(1).acao is None

    def test_iniciada_em_preenchido(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        assert conv.iniciada_em is not None


class TestOrdemPorAcao:
    def test_cada_acao_tem_ordem(self):
        assert set(ORDEM_POR_ACAO) == {
            Acao.NOVA,
            Acao.EDITAR,
            Acao.REMOVER,
            Acao.BUSCAR,
            Acao.PUBLICAR,
            Acao.RESTAURAR,
        }

    def test_nova_termina_em_aprovacao(self):
        assert ORDEM_POR_ACAO[Acao.NOVA][-1] is EstadoConversa.APROVACAO

    def test_editar_termina_em_aprovacao(self):
        assert ORDEM_POR_ACAO[Acao.EDITAR][-1] is EstadoConversa.APROVACAO

    def test_remover_nao_tem_preview(self):
        assert EstadoConversa.PREVIEW not in ORDEM_POR_ACAO[Acao.REMOVER]

    def test_buscar_e_terminal(self):
        assert ORDEM_POR_ACAO[Acao.BUSCAR] == [EstadoConversa.BUSCAR_NOME]

    def test_publicar_tem_confirmacao(self):
        assert ORDEM_POR_ACAO[Acao.PUBLICAR] == [EstadoConversa.PUBLICAR_CONFIRMACAO]

    def test_restaurar_sequencia_de_estados(self):
        assert ORDEM_POR_ACAO[Acao.RESTAURAR] == [
            EstadoConversa.RESTAURAR_ESCOLHA,
            EstadoConversa.RESTAURAR_CONFIRMACAO,
        ]


class TestProximoEstado:
    def test_sem_acao_retorna_none(self, gerenciador):
        assert gerenciador.proximo_estado(gerenciador.obter(1)) is None

    def test_nova_sequencia(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        esperado = [
            EstadoConversa.NOVA_LINKS,
            EstadoConversa.NOVA_SECAO,
            EstadoConversa.PREVIEW,
            EstadoConversa.APROVACAO,
            None,
        ]
        obtido = []
        while True:
            proximo = gerenciador.proximo_estado(conv)
            obtido.append(proximo)
            if proximo is None:
                break
            conv.estado = proximo
        assert obtido == esperado

    def test_remover_sequencia(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.REMOVER)
        assert conv.estado is EstadoConversa.REMOVER_NOME
        conv.estado = gerenciador.proximo_estado(conv)
        assert conv.estado is EstadoConversa.REMOVER_CONFIRMACAO
        assert gerenciador.proximo_estado(conv) is None

    def test_publicar_sequencia(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.PUBLICAR)
        assert conv.estado is EstadoConversa.PUBLICAR_CONFIRMACAO
        assert gerenciador.proximo_estado(conv) is None

    def test_restaurar_sequencia(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.RESTAURAR)
        assert conv.estado is EstadoConversa.RESTAURAR_ESCOLHA
        conv.estado = gerenciador.proximo_estado(conv)
        assert conv.estado is EstadoConversa.RESTAURAR_CONFIRMACAO
        assert gerenciador.proximo_estado(conv) is None

    def test_editar_apenas_nome(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.EDITAR)
        conv.estado = EstadoConversa.EDITAR_ESCOLHA
        conv.campo_editar = CAMPO_NOME
        assert gerenciador.proximo_estado(conv) is EstadoConversa.EDITAR_NOVO_NOME
        conv.estado = EstadoConversa.EDITAR_NOVO_NOME
        assert gerenciador.proximo_estado(conv) is EstadoConversa.PREVIEW

    def test_editar_apenas_links(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.EDITAR)
        conv.estado = EstadoConversa.EDITAR_ESCOLHA
        conv.campo_editar = CAMPO_LINKS
        assert gerenciador.proximo_estado(conv) is EstadoConversa.EDITAR_LINKS
        conv.estado = EstadoConversa.EDITAR_LINKS
        assert gerenciador.proximo_estado(conv) is EstadoConversa.PREVIEW

    def test_editar_ambos(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.EDITAR)
        conv.estado = EstadoConversa.EDITAR_ESCOLHA
        conv.campo_editar = CAMPO_AMBOS
        assert gerenciador.proximo_estado(conv) is EstadoConversa.EDITAR_NOVO_NOME
        conv.estado = EstadoConversa.EDITAR_NOVO_NOME
        assert gerenciador.proximo_estado(conv) is EstadoConversa.EDITAR_LINKS
        conv.estado = EstadoConversa.EDITAR_LINKS
        assert gerenciador.proximo_estado(conv) is EstadoConversa.PREVIEW

    def test_estado_fora_da_ordem(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        conv.estado = EstadoConversa.BUSCAR_NOME
        assert gerenciador.proximo_estado(conv) is None

    def test_aprovacao_termina_fluxo(self, gerenciador):
        conv = gerenciador.iniciar(1, Acao.NOVA)
        conv.estado = EstadoConversa.APROVACAO
        assert gerenciador.proximo_estado(conv) is None
