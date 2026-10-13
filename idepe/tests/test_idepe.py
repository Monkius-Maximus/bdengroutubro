"""
Motor do Simulador IDEPE (motor.js) contra a aba "Simulador IDEPE" da
planilha do Nucleo da Seplag (1_Simulador_Idepe_Ideb_e_Atingimento_de_metas).

Os valores esperados sao os que a propria planilha calculou: os casos foram
digitados nas celulas amarelas e a planilha recalculada no LibreOffice. P e N
batem ate a 9a casa; o IDEPE, com duas casas, como a celula C14 exibe.

Taxa abaixo de 65%: a planilha so aceita de 65 a 100 e pede que a escola
digite 65 no lugar. O simulador aceita a taxa real e aplica o 65 sozinho;
nos casos abaixo, a planilha recebeu 65 onde o motor recebe a taxa real.

Unica diferenca de proposito: com N x P = 0 a planilha deixa o IDEPE em branco
(o AND da C14 trata zero como falso). O motor devolve 0,00.

    python3 tests/test_idepe.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

MOTOR = Path(__file__).resolve().parent.parent / "motor.js"

# (descricao, etapa, aprovacoes preenchidas, LP, MT, P, N, IDEPE da planilha)
CASOS = [
    ("AI cinco anos", "ai", [95, 92.5, 88, 90, 97.3], 210.5, 225.3,
     0.924396112552462, 6.09094378903539, 5.63044476035988),
    ("AF sem o 7o ano", "af", [85, 80.2, 91], 255, 250,
     0.85172721531153, 5.08333333333333, 4.32961334450028),
    ("EM tres series", "em", [78, 82.5, 90], 280, 275.6,
     0.832112068965517, 4.75191751328803, 3.95412791353558),
    ("AI no teto", "ai", [100, 100, 100, 100, 100], 324, 322,
     1.0, 10.0, 10.0),
    ("AF no piso: planilha em branco, motor 0", "af", [70], 100, 100,
     0.7, 0.0, 0.0),
    ("EM 50% conta 65%", "em", [50], 451, 111,
     0.65, 5.0, 3.25),
    ("AI so o 5o ano", "ai", [99.9], 180.25, 200.75,
     0.999, 5.07243233865371, 5.06735990631506),
    ("AF 40% conta 65%", "af", [40, 72.33, 88.88, 93.1], 240.4, 233.9,
     0.781213365803825, 4.57166666666667, 3.57144710399982),
    ("EM 60% e 64,99% contam 65%", "em", [60, 64.99, 92], 270, 268,
     0.720481927710843, 4.49547534145193, 3.23890873998585),
]


def arredondar_excel(valor: float, casas: int) -> float:
    """Como a celula 0.00 exibe: empate para longe do zero."""
    return float(Decimal(repr(valor)).quantize(Decimal(10) ** -casas, ROUND_HALF_UP))


def respostas_js() -> list[dict]:
    entrada = [
        {"chave": etapa, "dados": {"aprovacoes": ap, "lp": lp, "mt": mt}}
        for _, etapa, ap, lp, mt, *_ in CASOS
    ]
    runner = f"""
{MOTOR.read_text("utf-8")}
const casos = {json.dumps(entrada)};
process.stdout.write(JSON.stringify(casos.map((c) => calcularIdepe(c.chave, c.dados))));
"""
    processo = subprocess.run(["node", "-e", runner], capture_output=True, text=True)
    if processo.returncode != 0:
        raise RuntimeError(f"Motor JS falhou:\n{processo.stderr}")
    return json.loads(processo.stdout)


def main() -> int:
    falhas = []
    for caso, r in zip(CASOS, respostas_js()):
        nome, *_, p, n, idepe = caso
        if abs(r["rendimento"] - p) > 1e-9:
            falhas.append(f"{nome}: P {r['rendimento']} != planilha {p}")
        if abs(r["nota_saepe"] - n) > 1e-9:
            falhas.append(f"{nome}: N {r['nota_saepe']} != planilha {n}")
        if r["idepe"] != arredondar_excel(idepe, 2):
            falhas.append(f"{nome}: IDEPE {r['idepe']} != planilha {arredondar_excel(idepe, 2)}")

    for f in falhas:
        print("FALHA", f)
    print(f"{len(CASOS) - len(falhas)}/{len(CASOS)} casos ok")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
