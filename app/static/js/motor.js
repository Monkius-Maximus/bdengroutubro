/* ============================================================================
   Motor BDE — porte de src/bde/service.py para o navegador.

   O Google Sites e hospedagem estatica: nao roda Python, nao roda o FastAPI.
   Este motor substitui a chamada a /api/v1/simular-bde e devolve exatamente o
   mesmo formato que a API devolvia, para que o wizard nao precise saber de
   onde veio o resultado.

   A participacao de 80% no SAEPE e por etapa e funciona como portao: etapa que
   nao atingiu nao tem IDEPE divulgado, entra na conta com atingimento zero e
   continua pesando pelas suas matriculas.

   Cadeia de calculo:

     variacao_i    resultado - meta, so nas etapas que participaram
     H47           media ponderada das variacoes, SO entre as aprovadas
     H45           conversao da media em percentual de atingimento
     diluicao      percentual x (matriculas aprovadas / matriculas totais)
     B40 / B41     cota resultado = min(idepe; 1) / cota alem (informativa)
     equidade      +100% por quesito atingido, os dois somam +200%
     participacao  +50% se QUALQUER etapa atingiu 80%
     total         min(B40 + equidade + elementares + participacao; 3.0)

   A formula C45 da planilha nao vale mais: ela tratava os dois quesitos de
   equidade com OU. A regra do ciclo 2026 soma por quesito, entao o simulador
   diverge da planilha de proposito. Ver docs/EXTRACAO_PLANILHA.md secao 5.1.

   A diluicao acontece DEPOIS da conversao, nao antes: uma etapa sem meta e sem
   resultado nao tem variacao para entrar no H47. Assim, enquanto todas as
   etapas passarem no portao, o percentual_idepe e identico ao do ciclo
   anterior.
   ============================================================================ */

var COTA_POR_QUESITO_EQUIDADE = 1.0;
var COTA_PARTICIPACAO = 0.5;
var TETO_BDE = 3.0;

// Faixas da validacao de dados da planilha (B6:B8 e B19/B20 etc.).
var MATRICULAS_MIN = 8;
var MATRICULAS_MAX = 50000;
var IDEPE_MIN = 1.5;
var IDEPE_MAX = 9.2;

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

    // Etapa sem 80% nao tem IDEPE divulgado: variacao fica nula, que e
    // diferente de zero — zero e quem participou e empatou com a meta.
    var detalhes = etapas.map(function (e) {
        var participou = e.participou;
        var variacao = participou ? arredondarExcel(e.resultado - e.meta) : null;
        return {
            nome: e.nome,
            matriculas: e.matriculas,
            participou: participou,
            meta: participou ? e.meta : null,
            resultado: participou ? e.resultado : null,
            variacao: variacao,
            percentual_atingimento: participou
                ? converterDiferencaEmPercentual(variacao)
                : 0.0,
        };
    });

    var aprovadas = detalhes.filter(function (d) { return d.participou; });

    // H47 — so entre as aprovadas, porque so elas tem variacao. Com nenhuma
    // aprovada nao ha IDEPE: a escola concorre apenas aos quesitos de equidade.
    var matAprovadas = aprovadas.reduce(function (s, d) { return s + d.matriculas; }, 0);
    var mediaVariacao = 0.0;
    var pctAprovadas = 0.0;
    if (aprovadas.length > 0) {
        var soma = aprovadas.reduce(function (s, d) {
            return s + d.variacao * d.matriculas;
        }, 0);
        mediaVariacao = arredondarExcel(soma / matAprovadas);
        pctAprovadas = converterDiferencaEmPercentual(mediaVariacao);
    }

    // Diluicao pelas reprovadas: atingimento zero, peso das matriculas. Sem
    // reprovada nenhuma a fracao e 1 e o percentual e o do ciclo anterior.
    var matTotal = detalhes.reduce(function (s, d) { return s + d.matriculas; }, 0);
    var percentualIdepe = arredondarExcel(pctAprovadas * (matAprovadas / matTotal));

    // B40 / B41. A parcela acima de 100% continua fora da soma; fica exposta
    // para o gestor entender por que superar muito a meta nao mudou nada.
    var cotaResultado = Math.min(percentualIdepe, 1.0);
    var cotaAlemResultado = Math.max(percentualIdepe - cotaResultado, 0.0);

    // Equidade soma por quesito e vale para toda escola, tenha ou nao passado
    // no portao da participacao.
    var bonusEquidade = payload.reduziu_desigualdade ? COTA_POR_QUESITO_EQUIDADE : 0.0;
    var bonusElementares = payload.terco_menor_elementares ? COTA_POR_QUESITO_EQUIDADE : 0.0;
    var bonusParticipacao = aprovadas.length > 0 ? COTA_PARTICIPACAO : 0.0;

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
