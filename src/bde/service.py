"""
Servico de calculo do BDE — formula exata da celula C45 da planilha.

Cadeia de calculo (ordem da planilha):

  B21/B29/B37  diferenca por etapa = resultado - meta
  H47          media ponderada pelas matriculas, ROUND(..., 4)
  H45          conversao da media em percentual (tabela)
  B40          cota resultado = min(H45, 1)
  B41          cota alem do resultado = H45 - B40
  B42          cota equidade = 1 se D12="SIM", senao 0
  B43          cota elementares = 1 se D13="SIM", senao 0
  B44          cota participacao = 0.5 se >= 80%, senao 0
  C45          cota do BDE (formula composta) + B44

Formula C45 (EXATA da planilha):
  =SE(E(B40=1;B41=1;B42=1;B43=1); 2,5;
    SE(E(B40<=1;OU(B42=1;B43=1)); 1+B40;
      SE(E((B40+B41)>1;OU(B42=1;B43=1)); 2;
        B40
      )
    )
  ) + B44
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
# Formula C45 — EXATA da planilha
# ============================================================================

def _calcular_c45(
    percentual_idepe: float,
    tem_equidade: bool,
    tem_elementares: bool,
) -> float:
    """
    Formula C45 da planilha, sem B44.

    B40 = min(percentual_idepe, 1.0)
    B41 = max(percentual_idepe - B40, 0.0)
    B42 = 1 se equidade, senao 0
    B43 = 1 se elementares, senao 0

    C45 =
      SE( E(B40=1; B41=1; B42=1; B43=1); 2.5;
        SE( E(B40<=1; OU(B42=1; B43=1)); 1+B40;
          SE( E((B40+B41)>1; OU(B42=1; B43=1)); 2;
            B40
          )
        )
      )
    """
    b40 = min(percentual_idepe, 1.0)
    b41 = max(percentual_idepe - b40, 0.0)
    b42 = 1.0 if tem_equidade else 0.0
    b43 = 1.0 if tem_elementares else 0.0

    # Condicao 1: todos igual a 1
    if b40 == 1.0 and b41 == 1.0 and b42 == 1.0 and b43 == 1.0:
        return 2.5

    # Condicao 2: B40<=1 e (equidade ou elementares)
    if b40 <= 1.0 and (b42 == 1.0 or b43 == 1.0):
        return 1.0 + b40

    # Condicao 3: (B40+B41)>1 e (equidade ou elementares)
    if (b40 + b41) > 1.0 and (b42 == 1.0 or b43 == 1.0):
        return 2.0

    # Default
    return b40


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
    """Calcula o BDE com a formula exata da planilha."""

    # 1. Coletar etapas
    entrada: list[tuple[str, EtapaIDEPE]] = []
    if req.etapa_ai is not None:
        entrada.append(("ai", req.etapa_ai))
    if req.etapa_af is not None:
        entrada.append(("af", req.etapa_af))
    if req.etapa_em is not None:
        entrada.append(("em", req.etapa_em))

    # 2. Diferenca por etapa
    detalhes: list[DetalheEtapa] = []
    for chave, etapa in entrada:
        variacao = round(etapa.resultado - etapa.meta, 4)
        pct = _converter(variacao)
        detalhes.append(DetalheEtapa(
            nome=_NOMES[chave],
            matriculas=etapa.matriculas,
            meta=etapa.meta,
            resultado=etapa.resultado,
            variacao=variacao,
            percentual_atingimento=pct,
        ))

    # 3. Media ponderada (H47)
    total_mat = sum(d.matriculas for d in detalhes)
    soma = sum(d.variacao * d.matriculas for d in detalhes)
    media = round(soma / total_mat, 4) if total_mat else 0.0

    # 4. Percentual IDEPE (H45)
    percentual_idepe = _converter(media)

    # 5. B40 / B41
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem = max(percentual_idepe - cota_resultado, 0.0)

    # 6. B42 / B43 / B44
    cota_eq = 1.0 if req.reduziu_desigualdade else 0.0
    cota_el = 1.0 if req.terco_menor_elementares else 0.0
    cota_part = 0.5 if req.participacao_maior_80 else 0.0

    # 7. C45 (formula exata)
    cota_bde = _calcular_c45(percentual_idepe, req.reduziu_desigualdade, req.terco_menor_elementares)

    # 8. Total = C45 + B44
    percentual_final = round(cota_bde + cota_part, 4)
    apto = percentual_final > 0.0

    return RespostaBDE(
        percentual_bde=percentual_final,
        percentual_formatado=f"{percentual_final * 100:.0f}%",
        apto_a_receber=apto,
        media_ponderada_variacao=media,
        percentual_idepe=percentual_idepe,
        cota_resultado=cota_resultado,
        cota_alem_resultado=cota_alem,
        cota_equidade=cota_eq,
        cota_elementares=cota_el,
        cota_participacao=cota_part,
        cota_bde_calculada=cota_bde,
        bonus_equidade=cota_eq,
        bonus_elementares=cota_el,
        bonus_participacao=cota_part,
        etapas=detalhes,
    )
