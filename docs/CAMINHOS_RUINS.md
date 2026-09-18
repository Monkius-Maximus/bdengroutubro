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

*Mitigação:* a tela da etapa em `web/index.html` recalcula a diferença a cada
tecla e a mostra em palavras ("seu resultado ficou 0,20 ponto(s) abaixo da
meta"), com fundo verde ou âmbar conforme o sinal. A inversão fica evidente
antes de avançar — nenhuma validação de faixa a pegaria, porque os dois números
são IDEPEs plausíveis.

### A4. Digitar o IDEPE em escala errada — [Mitigado]
`45` no lugar de `4,5`, ou a taxa de aprovação (`85`) no lugar do índice.

*Mitigação:* faixa 1,5 a 9,2, lida da validação de dados da planilha.

### A5. Enviar decimal com vírgula — [Mitigado]
O gestor digita `4,7`. Em JSON isso vira a string `"4,7"`, e o Pydantic rejeita
com uma mensagem em inglês sobre parsing de float.

*Mitigação:* `lerDecimal()` aceita vírgula e converte para `number` na
fronteira do formulário. O motor só recebe número. O backend continua recusando
string: seria um segundo caminho para a mesma entrada.

### A6. Usar matrículas do ano errado — [Mitigado]
A ponderação é pelas **matrículas de 2025**, não pelas do ano corrente. Uma
escola que cresceu ou encolheu muda o peso relativo entre etapas e altera a
faixa final.

*Mitigação:* o campo se chama "Matrículas de 2025" e o texto de ajuda nomeia a
fonte (Censo Escolar 2025) e desaconselha as matrículas do ano corrente.

### A7. Usar o IDEB no lugar do IDEPE — [Mitigado]
A pasta tem duas abas de cálculo com padronizações diferentes (AI: `(LP-49)/275`
no IDEPE contra as constantes do SAEB no IDEB). Os dois índices têm a mesma
ordem de grandeza, então o número passa em qualquer validação de faixa e produz
um resultado errado sem nenhum sinal.

*Mitigação:* cada tela de etapa abre dizendo que os números são do
**IDEPE/SAEPE** e não do IDEB/SAEB, e por que trocá-los não dispara nenhum
alarme.

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

### B1. Assumir que os bônus são cumulativos — [Mitigado]
A regra declarada diz "independentes e cumulativos". A fórmula `C45` da planilha
usa `OR`: ter equidade **e** elementares vale o mesmo que ter só um, salvo quando
o IDEPE é exatamente 200%. Divergem 20 das 28 combinações.

*Mitigação:* decidido reproduzir a planilha, por ser mecanismo já validado e em
uso. `calcular_cota_bde()` implementa `C45` na forma reduzida de 3 ramos,
equivalente à literal de 4 (o 3º ramo é inalcançável **e** redundante).
Conferido nas 36 combinações da tabela-verdade de `EXTRACAO_PLANILHA.md` §6.

### B2. Esperar que desempenho acima da meta sempre aumente a cota — [Mitigado]
Em `C45`, `B41` (cota além do resultado) é descartada no caminho normal. Sem
bônus, 200% de IDEPE rende exatamente o mesmo que 100%. É o caminho mais
provável de contestação: a escola que mais superou a meta não vê diferença.

*Mitigação:* a `memoria_calculo` diz explicitamente que a cota além do resultado
não entrou no total e por quê, e os `alertas` avisam quando a cota de resultado
já está no teto. O número continua o da planilha; o que muda é o gestor saber
disso antes de contestar.

### B2b. Prometer valores intermediários entre 250% e 300% — [Mitigado]
`C45` produz apenas 10 cotas distintas, e o salto de 250% para 300% não tem
nenhum degrau no meio. Um frontend com barra de progresso contínua, ou um texto
do tipo "faltam 20% para o teto", inventa uma granularidade que a regra não tem.

*Mitigação:* os `alertas` dizem a condição exata e completa do teto (IDEPE de
200% + as duas metas de equidade + participação), em vez de uma distância. A
barra de progresso de `web/index.html` mede **etapas do formulário** ("Etapa 3
de 6"), nunca proximidade do teto — são coisas diferentes e a rotulagem
explicita qual delas está na tela.

### B2c. Orientar a escola a "superar mais a meta" — [Mitigado]
Conselho intuitivo e quase sempre inútil: entre 100% e 200% de IDEPE a cota não
muda, salvo se a escola também tiver as duas metas de equidade. Uma escola em
125% ganha muito mais perseguindo a meta de equidade (+100 pontos) do que
subindo o IDEPE.

*Mitigação:* quando a cota de resultado está no teto, os `alertas` dizem isso e
apontam onde o ganho ainda existe.

### B3. Tratar a participação como eliminatória — [Mitigado]
"Gatilho de participação" sugere que abaixo de 80% a escola perde tudo. Não é o
caso: é uma **cota parcial adicional** que soma 50% ao resultado.

*Mitigação:* o campo se chama `participacao_minima_atingida` e aparece na saída
como `cota_participacao`, somando — nunca multiplicando ou zerando.

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

---

## Resumo dos itens que exigem ação

| # | Item | Estado |
|---|---|---|
| B1 | `OR` vs. bônus cumulativos em `C45` | Decidido: reproduzir a planilha |
| B2 | Cota além do resultado descartada | Decidido: reproduzir, com aviso ao gestor |
| A8 | Buraco da faixa (−0,3; −0,2) em `H45` | Decidido: reproduzir, com alerta explícito |
| — | Confirmar o buraco da faixa com o Núcleo da SEPLAG | **Aberto — fora do código** |
| B4 | Cota de participação fixada em 50% | Mitigado: constante nomeada por ciclo |
| C3 | CORS liberado | Aberto, antes de produção |
| C7 | Tabela de conversão duplicada no frontend | Decidido: duplicar, com teste de paridade |
| A8 | Resíduo de ponto flutuante antes do `ROUND` | Corrigido em `arredondar_excel()` |
