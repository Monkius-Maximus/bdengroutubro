"""
Serviço de cálculo do BDE.

Fonte de verdade: o slide oficial "CENÁRIO DE METAS 2025 — BDE 2026" e a regra
de negócio do projeto. As cotas **somam** e o total é limitado a 300%:

    total = min(atingimento + equidade + elementares + participação, 300%)

Escala de atingimento — 8 degraus, o último é terminal ("0,3 ou mais"):

    < −0,3 → 0%   |  ≥ −0,3 → 25%  |  ≥ −0,2 → 50%  |  ≥ −0,1 → 75%
    ≥ 0,0 → 100% (META)  |  ≥ +0,1 → 125%  |  ≥ +0,2 → 150%  |  ≥ +0,3 → 175%

O máximo somável é 1,75 + 1,0 + 1,0 + 0,5 = 4,25, sempre cortado em 3,0. Uma
escola que supera a meta e atinge os dois objetivos bônus soma 375% e recebe
300% — o teto é o que vale, não a soma.

A média ponderada pelas matrículas vem da planilha da SEPLAG (nota 5: "para
escolas com mais de uma etapa, o atingimento é calculado de forma ponderada").
A fórmula C45 daquela planilha **não** é usada: ela combina os bônus com OR e
contradiz os cenários oficiais. Ver docs/EXTRACAO_PLANILHA.md §5.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.bde.schemas import (
    DetalheEtapa,
    Etapa,
    EtapaIDEPE,
    RequisicaoBDE,
    RespostaBDE,
)

COTA_EQUIDADE = 1.0
COTA_ELEMENTARES = 1.0
COTA_PARTICIPACAO = 0.5

TETO_BDE = 3.0

# Escala de atingimento, do degrau mais alto para o mais baixo.
# O primeiro limite que a diferença alcançar define o percentual.
TABELA_ATINGIMENTO: tuple[tuple[float, float], ...] = (
    (0.3, 1.75),  # "0,3 ou mais" — degrau terminal
    (0.2, 1.50),
    (0.1, 1.25),
    (0.0, 1.00),  # META
    (-0.1, 0.75),
    (-0.2, 0.50),
    (-0.3, 0.25),
)
ATINGIMENTO_MAXIMO = TABELA_ATINGIMENTO[0][1]

MARGEM_ALERTA = 0.01

NOMES_ETAPAS: dict[Etapa, str] = {
    Etapa.ANOS_INICIAIS: "Anos Iniciais",
    Etapa.ANOS_FINAIS: "Anos Finais",
    Etapa.ENSINO_MEDIO: "Ensino Médio",
}


def arredondar_excel(valor: float) -> float:
    """
    ROUND(valor; 4) do Excel — empate vai para longe do zero.

    O round() do Python é bancário e cairia no degrau errado em 0,09995, que
    separa 100% de 125%.
    """
    return float(
        Decimal(repr(valor)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    )


def converter_diferenca_em_percentual(diferenca: float) -> float:
    """Aplica a escala de 8 degraus. Abaixo de −0,3 a escola não pontua."""
    for limite, percentual in TABELA_ATINGIMENTO:
        if diferenca >= limite:
            return percentual
    return 0.0


def _detalhar_etapa(etapa: Etapa, dados: EtapaIDEPE) -> DetalheEtapa:
    diferenca = arredondar_excel(dados.resultado - dados.meta)
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


def _ganho_real(total: float, acrescimo: float) -> float:
    """Quanto um acréscimo de fato adiciona, já descontado o teto."""
    return min(total + acrescimo, TETO_BDE) - total


def _gerar_alertas(
    *,
    media_ponderada: float,
    percentual_idepe: float,
    percentual_bde: float,
    soma_sem_teto: float,
    tem_equidade: bool,
    tem_elementares: bool,
    tem_participacao: bool,
) -> list[str]:
    """Traduz o cálculo em orientação sobre o que ainda pode mudar o resultado."""
    alertas: list[str] = []

    if soma_sem_teto > TETO_BDE:
        alertas.append(
            f"Suas cotas somam {soma_sem_teto * 100:.0f}%, mas o BDE é limitado a "
            f"{TETO_BDE * 100:.0f}%. É esse teto que vale."
        )

    if percentual_idepe < ATINGIMENTO_MAXIMO:
        acima = [limite for limite, _ in reversed(TABELA_ATINGIMENTO) if limite > media_ponderada]
        if acima:
            proximo = acima[0]
            falta = proximo - media_ponderada
            if falta < MARGEM_ALERTA:
                subiria = converter_diferenca_em_percentual(proximo)
                alertas.append(
                    f"Faltaram {falta:.4f} na média ponderada para alcançar "
                    f"{proximo:+.1f}, que levaria o atingimento de "
                    f"{percentual_idepe * 100:.0f}% para {subiria * 100:.0f}%."
                )
    else:
        alertas.append(
            "Seu atingimento está no degrau máximo da escala (0,3 ou mais acima "
            "da meta), que vale 175%. Superar ainda mais a meta não altera essa cota."
        )

    pendentes = [
        (not tem_equidade, COTA_EQUIDADE,
         "atingir a meta de equidade (evolução dos estudantes PPI e de NSE I e II)"),
        (not tem_elementares, COTA_ELEMENTARES,
         "estar no 1º terço com menor percentual de estudantes nos níveis elementares"),
        (not tem_participacao, COTA_PARTICIPACAO,
         "alcançar participação de pelo menos 80% no SAEPE"),
    ]
    for falta, valor, descricao in pendentes:
        if not falta:
            continue
        ganho = _ganho_real(percentual_bde, valor)
        if ganho > 0:
            alertas.append(
                f"Ainda dá para subir: {descricao} acrescentaria "
                f"{ganho * 100:.0f} pontos percentuais."
            )

    return alertas


def calcular_bde(requisicao: RequisicaoBDE) -> RespostaBDE:
    """Calcula a cota do BDE a partir das respostas acumuladas do wizard."""
    informadas = [
        (Etapa.ANOS_INICIAIS, requisicao.etapa_anos_iniciais),
        (Etapa.ANOS_FINAIS, requisicao.etapa_anos_finais),
        (Etapa.ENSINO_MEDIO, requisicao.etapa_ensino_medio),
    ]
    avaliadas = [(etapa, dados) for etapa, dados in informadas if dados is not None]
    etapas = [_detalhar_etapa(etapa, dados) for etapa, dados in avaliadas]

    # Média ponderada pelas matrículas, sobre as diferenças cruas.
    total_matriculas = sum(dados.matriculas for _, dados in avaliadas)
    soma_ponderada = sum(
        (dados.resultado - dados.meta) * dados.matriculas for _, dados in avaliadas
    )
    media_ponderada = arredondar_excel(soma_ponderada / total_matriculas)

    percentual_idepe = converter_diferenca_em_percentual(media_ponderada)
    cota_equidade = COTA_EQUIDADE if requisicao.reduziu_desigualdade else 0.0
    cota_elementares = COTA_ELEMENTARES if requisicao.terco_menor_elementares else 0.0
    cota_participacao = (
        COTA_PARTICIPACAO if requisicao.participacao_minima_atingida else 0.0
    )

    soma_sem_teto = (
        percentual_idepe + cota_equidade + cota_elementares + cota_participacao
    )
    percentual_bde = min(soma_sem_teto, TETO_BDE)

    memoria = [
        f"{e.nome}: {e.resultado:.2f} − {e.meta:.2f} = {e.diferenca:+.4f} "
        f"(peso {e.matriculas} matrículas)"
        for e in etapas
    ]
    memoria += [
        f"Média ponderada das diferenças: {media_ponderada:+.4f}",
        f"Atingimento da meta: {percentual_idepe * 100:.0f}%",
        f"Meta de equidade (PPI e NSE I e II): +{cota_equidade * 100:.0f}%",
        f"1º terço com menor % de elementares: +{cota_elementares * 100:.0f}%",
        f"Participação ≥ 80% no SAEPE: +{cota_participacao * 100:.0f}%",
        f"Soma das cotas: {soma_sem_teto * 100:.0f}%",
    ]
    if soma_sem_teto > TETO_BDE:
        memoria.append(
            f"Teto do BDE aplicado: {soma_sem_teto * 100:.0f}% "
            f"→ {TETO_BDE * 100:.0f}%"
        )
    memoria.append(f"Cota total do BDE: {percentual_bde * 100:.0f}%")

    return RespostaBDE(
        percentual_bde=percentual_bde,
        percentual_formatado=f"{percentual_bde * 100:.0f}%",
        apto_a_receber=percentual_bde > 0.0,
        media_ponderada_diferenca=media_ponderada,
        percentual_idepe=percentual_idepe,
        cota_equidade=cota_equidade,
        cota_elementares=cota_elementares,
        cota_participacao=cota_participacao,
        soma_sem_teto=soma_sem_teto,
        teto_aplicado=soma_sem_teto > TETO_BDE,
        etapas=etapas,
        memoria_calculo=memoria,
        alertas=_gerar_alertas(
            media_ponderada=media_ponderada,
            percentual_idepe=percentual_idepe,
            percentual_bde=percentual_bde,
            soma_sem_teto=soma_sem_teto,
            tem_equidade=requisicao.reduziu_desigualdade,
            tem_elementares=requisicao.terco_menor_elementares,
            tem_participacao=requisicao.participacao_minima_atingida,
        ),
    )
