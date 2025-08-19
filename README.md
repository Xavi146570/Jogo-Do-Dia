# ⚽ Futebol Alertas Automático

Este projeto consulta a **API-Football** e envia alertas no **Telegram** quando:
- A liga tem mais de 75% dos jogos com Over 1.5 gols
- A equipa tem mais de 60% de vitórias
- A equipa tem mais de 70% de jogos Over 1.5
- O último jogo terminou em Under 1.5 (0x0, 1x0, 0x1)

## 🚀 Como usar

1. Clone o repositório
2. Configure no Render:
   - `API_KEY=968c152b0a72f3fa63087d74b04eee5d`
   - `TELEGRAM_TOKEN=<seu_token_do_bot>`
   - `TELEGRAM_CHAT_ID=<id_do_grupo_ou_usuario>`
3. Deploy automático no Render com **cron job diário**

## 📦 Dependências
- requests
