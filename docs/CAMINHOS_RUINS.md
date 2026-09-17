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

### A8. Arredondamento na borda de faixa — [Mitigado]
A média ponderada é arredondada a 4 casas. Uma diferença de 0,09999 dá 100%;
0,1 dá 125%. A distância entre duas telas do wizard pode valer 25 pontos.

*Mitigação:* `arredondar_excel()` replica o `ROUND(...; 4)` da planilha, que é
metade-para-longe-do-zero — o `round()` do Python é bancário e cairia no degrau
errado em `0,09995`. O ponderador usa as diferenças **cruas**, arredondando só o
quociente. Quando a média fica a menos de 0,01 do próximo degrau, entra um item
em `alertas`.

## B. Interpretação da regra

### B1. Tratar a fórmula `C45` da planilha como norma — [Mitigado]
A planilha da SEPLAG é um simulador auxiliar, não o motor de pagamento. Sua
fórmula `C45` combina os objetivos bônus com `OR` e contradiz os quatro cenários
que a área de negócio comunica às escolas — entre eles o exemplo dos 375%
cortados em 300%, um número que `C45` nunca chega a produzir.

*Mitigação:* a regra em vigor é a do slide oficial, cumulativa. `C45` está
documentada em `EXTRACAO_PLANILHA.md` §5.1 como bug conhecido, com o histórico
da decisão e sua reversão, para ninguém "corrigir" o código de volta.

### B2. Esperar que superar a meta compense sempre — [Mitigado]
Vale até certo ponto e depois para. `≥ 0,3` é degrau terminal: superar a meta em
0,3 ou em 1,2 dá o mesmo atingimento de 175%. E acima de 300% de soma nada mais
entra.

*Mitigação:* os `alertas` avisam quando o atingimento chegou ao degrau máximo e
quando o teto foi aplicado, dizendo o valor da soma antes do corte
(`soma_sem_teto`).

### B3. Prometer a soma em vez do teto — [Mitigado]
`175 + 100 + 100 + 50 = 425%`. Uma escola que faça essa conta de cabeça, ou uma
interface que mostre a soma como resultado, promete o que não será pago.

*Mitigação:* `percentual_bde` já vem limitado a 300%; `soma_sem_teto` e
`teto_aplicado` existem para explicar o corte, nunca para serem exibidos como
resultado. O frontend deve mostrar `percentual_formatado`.

### B4. Aconselhar a escola a perseguir a nota — [Mitigado]
Conselho intuitivo e muitas vezes pior que a alternativa: sair de 0% para 175%
de atingimento rende 175 pontos, enquanto os dois objetivos bônus rendem 200.
Uma escola abaixo da meta com os dois bônus (200%) supera uma que passou da meta
sem nenhum (175%).

*Mitigação:* os `alertas` calculam o ganho **real** de cada objetivo pendente,
já descontado o teto, em vez de repetir o valor nominal.

### B5. Tratar a participação como eliminatória — [Mitigado]
"Gatilho de participação" sugere que abaixo de 80% a escola perde tudo. Não é o
caso: é uma cota adicional que soma 50 pontos.

*Mitigação:* o campo se chama `participacao_minima_atingida` e aparece como
`cota_participacao`, somando — nunca multiplicando ou zerando.

### B6. Fixar os pesos das cotas como eternos — [Mitigado]
No ciclo BDE 2025 a cota de participação foi de **25%**, não 50%. Os percentuais
mudam entre ciclos.

*Mitigação:* `COTA_PARTICIPACAO`, `COTA_EQUIDADE`, `COTA_ELEMENTARES` e
`TABELA_ATINGIMENTO` são constantes nomeadas no topo de `service.py`. Nenhum
literal espalhado pelo serviço.

### B7. Esperar o valor em reais — [Mitigado]
O gestor vai perguntar "quanto eu vou receber?". A ferramenta só produz o
**percentual de referência**. A destinação das verbas é decisão do setor
financeiro, e o valor individual depende de salário-base, cargo e tempo de
vínculo.

*Mitigação:* `aviso_legal` na resposta diz isso explicitamente.

### B8. Tratar a simulação como resultado oficial — [Mitigado]
Numa versão web, com URL do governo e visual institucional, a chance de ser lida
como oficial é muito maior do que num `.xlsx` circulando por WhatsApp.

*Mitigação:* `aviso_legal` é campo obrigatório da resposta, com default fixo.

### B9. Portar as fórmulas mortas da planilha — [Mitigado]
`H7`, `J9`, `H37` (`#REF!`) e `I45` são rascunhos sobrepostos.

*Mitigação:* catalogados como mortos em `EXTRACAO_PLANILHA.md` §4.

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

### C7. Duplicar a tabela de conversão no frontend — [Mitigado]
Para dar preview instantâneo enquanto o usuário digita, é tentador reimplementar
a conversão em JavaScript. Duas fontes de verdade que divergem no primeiro
ajuste de regra.

*Mitigação:* o preview vem do backend. `POST /api/v1/simular-bde` é stateless e
barato — o frontend chama a cada mudança de resposta (com debounce ao digitar) e
usa o `percentual_formatado` que voltar. Não é preciso endpoint separado para a
tabela: isso seria uma segunda porta para a mesma regra.

Os limites de validação de cada campo (8 a 50.000 matrículas, IDEPE de 1,5 a
9,2) também não precisam ser recopiados: o `/openapi.json` já os publica como
`minimum`/`maximum`, junto com a descrição de cada pergunta. O wizard pode ser
gerado a partir dali.

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
| B1 | `C45` (OR) vs. regra cumulativa do slide | Decidido: regra do slide |
| A8 | Buraco da faixa (−0,3; −0,2) | Resolvido: o slide traz `≥ −0,3 → 25%` |
| — | Escala de 8 degraus: o slide diz "IDEB" | **Aberto — confirmar se IDEPE difere** |
| B3 | Promessa de 375% em vez do teto de 300% | Mitigado: `soma_sem_teto` + `teto_aplicado` |
| B6 | Pesos das cotas por ciclo | Mitigado: constantes nomeadas |
| C7 | Regra duplicada no frontend | Mitigado: preview via API + `/openapi.json` |
| A3 / A5 | Troca de meta/resultado, decimal com vírgula | Aberto — cabe ao wizard |
| A6 / A7 | Matrículas do ano errado, IDEB no lugar do IDEPE | Aberto — cabe à rotulagem |
| C3 | CORS liberado | Aberto — antes de produção, não bloqueia o dev |
