"""
Sistema de Retraining Automático - Aprende com seus próprios erros
Coleta avisos, analisa padrões e melhora prompts iterativamente
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re


class GerenciadorAvisos:
    """Registra, analisa e aprende com avisos de validação."""
    
    def __init__(self, arquivo_log="outputs/avisos_log.json"):
        self.arquivo_log = arquivo_log
        self.avisos_registrados = self._carregar_avisos()
    
    def _carregar_avisos(self):
        """Carrega histórico de avisos."""
        if os.path.exists(self.arquivo_log):
            try:
                with open(self.arquivo_log, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    # Compatibilidade: versões antigas eram lista direta.
                    if isinstance(dados, list):
                        return dados
                    if isinstance(dados, dict) and isinstance(dados.get("items"), list):
                        return dados.get("items", [])
                    return []
            except:
                return []
        return []
    
    def registrar_validacao(self, tipo_assistente, avisos, erros, resposta_original):
        """
        Registra resultado de uma validação.
        
        Args:
            tipo_assistente: 'financeiro', 'operacional' ou 'estrategico'
            avisos: lista de avisos detectados
            erros: lista de erros críticos
            resposta_original: texto da resposta do LLM
        """
        registro = {
            "timestamp": datetime.now().isoformat(),
            "assistente": tipo_assistente,
            "quantidade_avisos": len(avisos),
            "quantidade_erros": len(erros),
            "avisos": avisos,
            "erros": erros,
            "tamanho_resposta": len(resposta_original),
            "primeiras_100_chars": resposta_original[:100]
        }
        
        self.avisos_registrados.append(registro)
        self._salvar_avisos()
        
        return registro
    
    def _salvar_avisos(self):
        """Salva histórico de avisos."""
        os.makedirs(os.path.dirname(self.arquivo_log), exist_ok=True)
        with open(self.arquivo_log, 'w', encoding='utf-8') as f:
            payload = {
                "schema_version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "items": self.avisos_registrados,
            }
            json.dump(payload, f, ensure_ascii=False, indent=2)
    
    def analisar_padroes(self):
        """Analisa padrões nos avisos para identificar problemas recorrentes."""
        
        padroes = {
            "por_assistente": defaultdict(lambda: {"total": 0, "avisos": []}),
            "tipos_aviso": defaultdict(int),
            "falsos_positivos": [],
            "padroes_alucinacao": []
        }
        
        if not self.avisos_registrados:
            return padroes
        
        for registro in self.avisos_registrados:
            assistente = registro['assistente']
            padroes['por_assistente'][assistente]['total'] += 1
            
            for aviso in registro['avisos']:
                # Categoriza o tipo de aviso
                if 'Cliente/Empresa' in aviso and 'não encontrado' in aviso:
                    tipo = "cliente_invalido_falso_positivo"
                    padroes['falsos_positivos'].append(aviso)
                elif 'referência a' in aviso:
                    tipo = "referencia_invalida"
                elif '2024' in aviso or '2027' in aviso:
                    tipo = "ano_invalido"
                else:
                    tipo = "outro"
                
                padroes['tipos_aviso'][tipo] += 1
                padroes['por_assistente'][assistente]['avisos'].append({
                    'tipo': tipo,
                    'aviso': aviso
                })
        
        return padroes
    
    def gerar_relatorio(self):
        """Gera relatório executivo dos avisos."""
        padroes = self.analisar_padroes()
        
        relatorio = "# RELATÓRIO DE AVISOS E PADRÕES\n\n"
        relatorio += f"Data: {datetime.now().isoformat()}\n"
        relatorio += f"Total de execuções analisadas: {len(self.avisos_registrados)}\n\n"
        
        # Avisos por assistente
        relatorio += "## Avisos por Assistente\n"
        for assistente, dados in padroes['por_assistente'].items():
            media_avisos = sum(a['quantidade_avisos'] for a in self.avisos_registrados 
                              if a['assistente'] == assistente) / max(dados['total'], 1)
            relatorio += f"\n### {assistente.upper()}\n"
            relatorio += f"- Execuções: {dados['total']}\n"
            relatorio += f"- Média de avisos por execução: {media_avisos:.1f}\n"
        
        # Tipos de aviso mais comuns
        relatorio += "\n## Tipos de Aviso Mais Comuns\n"
        sorted_tipos = sorted(padroes['tipos_aviso'].items(), key=lambda x: x[1], reverse=True)
        for tipo, count in sorted_tipos:
            relatorio += f"- {tipo}: {count} ocorrências\n"
        
        # Falsos positivos
        if padroes['falsos_positivos']:
            relatorio += f"\n## Falsos Positivos Detectados ({len(padroes['falsos_positivos'])})\n"
            for aviso in padroes['falsos_positivos'][:5]:  # Top 5
                relatorio += f"- {aviso}\n"
        
        return relatorio


class AnalisadorErros:
    """Analisa erros específicos e sugere melhorias nos prompts."""
    
    PADROES_FALSO_POSITIVO = [
        # Padrão: "Cliente X fez algo" -> "Cliente" não é o nome, é referência
        (r'Cliente/Empresa \'([^\']+)\' não encontrado.*(?:fez|teve|contribuiu)', 
         'Falso positivo: menção de cliente em análise descritiva, não nome real'),
        
        # Padrão: "LIVELO contribuiu mais" -> "contribuiu mais" é predicado, não cliente
        (r'Cliente/Empresa \'.*(?:contribuiu|cresceu|diminuiu|variou).*\' não encontrado',
         'Falso positivo: verbo conjugado confundido com nome de cliente'),
        
        # Padrão: "O LIVELO é..." -> artigo + nome está ok
        (r'Cliente/Empresa \'(?:é|foi|foi|está|tem|possui|tem|apresenta).*não encontrado',
         'Falso positivo: após verbo de ligação ou tempo')
    ]
    
    @staticmethod
    def filtrar_falsos_positivos(avisos):
        """Remove falsos positivos da lista de avisos."""
        avisos_reais = []
        
        for aviso in avisos:
            eh_falso_positivo = False
            
            for padrao, _ in AnalisadorErros.PADROES_FALSO_POSITIVO:
                if re.search(padrao, aviso, re.IGNORECASE):
                    eh_falso_positivo = True
                    break
            
            if not eh_falso_positivo:
                avisos_reais.append(aviso)
        
        return avisos_reais
    
    @staticmethod
    def sugerir_melhorias(padroes_avisos):
        """Sugere melhorias nos prompts baseado em padrões."""
        sugestoes = []
        
        # Se muitos avisos de "cliente inválido", o problema é na detecção
        if padroes_avisos.get('cliente_invalido_falso_positivo', 0) > 3:
            sugestoes.append(
                "Melhoria 1: O regex de detecção de cliente está muito agressivo. "
                "Deve validar apenas NOMES de clientes, não menções em contexto."
            )
        
        # Se muitos avisos de "referência inválida"
        if padroes_avisos.get('referencia_invalida', 0) > 2:
            sugestoes.append(
                "Melhoria 2: O prompt deve ser mais específico sobre que tipo de "
                "referência é válida. Adicione exemplos de referências VÁLIDAS."
            )
        
        # Se há mix de avisos, talvez falte instrução no prompt
        if sum(padroes_avisos.values()) > 5:
            sugestoes.append(
                "Melhoria 3: Adicione seção 'EXEMPLOS DE ANÁLISE VÁLIDA' no prompt "
                "mostrando como analisar os dados sem inventar."
            )
        
        return sugestoes


class MelhoradorPrompt:
    """Melhora prompts automaticamente com base em análise de erros."""
    
    @staticmethod
    def adicionar_secao_exemplos(tipo_assistente, prompt_original):
        """Adiciona seção de exemplos válidos ao prompt."""
        
        exemplos_por_tipo = {
            'financeiro': """
