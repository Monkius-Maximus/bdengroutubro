/* ============================================================================
   Motor BDE — porte de src/bde/service.py para o navegador.

   O Google Sites e hospedagem estatica: nao roda Python, nao roda o FastAPI.
   Este motor substitui a chamada a /api/v1/simular-bde e devolve exatamente o
   mesmo formato que a API devolvia, para que o wizard nao precise saber de
   onde veio o resultado.

   A participacao de 80% no SAEPE e por etapa. Etapa que nao atingiu entra na
   media com IDEPE zero: a diferenca dela e 0 - meta, pesando pelas
   matriculas. Nenhuma etapa com matricula fica de fora da conta.

   Cadeia de calculo:

     idepe_i       resultado com 80% de participacao, 0 sem
     variacao_i    idepe_i - meta, em TODAS as etapas
     H47           media ponderada das variacoes pelas matriculas
     H45           conversao da media em percentual de atingimento
     equidade      +100% se reduziu desigualdade OU esta no terco de
                   elementares; o segundo quesito so vale (+50%) com IDEPE
                   de 200%
     B40           cota resultado:
                     sem quesito de equidade      idepe inteiro
                     com quesito                  min(idepe; 1)
     B41           cota alem = idepe - B40, a parte trocada pelo quesito
     participacao  +50% so se TODAS as etapas atingiram 80%
     total         min(B40 + equidade + elementares + participacao; 3.0)

   No topo da tabela, como na C45 da planilha: IDEPE de 200% + um quesito =
   200%; + os dois quesitos = 250%. Ver docs/EXTRACAO_PLANILHA.md secao 5.1.

   Com todas as etapas acima de 80%, o percentual_idepe e identico ao do ciclo
   anterior: o zero so muda a conta de quem tem etapa sem participacao.
   ============================================================================ */

var COTA_EQUIDADE = 1.0;
var COTA_PARTICIPACAO = 0.5;
var TETO_BDE = 3.0;

// Segundo quesito de equidade: so vale com o IDEPE no topo da tabela
// (variacao media >= 0,4), e vale metade.
var IDEPE_TOPO = 2.0;
var COTA_SEGUNDO_QUESITO = 0.5;

var NOMES_ETAPAS = {
    ai: 'Anos Iniciais',
    af: 'Anos Finais',
    em: "Ensino Médio",
};

/**
 * ROUND(valor; 4) do Excel — empate vai para longe do zero.
 *
 * Math.round sozinho arredonda meio-para-cima (em direcao a +infinito), o que
 * erra o sinal nos negativos; por isso o calculo roda no valor absoluto. O
 * toPrecision(12) descarta o residuo binario da subtracao: 4,59995 - 4,5 nao
 * da 0,09995, da 0,09994999999999976, que cairia na faixa de 100% em vez de
 * 125%.
 */
function arredondarExcel(valor) {
    var sinal = valor < 0 ? -1 : 1;
    var escalado = Number((Math.abs(valor) * 1e4).toPrecision(12));
    return (sinal * Math.round(escalado)) / 1e4;
}

/**
 * Formula H45. Recebe a diferenca ja arredondada por arredondarExcel.
 *
 * Le a grade de consulta E42:M43 da planilha: cada faixa vale a partir do seu
 * limite inferior, inclusive. A escada de IFs de H45 devolve 0% para
 * diferencas estritamente entre -0,3 e -0,2 — um buraco que a propria grade
 * contradiz, e que o simulador em uso no NGR nunca teve. Ver
 * docs/EXTRACAO_PLANILHA.md secao 5.2.
 */
function converterDiferencaEmPercentual(diferenca) {
    if (diferenca < -0.3) return 0.00;
    if (diferenca < -0.2) return 0.25;
    if (diferenca < -0.1) return 0.50;
    if (diferenca < 0.0) return 0.75;
    if (diferenca < 0.1) return 1.00;
    if (diferenca < 0.2) return 1.25;
    if (diferenca < 0.3) return 1.50;
    if (diferenca < 0.4) return 1.75;
    return 2.00;
}

