# Simulador do BDE — Pernambuco

Backend do simulador do **Bônus de Desempenho Educacional (BDE)** para gestores
da rede estadual de Pernambuco. Recebe as respostas de um wizard e devolve a
cota do BDE com a memória de cálculo aberta.

A regra implementada é a do slide oficial "CENÁRIO DE METAS 2025 — BDE 2026":

```
total = min(atingimento + equidade + elementares + participação, 300%)
```

As cotas **somam** e o total é cortado em 300%. O máximo somável é
`175 + 100 + 100 + 50 = 425%` — o teto é o que vale, não a soma.

Escala de atingimento, 8 degraus, o último terminal ("0,3 ou mais"):

| `< −0,3` | `≥ −0,3` | `≥ −0,2` | `≥ −0,1` | **META** | `≥ +0,1` | `≥ +0,2` | `≥ +0,3` |
|---|---|---|---|---|---|---|---|
| 0% | 25% | 50% | 75% | **100%** | 125% | 150% | 175% |

A média ponderada pelas matrículas vem da planilha
`Simulador_Idepe_e_Atingimento_de_metas_2026.xlsx` do Núcleo da SEPLAG/PE, cuja
auditoria está em [`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md). A
fórmula `C45` daquela planilha **não** é usada: ela combina os objetivos bônus
com `OR` e contradiz os cenários oficiais (§5.1).

> Simulação **não oficial**, e o resultado é um **percentual de referência** —
> não um valor em reais. A destinação das verbas é decisão do setor financeiro,
> e o valor individual depende ainda de salário-base, cargo e tempo de vínculo.

## Como rodar

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

## `POST /api/v1/simular-bde`

Etapas não pactuadas são omitidas do payload; ao menos uma é obrigatória. Cada
etapa exige `matriculas`, `meta` e `resultado` juntos — informar matrícula sem
meta diluiria a média ponderada em silêncio.

```json
{
  "etapa_anos_iniciais": { "matriculas": 320, "meta": 4.5, "resultado": 4.7 },
  "etapa_ensino_medio":  { "matriculas": 50,  "meta": 5.0, "resultado": 5.0 },
  "reduziu_desigualdade": true,
  "terco_menor_elementares": false,
  "participacao_minima_atingida": true
}
```

Resposta (abreviada):

```json
{
  "percentual_bde": 2.5,
  "percentual_formatado": "250%",
  "apto_a_receber": true,
  "media_ponderada_diferenca": 0.173,
  "percentual_idepe": 1.25,
  "cota_equidade": 1.0,
  "cota_elementares": 0.0,
  "cota_participacao": 0.5,
  "soma_sem_teto": 2.75,
  "teto_aplicado": false,
  "etapas": [ "..." ],
  "memoria_calculo": [ "..." ],
  "alertas": [ "..." ],
  "aviso_legal": "..."
}
```

`percentual_formatado` é o que se mostra ao gestor. `soma_sem_teto` e
`teto_aplicado` existem para **explicar** o corte quando a soma passa de 300% —
nunca para serem exibidos como resultado.

`memoria_calculo` abre a conta parcela por parcela. `alertas` calcula o ganho
real de cada objetivo ainda pendente, já descontado o teto.

## Três leituras da regra que o frontend precisa comunicar

Levantadas da tabela-verdade completa ([`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md) §6):

1. **Os objetivos bônus valem mais que o desempenho na meta.** Os dois somam 200
   pontos; o atingimento máximo soma 175. Uma escola abaixo da meta com os dois
   bônus (200%) supera uma que passou da meta sem nenhum (175%).
2. **O teto corta com frequência.** Quem atinge a meta e os dois objetivos já
   soma 300% — participação e desempenho extra não acrescentam nada.
3. **`≥ 0,3` é degrau terminal.** Superar a meta em 0,3 ou em 1,2 dá os mesmos
   175%.

## Estrutura

```
main.py              aplicação FastAPI e CORS
src/bde/schemas.py   contrato de entrada e saída (Pydantic)
src/bde/service.py   motor de cálculo — reprodução de H45, H47 e C45
src/bde/router.py    POST /api/v1/simular-bde
```

## Documentação

- [`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md) — auditoria célula a
  célula, fórmulas mortas, divergências e a tabela-verdade de conferência.
- [`docs/CAMINHOS_RUINS.md`](docs/CAMINHOS_RUINS.md) — rotas de uso que quebram
  a solução, com o estado de cada uma.
