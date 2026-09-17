"""
Serviço de cálculo do Bônus de Desempenho Educacional (BDE).

Nomenclatura:
  variação      = Resultado − Meta  (negativa = abaixo da meta, positiva = acima)
  percentual    = conversão da variação via tabela (0% a 200%)
  cota          = parcela do BDE atribuída a cada componente
  bônus         = valor extra (0 ou 1) para equidade/elementares
  participação  = 0.5 (50%) quando ≥ 80% de participação no SAEPE

Tabela de conversão (variação → percentual):
  variação < −0.3  →   0%
  variação ≥ −0.3  →  25%
  variação ≥ −0.2  →  50%
  variação ≥ −0.1  →  75%
  variação ≥  0.0  → 100%  (atingiu a meta)
  variação ≥ +0.1  → 125%
  variação ≥ +0.2  → 150%
  variação ≥ +0.3  → 175%
  variação ≥ +0.4  → 200%

Fórmula do BDE (C45 da planilha, validada com PDF pág. 47-57):
  cota_bde = min(percentual_idepe + bonus_equidade + bonus_elementares, 2.5)
  total    = min(cota_bde + bonus_participacao, 3.0)

Teto: 300% (3.0).
"""

from __future__ import annotations

from src.bde.schemas import (
    DetalheEtapa,
    RequisicaoBDE,
    RespostaBDE,
    EtapaIDEPE,
)


# ---------------------------------------------------------------------------
# Tabela de conversão: variação → percentual IDEPE
# ---------------------------------------------------------------------------

# Cada tupla é (limiar inferior da faixa, percentual correspondente).
# A primeira faixa (variação < −0.3) retorna 0% e é tratada separadamente.
_TABELA_VARIAÇÃO_PERCENTUAL: list[tuple[float, float]] = [
    # (limiar_da_faixa, percentual_correspondente)
    # A faixa é: limiar ≤ variação < próximo_limiar
    # A primeira faixa (variação < −0.3) retorna 0% e é tratada separadamente.
    #
    # Referência: Linhas 42-43 da planilha + H45 (conversão)
    (-0.3, 0.25),   # −0.3 ≤ var < −0.2  → 25%
    (-0.2, 0.50),   # −0.2 ≤ var < −0.1  → 50%
    (-0.1, 0.75),   # −0.1 ≤ var <  0.0  → 75%
    ( 0.0, 1.00),   #  0.0 ≤ var < +0.1  → 100% (meta atingida)
    ( 0.1, 1.25),   # +0.1 ≤ var < +0.2  → 125%
    ( 0.2, 1.50),   # +0.2 ≤ var < +0.3  → 150%
    ( 0.3, 1.75),   # +0.3 ≤ var < +0.4  → 175%
    ( 0.4, 2.00),   # +0.4 ≤ var          → 200%
]

# Constantes dos bônus
_BONUS_EQUIDADE = 1.0
_BONUS_ELEMENTARES = 1.0
_BONUS_PARTICIPACAO = 0.5

# Limites
_TETO_COTA_BDE = 2.5
_TETO_FINAL = 3.0


def _converter_variacao_em_percentual(variacao: float) -> float:
    """
    Aplica a tabela de conversão (célula H45 da planilha).

    Mapeia a variação (Resultado − Meta) para o percentual de atingimento.
    Escala: 0.0 (0%) a 2.0 (200%).

    Lógica (cada faixa é inclusiva no limite inferior):
      variação < −0.3  → 0.0  (0%)
      variação ≥ −0.3  → 0.25 (25%)
      variação ≥ −0.2  → 0.50 (50%)
      variação ≥ −0.1  → 0.75 (75%)
      variação ≥  0.0  → 1.00 (100%) — meta atingida
      variação ≥ +0.1  → 1.25 (125%)
      variação ≥ +0.2  → 1.50 (150%)
      variação ≥ +0.3  → 1.75 (175%)
      variação ≥ +0.4  → 2.00 (200%)
    """
    if variacao < -0.3:
        return 0.0
    if variacao < -0.2:
        return 0.25
    if variacao < -0.1:
        return 0.50
    if variacao < 0.0:
        return 0.75
    if variacao < 0.1:
        return 1.00
    if variacao < 0.2:
        return 1.25
    if variacao < 0.3:
        return 1.50
    if variacao < 0.4:
        return 1.75
    return 2.00


# ---------------------------------------------------------------------------
# Nomes das etapas (para exibição na resposta)
# ---------------------------------------------------------------------------

_NOMES_ETAPAS = {
    "ai": "Anos Iniciais",
    "af": "Anos Finais",
    "em": "Ensino Médio",
}


