# Extração da planilha — `Simulador_Idepe_e_Atingimento_de_metas_2026.xlsx`

Auditoria célula a célula da pasta de trabalho do Núcleo da SEPLAG/PE que
originou este projeto. Este documento é a **fonte de verdade** do backend:
toda constante em `src/bde/` deve ser rastreável até uma célula listada aqui.

## 1. Abas

| Aba | Papel | Entra no backend? |
|---|---|---|
| **Simulador BDE** | Cálculo da cota do BDE. É o núcleo do produto. | **Sim** |
| Simulador IDEPE | Calcula o IDEPE a partir de aprovação por ano e proficiências LP/MT. | Não nesta etapa |
| Simulador Ideb | Idêntico ao anterior, com as padronizações do SAEB. | Não nesta etapa |
| Matrículas 2025 | Tabela de 1.066 escolas: `CO_ENTIDADE`, escola, município, matrículas AI/AF/EM. | Não (ver Caminhos Ruins, §C4) |
| Cenário Validado | Vazia no arquivo entregue (`A1:C4`, todas as células nulas). | Não |

O gestor informa meta e resultado já prontos; as abas IDEPE/Ideb são
calculadoras auxiliares e ficam fora do escopo deste backend.

## 2. Variáveis de entrada (células amarelas)

As células de preenchimento estão marcadas em amarelo (`FFFFFF00`) e têm
validação de dados nativa do Excel. Os limites abaixo foram lidos do XML.

| Célula | Variável | Tipo | Validação na planilha | Campo no `RequestSchema` |
|---|---|---|---|---|
| B6 | Matrículas Anos Iniciais | inteiro | 8 a 50.000, vazio = etapa não avaliada | `etapa_anos_iniciais.matriculas` |
| B7 | Matrículas Anos Finais | inteiro | 8 a 50.000, vazio = etapa não avaliada | `etapa_anos_finais.matriculas` |
| B8 | Matrículas Ensino Médio | inteiro | 8 a 50.000, vazio = etapa não avaliada | `etapa_ensino_medio.matriculas` |
| B19 | Meta IDEPE EFAI 2025 | decimal | 1,5 a 9,2 | `etapa_anos_iniciais.meta` |
| B20 | IDEPE EFAI 2025 | decimal | 1,9 a 9,2 | `etapa_anos_iniciais.resultado` |
| B27 | Meta IDEPE EFAF 2025 | decimal | 1,5 a 9,2 | `etapa_anos_finais.meta` |
| B28 | IDEPE EFAF 2025 | decimal | 1,9 a 9,2 | `etapa_anos_finais.resultado` |
| B35 | Meta IDEPE Ens. Médio 2025 | decimal | 1,5 a 9,2 | `etapa_ensino_medio.meta` |
| B36 | IDEPE Ens. Médio 2025 | decimal | 1,9 a 9,2 | `etapa_ensino_medio.resultado` |
| D12 | Equidade PPI + NSE | lista `SIM`/`NÃO`/vazio | `$H$2:$H$4` | `reduziu_desigualdade` |
| D13 | 1º terço de elementares | lista `SIM`/`NÃO`/vazio | `$H$2:$H$4` | `terco_menor_elementares` |
| — | Participação ≥ 80% no SAEPE | — | **não existe na planilha** | `participacao_minima_atingida` |

Decisões tomadas na transcrição para o Pydantic:

- **Piso único 1,5 para meta e resultado.** A planilha exige 1,9 no resultado e
  1,5 na meta. Rejeitar um IDEPE legitimamente baixo (1,7) é pior do que
  aceitar a faixa mais larga, então adotamos 1,5 nos dois campos.
- **Etapa é um bloco atômico.** Ver §5, item 3.
- **Participação é booleana, não uma taxa.** A exigência é "≥ 80% em todos os
  componentes e em todas as etapas". Um único número (`taxa_participacao:
  float`) não consegue representar isso — uma escola com 95% em Língua
  Portuguesa e 60% em Matemática não atende, e a média mentiria. A pergunta
  fechada é a única representação honesta, e mantém coerência com D12/D13.

## 3. Fórmulas do cálculo

```
B21 = IF(AND(B19<>"",B20<>""), B20-B19, "")      diferença AI (idem B29, B37)

H47 = ROUND( SUMPRODUCT(matrículas; diferenças) / SUM(matrículas) ; 4 )
      média ponderada das diferenças pelas matrículas

