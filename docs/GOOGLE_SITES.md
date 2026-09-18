# Publicar no Google Sites

O que muda entre o backend deste repositório e uma página no Google Sites, e o
passo a passo para pôr o simulador no ar.

## O impedimento

O Google Sites é hospedagem **estática**. Ele serve HTML, CSS e JavaScript e
não executa nada do lado do servidor: não há Python, não há `uvicorn`, não há
como subir o FastAPI lá dentro. Não existe configuração que contorne isso.

Restavam duas saídas, e a escolhida foi a primeira:

1. **Calcular no navegador.** A fórmula do BDE é aritmética sobre meia dúzia de
   números — não precisa de servidor. `web/index.html` carrega o motor em
   JavaScript e responde sem rede. Sem hospedagem, sem custo, sem CORS, sem
   cold start, e a página continua de pé se qualquer serviço externo cair.
2. Manter o FastAPI hospedado fora (Render, Fly, Cloud Run) e chamar por
   `fetch`. Descartada: acrescenta um ponto de falha e uma conta a pagar para
   calcular uma média ponderada.

O backend **não foi removido**. Ele continua sendo a referência auditável da
regra e o outro lado do teste de paridade (`tests/test_paridade.py`), que é o
que impede os dois motores de divergirem em silêncio.

## O que a página teve de respeitar

Restrições do embed do Google Sites que moldaram `web/index.html`:

| Restrição | Consequência no código |
| --- | --- |
| O conteúdo roda dentro de um iframe em origem isolada do Google | `localStorage`, `sessionStorage` e cookies podem simplesmente lançar exceção. A página não usa nenhum dos três: todo o estado vive em memória. |
| A altura do iframe é fixada no editor e a página não consegue redimensionar o pai | Cada tela do wizard cabe em ~640 px e o que passar disso rola dentro do próprio embed. |
| O campo "Inserir código" é uma caixa de texto para trechos curtos | Os 34 KB da página não se colam ali. A página é hospedada e o embed é só um `<iframe>` de uma linha. |
| A largura do embed varia com o tema e o dispositivo | Layout fluido, com quebra para coluna única abaixo de 460 px. |
| Recursos externos podem ser bloqueados ou ficar lentos | Zero dependências: nenhuma fonte do Google Fonts, nenhuma biblioteca de CDN. Um arquivo, nada mais. |

## Passo a passo

### 1. Hospedar a página

Pelo GitHub Pages, que já é onde o repositório está:

1. **Settings → Pages** no repositório.
2. Em *Source*, escolha **Deploy from a branch**; branch `main`, pasta `/ (root)`.
3. Salve e aguarde o deploy.

A página fica em `https://<usuário>.github.io/<repositório>/web/index.html`.
Abra esse endereço e confirme que o wizard responde antes de seguir.

### 2. Embutir no site

No editor do Google Sites: **Inserir → Incorporar → Código incorporado**, e cole
a linha abaixo trocando o endereço pelo do passo anterior.

```html
<iframe src="https://SEU-USUARIO.github.io/SEU-REPOSITORIO/web/index.html"
        style="width:100%;height:760px;border:0" title="Simulador do BDE"></iframe>
```

Depois arraste o bloco para ocupar a largura inteira da seção. `height` é o
único ajuste que costuma ser necessário: a tela de resultado é a mais alta, e
760 px evita rolagem interna na maioria dos casos.

## Manutenção

A regra do BDE muda entre ciclos — pesos das cotas, faixas de conversão,
percentual mínimo de participação. Quando mudar, **altere os dois motores** e
rode o teste de paridade antes de publicar:

```bash
python3 tests/test_paridade.py
```

Ele compara 400 casos entre `src/bde/service.py` e o JavaScript de
`web/index.html`, varrendo os limites de faixa de H45 — onde 0,0001 de
diferença vale 25 pontos percentuais de bônus.
