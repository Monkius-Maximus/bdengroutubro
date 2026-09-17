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

### A3. Trocar meta e resultado de campo — [Aberto]
Digitar 4,5 em "resultado" e 4,7 em "meta" inverte o sinal da diferença e pode
levar de 125% para 75%. Nenhuma validação detecta isso: ambos são IDEPEs
plausíveis.

*Mitigação recomendada:* o wizard exibe a diferença calculada ("seu resultado
ficou 0,20 acima da meta") na mesma tela, antes de avançar. Erro de troca fica
evidente na leitura.

### A4. Digitar o IDEPE em escala errada — [Mitigado]
`45` no lugar de `4,5`, ou a taxa de aprovação (`85`) no lugar do índice.

*Mitigação:* faixa 1,5 a 9,2, lida da validação de dados da planilha.

### A5. Enviar decimal com vírgula — [Aberto]
O gestor digita `4,7`. Em JSON isso vira a string `"4,7"`, e o Pydantic rejeita
com uma mensagem em inglês sobre parsing de float.

*Mitigação recomendada:* normalizar no frontend (input com máscara pt-BR
convertendo para `number` antes do `POST`). Não aceitar string no backend:
seria um segundo caminho para a mesma entrada.

### A6. Usar matrículas do ano errado — [Aberto]
A ponderação é pelas **matrículas de 2025**, não pelas do ano corrente. Uma
escola que cresceu ou encolheu muda o peso relativo entre etapas e altera a
faixa final.

*Mitigação recomendada:* rotular o campo como "Matrículas 2025" no wizard, com
a origem do dado (Censo/aba `Matrículas 2025`) no texto de ajuda.

### A7. Usar o IDEB no lugar do IDEPE — [Aberto]
A pasta tem duas abas de cálculo com padronizações diferentes (AI: `(LP-49)/275`
no IDEPE contra as constantes do SAEB no IDEB). Os dois índices têm a mesma
ordem de grandeza, então o número passa em qualquer validação de faixa e produz
um resultado errado sem nenhum sinal.

*Mitigação recomendada:* deixar explícito em cada tela que o simulador trabalha
com **IDEPE/SAEPE**, e não com IDEB/SAEB.

### A8. Arredondamento na borda de faixa — [Aberto]
`H47` é arredondado a 4 casas. Uma diferença de 0,09999 dá 100%; 0,1 dá 125%.
A distância entre duas telas do wizard pode valer 25 pontos percentuais.

*Mitigação recomendada:* replicar o `ROUND(...; 4)` da planilha (não o
arredondamento padrão do float) e, quando a média ficar a menos de 0,01 da
próxima faixa, emitir um item em `alertas`.

---

## B. Interpretação da regra

### B1. Assumir que os bônus são cumulativos — [Decisão]
A regra declarada diz "independentes e cumulativos". A fórmula `C45` da planilha
usa `OR`: ter equidade **e** elementares vale o mesmo que ter só um, salvo quando
o IDEPE é exatamente 200%. Divergem 20 das 28 combinações.

**O código hoje no repositório implementa a versão cumulativa e, portanto, não
bate com a planilha que o gestor tem aberta na outra janela.** Detalhes e tabela
completa em `EXTRACAO_PLANILHA.md` §5.1. Decisão de negócio, não de engenharia.

### B2. Esperar que desempenho acima da meta sempre aumente a cota — [Decisão]
Em `C45`, `B41` (cota além do resultado) é descartada no caminho normal. Sem
bônus, 200% de IDEPE rende exatamente o mesmo que 100%. É o caminho mais
provável de contestação: a escola que mais superou a meta não vê diferença.

### B3. Tratar a participação como eliminatória — [Mitigado]
"Gatilho de participação" sugere que abaixo de 80% a escola perde tudo. Não é o
caso: é uma **cota parcial adicional** que soma 50% ao resultado.

*Mitigação:* o campo se chama `participacao_minima_atingida` e aparece na saída
como `cota_participacao`, somando — nunca multiplicando ou zerando.

### B4. Fixar 50% como o valor eterno da cota de participação — [Aberto]
No ciclo BDE 2025 (resultados de 2024) essa cota foi de **25%**. O percentual
muda entre ciclos.

*Mitigação recomendada:* constante nomeada e versionada por ciclo, em um único
lugar. Nunca um literal `0.5` espalhado pelo serviço.

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

### C2. Router engolindo exceções — [Aberto]
`router.py` tem `except Exception` convertendo qualquer erro em 422. Um bug de
divisão por zero vira "erro de validação" para o usuário e some do log.

*Mitigação recomendada:* remover o `try/except`. O `RequestSchema` já garante as
pré-condições; o que passar dele e quebrar é bug nosso e deve virar 500 com
stack trace.

### C3. `allow_origins=["*"]` em produção — [Aberto]
Aceitável em desenvolvimento; em produção permite que qualquer site incorpore o
simulador e o apresente como oficial.

*Mitigação recomendada:* lista de origens por variável de ambiente.

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

### C7. Duplicar a tabela de conversão no frontend — [Aberto]
Para dar preview instantâneo enquanto o usuário digita, é tentador reimplementar
a conversão em JavaScript. Duas fontes de verdade que divergem no primeiro
ajuste de regra.

*Mitigação recomendada:* o preview vem do backend, ou o backend expõe a tabela
como dado. A regra vive em um lugar só.

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
| B1 | `OR` vs. bônus cumulativos em `C45` | **Decisão — bloqueia o service** |
| B2 | Cota além do resultado descartada | **Decisão — bloqueia o service** |
| A8 | Buraco da faixa (−0,3; −0,2) em `H45` | **Decisão** (recomendado: seguir a regra) |
| C2 | `except Exception` no router | Aberto, correção trivial |
| B4 | Cota de participação fixada em 50% | Aberto, extrair para constante de ciclo |
| C3 | CORS liberado | Aberto, antes de produção |