### EXEMPLOS DE ANÁLISE VÁLIDA ✓
**Errado (inventado)**: "Cliente X cresceu 340% no setor"
**Correto**: "LIVELO teve faturamento de R$ X em 2025 e R$ Y em 2026, variação de Z%"

**Errado**: "Estimamos que a receita será R$ 2 bilhões em 2027"
**Correto**: "Com base no padrão mensal observado, projeção conservadora: R$ Z"

**Errado**: "Em 2024, o faturamento era..."
**Correto**: "Não há dados de 2024. Analisando 2025 vs 2026..."
""",
            
            'operacional': """
### EXEMPLOS DE ANÁLISE VÁLIDA ✓
**Errado (especulação)**: "A equipe está sobrecarregada"
**Correto**: "Com 137 colaboradores gerando R$ X, carga média por pessoa: R$ Y"

**Errado**: "Precisamos contratar 50 pessoas"
**Correto**: "Número de colaboradores em 2025: 137. Em 2026: 142. Variação: +3.6%"

**Errado**: "O departamento de TI está no limite"
**Correto**: "Não há dados de departaments nos arquivos fornecidos"
""",
            
            'estrategico': """
### EXEMPLOS DE ANÁLISE VÁLIDA ✓
**Errado (invenção)**: "Devemos explorar mercados emergentes em SE Ásia"
**Correto**: "Clientes atuais: LIVELO, VELOE, ALELO. Concentração: X%"

**Errado**: "Analistas do setor preveem crescimento de 25%"
**Correto**: "Comparando dados reais: 2025 vs 2026 mostra tendência de -55.19%"

