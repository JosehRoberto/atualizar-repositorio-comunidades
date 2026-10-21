"""Serviço Git/GitLab — commit, branch, push e Merge Request (docs/requisitos.md §2.7, §2.12).

Autenticação por Personal Access Token **fora da URL do remote**: a URL autenticada é
montada em runtime apenas para o `push`, nunca persistida em `.git/config`. O token nunca
aparece em mensagens de erro (é mascarado). Toda chamada externa (`subprocess`, `requests`)
é isolável por mock nos testes.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import requests

from bot.config import Config

TEMPO_LIMITE_API = 30


class GitError(Exception):
    """Erro base do serviço Git/GitLab."""


def mascarar(texto: str, token: str) -> str:
    """Remove o token de um texto (logs/erros) antes de expor."""
    if token:
        return texto.replace(token, "***")
    return texto


def url_autenticada(repo_url: str, username: str, token: str) -> str:
    """Monta `https://<username>:<token>@host/caminho` em runtime (sem persistir)."""
    if not token:
        raise GitError("token GitLab ausente")
    partes = urllib.parse.urlsplit(repo_url)
    if partes.scheme not in ("http", "https") or not partes.netloc:
        raise GitError(f"URL de repositório inválida: {repo_url}")
    usuario = urllib.parse.quote(username, safe="")
    senha = urllib.parse.quote(token, safe="")
    return urllib.parse.urlunsplit(
        (partes.scheme, f"{usuario}:{senha}@{partes.netloc}", partes.path, "", "")
    )


def hash_conteudo(texto: str) -> str:
    """Hash SHA-256 do conteúdo (recheck antes de gravar, §2.12)."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def hash_arquivo(caminho: str | Path) -> str:
    """Hash SHA-256 do arquivo em disco."""
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


