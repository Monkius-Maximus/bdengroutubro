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

### 5.1 `C45` não trata os bônus como cumulativos (BLOQUEANTE)

A regra declarada diz "duas condições extras que adicionam bônus de forma
**independente**, cumulativas até o teto". A fórmula usa `OR(B42=1; B43=1)`:
**ter as duas condições vale o mesmo que ter uma só**, exceto no caso único em
que o IDEPE é exatamente 200%.

Além disso, `B41` (cota além do resultado) é **descartada** no caminho normal:
um IDEPE de 200% sem nenhum bônus resulta em 150%, o mesmo que 100% sem bônus.
O 3º ramo (`1+B41 > 1 → 2`), que corrigiria isso, é **código morto**: `B40` é
`min(H45; 1)` e portanto `B40<=1` é sempre verdadeiro, de modo que o 2º ramo
captura todos os casos antes.

Comparação exaustiva (já somada a cota de participação de 50%):

| IDEPE | Equidade | Elementares | Planilha (C45) | Cumulativo (regra declarada) |
|---|---|---|---|---|
| 0% | Não | Não | 50% | 50% |
| 0% | Sim | Sim | 150% | **250%** |
| 50% | Sim | Sim | 200% | **300%** |
| 75% | Sim | Sim | 225% | **300%** |
| 100% | Sim | Não | 250% | 250% |
| 100% | Sim | Sim | 250% | **300%** |
| 125% | Não | Não | **150%** | 175% |
| 150% | Não | Não | **150%** | 200% |
| 200% | Não | Não | **150%** | 250% |
| 200% | Sim | Não | 250% | **300%** |
| 200% | Sim | Sim | 300% | 300% |

Divergem 20 das 28 combinações possíveis. **O código hoje no repositório
(`service.py`) implementa a coluna "Cumulativo"** — ou seja, hoje ele não
reproduz a planilha.

### 5.2 Buraco na faixa (−0,3; −0,2) na fórmula `H45`

`H45` começa com `IF(H47 < -0,3; 0; IF(H47 <= -0,3; 0,25; IF(H47 < -0,2; 0; …`.
O terceiro teste devolve **0%** para qualquer diferença estritamente entre
−0,3 e −0,2; só a igualdade exata a −0,3 rende 25%.

| Diferença | H45 (planilha) | Regra declarada |
|---|---|---|
| −0,30 | 25% | 25% |
| −0,29 | **0%** | 25% |
| −0,25 | **0%** | 25% |
| −0,21 | **0%** | 25% |
| −0,20 | 50% | 50% |

Como `H47` é arredondado a 4 casas, cair exatamente em −0,3 é raro em escolas
com mais de uma etapa. Na prática, a planilha zera a bonificação de escolas que
ficaram pouco abaixo da meta. Isso é um erro de digitação da fórmula, não uma
regra: o padrão `≥ limite inferior` vale para todas as outras oito faixas.
**Recomendação: seguir a regra declarada.**

### 5.3 A cota de participação não é condicional na planilha

`B44` é a constante `0,5`, somada incondicionalmente — a planilha não pergunta
sobre participação. A regra de negócio deste produto torna essa cota
condicional a participação ≥ 80% no SAEPE, o que introduz um resultado novo
que a planilha não consegue produzir: `0%` (IDEPE zerado, sem bônus, sem
participação). O campo `apto_a_receber` existe justamente para esse caso.

Registro de contexto: no ciclo anterior (BDE 2025, sobre resultados de 2024) a
cota adicional por participação ≥ 80% foi de **25%**, não 50%. O percentual
muda entre ciclos e precisa ser uma constante nomeada e versionada, nunca um
literal espalhado pelo serviço.

## 6. Decisão pendente

Para o `BDECalculatorService` a pergunta é uma só:

> **O simulador web deve reproduzir `C45` fielmente (inclusive o `OR` e o ramo
> morto), ou implementar a regra cumulativa declarada?**

- **Fidelidade à planilha** — o gestor confere os dois e bate. Mas replicamos
  um comportamento que contradiz a norma e penaliza escolas de alto desempenho.
- **Regra cumulativa** — coerente com o texto normativo, porém o simulador web
  passa a dizer 300% onde a planilha diz 200%, e a SEPLAG recebe contestações.

Não é uma decisão de engenharia. Recomendamos levar a §5.1 ao Núcleo da SEPLAG
(Zaplag (81) 98494-4837, contato da nota 6 da planilha) antes de codificar.
Qualquer que seja a resposta, a fórmula escolhida deve ficar isolada em uma
única função, com a tabela acima como teste de regressão.
