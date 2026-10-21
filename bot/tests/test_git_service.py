"""Testes herméticos do serviço Git/GitLab (subprocess e requests mockados)."""

import hashlib
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from bot.services.git_service import (
    GitError,
    GitService,
    hash_arquivo,
    hash_conteudo,
    mascarar,
    url_autenticada,
)

TOKEN = "glpat-ABC123xyz"
REPO_URL = "https://gitlab.com/paralivre/comunidades-de-tecnologia-pa.git"


@pytest.fixture
def service(tmp_path):
    return GitService(
        repo_dir=tmp_path,
        repo_url=REPO_URL,
        branch="master",
        username="oauth2",
        token=TOKEN,
        user_name="ParaLivre",
        user_email="contato@paralivre.org",
    )


def _ok(stdout=""):
    return subprocess.CompletedProcess(args=["git"], returncode=0, stdout=stdout, stderr="")


class TestUrlEAuth:
    def test_url_autenticada_monta_credenciais(self):
        url = url_autenticada(REPO_URL, "oauth2", TOKEN)
        assert url == f"https://oauth2:{TOKEN}@gitlab.com/paralivre/comunidades-de-tecnologia-pa.git"

    def test_url_autenticada_escapa_caracteres(self):
        url = url_autenticada("https://gitlab.com/g/p.git", "user@mail.com", "a/b+c")
        assert "user%40mail.com" in url
        assert "a%2Fb%2Bc" in url

    def test_url_autenticada_sem_token(self):
        with pytest.raises(GitError):
            url_autenticada(REPO_URL, "oauth2", "")

    def test_url_autenticada_url_invalida(self):
        with pytest.raises(GitError):
            url_autenticada("git@gitlab.com:g/p.git", "oauth2", TOKEN)

    def test_mascarar_remove_token(self):
        assert mascarar(f"erro com {TOKEN} aqui", TOKEN) == "erro com *** aqui"

    def test_mascarar_sem_token(self):
        assert mascarar("erro normal", "") == "erro normal"


class TestHashes:
    def test_hash_conteudo(self):
        assert hash_conteudo("abc") == hashlib.sha256(b"abc").hexdigest()

    def test_hash_arquivo(self, tmp_path):
        arquivo = tmp_path / "README.md"
        arquivo.write_text("abc", encoding="utf-8")
        assert hash_arquivo(arquivo) == hashlib.sha256(b"abc").hexdigest()

    def test_hash_metodo_aceita_relativo(self, service, tmp_path):
        (tmp_path / "README.md").write_text("abc", encoding="utf-8")
        assert service.hash_arquivo("README.md") == hashlib.sha256(b"abc").hexdigest()


class TestExecucaoGit:
    def test_usa_cwd_e_env_sem_prompt(self, service, tmp_path):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("main\n")) as run:
            service.branch_atual()
        _, kwargs = run.call_args
        assert kwargs["cwd"] == str(tmp_path)
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert kwargs["check"] is True

    def test_falha_vira_git_error_com_token_mascarado(self, service):
        erro = subprocess.CalledProcessError(
            returncode=1, cmd=["git"], stderr=f"fatal: auth {TOKEN} falhou"
        )
        with mock.patch("bot.services.git_service.subprocess.run", side_effect=erro):
            with pytest.raises(GitError) as exc:
                service.fetch()
        assert TOKEN not in str(exc.value)
        assert "***" in str(exc.value)

    def test_branch_atual(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("main\n")):
            assert service.branch_atual() == "main"

    def test_status_limpo(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("")):
            assert service.status_limpo() is True
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok(" M README.md\n")):
            assert service.status_limpo() is False

    def test_alteracoes(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok(" M README.md\n?? x\n")):
            assert service.alteracoes() == [" M README.md", "?? x"]

    def test_alteracoes_vazio(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("")):
            assert service.alteracoes() == []

    def test_sincronizar_fetch_e_pull(self, service):
        with mock.patch.object(service, "fetch") as fetch, mock.patch.object(service, "pull_ff_only") as pull:
            service.sincronizar()
        fetch.assert_called_once()
        pull.assert_called_once()

    def test_pull_ff_only_usa_flag(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok()) as run:
            service.pull_ff_only()
        args = run.call_args[0][0]
        assert args == ["git", "pull", "--ff-only"]

    def test_criar_branch(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok()) as run:
            service.criar_branch("feat/x")
        assert run.call_args[0][0] == ["git", "checkout", "-b", "feat/x"]


