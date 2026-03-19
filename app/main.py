# -*- coding: utf-8 -*-
import subprocess
import webbrowser
import time
import sys
import socket
import io

# Força encoding UTF-8 mesmo no Windows
if sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from app.excel_reader import read_all_excels
from app.llm_retraining import SistemaRetraining

from app.assistentes import (
    assistente_financeiro,
    assistente_operacional,
    assistente_estrategico
)

from app.gerente import gerente_decisor

from app.file_manager import save_outputs

# =========================
# PIPELINE PRINCIPAL
# =========================
def main(skip_dashboard=False):
    print("[*] Lendo planilhas...")
    df = read_all_excels("data")

    if df is None:
        print("Nenhuma planilha encontrada ou não há dados válidos.")
        return

    print("[*] Executando assistentes...")

    insights = {
        "financeiro": assistente_financeiro(df),
        "operacional": assistente_operacional(df),
        "estrategico": assistente_estrategico(df)
    }

    print("[*] Gerente consolidando decisao...")
    markdown = gerente_decisor(insights)

    print("[*] Salvando outputs...")
    save_outputs(insights, markdown)

    print("[OK] Pipeline finalizado!")
    
    if not skip_dashboard:
        return True  # Indica que pode abrir dashboard
    return False


# =========================
# STREAMLIT
# =========================
def esperar_streamlit(host="localhost", port=8501, timeout=10):
    for _ in range(timeout):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except:
            time.sleep(1)
    return False

def run_dashboard(open_browser=True):
    print("[>] Iniciando dashboard...")

    streamlit_process = subprocess.Popen([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "dashboard.py"
    ])

    if esperar_streamlit():
        print("[OK] Dashboard iniciado em: http://localhost:8501")
        if open_browser:
            webbrowser.open("http://localhost:8501")
        
        print("\n[!] Para sair do dashboard, pressione Ctrl+C nesta janela.")
        try:
            streamlit_process.wait()
        except KeyboardInterrupt:
            print("\n[-] Encerrando dashboard...")
            streamlit_process.terminate()
            streamlit_process.wait()
    else:
        print("[!] Streamlit demorou para subir")
        streamlit_process.terminate()


def show_menu():
    """Exibe menu interativo para o usuário escolher opção."""
    print("\n" + "="*60)
    print("DASHBOARD IA - MENU PRINCIPAL")
    print("="*60)
    print("1. Apenas RODAR ANALISE (cria JSON, Markdown, PDF)")
    print("2. RODAR ANALISE + ABRIR DASHBOARD")
    print("3. APENAS ABRIR DASHBOARD (sem rodar analise novamente)")
    print("4. SAIR")
    print("="*60)
    
    while True:
        try:
            opcao = input("\nEscolha uma opcao (1-4): ").strip()
            if opcao in ["1", "2", "3", "4"]:
                return opcao
            print("[!] Opcao invalida. Digite 1, 2, 3 ou 4.")
        except KeyboardInterrupt:
            print("\nAte logo!")
            sys.exit(0)

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    opcao = show_menu()
    
    if opcao == "1":
        # Apenas rodar análise
        print("\n[>>] Rodando analise...\n")
        main(skip_dashboard=True)
        print("\n[OK] Analise completa! Arquivos salvos em 'outputs/'")
        print("[OK] Verifique: JSON, Markdown e PDF em outputs/")
        
    elif opcao == "2":
        # Rodar análise + dashboard
        print("\n[>>] Rodando analise e abrindo dashboard...\n")
        main(skip_dashboard=False)
        run_dashboard(open_browser=True)
        
    elif opcao == "3":
        # Apenas dashboard
        print("\n[>>] Abrindo dashboard...\n")
        run_dashboard(open_browser=True)
        
    elif opcao == "4":
        print("👋 Até logo!")
        sys.exit(0)