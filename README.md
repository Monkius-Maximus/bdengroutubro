# Simulador do BDE — Pernambuco

Simulador do **Bônus de Desempenho Educacional (BDE)** para gestores da rede
estadual de Pernambuco. Um wizard pergunta os números do IDEPE e devolve a cota
do BDE com a memória de cálculo aberta.

São duas implementações da mesma regra, mantidas idênticas por teste:

- **`web/index.html`** — a página que vai ao ar. Wizard completo, calcula no
  navegador, sem dependências e sem rede. É o que se publica no Google Sites
  ([`docs/GOOGLE_SITES.md`](docs/GOOGLE_SITES.md)).
- **`main.py` + `src/bde/`** — o backend FastAPI, para quem precisar consumir a
  regra como API. Não é usado pela página.

O motor reproduz a planilha `Simulador_Idepe_e_Atingimento_de_metas_2026.xlsx`
do Núcleo da SEPLAG/PE, célula por célula — inclusive onde ela contraria a regra
escrita, para que o simulador web e a planilha em circulação nunca divirjam.
As decisões estão registradas em [`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md).

> Simulação **não oficial**. O valor final do BDE depende ainda de salário-base,
> cargo e tempo de vínculo, que não entram neste cálculo.

## Como rodar

A página não precisa de nada instalado — basta abrir `web/index.html` no
navegador.

O backend:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

## Testes

```bash
python3 tests/test_paridade.py
```

Roda os dois motores sobre os mesmos 400 casos e falha se qualquer campo
divergir. Os casos pousam em cima dos limites de faixa de `H45` e nos empates de
`ROUND(...; 4)` — onde 0,0001 na média ponderada vale 25 pontos percentuais de
bônus. **Mudou a regra, mudam os dois motores, e este teste roda antes de
publicar.**

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
  "cota_resultado": 1.0,
  "cota_alem_resultado": 0.25,
  "cota_equidade": 1.0,
  "cota_elementares": 0.0,
  "cota_participacao": 0.5,
  "etapas": [ "..." ],
  "memoria_calculo": [ "..." ],
  "alertas": [ "..." ],
  "aviso_legal": "..."
}
```

`memoria_calculo` reproduz a cadeia `B21 → H47 → H45 → B40/B41 → C45` em
linguagem natural. `alertas` traduz os platôs da fórmula em orientação — é o que
evita que o gestor supere a meta e não veja diferença no bônus.

## Três leituras da regra que o frontend precisa comunicar

Levantadas da tabela-verdade completa ([`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md) §6):

1. **300% só existe em uma combinação**: IDEPE de 200% + as duas metas de
   equidade + participação. Não há degraus entre 250% e 300%.
2. **IDEPE acima de 100% é irrelevante** fora dessa combinação: 125%, 150%, 175%
   e 200% rendem a mesma cota que 100%.
3. **Ter as duas metas de equidade vale o mesmo que ter uma só**, exceto naquela
   combinação — a fórmula usa `OR`, não soma.

## Estrutura

```
web/index.html         página publicável — wizard + motor em JavaScript
main.py                aplicação FastAPI e CORS
src/bde/schemas.py     contrato de entrada e saída (Pydantic)
src/bde/service.py     motor de cálculo — reprodução de H45, H47 e C45
src/bde/router.py      POST /api/v1/simular-bde
tests/test_paridade.py paridade entre o motor Python e o motor JavaScript
```

## Documentação

- [`docs/EXTRACAO_PLANILHA.md`](docs/EXTRACAO_PLANILHA.md) — auditoria célula a
  célula, fórmulas mortas, divergências e a tabela-verdade de conferência.
- [`docs/CAMINHOS_RUINS.md`](docs/CAMINHOS_RUINS.md) — rotas de uso que quebram
  a solução, com o estado de cada uma.
- [`docs/GOOGLE_SITES.md`](docs/GOOGLE_SITES.md) — o que muda para publicar no
  Google Sites e o passo a passo.
