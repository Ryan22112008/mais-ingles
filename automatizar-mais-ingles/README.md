# Mais Inglês MT Automation

Automação modular para interação com a plataforma educacional Mais Inglês MT usando Python + Playwright.

## Estrutura do projeto

```text
automatizar-mais-ingles/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── main.py
├── src/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   ├── llm.py
│   └── utils.py
└── artifacts/
    └── screenshots/
```

## Requisitos

- Python 3.10+
- Google Chrome / Chromium ou Microsoft Edge instalados
- Tesseract OCR (se quiser usar OCR local)
- OpenAI API Key (opcional, para inteligência mais robusta)

## Configuração

1. Crie um ambiente virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
playwright install chromium
```

3. Copie o arquivo de exemplo:

```bash
copy .env.example .env
```

4. Edite o `.env` com suas credenciais e configuração.

Exemplo:

```env
MAIS_INGLES_USERNAME=seu_cpf_ou_login
MAIS_INGLES_PASSWORD=sua_senha
MAIS_INGLES_BASE_URL=https://maisingles.seduc.mt.gov.br
OPENAI_API_KEY=sua_chave
LLM_MODEL=gpt-4o-mini
PLAYWRIGHT_HEADLESS=true
```

## Como rodar

```bash
python main.py
```

Se quiser rodar em modo de depuração visual:

```env
PLAYWRIGHT_HEADLESS=false
DEBUG=true
```

## Observações importantes

- O código foi desenhado para ser modular e robusto, com seletores genéricos para lidar com diferentes páginas da plataforma.
- O uso de LLM é opcional. Se a chave da OpenAI não estiver configurada, o bot tenta responder por heurísticas locais.
- O `playwright-stealth` ajuda a reduzir a detecção do navegador por automação.
- Em caso de erro ou página inesperada, screenshots são salvos em `artifacts/screenshots`.

## Dicas de instalação do Tesseract (Windows)

- Baixe em: https://github.com/UB-Mannheim/tesseract/wiki
- Instale e adicione a pasta `bin` ao PATH.
- No `.env`, configure:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Aviso

Este projeto é uma base para automação educacional. Sempre respeite os termos de uso, políticas de acesso e regras do ambiente da plataforma. Use com responsabilidade.
