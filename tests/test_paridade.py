"""
Paridade entre o motor Python (src/bde/service.py) e o motor JavaScript
embarcado em index.html.

Os dois existem porque o Google Sites nao hospeda backend: a pagina publicada
e estatica e calcula no navegador, enquanto o FastAPI continua servindo a
mesma regra como API. Duas implementacoes divergem sozinhas com o tempo — este
teste e o que impede isso.

Foi exatamente esse tipo de desencontro que ja quebrou o simulador uma vez: os
schemas foram renomeados de um lado so, o payload passou a ser recusado com 422
e os cartoes do resultado passaram a exibir NaN%.

    python3 tests/test_paridade.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from itertools import product
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.bde.schemas import EtapaIDEPE, RequisicaoBDE  # noqa: E402
from src.bde.service import calcular_bde  # noqa: E402

PAGINA = RAIZ / "index.html"

# O motor JS termina onde comeca o wizard; dai para baixo o codigo toca o DOM.
MARCA_FIM_DO_MOTOR = "Wizard BDE"


def extrair_motor_js() -> str:
    script = re.search(r"<script>(.*?)</script>", PAGINA.read_text("utf-8"), re.S)
    if script is None:
        raise RuntimeError(f"Nenhum <script> encontrado em {PAGINA}.")

    corpo = script.group(1)
    corte = corpo.find(MARCA_FIM_DO_MOTOR)
    if corte == -1:
        raise RuntimeError(
            f"Marcador {MARCA_FIM_DO_MOTOR!r} sumiu de {PAGINA}: o teste nao "
            "consegue mais separar o motor do wizard."
        )
    return corpo[: corpo.rfind("/* =", 0, corte)]


def resposta_python(caso: dict) -> dict:
    r = calcular_bde(
        RequisicaoBDE(
            etapa_ai=EtapaIDEPE(**caso["etapa_ai"]) if "etapa_ai" in caso else None,
            etapa_af=EtapaIDEPE(**caso["etapa_af"]) if "etapa_af" in caso else None,
            etapa_em=EtapaIDEPE(**caso["etapa_em"]) if "etapa_em" in caso else None,
            reduziu_desigualdade=caso["reduziu_desigualdade"],
            terco_menor_elementares=caso["terco_menor_elementares"],
        )
    )
    return {
        "percentual_bde": r.percentual_bde,
        "percentual_formatado": r.percentual_formatado,
        "apto_a_receber": r.apto_a_receber,
        "media": r.media_ponderada_variacao,
        "percentual_idepe": r.percentual_idepe,
        "cota_resultado": r.cota_resultado,
        "cota_alem_resultado": r.cota_alem_resultado,
        "cota_bde_calculada": r.cota_bde_calculada,
        "bonus_equidade": r.bonus_equidade,
        "bonus_elementares": r.bonus_elementares,
        "bonus_participacao": r.bonus_participacao,
        "etapas": [
            {
                "nome": e.nome,
                "participou": e.participou,
                "variacao": e.variacao,
                "percentual_atingimento": e.percentual_atingimento,
            }
            for e in r.etapas
        ],
    }


def respostas_js(casos: list[dict]) -> list[dict]:
    runner = f"""
{extrair_motor_js()}

