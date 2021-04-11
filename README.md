# El Informador Madrileño

Telegram bot for updating on Madrid weather

<https://t.me/MadriletaBot>

Almost every response is in Spanish, if you want internationalization open an issue to see if there is demand for it

## Authentication

This bot need the telegram bot token, a OpenWeatherMap api key and a redis instance to save user subscriptions.
Optional: specify the creator id for the "notificar" command.

You can have a .env file with the following structure:

```text
BOT_TOKEN=<token>
MAP_KEY=<OpenWeatherMap api key>
REDIS_URL=<redis URL>
REDIS_PORT=<redis port>
CREATOR=<creator [optional]>
```

Or you can set the following environment variables:

- BOT_TOKEN: Telegram bot token
- MAP_KEY: OpenWeatherMap api key
- REDIS_URL: Redis URL
- REDIS_PORT: Redis port
- CREATOR: creator [optional]
