/* ============================================================================
   Wizard BDE — Navegação, API e Gamificação
   ============================================================================ */

/* Indices fixos no template. O numero de telas visiveis varia com as etapas
   pactuadas, entao quem manda no progresso e passosVisiveis(), nao o indice. */
const PASSO_ETAPAS = 0;
const PASSO_EQUIDADE = 4;
const PASSO_RESUMO = 5;
const PASSO_RESULTADO = 6;

const PASSO_DA_ETAPA = { ai: 1, af: 2, em: 3 };

/* Nomes das etapas como aparecem nas mensagens: "dos Anos Iniciais". */
const ETAPA_NAS_MENSAGENS = { ai: 'dos Anos Iniciais', af: 'dos Anos Finais', em: 'do Ensino Médio' };

/* Limites dos campos. Os mesmos valem no backend, em src/bde/schemas.py. */
const LIMITES = {
    matriculas: { min: 10, max: 300000 },
    meta: { min: 2, max: 6 },
    resultado: { min: 0, max: 10 },
};

const estado = {
    stepAtual: 0,
    resultadoApi: null,
    /* A participacao vive fora de respostas.etapa_* porque e respondida antes
       de a etapa estar completa — e a etapa so vira objeto quando valida. */
    participacao: { ai: null, af: null, em: null },
    respostas: {
        etapas_selecionadas: [],
        etapa_ai: null,
        etapa_af: null,
        etapa_em: null,
        reduziu_desigualdade: null,
        terco_menor_elementares: null,
    },
};

/** Telas efetivamente alcancaveis, na ordem. */
function passosVisiveis() {
    const passos = [PASSO_ETAPAS];
    ['ai', 'af', 'em'].forEach((chave) => {
        if (estado.respostas.etapas_selecionadas.includes(chave)) {
            passos.push(PASSO_DA_ETAPA[chave]);
        }
    });
    return passos.concat([PASSO_EQUIDADE, PASSO_RESUMO, PASSO_RESULTADO]);
}

document.addEventListener('DOMContentLoaded', () => {
    ajustarEspacoDoRodape();
    atualizarUI();
});

/**
 * O rodape e position:fixed, e o .wizard-container reserva 80px embaixo para
 * nao passar por baixo dele. Em tela estreita o rodape passa de 80px — os dois
 * botoes e o credito quebram em varias linhas — e ai ele cobre o "Proximo".
 * A 390px o rodape mede 146px e o botao da etapa de equidade fica embaixo
 * dele, sem como ser clicado.
 *
 * Reserva a altura real, medida. O max(80) mantem o espaco original nas telas
 * onde o rodape ja cabia.
 */
function ajustarEspacoDoRodape() {
    const rodape = document.querySelector('.footer');
    const container = document.querySelector('.wizard-container');
    if (!rodape || !container) return;
    const altura = rodape.getBoundingClientRect().height + 16;
    container.style.paddingBottom = `${Math.max(80, Math.round(altura))}px`;
}

window.addEventListener('resize', ajustarEspacoDoRodape);

/* Redesenhado a cada atualizacao porque a quantidade de telas muda conforme
   as etapas pactuadas. */
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
    const pos = Math.max(0, visiveis.indexOf(stepAtual));
    const percentual = totalSteps > 1 ? Math.round((pos / (totalSteps - 1)) * 100) : 100;

    renderizarDots(totalSteps);

    const barra = document.getElementById('barra-progresso');
    barra.style.width = `${percentual}%`;
    barra.style.background = corBarra(corFase(pos, totalSteps));

    document.getElementById('lbl-etapa').textContent = `Passo ${pos + 1} de ${totalSteps}`;
    document.getElementById('lbl-progresso').textContent = `${percentual}%`;

    for (let i = 0; i < totalSteps; i++) {
        const dot = document.getElementById(`dot-${i}`);
        if (!dot) continue;
        dot.className = 'dot';
        const fase = corFase(i, totalSteps);
        if (fase === 'dourado') dot.classList.add('fase-dourado');
        if (fase === 'verde') dot.classList.add('fase-verde');
        if (i < pos) dot.classList.add('completo');
        if (i === pos) dot.classList.add('ativo');
    }

    document.querySelectorAll('.step').forEach(s => s.style.display = 'none');
    const stepEl = document.querySelector(`.step[data-step="${stepAtual}"]`);
    if (stepEl) {
        stepEl.style.display = 'flex';
        stepEl.style.flexDirection = 'column';
        stepEl.style.justifyContent = 'center';
        stepEl.style.animation = 'none';
        stepEl.offsetHeight;
        stepEl.style.animation = 'fadeSlideUp .35s ease-out';
    }

    const btnVoltar = document.getElementById('btn-voltar');
    const btnProximo = document.getElementById('btn-proximo');

    const ehResultado = stepAtual === PASSO_RESULTADO;
    const ehResumo = stepAtual === PASSO_RESUMO;

    btnVoltar.style.display = stepAtual > 0 && !ehResultado ? 'flex' : 'none';

    if (ehResultado) {
        btnProximo.style.display = 'none';
    } else if (ehResumo) {
        btnProximo.style.display = 'flex';
        btnProximo.textContent = 'Ver Resultado';
        btnProximo.className = 'btn btn-resultado';
        btnProximo.disabled = false;
        btnProximo.onclick = () => {
            mostrarResultado(estado.resultadoApi);
        };
    } else {
        btnProximo.style.display = 'flex';
        btnProximo.textContent = 'Próximo';
        btnProximo.className = 'btn btn-proximo';
        btnProximo.disabled = false;
        btnProximo.onclick = proximo;
    }
}

