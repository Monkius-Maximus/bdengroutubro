"""
FastAPI — Simulador do Bônus de Desempenho Educacional (BDE).
"""

from __future__ import annotations

import sys
import os

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.bde import bde_router

app = FastAPI(
    title="Simulador BDE — Pernambuco",
    description=(
        "Backend do Simulador do Bônus de Desempenho Educacional (BDE) "
        "para gestores escolares do estado de Pernambuco."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bde_router)


@app.get("/")
async def raiz():
    return {
        "servico": "Simulador BDE",
        "versao": "1.0.0",
        "endpoint_simulacao": "/api/v1/simular-bde",
        "documentacao": "/docs",
    }
