/* ============================================================================
   Wizard IDEB — navegacao, leitura dos campos e telas de resumo e resultado.

   Mesmo fluxo do simulador do BDE (app/static/js/wizard.js): etapas, uma
   tela por etapa marcada, resumo e resultado. O calculo esta em motor.js.
   ============================================================================ */

/* Indices fixos no template. O numero de telas visiveis varia com as etapas
   marcadas, entao quem manda no progresso e passosVisiveis(), nao o indice. */
const PASSO_ETAPAS = 0;
const PASSO_RESUMO = 4;
const PASSO_RESULTADO = 5;

const PASSO_DA_ETAPA = { ai: 1, af: 2, em: 3 };
const ETAPAS = ['ai', 'af', 'em'];

const NOME_ETAPA = { ai: 'Anos Iniciais', af: 'Anos Finais', em: 'Ensino Médio' };
/* Nomes das etapas como aparecem nas mensagens: "dos Anos Iniciais". */
const ETAPA_NAS_MENSAGENS = { ai: 'dos Anos Iniciais', af: 'dos Anos Finais', em: 'do Ensino Médio' };

/* Taxa de aprovacao em %. */
const APROVACAO_MIN = 0;
const APROVACAO_MAX = 100;

const estado = {
    stepAtual: PASSO_ETAPAS,
    etapas: [],
    /* So existe a etapa cuja tela foi validada, no Proximo. */
    dados: {},
    resultados: {},
};

/** Telas efetivamente alcancaveis, na ordem. */
function passosVisiveis() {
    const passos = [PASSO_ETAPAS];
    ETAPAS.forEach((chave) => {
        if (estado.etapas.includes(chave)) passos.push(PASSO_DA_ETAPA[chave]);
    });
    return passos.concat([PASSO_RESUMO, PASSO_RESULTADO]);
}

function etapaDoPasso(step) {
    return ETAPAS.find((chave) => PASSO_DA_ETAPA[chave] === step);
}

document.addEventListener('DOMContentLoaded', () => {
    ajustarEspacoDoRodape();
    atualizarUI();
});

/**
 * O rodape e position:fixed e, em tela estreita, passa dos 80px reservados
 * embaixo do .wizard-container, cobrindo o "Proximo". Reserva a altura real.
 */
function ajustarEspacoDoRodape() {
    const rodape = document.querySelector('.footer');
    const container = document.querySelector('.wizard-container');
    const altura = rodape.getBoundingClientRect().height + 16;
    container.style.paddingBottom = `${Math.max(80, Math.round(altura))}px`;
}

window.addEventListener('resize', ajustarEspacoDoRodape);

/* Redesenhado a cada atualizacao porque a quantidade de telas muda conforme
   as etapas marcadas. */
function renderizarDots(total) {
    const c = document.getElementById('steps-dots');
    if (c.childElementCount === total) return;
    c.innerHTML = '';
    for (let i = 0; i < total; i++) {
        const d = document.createElement('div');
        d.className = 'dot';
        d.id = `dot-${i}`;
        c.appendChild(d);
    }
}

function corFase(pos, total) {
    const fracao = total > 1 ? pos / (total - 1) : 1;
    if (fracao >= 2 / 3) return 'verde';
    if (fracao >= 1 / 3) return 'dourado';
    return 'azul';
}

function corBarra(fase) {
    if (fase === 'verde') return 'linear-gradient(90deg, #ca8a04, #16a34a)';
    if (fase === 'dourado') return 'linear-gradient(90deg, #1a3a5c, #ca8a04)';
    return 'linear-gradient(90deg, #1a3a5c, #2a6496)';
}

