"""
Router FastAPI — Simulador do Bônus de Desempenho Educacional (BDE).

Endpoint: POST /api/v1/simular-bde
"""

from __future__ import annotations

from fastapi import APIRouter

from src.bde.schemas import RequisicaoBDE, RespostaBDE
from src.bde.service import calcular_bde

router = APIRouter(prefix="/api/v1", tags=["BDE"])


@router.post("/simular-bde", response_model=RespostaBDE)
async def simular_bde(requisicao: RequisicaoBDE) -> RespostaBDE:
    """
    Simula a cota do BDE a partir das respostas acumuladas do wizard.

    Sem try/except: o `RequisicaoBDE` já garante as pré-condições e devolve 422
    com o campo exato. O que passar dele e quebrar é bug do serviço e deve
    aparecer como 500, não disfarçado de erro de validação.
    """
    return calcular_bde(requisicao)
