"""
Schemas Pydantic — Simulador do Bônus de Desempenho Educacional (BDE).

Nomenclatura em português com siglas claras:
  AI  = Anos Iniciais (Ensino Fundamental)
  AF  = Anos Finais  (Ensino Fundamental)
  EM  = Ensino Médio

Referências de células (aba "Simulador BDE"):
  B6/B7/B8    → matrículas por etapa
  B19/B20     → Meta / Resultado EFAI  → diferença em B21
  B27/B28     → Meta / Resultado EFAF  → diferença em B29
  B35/B36     → Meta / Resultado EM    → diferença em B37
  H47 / J9    → média ponderada das diferenças
  H45         → percentual IDEPE (tabela de conversão)
  B40         → cota resultado
  B41         → cota além do resultado
  B42         → cota equidade  (SIM/NÃO)
  B43         → cota elementares (SIM/NÃO)
  B44         → cota participação ≥ 80%
  C45         → cota do BDE (fórmula composta)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Etapa avaliada (cada etapa é opcional — escola pode pactuar 1, 2 ou 3)
# ---------------------------------------------------------------------------

class EtapaIDEPE(BaseModel):
    """
    Dados de uma etapa letiva para cálculo do IDEPE.
    Cada etapa possui matrículas (peso), meta pactuada e resultado obtido.
    """

    matriculas: int = Field(
        ...,
        gt=0,
        description=(
            "Quantidade de matrículas na etapa. "
            "Usado como peso no cálculo da média ponderada."
        ),
    )
    meta: float = Field(
        ...,
        gt=0,
        description="Meta IDEPE pactuada para a etapa (ex: 4.50).",
    )
    resultado: float = Field(
        ...,
        gt=0,
        description="Resultado IDEPE obtido pela escola (ex: 4.70).",
    )


# ---------------------------------------------------------------------------
# Request — payload completo do wizard (todas as respostas acumuladas)
# ---------------------------------------------------------------------------

class RequisicaoBDE(BaseModel):
    """
    Payload enviado pelo frontend ao final do wizard.
    Pelo menos UMA etapa deve ser informada.
    """

    # ---- Etapas avaliadas (pelo menos uma obrigatória) ----
    etapa_ai: Optional[EtapaIDEPE] = Field(
        None,
        description="Ensino Fundamental — Anos Iniciais (1º ao 5º ano).",
    )
    etapa_af: Optional[EtapaIDEPE] = Field(
        None,
        description="Ensino Fundamental — Anos Finais (6º ao 9º ano).",
    )
    etapa_em: Optional[EtapaIDEPE] = Field(
        None,
        description="Ensino Médio (1º ao 3º ano).",
    )

    # ---- Equidade (bônus independente #1) ----
    reduziu_desigualdade: bool = Field(
        ...,
        description=(
            "Houve evolução, no SAEPE 2025, dos estudantes "
            "Pretos, Pardos e Indígenas (PPI) e daqueles de "
            "nível socioeconômico mais baixo, em comparação com 2024? "
            "(SIM / NÃO)"
        ),
    )

    # ---- Elementares (bônus independente #2) ----
    terco_menor_elementares: bool = Field(
        ...,
        description=(
            "Na Macrorregião, comparando com escolas do mesmo tipo, "
            "sua escola está entre o 1º terço (33,3%) com menor "
            "percentual de estudantes nos níveis elementares (PD 1 e 2) "
            "no SAEPE 2025? (SIM / NÃO)"
        ),
    )

    # ---- Participação ----
    participacao_maior_80: bool = Field(
        ...,
        description=(
            "A escola atingiu participação igual ou superior a 80% "
            "em TODOS os componentes e etapas avaliados no SAEPE 2026? "
            "(SIM / NÃO)"
        ),
    )

    @model_validator(mode="after")
    def _pelo_menos_uma_etapa(self):
        if not any([self.etapa_ai, self.etapa_af, self.etapa_em]):
            raise ValueError(
                "Informe pelo menos UMA etapa avaliada (Anos Iniciais, "
                "Anos Finais ou Ensino Médio)."
            )
        return self


# ---------------------------------------------------------------------------
# Detalhamento por etapa (usado na resposta)
# ---------------------------------------------------------------------------

class DetalheEtapa(BaseModel):
    """Resultado do cálculo para uma etapa individual."""

    nome: str = Field(description="Nome da etapa (ex: 'Anos Iniciais').")
    matriculas: int = Field(description="Matrículas da etapa.")
    meta: float = Field(description="Meta IDEPE da etapa.")
    resultado: float = Field(description="Resultado IDEPE da etapa.")
    variacao: float = Field(
        description="Variacao = Resultado − Meta (pode ser negativa)."
    )
    percentual_atingimento: float = Field(
        description=(
            "Percentual de atingimento da meta, convertido pela "
            "tabela IDEPE (0.0 a 2.0, ou 0% a 200%)."
        )
    )


# ---------------------------------------------------------------------------
# Response — resultado completo do simulador
# ---------------------------------------------------------------------------

class RespostaBDE(BaseModel):
    """Resposta detalhada do simulador BDE."""

    # ---- Percentual final ----
    percentual_bde: float = Field(
        ...,
        le=3.0,
        ge=0.0,
        description="Percentual final do BDE (0.0 a 3.0, ou 0% a 300%).",
    )
    percentual_formatado: str = Field(
        ...,
        description="Percentual formatado para exibição (ex: '200%').",
    )

    # ---- Média ponderada ----
    media_ponderada_variacao: float = Field(
        description=(
            "Média ponderada das variações (Resultado − Meta) "
            "entre todas as etapas avaliadas, ponderada pelas matrículas."
        ),
    )

    # ---- Percentual IDEPE (tabela de conversão) ----
    percentual_idepe: float = Field(
        description=(
            "Percentual convertido da média de variação via tabela IDEPE. "
            "Escala: 0% a 200%."
        ),
    )

    # ---- Bônus independentes ----
    bonus_equidade: float = Field(
        description="Bônus por redução de desigualdades PPI/Renda (0 ou 1.0)."
    )
    bonus_elementares: float = Field(
        description="Bônus por estar no 1º terço de elementares (0 ou 1.0)."
    )
    bonus_participacao: float = Field(
        description="Bônus por participação ≥ 80% (0 ou 0.5)."
    )

    # ---- Cotas intermediárias (transparência do cálculo) ----
    cota_resultado: float = Field(
        description="Cota base derivada do percentual IDEPE (máx. 1.0)."
    )
    cota_alem_resultado: float = Field(
        description="Parcela do percentual IDEPE que ultrapassa 100% (0 a 1.0)."
    )
    cota_bde_calculada: float = Field(
        description=(
            "Cota do BDE calculada = "
            "min(IDEPE + equidade + elementares, 2.5). "
            "A participação é somada depois."
        ),
    )

    # ---- Indicador final ----
    apto_a_receber: bool = Field(
        description="Escola tem direito a receber o BDE (percentual > 0%)."
    )

    # ---- Detalhamento por etapa ----
    etapas: list[DetalheEtapa] = Field(
        default_factory=list,
        description="Detalhamento do cálculo para cada etapa avaliada.",
    )
