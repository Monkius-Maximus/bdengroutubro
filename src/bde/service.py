"""
Serviço de cálculo do BDE.

>>> ATENÇÃO — a fórmula abaixo ainda NÃO foi validada contra a planilha. <<<

Esta versão implementa os bônus de equidade e elementares como **cumulativos**,
conforme a regra de negócio declarada. A fórmula C45 da planilha usa `OR` e
diverge em 20 das 28 combinações possíveis. A decisão está aberta em
`docs/CAMINHOS_RUINS.md` (B1 e B2) e detalhada em `docs/EXTRACAO_PLANILHA.md`
§5.1. Este módulo foi apenas realinhado aos nomes dos schemas; a escolha da
fórmula será refeita na etapa da lógica matemática.

Vocabulário:
  diferença   = Resultado − Meta
  percentual  = diferença convertida pela tabela (0% a 200%)
  cota        = parcela do BDE atribuída a cada componente
"""

from __future__ import annotations

from src.bde.schemas import (
    DetalheEtapa,
    Etapa,
    EtapaIDEPE,
    RequisicaoBDE,
    RespostaBDE,
)

# Pesos das cotas — por ciclo. Ver CAMINHOS_RUINS.md B4: no BDE 2025 a cota de
# participação foi de 25%, não 50%.
COTA_EQUIDADE = 1.0
COTA_ELEMENTARES = 1.0
COTA_PARTICIPACAO = 0.5

TETO_COTA_BDE = 2.5
TETO_FINAL = 3.0

NOMES_ETAPAS: dict[Etapa, str] = {
    Etapa.ANOS_INICIAIS: "Anos Iniciais",
    Etapa.ANOS_FINAIS: "Anos Finais",
    Etapa.ENSINO_MEDIO: "Ensino Médio",
}


def converter_diferenca_em_percentual(diferenca: float) -> float:
    """
    Tabela de conversão (grade E42:M43 da planilha).

    Cada faixa é inclusiva no limite inferior:
      < −0,3 → 0% | ≥ −0,3 → 25% | ≥ −0,2 → 50% | ≥ −0,1 → 75%
      ≥ 0,0 → 100% | ≥ +0,1 → 125% | ≥ +0,2 → 150% | ≥ +0,3 → 175% | ≥ +0,4 → 200%

    Divergência conhecida: a fórmula H45 devolve 0% para −0,3 < d < −0,2.
    Ver EXTRACAO_PLANILHA.md §5.2.
    """
    if diferenca < -0.3:
        return 0.0
    if diferenca < -0.2:
        return 0.25
    if diferenca < -0.1:
        return 0.50
    if diferenca < 0.0:
        return 0.75
    if diferenca < 0.1:
        return 1.00
    if diferenca < 0.2:
        return 1.25
    if diferenca < 0.3:
        return 1.50
    if diferenca < 0.4:
        return 1.75
    return 2.00


def _detalhar_etapa(etapa: Etapa, dados: EtapaIDEPE) -> DetalheEtapa:
    diferenca = round(dados.resultado - dados.meta, 4)
    return DetalheEtapa(
        etapa=etapa,
        nome=NOMES_ETAPAS[etapa],
        matriculas=dados.matriculas,
        meta=dados.meta,
        resultado=dados.resultado,
        diferenca=diferenca,
        atingiu_meta=diferenca >= 0,
        percentual_atingimento=converter_diferenca_em_percentual(diferenca),
    )


def calcular_bde(requisicao: RequisicaoBDE) -> RespostaBDE:
    """Calcula a cota do BDE a partir das respostas acumuladas do wizard."""
    informadas = [
        (Etapa.ANOS_INICIAIS, requisicao.etapa_anos_iniciais),
        (Etapa.ANOS_FINAIS, requisicao.etapa_anos_finais),
        (Etapa.ENSINO_MEDIO, requisicao.etapa_ensino_medio),
    ]
    etapas = [_detalhar_etapa(e, d) for e, d in informadas if d is not None]

    # H47 — média ponderada das diferenças pelas matrículas.
    total_matriculas = sum(e.matriculas for e in etapas)
    media_ponderada = round(
        sum(e.diferenca * e.matriculas for e in etapas) / total_matriculas, 4
    )

    # H45 — conversão em percentual de atingimento.
    percentual_idepe = converter_diferenca_em_percentual(media_ponderada)

    # B40 / B41 — decomposição do IDEPE em cota de resultado e excedente.
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem_resultado = max(percentual_idepe - cota_resultado, 0.0)

    # B42 / B43 / B44 — cotas independentes.
    cota_equidade = COTA_EQUIDADE if requisicao.reduziu_desigualdade else 0.0
    cota_elementares = COTA_ELEMENTARES if requisicao.terco_menor_elementares else 0.0
    cota_participacao = (
        COTA_PARTICIPACAO if requisicao.participacao_minima_atingida else 0.0
    )

    # C45 — ver aviso no topo do módulo.
    cota_bde = min(percentual_idepe + cota_equidade + cota_elementares, TETO_COTA_BDE)
    percentual_bde = round(min(cota_bde + cota_participacao, TETO_FINAL), 4)

    memoria = [
        f"{e.nome}: {e.resultado:.2f} − {e.meta:.2f} = {e.diferenca:+.2f} "
        f"({e.percentual_atingimento * 100:.0f}% de atingimento, "
        f"peso {e.matriculas} matrículas)"
        for e in etapas
    ]
    memoria.append(
        f"Média ponderada das diferenças: {media_ponderada:+.4f} "
        f"→ {percentual_idepe * 100:.0f}% de atingimento do IDEPE"
    )
    memoria.append(
        f"Cotas somadas: resultado {cota_resultado * 100:.0f}% + equidade "
        f"{cota_equidade * 100:.0f}% + elementares {cota_elementares * 100:.0f}% "
        f"+ participação {cota_participacao * 100:.0f}%"
    )
    memoria.append(f"Cota total do BDE: {percentual_bde * 100:.0f}%")

    return RespostaBDE(
        percentual_bde=percentual_bde,
        percentual_formatado=f"{percentual_bde * 100:.0f}%",
        apto_a_receber=percentual_bde > 0.0,
        media_ponderada_diferenca=media_ponderada,
        percentual_idepe=percentual_idepe,
        cota_resultado=cota_resultado,
        cota_alem_resultado=cota_alem_resultado,
        cota_equidade=cota_equidade,
        cota_elementares=cota_elementares,
        cota_participacao=cota_participacao,
        etapas=etapas,
        memoria_calculo=memoria,
    )
