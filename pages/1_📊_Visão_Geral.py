import streamlit as st
import json
import os

st.markdown("""
<style>
/* reduzir tamanho geral */
html, body, [class*="css"]  {
    font-size: 14px;
}

/* títulos menores */
h1 { font-size: 26px !important; }
h2 { font-size: 20px !important; }
h3 { font-size: 16px !important; }

/* reduzir espaçamento */
.block-container {
    padding-top: 2rem;
    padding-bottom: 1rem;
}

/* cards mais clean */
.card {
    padding: 15px;
    border-radius: 10px;
    background-color: #f7f7f7;
    margin-bottom: 10px;
}

/* texto mais leve */
p {
    font-size: 13px;
    color: #444;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Visão Geral Executiva")

# =========================
# 📂 Carregar dados
# =========================
insights_path = "outputs/insights.json"
dashboard_path = "outputs/dashboard.md"

if not os.path.exists(insights_path):
    st.warning("⚠️ Insights não encontrados. Rode o pipeline primeiro.")
    st.stop()

with open(insights_path, "r", encoding="utf-8") as f:
    insights = json.load(f)

# =========================
# 🤖 Assistentes
# =========================
st.header("🤖 Insights dos Assistentes")

col1, col2, col3 = st.columns(3)

def _payload_to_text(payload):
    if isinstance(payload, dict):
        return (
            payload.get("resumo_executivo")
            or payload.get("texto_markdown")
            or ""
        )
    return payload or ""

col1.subheader("💰 Financeiro")
col1.write(_payload_to_text(insights.get("financeiro", "Sem dados")))

col2.subheader("⚙️ Operacional")
col2.write(_payload_to_text(insights.get("operacional", "Sem dados")))

col3.subheader("🧭 Estratégico")
col3.write(_payload_to_text(insights.get("estrategico", "Sem dados")))

# =========================
# 🧠 Gerente
# =========================
st.header("🧠 Decisão do Gerente")

if os.path.exists(dashboard_path):
    with open(dashboard_path, "r", encoding="utf-8") as f:
        markdown = f.read()
        st.markdown(markdown)
else:
    st.warning("⚠️ Dashboard do gerente não encontrado.")

# =========================
# 🧪 Avaliação dos Assistentes
# =========================

st.header("🧪 Avaliação dos Assistentes")

def score_card(nome, texto):
    if isinstance(texto, dict):
        texto = texto.get("texto_markdown") or texto.get("resumo_executivo") or ""
    tamanho = len(texto)

    if tamanho < 150:
        cor = "#ff4d4f"
        status = "Fraco"
    elif tamanho < 400:
        cor = "#faad14"
        status = "Médio"
    else:
        cor = "#52c41a"
        status = "Bom"

    st.markdown(f"""
    <div style="padding:10px;border-left:5px solid {cor};background:#fafafa;margin-bottom:8px;">
        <strong>{nome}</strong> → {status}
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    score_card("Financeiro", insights.get("financeiro", ""))

with col2:
    score_card("Operacional", insights.get("operacional", ""))

with col3:
    score_card("Estratégico", insights.get("estrategico", ""))


# =========================
# 🧠 Feedback Executivo (simulado)
# =========================
st.header("🧠 Feedback Executivo do Gerente")

feedback = []

if insights.get("financeiro"):
    feedback.append("💰 Financeiro: boa base analítica, mas pode aprofundar tendências e sazonalidade.")

if insights.get("operacional"):
    feedback.append("⚙️ Operacional: insights úteis, porém faltam impactos diretos na operação.")

if insights.get("estrategico"):
    feedback.append("🧭 Estratégico: visão relevante, pode melhorar priorização de decisões.")

for f in feedback:
    st.write(f)

# =========================
# 🧭 Conclusão executiva
# =========================
st.header("📌 Conclusão Executiva")

st.info("""
O modelo multi-agentes está funcionando corretamente, porém há oportunidade de evolução:

- Melhor profundidade analítica
- Maior conexão com impacto real no negócio
- Padronização dos insights

Recomendação: evoluir prompts e enriquecer dados para maior precisão.
""")