/* ============================================================================
   Wizard BDE — Navegação, API e Gamificação
   ============================================================================ */

const estado = {
    stepAtual: 0,
    totalSteps: 8,
    resultadoApi: null,
    respostas: {
        etapas_selecionadas: [],
        etapa_ai: null,
        etapa_af: null,
        etapa_em: null,
        reduziu_desigualdade: null,
        terco_menor_elementares: null,
        participacao_maior_80: null,
    },
};

document.addEventListener('DOMContentLoaded', () => {
    renderizarDots();
    atualizarUI();
});

function renderizarDots() {
    const c = document.getElementById('steps-dots');
    c.innerHTML = '';
    for (let i = 0; i < estado.totalSteps; i++) {
        const d = document.createElement('div');
        d.className = 'dot';
        d.id = `dot-${i}`;
        c.appendChild(d);
    }
}

function corFase(step) {
    if (step >= 6) return 'verde';
    if (step >= 3) return 'dourado';
    return 'azul';
}

function corBarra(fase) {
    if (fase === 'verde') return 'linear-gradient(90deg, #ca8a04, #16a34a)';
    if (fase === 'dourado') return 'linear-gradient(90deg, #1a3a5c, #ca8a04)';
    return 'linear-gradient(90deg, #1a3a5c, #2a6496)';
}

function atualizarUI() {
    const { stepAtual, totalSteps } = estado;
    const percentual = Math.round((stepAtual / (totalSteps - 1)) * 100);

    const barra = document.getElementById('barra-progresso');
    barra.style.width = `${percentual}%`;
    barra.style.background = corBarra(corFase(stepAtual));

    document.getElementById('lbl-etapa').textContent = `Passo ${stepAtual + 1} de ${totalSteps}`;
    document.getElementById('lbl-progresso').textContent = `${percentual}%`;

    for (let i = 0; i < totalSteps; i++) {
        const dot = document.getElementById(`dot-${i}`);
        if (!dot) continue;
        dot.className = 'dot';
        const fase = corFase(i);
        if (fase === 'dourado') dot.classList.add('fase-dourado');
        if (fase === 'verde') dot.classList.add('fase-verde');
        if (i < stepAtual) dot.classList.add('completo');
        if (i === stepAtual) dot.classList.add('ativo');
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

    const ehResultado = stepAtual === 7;
    const ehResumo = stepAtual === 6;

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
        case 0: return estado.respostas.etapas_selecionadas.length > 0;
        case 1: return estado.respostas.etapa_ai !== null;
        case 2: return estado.respostas.etapa_af !== null;
        case 3: return estado.respostas.etapa_em !== null;
        case 4:
            return estado.respostas.reduziu_desigualdade !== null
                && estado.respostas.terco_menor_elementares !== null;
        case 5: return estado.respostas.participacao_maior_80 !== null;
        default: return true;
    }
}

