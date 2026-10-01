"""
Servico de calculo do BDE — BDE 2027.

A participacao de 80% no SAEPE e por etapa. Etapa que nao atingiu entra na
media com IDEPE zero: a diferenca dela e 0 - meta, pesando pelas matriculas.
Nenhuma etapa com matricula fica de fora da conta.

Cadeia de calculo:

  idepe_i          resultado com 80% de participacao, 0 sem
  variacao_i       idepe_i - meta, em TODAS as etapas
  H47              media ponderada das variacoes pelas matriculas
  H45              conversao da media em percentual (tabela _TABELA)
  equidade         +100% se reduziu desigualdade OU esta no terco de
                   elementares — os dois quesitos nao somam entre si
  B40              cota resultado:
                     sem quesito de equidade      percentual_idepe inteiro
                     com quesito e IDEPE < 200%   min(percentual_idepe, 1)
                     com quesito e IDEPE = 200%   percentual_idepe inteiro
  B41              cota alem do resultado = percentual_idepe - B40, a parte
                   do resultado trocada pelo quesito de equidade
  participacao     +50% so se TODAS as etapas atingiram 80%
  total            min(B40 + equidade + participacao, 3.0)

O excedente acima de 100% e o quesito de equidade so se acumulam quando a
escola chega a 200% de IDEPE (variacao >= 0,4). Abaixo disso ela fica com o
maior dos dois caminhos, que com quesito e sempre 100% + 100%. Ver
docs/EXTRACAO_PLANILHA.md secao 5.1.

Com todas as etapas acima de 80%, o percentual_idepe e identico ao do ciclo
anterior: o zero so muda a conta de quem tem etapa sem participacao.
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
# Pesos das cotas — mudam entre ciclos
# ============================================================================

COTA_EQUIDADE: Final[float] = 1.0
COTA_PARTICIPACAO: Final[float] = 0.5
TETO_BDE: Final[float] = 3.0

# IDEPE a partir do qual o excedente acima de 100% soma com a equidade. E o
# topo da tabela: variacao media >= 0,4.
IDEPE_ACUMULA_COM_EQUIDADE: Final[float] = 2.0


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

    # 2. Detalhe por etapa. Etapa sem 80% entra com IDEPE zero, e a diferenca
    #    dela e 0 - meta.
    detalhes: list[DetalheEtapa] = []
    for chave, etapa in entrada:
        idepe = etapa.resultado if etapa.participacao_maior_80 else 0.0
        variacao = round(idepe - etapa.meta, 4)
        detalhes.append(DetalheEtapa(
            nome=_NOMES[chave],
            matriculas=etapa.matriculas,
            participou=etapa.participacao_maior_80,
            meta=etapa.meta,
            resultado=idepe,
            variacao=variacao,
            percentual_atingimento=_converter(variacao),
        ))

    # 3. Media ponderada (H47) entre todas as etapas, pesando pelas matriculas
    mat_total = sum(d.matriculas for d in detalhes)
    soma = sum(d.variacao * d.matriculas for d in detalhes)
    media = round(soma / mat_total, 4)

    # 4. Conversao (H45)
    percentual_idepe = _converter(media)

    # 5. Equidade: um quesito basta e os dois valem o mesmo que um. O +100%
    #    vale para toda escola, tenha ou nao atingido 80% de participacao.
    #    Quem atinge os dois aparece com a cota em equidade.
    cota_eq = COTA_EQUIDADE if req.reduziu_desigualdade else 0.0
    cota_el = COTA_EQUIDADE if req.terco_menor_elementares and not req.reduziu_desigualdade else 0.0
    tem_quesito = cota_eq + cota_el > 0.0

    # 6. B40 / B41. Com quesito de equidade e IDEPE abaixo de 200%, a escola
    #    troca o excedente acima de 100% pelo quesito.
    if tem_quesito and percentual_idepe < IDEPE_ACUMULA_COM_EQUIDADE:
        cota_resultado = min(percentual_idepe, 1.0)
    else:
        cota_resultado = percentual_idepe
    cota_alem = round(percentual_idepe - cota_resultado, 4)

    # 7. Participacao: uma etapa sem 80% ja tira os +50%.
    cota_part = COTA_PARTICIPACAO if all(d.participou for d in detalhes) else 0.0

    # 8. Total, no teto de 300%
    cota_bde = cota_resultado + cota_eq + cota_el
    percentual_final = round(min(cota_bde + cota_part, TETO_BDE), 4)
    apto = percentual_final > 0.0

    return RespostaBDE(
        percentual_bde=percentual_final,
        percentual_formatado=f"{percentual_final * 100:.0f}%",
        apto_a_receber=apto,
        media_ponderada_variacao=media,
        percentual_idepe=percentual_idepe,
        cota_resultado=cota_resultado,
        cota_alem_resultado=cota_alem,
        cota_bde_calculada=cota_bde,
        bonus_equidade=cota_eq,
        bonus_elementares=cota_el,
        bonus_participacao=cota_part,
        etapas=detalhes,
    )