/**
 * Confere o passo atual e devolve os erros encontrados, cada um com o
 * elemento onde a mensagem aparece. Lista vazia = pode avancar.
 */
function validarPasso(step) {
    if (step === PASSO_ETAPAS) {
        return estado.respostas.etapas_selecionadas.length > 0
            ? []
            : [{ alvo: document.getElementById('opcoes-etapas'), msg: 'Marque ao menos uma etapa para continuar.' }];
    }
    const prefixo = Object.keys(PASSO_DA_ETAPA).find((k) => PASSO_DA_ETAPA[k] === step);
    if (prefixo) return lerEtapa(prefixo).erros;
    if (step === PASSO_EQUIDADE) {
        const erros = [];
        if (estado.respostas.reduziu_desigualdade === null) {
            erros.push({ alvo: document.getElementById('bloco-reduziu_desigualdade'), msg: 'Responda Sim ou Não à pergunta sobre a evolução dos estudantes PPI e de nível socioeconômico mais baixo.' });
        }
        if (estado.respostas.terco_menor_elementares === null) {
            erros.push({ alvo: document.getElementById('bloco-terco_menor_elementares'), msg: 'Responda Sim ou Não à pergunta sobre o 1º terço de elementares.' });
        }
        return erros;
    }
    return [];
}

function proximo() {
    const step = estado.stepAtual;
    limparErros(document.querySelector(`.step[data-step="${step}"]`));
    const erros = validarPasso(step);
    if (erros.length > 0) {
        mostrarErrosDeCampo(erros);
        return;
    }

    const prefixo = Object.keys(PASSO_DA_ETAPA).find((k) => PASSO_DA_ETAPA[k] === step);
    if (prefixo) estado.respostas[`etapa_${prefixo}`] = lerEtapa(prefixo).dados;

    if (step === PASSO_EQUIDADE) {
        enviarSimulacao();
        return;
    }

    estado.stepAtual++;
    while (devePularStep(estado.stepAtual) && estado.stepAtual < PASSO_RESUMO) {
        estado.stepAtual++;
    }
    atualizarUI();
}

function voltar() {
    if (estado.stepAtual <= 0) return;
    estado.stepAtual--;
    while (devePularStep(estado.stepAtual) && estado.stepAtual > 0) {
        estado.stepAtual--;
    }
    atualizarUI();
}

function devePularStep(step) {
    if (step === 1) return !estado.respostas.etapas_selecionadas.includes('ai');
    if (step === 2) return !estado.respostas.etapas_selecionadas.includes('af');
    if (step === 3) return !estado.respostas.etapas_selecionadas.includes('em');
    return false;
}

/* Os dados da etapa so passam a existir quando a tela dela e validada, no
   Proximo. Marcar a etapa aqui nao cria dados vazios. */
function toggleOpcao(card) {
    const campo = card.dataset.campo;
    const marcado = card.classList.toggle('selecionado');
    card.setAttribute('aria-checked', String(marcado));
    const chave = campo.replace('etapa_', '');
    if (marcado) {
        estado.respostas.etapas_selecionadas.push(chave);
    } else {
        estado.respostas.etapas_selecionadas.splice(estado.respostas.etapas_selecionadas.indexOf(chave), 1);
        estado.respostas[campo] = null;
    }
    limparErros(document.getElementById('opcoes-etapas').parentElement);
    atualizarUI();
}

