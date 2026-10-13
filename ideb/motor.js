/* ============================================================================
   Motor IDEB — porte da aba "Simulador Ideb" da planilha do Núcleo da Seplag.

   IDEB = N x P, calculado por etapa. Nao existe IDEB unico da escola.

     P   rendimento: media harmonica das taxas de aprovacao dos anos da
         etapa que a escola tem. F7 = media de 1/taxa, G7 = inverso.
         Ano em branco fica fora da media (COUNT so conta o preenchido).
     N   aprendizado: media das notas padronizadas de LP e MT no SAEB,
         nota = (proficiencia - limite inferior) / (superior - inferior) x 10,
         com os limites do SAEB 1997 (Inep).
     IDEB  N x P, divulgado com uma casa decimal.

   Diferenca para a planilha, de proposito: com N x P = 0 a C14 fica em
   branco, porque o AND(...; E11*G7) trata zero como falso. Aqui o IDEB e 0,0.
   ============================================================================ */

var LIMITES_SAEB = {
    ai: { lp: { inf: 49, sup: 324 }, mt: { inf: 60, sup: 322 } },
    af: { lp: { inf: 100, sup: 400 }, mt: { inf: 100, sup: 400 } },
    em: { lp: { inf: 117, sup: 451 }, mt: { inf: 111, sup: 467 } },
};

var ANOS_DA_ETAPA = {
    ai: ['1º ano', '2º ano', '3º ano', '4º ano', '5º ano'],
    af: ['6º ano', '7º ano', '8º ano', '9º ano'],
    em: ['1ª série', '2ª série', '3ª série', '4ª série'],
};

/**
 * Arredonda como a celula do Excel exibe: empate vai para longe do zero. O
 * toPrecision(12) descarta o residuo binario do produto (4,45 que chega como
 * 4,4499999...).
 */
function arredondar(valor, casas) {
    var fator = Math.pow(10, casas);
    var escalado = Number((Math.abs(valor) * fator).toPrecision(12));
    return (valor < 0 ? -1 : 1) * Math.round(escalado) / fator;
}

/**
 * P. Recebe as taxas em percentual (0 a 100), so dos anos preenchidos.
 * Uma taxa zero leva P a zero: 1/0 e Infinity, o inverso da media tambem.
 */
function calcularRendimento(aprovacoes) {
    if (aprovacoes.length === 0) {
        throw new Error('Informe ao menos uma taxa de aprovação da etapa.');
    }
    var somaInversos = aprovacoes.reduce(function (s, taxa) { return s + 100 / taxa; }, 0);
    return aprovacoes.length / somaInversos;
}

function padronizar(proficiencia, limite) {
    return ((proficiencia - limite.inf) / (limite.sup - limite.inf)) * 10;
}

/**
 * IDEB de uma etapa. `chave` e 'ai', 'af' ou 'em'; `dados` traz
 * { aprovacoes: [taxas preenchidas], lp, mt }.
 */
function calcularIdeb(chave, dados) {
    var limites = LIMITES_SAEB[chave];
    var rendimento = calcularRendimento(dados.aprovacoes);
    var notaLp = padronizar(dados.lp, limites.lp);
    var notaMt = padronizar(dados.mt, limites.mt);
    var notaSaeb = (notaLp + notaMt) / 2;
    return {
        rendimento: rendimento,
        nota_lp: notaLp,
        nota_mt: notaMt,
        nota_saeb: notaSaeb,
        ideb: arredondar(notaSaeb * rendimento, 1),
    };
}
