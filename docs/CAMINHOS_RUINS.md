# Caminhos Ruins

Rotas e ações que um usuário (ou nós mesmos) pode querer tomar e que quebram um
simulador como este. Cada item traz o que acontece e a mitigação adotada ou
recomendada.

Legenda de estado: **[Mitigado]** já tratado no código · **[Aberto]** ainda não
tratado · **[Decisão]** exige decisão de negócio.

---

## A. Entrada de dados

### A1. Informar matrículas de uma etapa sem informar meta e resultado — [Mitigado]
Na planilha, matrículas (B6:B8) e metas (B19/B27/B35) são blocos separados. Uma
escola que digita 500 matrículas nos Anos Iniciais mas só preenche meta e
resultado do Ensino Médio entra em `H47` com peso 500 e diferença zero: o
resultado do Ensino Médio é diluído silenciosamente, sem nenhum aviso.

*Mitigação:* `EtapaIDEPE` exige `matriculas`, `meta` e `resultado` juntos. A
etapa ou é avaliada por inteiro, ou não existe no payload. O wizard deve
perguntar "esta etapa foi pactuada?" antes de pedir os números.

### A2. Não informar nenhuma etapa — [Mitigado]
`SUM(matrículas)` seria zero e a média ponderada dividiria por zero. A planilha
mascara com `IFERROR` e devolve célula vazia, o que o gestor lê como "ainda
estou preenchendo".

*Mitigação:* `model_validator` exige ao menos uma etapa e devolve 422 dizendo
que escola sem meta pactuada não é elegível ao BDE — que é a informação que o
gestor precisa, e não um campo em branco.

### A3. Trocar meta e resultado de campo — [Mitigado]
Digitar 4,5 em "resultado" e 4,7 em "meta" inverte o sinal da diferença e pode
levar de 125% para 75%. Nenhuma validação detecta isso: ambos são IDEPEs
plausíveis.

*Mitigação parcial:* o passo "Resumo das Informações" mostra, por etapa,
`Meta | Resultado | Variação` com fundo verde ou vermelho, antes de o gestor ver
o resultado. A inversão fica visível ali — mas só depois de preencher tudo,
não no momento da digitação. Nenhuma validação de faixa a pegaria, porque os
dois números são IDEPEs plausíveis.

### A4. Digitar o IDEPE em escala errada — [Mitigado]
`45` no lugar de `4,5`, ou a taxa de aprovação (`85`) no lugar do índice.

*Mitigação:* faixa 1,5 a 9,2, lida da validação de dados da planilha.

### A5. Enviar decimal com vírgula — [Mitigado]
O gestor digita `4,7`. Em JSON isso vira a string `"4,7"`, e o Pydantic rejeita
com uma mensagem em inglês sobre parsing de float.

*Mitigação:* os campos são `<input type="number" step="0.01">`. Em navegador
com locale pt-BR isso aceita vírgula e entrega ponto para o `parseFloat`, e o
teclado do celular já abre numérico. O motor só recebe número.

### A6. Usar matrículas do ano errado — [Mitigado]
A ponderação é pelas **matrículas de 2025**, não pelas do ano corrente. Uma
escola que cresceu ou encolheu muda o peso relativo entre etapas e altera a
faixa final.

*Mitigação:* o campo se chama "Matrículas 2026", dizendo de que ano é o dado.

### A7. Usar o IDEB no lugar do IDEPE — [Aberto]
A pasta tem duas abas de cálculo com padronizações diferentes (AI: `(LP-49)/275`
no IDEPE contra as constantes do SAEB no IDEB). Os dois índices têm a mesma
ordem de grandeza, então o número passa em qualquer validação de faixa e produz
um resultado errado sem nenhum sinal.

*Mitigação parcial:* os campos se chamam "Meta IDEPE" e "Resultado IDEPE", o
que já orienta. Falta o aviso explícito de que **não** é IDEB/SAEB — que é o
erro que nenhuma validação de faixa detecta.

### A8. Arredondamento na borda de faixa — [Mitigado]
`H47` é arredondado a 4 casas. Uma diferença de 0,09999 dá 100%; 0,1 dá 125%.
A distância entre duas telas do wizard pode valer 25 pontos percentuais.

