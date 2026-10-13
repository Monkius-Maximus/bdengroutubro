# Simulador IDEPE — NGR-EDU · Seplag

Simula o IDEPE da escola por etapa, a partir das taxas de aprovação do Censo
Escolar e das proficiências do SAEPE. Porta a aba "Simulador IDEPE" da planilha
do Núcleo da Seplag para o mesmo front-end do Simulador BDE.

Página estática: não tem backend. Esta pasta é autossuficiente — vira a raiz de
um repositório próprio sem mudar nada, e o GitHub Pages serve o `index.html`.

## A regra

IDEPE = N × P, por etapa (não existe IDEPE único da escola).

- **P (fluxo):** média harmônica das taxas de aprovação dos anos da etapa.
  Ano que a escola não tem fica em branco e fora da média.
  **Taxa abaixo de 65% entra como 65%.**
- **N (aprendizado):** média das notas de LP e MT no SAEPE, cada uma
  padronizada por (proficiência − Sinf) ÷ (Ssup − Sinf) × 10:

  | Etapa | LP Sinf–Ssup | MT Sinf–Ssup |
  | --- | --- | --- |
  | Anos Iniciais (1º ao 5º ano) | 49–324 | 60–322 |
  | Anos Finais (6º ao 9º ano) | 100–400 | 100–400 |
  | Ensino Médio (1ª à 3ª série) | 117–451 | 111–467 |

- **Resultado com duas casas decimais.**

O que distingue do IDEB: o piso de 65% nas aprovações, a prova (SAEPE e não
SAEB), o ensino médio só até a 3ª série e as duas casas decimais. A regra de
participação de 80% é do BDE, não do IDEPE, e não entra aqui.

Única diferença de propósito para a planilha: com N × P = 0 a planilha deixa a
célula em branco; o simulador mostra 0,00.

## Arquivos

- `motor.js` — o cálculo, sem DOM
- `wizard.js` — navegação e telas
- `estilo.css` — cópia do estilo do Simulador BDE + o que só o IDEPE usa
- `img/logo-ngr.png`
- `tests/test_idepe.py` — confere o motor contra valores calculados pela
  própria planilha (`python3 tests/test_idepe.py`, precisa do Node)

Para ver localmente: `python3 -m http.server` nesta pasta e abra
http://127.0.0.1:8000.
