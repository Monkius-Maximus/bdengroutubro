"""
FastAPI — Simulador do Bonus de Desempenho Educacional (BDE).
"""

from __future__ import annotations

import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.bde import bde_router

app = FastAPI(
    title="Simulador BDE — Pernambuco",
    description=(
        "Backend do Simulador do Bonus de Desempenho Educacional (BDE) "
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

# Estatica e templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
async def raiz(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
