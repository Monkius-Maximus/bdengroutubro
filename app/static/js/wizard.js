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
        btnProximo.disabled = !stepValido(stepAtual);
        btnProximo.onclick = proximo;
    }
}

function stepValido(step) {
    switch (step) {
        case PASSO_ETAPAS: return estado.respostas.etapas_selecionadas.length > 0;
        case 1: return estado.respostas.etapa_ai !== null;
        case 2: return estado.respostas.etapa_af !== null;
        case 3: return estado.respostas.etapa_em !== null;
        case PASSO_EQUIDADE:
            return estado.respostas.reduziu_desigualdade !== null
                && estado.respostas.terco_menor_elementares !== null;
        default: return true;
    }
}

function proximo() {
    if (!stepValido(estado.stepAtual)) return;

    if (estado.stepAtual === PASSO_EQUIDADE) {
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

function toggleOpcao(card) {
    const campo = card.dataset.campo;
    card.classList.toggle('selecionado');
    const chave = campo.replace('etapa_', '');
    const idx = estado.respostas.etapas_selecionadas.indexOf(chave);
    if (idx >= 0) {
        estado.respostas.etapas_selecionadas.splice(idx, 1);
        estado.respostas[campo] = null;
    } else {
        estado.respostas.etapas_selecionadas.push(chave);
        estado.respostas[campo] = {};
    }
    atualizarUI();
}

function toggleSimNaoPergunta(btn) {
    const campo = btn.dataset.campo;
    const valor = btn.dataset.valor === 'true';

    btn.parentElement.querySelectorAll('.btn-simnao').forEach(b => b.classList.remove('selecionado'));
    btn.classList.add('selecionado');

    estado.respostas[campo] = valor;
    atualizarUI();
}

/**
 * Participacao da etapa. E um portao: no Sim aparecem meta e resultado; no Nao
 * eles somem, porque o IDEPE da etapa nao e divulgado, e entra o aviso de que
 * ela ainda pesa na conta com 0% de atingimento.
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
        document.getElementById(`inp-${prefixo}-meta`).value = '';
        document.getElementById(`inp-${prefixo}-res`).value = '';
    }

    recalcularEtapa(prefixo, true);
    ajustarEspacoDoRodape();
}

/**
 * `silencioso` existe porque a validacao roda tambem em momentos em que o
 * campo vazio e o estado normal — logo apos marcar "Sim" na participacao, por
 * exemplo, quando meta e resultado ainda nem apareceram na tela. Reclamar ali
 * seria acusar a pessoa de nao ter digitado o que acabou de surgir.
 */
function validarInputsEtapa(prefixo, silencioso = false) {
    const reclamar = (msg) => { if (!silencioso) mostrarErro(msg); return null; };

    const participou = estado.participacao[prefixo];
    if (participou === null) return null;

    const mat = parseFloat(document.getElementById(`inp-${prefixo}-mat`).value);
    if (!mat || mat <= 0) {
        return reclamar('Informe as matrículas da etapa (maior que zero).');
    }

    // Etapa sem 80% nao tem IDEPE divulgado: matricula e tudo que existe dela.
    if (!participou) {
        return { matriculas: Math.round(mat), participacao_maior_80: false };
    }

    const meta = parseFloat(document.getElementById(`inp-${prefixo}-meta`).value);
    const res = parseFloat(document.getElementById(`inp-${prefixo}-res`).value);
    if (isNaN(meta) || isNaN(res) || meta <= 0 || res <= 0) {
        return reclamar('Preencha meta e resultado IDEPE com valores válidos (maiores que zero).');
    }
    return {
        matriculas: Math.round(mat),
        participacao_maior_80: true,
        meta,
        resultado: res,
    };
}

/** Revalida a etapa e guarda o objeto (ou null) em estado.respostas. */
function recalcularEtapa(prefixo, silencioso = false) {
    estado.respostas[`etapa_${prefixo}`] = validarInputsEtapa(prefixo, silencioso);
    atualizarUI();
}

document.addEventListener('focusout', (e) => {
    if (!e.target.matches('.input-campo input')) return;
    const step = e.target.closest('.step');
    if (!step) return;
    const stepNum = parseInt(step.dataset.step);
    let prefixo = null;
    if (stepNum === 1) prefixo = 'ai';
    if (stepNum === 2) prefixo = 'af';
    if (stepNum === 3) prefixo = 'em';
    if (!prefixo) return;

    // So valida quando os campos esperados tem algo digitado: sair de
    // "Matriculas" para preencher "Meta" nao e erro, e o toast a cada tab era
    // ruido. Etapa sem participacao espera so a matricula.
    const esperados = estado.participacao[prefixo] ? ['mat', 'meta', 'res'] : ['mat'];
    const preenchidos = esperados.every(function (campo) {
        return document.getElementById(`inp-${prefixo}-${campo}`).value.trim() !== '';
    });
    if (!preenchidos) {
        estado.respostas[`etapa_${prefixo}`] = null;
        atualizarUI();
        return;
    }
    recalcularEtapa(prefixo);
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
    let html = '<h2 class="resumo-titulo">Resumo das Informações</h2>';

    r.etapas_selecionadas.forEach(chave => {
        const dados = r[`etapa_${chave}`];
        if (!dados) return;

        if (!dados.participacao_maior_80) {
            html += `
                <div class="resumo-item nao">
                    <div class="resumo-icone">-</div>
                    <div class="resumo-texto">
                        <strong>${etapasNomes[chave]}</strong> — Sem participação de 80%: IDEPE não divulgado. Entra com 0% de atingimento, pesando ${dados.matriculas} matrículas.
                    </div>
                </div>`;
            return;
        }

        const variacao = (dados.resultado - dados.meta).toFixed(2);
        const sinal = parseFloat(variacao) >= 0 ? '+' : '';
        html += `
            <div class="resumo-item ${parseFloat(variacao) >= 0 ? 'sim' : 'nao'}">
                <div class="resumo-icone">${parseFloat(variacao) >= 0 ? '+' : '-'}</div>
                <div class="resumo-texto">
                    <strong>${etapasNomes[chave]}</strong> — Meta: ${dados.meta} | Resultado: ${dados.resultado} | Variação: ${sinal}${variacao}
                </div>
            </div>`;
    });

    const eq = r.reduziu_desigualdade;
    const el = r.terco_menor_elementares;
    const part = ['ai', 'af', 'em'].some((chave) => {
        const d = r[`etapa_${chave}`];
        return d && d.participacao_maior_80;
    });

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
            <div class="resumo-texto"><strong>Participação:</strong> ${part ? 'Ao menos uma etapa atingiu >= 80% no SAEPE' : 'Nenhuma etapa atingiu 80% de participação'}</div>
        </div>`;

    const motivos = [];
    // So as etapas com 80% tem IDEPE para comparar com a meta.
    const comIdepe = r.etapas_selecionadas
        .map((k) => r[`etapa_${k}`])
        .filter((d) => d && d.participacao_maior_80);

    if (comIdepe.length > 0) {
        const diffs = comIdepe.map((d) => d.resultado - d.meta);
        const media = diffs.reduce((a, b) => a + b, 0) / diffs.length;
        if (media >= 0.4) motivos.push('superou a meta em 0.4 pontos ou mais');
        else if (media >= 0.1) motivos.push('superou a meta');
        else if (media >= 0) motivos.push('atingiu ou está próximo da meta');
        else motivos.push('ficou abaixo da meta');
    } else {
        motivos.push('não teve IDEPE divulgado em nenhuma etapa, por falta de participação');
    }
    if (eq) motivos.push('reduziu desigualdades de PPI e renda');
    if (el) motivos.push('está entre as escolas com menor % de estudantes nos padrões elementares');
    if (part) motivos.push('atingiu participação igual ou superior a 80%');

    if (motivos.length > 0) {
        html += `
            <div class="resumo-motivo">
                <strong>Por que sua escola pode receber o BDE?</strong><br>
                Porque ${motivos.join(', ')}.
            </div>`;
    }

    return html;
}

function mostrarResumo() {
    estado.stepAtual = PASSO_RESUMO;
    document.getElementById('resumo-area').innerHTML = montarResumo();
    atualizarUI();
}

function corKPI(valor) {
    if (valor >= 2.0) return 'kpi-verde';
    if (valor >= 1.0) return 'kpi-dourado';
    return 'kpi-vermelho';
}

function mostrarResultado(r) {
    estado.stepAtual = PASSO_RESULTADO;
    atualizarUI();

    const apto = r.apto_a_receber;
    const badgeCor = apto
        ? (r.percentual_bde >= 2.0 ? 'var(--verde)' : r.percentual_bde >= 1.0 ? 'var(--dourado)' : 'var(--amarelo)')
        : 'var(--vermelho)';

    const clsIdepe = r.percentual_idepe >= 1.0 ? 'positivo' : r.percentual_idepe >= 0.75 ? 'neutro' : 'negativo';

    let etapasHtml = '';
    if (r.etapas && r.etapas.length > 0) {
        etapasHtml = '<div class="etapas-detalhe">';
        r.etapas.forEach(e => {
            // variacao nula e etapa sem IDEPE divulgado — diferente de zero,
            // que e a etapa que participou e empatou com a meta.
            if (e.variacao === null || e.variacao === undefined) {
                etapasHtml += `
                <div class="etapa-detalhe">
                    <span class="etapa-nome">${e.nome}</span>
                    <span class="etapa-variacao negativo">Sem participação (0%)</span>
                </div>`;
                return;
            }
            const cls = e.variacao > 0 ? 'positivo' : e.variacao === 0 ? 'neutro' : 'negativo';
            const sinal = e.variacao > 0 ? '+' : '';
            etapasHtml += `
                <div class="etapa-detalhe">
                    <span class="etapa-nome">${e.nome}</span>
                    <span class="etapa-variacao ${cls}">${sinal}${e.variacao.toFixed(4)} (${(e.percentual_atingimento * 100).toFixed(0)}%)</span>
                </div>`;
        });
        etapasHtml += '</div>';
    }

    document.getElementById('resultado-area').innerHTML = `
        <div class="resultado-badge ${apto ? '' : 'badge-nao-apto'}" style="background: ${badgeCor}; color: white;">
            <span class="percentual">${r.percentual_formatado}</span>
            <span class="label-pct">BDE</span>
        </div>
        <h2 class="resultado-titulo">${apto ? 'Escola apta a receber o BDE' : 'Escola não atingiu o mínimo'}</h2>
        <p class="resultado-subtitulo">${apto
            ? 'Confira o detalhamento do cálculo do seu bônus.'
            : 'A escola não atingiu percentual mínimo para receber o bônus.'}</p>
        <div class="detalhes-grid">
            <div class="detalhe-card" onclick="abrirPopupMetrica('media-idepe')" role="button" tabindex="0">
                <div class="detalhe-valor ${clsIdepe}">${(r.percentual_idepe * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Média IDEPE</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
            <div class="detalhe-card" onclick="abrirPopupMetrica('cota-resultado')" role="button" tabindex="0">
                <div class="detalhe-valor">${(r.cota_resultado * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Cota Resultado</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
            <div class="detalhe-card" onclick="abrirPopupMetrica('equidade')" role="button" tabindex="0">
                <div class="detalhe-valor ${r.bonus_equidade > 0 ? 'positivo' : 'negativo-bg'}">${(r.bonus_equidade * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Equidade</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
            <div class="detalhe-card" onclick="abrirPopupMetrica('elementares')" role="button" tabindex="0">
                <div class="detalhe-valor ${r.bonus_elementares > 0 ? 'positivo' : 'negativo-bg'}">${(r.bonus_elementares * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Elementares (1/3 inferior)</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
            <div class="detalhe-card" onclick="abrirPopupMetrica('participacao')" role="button" tabindex="0">
                <div class="detalhe-valor ${r.bonus_participacao > 0 ? 'positivo' : 'negativo-bg'}">${(r.bonus_participacao * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Participação ≥ 80%</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
            <div class="detalhe-card" onclick="abrirPopupMetrica('cota-bde')" role="button" tabindex="0">
                <div class="detalhe-valor">${(r.cota_bde_calculada * 100).toFixed(0)}%</div>
                <div class="detalhe-label">Cota BDE Calculada</div>
                <div class="detalhe-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
            </div>
        </div>
        ${etapasHtml}
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
    document.querySelectorAll('.opcao-card').forEach(c => c.classList.remove('selecionado'));
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
   Popups de Métricas (Step 7)
   ===================================================================== */

const METRICAS_CONTEUDO = {
    'media-idepe': {
        titulo: 'Média IDEPE',
        texto: 'A Média IDEPE parte da variação entre o resultado obtido e a meta pactuada, ponderada pelas matrículas, e é convertida em percentual por uma tabela — variações positivas rendem percentuais maiores, até 200%. Só entram nessa média as etapas que atingiram 80% de participação, porque as demais não têm IDEPE divulgado. O percentual resultante é então reduzido na proporção das matrículas que ficaram de fora: uma etapa sem participação não some da conta, ela entra com 0%.'
    },
    'cota-resultado': {
        titulo: 'Cota Resultado',
        texto: 'A Cota Resultado é a parcela do percentual IDEPE que equivale a até 100%, e representa o ganho base pelo desempenho. Se o percentual IDEPE passar de 100%, o excedente vai para a "Cota Além do Resultado" e não entra na soma do BDE — superar muito a meta não aumenta o bônus.'
    },
    'equidade': {
        titulo: 'Redução de Desigualdades',
        texto: 'Este bônus avalia se houve evolução, no SAEPE 2026, dos estudantes Pretos, Pardos e Indígenas (PPI) e daqueles de nível socioeconômico mais baixo, em comparação com 2025. Caso positivo, a escola soma 100% ao cálculo do BDE. Vale para qualquer escola, tenha ela atingido ou não os 80% de participação — é a única parcela que sobra para quem ficou sem IDEPE.'
    },
    'elementares': {
        titulo: 'Elementares (1/3 inferior)',
        texto: 'Este bônus é destinado às escolas que estão entre o primeiro terço (33,3%) com menor percentual de estudantes nos níveis elementares (PD 1 e 2), na comparação com escolas do mesmo tipo dentro da mesma Macrorregião. Caso positivo, a escola soma outros 100%. Os dois quesitos de equidade somam entre si: atingir os dois vale 200%.'
    },
    'participacao': {
        titulo: 'Participação ≥ 80%',
        texto: 'A participação é verificada por etapa e funciona como condição para o IDEPE: etapa que não atinge 80% não tem resultado divulgado e entra no cálculo com 0% de atingimento. Além disso, basta uma etapa atingir os 80% para a escola somar uma cota adicional de 50% no BDE.'
    },
    'cota-bde': {
        titulo: 'Cota BDE Calculada',
        texto: 'A Cota BDE soma a Cota Resultado (até 100%) com os bônus de Equidade e de Elementares (100% cada), chegando a até 300%. A Participação acrescenta mais 50% ao total, que é então limitado ao teto de 300% do BDE.'
    }
};

function abrirPopupMetrica(chave) {
    const conteudo = METRICAS_CONTEUDO[chave];
    if (!conteudo) return;

    const overlay = document.createElement('div');
    overlay.className = 'popup-overlay ativo';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    overlay.innerHTML = `
        <div class="popup-conteudo popup-metrica" onclick="event.stopPropagation()">
            <button class="popup-fechar" onclick="this.closest('.popup-overlay').remove()" aria-label="Fechar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
            <div class="popup-header">
                <h3>${conteudo.titulo}</h3>
            </div>
            <div class="popup-body">
                <p class="popup-metrica-texto">${conteudo.texto}</p>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    document.addEventListener('keydown', function handler(e) {
        if (e.key === 'Escape') {
            overlay.remove();
            document.removeEventListener('keydown', handler);
        }
    });
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