# ---------------------------------------------------------------------------
# Função principal de cálculo
# ---------------------------------------------------------------------------

def calcular_bde(requisicao: RequisicaoBDE) -> RespostaBDE:
    """
    Calcula o Bônus de Desempenho Educacional.

    Fluxo (espelhando a planilha célula por célula):

    1. Para cada etapa avaliada:
       - Calcula a variação = resultado − meta (B21/B29/B37)
       - Converte a variação em percentual (tabela H45)

    2. Calcula a média ponderada das variações (H47 / J9):
       media = Σ(variação × matrículas) / Σ(matrículas)

    3. Converte a média em percentual IDEPE (H45)

    4. Aplica bônus independentes:
       - Equidade:     0 ou 1.0 (B42)
       - Elementares:  0 ou 1.0 (B43)
       - Participação: 0 ou 0.5 (B44)

    5. Calcula a cota do BDE (C45):
       cota = min(IDEPE + equidade + elementares, 2.5)
       total = min(cota + participação, 3.0)
    """
    # -----------------------------------------------------------------------
    # Passo 1: coletar etapas e calcular variação por etapa
    # -----------------------------------------------------------------------
    etapas_entrada: list[tuple[str, EtapaIDEPE]] = []
    if requisicao.etapa_ai is not None:
        etapas_entrada.append(("ai", requisicao.etapa_ai))
    if requisicao.etapa_af is not None:
        etapas_entrada.append(("af", requisicao.etapa_af))
    if requisicao.etapa_em is not None:
        etapas_entrada.append(("em", requisicao.etapa_em))

    detalhes_etapas: list[DetalheEtapa] = []
    for chave, etapa in etapas_entrada:
        variacao = round(etapa.resultado - etapa.meta, 4)
        percentual = _converter_variacao_em_percentual(variacao)
        detalhes_etapas.append(
            DetalheEtapa(
                nome=_NOMES_ETAPAS[chave],
                matriculas=etapa.matriculas,
                meta=etapa.meta,
                resultado=etapa.resultado,
                variacao=variacao,
                percentual_atingimento=percentual,
            )
        )

    # -----------------------------------------------------------------------
    # Passo 2: média ponderada das variações (H47)
    # -----------------------------------------------------------------------
    total_matriculas = sum(d.matriculas for d in detalhes_etapas)
    soma_produto = sum(d.variacao * d.matriculas for d in detalhes_etapas)
    media_ponderada = round(soma_produto / total_matriculas, 4) if total_matriculas else 0.0

    # -----------------------------------------------------------------------
    # Passo 3: conversão da média em percentual IDEPE (H45)
    # -----------------------------------------------------------------------
    percentual_idepe = _converter_variacao_em_percentual(media_ponderada)

    # -----------------------------------------------------------------------
    # Passo 4: bônus independentes
    # -----------------------------------------------------------------------
    bonus_eq = _BONUS_EQUIDADE if requisicao.reduziu_desigualdade else 0.0
    bonus_el = _BONUS_ELEMENTARES if requisicao.terco_menor_elementares else 0.0
    bonus_part = _BONUS_PARTICIPACAO if requisicao.participacao_maior_80 else 0.0

    # -----------------------------------------------------------------------
    # Passo 5: cota resultado (B40) e cota além do resultado (B41)
    # -----------------------------------------------------------------------
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem_resultado = max(percentual_idepe - cota_resultado, 0.0)

    # -----------------------------------------------------------------------
    # Passo 6: cota do BDE (C45)
    # -----------------------------------------------------------------------
    soma_bonificada = percentual_idepe + bonus_eq + bonus_el
    cota_bde_calculada = round(min(soma_bonificada, _TETO_COTA_BDE), 4)

    # -----------------------------------------------------------------------
    # Passo 7: percentual final (C45 + B44), teto 300%
    # -----------------------------------------------------------------------
    percentual_final = round(min(cota_bde_calculada + bonus_part, _TETO_FINAL), 4)
    apto = percentual_final > 0.0

    return RespostaBDE(
        percentual_bde=percentual_final,
        percentual_formatado=f"{percentual_final * 100:.0f}%",
        media_ponderada_variacao=media_ponderada,
        percentual_idepe=percentual_idepe,
        bonus_equidade=bonus_eq,
        bonus_elementares=bonus_el,
        bonus_participacao=bonus_part,
        cota_resultado=cota_resultado,
        cota_alem_resultado=cota_alem_resultado,
        cota_bde_calculada=cota_bde_calculada,
        apto_a_receber=apto,
        etapas=detalhes_etapas,
    )
