import json
import re

from app.llm import call_llm


def carregar_prompt(nome_arquivo):
    with open(f"prompts/{nome_arquivo}", "r", encoding="utf-8") as f:
        return f.read()


def gerente_decisor(insights_dict):
    """
    Consolidar insights estruturados (kpis/insights) em um plano executivo em Markdown.
    """
    template = carregar_prompt("gerente.txt")

    insights_json = json.dumps(
        insights_dict,
        ensure_ascii=False,
        indent=2,
    )

    if "{insights}" not in template:
        raise Exception("[!] Placeholder {insights} não encontrado no prompt do gerente.")

    # Evita problemas do .format com chaves do JSON.
    prompt = template.replace("{insights}", insights_json)

    resposta = call_llm(prompt)

    if not resposta:
        return "❌ Gerente não retornou conteúdo"

    if _validar_formato_dashboard(resposta):
        return resposta

    # 1 retry: reformatar exatamente no molde do prompt.
    retry_prompt = (
        prompt
        + "\n\n---\n"
        + "ATENCAO: A resposta anterior NAO seguiu o formato requerido. "
        + "Reescreva SOMENTE com Markdown e seguindo exatamente todas as seções obrigatórias do início do template."
        + "\n\n---\n"
        + "Resposta anterior (para referência):\n"
        + str(resposta)
    )

    resposta_retry = call_llm(retry_prompt)
    if resposta_retry and _validar_formato_dashboard(resposta_retry):
        return resposta_retry

    # Fallback: retorna o que veio, mas sinaliza problema de formato.
    return "❌ Gerente retornou conteúdo, mas o formato ficou fora do padrão.\n\n" + str(resposta)


def _validar_formato_dashboard(markdown: str) -> bool:
    if not isinstance(markdown, str) or not markdown.strip():
        return False

    # Seções obrigatórias do prompt (todas devem existir).
    obrigatorias = [
        r"^#\s+🧭\s+Plano Executivo de Dashboard\s*$",
        r"^##\s+🎯\s+Objetivo do Dashboard\s*$",
        r"^##\s+🧠\s+Leitura Executiva\s*$",
        r"^##\s+📈\s+KPIs Prioritários\s*$",
        r"^##\s+📊\s+Visualizações Recomendadas\s*$",
        r"^##\s+🧠\s+Insights Refinados e Priorizados\s*$",
        r"^##\s+⚠️\s+Pontos de Atenção\s*$",
        r"^##\s+🛠️\s+Estrutura Técnica do Dashboard\s*$",
        r"^##\s+🚀\s+Roadmap de Implementação\s*$",
        r"^##\s+📌\s+Recomendações Executivas\s*$",
    ]

    for pattern in obrigatorias:
        if not re.search(pattern, markdown, flags=re.MULTILINE):
            return False

    return True