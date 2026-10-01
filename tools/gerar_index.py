"""
Gera o index.html da raiz a partir do app/.

O Google Sites e hospedagem estatica: nao roda o FastAPI. A pagina publicada e
o template, o estilo e o wizard reunidos num arquivo so, com o POST para
/api/v1/simular-bde trocado pelo motor local (app/static/js/motor.js).

A fonte continua sendo o app/. Mexeu la, rode isto e o teste de paridade:

    python3 tools/gerar_index.py
    python3 tests/test_paridade.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

TEMPLATE = RAIZ / "app/templates/index.html"
ESTILO = RAIZ / "app/static/css/estilo.css"
WIZARD = RAIZ / "app/static/js/wizard.js"
MOTOR = RAIZ / "app/static/js/motor.js"
SAIDA = RAIZ / "index.html"

CHAMADA_API = """    try {
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
}"""

CHAMADA_LOCAL = """    try {
        estado.resultadoApi = simularBde(payload);
        mostrarResumo();
    } catch (e) {
        mostrarErro(e.message);
    }
}"""

ABERTURA_ASSINCRONA = """async function enviarSimulacao() {
    const btn = document.getElementById('btn-proximo');
    btn.disabled = true;
    btn.textContent = 'Calculando...';

    const payload = {};"""

ABERTURA_LOCAL = """/**
 * Era um POST para /api/v1/simular-bde. O Google Sites nao roda o FastAPI,
 * entao o calculo vem do motor local, que devolve exatamente o mesmo formato
 * que a API devolvia — o wizard nao sabe de onde veio.
 */
function enviarSimulacao() {
    const payload = {};"""


def trocar(texto: str, antigo: str, novo: str, onde: str) -> str:
    if antigo not in texto:
        raise SystemExit(
            f"gerar_index: nao encontrei em {onde} o trecho que precisa ser "
            f"trocado.\n\n{antigo[:200]}\n\n"
            "O app/ mudou de forma que este gerador nao previu. Ajuste o "
            "gerador antes de publicar, para a pagina nao sair diferente da "
            "versao servida pelo FastAPI."
        )
    return texto.replace(antigo, novo, 1)


def main() -> int:
    html = TEMPLATE.read_text(encoding="utf-8")
    css = ESTILO.read_text(encoding="utf-8")
    js = WIZARD.read_text(encoding="utf-8")
    motor = MOTOR.read_text(encoding="utf-8")

    # Sem servidor nao existe /static: os caminhos passam a ser relativos a raiz.
    html = trocar(html, '    <link rel="stylesheet" href="/static/css/estilo.css">\n', "", "template")
    html = trocar(html, '    <script src="/static/js/wizard.js"></script>\n', "", "template")
    html = html.replace('"/static/img/', '"app/static/img/')

    js = trocar(js, ABERTURA_ASSINCRONA, ABERTURA_LOCAL, "wizard.js")
    js = trocar(js, CHAMADA_API, CHAMADA_LOCAL, "wizard.js")

    cabeca = html.split("<head>", 1)[1].split("</head>", 1)[0]
    corpo = html.split("<body>", 1)[1].rsplit("</body>", 1)[0]

    SAIDA.write_text(
        f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>{cabeca}<style>
{css}</style>
</head>
<body>
{corpo}
<script>
{motor}
{js}</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(f"index.html gerado: {SAIDA.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
