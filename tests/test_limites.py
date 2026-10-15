"""
Limites dos campos de uma etapa, conferidos no backend (src/bde/schemas.py).

    python3 tests/test_limites.py

Matriculas de 10 a 300.000; meta de 2,00 a 6,00; resultado de 0,00 a 10,00;
meta e resultado com no maximo duas casas decimais. Os mesmos limites estao em
LIMITES, no app/static/js/wizard.js: mudou num, mude no outro.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from pydantic import ValidationError  # noqa: E402

from src.bde.schemas import EtapaIDEPE  # noqa: E402


def etapa(matriculas=100, participou=True, meta=4.0, resultado=4.0) -> dict:
    dados = {"matriculas": matriculas, "participacao_maior_80": participou, "meta": meta}
    if participou:
        dados["resultado"] = resultado
    return dados


ACEITOS = [
    ("limites inferiores", etapa(matriculas=10, meta=2.0, resultado=0.0)),
    ("limites superiores", etapa(matriculas=300_000, meta=6.0, resultado=10.0)),
    ("duas casas decimais", etapa(meta=4.55, resultado=4.07)),
    ("sem participacao, so meta", etapa(participou=False)),
]

RECUSADOS = [
    ("matriculas 9", etapa(matriculas=9)),
    ("matriculas 300.001", etapa(matriculas=300_001)),
    ("meta 1,99", etapa(meta=1.99)),
    ("meta 6,01", etapa(meta=6.01)),
    ("meta com tres casas", etapa(meta=4.555)),
    ("resultado -0,01", etapa(resultado=-0.01)),
    ("resultado 10,01", etapa(resultado=10.01)),
    ("resultado com tres casas", etapa(resultado=4.123)),
]


def main() -> int:
    falhas = []
    for nome, dados in ACEITOS:
        try:
            EtapaIDEPE(**dados)
        except ValidationError as e:
            falhas.append(f"devia aceitar {nome}: {e.errors()[0]['msg']}")
    for nome, dados in RECUSADOS:
        try:
            EtapaIDEPE(**dados)
            falhas.append(f"devia recusar {nome}")
        except ValidationError:
            pass

    for f in falhas:
        print("FALHA:", f)
    if falhas:
        print(f"\nFALHOU — {len(falhas)} verificacoes.")
        return 1
    print(f"OK — {len(ACEITOS)} aceitos e {len(RECUSADOS)} recusados como esperado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
