"""
Sistema de validação e autocorreção de respostas dos assistentes.
Detecta alucinações e atualiza prompts automaticamente.
"""

import re
import pandas as pd
from pathlib import Path


class ValidadorAlucinacao:
    """Detecta e previne alucinações nas respostas dos assistentes."""
    
    def __init__(self, df):
        """
        Args:
            df: DataFrame com os dados reais
        """
        self.df = df
        self.anos_reais = sorted(df['ano'].unique())
        self.meses_reais = sorted(df['mês'].unique())
        self.clientes_reais = set(df['nmcliente'].unique())
        self.colaboradores_reais = set(df['nmcolaborador'].unique())
        self.min_faturamento = df['vlrfaturamento'].min()
        self.max_faturamento = df['vlrfaturamento'].max()
        self.media_faturamento = df['vlrfaturamento'].mean()
        
    def validar_resposta(self, resposta, tipo_assistente):
        """
        Valida uma resposta e retorna lista de alucinações detectadas.
        
        Args:
            resposta: Texto da resposta do assistente
            tipo_assistente: 'financeiro', 'operacional' ou 'estrategico'
            
        Returns:
            dict com {'valida': bool, 'alucinacoes': [], 'avisos': []}
        """
        resultado = {
            'valida': True,
            'alucinacoes': [],
            'avisos': []
        }
        
        # 1. Detecta menção a anos que não existem
        anos_mencionados = re.findall(r'\b(202[0-9])\b', resposta)
        for ano in set(anos_mencionados):
            if int(ano) not in self.anos_reais:
                resultado['alucinacoes'].append(
                    f"Menção a ano {ano} que não existe nos dados (anos disponíveis: {self.anos_reais})"
                )
                resultado['valida'] = False
        
        # 2. Detecta referência a clientes que não existem
        # Procura por padrões como "cliente X" ou "empresa Y"
        padroes_cliente_invalido = [
            r'cliente\s+([^,\.]+)',
            r'empresa\s+([^,\.]+)',
            r'(?:para|de)\s+([A-Z][A-Za-z\s]{3,})\s+(?:aumentou|recebemos|contratamos)',
        ]
        
        for padrao in padroes_cliente_invalido:
            matches = re.findall(padrao, resposta, re.IGNORECASE)
            for cliente_mencionado in matches:
                cliente_mencionado = cliente_mencionado.strip()
                if cliente_mencionado and cliente_mencionado.lower() not in [c.lower() for c in self.clientes_reais]:
                    # Verifica se é realmente um cliente (não é uma palavra comum)
                    if len(cliente_mencionado) > 3 and cliente_mencionado not in ['qual', 'este', 'seria']:
                        resultado['avisos'].append(
                            f"Cliente/Empresa '{cliente_mencionado}' não encontrado na planilha"
                        )
        
        # 3. Detecta padrões claros de alucinação (inventar dados históricos)
        padroes_alucinacao = [
            (r'em\s+2024\s+(?:tínhamos|foi|era)', 'referência a 2024 que não existe nos dados'),
            (r'(?:crescimento|aumento)\s+(?:nos\s+últimos\s+)?3\s+anos', 'menção a 3 anos quando só há 2'),
            (r'(?:historicamente|no\s+passado)\s+[^.]*(?:2020|2021|2022|2023)', 'referência a anos históricos não presentes'),
            (r'com\s+base\s+(?:na\s+)?experiência(?!\s+própria)', 'análise externa sem base em dados'),
        ]
        
        for padrao, descricao in padroes_alucinacao:
            if re.search(padrao, resposta, re.IGNORECASE):
                resultado['avisos'].append(f"AVISO: {descricao}")
        
        # 4. Verifica se a análise refencia dados que não vê
        if 'não há dados' in resposta.lower():
            # Se admite que não há dados, isso é BOAS - não está alucinando
            pass
        
        return resultado
    
    def gerar_feedback(self, resposta, tipo_assistente):
        """
        Gera feedback detalhado para melhorar o prompt.
        
        Returns:
            str com sugestões de melhoria
        """
        validacao = self.validar_resposta(resposta, tipo_assistente)
        
        if not validacao['alucinacoes'] and not validacao['avisos']:
            return None  # Resposta válida
        
        feedback = "DETECÇÃO DE ALUCINAÇÃO:\n\n"
        
        if validacao['alucinacoes']:
            feedback += "ERROS CRÍTICOS:\n"
            for alucinacao in validacao['alucinacoes']:
                feedback += f"- {alucinacao}\n"
        
        if validacao['avisos']:
            feedback += "\nAVISOS:\n"
            for aviso in validacao['avisos']:
                feedback += f"- {aviso}\n"
        
        # Adiciona informações corretas
        feedback += "\n\nINFORMAÇÕES REAIS PARA CORRIGIR:\n"
        feedback += f"- Anos disponíveis: {self.anos_reais}\n"
        feedback += f"- Meses disponíveis: {self.meses_reais}\n"
        feedback += f"- Clientes na planilha: {', '.join(sorted(self.clientes_reais))}\n"
        feedback += f"- Range de faturamento: R$ {self.min_faturamento:.2f} a R$ {self.max_faturamento:.2f}\n"
        feedback += f"- Média de faturamento: R$ {self.media_faturamento:.2f}\n"
        
        return feedback


