from app.llm import call_llm

def carregar_prompt(nome_arquivo):
    with open(f"prompts/{nome_arquivo}", "r", encoding="utf-8") as f:
        return f.read()

def gerente_decisor(insights):
    template = carregar_prompt("gerente.txt")

    prompt = template.format(insights=insights)

    resposta = call_llm(prompt)

    if not resposta:
        return "❌ Gerente não retornou conteúdo"

    return resposta
    
def formatar_insights(insights_dict):
    texto = ""

    for area, conteudo in insights_dict.items():
        texto += f"\n## {area.upper()}\n{conteudo}\n"

    return texto    
    
    return call_llm(prompt)