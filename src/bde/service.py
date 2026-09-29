"""
Servico de calculo do BDE.

A regra vive em src/bde/schemas.py — este modulo so a executa.

Cadeia de calculo:

  variacao_i       resultado - meta, por etapa (B21/B29/B37)
  H47              media ponderada das variacoes pelas matriculas, ROUND 4
  H45              conversao da media em percentual IDEPE (tabela _TABELA)
  B40              cota resultado = min(percentual_idepe, 1)
  B41              cota alem do resultado = percentual_idepe - B40
  B42 / B43        +100% por quesito de equidade atingido
  C45              cota do BDE = min(percentual_idepe + B42 + B43, 2.5)
  B44              +50% se a escola atingiu 80% de participacao
  total            min(C45 + B44, 3.0)

Toda parcela e multipla de 25%: a tabela de conversao so devolve degraus de
0,25, os quesitos valem 1,0 e a participacao 0,5. O percentual final, portanto,
nunca e um valor quebrado.
"""

from __future__ import annotations

import bisect
from typing import Final

from src.bde.schemas import (
    DetalheEtapa,
    EtapaIDEPE,
    RequisicaoBDE,
    RespostaBDE,
)


# ============================================================================
# Tabela de conversao: diferenca -> percentual (H45)
# ============================================================================

_TABELA: Final[list[tuple[float, float]]] = [
    (-0.3, 0.25),
    (-0.2, 0.50),
    (-0.1, 0.75),
    ( 0.0, 1.00),
    ( 0.1, 1.25),
    ( 0.2, 1.50),
    ( 0.3, 1.75),
    ( 0.4, 2.00),
]

_CHAVES: Final[list[float]] = [t[0] for t in _TABELA]


def _converter(diferenca: float) -> float:
    """H45: busca binaria na tabela de conversao."""
    if diferenca < _CHAVES[0]:
        return 0.0
    idx = bisect.bisect_right(_CHAVES, diferenca) - 1
    return _TABELA[idx][1]


# ============================================================================
# Pesos das cotas
# ============================================================================

COTA_POR_QUESITO_EQUIDADE: Final[float] = 1.0
COTA_PARTICIPACAO: Final[float] = 0.5
TETO_COTA_BDE: Final[float] = 2.5
TETO_BDE: Final[float] = 3.0


# ============================================================================
# Nomes das etapas
# ============================================================================

_NOMES: Final[dict[str, str]] = {
    "ai": "Anos Iniciais",
    "af": "Anos Finais",
    "em": "Ensino Médio",
}


# ============================================================================
# Funcao principal
# ============================================================================

def calcular_bde(req: RequisicaoBDE) -> RespostaBDE:
    """Calcula o BDE a partir das respostas acumuladas do wizard."""

    # 1. Coletar etapas
    entrada: list[tuple[str, EtapaIDEPE]] = []
    if req.etapa_ai is not None:
        entrada.append(("ai", req.etapa_ai))
    if req.etapa_af is not None:
        entrada.append(("af", req.etapa_af))
    if req.etapa_em is not None:
        entrada.append(("em", req.etapa_em))

    # 2. Variacao por etapa (B21/B29/B37)
    detalhes: list[DetalheEtapa] = []
    for chave, etapa in entrada:
        variacao = round(etapa.resultado - etapa.meta, 4)
        detalhes.append(DetalheEtapa(
            nome=_NOMES[chave],
            matriculas=etapa.matriculas,
            meta=etapa.meta,
            resultado=etapa.resultado,
            variacao=variacao,
            percentual_atingimento=_converter(variacao),
        ))

    # 3. Media ponderada (H47)
    total_mat = sum(d.matriculas for d in detalhes)
    soma = sum(d.variacao * d.matriculas for d in detalhes)
    media = round(soma / total_mat, 4)

    # 4. Percentual IDEPE (H45)
    percentual_idepe = _converter(media)

    # 5. B40 / B41
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem = percentual_idepe - cota_resultado

    # 6. B42 / B43 / B44
    bonus_eq = COTA_POR_QUESITO_EQUIDADE if req.reduziu_desigualdade else 0.0
    bonus_el = COTA_POR_QUESITO_EQUIDADE if req.terco_menor_elementares else 0.0
    bonus_part = COTA_PARTICIPACAO if req.participacao_maior_80 else 0.0

    # 7. C45 — a participacao fica de fora e e somada depois
    cota_bde = min(percentual_idepe + bonus_eq + bonus_el, TETO_COTA_BDE)

    # 8. Total, no teto de 300%
    percentual_final = min(cota_bde + bonus_part, TETO_BDE)

    return RespostaBDE(
        percentual_bde=percentual_final,
        percentual_formatado=f"{percentual_final * 100:.0f}%",
        media_ponderada_variacao=media,
        percentual_idepe=percentual_idepe,
        bonus_equidade=bonus_eq,
        bonus_elementares=bonus_el,
        bonus_participacao=bonus_part,
        cota_resultado=cota_resultado,
        cota_alem_resultado=cota_alem,
        cota_bde_calculada=cota_bde,
        apto_a_receber=percentual_final > 0.0,
        etapas=detalhes,
    )