function proximo() {
    if (!stepValido(estado.stepAtual)) return;

    if (estado.stepAtual === 5) {
        enviarSimulacao();
        return;
    }

    estado.stepAtual++;
    while (devePularStep(estado.stepAtual) && estado.stepAtual < 6) {
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

function toggleSimNao(card, valor) {
    card.parentElement.querySelectorAll('.opcao-card').forEach(c => c.classList.remove('selecionado'));
    card.classList.add('selecionado');
    estado.respostas.participacao_maior_80 = valor;
    atualizarUI();
}

function validarInputsEtapa(prefixo) {
    const mat = parseFloat(document.getElementById(`inp-${prefixo}-mat`).value);
    const meta = parseFloat(document.getElementById(`inp-${prefixo}-meta`).value);
    const res = parseFloat(document.getElementById(`inp-${prefixo}-res`).value);
    if (!mat || mat <= 0 || isNaN(meta) || isNaN(res) || meta <= 0 || res <= 0) {
        mostrarErro('Preencha todos os campos com valores válidos (maiores que zero).');
        return null;
    }
    return { matriculas: Math.round(mat), meta, resultado: res };
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
    const dados = validarInputsEtapa(prefixo);
    if (dados) {
        estado.respostas[`etapa_${prefixo}`] = dados;
    } else {
        estado.respostas[`etapa_${prefixo}`] = null;
    }
    atualizarUI();
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
    payload.participacao_maior_80 = estado.respostas.participacao_maior_80;

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
        if (dados) {
            const variacao = (dados.resultado - dados.meta).toFixed(2);
            const sinal = parseFloat(variacao) >= 0 ? '+' : '';
            html += `
                <div class="resumo-item ${parseFloat(variacao) >= 0 ? 'sim' : 'nao'}">
                    <div class="resumo-icone">${parseFloat(variacao) >= 0 ? '+' : '-'}</div>
                    <div class="resumo-texto">
                        <strong>${etapasNomes[chave]}</strong> — Meta: ${dados.meta} | Resultado: ${dados.resultado} | Variação: ${sinal}${variacao}
                    </div>
                </div>`;
        }
    });

    const eq = r.reduziu_desigualdade;
    const el = r.terco_menor_elementares;
    const part = r.participacao_maior_80;

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
            <div class="resumo-texto"><strong>Participação:</strong> ${part ? 'Atingiu >= 80% no SAEPE' : 'Não atingiu 80% de participação'}</div>
        </div>`;

    const motivos = [];
    if (r.etapas_selecionadas.length > 0) {
        const diffs = r.etapas_selecionadas.map(k => {
            const d = r[`etapa_${k}`];
            return d ? d.resultado - d.meta : 0;
        });
        const media = diffs.reduce((a, b) => a + b, 0) / diffs.length;
        if (media >= 0.4) motivos.push('superou a meta em 0.4 pontos ou mais');
        else if (media >= 0.1) motivos.push('superou a meta');
        else if (media >= 0) motivos.push('atingiu ou está próximo da meta');
        else motivos.push('ficou abaixo da meta');
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
    estado.stepAtual = 6;
    document.getElementById('resumo-area').innerHTML = montarResumo();
    atualizarUI();
}

function corKPI(valor) {
    if (valor >= 2.0) return 'kpi-verde';
    if (valor >= 1.0) return 'kpi-dourado';
    return 'kpi-vermelho';
}

function mostrarResultado(r) {
    estado.stepAtual = 7;
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
    estado.stepAtual = 0;
    estado.resultadoApi = null;
    estado.respostas = {
        etapas_selecionadas: [],
        etapa_ai: null,
        etapa_af: null,
        etapa_em: null,
        reduziu_desigualdade: null,
        terco_menor_elementares: null,
        participacao_maior_80: null,
    };
    document.querySelectorAll('.opcao-card').forEach(c => c.classList.remove('selecionado'));
    document.querySelectorAll('.btn-simnao').forEach(b => b.classList.remove('selecionado'));
    document.querySelectorAll('.input-campo input').forEach(i => i.value = '');
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
        texto: 'A Média IDEPE é calculada a partir da variação entre o resultado obtido e a meta pactuada em cada etapa avaliada, ponderada pela quantidade de matrículas. Essa média é convertida em percentual por meio de uma tabela de conversão, onde valores de variação positivos resultam em percentuais maiores, chegando até 200%.'
    },
    'cota-resultado': {
        titulo: 'Cota Resultado',
        texto: 'A Cota Resultado é a parcela do percentual IDEPE que equivale a até 100%. Ela representa o ganho base da escola com base no desempenho do IDEPE. Se o percentual IDEPE for superior a 100%, o excedente vai para a "Cota Além do Resultado".'
    },
    'equidade': {
        titulo: 'Redução de Desigualdades',
        texto: 'Este bônus avalia se houve evolução, no SAEPE 2025, dos estudantes Pretos, Pardos e Indígenas (PPI) e daqueles de nível socioeconômico mais baixo, em comparação com 2024. Caso positivo, a escola recebe um bônus de até 100% no cálculo do BDE.'
    },
    'elementares': {
        titulo: 'Elementares (1/3 inferior)',
        texto: 'Este bônus é destinado às escolas que estão entre o primeiro terço (33,3%) com menor percentual de estudantes nos níveis elementares (PD 1 e 2), na comparação com escolas do mesmo tipo dentro da mesma Macrorregião. Caso positivo, a escola recebe um bônus de até 100%.'
    },
    'participacao': {
        titulo: 'Participação ≥ 80%',
        texto: 'As escolas que atingirem uma participação igual ou superior a 80% em todos os componentes e etapas avaliados no SAEPE terão direito a uma cota parcial adicional de até 50% no cálculo do BDE.'
    },
    'cota-bde': {
        titulo: 'Cota BDE Calculada',
        texto: 'A Cota BDE é o resultado da fórmula composta que combina a Cota Resultado, o bônus de Equidade e o bônus de Elementares. Essa cota pode chegar até 250%. A Participação é somada posteriormente ao total, podendo o BDE final ultrapassar 300%.'
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