class AtualizadorPrompt:
    """Atualiza prompts automaticamente com base em validação."""
    
    @staticmethod
    def adicionar_restricao_alucinacao(prompt_original, anos_reais, clientes_reais):
        """
        Adiciona seção de validação ao prompt.
        
        Args:
            prompt_original: Prompt original
            anos_reais: Lista de anos disponíveis
            clientes_reais: Set de clientes disponíveis
            
        Returns:
            Prompt melhorado
        """
        secao_validacao = f"""
---

## ⚠️ RESTRIÇÕES CRÍTICAS DE VALIDAÇÃO

Você DEVE seguir estas regras rigorosamente:

1. DADOS REAIS DISPONÍVEIS:
   - Anos: {anos_reais}
   - Clientes: {', '.join(sorted(clientes_reais))}
   - Você NUNCA deve mencionar outros anos ou clientes

2. PROIBIÇÕES ABSOLUTAS:
   - ❌ NÃO invente Years/Années/Anos que não estejam em {anos_reais}
   - ❌ NÃO mencione clientes que não estejam na lista acima
   - ❌ NÃO refira-se a 2024 ou outros anos não disponíveis
   - ❌ NÃO invente tendências históricas
   - ❌ NÃO estime baseado em "padrões do setor" - use APENAS data real

3. VALIDAÇÃO DE RESPOSTA:
   - Antes de enviar resposta, verifique CADA número mencionado contra os dados
   - Se não tiver certeza absoluta, diga explicitamente "não há dado suficiente"
   - Referenecie as fontes exatas dos dados

4. DETECÇÃO DE PRÓPRIOS ERROS:
   - Se você não conseguir validar uma afirmação contra os dados, DELETE ela
   - Se sua análise depender de informação que não existe, REESCREVA

"""
        return prompt_original + secao_validacao
    
    @staticmethod
    def salvar_prompt_atualizado(tipo, prompt_atualizado, pasta_prompts="prompts"):
        """Salva prompt atualizado."""
        caminho = Path(pasta_prompts) / f"assistente_{tipo}_v2.txt"
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(prompt_atualizado)
        print(f"[✓] Prompt atualizado salvo: {caminho}")
        return caminho


def criar_dados_validacao(df):
    """Cria um sumário dos dados reais para passar ao assistente."""
    
    resumo = f"""
## DADOS REAIS VERIFICADOS

### Período
- Anos: {sorted(df['ano'].unique())}
- Meses: {sorted(df['mês'].unique())}

### Clientes ({len(df['nmcliente'].unique())} identificados)
{', '.join(sorted(df['nmcliente'].unique()))}

### Colaboradores
- Total: {df['idcolaborador'].nunique()} colaboradores diferentes

### Faturamento
- Mínimo: R$ {df['vlrfaturamento'].min():,.2f}
- Máximo: R$ {df['vlrfaturamento'].max():,.2f}
- Média: R$ {df['vlrfaturamento'].mean():,.2f}
- Mediana: R$ {df['vlrfaturamento'].median():,.2f}

### Faturamento por Ano
{df.groupby('ano')['vlrfaturamento'].sum().to_string()}

### Faturamento por Mês (Todos os Anos)
{df.groupby('mês')['vlrfaturamento'].sum().to_string()}

### Clientes por Frequência
{df['nmcliente'].value_counts().head(10).to_string()}

"""
    return resumo
