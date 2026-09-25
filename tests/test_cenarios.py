"""
Tabela de conferencia da regra do BDE 2027.

Cada cenario aqui foi descrito pelo gestor da regra, nao derivado do codigo.
Se um deles quebrar, ou a regra mudou e este arquivo precisa mudar junto, ou o
motor saiu do combinado — nunca "o teste esta errado".

    python3 tests/test_cenarios.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.bde.schemas import EtapaIDEPE, RequisicaoBDE  # noqa: E402
from src.bde.service import calcular_bde  # noqa: E402


def etapa(matriculas: int, participou: bool, meta=None, resultado=None) -> EtapaIDEPE:
    return EtapaIDEPE(
        matriculas=matriculas,
        participacao_maior_80=participou,
        meta=meta,
        resultado=resultado,
    )


# (id, descricao, requisicao, idepe esperado, bde esperado)
CENARIOS = [
    (
        "A",
        "1 etapa, sem 80%, sem equidade — pior caso possivel",
        RequisicaoBDE(
            etapa_ai=etapa(300, False),
            reduziu_desigualdade=False,
            terco_menor_elementares=False,
        ),
        0.0,
        0.0,
    ),
    (
        "B",
        "1 etapa, sem 80%, os dois quesitos — teto do caminho zerado",
        RequisicaoBDE(
            etapa_ai=etapa(300, False),
            reduziu_desigualdade=True,
            terco_menor_elementares=True,
        ),
        0.0,
        2.0,
    ),
    (
        "C",
        "1 etapa, com 80%, +0,05, 1 quesito — igual ao ciclo anterior",
        RequisicaoBDE(
            etapa_ai=etapa(300, True, meta=4.50, resultado=4.55),
            reduziu_desigualdade=True,
            terco_menor_elementares=False,
        ),
        1.0,
        2.5,
    ),
    (
        "D",
        "1 etapa, com 80%, +0,05, 2 quesitos — a mudanca da equidade",
        RequisicaoBDE(
            etapa_ai=etapa(300, True, meta=4.50, resultado=4.55),
            reduziu_desigualdade=True,
            terco_menor_elementares=True,
        ),
        1.0,
        3.0,
    ),
    (
        "E",
        "AI 300 com 80% (+0,40), EM 100 sem 80%, 1 quesito — diluicao",
        RequisicaoBDE(
            etapa_ai=etapa(300, True, meta=4.50, resultado=4.90),
            etapa_em=etapa(100, False),
            reduziu_desigualdade=True,
            terco_menor_elementares=False,
        ),
        1.5,
        2.5,
    ),
    (
        "F",
        "3 etapas todas com 80% — regressao: IDEPE nao pode mudar",
        RequisicaoBDE(
            etapa_ai=etapa(317, True, meta=4.5, resultado=4.7),
            etapa_af=etapa(83, True, meta=5.1, resultado=5.0),
            etapa_em=etapa(1234, True, meta=3.8, resultado=4.05),
            reduziu_desigualdade=True,
            terco_menor_elementares=False,
        ),
        1.5,
        2.5,
    ),
]

# Valores do ciclo anterior para o caso F, colhidos antes da mudanca da regra.
# A diluicao nao pode encostar em escola com todas as etapas aprovadas.
REGRESSAO_F = {"media": 0.2225, "idepe": 1.5}


def main() -> int:
    falhas = []

    print(f"{'#':<3} {'IDEPE':>8} {'BDE':>8}  cenario")
    print("-" * 72)

    for ident, descricao, requisicao, idepe_esperado, bde_esperado in CENARIOS:
        r = calcular_bde(requisicao)
        ok_idepe = r.percentual_idepe == idepe_esperado
        ok_bde = r.percentual_bde == bde_esperado

        marca = " " if (ok_idepe and ok_bde) else "X"
        print(
            f"{ident:<3} {r.percentual_idepe * 100:>7.0f}% "
            f"{r.percentual_bde * 100:>7.0f}% {marca} {descricao}"
        )

        if not ok_idepe:
            falhas.append(
                f"{ident}: IDEPE deu {r.percentual_idepe}, esperado {idepe_esperado}"
            )
        if not ok_bde:
            falhas.append(
                f"{ident}: BDE deu {r.percentual_bde}, esperado {bde_esperado}"
            )

        if ident == "F":
            if r.media_ponderada_variacao != REGRESSAO_F["media"]:
                falhas.append(
                    f"F: media ponderada deu {r.media_ponderada_variacao}, "
                    f"o ciclo anterior dava {REGRESSAO_F['media']}"
                )
            if r.percentual_idepe != REGRESSAO_F["idepe"]:
                falhas.append(
                    f"F: IDEPE deu {r.percentual_idepe}, "
                    f"o ciclo anterior dava {REGRESSAO_F['idepe']}"
                )

    print("-" * 72)
    for f in falhas:
        print("FALHA:", f)

    if falhas:
        print(f"\nFALHOU — {len(falhas)} verificacoes.")
        return 1

    print(f"\nOK — {len(CENARIOS)} cenarios conferem com a regra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
