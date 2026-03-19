"""
Testes para o menu interativo do Dashboard IA
"""
import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Adiciona o diretório do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestMenuOpcao1:
    """Testes para a opção 1: Apenas rodar análise"""

    def setup_method(self):
        """Limpar outputs antes de cada teste"""
        output_dir = Path("outputs")
        if output_dir.exists():
            for file in output_dir.glob("*"):
                file.unlink()

    def test_opcao_1_cria_json(self):
        """Verifica se opção 1 cria arquivo JSON"""
        # Arrange
        cmd = f'echo 1 | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Assert
        assert result.returncode == 0, f"Programa falhou: {result.stderr}"
        assert Path("outputs/insights.json").exists(), "Arquivo JSON não foi criado"
        
        # Validar conteúdo JSON
        with open("outputs/insights.json") as f:
            data = json.load(f)
            assert "financeiro" in data or "operacional" in data, "JSON não tem dados esperados"

    def test_opcao_1_cria_markdown(self):
        """Verifica se opção 1 cria arquivo Markdown"""
        # Arrange
        cmd = f'echo 1 | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Assert
        assert result.returncode == 0
        assert Path("outputs/dashboard.md").exists(), "Arquivo Markdown não foi criado"
        
        # Validar conteúdo
        with open("outputs/dashboard.md") as f:
            content = f.read()
            assert len(content) > 0, "Markdown está vazio"

    def test_opcao_1_cria_pdf(self):
        """Verifica se opção 1 cria arquivo PDF"""
        # Arrange
        cmd = f'echo 1 | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Assert
        assert result.returncode == 0
        assert Path("outputs/analise_completa.pdf").exists(), "Arquivo PDF não foi criado"

    def test_opcao_1_nao_abre_browser(self):
        """Verifica se opção 1 não abre navegador"""
        # Arrange
        cmd = f'echo 1 | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        
        # Assert
        assert result.returncode == 0
        assert "Dashboard iniciado" not in result.stdout, "Dashboard foi aberto na opção 1"
        assert "✨ Análise completa!" in result.stdout, "Análise não completou com sucesso"


class TestMenuOpcao2:
    """Testes para a opção 2: Análise + Dashboard (skip em CI/CD)"""

    @pytest.mark.skip(reason="Requer interação manual (pressionar Ctrl+C)")
    def test_opcao_2_abre_dashboard(self):
        """Verifica se opção 2 abre dashboard"""
        # Este teste requer interação manual
        pass


class TestMenuOpcao3:
    """Testes para a opção 3: Apenas Dashboard (skip em CI/CD)"""

    @pytest.mark.skip(reason="Requer interação manual (pressionar Ctrl+C)")
    def test_opcao_3_apenas_dashboard(self):
        """Verifica se opção 3 abre apenas dashboard"""
        # Este teste requer interação manual
        pass


class TestMenuOpcao4:
    """Testes para a opção 4: Sair"""

    def test_opcao_4_sair(self):
        """Verifica se opção 4 encerra o programa"""
        # Arrange
        cmd = f'echo 4 | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        # Assert
        assert result.returncode == 0
        assert "👋 Até logo!" in result.stdout, "Mensagem de saída não encontrada"


class TestMenuValidacao:
    """Testes para validação de entrada"""

    def test_opcao_invalida(self):
        """Verifica comportamento com entrada inválida"""
        # Arrange - simular entrada inválida seguida de saída
        cmd = f'echo -e "5\\n4" | & "D:\\02. ProjetoIADashboard\\dist\\main.exe"'
        
        # Act
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        # Assert
        assert result.returncode == 0
        assert "❌ Opção inválida" in result.stdout or "Digite 1, 2, 3 ou 4" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
