# Guía para obtener las API Keys

>>> Para que Movlog funcione, es estrictamente necesario acceder al archivo .env y cambiar el contenido de las siguientes claves por las tuyas:
>>> - ALPACA_API_KEY
>>> - ALPACA_SECRET_KEY
>>> - NEWSAPI_KEY
>>> - HF_API_TOKEN

Indicaciones para rellenar ALPACA_API_KEY y ALPACA_SECRET_KEY:
1. Accede a https://alpaca.markets/
2. Inicia sesión o regístrate con tu cuenta "Trading API"
3. Activa la multi-factor authentication de tu cuenta usando la app de Google Authenticator en tu móvil (obligatorio)
4. Accede al Home y abajo a la derecha encontrarás tu sección de API Keys


Indicaciones para rellenar NEWSAPI_KEY:
1. Accede a https://newsapi.org/
2. Arriba a la derecha dale a Login o regístrate en Get API Key para encontrar tu API Key


Indicaciones para rellenar HF_API_TOKEN:
1. Accede a https://huggingface.co/ e inicia sesión o regístrate
2. Accede a tu [configuración de tokens](https://huggingface.co/settings/tokens/new?ownUserPermissions=inference.serverless.write&tokenType=fineGrained)
3. Crea un token de tipo "read" y llámalo "movlog-dev"


>>>Una vez tengas el archivo .env correctamente configurado, ejecuta por consola el siguiente comando:
>>>**start_movlog**
