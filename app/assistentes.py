import os
import sys
from app.llm import call_llm
from app.llm_validator import (
    ValidadorAlucinacao,
    criar_dados_validacao,
    extrair_json_do_texto,
    normalizar_payload_area,
)
from app.llm_retraining import SistemaRetraining

# =========================
# CARREGAR PROMPT
# =========================
def carregar_prompt(nome_arquivo):
    caminhos = []

    # Quando empacotado com PyInstaller, recursos estão em sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Prompts foram colocados em sys._MEIPASS/prompts via --add-data
        meipass_path = os.path.join(sys._MEIPASS, "prompts", nome_arquivo)
        caminhos.append(meipass_path)
        if os.path.exists(meipass_path):
            with open(meipass_path, "r", encoding="utf-8") as f:
                return f.read()

    # Execução normal: procura em app/prompts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, "prompts", nome_arquivo)
    caminhos.append(local_path)
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()

    # Procura no diretório raiz do projeto
    projeto_root = os.path.dirname(base_dir)
    root_path = os.path.join(projeto_root, "prompts", nome_arquivo)
    caminhos.append(root_path)
    if os.path.exists(root_path):
        with open(root_path, "r", encoding="utf-8") as f:
            return f.read()

    raise Exception(f"[!] Prompt '{nome_arquivo}' nao encontrado. Procurei em: {caminhos}")


# =========================
# GERADOR PADRAO DE PROMPT COM VALIDACAO
# =========================
def gerar_prompt(nome_arquivo, df):
    """Gera prompt com dados reais para validação."""
    template = carregar_prompt(nome_arquivo)
    
    # Cria sumário dos dados reais para o assistente verificar
    dados_reais = criar_dados_validacao(df)

    if "{dados}" not in template:
        raise Exception("[!] Placeholder {dados} não encontrado no prompt.")

    # Usar replace evita problemas com chaves { } presentes em JSON.
    prompt = template.replace("{dados}", dados_reais)

    return prompt