*Mitigação:* `arredondar_excel()` replica o `ROUND(...; 4)` da planilha, que é
metade-para-longe-do-zero — o `round()` do Python é bancário e cairia na faixa
errada em `0,09995`. E o ponderador usa as diferenças **cruas**, arredondando
só o quociente, como faz `H47`. Quando a média fica a menos de 0,01 da próxima
faixa, entra um item em `alertas`.

O empate, porém, não sobrevive à subtração em ponto flutuante: `4,59995 − 4,5`
não dá `0,09995`, dá `0,09994999999999976`, que arredondaria para `0,0999` e
devolveria 100% onde a planilha devolve 125%. Por isso o valor passa antes por
um corte em 12 dígitos significativos, que descarta o resíduo binário sem tocar
em nenhum dígito digitado pelo gestor. Regressão coberta por
`tests/test_paridade.py`.

---

## B. Interpretação da regra

### B1. Assumir que os bônus NÃO são cumulativos — [Invertido no ciclo 2026]
Até o ciclo 2025 valia o contrário: a `C45` usava `OR` e ter os dois quesitos de
equidade valia o mesmo que ter um só. **No ciclo 2026 os quesitos somam**: cada
um vale +100%, os dois valem +200%.

*O caminho ruim agora é o inverso* — repetir para o gestor a explicação antiga,
ou comparar o resultado com a planilha em circulação, que ainda usa `OR`. Uma
escola com IDEPE de 100% e os dois quesitos vê 250% na planilha e 300% aqui.

*Mitigação:* `EXTRACAO_PLANILHA.md` §5.1 registra a mudança e a divergência
proposital com a planilha. `tests/test_cenarios.py` trava o cenário D, que é
exatamente esse caso.

### B2. Esperar que desempenho acima da meta sempre aumente a cota — [Mitigado]
Em `C45`, `B41` (cota além do resultado) é descartada no caminho normal. Sem
bônus, 200% de IDEPE rende exatamente o mesmo que 100%. É o caminho mais
provável de contestação: a escola que mais superou a meta não vê diferença.

*Mitigação:* `cota_alem_resultado` continua exposta na resposta e o popup da
"Cota Resultado" diz, em palavras, que o excedente não entra na soma. O ciclo
2026 não mudou isso: a cota de resultado segue limitada a 100%.

### B2b. Prometer valores intermediários que a regra não produz — [Mitigado]
A regra produz um conjunto pequeno de valores distintos, e um texto do tipo
"faltam 20% para o teto" inventa uma granularidade que não existe. No ciclo 2026
há um platô novo: a soma é travada em 300%, então combinações diferentes exibem
o mesmo 300% — IDEPE de 100% com os dois quesitos e participação dá 350% antes
do teto, e o gestor não vê diferença se melhorar.

*Mitigação:* os `alertas` dizem a condição exata e completa do teto (IDEPE de
200% + as duas metas de equidade + participação), em vez de uma distância. A
barra de progresso mede **passos do formulário** ("Passo 3 de 8"), nunca
proximidade do teto — são coisas diferentes e a rotulagem explicita qual delas
está na tela.

### B2c. Orientar a escola a "superar mais a meta" — [Mitigado]
Conselho intuitivo e quase sempre inútil: acima de 100% de IDEPE a cota de
resultado não muda mais. Uma escola em 125% ganha muito mais perseguindo um
quesito de equidade (+100 pontos) do que subindo o IDEPE. No ciclo 2026 isso
ficou mais forte, porque os dois quesitos somam +200.

*Mitigação:* o popup da "Cota Resultado" diz que o excedente não entra na soma.

### B3. Tratar a participação como só um bônus — [Invertido no ciclo 2026]
Até o ciclo 2025 a participação era apenas uma cota adicional de 50%, e o
caminho ruim era chamá-la de eliminatória. **No ciclo 2026 ela é as duas
coisas**, e por etapa:

- **Portão:** etapa sem 80% não tem IDEPE divulgado e entra com 0% de
  atingimento, pesando pelas matrículas.
