# Simulador BDE — NGR-SEE

![Simulador BDE](app/static/img/UI-BDE-INTERFACE3.png)

Sistema interativo para simulacao do Bonus de Desempenho Educacional (BDE) de Pernambuco.

## O que e?

O Simulador BDE foi desenvolvido pelo Nucleo de Gestao para Resultados na Educacao (NGR-SEE) / Seplag para facilitar a vida dos gestores escolares. Antes, o calculo do BDE era feito manualmente em planilhas Excel. Agora, basta preencher os dados em um passo a passo guiado e o sistema faz todo o calculo automaticamente.

## Funcionalidades

- **Wizard passo a passo**: navegacao intuitiva em etapas
- **Calculo automatico**: formula exata da planilha original
- **Resultado detalhado**: visualizacao de cada componente do BDE
- **Explicacoes interativas**: clique nos cards do resultado para entender cada metrica
- **Contato integrado**: WhatsApp para suporte

## Como executar

```bash
cd "D:\exemplo\mudar-caminho"
python -m uvicorn main:app --reload
```

Acesse: http://127.0.0.1:8000

## Publicacao (Google Sites / GitHub Pages)

O `index.html` na raiz e a mesma interface sem servidor: os tres arquivos de
`app/` reunidos, com o calculo em JavaScript no lugar da chamada a API. E o que
o GitHub Pages serve em https://monkius-maximus.github.io/bdengroutubro/ e o
que o Google Sites embute.

Mexeu em `app/`? Regenere o `index.html` e rode `python3 tests/test_paridade.py`.
Passo a passo em [`docs/GOOGLE_SITES.md`](docs/GOOGLE_SITES.md).

## Stack

- **Backend**: FastAPI + Python
- **Frontend**: HTML + CSS + JavaScript vanilla
- **Templates**: Jinja2
