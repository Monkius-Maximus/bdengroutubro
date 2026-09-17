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

### 5.1 `C45` foi REJEITADA como regra de cálculo

Histórico da decisão, porque ela mudou:

1. A auditoria mostrou que `C45` combina os bônus com `OR` e diverge da regra
   de negócio declarada em 20 das 28 combinações.
2. Decidiu-se reproduzir `C45`, por ser mecanismo já em uso e validado.
3. O slide oficial **"CENÁRIO DE METAS 2025 — BDE 2026"**, com os quatro
   cenários narrados pela área de negócio, mostrou que `C45` **não descreve a
   regra que a SEPLAG comunica às escolas**. Decisão revertida.

A aritmética que fecha a questão é o exemplo do próprio material: uma escola que
supera a meta e atinge os dois objetivos bônus somaria `175 + 100 + 100 = 375`,
"cortado em 300". O número **375 só existe se os bônus somarem**. Em `C45` esse
mesmo caso dá 200% — 375 nunca chega a se formar, porque a fórmula usa `OR`.

| Cenário oficial | Regra oficial | `C45` | Modelo adotado |
|---|---|---|---|
| Abaixo de −0,3, sem bônus | 0% | 0% | 0% |
| Abaixo da meta + os dois bônus | até 200% | 100% ✗ | 200% |
| Atingiu a meta + os dois bônus | até 300% | 200% ✗ | 300% |
| Passou da meta + os dois bônus | 300%, não 375% | 200% ✗ | 300% |

**Regra em vigor:**

```
total = min(atingimento + equidade + elementares + participação, 300%)
```

`C45` passa a ser tratada como bug de um simulador auxiliar, não como norma.
As células `B40` (cota resultado) e `B41` (cota além do resultado) não têm
equivalente no modelo adotado e saíram do contrato da API: no modelo cumulativo
o atingimento entra inteiro na soma, sem ser partido em 100%.

### 5.2 Buraco na faixa (−0,3; −0,2) — RESOLVIDO

`H45` devolve 0% para diferenças estritamente entre −0,3 e −0,2, e só a
igualdade exata a −0,3 rende 25%. Chegou a ser reproduzido por fidelidade.

O material oficial encerra a dúvida em duas frentes: o slide traz
`≥ −0,3 → 25%`, e o texto da área de negócio diz que "aqueles que ficarem
**abaixo** de 0,3 décimos não receberão". Confirma-se o erro de digitação na
escada de IFs, que lia errado a própria grade `E42:M43` da planilha. A escala
implementada usa `≥ limite inferior` em todos os degraus.

### 5.3 A planilha tem um degrau a mais que o slide — REMOVIDO

A grade `E42:M43` tem 9 degraus e termina em `≥ 0,4 → 200%`. O slide tem 8 e
termina em `≥ 0,3 → 175%`, e o texto oficial diz "0,3 **ou mais** = 175%".

Adotados os 8 degraus do slide. O teto do atingimento é **175%**, e `≥ 0,3` é
degrau terminal. Registro para reavaliação: a faixa azul do slide diz "O IDEB e
o Bônus", e a pasta tem abas separadas para IDEB e IDEPE — se as duas escalas
diferirem de fato, este é o ponto a revisitar.

### 5.4 A cota de participação não existe na planilha

`B44` é a constante `0,5`, somada incondicionalmente. O slide não menciona
participação. A regra do projeto a mantém condicional a participação ≥ 80% em
todos os componentes e etapas do SAEPE, valendo +50%, e é assim que está
implementada.

No ciclo anterior (BDE 2025, resultados de 2024) essa cota foi de **25%**. O
percentual muda entre ciclos — daí `COTA_PARTICIPACAO` ser constante nomeada.

## 6. Tabela-verdade — referência de conferência manual

Total do BDE por atingimento × objetivos bônus × participação. Máximo somável:
`175 + 100 + 100 + 50 = 425%`, sempre cortado em 300%.

| Atingimento | sem bônus | + partic. | 1 bônus | + partic. | 2 bônus | + partic. |
|---|---|---|---|---|---|---|
| 0% | 0% | 50% | 100% | 150% | 200% | 250% |
| 25% | 25% | 75% | 125% | 175% | 225% | 275% |
| 50% | 50% | 100% | 150% | 200% | 250% | 300% |
| 75% | 75% | 125% | 175% | 225% | 275% | 300% |
| 100% | 100% | 150% | 200% | 250% | 300% | 300% |
| 125% | 125% | 175% | 225% | 275% | 300% | 300% |
| 150% | 150% | 200% | 250% | 300% | 300% | 300% |
| 175% | 175% | 225% | 275% | 300% | 300% | 300% |

Três leituras que o produto precisa comunicar:

1. **Os objetivos bônus valem mais que o desempenho na meta.** Sair de 0% para
   175% de atingimento rende 175 pontos; atingir os dois objetivos bônus rende
   200. Uma escola abaixo da meta com os dois bônus (200%) supera uma escola que
   passou da meta sem nenhum (175%).
2. **O teto corta com frequência.** Qualquer escola que atinja a meta e os dois
   objetivos já soma 300% — participação e desempenho extra não acrescentam
   nada além disso.
3. **`≥ 0,3` é degrau terminal.** Superar a meta em 0,3 ou em 1,2 dá o mesmo
   atingimento de 175%.
