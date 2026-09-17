"""
Schemas Pydantic — Simulador do Bônus de Desempenho Educacional (BDE).

Fonte de verdade: aba "Simulador BDE" da planilha
"Simulador_Idepe_e_Atingimento_de_metas_2026.xlsx" (Núcleo da SEPLAG/PE).

Mapa célula → campo:
  B6  / B7  / B8   → matrículas AI / AF / EM      (peso da média ponderada)
  B19 / B20 / B21  → meta / resultado / diferença — Anos Iniciais
  B27 / B28 / B29  → meta / resultado / diferença — Anos Finais
  B35 / B36 / B37  → meta / resultado / diferença — Ensino Médio
  D12              → equidade PPI/NSE (SIM/NÃO)
  D13              → 1º terço com menor % de elementares (SIM/NÃO)
  H47              → média ponderada das diferenças (ROUND 4 casas)
  H45              → percentual IDEPE (tabela de conversão)
  B40 / B41        → cota resultado / cota além do resultado
  B42 / B43 / B44  → cota equidade / elementares / participação
  C45              → cota total do BDE

Divergência deliberada: a planilha não possui campo de participação — B44 é a
constante 0,5 sempre somada. A regra de negócio deste produto condiciona essa
cota à participação ≥ 80% no SAEPE, por isso o campo existe aqui.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Limites extraídos da validação de dados da planilha
# ---------------------------------------------------------------------------

# B6/B7/B8: decimal entre 8 e 50000 ("caso não tenha matrículas, deixar vazio")
MATRICULAS_MIN = 8
MATRICULAS_MAX = 50_000

# B19/B27/B35 (meta): 1,5 a 9,2 — B20/B28/B36 (resultado): 1,9 a 9,2.
# Adotamos 1,5 como piso único: rejeitar um resultado legitimamente baixo
# (ex.: 1,7) seria pior do que aceitar o intervalo mais largo da meta.
IDEPE_MIN = 1.5
IDEPE_MAX = 9.2


class Etapa(str, Enum):
    """Etapas em que a escola pode ter pactuado metas."""

    ANOS_INICIAIS = "anos_iniciais"
    ANOS_FINAIS = "anos_finais"
    ENSINO_MEDIO = "ensino_medio"


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


class EtapaIDEPE(BaseModel):
    """
    Bloco atômico de uma etapa avaliada.

    Os três valores andam juntos por decisão de projeto: na planilha as
    matrículas (B6:B8) e as metas (B19/B27/B35) são preenchidas em blocos
    separados, e informar matrícula sem meta faz a etapa entrar no
    denominador de H47 com diferença zero, diluindo o resultado sem aviso.
    Aqui a etapa ou é informada por inteiro, ou não é avaliada.
    """

    matriculas: int = Field(
        ...,
        ge=MATRICULAS_MIN,
        le=MATRICULAS_MAX,
        description="Matrículas de 2025 na etapa. Peso da média ponderada (B6/B7/B8).",
    )
    meta: float = Field(
        ...,
        ge=IDEPE_MIN,
        le=IDEPE_MAX,
        description="Meta IDEPE 2025 pactuada no Termo de Compromisso (B19/B27/B35).",
    )
    resultado: float = Field(
        ...,
        ge=IDEPE_MIN,
        le=IDEPE_MAX,
        description="IDEPE 2025 obtido pela escola (B20/B28/B36).",
    )


class RequisicaoBDE(BaseModel):
    """
    Payload acumulado do wizard. Etapas não pactuadas são omitidas.
    """

    etapa_anos_iniciais: Optional[EtapaIDEPE] = Field(
        None, description="Ensino Fundamental — Anos Iniciais (1º ao 5º ano)."
    )
    etapa_anos_finais: Optional[EtapaIDEPE] = Field(
        None, description="Ensino Fundamental — Anos Finais (6º ao 9º ano)."
    )
    etapa_ensino_medio: Optional[EtapaIDEPE] = Field(
        None, description="Ensino Médio (1ª à 3ª série)."
    )

    reduziu_desigualdade: bool = Field(
        ...,
        description=(
            "D12 — Houve evolução, no SAEPE 2025, dos estudantes Pretos, Pardos e "
            "Indígenas e daqueles de nível socioeconômico mais baixo, em comparação "
            "com 2024? (consultar o BI da Equidade)"
        ),
    )
    terco_menor_elementares: bool = Field(
        ...,
        description=(
            "D13 — Na Macrorregião, comparando com escolas do mesmo tipo, a escola "
            "está no 1º terço (33,3%) com menor percentual de estudantes nos níveis "
            "elementares no SAEPE 2025? (consultar o BI do SAEPE, versão GRE)"
        ),
    )
    participacao_minima_atingida: bool = Field(
        ...,
        description=(
            "A escola atingiu participação ≥ 80% em TODOS os componentes e etapas "
            "avaliados no SAEPE? Booleano, e não a taxa: a exigência é por "
            "componente e por etapa, logo um único percentual não a representa."
        ),
    )

    @model_validator(mode="after")
    def _exige_ao_menos_uma_etapa(self) -> "RequisicaoBDE":
        if not (
            self.etapa_anos_iniciais
            or self.etapa_anos_finais
            or self.etapa_ensino_medio
        ):
            raise ValueError(
                "Informe ao menos uma etapa pactuada (Anos Iniciais, Anos Finais "
                "ou Ensino Médio). Escola sem meta pactuada não é elegível ao BDE."
            )
        return self


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------


class DetalheEtapa(BaseModel):
    """Recorte por etapa, para o wizard mostrar o que foi ou não atingido."""

    etapa: Etapa
    nome: str = Field(description="Rótulo de exibição (ex.: 'Anos Iniciais').")
    matriculas: int
    meta: float
    resultado: float
    diferenca: float = Field(
        description="Resultado − Meta, arredondado a 4 casas (B21/B29/B37)."
    )
    atingiu_meta: bool = Field(description="diferenca >= 0.")
    percentual_atingimento: float = Field(
        description="Diferença da etapa convertida pela escala (0,0 a 1,75)."
    )


class RespostaBDE(BaseModel):
    """Resultado do simulador, com a memória de cálculo aberta."""

    # ---- Resultado final ----
    percentual_bde: float = Field(
        ..., ge=0.0, le=3.0, description="Cota total do BDE, já limitada a 3,0."
    )
    percentual_formatado: str = Field(
        ..., description="Percentual pronto para exibição (ex.: '250%')."
    )
    apto_a_receber: bool = Field(
        description="Escola faz jus a alguma cota do BDE (percentual > 0)."
    )

    # ---- Atingimento do IDEPE ----
    media_ponderada_diferenca: float = Field(
        description="H47 — Σ(diferença × matrículas) / Σ(matrículas), 4 casas."
    )
    percentual_idepe: float = Field(
        description=(
            "Atingimento da meta: média ponderada convertida pela escala de 8 "
            "degraus (0,0 a 1,75). É a cota base, somada às demais."
        )
    )

    # ---- Cotas que compõem a soma ----
    cota_equidade: float = Field(
        description="+100% por evolução dos estudantes PPI e de NSE I e II."
    )
    cota_elementares: float = Field(
        description="+100% por estar no 1º terço com menor % de elementares."
    )
    cota_participacao: float = Field(
        description="+50% por participação ≥ 80% no SAEPE."
    )

    # ---- Teto ----
    soma_sem_teto: float = Field(
        description=(
            "Soma das cotas antes do corte. Pode passar de 3,0: o máximo "
            "somável é 1,75 + 1,0 + 1,0 + 0,5 = 4,25."
        )
    )
    teto_aplicado: bool = Field(
        description="A soma ultrapassou 300% e foi limitada ao teto."
    )

    # ---- Transparência ----
    etapas: list[DetalheEtapa] = Field(
        default_factory=list, description="Detalhamento por etapa avaliada."
    )
    memoria_calculo: list[str] = Field(
        default_factory=list,
        description="Passos do cálculo em linguagem natural, na ordem de aplicação.",
    )
    alertas: list[str] = Field(
        default_factory=list,
        description="Avisos ao gestor (ex.: resultado próximo de uma faixa superior).",
    )
    aviso_legal: str = Field(
        default=(
            "Simulação não oficial. Desenvolvida para esclarecer dúvidas sobre o "
            "atingimento das metas; pequenas diferenças podem ocorrer por "
            "arredondamento. O valor final do BDE depende ainda de salário-base, "
            "cargo e tempo de vínculo, que não entram nesta simulação."
        ),
        description="Reprodução do disclaimer das notas 1, 2 e 4 da planilha.",
    )
