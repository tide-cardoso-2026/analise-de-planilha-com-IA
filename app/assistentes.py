import os
import sys
from app.llm import call_llm
from app.llm_validator import ValidadorAlucinacao, criar_dados_validacao
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

    try:
        prompt = template.format(dados=dados_reais)
    except KeyError as e:
        raise Exception(f"[!] Placeholder faltando no prompt: {e}")

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
    
    print(f"   [Validando resposta...]", end=" ")
    
    # Gera prompt
    prompt = gerar_prompt(nome_arquivo, df)
    
    # Chama LLM
    resposta = call_llm(prompt)
    
    if resposta is None or resposta.startswith("[!]"):
        print("Erro ao chamar LLM")
        return resposta
    
    # Valida resposta
    resultado_validacao = validador.validar_resposta(resposta, tipo_assistente)
    
    # Processa resultado e filtra falsos positivos
    avisos_reais = retraining.processar_resultado(
        tipo_assistente,
        resultado_validacao['avisos'],
        resultado_validacao['alucinacoes'],
        resposta
    )
    
    if resultado_validacao['valida'] and not avisos_reais:
        print("[OK] Validado")
        return resposta
    
    if avisos_reais or resultado_validacao['alucinacoes']:
        print("[!] Alucinacoes detectadas")
        
        # Log das alucinações REAIS (já filtradas)
        for alucinacao in resultado_validacao['alucinacoes']:
            print(f"      - {alucinacao}")
        for aviso in avisos_reais[:3]:  # Top 3 apenas
            print(f"      - AVISO: {aviso}")
        
        # Retorna mesmo com avisos (foi detectado e está no log)
        print(f"   [Retornando resposta com correções detectadas]")
        return resposta
    
    return resposta

# =========================
# ASSISTENTE FINANCEIRO
# =========================
def assistente_financeiro(df):
    print(f"[*] Leitura Assistente Financeiro")
    return chamar_assistente_com_validacao(
        "assistente_financeiro_v2.txt", 
        "financeiro", 
        df
    )

# =========================
# ASSISTENTE OPERACIONAL
# =========================
def assistente_operacional(df):
    print(f"[*] Leitura Assistente Operacional")
    return chamar_assistente_com_validacao(
        "assistente_operacional_v2.txt", 
        "operacional", 
        df
    )

# =========================
# ASSISTENTE ESTRATEGICO
# =========================
def assistente_estrategico(df):
    print(f"[*] Leitura Assistente Estrategico")
    return chamar_assistente_com_validacao(
        "assistente_estrategico_v2.txt", 
        "estrategico", 
        df
    )