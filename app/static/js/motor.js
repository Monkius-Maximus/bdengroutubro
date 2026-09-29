/* ============================================================================
   Motor BDE — porte de src/bde/service.py para o navegador.

   O Google Sites e hospedagem estatica: nao roda Python, nao roda o FastAPI.
   Este motor substitui a chamada a /api/v1/simular-bde e devolve exatamente o
   mesmo formato que a API devolvia, para que o wizard nao precise saber de
   onde veio o resultado.

   A regra vive em src/bde/schemas.py; este motor e o service.py a executam.

   Cadeia de calculo:

     variacao_i    resultado - meta, por etapa (B21/B29/B37)
     H47           media ponderada das variacoes pelas matriculas, ROUND 4
     H45           conversao da media em percentual IDEPE
     B40 / B41     cota resultado = min(idepe; 1) / cota alem = idepe - B40
     B42 / B43     +100% por quesito de equidade atingido
     C45           cota do BDE = min(idepe + B42 + B43; 2.5)
     B44           +50% se a escola atingiu 80% de participacao
     total         min(C45 + B44; 3.0)

   Toda parcela e multipla de 25%, entao o percentual final nunca e quebrado.
   ============================================================================ */

var COTA_POR_QUESITO_EQUIDADE = 1.0;
var COTA_PARTICIPACAO = 0.5;
var TETO_COTA_BDE = 2.5;
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
 */
function simularBde(payload) {
    var etapas = [];
    ['ai', 'af', 'em'].forEach(function (chave) {
        var dados = payload['etapa_' + chave];
        if (dados) {
            etapas.push({
                nome: NOMES_ETAPAS[chave],
                matriculas: dados.matriculas,
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

    // B21/B29/B37
    var detalhes = etapas.map(function (e) {
        var variacao = arredondarExcel(e.resultado - e.meta);
        return {
            nome: e.nome,
            matriculas: e.matriculas,
            meta: e.meta,
            resultado: e.resultado,
            variacao: variacao,
            percentual_atingimento: converterDiferencaEmPercentual(variacao),
        };
    });

    // H47
    var totalMatriculas = detalhes.reduce(function (s, d) { return s + d.matriculas; }, 0);
    var soma = detalhes.reduce(function (s, d) { return s + d.variacao * d.matriculas; }, 0);
    var mediaVariacao = arredondarExcel(soma / totalMatriculas);

    // H45
    var percentualIdepe = converterDiferencaEmPercentual(mediaVariacao);

    // B40 / B41
    var cotaResultado = Math.min(percentualIdepe, 1.0);
    var cotaAlemResultado = percentualIdepe - cotaResultado;

    // B42 / B43 / B44
    var bonusEquidade = payload.reduziu_desigualdade ? COTA_POR_QUESITO_EQUIDADE : 0.0;
    var bonusElementares = payload.terco_menor_elementares ? COTA_POR_QUESITO_EQUIDADE : 0.0;
    var bonusParticipacao = payload.participacao_maior_80 ? COTA_PARTICIPACAO : 0.0;

    // C45 — a participacao fica de fora e e somada depois
    var cotaBdeCalculada = Math.min(
        percentualIdepe + bonusEquidade + bonusElementares, TETO_COTA_BDE
    );
    var percentualBde = Math.min(cotaBdeCalculada + bonusParticipacao, TETO_BDE);

    // Os nomes e a ordem sao os de RespostaBDE em src/bde/schemas.py. A pagina
    // e a API tem de devolver o mesmo objeto: o wizard nao sabe de onde veio.
    return {
        percentual_bde: percentualBde,
        percentual_formatado: Math.round(percentualBde * 100) + '%',
        media_ponderada_variacao: mediaVariacao,
        percentual_idepe: percentualIdepe,
        bonus_equidade: bonusEquidade,
        bonus_elementares: bonusElementares,
        bonus_participacao: bonusParticipacao,
        cota_resultado: cotaResultado,
        cota_alem_resultado: cotaAlemResultado,
        cota_bde_calculada: cotaBdeCalculada,
        apto_a_receber: percentualBde > 0.0,
        etapas: detalhes,
    };
}
