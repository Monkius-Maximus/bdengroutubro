# Simulador IDEB — NGR-EDU · Seplag

Simula o IDEB da escola por etapa, a partir das taxas de aprovação do Censo
Escolar e das proficiências do SAEB. Porta a aba "Simulador Ideb" da planilha
do Núcleo da Seplag para o mesmo front-end do Simulador BDE.

Página estática: não tem backend. Esta pasta é autossuficiente — o **conteúdo**
dela (não a pasta) vai para a raiz do repositório, e o GitHub Pages serve o
`index.html` da raiz.

## A regra

IDEB = N × P, por etapa (não existe IDEB único da escola).

- **P (fluxo):** média harmônica das taxas de aprovação dos anos da etapa.
  Ano que a escola não tem fica em branco e fora da média.
- **N (aprendizado):** média das notas de LP e MT no SAEB, cada uma
  padronizada por (proficiência − Sinf) ÷ (Ssup − Sinf) × 10, com os limites
  do SAEB 1997 (Inep):

  | Etapa | LP Sinf–Ssup | MT Sinf–Ssup |
  | --- | --- | --- |
  | Anos Iniciais (1º ao 5º ano) | 49–324 | 60–322 |
  | Anos Finais (6º ao 9º ano) | 100–400 | 100–400 |
  | Ensino Médio (1ª à 4ª série) | 117–451 | 111–467 |

- **Resultado com uma casa decimal.**

Única diferença de propósito para a planilha: com N × P = 0 a planilha deixa a
célula em branco; o simulador mostra 0,0.

## Arquivos

- `motor.js` — o cálculo, sem DOM
- `wizard.js` — navegação e telas
- `estilo.css` — cópia do estilo do Simulador BDE + o que só o IDEB usa
- `img/logo-ngr.png`
- `tests/test_ideb.py` — confere o motor contra valores calculados pela
  própria planilha (`python3 tests/test_ideb.py`, precisa do Node)

Para ver localmente: `python3 -m http.server` nesta pasta e abra
http://127.0.0.1:8000.
