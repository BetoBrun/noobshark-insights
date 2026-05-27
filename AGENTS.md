# AGENTS.md — Diretrizes para Antigravity / agentes de código

## Missão

Construir o NoobShark Insights: uma plataforma estática de inteligência de mercado para cripto, macro e ativos globais, rodando no GitHub Pages, com atualização automática por GitHub Actions.

## Princípios de produto

- Clareza executiva acima de excesso técnico.
- Semáforo simples: verde, amarelo, vermelho e preto.
- Toda leitura deve separar:
  - dado observado;
  - interpretação;
  - risco;
  - postura operacional.
- Não escrever promessa de lucro.
- Sempre manter aviso de que não é recomendação financeira.

## Arquitetura

Manter o projeto sem backend obrigatório.

- Frontend estático em `docs/`.
- Dados em JSON dentro de `docs/data/`.
- Atualização via Python em `scripts/update_data.py`.
- Deploy por GitHub Pages.
- Automação por GitHub Actions.

## Regras de código

- Não quebrar compatibilidade com GitHub Pages.
- Evitar dependências pesadas.
- Usar JavaScript simples.
- Manter fallback visual caso os dados não carreguem.
- Documentar novas fórmulas no README.
- Evitar secrets no código.
- Secrets somente via GitHub Actions.

## Identidade editorial

Tom: executivo, direto, didático e prudente.

Exemplo de leitura:

"O BTC segue mais correlacionado com tecnologia/growth do que com ouro. Isso reforça que Nasdaq, juros e liquidez global pesam mais no curto prazo do que a narrativa de reserva de valor."

## Roadmap técnico

1. Melhorar dashboard.
2. Histórico.
3. Feed de insights.
4. Backtest.
5. Integração Hyperliquid.
6. Integração Deribit.
7. Integração Telegram.
8. Página de metodologia.
9. Modo mobile premium.
10. Exportação do resumo diário.
