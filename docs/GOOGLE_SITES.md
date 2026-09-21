# Publicar no Google Sites

O que muda entre o backend deste repositório e uma página no Google Sites, e o
passo a passo para pôr o simulador no ar.

## O impedimento

O Google Sites é hospedagem **estática**. Ele serve HTML, CSS e JavaScript e
não executa nada do lado do servidor: não há Python, não há `uvicorn`, não há
como subir o FastAPI lá dentro. Não existe configuração que contorne isso.

Restavam duas saídas, e a escolhida foi a primeira:

1. **Calcular no navegador.** A fórmula do BDE é aritmética sobre meia dúzia de
   números — não precisa de servidor. `index.html` é a interface do NGR-SEE
   com o motor em JavaScript no lugar do `fetch`: mesma tela, mesmo fluxo de 8
   passos, mesmos cartões de resultado, sem rede. Sem hospedagem, sem custo,
   sem CORS, sem cold start.
2. Manter o FastAPI hospedado fora (Render, Fly, Cloud Run) e chamar por
   `fetch`. Descartada: acrescenta um ponto de falha e uma conta a pagar para
   calcular uma média ponderada.

O backend **não foi removido**. Ele continua sendo a referência auditável da
regra e o outro lado do teste de paridade (`tests/test_paridade.py`), que é o
que impede os dois motores de divergirem em silêncio.

## O que mudou da versão FastAPI

| Antes | Agora |
| --- | --- |
| `app/templates/index.html` + `static/css` + `static/js` servidos pelo Jinja2 | `index.html` único na raiz, com CSS e JS embutidos |
| `POST /api/v1/simular-bde` via `fetch` | `simularBde(payload)` local, devolvendo o mesmo formato |
| `<img src="/static/img/...">` | `<img src="app/static/img/...">`, relativo à raiz |
| `main.py` servindo a página | `main.py` serve só a API; a página não depende dele |

**A página é gerada a partir do `app/`, não escrita à mão.** O HTML, o CSS e o
JS de `app/` continuam sendo a fonte; `index.html` é os três num arquivo só,
com o `fetch` trocado pelo motor local. Mexeu no `app/`, regenere o
`index.html` — senão a página publicada congela na versão antiga.

O fluxo, os textos, os popups, os cartões e o selo circular são os do sistema
em uso. Mudou um defeito só, e ele estava nos dois:

- O rodapé é `position: fixed` e o `.wizard-container` reservava `80px` embaixo
  para não passar por baixo dele. Em tela estreita o rodapé passa de 80 px — os
  dois botões e o crédito quebram em várias linhas — e cobre o botão "Próximo".
  Medido a 390 px: rodapé de 146 px começando em y=714, botão terminando em
  y=780, `elementFromPoint` devolvendo `footer`. **Na etapa de equidade não
  havia como avançar pelo celular.** `ajustarEspacoDoRodape()` passou a reservar
  a altura real, medida, com `Math.max(80, …)` para não mexer no desktop.

## O que a página teve de respeitar

Restrições do embed do Google Sites que moldaram `index.html`:

| Restrição | Consequência no código |
| --- | --- |
| O conteúdo roda dentro de um iframe em origem isolada do Google | `localStorage`, `sessionStorage` e cookies podem simplesmente lançar exceção. A página não usa nenhum dos três: todo o estado vive em memória. |
| A altura do iframe é fixada no editor e a página não consegue redimensionar o pai | O que passar da altura do embed rola dentro dele. O rodapé fixo torna o `ajustarEspacoDoRodape()` obrigatório: sem ele o botão de avançar some sob o rodapé em embed estreito. |
| O campo "Inserir código" é uma caixa de texto para trechos curtos | Os 60 KB da página não se colam ali. A página é hospedada e o embed é só um `<iframe>` de uma linha. |
| A largura do embed varia com o tema e o dispositivo | Layout fluido, com quebra para coluna única abaixo de 460 px. |
| Recursos externos podem ser bloqueados ou ficar lentos | Zero dependências: nenhuma fonte do Google Fonts, nenhuma biblioteca de CDN. Só a página e o logo — 116 KB no total. |

## Passo a passo

### 1. Hospedar a página

Pelo GitHub Pages, que já é onde o repositório está:

1. **Settings → Pages** no repositório.
2. Em *Source*, escolha **Deploy from a branch**; branch `main`, pasta `/ (root)`.
3. Salve e aguarde o deploy.

A página fica em `https://monkius-maximus.github.io/bdengroutubro/`.

O `index.html` está na **raiz** do repositório de propósito: o GitHub Pages serve
`index.html` da raiz nesse endereço direto. Se o arquivo estivesse numa subpasta,
esse endereço cairia no `README.md` renderizado — que é uma página de
documentação, não o simulador.

> **Se o endereço mostrar o README,** é sempre a mesma causa: a branch escolhida
> em *Settings → Pages* não tem `index.html` na raiz. Já aconteceu — a página
> vivia numa branch, a `main` recebeu o `app/` do FastAPI sem a versão estática,
> e o Pages passou a servir a documentação. Confira em qual branch o Pages está
> apontado e se aquela branch tem o `index.html` na raiz.

### 2. Embutir no site

No editor do Google Sites: **Inserir → Incorporar → Código incorporado**, e cole
a linha abaixo trocando o endereço pelo do passo anterior.

```html
<iframe src="https://monkius-maximus.github.io/bdengroutubro/"
        style="width:100%;height:900px;border:0" title="Simulador do BDE"></iframe>
```

Depois arraste o bloco para ocupar a largura inteira da seção. `height` é o
único ajuste que costuma ser necessário: a tela de resultado, com os seis
cartões e as notas de rodapé, é a mais alta.

## Manutenção

A regra do BDE muda entre ciclos — pesos das cotas, faixas de conversão,
percentual mínimo de participação. Quando mudar, **altere os dois motores** e
rode o teste de paridade antes de publicar:

```bash
python3 tests/test_paridade.py
```

Ele compara 552 casos entre `src/bde/service.py` e o JavaScript de
`index.html` — a resposta inteira, campo a campo, inclusive os nomes —
varrendo os limites da tabela de conversão, onde 0,01 na média ponderada vale
25 pontos percentuais de bônus.

O teste existe porque esse desencontro já aconteceu duas vezes. Uma, quando os
schemas foram renomeados no backend sem o frontend junto, que morava em outro
repositório: 422 no POST e `NaN%` nos cartões. Outra, neste porte, quando o
motor da página devolvia `media_ponderada_diferenca` e o contrato pedia
`media_ponderada_variacao` — o wizard não lê esse campo, então nada aparecia
quebrado na tela, e só o teste pegou.

### Regenerar a página

Depois de mexer em `app/templates/index.html`, `app/static/css/estilo.css` ou
`app/static/js/wizard.js`:

1. Junte os três em `index.html`, trocando os caminhos `/static/...` por
   `app/static/...` e o `fetch('/api/v1/simular-bde')` pela chamada a
   `simularBde(payload)`.
2. Rode `python3 tests/test_paridade.py`.
3. Confira a página no navegador em largura de celular, porque é lá que o
   rodapé fixo cobre os botões.