function atualizarUI() {
    const { stepAtual } = estado;
    const visiveis = passosVisiveis();
    const totalSteps = visiveis.length;
    const pos = visiveis.indexOf(stepAtual);
    const percentual = Math.round((pos / (totalSteps - 1)) * 100);

    renderizarDots(totalSteps);

    const barra = document.getElementById('barra-progresso');
    barra.style.width = `${percentual}%`;
    barra.style.background = corBarra(corFase(pos, totalSteps));

    document.getElementById('lbl-etapa').textContent = `Passo ${pos + 1} de ${totalSteps}`;
    document.getElementById('lbl-progresso').textContent = `${percentual}%`;

    for (let i = 0; i < totalSteps; i++) {
        const dot = document.getElementById(`dot-${i}`);
        dot.className = 'dot';
        const fase = corFase(i, totalSteps);
        if (fase === 'dourado') dot.classList.add('fase-dourado');
        if (fase === 'verde') dot.classList.add('fase-verde');
        if (i < pos) dot.classList.add('completo');
        if (i === pos) dot.classList.add('ativo');
    }

    document.querySelectorAll('.step').forEach(s => s.style.display = 'none');
    const stepEl = document.querySelector(`.step[data-step="${stepAtual}"]`);
    stepEl.style.display = 'flex';
    stepEl.style.flexDirection = 'column';
    stepEl.style.justifyContent = 'center';
    stepEl.style.animation = 'none';
    stepEl.offsetHeight;
    stepEl.style.animation = 'fadeSlideUp .35s ease-out';

    const btnVoltar = document.getElementById('btn-voltar');
    const btnProximo = document.getElementById('btn-proximo');

    btnVoltar.style.display = stepAtual !== PASSO_ETAPAS && stepAtual !== PASSO_RESULTADO ? 'flex' : 'none';

    if (stepAtual === PASSO_RESULTADO) {
        btnProximo.style.display = 'none';
    } else if (stepAtual === PASSO_RESUMO) {
        btnProximo.style.display = 'flex';
        btnProximo.textContent = 'Ver Resultado';
        btnProximo.className = 'btn btn-resultado';
        btnProximo.onclick = mostrarResultado;
    } else {
        btnProximo.style.display = 'flex';
        btnProximo.textContent = 'Próximo';
        btnProximo.className = 'btn btn-proximo';
        btnProximo.onclick = proximo;
    }
}

/**
 * Confere o passo atual e devolve os erros encontrados, cada um com o
 * elemento onde a mensagem aparece. Lista vazia = pode avancar.
 */
function validarPasso(step) {
    if (step === PASSO_ETAPAS) {
        return estado.etapas.length > 0
            ? []
            : [{ alvo: document.getElementById('opcoes-etapas'), msg: 'Marque ao menos uma etapa para continuar.' }];
    }
    return lerEtapa(etapaDoPasso(step)).erros;
}

function proximo() {
    const step = estado.stepAtual;
    limparErros(document.querySelector(`.step[data-step="${step}"]`));
    const erros = validarPasso(step);
    if (erros.length > 0) {
        mostrarErrosDeCampo(erros);
        return;
    }

    const chave = etapaDoPasso(step);
    if (chave) estado.dados[chave] = lerEtapa(chave).dados;

    const visiveis = passosVisiveis();
    const seguinte = visiveis[visiveis.indexOf(step) + 1];
    if (seguinte === PASSO_RESUMO) {
        mostrarResumo();
        return;
    }
    estado.stepAtual = seguinte;
    atualizarUI();
}

function voltar() {
    const visiveis = passosVisiveis();
    estado.stepAtual = visiveis[visiveis.indexOf(estado.stepAtual) - 1];
    atualizarUI();
}

/* Os dados da etapa so passam a existir quando a tela dela e validada, no
   Proximo. Marcar a etapa aqui nao cria dados vazios. */
function toggleEtapa(card) {
    const chave = card.dataset.etapa;
    const marcado = card.classList.toggle('selecionado');
    card.setAttribute('aria-checked', String(marcado));
    if (marcado) {
        estado.etapas.push(chave);
    } else {
        estado.etapas.splice(estado.etapas.indexOf(chave), 1);
        delete estado.dados[chave];
    }
    limparErros(document.getElementById('opcoes-etapas').parentElement);
    atualizarUI();
}

/* Espaco e Enter marcam a etapa, como numa caixa de selecao. */
function teclaNaOpcao(e, card) {
    if (e.key !== ' ' && e.key !== 'Enter') return;
    e.preventDefault();
    toggleEtapa(card);
}

/**
 * Le um campo numerico com ate duas casas decimais. Devolve { valor } ou
 * { msg } com o motivo da recusa.
 */