/* Espaco e Enter marcam a etapa, como numa caixa de selecao. */
function teclaNaOpcao(e, card) {
    if (e.key !== ' ' && e.key !== 'Enter') return;
    e.preventDefault();
    toggleOpcao(card);
}

function toggleSimNaoPergunta(btn) {
    const campo = btn.dataset.campo;
    const valor = btn.dataset.valor === 'true';

    btn.parentElement.querySelectorAll('.btn-simnao').forEach(b => b.classList.remove('selecionado'));
    btn.classList.add('selecionado');

    estado.respostas[campo] = valor;
    limparErros(document.getElementById(`bloco-${campo}`));
    atualizarUI();
}

/**
 * Participacao da etapa. No Sim aparece o resultado; no Nao ele some, porque o
 * IDEPE da etapa e considerado zero, e entra o aviso explicando isso. A meta
 * fica na tela nos dois casos: ela entra na conta de qualquer jeito.
 */
function toggleParticipacaoEtapa(btn) {
    const prefixo = btn.dataset.campo;
    const participou = btn.dataset.valor === 'true';

    btn.parentElement.querySelectorAll('.btn-simnao').forEach(b => b.classList.remove('selecionado'));
    btn.classList.add('selecionado');

    estado.participacao[prefixo] = participou;
    document.getElementById(`idepe-${prefixo}`).style.display = participou ? 'flex' : 'none';
    document.getElementById(`aviso-${prefixo}`).style.display = participou ? 'none' : 'block';

    if (!participou) {
        document.getElementById(`inp-${prefixo}-res`).value = '';
        limparErros(document.getElementById(`idepe-${prefixo}`));
    }

    limparErros(document.getElementById(`bloco-${prefixo}-part`));
    ajustarEspacoDoRodape();
}

/**
 * Le um campo numerico. `decimais` e o maximo de casas depois da virgula.
 * Devolve { valor } ou { msg } com o motivo da recusa.
 */
function lerNumero(input, nomeCampo, limite, decimais) {
    const texto = input.value.trim();
    if (texto === '') {
        // Campo com texto invalido (ex.: letras) chega vazio: validity diferencia.
        return { msg: input.validity.badInput
            ? `O campo ${nomeCampo} tem um valor inválido. Use apenas números.`
            : `Preencha o campo ${nomeCampo}.` };
    }
    const formato = decimais === 0 ? /^\d+$/ : new RegExp(`^\\d+(\\.\\d{1,${decimais}})?$`);
    const faixa = decimais === 0
        ? `um número inteiro de ${limite.min.toLocaleString('pt-BR')} a ${limite.max.toLocaleString('pt-BR')}`
        : `um valor de ${limite.min.toFixed(2).replace('.', ',')} a ${limite.max.toFixed(2).replace('.', ',')}, com até duas casas decimais`;
    const valor = Number(texto);
    if (!formato.test(texto) || valor < limite.min || valor > limite.max) {
        return { msg: `${nomeCampo}: informe ${faixa}.` };
    }
    return { valor };
}

/**
 * Le a tela de uma etapa. Devolve { dados, erros }: `dados` e o objeto que vai
 * para o calculo, e so existe quando `erros` esta vazio.
 */
function lerEtapa(prefixo) {
    const de = ETAPA_NAS_MENSAGENS[prefixo];
    const erros = [];
    const campo = (sufixo) => document.getElementById(`inp-${prefixo}-${sufixo}`);

    const mat = lerNumero(campo('mat'), `Matrículas 2026 ${de}`, LIMITES.matriculas, 0);
    if (mat.msg) erros.push({ alvo: campo('mat'), msg: mat.msg });
    const meta = lerNumero(campo('meta'), `Meta IDEPE 2026 ${de}`, LIMITES.meta, 2);
    if (meta.msg) erros.push({ alvo: campo('meta'), msg: meta.msg });

    const participou = estado.participacao[prefixo];
    if (participou === null) {
        erros.push({ alvo: document.getElementById(`bloco-${prefixo}-part`), msg: `Responda se a participação ${de} atingiu 80%.` });
    }
    let res = {};
    if (participou) {
        res = lerNumero(campo('res'), `Resultado IDEPE 2026 ${de}`, LIMITES.resultado, 2);
        if (res.msg) erros.push({ alvo: campo('res'), msg: res.msg });
    }

    if (erros.length > 0) return { dados: null, erros };
    // Etapa sem 80% entra com IDEPE zero: nao tem resultado a informar.
    const dados = { matriculas: mat.valor, participacao_maior_80: participou, meta: meta.valor };
    if (participou) dados.resultado = res.valor;
    return { dados, erros };
}

