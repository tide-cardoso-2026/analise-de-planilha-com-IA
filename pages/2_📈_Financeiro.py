import streamlit as st
import pandas as pd
import os

st.title("📈 Análise Financeira")

# carregar dados
files = os.listdir("data")
dfs = []

for file in files:
    if file.endswith(".xlsx"):
        df = pd.read_excel(f"data/{file}")
        df.columns = df.columns.str.lower()
        dfs.append(df)

df = pd.concat(dfs)

# KPI
total = df["vlrfaturamento"].sum()
st.metric("💰 Faturamento Total", f"R$ {total:,.0f}")

# gráfico
df_group = df.groupby(["ano", "mês"])["vlrfaturamento"].sum().reset_index()
st.line_chart(df_group["vlrfaturamento"])