const casos = JSON.parse(require("fs").readFileSync(process.env.CASOS_JSON, "utf8"));
process.stdout.write(JSON.stringify(casos.map((caso) => {{
  const r = simularBde(caso);
  return {{
    percentual_bde: r.percentual_bde,
    percentual_formatado: r.percentual_formatado,
    apto_a_receber: r.apto_a_receber,
    media: r.media_ponderada_variacao,
    percentual_idepe: r.percentual_idepe,
    cota_resultado: r.cota_resultado,
    cota_alem_resultado: r.cota_alem_resultado,
    cota_bde_calculada: r.cota_bde_calculada,
    bonus_equidade: r.bonus_equidade,
    bonus_elementares: r.bonus_elementares,
    bonus_participacao: r.bonus_participacao,
    etapas: r.etapas.map((e) => ({{
      nome: e.nome,
      participou: e.participou,
      variacao: e.variacao,
      percentual_atingimento: e.percentual_atingimento,
    }})),
  }};
}})));
"""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", encoding="utf-8", delete=False
    ) as arquivo:
        json.dump(casos, arquivo)
        entrada = arquivo.name

    processo = subprocess.run(
        ["node", "-e", runner],
        capture_output=True,
        text=True,
        env={**os.environ, "CASOS_JSON": entrada},
    )
    if processo.returncode != 0:
        raise RuntimeError(f"Motor JS falhou:\n{processo.stderr}")
    return json.loads(processo.stdout)


def _etapa(matriculas: int, participou: bool, meta=None, resultado=None) -> dict:
    dados = {"matriculas": matriculas, "participacao_maior_80": participou}
    if participou:
        dados["meta"] = meta
        dados["resultado"] = resultado
    return dados


def gerar_casos() -> list[dict]:
    """
    Resultados escolhidos para pousar em cima dos limites da tabela de conversao
    e a um passo deles, onde 0,01 na media ponderada vale 25 pontos percentuais.

    As familias cobrem os quatro caminhos da regra do ciclo 2026: todas as
    etapas aprovadas, todas reprovadas, e as duas misturas — aprovada grande com
    reprovada pequena e o inverso, que e onde a diluicao mais pesa.
    """
    resultados = [
        1.5, 4.19, 4.2, 4.21, 4.25, 4.29, 4.3, 4.31, 4.35, 4.4, 4.49,
        4.5, 4.59, 4.6, 4.69, 4.7, 4.79, 4.8, 4.89, 4.9, 5.2, 6.0, 9.2,
    ]
    casos = []
    for resultado, (equidade, elementares) in product(
        resultados, product([True, False], repeat=2)
    ):
        comuns = {
            "reduziu_desigualdade": equidade,
            "terco_menor_elementares": elementares,
        }
        # Etapa unica aprovada, em duas posicoes do payload.
        casos.append({"etapa_ai": _etapa(320, True, 4.5, resultado), **comuns})
        casos.append({"etapa_af": _etapa(91, True, 5.1, resultado), **comuns})
        # Etapa unica reprovada — o caminho que so concorre a equidade.
        casos.append({"etapa_ai": _etapa(320, False), **comuns})
        # Misturas: o peso da reprovada muda tudo.
        casos.append(
            {
                "etapa_ai": _etapa(1000, True, 4.5, resultado),
                "etapa_em": _etapa(50, False),
                **comuns,
            }
        )
        casos.append(
            {
                "etapa_ai": _etapa(50, True, 4.5, resultado),
                "etapa_em": _etapa(1000, False),
                **comuns,
            }
        )
        # Tres etapas aprovadas — regressao do ciclo anterior.
        casos.append(
            {
                "etapa_ai": _etapa(317, True, 4.5, resultado),
                "etapa_af": _etapa(83, True, 5.1, 5.0),
                "etapa_em": _etapa(1234, True, 3.8, 4.05),
                **comuns,
            }
        )
        # Tres etapas com a do meio reprovada.
        casos.append(
            {
                "etapa_ai": _etapa(317, True, 4.5, resultado),
                "etapa_af": _etapa(83, False),
                "etapa_em": _etapa(1234, True, 3.8, 4.05),
                **comuns,
            }
        )
        # Todas reprovadas.
        casos.append(
            {"etapa_ai": _etapa(317, False), "etapa_af": _etapa(83, False), **comuns}
        )
    return casos


def main() -> int:
    casos = gerar_casos()
    esperados = [resposta_python(caso) for caso in casos]
    obtidos = respostas_js(casos)

    divergencias = [
        (caso, esperado, obtido)
        for caso, esperado, obtido in zip(casos, esperados, obtidos)
        if esperado != obtido
    ]

    for caso, esperado, obtido in divergencias[:5]:
        print("DIVERGENCIA")
        print("  caso:   ", json.dumps(caso, ensure_ascii=False))
        print("  python: ", json.dumps(esperado, ensure_ascii=False))
        print("  js:     ", json.dumps(obtido, ensure_ascii=False))
        print()

    if divergencias:
        print(f"FALHOU — {len(divergencias)} de {len(casos)} casos divergiram.")
        return 1

    print(f"OK — {len(casos)} casos, motores identicos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
