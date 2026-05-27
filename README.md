# NoobShark Insights

Dashboard estático para GitHub Pages inspirado no conceito de inteligência de mercado tipo Targen, com identidade própria: macro, BTC, altcoins, correlações, semáforo de decisão e resumo executivo.

## O que o projeto entrega

- Dashboard web em `docs/`
- Atualização automática via GitHub Actions
- Coleta de dados com Python
- Correlações rolantes do BTC contra GOLD, SPX, DXY/USD, NASDAQ e IGV
- Scores proprietários:
  - `Global Risk Score`
  - `BTC Cycle Score`
  - `Altseason Window`
  - `Tech Correlation Score`
- Semáforo de decisão: verde, amarelo, vermelho ou preto
- Resumo executivo automático
- Histórico em JSON
- Envio opcional para Telegram

> Importante: este projeto é educacional e analítico. Não é recomendação financeira.

---

## Estrutura

```txt
noobshark-insights/
├─ docs/
│  ├─ index.html
│  ├─ styles.css
│  ├─ app.js
│  └─ data/
│     ├─ dashboard.json
│     └─ history.json
├─ scripts/
│  └─ update_data.py
├─ .github/
│  └─ workflows/
│     └─ update-dashboard.yml
├─ requirements.txt
├─ .env.example
├─ AGENTS.md
└─ README.md
```

---

## Como rodar localmente

```bash
pip install -r requirements.txt
python scripts/update_data.py
python -m http.server 8000 -d docs
```

Abra:

```txt
http://localhost:8000
```

---

## Como publicar no GitHub Pages

1. Crie um repositório no GitHub.
2. Suba todos os arquivos.
3. Vá em **Settings → Pages**.
4. Em **Build and deployment**, selecione:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/docs`
5. Salve.

A página ficará em algo como:

```txt
https://SEU_USUARIO.github.io/noobshark-insights/
```

---

## Como automatizar atualização

O arquivo `.github/workflows/update-dashboard.yml` roda:

- a cada 1 hora;
- manualmente por `workflow_dispatch`.

Ele executa `scripts/update_data.py`, atualiza os JSONs em `docs/data/` e commita as mudanças.

Em **Settings → Actions → General**, confirme que o workflow tem permissão de escrita:

```txt
Workflow permissions → Read and write permissions
```

---

## Telegram opcional

Crie secrets no GitHub:

```txt
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

O script enviará automaticamente o resumo quando esses secrets existirem.

---

## Variáveis monitoradas no MVP

### Mercado tradicional

- BTC-USD
- GOLD: `GC=F`
- S&P 500: `^GSPC`
- Nasdaq: `^IXIC`
- DXY: `DX-Y.NYB`
- IGV ETF: `IGV`

### Cripto

- BTC
- ETH
- TOTAL/TOTAL2/TOTAL3 ainda ficam como próximos passos, porque nem sempre são acessíveis de forma estável via APIs públicas gratuitas.

---

## Fórmula dos scores

### Tech Correlation Score

Média das correlações:

```txt
BTC x SPX
BTC x NASDAQ
BTC x IGV
```

### Global Risk Score

Combina:

- força do BTC em 30 dias;
- força do Nasdaq em 30 dias;
- força do S&P 500 em 30 dias;
- dólar/DXY como penalidade;
- BTC acima ou abaixo da média móvel de 200 dias;
- correlação com tecnologia.

### BTC Cycle Score

Combina:

- BTC acima da média de 200 dias;
- BTC acima da média de 200 semanas aproximada;
- retorno de 30 e 90 dias;
- drawdown contra máxima de 1 ano;
- correlação com tecnologia.

### Altseason Window

Combina:

- ETH/BTC em 30 dias;
- BTC estável ou construtivo;
- Nasdaq construtivo;
- dólar fraco;
- ambiente de correlação favorável;
- sem euforia extrema.

---

## Próximos módulos recomendados

- Integração Hyperliquid: funding, open interest e CVD.
- Integração Deribit: call wall, put wall, IV e vencimentos.
- Fear & Greed Index.
- Dominância BTC.
- TOTAL2/TOTAL3.
- Análise de canais do YouTube.
- Feed editorial com curadoria LLM.
- Backtest do semáforo.
- Página de histórico com performance 7D/30D.
- Sistema de alertas por mudança de regime.

---

## Prompt para usar no Antigravity

Copie este briefing para o Antigravity:

```txt
Quero evoluir este repositório NoobShark Insights.

Objetivo: transformar o MVP em uma plataforma estática no GitHub Pages com dashboard executivo de mercado, scores proprietários e feed de inteligência.

Preserve a arquitetura atual:
- docs/index.html
- docs/app.js
- docs/styles.css
- scripts/update_data.py
- docs/data/dashboard.json
- docs/data/history.json
- GitHub Actions rodando de hora em hora.

Prioridades:
1. Melhorar UI dark premium.
2. Criar página separada de histórico.
3. Adicionar gráficos de correlação rolante do BTC com GOLD, SPX, DXY, NASDAQ e IGV.
4. Adicionar cards de semáforo, Global Risk Score, BTC Cycle Score e Altseason Window.
5. Criar feed de insights em formato curto.
6. Manter fallback quando APIs falharem.
7. Não adicionar backend pago.
8. Manter deploy compatível com GitHub Pages.
9. Código limpo, comentado e simples de manter.
10. O projeto é educacional e não deve prometer rentabilidade.
```