- **Bônus:** basta uma etapa atingir os 80% para a escola somar +50%.

*O caminho ruim agora é dizer que a escola "perde tudo" sem participação.* Ela
não perde: os quesitos de equidade continuam valendo, e uma escola sem nenhuma
participação ainda chega a 200% se atingir os dois. Só chega a 0% quem não
atinge nem participação nem equidade.

*Mitigação:* `participacao_maior_80` é campo de `EtapaIDEPE`, não da requisição,
e um `model_validator` recusa meta e resultado em etapa que não participou —
IDEPE não divulgado não entra por engano.

### B4. Fixar 50% como o valor eterno da cota de participação — [Mitigado]
No ciclo BDE 2025 (resultados de 2024) essa cota foi de **25%**. O percentual
muda entre ciclos.

*Mitigação:* `COTA_PARTICIPACAO`, `COTA_EQUIDADE` e `COTA_ELEMENTARES` são
constantes nomeadas no topo de `service.py`, com o registro do valor do ciclo
anterior. Nenhum literal `0.5` espalhado pelo serviço.

### B5. Esperar o valor em reais — [Mitigado]
O gestor vai perguntar "quanto eu vou receber?". O simulador só produz o
**percentual de atingimento**. O valor depende de salário-base, cargo e meses de
vínculo na escola no ano de referência — nada disso está na planilha.

*Mitigação:* `aviso_legal` na resposta diz isso explicitamente.

### B6. Tratar a simulação como resultado oficial — [Mitigado]
A nota 1 da planilha é clara: "os resultados apresentados não são oficiais".
Em uma versão web, com URL do governo e visual institucional, a chance de ser
lida como oficial é muito maior do que em um `.xlsx` circulando por WhatsApp.

*Mitigação:* `aviso_legal` é campo obrigatório da resposta, com default fixo —
não dá para o frontend receber um payload sem ele.

### B7. Portar as fórmulas mortas da planilha — [Mitigado]
`H7`, `J9`, `H37` (`#REF!`) e `I45` são rascunhos sobrepostos. Portá-los por
fidelidade criaria caminhos alternativos para o mesmo cálculo.

*Mitigação:* catalogados como mortos em `EXTRACAO_PLANILHA.md` §4.

---

## C. Produto e escopo

### C1. Wizard com estado parcial chegando ao backend — [Mitigado]
O usuário volta duas telas, muda a resposta e o frontend envia um payload
meio montado.

*Mitigação:* o backend é stateless e valida o payload completo de uma vez. A
montagem incremental é responsabilidade do frontend. O 422 do Pydantic aponta o
campo exato.

### C2. Router engolindo exceções — [Mitigado]
`router.py` tem `except Exception` convertendo qualquer erro em 422. Um bug de
divisão por zero vira "erro de validação" para o usuário e some do log.

*Mitigação:* `try/except` removido. O `RequisicaoBDE` já garante as
pré-condições e devolve 422 apontando o campo; o que passar dele e quebrar vira
500 com stack trace, como deve.

### C3. `allow_origins=["*"]` em produção — [Aberto]
Aceitável em desenvolvimento; em produção permite que qualquer site incorpore o
simulador e o apresente como oficial.

*Mitigação recomendada:* lista de origens por variável de ambiente. Deixou de
ser urgente quando a página passou a calcular no navegador: o site publicado não
chama o backend, então o CORS liberado só expõe uma API que ninguém precisa
consumir.

### C4. "Busque as matrículas pelo código INEP" — [Aberto]
A aba `Matrículas 2025` tem 1.066 escolas com `CO_ENTIDADE`, nome, município e
matrículas. É tentador embutir isso e poupar digitação.

*Por que é um caminho ruim:* congela no código um recorte de um ano específico,
que passa a precisar de manutenção anual; transforma o simulador em publicador
de uma base de escolas; e cria uma segunda fonte de verdade para as matrículas
(a embutida e a digitada), divergindo da planilha na virada do ano.

*Se for feito mesmo assim:* dado externo versionado, com data de referência
visível e o campo permanecendo editável.

