import pandas as pd
import os
import sys


def _resolve_data_folder(folder_path):
    # Se o caminho foi passado explicitamente e existe, use-o
    if folder_path and os.path.exists(folder_path):
        return folder_path

    tried = []

    # Quando empacotado com PyInstaller --onefile, recursos adicionados por
    # --add-data são extraídos em sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = os.path.join(sys._MEIPASS, folder_path)
        tried.append(candidate)
        if os.path.exists(candidate):
            return candidate

    # caminho relativo ao código (execução normal ou quando dist contém pasta)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base_dir, folder_path)
    tried.append(candidate)
    if os.path.exists(candidate):
        return candidate

    # caminho relativo ao diretório de trabalho atual
    candidate = os.path.join(os.getcwd(), folder_path)
    tried.append(candidate)
    if os.path.exists(candidate):
        return candidate

    # Se nada encontrou, retorna o caminho relativo ao cwd (cria se houver dados)
    return os.path.join(os.getcwd(), folder_path)


def _create_sample_data(folder_path="data"):
    """Cria dados de exemplo se a pasta não existir ou estiver vazia."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    sample_file = os.path.join(folder_path, "dados_exemplo.xlsx")
    if not os.path.exists(sample_file):
        # Cria um DataFrame de exemplo
        data = {
            "ano": [2023, 2023, 2024, 2024],
            "mês": [1, 2, 1, 2],
            "vlrfaturamento": [10000, 12000, 15000, 18000],
            "categoria": ["A", "B", "A", "B"]
        }
        df = pd.DataFrame(data)
        df.to_excel(sample_file, index=False)
        print(f"✓ Dados de exemplo criados em: {sample_file}")


def read_all_excels(folder_path="data"):
    folder = _resolve_data_folder(folder_path)
    dataframes = []

    # Cria dados de exemplo se necessário
    if not os.path.exists(folder) or not any(f.endswith(".xlsx") for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))):
        _create_sample_data(folder)

    # Tenta listar arquivos da pasta
    if not os.path.exists(folder):
        return None

    for file in os.listdir(folder):
        if file.endswith(".xlsx"):
            path = os.path.join(folder, file)
            try:
                df = pd.read_excel(path)
                df.columns = df.columns.str.strip().str.lower()
                dataframes.append(df)
            except Exception as e:
                print(f"⚠ Erro ao ler {file}: {e}")

    if dataframes:
        return pd.concat(dataframes, ignore_index=True)

    return None