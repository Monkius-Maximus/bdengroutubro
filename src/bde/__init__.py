"""Módulo BDE — Simulador do Bônus de Desempenho Educacional."""

from src.bde.router import router as bde_router
from src.bde.schemas import RequisicaoBDE, RespostaBDE, EtapaIDEPE, DetalheEtapa
from src.bde.service import calcular_bde

__all__ = [
    "bde_router",
    "RequisicaoBDE",
    "RespostaBDE",
    "EtapaIDEPE",
    "DetalheEtapa",
    "calcular_bde",
]
