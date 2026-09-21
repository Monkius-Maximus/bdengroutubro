"""
Servico de calculo do BDE — ciclo 2026.

A participacao de 80% no SAEPE e por etapa e funciona como portao: etapa que
nao atingiu nao tem IDEPE divulgado, entra na conta com atingimento zero e
continua pesando pelas suas matriculas.

Cadeia de calculo:

  variacao_i       resultado - meta, so nas etapas que participaram
  H47              media ponderada das variacoes, SO entre as aprovadas
  H45              conversao da media em percentual (tabela _TABELA)
  diluicao         percentual x (matriculas aprovadas / matriculas totais)
  B40              cota resultado = min(percentual_idepe, 1)
  B41              cota alem do resultado = percentual_idepe - B40 (informativa)
  equidade         +100% por quesito atingido, os dois somam +200%
  participacao     +50% se QUALQUER etapa atingiu 80%
  total            min(B40 + equidade + elementares + participacao, 3.0)

A formula C45 da planilha nao vale mais. Ela tratava os dois quesitos de
equidade com OU — ter os dois valia o mesmo que ter um so, salvo num unico
ramo. A regra do ciclo 2026 soma por quesito, entao o simulador diverge da
planilha de proposito a partir daqui. Ver docs/EXTRACAO_PLANILHA.md secao 5.1.

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

COTA_POR_QUESITO_EQUIDADE: Final[float] = 1.0
COTA_PARTICIPACAO: Final[float] = 0.5
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

    # 5. B40 / B41. A parcela acima de 100% continua fora da soma; fica
    #    exposta para o gestor entender por que superar muito nao mudou nada.
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem = max(percentual_idepe - cota_resultado, 0.0)

    # 6. Equidade soma por quesito atingido, e vale para toda escola, tenha ou
    #    nao passado no portao da participacao.
    cota_eq = COTA_POR_QUESITO_EQUIDADE if req.reduziu_desigualdade else 0.0
    cota_el = COTA_POR_QUESITO_EQUIDADE if req.terco_menor_elementares else 0.0
    cota_part = COTA_PARTICIPACAO if aprovadas else 0.0

    # 7. Total, no teto de 300%
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
        cota_equidade=cota_eq,
        cota_elementares=cota_el,
        cota_participacao=cota_part,
        cota_bde_calculada=cota_bde,
        bonus_equidade=cota_eq,
        bonus_elementares=cota_el,
        bonus_participacao=cota_part,
        etapas=detalhes,
    )
