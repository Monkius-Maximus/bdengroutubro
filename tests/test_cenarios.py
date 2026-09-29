"""
Tabela de conferencia da regra do BDE, conforme src/bde/schemas.py:

    cota_bde       = min(percentual_idepe + equidade + elementares, 2.5)
    percentual_bde = min(cota_bde + participacao, 3.0)

Se um cenario quebrar, ou a regra mudou e este arquivo precisa mudar junto, ou
o motor saiu do combinado — nunca "o teste esta errado".

Alem dos cenarios, confere a propriedade que a regra garante: o percentual
final e sempre multiplo de 25%, nunca um valor quebrado.

    python3 tests/test_cenarios.py
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.bde.schemas import EtapaIDEPE, RequisicaoBDE  # noqa: E402
from src.bde.service import calcular_bde  # noqa: E402


def etapa(matriculas: int, meta: float, resultado: float) -> EtapaIDEPE:
    return EtapaIDEPE(matriculas=matriculas, meta=meta, resultado=resultado)


# (id, descricao, requisicao, idepe esperado, bde esperado)
CENARIOS = [
    (
        "A",
        "1 etapa, -0,50, nada mais — pior caso possivel",
        RequisicaoBDE(
            etapa_ai=etapa(300, 4.50, 4.00),
            reduziu_desigualdade=False,
            terco_menor_elementares=False,
            participacao_maior_80=False,
        ),
        0.0,
        0.0,
    ),
    (
        "B",
        "1 etapa, -0,50, 2 quesitos + participacao",
        RequisicaoBDE(
            etapa_ai=etapa(300, 4.50, 4.00),
            reduziu_desigualdade=True,
            terco_menor_elementares=True,
            participacao_maior_80=True,
        ),
        0.0,
        2.5,
    ),
    (
        "C",
        "1 etapa, +0,05, 1 quesito + participacao",
        RequisicaoBDE(
            etapa_ai=etapa(300, 4.50, 4.55),
            reduziu_desigualdade=True,
            terco_menor_elementares=False,
            participacao_maior_80=True,
        ),
        1.0,
        2.5,
    ),
    (
        "D",
        "1 etapa, +0,05, 2 quesitos + participacao — C45 trava em 250%",
        RequisicaoBDE(
            etapa_ai=etapa(300, 4.50, 4.55),
            reduziu_desigualdade=True,
            terco_menor_elementares=True,
            participacao_maior_80=True,
        ),
        1.0,
        3.0,
    ),
    (
        "E",
        "1 etapa, +0,40, sem quesitos nem participacao — IDEPE cheio",
        RequisicaoBDE(
            etapa_ai=etapa(300, 4.50, 4.90),
            reduziu_desigualdade=False,
            terco_menor_elementares=False,
            participacao_maior_80=False,
        ),
        2.0,
        2.0,
    ),
    (
        "F",
        "3 etapas, media 0,2225, 1 quesito + participacao",
        RequisicaoBDE(
            etapa_ai=etapa(317, 4.5, 4.7),
            etapa_af=etapa(83, 5.1, 5.0),
            etapa_em=etapa(1234, 3.8, 4.05),
            reduziu_desigualdade=True,
            terco_menor_elementares=False,
            participacao_maior_80=True,
        ),
        1.5,
        3.0,
    ),
    (
        "G",
        "2 etapas com pesos 2:1, media +0,05 — sem valor quebrado",
        RequisicaoBDE(
            etapa_ai=etapa(200, 4.50, 4.60),
            etapa_af=etapa(100, 5.00, 4.95),
            reduziu_desigualdade=False,
            terco_menor_elementares=False,
            participacao_maior_80=True,
        ),
        1.0,
        1.5,
    ),
]


def conferir_cenarios() -> list[str]:
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

    print("-" * 72)
    return falhas


def conferir_sem_valor_quebrado() -> tuple[int, list[str]]:
    """Varre combinacoes de etapas e respostas: todo BDE e multiplo de 25%."""
    resultados = [x / 100 for x in range(380, 521, 3)]
    pesos = [(1, 1, 1), (317, 83, 1234), (1000, 7, 50), (8, 50000, 333)]
    falhas = []
    total = 0

    for (m_ai, m_af, m_em), r_ai, r_em, (eq, el, part) in product(
        pesos, resultados, [3.7, 4.05, 4.4], product([True, False], repeat=3)
    ):
        r = calcular_bde(
            RequisicaoBDE(
                etapa_ai=etapa(m_ai, 4.5, r_ai),
                etapa_af=etapa(m_af, 5.1, 5.0),
                etapa_em=etapa(m_em, 3.8, r_em),
                reduziu_desigualdade=eq,
                terco_menor_elementares=el,
                participacao_maior_80=part,
            )
        )
        total += 1
        if (r.percentual_bde * 4) % 1 != 0:
            falhas.append(
                f"BDE quebrado: {r.percentual_bde} (AI {m_ai}/{r_ai}, "
                f"AF {m_af}, EM {m_em}/{r_em}, eq={eq}, el={el}, part={part})"
            )
    return total, falhas


def main() -> int:
    falhas = conferir_cenarios()
    total, quebrados = conferir_sem_valor_quebrado()
    falhas += quebrados[:5]

    for f in falhas:
        print("FALHA:", f)

    if falhas:
        print(f"\nFALHOU — {len(falhas)} verificacoes.")
        return 1

    print(f"\nOK — {len(CENARIOS)} cenarios conferem com a regra.")
    print(f"OK — {total} combinacoes, nenhum BDE fora dos degraus de 25%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