### C5. "Salve minha simulação" / "compartilhe meu resultado" — [Aberto]
Pedido natural, e o primeiro que transforma um calculador stateless em
aplicação com banco, autenticação e retenção de dados.

*Mitigação recomendada:* se precisar existir, codificar o payload na própria
URL. Nada persistido no servidor, nada para vazar.

### C6. Pedir dados pessoais do servidor — [Aberto]
CPF, matrícula funcional ou nome não entram em nenhuma fórmula. Coletá-los
"para depois" traz LGPD para dentro de um simulador anônimo sem nenhum ganho.

*Mitigação recomendada:* manter o simulador anônimo. Se o dado não entra na
conta, não é pedido.

### C7. Duplicar a tabela de conversão no frontend — [Decisão]
Reimplementar a conversão em JavaScript cria duas fontes de verdade, que
divergem no primeiro ajuste de regra.

*Decisão:* a duplicação foi aceita, porque o destino é o Google Sites — que é
hospedagem estática e não roda o FastAPI (ver `GOOGLE_SITES.md`). Sem servidor,
ou a regra vive no navegador ou não existe página.

*Mitigação:* `tests/test_paridade.py` roda os dois motores sobre os mesmos 400
casos e falha se qualquer campo divergir. Os casos pousam em cima dos limites de
faixa de `H45` e nos empates de `ROUND(...; 4)`, que é onde uma reimplementação
erra primeiro. O teste já pegou uma divergência real: o resíduo de ponto
flutuante descrito em A8, que estava **no Python**.

*Condição:* mudou a regra, mudam os dois motores, e o teste roda antes de
publicar. Um motor alterado sozinho é um bug não detectado até alguém contestar
o próprio bônus.

### C8. Ler o `.xlsx` em tempo de execução — [Aberto]
Usar a planilha como fonte de dados em produção acopla o serviço a um arquivo
binário que qualquer pessoa pode reeditar, e carrega junto as fórmulas mortas e
os erros de borda.

*Mitigação recomendada:* a planilha é **especificação**, não dependência. As
regras foram transcritas para código e auditadas em `EXTRACAO_PLANILHA.md`.

### C9. Renomear campos do schema sem o frontend no repositório — [Mitigado]
O commit que realinhou os schemas trocou `bonus_equidade` por `cota_equidade`,
`participacao_maior_80` por `participacao_minima_atingida`, `etapa_ai` por
`etapa_anos_iniciais` e `variacao` por `diferenca`. O frontend vivia em outro
lugar e não acompanhou: passou a mandar um payload que o backend recusa com 422
e a ler campos que voltam `undefined`, exibindo `NaN%` nos cartões.

*Mitigação:* a interface passou a morar no mesmo repositório, e
`tests/test_paridade.py` compara os dois motores campo a campo — um rename só
de um lado agora reprova o teste em vez de aparecer na tela do gestor.

---

## Resumo dos itens que exigem ação

| # | Item | Estado |
|---|---|---|
| B1 | Equidade cumulativa (+100% por quesito) | Ciclo 2026: soma; diverge da planilha de propósito |
| B3 | Participação por etapa, como portão do IDEPE | Ciclo 2026: implementado |
| B2 | Cota além do resultado descartada | Decidido: reproduzir, com aviso ao gestor |
| A8 | Buraco da faixa (−0,3; −0,2) em `H45` | Decidido: ler a grade (25%), como o sistema em uso |
| — | Levar o buraco da faixa ao Núcleo da SEPLAG | **Aberto — fora do código** |
| B4 | Cota de participação fixada em 50% | Mitigado: constante nomeada por ciclo |
| C3 | CORS liberado | Aberto, antes de produção |
| C7 | Tabela de conversão duplicada no frontend | Decidido: duplicar, com teste de paridade |
| C9 | Rename de schema sem o frontend junto | Mitigado: frontend no repo + paridade |
| A6 | Rótulo não diz de que ano são as matrículas | Mitigado: "Matrículas 2026" |
| A7 | Falta aviso explícito de IDEPE ≠ IDEB | Aberto |
| A8 | Resíduo de ponto flutuante antes do `ROUND` | Corrigido em `arredondar_excel()` |
