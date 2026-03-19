import streamlit as st
import pandas as pd
import os
import plotly.express as px
from sklearn.linear_model import LinearRegression

st.set_page_config(layout="wide")

st.title("📊 Dashboard Executivo de Faturamento")

# =========================
# 📂 Carregar dados
# =========================
@st.cache_data
def load_data():
    files = os.listdir("data")
    dfs = []

    for file in files:
        if file.endswith(".xlsx"):
            df = pd.read_excel(f"data/{file}")
            df.columns = df.columns.str.lower()
            dfs.append(df)

    return pd.concat(dfs)

df = load_data()

# =========================
# 🎛️ FILTROS
# =========================
st.sidebar.header("🔎 Filtros")

anos = sorted(df["ano"].unique())
clientes = sorted(df["nmcliente"].unique())
meses = sorted(df["mês"].unique())

ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
cliente_sel = st.sidebar.multiselect("Cliente", clientes, default=clientes)
mes_sel = st.sidebar.multiselect("Mês", meses, default=meses)

df_filtro = df[
    (df["ano"].isin(ano_sel)) &
    (df["nmcliente"].isin(cliente_sel)) &
    (df["mês"].isin(mes_sel))
]

# =========================
# 📊 BASES
# =========================
df_group = df_filtro.groupby(["ano", "mês"])["vlrfaturamento"].sum().reset_index()

ranking = df_filtro.groupby("nmcliente")["vlrfaturamento"].sum().sort_values(ascending=False)

# =========================
# 💰 KPIs
# =========================
total = df_filtro["vlrfaturamento"].sum()

col1, col2, col3 = st.columns(3)

col1.metric("💰 Receita Total", f"R$ {total:,.0f}")
col2.metric("📈 Média Mensal", f"R$ {df_group['vlrfaturamento'].mean():,.0f}")
col3.metric("🏆 Top Cliente", ranking.index[0] if len(ranking) > 0 else "-")

# =========================
# 📈 Evolução mensal (Plotly)
# =========================
st.subheader("📈 Evolução de Faturamento")

fig = px.line(
    df_group,
    x="mês",
    y="vlrfaturamento",
    color="ano",
    markers=True
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# 🔁 COMPARAÇÃO YoY
# =========================
st.subheader("🔁 Comparação YoY")

pivot = df_group.pivot(index="mês", columns="ano", values="vlrfaturamento")

st.line_chart(pivot)

# =========================
# 🏆 Ranking clientes
# =========================
st.subheader("🏆 Ranking de Clientes")

fig_bar = px.bar(
    ranking.reset_index(),
    x="nmcliente",
    y="vlrfaturamento",
    text_auto=True
)

st.plotly_chart(fig_bar, use_container_width=True)

# =========================
# 🔍 DRILL-DOWN
# =========================
st.subheader("🔍 Detalhamento")

cliente_select = st.selectbox("Selecione um cliente", clientes)

df_cliente = df[df["nmcliente"] == cliente_select]

st.dataframe(df_cliente)

# =========================
# 🔮 FORECAST (Regressão)
# =========================
st.subheader("🔮 Previsão com Regressão")

df_prev = df_group.copy()
df_prev["t"] = range(len(df_prev))

X = df_prev[["t"]]
y = df_prev["vlrfaturamento"]

model = LinearRegression()
model.fit(X, y)

df_prev["forecast"] = model.predict(X)

fig_forecast = px.line(df_prev, y=["vlrfaturamento", "forecast"])

st.plotly_chart(fig_forecast, use_container_width=True)

# =========================
# 🔮 FUTURO
# =========================
future = pd.DataFrame({"t": range(len(df_prev), len(df_prev) + 6)})
future["forecast"] = model.predict(future)

st.write("📊 Próximos meses previstos:")
st.dataframe(future)

# =========================
# 🧠 Insights IA
# =========================
st.subheader("🧠 Insights Estratégicos")

if os.path.exists("outputs/dashboard.md"):
    with open("outputs/dashboard.md", "r", encoding="utf-8") as f:
        st.markdown(f.read())