/* Mensagem em vermelho e caixa alta logo abaixo do campo ou da pergunta. */
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
    if (raiz.classList.contains('com-erro')) raiz.classList.remove('com-erro');
    raiz.querySelectorAll('[aria-invalid]').forEach((el) => el.removeAttribute('aria-invalid'));
}

/* Digitar de novo num campo apaga a mensagem dele. */
document.addEventListener('input', (e) => {
    const caixa = e.target.closest('.input-campo');
    if (caixa) limparErros(caixa);
});

async function enviarSimulacao() {
    const btn = document.getElementById('btn-proximo');
    btn.disabled = true;
    btn.textContent = 'Calculando...';

    const payload = {};
    if (estado.respostas.etapas_selecionadas.includes('ai')) payload.etapa_ai = estado.respostas.etapa_ai;
    if (estado.respostas.etapas_selecionadas.includes('af')) payload.etapa_af = estado.respostas.etapa_af;
    if (estado.respostas.etapas_selecionadas.includes('em')) payload.etapa_em = estado.respostas.etapa_em;
    payload.reduziu_desigualdade = estado.respostas.reduziu_desigualdade;
    payload.terco_menor_elementares = estado.respostas.terco_menor_elementares;
    // A participacao vai dentro de cada etapa, nao mais solta no payload.

    try {
        const resp = await fetch('/api/v1/simular-bde', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Erro ao calcular BDE.');
        }
        estado.resultadoApi = await resp.json();
        mostrarResumo();
    } catch (e) {
        mostrarErro(e.message);
        btn.disabled = false;
        btn.textContent = 'Próximo';
    }
}

function montarResumo() {
    const r = estado.respostas;
    const etapasNomes = { ai: 'Anos Iniciais', af: 'Anos Finais', em: 'Ensino Médio' };
    let html = '<h2 class="resumo-titulo">Resumo das Informações</h2>'
        + '<p class="pergunta-instrucao">Confira os dados antes de ver o resultado. Para corrigir algo, use Voltar.</p>';

    r.etapas_selecionadas.forEach(chave => {
        const dados = r[`etapa_${chave}`];
        if (!dados) return;

        // Sem 80% de participacao o IDEPE considerado e zero.
        const idepe = dados.participacao_maior_80 ? dados.resultado : 0;
        const rotuloIdepe = dados.participacao_maior_80
            ? `Resultado: ${idepe}`
            : 'Resultado: 0 (sem 80% de participação)';
        const variacao = (idepe - dados.meta).toFixed(2);
        const sinal = parseFloat(variacao) >= 0 ? '+' : '';
        html += `
            <div class="resumo-item ${parseFloat(variacao) >= 0 ? 'sim' : 'nao'}">
                <div class="resumo-icone">${parseFloat(variacao) >= 0 ? '+' : '-'}</div>
                <div class="resumo-texto">
                    <strong class="etapa-nome etapa-${chave}">${etapasNomes[chave]}</strong> — Meta: ${dados.meta} | ${rotuloIdepe} | Diferença Meta-Resultado: ${sinal}${variacao}
                </div>
            </div>`;
    });

    const eq = r.reduziu_desigualdade;
    const el = r.terco_menor_elementares;
    const part = estado.resultadoApi.bonus_participacao > 0;

    html += `
        <div class="resumo-item ${eq ? 'sim' : 'nao'}">
            <div class="resumo-icone">${eq ? '+' : '-'}</div>
            <div class="resumo-texto"><strong>Equidade:</strong> ${eq ? 'Houve evolução de PPI e renda/NSE' : 'Não houve evolução de equidade'}</div>
        </div>
        <div class="resumo-item ${el ? 'sim' : 'nao'}">
            <div class="resumo-icone">${el ? '+' : '-'}</div>
            <div class="resumo-texto"><strong>Elementares:</strong> ${el ? 'Escola está no 1º terço com menor % de elementares' : 'Escola não está no 1º terço'}</div>
        </div>
        <div class="resumo-item ${part ? 'sim' : 'nao'}">
            <div class="resumo-icone">${part ? '+' : '-'}</div>
            <div class="resumo-texto"><strong>Participação:</strong> ${part ? 'Todas as etapas atingiram >= 80% no SAEPE' : 'Ao menos uma etapa não atingiu 80% de participação'}</div>
        </div>`;

    const motivos = [];
    // Abaixo de -0,3 a tabela da 0%: ai a escola nao esta na faixa.
    if (estado.resultadoApi.percentual_idepe > 0) motivos.push('Está na faixa de bonificação');
    if (eq) motivos.push('Reduziu desigualdades de PPI e renda');
    else if (el) motivos.push('Está entre as escolas com menor % de estudantes nos padrões elementares');
    if (part) motivos.push('Atingiu participação igual ou superior a 80%');

    if (motivos.length > 0) {
        html += `
            <div class="resumo-motivo">
                <strong>Critérios considerados na avaliação</strong>
                <ul>${motivos.map((m) => `<li>${m}</li>`).join('')}</ul>
            </div>`;
    }

    return html;
}

