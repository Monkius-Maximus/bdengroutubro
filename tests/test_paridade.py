"""
Paridade entre o motor Python (src/bde/service.py) e o motor JavaScript
embarcado em web/index.html.

Os dois motores existem porque o Google Sites não hospeda backend: a página é
estática e calcula no navegador. Duas implementações da mesma fórmula divergem
sozinhas com o tempo — este teste é o que impede isso. Ele varre os limites de
faixa de H45, onde 0,0001 vale 25 pontos percentuais.

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

PAGINA = RAIZ / "web" / "index.html"

# O motor JS termina onde começa o wizard; daí para baixo o código toca o DOM.
MARCA_FIM_DO_MOTOR = "WIZARD"


def extrair_motor_js() -> str:
    script = re.search(r"<script>(.*?)</script>", PAGINA.read_text("utf-8"), re.S)
    if script is None:
        raise RuntimeError(f"Nenhum <script> encontrado em {PAGINA}.")

    corpo = script.group(1)
    corte = corpo.find(MARCA_FIM_DO_MOTOR)
    if corte == -1:
        raise RuntimeError(
            f"Marcador {MARCA_FIM_DO_MOTOR!r} sumiu de {PAGINA}: o teste não "
            "consegue mais separar o motor do wizard."
        )
    return corpo[: corpo.rfind("/* =", 0, corte)]


def normalizar(texto: str) -> str:
    """Tira da comparação o que é só apresentação: vírgula decimal e sinal −."""
    return texto.replace(",", ".").replace("−", "-")


def resposta_python(caso: dict) -> dict:
    requisicao = RequisicaoBDE(
        etapa_anos_iniciais=(
            EtapaIDEPE(**caso["anos_iniciais"]) if "anos_iniciais" in caso else None
        ),
        etapa_anos_finais=(
            EtapaIDEPE(**caso["anos_finais"]) if "anos_finais" in caso else None
        ),
        etapa_ensino_medio=(
            EtapaIDEPE(**caso["ensino_medio"]) if "ensino_medio" in caso else None
        ),
        reduziu_desigualdade=caso["reduziu_desigualdade"],
        terco_menor_elementares=caso["terco_menor_elementares"],
        participacao_minima_atingida=caso["participacao_minima_atingida"],
    )
    r = calcular_bde(requisicao)
    return {
        "percentual_bde": r.percentual_bde,
        "media": r.media_ponderada_diferenca,
        "idepe": r.percentual_idepe,
        "cota_resultado": r.cota_resultado,
        "cota_alem": r.cota_alem_resultado,
        "cota_equidade": r.cota_equidade,
        "cota_elementares": r.cota_elementares,
        "cota_participacao": r.cota_participacao,
        "alertas": [normalizar(a) for a in r.alertas],
    }


def respostas_js(casos: list[dict]) -> list[dict]:
    runner = f"""
{extrair_motor_js()}

const NOMES = {{
  anos_iniciais: "Anos Iniciais",
  anos_finais: "Anos Finais",
  ensino_medio: "Ensino Médio",
}};

const casos = JSON.parse(require("fs").readFileSync(process.env.CASOS_JSON, "utf8"));
const saida = casos.map((caso) => {{
  const etapas = Object.keys(NOMES)
    .filter((id) => caso[id])
    .map((id) => Object.assign({{ etapa: id, nome: NOMES[id] }}, caso[id]));

  const r = calcularBde({{
    etapas: etapas,
    reduziuDesigualdade: caso.reduziu_desigualdade,
    tercoMenorElementares: caso.terco_menor_elementares,
    participacaoMinimaAtingida: caso.participacao_minima_atingida,
  }});

  return {{
    percentual_bde: r.percentualBde,
    media: r.mediaPonderadaDiferenca,
    idepe: r.percentualIdepe,
    cota_resultado: r.cotaResultado,
    cota_alem: r.cotaAlemResultado,
    cota_equidade: r.cotaEquidade,
    cota_elementares: r.cotaElementares,
    cota_participacao: r.cotaParticipacao,
    alertas: r.alertas.map((a) => a.replace(/,/g, ".").replace(/−/g, "-")),
  }};
}});

process.stdout.write(JSON.stringify(saida));
"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as arquivo:
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


def gerar_casos() -> list[dict]:
    """
    Metas e resultados escolhidos para pousar em cima dos limites de H45 e a
    um passo deles, onde o arredondamento decide a faixa.
    """
    meta = 4.5
    resultados = [
        4.19, 4.2, 4.2001, 4.25, 4.29, 4.2999, 4.3, 4.3001,  # o buraco de −0,3 a −0,2
        4.35, 4.4, 4.4999, 4.5, 4.5999, 4.6, 4.69999, 4.7,
        4.79999, 4.8, 4.89999, 4.9, 5.2, 6.0, 9.2,
        4.59995, 4.49995,  # empates de ROUND(...; 4)
    ]
    booleanos = list(product([True, False], repeat=3))

    casos = []
    for resultado, (equidade, elementares, participacao) in product(resultados, booleanos):
        comuns = {
            "reduziu_desigualdade": equidade,
            "terco_menor_elementares": elementares,
            "participacao_minima_atingida": participacao,
        }
        # Etapa única.
        casos.append(
            {"anos_iniciais": {"matriculas": 320, "meta": meta, "resultado": resultado}, **comuns}
        )
        # Três etapas com pesos desiguais — exercita a ponderação crua de H47.
        casos.append(
            {
                "anos_iniciais": {"matriculas": 317, "meta": meta, "resultado": resultado},
                "anos_finais": {"matriculas": 83, "meta": 5.1, "resultado": 5.0},
                "ensino_medio": {"matriculas": 1234, "meta": 3.8, "resultado": 4.05},
                **comuns,
            }
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
        print("DIVERGÊNCIA")
        print("  caso:   ", json.dumps(caso, ensure_ascii=False))
        print("  python: ", json.dumps(esperado, ensure_ascii=False))
        print("  js:     ", json.dumps(obtido, ensure_ascii=False))
        print()

    if divergencias:
        print(f"FALHOU — {len(divergencias)} de {len(casos)} casos divergiram.")
        return 1

    print(f"OK — {len(casos)} casos, motores idênticos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