function lerNumero(input, nomeCampo, min, max) {
    const texto = input.value.trim();
    if (texto === '') {
        // Campo com texto invalido (ex.: letras) chega vazio: validity diferencia.
        return { msg: input.validity.badInput
            ? `O campo ${nomeCampo} tem um valor inválido. Use apenas números.`
            : `Preencha o campo ${nomeCampo}.` };
    }
    const valor = Number(texto);
    if (!/^\d+(\.\d{1,2})?$/.test(texto) || valor < min || valor > max) {
        return { msg: `${nomeCampo}: informe um valor de ${formatar(min, 2)} a ${formatar(max, 2)}, com até duas casas decimais.` };
    }
    return { valor };
}

/**
 * Le a tela de uma etapa. Devolve { dados, erros }: `dados` e o objeto que vai
 * para o calculo, e so existe quando `erros` esta vazio.
 *
 * As aprovacoes sao opcionais uma a uma (a escola pode nao ter o ano), mas a
 * etapa precisa de ao menos uma. Ano em branco fica de fora da media.
 */
function lerEtapa(chave) {
    const de = ETAPA_NAS_MENSAGENS[chave];
    const erros = [];
    const campo = (sufixo) => document.getElementById(`inp-${chave}-${sufixo}`);

    const aprovacoes = [];
    ANOS_DA_ETAPA[chave].forEach((ano, i) => {
        const input = campo(`ap-${i + 1}`);
        if (input.value.trim() === '' && !input.validity.badInput) {
            aprovacoes.push(null);
            return;
        }
        const taxa = lerNumero(input, `Aprovação (${ano}) ${de}`, APROVACAO_MIN, APROVACAO_MAX);
        if (taxa.msg) erros.push({ alvo: input, msg: taxa.msg });
        aprovacoes.push(taxa.valor);
    });
    if (aprovacoes.every((taxa) => taxa === null)) {
        erros.push({ alvo: document.getElementById(`grade-${chave}-ap`), msg: `Informe a taxa de aprovação de ao menos um ano ${de}.` });
    }

    const limites = LIMITES_SAEB[chave];
    const lp = lerNumero(campo('lp'), `Proficiência em Língua Portuguesa ${de}`, limites.lp.inf, limites.lp.sup);
    if (lp.msg) erros.push({ alvo: campo('lp'), msg: lp.msg });
    const mt = lerNumero(campo('mt'), `Proficiência em Matemática ${de}`, limites.mt.inf, limites.mt.sup);
    if (mt.msg) erros.push({ alvo: campo('mt'), msg: mt.msg });

    if (erros.length > 0) return { dados: null, erros };
    return { dados: { aprovacoes, lp: lp.valor, mt: mt.valor }, erros };
}

/* Mensagem em vermelho e caixa alta logo abaixo do campo ou da grade. */
function mostrarErrosDeCampo(erros) {
    erros.forEach(({ alvo, msg }) => {
        const ehCampo = alvo.tagName === 'INPUT';
        const caixa = ehCampo ? alvo.closest('.input-campo') : alvo;
        const p = document.createElement('p');
        p.className = 'erro-campo';
        p.setAttribute('role', 'alert');
        p.textContent = msg;
        caixa.appendChild(p);
        caixa.classList.add('com-erro');
        if (ehCampo) alvo.setAttribute('aria-invalid', 'true');
    });
    const primeiro = erros[0].alvo;
    primeiro.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (primeiro.tagName === 'INPUT') primeiro.focus({ preventScroll: true });
}

function limparErros(raiz) {
    raiz.querySelectorAll('.erro-campo').forEach((el) => el.remove());
    raiz.querySelectorAll('.com-erro').forEach((el) => el.classList.remove('com-erro'));
    raiz.classList.remove('com-erro');
    raiz.querySelectorAll('[aria-invalid]').forEach((el) => el.removeAttribute('aria-invalid'));
}

/* Digitar de novo num campo apaga a mensagem dele e a da grade, se houver. */
document.addEventListener('input', (e) => {
    const caixa = e.target.closest('.input-campo');
    if (caixa) limparErros(caixa);
    const grade = e.target.closest('.grade-aprovacoes');
    if (grade) {
        grade.querySelectorAll(':scope > .erro-campo').forEach((el) => el.remove());
        grade.classList.remove('com-erro');
    }
});