function mostrarResumo() {
    estado.stepAtual = PASSO_RESUMO;
    document.getElementById('resumo-area').innerHTML = montarResumo();
    atualizarUI();
}

const MENSAGEM_PARABENS =
    'Parabenizamos a escola pelo seu empenho e participação na educação dos jovens que compõem o presente e o futuro de nossa nação. Esperamos que essa premiação possa incentivar a buscar cada vez mais excelência, de forma a alcançar os resultados da educação esperados.';
const MENSAGEM_INCENTIVO =
    'De acordo com os dados inseridos, sua escola não possui os resultados necessários para uma bonificação mais alta. Continue se esforçando para melhorar os resultados futuros.';

function mostrarResultado(r) {
    estado.stepAtual = PASSO_RESULTADO;
    atualizarUI();

    const apto = r.apto_a_receber;
    const badgeCor = apto
        ? (r.percentual_bde >= 2.0 ? 'var(--verde)' : r.percentual_bde >= 1.0 ? 'var(--dourado)' : 'var(--amarelo)')
        : 'var(--vermelho)';
    const mensagem = r.percentual_bde >= 1.0 ? MENSAGEM_PARABENS : MENSAGEM_INCENTIVO;

    document.getElementById('resultado-area').innerHTML = `
        <div class="resultado-badge ${apto ? '' : 'badge-nao-apto'}" style="background: ${badgeCor}; color: white;">
            <span class="percentual">${r.percentual_formatado}</span>
            <span class="label-pct">BDE</span>
        </div>
        <h2 class="resultado-titulo">${apto ? 'Escola apta a receber o BDE' : 'Escola não atingiu o mínimo'}</h2>
        <p class="resultado-mensagem">${mensagem}</p>
        <button class="btn btn-reiniciar" onclick="reiniciar()">Simular outra escola</button>
    `;
}

function reiniciar() {
    estado.stepAtual = PASSO_ETAPAS;
    estado.resultadoApi = null;
    estado.participacao = { ai: null, af: null, em: null };
    estado.respostas = {
        etapas_selecionadas: [],
        etapa_ai: null,
        etapa_af: null,
        etapa_em: null,
        reduziu_desigualdade: null,
        terco_menor_elementares: null,
    };
    document.querySelectorAll('.opcao-card').forEach(c => {
        c.classList.remove('selecionado');
        c.setAttribute('aria-checked', 'false');
    });
    limparErros(document.getElementById('area-conteudo'));
    document.querySelectorAll('.btn-simnao').forEach(b => b.classList.remove('selecionado'));
    document.querySelectorAll('.input-campo input').forEach(i => i.value = '');
    ['ai', 'af', 'em'].forEach((prefixo) => {
        document.getElementById(`idepe-${prefixo}`).style.display = 'none';
        document.getElementById(`aviso-${prefixo}`).style.display = 'none';
    });
    document.getElementById('btn-proximo').style.display = 'flex';
    document.getElementById('btn-proximo').textContent = 'Próximo';
    document.getElementById('btn-proximo').className = 'btn btn-proximo';
    atualizarUI();
}

function mostrarErro(msg) {
    const toast = document.getElementById('toast-erro');
    toast.textContent = msg;
    toast.classList.add('visivel');
    setTimeout(() => toast.classList.remove('visivel'), 4000);
}

/* =====================================================================
   Popups
   ===================================================================== */

function abrirPopup(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.add('ativo');
        document.body.style.overflow = 'hidden';
    }
}

function fecharPopup(event, id) {
    if (event.target === event.currentTarget) {
        fecharPopupDireto(id);
    }
}

function fecharPopupDireto(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('ativo');
        document.body.style.overflow = '';
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.popup-overlay.ativo').forEach(p => {
            p.classList.remove('ativo');
        });
        document.body.style.overflow = '';
    }
});