**Errado**: "Histórico de 5 anos mostra..."
**Correto**: "Dados disponíveis: 2025-2026 (2 anos). Comparação YoY..."
"""
        }
        
        exemplo = exemplos_por_tipo.get(tipo_assistente, "")
        
        if exemplo and "EXEMPLOS DE ANÁLISE VÁLIDA" not in prompt_original:
            # Insere antes da seção de AUTO-VALIDAÇÃO
            return prompt_original.replace(
                "## ⚠️ AUTO-VALIDAÇÃO",
                exemplo + "\n## ⚠️ AUTO-VALIDAÇÃO"
            )
        
        return prompt_original
    
    @staticmethod
    def adicionar_restricoes_especificas(tipo_assistente, prompt_original):
        """Adiciona restrições baseadas em erros específicos detectados."""
        
        restricoes = {
            'financeiro': """
### RESTRIÇÕES ESPECÍFICAS PARA ESTE ASSISTENTE
- Não mencione anos antes de 2025 ou depois de 2026
- Não refira-se a "setores" ou "benchmarks" - use APENAS dados da planilha
- Se fizer análise, cite o cliente específico: "LIVELO faturou R$ X"
- Não estime "potencial de mercado" - isso é invenção
- Sempre termine com: "Esta análise é baseada exclusivamente em [ano] até [ano]"
""",
            
            'operacional': """
### RESTRIÇÕES ESPECÍFICAS PARA ESTE ASSISTENTE
- Não invente departamentos (não há dados de estrutura)
- Não cite "melhorias de processo" que não vê nos dados
- Menção a colaborador? Cite sempre o número real observado
- Não use termos como "provavelmente", "pode ser" - seja assertivo com dados
- Se não há informação (ex: dados de demissões), diga explicitamente
""",
            
            'estrategico': """
### RESTRIÇÕES ESPECÍFICAS PARA ESTE ASSISTENTE
- Tendências devem ser MENSURÁVEIS nos dados (não "intuitivas")
- SWOT deve vir de dados reais observáveis, não de "expertise do setor"
- Não mencione "riscos geopolíticos" ou externos não vistos nos dados
- Recomendações devem ser baseadas em padrão observado (ex: "Alta concentração em LIVELO")
- Se fizer projeção, seja claro: "baseado em média de crescimento observado"
"""
        }
        
        restricao = restricoes.get(tipo_assistente, "")
        
        if restricao and "RESTRIÇÕES ESPECÍFICAS" not in prompt_original:
            return prompt_original.replace(
                "## ⚠️ RESTRIÇÕES CRÍTICAS",
                "## ⚠️ RESTRIÇÕES CRÍTICAS\n" + restricao
            )
        
        return prompt_original


class SistemaRetraining:
    """Sistema completo de retraining automático."""
    
    def __init__(self):
        self.gerenciador = GerenciadorAvisos()
        self.analisador = AnalisadorErros()
        self.melhorador = MelhoradorPrompt()
    
    def processar_resultado(self, tipo_assistente, avisos, erros, resposta):
        """Processa resultado e armazena para aprendizado."""
        # Filtra falsos positivos
        avisos_reais = self.analisador.filtrar_falsos_positivos(avisos)
        
        # Registra
        self.gerenciador.registrar_validacao(
            tipo_assistente, 
            avisos_reais,  # Apenas avisos reais
            erros, 
            resposta
        )
        
        # Retorna avisos após filtro
        return avisos_reais
    
    def gerar_relatorio_completo(self):
        """Gera relatório completo com análise e sugestões."""
        relatorio = self.gerenciador.gerar_relatorio()
        padroes = self.gerenciador.analisar_padroes()
        
        # Extrai tipos de aviso
        tipos_aviso = defaultdict(int)
        for registro in self.gerenciador.avisos_registrados:
            for aviso in registro.get('avisos', []):
                if 'Cliente/Empresa' in aviso:
                    tipos_aviso['cliente_invalido_falso_positivo'] += 1
                elif 'referência' in aviso:
                    tipos_aviso['referencia_invalida'] += 1
                else:
                    tipos_aviso['outro'] += 1
        
        # Sugestões
        sugestoes = AnalisadorErros.sugerir_melhorias(tipos_aviso)
        if sugestoes:
            relatorio += "\n\n## SUGESTÕES DE MELHORIA\n"
            for sug in sugestoes:
                relatorio += f"- {sug}\n"
        
        return relatorio
    
    def melhorar_prompt(self, tipo_assistente, prompt_original):
        """Melhora um prompt baseado em histórico de erros."""
        prompt = prompt_original
        
        # Adiciona exemplos
        prompt = self.melhorador.adicionar_secao_exemplos(tipo_assistente, prompt)
        
        # Adiciona restrições específicas
        prompt = self.melhorador.adicionar_restricoes_especificas(tipo_assistente, prompt)
        
        return prompt