/** Numero no formato brasileiro: 5,63 -> "5,63". */
function formatar(valor, casas) {
    return arredondar(valor, casas).toFixed(casas).replace('.', ',');
}

function montarResumo() {
    let html = '<h2 class="resumo-titulo">Resumo das Informações</h2>'
        + '<p class="pergunta-instrucao">Confira os dados antes de ver o resultado. Para corrigir algo, use Voltar.</p>';

    estado.etapas.forEach((chave) => {
        const dados = estado.dados[chave];
        const aprovacoes = ANOS_DA_ETAPA[chave]
            .map((ano, i) => `${ano}: ${dados.aprovacoes[i] === null ? 'em branco' : `${formatar(dados.aprovacoes[i], 2)}%`}`)
            .join(' · ');
        html += `
            <div class="resumo-etapa etapa-${chave}">
                <strong class="etapa-nome etapa-${chave}">${NOME_ETAPA[chave]}</strong>
                <ul>
                    <li>Aprovação — ${aprovacoes}</li>
                    <li>SAEB — Língua Portuguesa: ${formatar(dados.lp, 2)} · Matemática: ${formatar(dados.mt, 2)}</li>
                </ul>
            </div>`;
    });
    return html;
}

function mostrarResumo() {
    estado.resultados = {};
    estado.etapas.forEach((chave) => {
        const dados = estado.dados[chave];
        estado.resultados[chave] = calcularIdeb(chave, {
            aprovacoes: dados.aprovacoes.filter((taxa) => taxa !== null),
            lp: dados.lp,
            mt: dados.mt,
        });
    });
    estado.stepAtual = PASSO_RESUMO;
    document.getElementById('resumo-area').innerHTML = montarResumo();
    atualizarUI();
}

const MENSAGEM_RESULTADO =
    'O IDEB vai de 0 a 10 e é o produto do aprendizado (N), medido pelas notas do SAEB, pelo fluxo (P), medido pelas taxas de aprovação. Para subir o IDEB, as duas partes contam: estudantes aprendendo mais e sendo aprovados na idade certa.';

function mostrarResultado() {
    estado.stepAtual = PASSO_RESULTADO;
    atualizarUI();

    const selos = estado.etapas.map((chave) => {
        const r = estado.resultados[chave];
        return `
            <div class="selo-etapa etapa-${chave}">
                <div class="resultado-badge">
                    <span class="percentual">${formatar(r.ideb, 1)}</span>
                    <span class="label-pct">IDEB</span>
                </div>
                <strong class="etapa-nome etapa-${chave}">${NOME_ETAPA[chave]}</strong>
                <p class="selo-conta">Aprendizado (N) ${formatar(r.nota_saeb, 2)}<br>× Fluxo (P) ${formatar(r.rendimento, 2)}</p>
            </div>`;
    }).join('');

    document.getElementById('resultado-area').innerHTML = `
        <h2 class="resultado-titulo">IDEB simulado da escola</h2>
        <div class="selos">${selos}</div>
        <p class="resultado-mensagem">${MENSAGEM_RESULTADO}</p>
        <button class="btn btn-reiniciar" onclick="reiniciar()">Simular outra escola</button>
    `;
}

function reiniciar() {
    estado.stepAtual = PASSO_ETAPAS;
    estado.etapas = [];
    estado.dados = {};
    estado.resultados = {};
    document.querySelectorAll('.opcao-card').forEach(c => {
        c.classList.remove('selecionado');
        c.setAttribute('aria-checked', 'false');
    });
    limparErros(document.getElementById('area-conteudo'));
    document.querySelectorAll('.step input').forEach(i => i.value = '');
    atualizarUI();
}

/* =====================================================================
   Popups
   ===================================================================== */

function abrirPopup(id) {
    document.getElementById(id).classList.add('ativo');
    document.body.style.overflow = 'hidden';
}

function fecharPopup(event, id) {
    if (event.target === event.currentTarget) fecharPopupDireto(id);
}

function fecharPopupDireto(id) {
    document.getElementById(id).classList.remove('ativo');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.popup-overlay.ativo').forEach(p => p.classList.remove('ativo'));
        document.body.style.overflow = '';
    }
});