class TestCommit:
    def test_commit_retorna_hash(self, service, tmp_path):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("deadbeef\n")) as run:
            resultado = service.commit("README.md", "docs: msg")
        assert resultado == "deadbeef"
        comandos = [c[0][0] for c in run.call_args_list]
        assert comandos[0][:2] == ["git", "add"]
        assert comandos[1][:2] == ["git", "commit"] or "commit" in comandos[1]

    def test_commit_define_autor(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok("h\n")) as run:
            service.commit("README.md", "msg")
        args_commit = run.call_args_list[1][0][0]
        assert "user.name=ParaLivre" in args_commit
        assert "user.email=contato@paralivre.org" in args_commit


class TestPush:
    def test_push_usa_url_autenticada_e_nao_persiste(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok()) as run:
            service.push()
        args = run.call_args[0][0]
        assert "credential.helper=" in args
        assert "push" in args
        assert "HEAD:master" in args
        # A URL autenticada é passada como argumento, não gravada em config.
        assert any(TOKEN in a for a in args)
        assert not any("config" in a for a in args)

    def test_push_branch_customizada(self, service):
        with mock.patch("bot.services.git_service.subprocess.run", return_value=_ok()) as run:
            service.push("minha-branch")
        assert "HEAD:minha-branch" in run.call_args[0][0]


class TestMergeRequest:
    def _projeto_url(self):
        return "https://gitlab.com/api/v4/projects/paralivre%2Fcomunidades-de-tecnologia-pa/merge_requests"

    def test_cria_mr_com_header_private_token(self, service):
        resposta = mock.Mock(status_code=201)
        resposta.json.return_value = {"iid": 7, "web_url": "https://gitlab.com/mr/7"}
        with mock.patch("bot.services.git_service.requests.post", return_value=resposta) as post:
            dados = service.criar_merge_request("Título", "feat/x", "master", "Desc")
        assert dados["iid"] == 7
        url = post.call_args[0][0]
        assert url == self._projeto_url()
        _, kwargs = post.call_args
        assert kwargs["headers"]["PRIVATE-TOKEN"] == TOKEN
        assert kwargs["json"]["source_branch"] == "feat/x"
        assert kwargs["json"]["target_branch"] == "master"
        assert kwargs["json"]["remove_source_branch"] is True

    def test_erro_http_vira_git_error(self, service):
        resposta = mock.Mock(status_code=401)
        with mock.patch("bot.services.git_service.requests.post", return_value=resposta):
            with pytest.raises(GitError):
                service.criar_merge_request("T", "feat/x")

    def test_sem_token(self, tmp_path):
        service = GitService(repo_dir=tmp_path, repo_url=REPO_URL, token="")
        with pytest.raises(GitError):
            service.criar_merge_request("T", "feat/x")


class TestFromConfig:
    def test_from_config_usa_env(self, monkeypatch, tmp_path):
        from bot.config import Config

        monkeypatch.setattr(Config, "GIT_REPO_URL", REPO_URL)
        monkeypatch.setattr(Config, "GIT_BRANCH", "master")
        monkeypatch.setattr(Config, "GITLAB_USERNAME", "oauth2")
        monkeypatch.setattr(Config, "GITLAB_TOKEN", TOKEN)
        monkeypatch.setattr(Config, "GIT_USER_NAME", "ParaLivre")
        monkeypatch.setattr(Config, "GIT_USER_EMAIL", "contato@paralivre.org")
        monkeypatch.setattr(Config, "README_PATH", tmp_path / "README.md")

        service = GitService.from_config()
        assert service.repo_dir == tmp_path
        assert service.token == TOKEN
        assert service.branch == "master"