/**
 * Substitui o POST /api/v1/simular-bde. Recebe e devolve os mesmos formatos.
 *
 * Cada etapa do payload traz { matriculas, participacao_maior_80 } e, so
 * quando participou, { meta, resultado }.
 */
function simularBde(payload) {
    var etapas = [];
    ['ai', 'af', 'em'].forEach(function (chave) {
        var dados = payload['etapa_' + chave];
        if (dados) {
            etapas.push({
                nome: NOMES_ETAPAS[chave],
                matriculas: dados.matriculas,
                participou: !!dados.participacao_maior_80,
                meta: dados.meta,
                resultado: dados.resultado,
            });
        }
    });

    if (etapas.length === 0) {
        throw new Error(
            'Informe ao menos uma etapa pactuada. Escola sem meta pactuada nao ' +
            'e elegivel ao BDE.'
        );
    }

    // Etapa sem 80% entra com IDEPE zero, e a diferenca dela e 0 - meta.
    var detalhes = etapas.map(function (e) {
        var idepe = e.participou ? e.resultado : 0.0;
        var variacao = arredondarExcel(idepe - e.meta);
        return {
            nome: e.nome,
            matriculas: e.matriculas,
            participou: e.participou,
            meta: e.meta,
            resultado: idepe,
            variacao: variacao,
            percentual_atingimento: converterDiferencaEmPercentual(variacao),
        };
    });

    // H47 entre todas as etapas, pesando pelas matriculas
    var matTotal = detalhes.reduce(function (s, d) { return s + d.matriculas; }, 0);
    var soma = detalhes.reduce(function (s, d) { return s + d.variacao * d.matriculas; }, 0);
    var mediaVariacao = arredondarExcel(soma / matTotal);
    var percentualIdepe = converterDiferencaEmPercentual(mediaVariacao);

    // Equidade: o primeiro quesito vale +100% para toda escola, tenha ou nao
    // atingido 80% de participacao, e aparece em equidade. O segundo so vale
    // com IDEPE de 200%, e vale +50%, em elementares.
    var doisQuesitos = !!(payload.reduziu_desigualdade && payload.terco_menor_elementares);
    var temQuesito = !!(payload.reduziu_desigualdade || payload.terco_menor_elementares);
    var bonusEquidade = temQuesito ? COTA_EQUIDADE : 0.0;
    var bonusElementares = doisQuesitos && percentualIdepe >= IDEPE_TOPO ? COTA_SEGUNDO_QUESITO : 0.0;

    // B40 / B41. Com quesito de equidade, a escola troca o excedente acima de
    // 100% pelo quesito. Sem quesito, o IDEPE conta inteiro.
    var cotaResultado = temQuesito ? Math.min(percentualIdepe, 1.0) : percentualIdepe;
    var cotaAlemResultado = arredondarExcel(percentualIdepe - cotaResultado);

    // Participacao: uma etapa sem 80% ja tira os +50%.
    var bonusParticipacao = detalhes.every(function (d) { return d.participou; })
        ? COTA_PARTICIPACAO : 0.0;

    var cotaBdeCalculada = cotaResultado + bonusEquidade + bonusElementares;
    var percentualBde = arredondarExcel(
        Math.min(cotaBdeCalculada + bonusParticipacao, TETO_BDE)
    );

    // Os nomes e a ordem sao os de RespostaBDE em src/bde/schemas.py. A pagina
    // e a API tem de devolver o mesmo objeto: o wizard nao sabe de onde veio.
    return {
        percentual_bde: percentualBde,
        percentual_formatado: Math.round(percentualBde * 100) + '%',
        apto_a_receber: percentualBde > 0.0,
        media_ponderada_variacao: mediaVariacao,
        percentual_idepe: percentualIdepe,
        cota_resultado: cotaResultado,
        cota_alem_resultado: cotaAlemResultado,
        cota_bde_calculada: cotaBdeCalculada,
        bonus_equidade: bonusEquidade,
        bonus_elementares: bonusElementares,
        bonus_participacao: bonusParticipacao,
        etapas: detalhes,
    };
}
