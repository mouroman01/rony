# Instalar o R.O.N.Y em outro computador

Este guia serve para baixar a versao atual do R.O.N.Y do GitHub e iniciar em um novo computador Windows.

## 1. Entrar na mesma conta

Para continuar a conversa com o Codex/ChatGPT, entre no outro computador usando a mesma conta em que este projeto foi criado.

Mesmo que a conversa nao apareca, o codigo esta publicado no GitHub:

```text
https://github.com/mouroman01/rony
```

## 2. Instalar os programas necessarios

Instale no novo computador:

- Git
- Python 3.11 ou superior
- Node.js LTS, caso precise reconstruir o frontend

Depois reinicie o PowerShell para garantir que os comandos fiquem disponiveis.

## 3. Baixar o projeto

Abra o PowerShell na pasta onde deseja guardar o projeto e rode:

```powershell
git clone https://github.com/mouroman01/rony.git
cd rony
```

## 4. Criar o arquivo .env

O arquivo `.env` nao sobe para o GitHub porque contem chaves privadas.

Crie um arquivo chamado `.env` dentro da pasta `rony` e coloque suas chaves:

```env
GEMINI_API_KEY=sua_chave_gemini_aqui
SERPAPI_API_KEY=sua_chave_serpapi_aqui
OPENAI_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
XAI_API_KEY=
```

As chaves vazias podem ficar assim se voce ainda nao usa esses provedores.

## 5. Instalar dependencias

Na pasta do projeto, execute:

```powershell
cmd /c INSTALAR.bat
```

Esse passo cria o ambiente virtual Python e instala as dependencias do R.O.N.Y.

## 6. Iniciar o R.O.N.Y

Depois da instalacao:

```powershell
cmd /c INICIAR_RONY.bat
```

Se quiser usar o atalho mais curto:

```powershell
cmd /c INICIAR.bat
```

## 7. Testes iniciais recomendados

Com o R.O.N.Y aberto, teste comandos simples primeiro:

```text
Rony, que horas sao?
Rony, abrir YouTube
Rony, pesquisar lojas de notebook em Sao Paulo
Rony, tira print
Rony, status da camera
```

Depois teste comandos mais pesados:

```text
Rony, analisa a tela
Rony, o que voce ve pela camera?
Rony, faca uma busca de viabilidade sobre abrir uma loja de acai no meu bairro
```

## 8. Atualizar no futuro

Quando houver novas atualizacoes no GitHub, entre na pasta do projeto e rode:

```powershell
git pull origin main
```

Depois inicie novamente:

```powershell
cmd /c INICIAR_RONY.bat
```

## Observacoes importantes

- Nunca publique o arquivo `.env`.
- Se o Windows pedir permissao para camera, microfone ou rede, permita para o R.O.N.Y funcionar corretamente.
- Se o computador antigo estiver lento, use o novo computador como ambiente principal e mantenha o projeto atualizado pelo GitHub.
- Toda versao publicada no GitHub deve ser considerada a fonte principal do projeto.
