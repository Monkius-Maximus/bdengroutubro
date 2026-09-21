"""
Router FastAPI — Simulador Bônus de Desempenho Educacional (BDE).

Endpoint: POST /api/v1/simular-bde
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.bde.schemas import RequisicaoBDE, RespostaBDE
from src.bde.service import calcular_bde

router = APIRouter(prefix="/api/v1", tags=["BDE"])


@router.post("/simular-bde", response_model=RespostaBDE)
async def simular_bde(requisicao: RequisicaoBDE) -> RespostaBDE:
    """
    Simula o Bônus de Desempenho Educacional.

    O frontend envia todas as respostas acumuladas do wizard.
    O backend retorna o percentual final detalhado, quebrado por componente.
    """
    try:
        return calcular_bde(requisicao)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Erro no cálculo do BDE: {exc}",
        )
