"""
Sistema de validação e autocorreção de respostas dos assistentes.
Detecta alucinações e atualiza prompts automaticamente.
"""

import re
import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


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

    anos = sorted(df["ano"].unique())
    meses = sorted(df["mês"].unique())
    clientes_unicos = sorted(df["nmcliente"].unique())
    colaboradores_unicos = sorted(df["nmcolaborador"].unique())

    top_clientes_por_faturamento = (
        df.groupby("nmcliente")["vlrfaturamento"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .to_string()
    )

    top_colaboradores_por_faturamento = (
        df.groupby("nmcolaborador")["vlrfaturamento"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .to_string()
    )

    top_colaboradores_por_registros = (
        df.groupby("nmcolaborador")
        .size()
        .sort_values(ascending=False)
        .head(15)
        .to_string()
    )

    faturamento_por_ano = df.groupby("ano")["vlrfaturamento"].sum().sort_index().to_string()

    # Tabela mês x ano (soma), usada para comparação 2025 vs 2026.
    faturamento_por_mes_ano = (
        df.pivot_table(
            index="mês",
            columns="ano",
            values="vlrfaturamento",
            aggfunc="sum",
        )
        .sort_index()
    )
    faturamento_por_mes_ano = faturamento_por_mes_ano.fillna(pd.NA)

    registros_por_mes_ano = (
        df.groupby(["ano", "mês"])
        .size()
        .sort_index()
        .to_string()
    )

    colaboradores_ativos_por_mes_ano = (
        df.groupby(["ano", "mês"])["nmcolaborador"]
        .nunique()
        .sort_index()
        .to_string()
    )

    resumo = f"""
## DADOS REAIS VERIFICADOS

### Período
- Anos: {anos}
- Meses: {meses}

### Clientes ({len(clientes_unicos)} identificados)
{', '.join(clientes_unicos)}

### Colaboradores ({len(colaboradores_unicos)} identificados)
{', '.join(colaboradores_unicos)}

### Volume de registros
- Total de registros: {len(df)}
- Registros por Ano e Mês (contagem):
{registros_por_mes_ano}

### Colaboradores ativos por Ano e Mês (contagem distinta)
{colaboradores_ativos_por_mes_ano}

### Faturamento (vlrfaturamento)
- Mínimo: R$ {df['vlrfaturamento'].min():,.2f}
- Máximo: R$ {df['vlrfaturamento'].max():,.2f}
- Soma total: R$ {df['vlrfaturamento'].sum():,.2f}
- Média: R$ {df['vlrfaturamento'].mean():,.2f}
- Mediana: R$ {df['vlrfaturamento'].median():,.2f}

### Faturamento por Ano (soma)
{faturamento_por_ano}

### Faturamento por Mês e Ano (soma)
{faturamento_por_mes_ano.to_string()}

### Top clientes por faturamento (até 15)
{top_clientes_por_faturamento}

### Top colaboradores por faturamento (até 15)
{top_colaboradores_por_faturamento}

### Top colaboradores por quantidade de registros (até 15)
{top_colaboradores_por_registros}

"""
    return resumo


def extrair_json_do_texto(texto: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Tenta extrair JSON válido de uma resposta do LLM.
    - Aceita JSON "puro" ou JSON dentro de codefence (```json ... ```).
    - Se não conseguir, retorna (None, erro).
    """
    if not texto or not isinstance(texto, str):
        return None, "texto vazio ou inválido"

    raw = texto.strip()

    # Remove code fences comuns.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n", "", raw)
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    # Tentativa 1: parse direto.
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload, None
        return None, "JSON carregado mas não é um objeto (dict)"
    except Exception:
        pass

    # Tentativa 2: tenta extrair o(s) objeto(s) JSON mais plausível(is) perto do final.
    end = raw.rfind("}")
    if end == -1:
        return None, "não foi possível localizar delimitadores de JSON"

    # Recuar o "start" até achar um JSON parseável.
    scan_end = end
    while scan_end > 0:
        start = raw.rfind("{", 0, scan_end + 1)
        if start == -1:
            break

        candidato = raw[start : end + 1]
        try:
            payload = json.loads(candidato)
            if isinstance(payload, dict):
                return payload, None
            return None, "JSON extraído mas não é um objeto (dict)"
        except Exception:
            # Se falhar, desloca o end para antes do '{' encontrado,
            # forçando a tentar outro candidato mais "interno".
            end = start - 1
            scan_end = end

    return None, "não foi possível localizar/parsear um objeto JSON válido"


def normalizar_payload_area(payload: Any, tipo_assistente: str) -> Dict[str, Any]:
    """
    Garante um formato mínimo (schema) para `outputs/insights.json`,
    mesmo se o LLM retornar algo incompleto ou falhar no parse do JSON.
    """
    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    schema_version = schema_version or "1.1"

    texto_markdown = ""
    resumo_executivo = ""
    kpis = []
    insights = []
    pontos_de_atencao = []

    checagem_payload = {}

    if isinstance(payload, dict):
        texto_markdown = payload.get("texto_markdown") or payload.get("texto") or ""
        resumo_executivo = payload.get("resumo_executivo") or ""
        kpis = payload.get("kpis", []) if isinstance(payload.get("kpis"), list) else []
        insights = payload.get("insights", []) if isinstance(payload.get("insights"), list) else []
        pontos_de_atencao = (
            payload.get("pontos_de_atencao", [])
            if isinstance(payload.get("pontos_de_atencao"), list)
            else []
        )
        checagem_payload = payload.get("checagem", {}) if isinstance(payload.get("checagem"), dict) else {}

    checagem = {
        "anos_e_periodos_usados_estao_nos_dados": bool(
            checagem_payload.get("anos_e_periodos_usados_estao_nos_dados", False)
        ),
        "numeros_citados_sao_verificaveis_nos_agregados": bool(
            checagem_payload.get("numeros_citados_sao_verificaveis_nos_agregados", False)
        ),
    }

    return {
        "schema_version": schema_version,
        "area": tipo_assistente,
        "resumo_executivo": resumo_executivo,
        "texto_markdown": texto_markdown,
        "kpis": kpis,
        "insights": insights,
        "pontos_de_atencao": pontos_de_atencao,
        "checagem": checagem,
    }
