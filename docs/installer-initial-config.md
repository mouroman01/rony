# Configuracao inicial no instalador

O instalador do Rony agora pode coletar, durante a instalacao:

- nome pelo qual a pessoa quer ser chamada;
- nome do assistente, usando Rony quando o campo fica em branco;
- chaves de API para Gemini, Groq, OpenAI, Anthropic e XAI/Grok.

As chaves informadas sao gravadas no arquivo `.env` da pasta instalada. As preferencias de nome sao gravadas em `%LOCALAPPDATA%\Rony\data\rony_config.json`, para o aplicativo ja iniciar personalizado.
