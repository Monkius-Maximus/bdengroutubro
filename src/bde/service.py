"""
Servico de calculo do BDE — BDE 2027.

A participacao de 80% no SAEPE e por etapa e funciona como portao: etapa que
nao atingiu nao tem IDEPE divulgado, entra na conta com atingimento zero e
continua pesando pelas suas matriculas.

Cadeia de calculo:

  variacao_i       resultado - meta, so nas etapas que participaram
  H47              media ponderada das variacoes, SO entre as aprovadas
  H45              conversao da media em percentual (tabela _TABELA)
  diluicao         percentual x (matriculas aprovadas / matriculas totais)
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

A diluicao acontece DEPOIS da conversao, nao antes: uma etapa sem meta e sem
resultado nao tem variacao para entrar no H47. Assim, enquanto todas as etapas
passarem no portao, o percentual_idepe e identico ao do ciclo anterior.
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
# topo da tabela: variacao media >= 0,4 com todas as etapas aprovadas.
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

    # 2. Detalhe por etapa. Etapa sem 80% nao tem IDEPE divulgado: variacao
    #    fica nula, que e diferente de zero (zero e quem empatou com a meta).
    detalhes: list[DetalheEtapa] = []
    for chave, etapa in entrada:
        if etapa.participacao_maior_80:
            variacao = round(etapa.resultado - etapa.meta, 4)
            pct = _converter(variacao)
        else:
            variacao = None
            pct = 0.0
        detalhes.append(DetalheEtapa(
            nome=_NOMES[chave],
            matriculas=etapa.matriculas,
            participou=etapa.participacao_maior_80,
            meta=etapa.meta,
            resultado=etapa.resultado,
            variacao=variacao,
            percentual_atingimento=pct,
        ))

    aprovadas = [d for d in detalhes if d.participou]

    # 3. Media ponderada (H47) — so entre as aprovadas, porque so elas tem
    #    variacao. Com nenhuma aprovada, nao ha IDEPE: a escola concorre
    #    apenas aos quesitos de equidade.
    mat_aprovadas = sum(d.matriculas for d in aprovadas)
    if aprovadas:
        soma = sum(d.variacao * d.matriculas for d in aprovadas)
        media = round(soma / mat_aprovadas, 4)
        pct_aprovadas = _converter(media)
    else:
        media = 0.0
        pct_aprovadas = 0.0

    # 4. Diluicao pelas reprovadas: elas entram com atingimento zero e com o
    #    peso das suas matriculas. Sem reprovada nenhuma, a fracao e 1 e o
    #    percentual e exatamente o do ciclo anterior.
    mat_total = sum(d.matriculas for d in detalhes)
    percentual_idepe = round(pct_aprovadas * (mat_aprovadas / mat_total), 4)

    # 5. Equidade: um quesito basta e os dois valem o mesmo que um. O +100%
    #    vale para toda escola, tenha ou nao passado no portao da participacao.
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
    cota_part = COTA_PARTICIPACAO if len(aprovadas) == len(detalhes) else 0.0

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
