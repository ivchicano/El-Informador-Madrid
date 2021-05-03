# El Informador Madrileño

Telegram bot for updating on Madrid weather

<https://t.me/MadriletaBot>

Almost every response is in Spanish, if you want internationalization open an issue to see if there is demand for it.

## Authentication

This bot need the telegram bot token and a OpenWeatherMap api key.
Optional: specify the creator id for the "notificar" command.

You have to set the following environment variables:

- BOT_TOKEN: Telegram bot token.
- MAP_KEY: OpenWeatherMap api key.
- CREATOR: creator id to allow the "notificar" command [optional]
- WEBHOOK_URL: URL to direct the webhook to. Examples: https://15s43cd72fe.ngrok.io/bot_token, https://appname.heroku.com/bot_token
- PORT: port for the webhook to listen to. Defaults to 8080.

The bot uses webhook to connect to the telegram API from Heroku. You can use ngrok for developing locally lie this:
```bash
ngrok http 8080
```
