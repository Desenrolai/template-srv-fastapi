"""Fiação dos gatilhos do CI.

Este arquivo não testa o CI — testa a FIAÇÃO dos gatilhos dele.

O defeito que fixa: com `push` em toda branch e `pull_request` declarados
juntos, cada commit de uma branch com PR aberto dispara DOIS runs completos do
mesmo SHA. Medido em repo gerado a partir de um destes templates: o mesmo SHA
com um run `success` e outro `failure`, criados com 4s de diferença. É o que faz
alguém concluir "flaky" e ignorar o vermelho.

O `concurrency` do workflow NÃO protege, e é aí que a leitura engana: a chave é
`github.ref`, que vale `refs/heads/<branch>` no push e `refs/pull/<n>/merge` no
pull_request. Grupos diferentes, zero cancelamento. Quem confere apenas que
existe um bloco `concurrency` conclui, errado, que o caso está resolvido.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
WORKFLOW_RAW = WORKFLOW_PATH.read_text(encoding="utf-8")


def strip_yaml_comments(yaml: str) -> str:
    """Remove as linhas de comentário do YAML.

    Obrigatório aqui: o comentário do próprio workflow documenta o defeito e cita
    o gatilho antigo textualmente. Sem esta limpeza, a prosa que explica a
    correção seria lida como a volta do defeito — comentário virando achado.
    """
    return "\n".join(
        linha for linha in yaml.split("\n") if not linha.lstrip().startswith("#")
    )


WORKFLOW = strip_yaml_comments(WORKFLOW_RAW)

_INICIO = re.search(r"^on:", WORKFLOW, re.M)
_FIM = re.search(r"^concurrency:", WORKFLOW, re.M)
GATILHOS = (
    WORKFLOW[_INICIO.start() : _FIM.start()]
    if _INICIO is not None and _FIM is not None and _FIM.start() > _INICIO.start()
    else ""
)

PUSH_TODA_BRANCH = re.compile(r"push:\s*\n\s*branches:\s*\[['\"]\*\*['\"]\]")


def test_bloco_de_gatilhos_foi_recortado() -> None:
    """Sem esta âncora, um recorte falho deixaria os testes abaixo verdes no vazio."""
    assert _INICIO is not None
    assert _FIM is not None
    assert "push:" in GATILHOS


def test_push_roda_so_na_branch_default() -> None:
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", GATILHOS)


def test_pull_request_cobre_toda_branch_inclusive_fork() -> None:
    assert re.search(r"pull_request:\s*\n\s*branches:\s*\[['\"]\*\*['\"]\]", GATILHOS)


def test_push_em_toda_branch_nao_volta() -> None:
    """Duplicaria o run do mesmo SHA — o defeito que este arquivo existe para barrar."""
    assert not PUSH_TODA_BRANCH.search(GATILHOS)


def test_o_ci_executa_a_suite_que_contem_este_teste() -> None:
    """Um teste que o CI não executa é a classe de defeito que este arquivo barra."""
    assert "uv run pytest" in WORKFLOW


def test_remocao_de_comentario_nao_come_conteudo() -> None:
    limpo = strip_yaml_comments("# nota\n  # indentado\nrun: uv sync\n")
    assert limpo == "run: uv sync\n"
    assert "a # b" in strip_yaml_comments('run: echo "a # b"\n')