# =========================
# VALIDACAO E AUTOCORRECCAO
# =========================
def chamar_assistente_com_validacao(nome_arquivo, tipo_assistente, df, max_tentativas=1):
    """
    Chama assistente com validação de alucinação e aprendizado.
    
    Args:
        nome_arquivo: nome do arquivo de prompt (já deve ser o v2)
        tipo_assistente: 'financeiro', 'operacional' ou 'estrategico'
        df: dataframe com os dados
        
    Returns:
        Resposta validada
    """
    validador = ValidadorAlucinacao(df)
    retraining = SistemaRetraining()

    if max_tentativas < 1:
        max_tentativas = 1

    for tentativa in range(max_tentativas):
        print(f"   [Validando resposta... {tentativa + 1}/{max_tentativas}]", end=" ")

        # Gera prompt
        prompt = gerar_prompt(nome_arquivo, df)

        if tentativa > 0:
            # Reforça contrato caso a tentativa anterior falhe em produzir JSON válido.
            prompt += (
                "\n\n=== CONTRATO DE SAIDA (OBRIGATORIO) ===\n"
                "- Responda APENAS com JSON válido.\n"
                "- Não inclua texto antes/depois, nem Markdown ou codefence.\n"
                "- O JSON DEVE ser um objeto (dict) e seguir o esquema descrito.\n"
            )

        # Chama LLM
        resposta = call_llm(prompt)

        if resposta is None:
            print("Erro ao chamar LLM (resposta None)")
            payload_norm = normalizar_payload_area({"texto_markdown": ""}, tipo_assistente)
            payload_norm["valido_por_conteudo"] = False
            payload_norm["erro_llm"] = "resposta None"
            return payload_norm

        if not isinstance(resposta, str) or resposta.startswith("[!]"):
            print("Erro ao chamar LLM")
            payload_norm = normalizar_payload_area({"texto_markdown": str(resposta)}, tipo_assistente)
            payload_norm["valido_por_conteudo"] = False
            payload_norm["erro_llm"] = "resposta inválida ou prefixo [!]"
            return payload_norm

        # Valida resposta (regex/heurísticas)
        resultado_validacao = validador.validar_resposta(resposta, tipo_assistente)

        # Processa resultado e filtra falsos positivos
        avisos_reais = retraining.processar_resultado(
            tipo_assistente,
            resultado_validacao["avisos"],
            resultado_validacao["alucinacoes"],
            resposta,
        )

        payload, erro_json = extrair_json_do_texto(resposta)
        payload_norm = normalizar_payload_area(payload or {"texto_markdown": resposta}, tipo_assistente)

        payload_norm["avisos_validador"] = avisos_reais
        payload_norm["alucinacoes_validador"] = resultado_validacao["alucinacoes"]
        payload_norm["erro_json"] = erro_json

        texto_markdown = str(payload_norm.get("texto_markdown") or "").strip()
        resumo = str(payload_norm.get("resumo_executivo") or "").strip()
        kpis = payload_norm.get("kpis") or []
        insights = payload_norm.get("insights") or []
        pontos = payload_norm.get("pontos_de_atencao") or []

        conteudo_estruturado_vazio = (
            not texto_markdown
            and not resumo
            and isinstance(kpis, list) and len(kpis) == 0
            and isinstance(insights, list) and len(insights) == 0
            and isinstance(pontos, list) and len(pontos) == 0
        )

        contrato_ok = (erro_json is None) and (not conteudo_estruturado_vazio)

        if conteudo_estruturado_vazio and erro_json is None:
            payload_norm["erro_conteudo"] = "conteudo_estruturado_vazio"

        payload_norm["valido_por_conteudo"] = bool(resultado_validacao["valida"]) and (
            not payload_norm["alucinacoes_validador"]
        ) and contrato_ok

        # Log simplificado
        if payload_norm["valido_por_conteudo"] and not avisos_reais:
            print("[OK] Validado (JSON + validação)")
            return payload_norm

        if erro_json is not None:
            print("[!] JSON inválido (contrato).")
        elif conteudo_estruturado_vazio and erro_json is None:
            print("[!] Conteúdo JSON vazio (contrato).")
        elif avisos_reais or resultado_validacao["alucinacoes"]:
            print("[!] Avisos/alucinações detectadas (mas JSON pode estar ok).")

        # Se o contrato falhou (JSON ou conteúdo vazio), tenta de novo.
        if (erro_json is not None or conteudo_estruturado_vazio) and tentativa < max_tentativas - 1:
            continue

        # Fallback: retorna o que veio (mesmo assim, com flags)
        return payload_norm

    # Nunca deveria chegar aqui.
    payload_norm = normalizar_payload_area({"texto_markdown": ""}, tipo_assistente)
    payload_norm["valido_por_conteudo"] = False
    payload_norm["erro_llm"] = "falha inesperada no loop"
    return payload_norm

# =========================
# ASSISTENTE FINANCEIRO
# =========================
def assistente_financeiro(df):
    print(f"[*] Leitura Assistente Financeiro")
    return chamar_assistente_com_validacao(
        "assistente_financeiro_v2.txt", 
        "financeiro", 
        df,
        max_tentativas=3,
    )

# =========================
# ASSISTENTE OPERACIONAL
# =========================
def assistente_operacional(df):
    print(f"[*] Leitura Assistente Operacional")
    return chamar_assistente_com_validacao(
        "assistente_operacional_v2.txt", 
        "operacional", 
        df,
        max_tentativas=3,
    )

# =========================
# ASSISTENTE ESTRATEGICO
# =========================
def assistente_estrategico(df):
    print(f"[*] Leitura Assistente Estrategico")
    return chamar_assistente_com_validacao(
        "assistente_estrategico_v2.txt", 
        "estrategico", 
        df,
        max_tentativas=3,
    )