@dataclass
class GitService:
    """Operações Git/GitLab sobre o clone local do repositório alvo."""

    repo_dir: Path
    repo_url: str
    branch: str = "master"
    username: str = "oauth2"
    token: str = ""
    user_name: str = "ParaLivre"
    user_email: str = "contato@paralivre.org"

    @classmethod
    def from_config(cls) -> "GitService":
        """Cria o serviço a partir da `Config` (`.env`), sem valores hardcoded."""
        return cls(
            repo_dir=Config.README_PATH.parent,
            repo_url=Config.GIT_REPO_URL,
            branch=Config.GIT_BRANCH,
            username=Config.GITLAB_USERNAME,
            token=Config.GITLAB_TOKEN,
            user_name=Config.GIT_USER_NAME,
            user_email=Config.GIT_USER_EMAIL,
        )

    def _env(self) -> dict:
        ambiente = dict(os.environ)
        ambiente["GIT_TERMINAL_PROMPT"] = "0"
        return ambiente

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        """Executa `git` no clone; erros viram `GitError` com o token mascarado."""
        comando = ["git", *args]
        try:
            return subprocess.run(
                comando,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                check=True,
                env=self._env(),
            )
        except subprocess.CalledProcessError as erro:
            detalhe = mascarar(erro.stderr or erro.stdout or "", self.token)
            raise GitError(f"falha ao executar {' '.join(comando)}: {detalhe.strip()}") from erro

    def _relativo(self, caminho: str | Path) -> str:
        caminho = Path(caminho)
        if caminho.is_absolute():
            return str(caminho.relative_to(self.repo_dir))
        return str(caminho)

    def hash_arquivo(self, caminho: str | Path) -> str:
        """Hash SHA-256 do arquivo (absoluto ou relativo ao clone)."""
        alvo = Path(caminho)
        if not alvo.is_absolute():
            alvo = self.repo_dir / alvo
        return hash_arquivo(alvo)

    def branch_atual(self) -> str:
        """Nome da branch atual."""
        return self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def status_limpo(self) -> bool:
        """True se não há alterações pendentes no clone."""
        return not self._git("status", "--porcelain").stdout.strip()

    def alteracoes(self) -> list[str]:
        """Lista as alterações pendentes (`git status --porcelain`), linha a linha."""
        saida = self._git("status", "--porcelain").stdout
        return [linha for linha in saida.splitlines() if linha.strip()]

    # ALTERADO [21/10/2026]: pendência restrita ao README e commits à frente (planejamento
    # guarda-publicacao-pendente, R10/R1). Não altera a semântica de status_limpo/alteracoes.
    def readme_pendente(self, caminho: str | Path | None = None) -> bool:
        """True se o README (alvo) tem alterações não commitadas.

        Restringe o `git status` ao arquivo alvo, para que arquivos alheios
        (untracked/não-README) não indiquem publicação pendente (R10).
        """
        alvo = self._relativo(caminho) if caminho is not None else "README.md"
        saida = self._git("status", "--porcelain", "--", alvo).stdout
        return bool(saida.strip())

    def commits_pendentes(self) -> list[str]:
        """Linhas (`--oneline`) dos commits locais à frente de `origin/<branch>`."""
        saida = self._git("log", "--oneline", f"origin/{self.branch}..HEAD").stdout
        return [linha for linha in saida.splitlines() if linha.strip()]

    def fetch(self) -> None:
        """Busca atualizações do remoto (sem alterar a árvore)."""
        self._git("fetch", "origin")

    def pull_ff_only(self) -> None:
        """Atualiza a branch local somente em fast-forward (§2.12)."""
        self._git("pull", "--ff-only")

    def sincronizar(self) -> None:
        """`fetch` + `pull --ff-only` antes de qualquer edição (§2.12)."""
        self.fetch()
        self.pull_ff_only()

    # ALTERADO [21/10/2026]: sincronização da publicação via rebase (planejamento
    # guarda-publicacao-pendente, R1/R2). A gravação segue com `pull --ff-only`.
    def pull_rebase(self) -> None:
        """`pull --rebase`: reaplica os commits locais sobre o remoto.

        Em conflito, aborta o rebase (preserva os commits locais) e propaga o erro (R2).
        """
        try:
            self._git("pull", "--rebase")
        except GitError:
            try:
                self._git("rebase", "--abort")
            except GitError:
                pass
            raise

    def sincronizar_publicacao(self) -> None:
        """`fetch` + `pull --rebase` antes do push (§2.12)."""
        self.fetch()
        self.pull_rebase()

    def criar_branch(self, nome: str) -> None:
        """Cria e muda para uma nova branch."""
        self._git("checkout", "-b", nome)

    def commit(self, arquivo: str | Path, mensagem: str) -> str:
        """Adiciona o arquivo e cria o commit; devolve o hash do commit."""
        rel = self._relativo(arquivo)
        self._git("add", "--", rel)
        self._git(
            "-c",
            f"user.name={self.user_name}",
            "-c",
            f"user.email={self.user_email}",
            "commit",
            "-m",
            mensagem,
            "--",
            rel,
        )
        return self._git("rev-parse", "HEAD").stdout.strip()

    def push(self, branch: str | None = None) -> None:
        """Envia a branch atual usando a URL autenticada em runtime (não persiste)."""
        destino = branch or self.branch
        self._git(
            "-c",
            "credential.helper=",
            "push",
            url_autenticada(self.repo_url, self.username, self.token),
            f"HEAD:{destino}",
        )

    def _projeto(self) -> str:
        caminho = urllib.parse.urlsplit(self.repo_url).path.lstrip("/")
        if caminho.endswith(".git"):
            caminho = caminho[: -len(".git")]
        return caminho

    def _api_merge_requests(self) -> str:
        base = urllib.parse.urlsplit(self.repo_url)
        return (
            f"{base.scheme}://{base.netloc}/api/v4/projects/"
            f"{urllib.parse.quote(self._projeto(), safe='')}/merge_requests"
        )

    def criar_merge_request(
        self,
        titulo: str,
        source_branch: str,
        target_branch: str | None = None,
        descricao: str = "",
    ) -> dict:
        """Abre um Merge Request no GitLab via API (header `PRIVATE-TOKEN`)."""
        if not self.token:
            raise GitError("token GitLab ausente")
        payload = {
            "source_branch": source_branch,
            "target_branch": target_branch or self.branch,
            "title": titulo,
            "description": descricao,
            "remove_source_branch": True,
        }
        resposta = requests.post(
            self._api_merge_requests(),
            headers={"PRIVATE-TOKEN": self.token},
            json=payload,
            timeout=TEMPO_LIMITE_API,
        )
        if resposta.status_code >= 400:
            raise GitError(f"falha ao criar Merge Request (HTTP {resposta.status_code})")
        return resposta.json()
