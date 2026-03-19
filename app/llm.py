from openai import OpenAI
import os
import sys
from dotenv import load_dotenv


# Carrega .env de modo compatível com execução normal e PyInstaller (--onefile)
def _load_env():
    env_paths = []

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # quando empacotado com PyInstaller, arquivos adicionados via --add-data
        # são extraídos em sys._MEIPASS
        env_paths.append(os.path.join(sys._MEIPASS, ".env"))

    # caminho relativo ao repositório (execução normal)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_paths.append(os.path.join(base_dir, ".env"))

    for p in env_paths:
        if os.path.exists(p):
            load_dotenv(p)
            return p

    # tenta carregar sem caminho (dotenv procura por padrão)
    load_dotenv()
    return None


_load_env()

api_key = os.getenv("OPENROUTER_API_KEY")

# Não printar a chave (sensível). Apenas indica se está presente.
if api_key:
    _has_key = True
else:
    _has_key = False

client = None
if _has_key:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    except Exception:
        client = None


def call_llm(prompt):
    if client is None:
        return "❌ OPENROUTER_API_KEY não encontrada ou cliente não inicializado. Verifique o .env ou variável de ambiente."

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )

        if not response or not getattr(response, "choices", None):
            return "❌ Erro: resposta vazia da IA"

        # compatibilidade com diferentes formatos de resposta
        try:
            content = response.choices[0].message.content
        except Exception:
            content = getattr(response.choices[0], "text", None)

        if not content:
            return "❌ Erro: conteúdo vazio retornado pela IA"

        return content

    except Exception as e:
        return f"❌ Erro ao chamar IA: {str(e)}"