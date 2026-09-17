"""
Serviço de cálculo do BDE — reprodução fiel da aba "Simulador BDE".

Cadeia de cálculo, na ordem da planilha:

    B21/B29/B37  diferença por etapa = resultado − meta (sem arredondar)
    H47          média ponderada pelas matrículas, ROUND(...; 4)
    H45          conversão da média em percentual de atingimento
    B40 / B41    cota resultado = min(H45; 1) / cota além = H45 − B40
    B42 / B43    cotas de equidade e de elementares
    B44          cota de participação
    C45          cota total do BDE

Divergências conhecidas da planilha em relação à regra escrita, reproduzidas
por decisão de negócio (mecanismo já validado e em uso na SEPLAG):

  - As cotas de equidade e elementares não são cumulativas: C45 usa OR.
  - H45 devolve 0% para diferenças entre −0,3 e −0,2.

Detalhes e tabela-verdade em docs/EXTRACAO_PLANILHA.md.
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

# Pesos das cotas — mudam entre ciclos. No BDE 2025 a participação valeu 25%.
COTA_EQUIDADE = 1.0
COTA_ELEMENTARES = 1.0
COTA_PARTICIPACAO = 0.5

TETO_BDE = 3.0

NOMES_ETAPAS: dict[Etapa, str] = {
    Etapa.ANOS_INICIAIS: "Anos Iniciais",
    Etapa.ANOS_FINAIS: "Anos Finais",
    Etapa.ENSINO_MEDIO: "Ensino Médio",
}

# Limites das faixas de H45, para o alerta de proximidade.
LIMITES_FAIXAS = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4)

# Distância a partir da qual vale avisar que a faixa seguinte está perto.
MARGEM_ALERTA = 0.01


def arredondar_excel(valor: float) -> float:
    """
    ROUND(valor; 4) do Excel — empate vai para longe do zero.

    O round() do Python é bancário e pode cair na faixa errada quando o valor
    encosta num limite: 0,09995 separa 100% de 125%.
    """
    return float(
        Decimal(repr(valor)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    )


def converter_diferenca_em_percentual(diferenca: float) -> float:
    """
    Fórmula H45. Recebe diferença já arredondada por `arredondar_excel`.

    A ordem dos testes reproduz a escada de IFs da planilha, inclusive o trecho
    em que ela devolve 0 em vez de ler 0,25 da grade E42:M43.
    """
    if diferenca < -0.3:
        return 0.00
    if diferenca == -0.3:
        return 0.25  # única diferença que rende 25% em H45
    if diferenca < -0.2:
        return 0.00  # buraco de H45, reproduzido por decisão de negócio
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


def calcular_cota_bde(
    percentual_idepe: float, tem_equidade: bool, tem_elementares: bool
) -> tuple[float, str]:
    """
    Fórmula C45, sem a parcela B44. Devolve a cota e o rótulo do ramo aplicado.

    Forma reduzida de 3 ramos. O 3º ramo da planilha é inalcançável (B40 é
    min(H45; 1), logo B40<=1 é sempre verdadeiro) e também redundante: quando
    valeria, devolveria 2, o mesmo que 1+B40 com B40=1.
    """
    cota_resultado = min(percentual_idepe, 1.0)  # B40
    cota_alem = max(percentual_idepe - cota_resultado, 0.0)  # B41

    if cota_resultado == 1.0 and cota_alem == 1.0 and tem_equidade and tem_elementares:
        return 2.5, "atingimento de 200% com as duas metas de equidade"
    if tem_equidade or tem_elementares:
        return 1.0 + cota_resultado, "cota de resultado + 100% por meta de equidade"
    return cota_resultado, "apenas a cota de resultado, sem metas de equidade"


def _detalhar_etapa(etapa: Etapa, dados: EtapaIDEPE) -> DetalheEtapa:
    """
    Recorte por etapa para o wizard.

    A diferença exibida é arredondada porque, numa escola de etapa única, H47
    reduz a ROUND(B21; 4) — é o número que o gestor vê na planilha.
    """
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


def _gerar_alertas(
    *,
    media_ponderada: float,
    percentual_idepe: float,
    percentual_bde: float,
    tem_equidade: bool,
    tem_elementares: bool,
    tem_participacao: bool,
) -> list[str]:
    """Traduz os platôs da fórmula em orientação para o gestor."""
    alertas: list[str] = []

    if -0.3 < media_ponderada < -0.2:
        alertas.append(
            "Sua média ponderada ficou entre −0,30 e −0,20. Nessa faixa a cota "
            "de resultado fica em 0%: apenas a diferença exatamente igual a "
            "−0,30 recebe 25%. Confirme o resultado com a sua GRE."
        )

    proximos = [limite for limite in LIMITES_FAIXAS if limite > media_ponderada]
    if proximos:
        proximo = proximos[0]
        falta = proximo - media_ponderada
        if falta < MARGEM_ALERTA:
            ganho = converter_diferenca_em_percentual(proximo)
            alertas.append(
                f"Faltaram {falta:.4f} ponto(s) na média ponderada para alcançar "
                f"a diferença de {proximo:+.1f}, que elevaria o atingimento do "
                f"IDEPE para {ganho * 100:.0f}%."
            )

    no_teto_absoluto = percentual_idepe == 2.0 and tem_equidade and tem_elementares
    if percentual_idepe > 1.0 and not no_teto_absoluto:
        alertas.append(
            "Sua cota de resultado já está no teto de 100%. Superar ainda mais a "
            "meta só aumenta o BDE se o atingimento chegar a 200% (diferença de "
            "+0,40 ou mais) e as duas metas de equidade forem atingidas."
        )

    if not tem_equidade and not tem_elementares:
        alertas.append(
            "Atingir qualquer uma das duas metas de equidade elevaria a cota do "
            "BDE em 100 pontos percentuais."
        )
    elif tem_equidade != tem_elementares:
        if percentual_idepe == 2.0:
            alertas.append(
                "Atingir também a outra meta de equidade elevaria a cota do BDE "
                "em 50 pontos percentuais."
            )
        else:
            alertas.append(
                "A segunda meta de equidade não altera a cota nesta faixa de "
                "atingimento: as duas juntas só valem mais que uma isolada "
                "quando o atingimento do IDEPE chega a 200%."
            )
    elif percentual_idepe < 2.0:
        alertas.append(
            "As duas metas de equidade juntas valem o mesmo que uma isolada "
            "nesta faixa de atingimento, porque a fórmula não as soma."
        )

    if not tem_participacao:
        alertas.append(
            "Participação igual ou superior a 80% em todos os componentes e "
            "etapas do SAEPE acrescentaria 50 pontos percentuais."
        )

    if percentual_bde < TETO_BDE and tem_participacao and (tem_equidade or tem_elementares):
        alertas.append(
            "O teto de 300% exige, simultaneamente: atingimento do IDEPE de 200%, "
            "as duas metas de equidade e participação de pelo menos 80%."
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

    # H47 — a planilha pondera as diferenças CRUAS e arredonda só o quociente.
    total_matriculas = sum(dados.matriculas for _, dados in avaliadas)
    soma_ponderada = sum(
        (dados.resultado - dados.meta) * dados.matriculas for _, dados in avaliadas
    )
    media_ponderada = arredondar_excel(soma_ponderada / total_matriculas)

    # H45 → B40 / B41
    percentual_idepe = converter_diferenca_em_percentual(media_ponderada)
    cota_resultado = min(percentual_idepe, 1.0)
    cota_alem_resultado = max(percentual_idepe - cota_resultado, 0.0)

    # B42 / B43 / B44
    cota_equidade = COTA_EQUIDADE if requisicao.reduziu_desigualdade else 0.0
    cota_elementares = COTA_ELEMENTARES if requisicao.terco_menor_elementares else 0.0
    cota_participacao = (
        COTA_PARTICIPACAO if requisicao.participacao_minima_atingida else 0.0
    )

    # C45
    cota_bde, ramo_aplicado = calcular_cota_bde(
        percentual_idepe,
        requisicao.reduziu_desigualdade,
        requisicao.terco_menor_elementares,
    )
    percentual_bde = cota_bde + cota_participacao

    memoria = [
        f"{e.nome}: {e.resultado:.2f} − {e.meta:.2f} = {e.diferenca:+.4f} "
        f"(peso {e.matriculas} matrículas)"
        for e in etapas
    ]
    memoria += [
        f"Média ponderada das diferenças (H47): {media_ponderada:+.4f}",
        f"Atingimento do IDEPE (H45): {percentual_idepe * 100:.0f}%",
        f"Cota resultado (B40): {cota_resultado * 100:.0f}% · "
        f"Cota além do resultado (B41): {cota_alem_resultado * 100:.0f}%",
        f"Cota equidade (B42): {cota_equidade * 100:.0f}% · "
        f"Cota elementares (B43): {cota_elementares * 100:.0f}%",
        f"Cota do BDE (C45): {cota_bde * 100:.0f}% — {ramo_aplicado}",
        f"Cota participação (B44): +{cota_participacao * 100:.0f}%",
        f"Cota total do BDE: {percentual_bde * 100:.0f}%",
    ]
    if cota_alem_resultado > 0 and cota_bde != 2.5:
        memoria.append(
            f"Observação: a cota além do resultado "
            f"({cota_alem_resultado * 100:.0f}%) não entra neste total. A fórmula "
            f"C45 só a considera quando o atingimento é de 200% e as duas metas "
            f"de equidade foram atingidas."
        )

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
        alertas=_gerar_alertas(
            media_ponderada=media_ponderada,
            percentual_idepe=percentual_idepe,
            percentual_bde=percentual_bde,
            tem_equidade=requisicao.reduziu_desigualdade,
            tem_elementares=requisicao.terco_menor_elementares,
            tem_participacao=requisicao.participacao_minima_atingida,
        ),
    )