H45 = tabela de conversão de H47 em percentual (grade E42:M43)
B40 = IF(H45>1; 1; H45)                          cota resultado
B41 = MAX(H45 - B40; 0)                          cota além do resultado
B42 = IF(D12="SIM"; 1; 0)                        cota equidade
B43 = IF(D13="SIM"; 1; 0)                        cota elementares
B44 = 0,5                                        cota participação (CONSTANTE)

C45 = IF(AND(B40=1; B41=1; B42=1; B43=1); 2,5;
      IF(AND(B40<=1; OR(B42=1; B43=1)); 1+B40;
      IF(AND((B40+B41)>1; OR(B42=1; B43=1)); 2;
      B40))) + B44
```

Grade de conversão declarada em `E42:M43`:

| Faixa (E42:M42) | -0,3 | -0,3 | -0,2 | -0,1 | 0 | 0,1 | 0,2 | 0,3 | 0,4 |
|---|---|---|---|---|---|---|---|---|---|
| Percentual (E43:M43) | 0% | 25% | 50% | 75% | 100% | 125% | 150% | 175% | 200% |

Teto: `C45` chega no máximo a `2,5 + 0,5 = 3,0` (300%), coerente com a regra
de negócio.

## 4. Células mortas (não portar)

| Célula | Conteúdo | Diagnóstico |
|---|---|---|
| H7 | Tabela de conversão paralela, lendo `J5:M6`, que só vai até 100% | Versão anterior de H45, sobreposta e não referenciada por C45. |
| H9:I11, J9 | Segunda média ponderada, idêntica a H15:I17/H47 | Duplicata. C45 usa a cadeia H15:I17 → H47. |
| H37 | `=IFERROR(#REF!/#REF!;"")` | Referência quebrada. |
| I45 | `=IF(H47<0,7;0;IF(H47=">0,7"&"<0,8";80;2))` | Compara número com texto; nunca retorna 80. Rascunho abandonado. |

## 5. Divergências entre a planilha e as regras de negócio declaradas

Três achados. O primeiro é decisivo e precisa de decisão de negócio antes de
escrevermos o `BDECalculatorService`.

### 5.1 `C45` não trata os bônus como cumulativos — SUPERADO no BDE 2027

> **Nomenclatura.** "BDE 2027" é o bônus pago em 2027, calculado com os
> resultados de 2026: metas 2026, matrículas 2026, SAEPE 2026, e os quesitos de
> equidade comparando 2026 com 2025. "BDE 2026" é a regra anterior, a que a
> planilha `Simulador_Idepe_e_Atingimento_de_metas_2026.xlsx` implementa.

**Registro histórico. Esta seção descreve a regra até o BDE 2026.**

A fórmula `C45` usava `OR(B42=1; B43=1)`: ter as duas condições de equidade
valia o mesmo que ter uma só, exceto no caso único em que o IDEPE era
exatamente 200%. `B41` era descartada no caminho normal. Divergiam 20 das 28
combinações em relação à regra declarada, que dizia "independentes e
cumulativos".

A decisão de então foi **reproduzir a planilha**, por ser mecanismo já validado
e em uso na SEPLAG.

**No BDE 2027 a regra passou a somar**, por determinação do gestor da regra:
cada quesito de equidade atingido vale +100%, os dois valem +200%, e isso vale
para toda escola — inclusive a que não atingiu os 80% de participação e ficou
sem IDEPE. A `C45` e seus quatro ramos saíram do código.

**A consequência precisa estar clara para quem atende o gestor:** a planilha em
circulação e o simulador passam a divergir de propósito. Uma escola com IDEPE
de 100% e os dois quesitos de equidade vê 250% na planilha e 300% aqui. Quem
manda é a regra do BDE 2027; a planilha é que está desatualizada.

O total passou a ser:

```python
cota_resultado = min(percentual_idepe, 1.0)
cota_bde = cota_resultado + (1.0 se equidade) + (1.0 se elementares)
percentual_bde = min(cota_bde + (0.5 se alguma etapa com 80%), 3.0)
```

Registro do que ficou para trás: o 3º ramo da `C45` (`(B40+B41)>1 → 2`) era
**inalcançável e redundante** — inalcançável porque `B40` é `min(H45; 1)`, logo
`B40<=1` era sempre verdadeiro e o 2º ramo capturava antes; redundante porque,
se fosse alcançado, devolveria `2`, o mesmo que `1+B40` com `B40=1`.

### 5.1-b A participação virou portão, e é por etapa — NOVO no BDE 2027

Até o BDE 2026 a participação era uma pergunta única da escola e apenas somava
`B44` (+50%). No BDE 2027 ela é perguntada **por etapa** e decide se a etapa
tem IDEPE:

- Etapa sem 80% não tem IDEPE divulgado. Não se pergunta meta nem resultado
  dela, e ela entra na conta com **0% de atingimento**, pesando pelas suas
  matrículas.
- A média ponderada (`H47`) roda **só entre as etapas aprovadas**, porque só
  elas têm variação. O percentual convertido é então reduzido na proporção das
  matrículas que ficaram de fora.
- O +50% continua existindo e basta **uma** etapa atingir os 80% para a escola
  somá-lo.

A ordem importa: a diluição acontece **depois** da conversão, não antes. Uma
etapa sem meta e sem resultado não tem variação para entrar no `H47`. Com essa
ordem, escola com todas as etapas aprovadas devolve exatamente o mesmo
`percentual_idepe` do ciclo anterior — a regressão está travada em
`tests/test_cenarios.py`, cenário F.

### 5.2 Buraco na faixa (−0,3; −0,2) em `H45` — DECIDIDO: ler a grade

`H45` começa com `IF(H47 < -0,3; 0; IF(H47 <= -0,3; 0,25; IF(H47 < -0,2; 0; …`.
O terceiro teste devolve **0%** para qualquer diferença estritamente entre
−0,3 e −0,2; só a igualdade exata a −0,3 rende 25%.

A grade de consulta da mesma planilha (`E42:M43`) traz `0,25` embaixo de
`−0,3`, e as outras oito faixas usam `≥ limite inferior`. As duas leituras da
planilha se contradizem: é a escada de IFs que lê a própria grade errado.

**Decisão: ler a grade** — a faixa inteira `[−0,3; −0,2)` vale 25%. É o que o
simulador em uso no NGR-SEE sempre fez (`_converter()` do `BDE-Interface`, uma
busca binária na tabela de faixas), e manter o simulador web divergindo dele
produziria 0% onde o sistema em circulação produz 25%, para a mesma escola.

Uma versão anterior deste repositório reproduzia o buraco. Foi revertido: o
critério aqui é não divergir do mecanismo já validado e em uso.

**Continua valendo levar o ponto ao Núcleo da SEPLAG** (Zaplag
(81) 98494-4837, nota 6 da planilha) para que a escada de IFs da planilha seja
corrigida — enquanto ela existir, a planilha e o simulador darão respostas
diferentes nessa faixa, e a diferença é de 25 pontos percentuais de bônus.

### 5.3 A cota de participação não é condicional na planilha

`B44` é a constante `0,5`, somada incondicionalmente — a planilha não pergunta
sobre participação. A regra de negócio deste produto torna essa cota
condicional a participação ≥ 80% no SAEPE, o que introduz um resultado novo que
a planilha não consegue produzir: `0%`. O campo `apto_a_receber` existe para
esse caso.

Registro de contexto: no ciclo anterior (BDE 2025, sobre resultados de 2024) a
cota adicional por participação ≥ 80% foi de **25%**, não 50%. O percentual muda
entre ciclos — daí `COTA_PARTICIPACAO` ser constante nomeada em `service.py`.

## 6. Tabela-verdade — referência de conferência manual

Saída de `C45` para as 9 faixas de IDEPE × equidade × elementares. A coluna
final já inclui a cota de participação; sem participação, subtraia 50 pontos.
É contra esta tabela que o motor Python foi conferido (36/36).

| IDEPE | Sem bônus | Um bônus | Dois bônus | Com participação (dois bônus) |
|---|---|---|---|---|
| 0% | 0% | 100% | 100% | 150% |
| 25% | 25% | 125% | 125% | 175% |
| 50% | 50% | 150% | 150% | 200% |
| 75% | 75% | 175% | 175% | 225% |
| 100% | 100% | 200% | 200% | 250% |
| 125% | 100% | 200% | 200% | 250% |
| 150% | 100% | 200% | 200% | 250% |
| 175% | 100% | 200% | 200% | 250% |
| 200% | 100% | 200% | **250%** | **300%** |

Três leituras que o produto precisa comunicar:

1. **300% só existe em uma combinação**: IDEPE de 200% + as duas metas de
   equidade + participação. Não há valores entre 250% e 300%.
2. **IDEPE acima de 100% é irrelevante** fora dessa combinação: 125%, 150%,
   175% e 200% rendem a mesma cota que 100%.
3. **Ter os dois bônus vale o mesmo que ter um só**, exceto naquela combinação.

Cotas distintas possíveis em `C45`: 0%, 25%, 50%, 75%, 100%, 125%, 150%, 175%,
200% e 250%.
