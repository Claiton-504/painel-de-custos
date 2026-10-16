# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Painel Avançado do Gestor)
==============================================================
Rodar no terminal:
    streamlit run dashboard_custos.py
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import io

st.set_page_config(
    page_title="Custos 2026 | Painel Avançado do Gestor",
    page_icon="📊",
    layout="wide",
)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_BASE = BASE / "base_calculada.csv"


@st.cache_data
def carregar_dados():
    if not CSV_LONG.exists():
        return None, None
    df = pd.read_csv(CSV_LONG)
    df["Centro"] = df["Centro_Codigo"].astype(str) + " - " + df["Centro_Nome"].astype(str)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    base = None
    if CSV_BASE.exists():
        base = pd.read_csv(CSV_BASE)
        if "Centro" not in base.columns and "Centro_Codigo" in base.columns:
            base["Centro"] = base["Centro_Codigo"].astype(str) + " - " + base["Centro_Nome"].astype(str)
    return df, base


df, base = carregar_dados()

st.title("CUSTOS 2026  |  PAINEL AVANÇADO DO GESTOR")
st.caption("Controlo interativo de orçamento, desvios e evolução mensal")

if df is None:
    st.error(
        "Arquivo **dados_longos.csv** não encontrado na pasta do script.\n\n"
        "Rode antes o `atualizar_painel_VSCODE.py` com os 9 relatórios."
    )
    st.stop()

# ═════════════════════════════════════════════════════════════════════
# BARRA LATERAL (FILTROS AVANÇADOS)
# ═════════════════════════════════════════════════════════════════════
st.sidebar.header("Filtros do Painel")

lista_centros = sorted(df["Centro"].unique().tolist())
# Permitir seleção múltipla de centros de custo
centros_sel = st.sidebar.multiselect(
    "Centros de Custo",
    options=lista_centros,
    default=lista_centros  # Começa com todos selecionados
)

meses_disponiveis = sorted(
    [m for m in df["Mes"].astype(str).unique().tolist() if m != "Total" and str(m).isdigit()],
    key=lambda x: int(x),
)
mes_sel = st.sidebar.selectbox("Mês de Referência", ["Todos os meses"] + meses_disponiveis)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Legenda de Status**\n\n"
    "- 🟢 **OK** — dentro do previsto\n"
    "- 🟡 **Atenção** — ≥ 80% consumido\n"
    "- 🔴 **Crítico** — estourou / saldo negativo"
)

# ═════════════════════════════════════════════════════════════════════
# FILTRAGEM DOS DADOS
# ═════════════════════════════════════════════════════════════════════
d = df.copy()
if centros_sel:
    d = d[d["Centro"].isin(centros_sel)]
else:
    # Se desmarcar tudo, considera todos para não quebrar o painel
    centros_sel = lista_centros

# Cálculo Anual / Consolidado Oficial (Linhas de Total)
d_prev_total = d[(d["Tipo"] == "Prev.") & (d["Mes"] == "Total") & (d["Conta_Codigo"] == "Total")]
d_real_total = d[(d["Tipo"] == "Real.") & (d["Mes"] == "Total") & (d["Conta_Codigo"] == "Total")]

orc_anual = float(d_prev_total["Valor_Abs"].sum())
real_anual = float(d_real_total["Valor_Abs"].sum())
saldo_anual = orc_anual - real_anual
pct_anual = (real_anual / orc_anual) if orc_anual > 0 else 0.0

# Cálculo Mensal
if mes_sel != "Todos os meses":
    d_prev_mes = d[(d["Tipo"] == "Prev.") & (d["Mes"].astype(str) == mes_sel) & (d["Conta_Codigo"] == "Total")]
    d_real_mes = d[(d["Tipo"] == "Real.") & (d["Mes"].astype(str) == mes_sel) & (d["Conta_Codigo"] == "Total")]
    orc_mes = float(d_prev_mes["Valor_Abs"].sum())
    real_mes = float(d_real_mes["Valor_Abs"].sum())
    saldo_mes = orc_mes - real_mes
    pct_mes = (real_mes / orc_mes) if orc_mes > 0 else 0.0
else:
    orc_mes = real_mes = saldo_mes = pct_mes = None

# ═════════════════════════════════════════════════════════════════════
# KPIs PRINCIPAIS
# ═════════════════════════════════════════════════════════════════════
st.subheader("Indicadores Principais")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Orçamento Consolidado", f"R$ {orc_anual:,.2f}")
c2.metric("Realizado Acumulado", f"R$ {real_anual:,.2f}")
c3.metric("Saldo Atual", f"R$ {saldo_anual:,.2f}", delta_color="inverse")
c4.metric("Orçamento Consumido", f"{pct_anual:.1%}")

if mes_sel != "Todos os meses":
    st.markdown(f"**Detalhe do Mês: {mes_sel}**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Orçado no Mês", f"R$ {orc_mes:,.2f}")
    m2.metric("Realizado no Mês", f"R$ {real_mes:,.2f}")
    m3.metric("Saldo do Mês", f"R$ {saldo_mes:,.2f}")
    m4.metric("% Gasto no Mês", f"{pct_mes:.1%}")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════
# GRÁFICOS: PIZZA DE CONSUMO + EVOLUÇÃO MENSAL (LINHA DO TEMPO)
# ═════════════════════════════════════════════════════════════════════
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("📊 Consumo do Orçamento")
    if mes_sel == "Todos os meses":
        gasto, disponivel, estouro = real_anual, max(0.0, saldo_anual), max(0.0, -saldo_anual)
        titulo_pizza = "Anual Consolidado"
    else:
        gasto, disponivel, estouro = real_mes, max(0.0, saldo_mes), max(0.0, -saldo_mes)
        titulo_pizza = f"Mês {mes_sel}"
        
    pie_df = pd.DataFrame(
        {"Fatia": ["Realizado (gasto)", "Disponível (saldo)", "Estouro"], "Valor": [gasto, disponivel, estouro]}
    )
    pie_df = pie_df[pie_df["Valor"] > 0]
    if not pie_df.empty:
        fig_pie = px.pie(
            pie_df, names="Fatia", values="Valor", title=f"Distribuição — {titulo_pizza}",
            color="Fatia",
            color_discrete_map={"Realizado (gasto)": "#2874A6", "Disponível (saldo)": "#1E8449", "Estouro": "#922B21"}
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.write("Sem valores para exibir no gráfico.")

with col_g2:
    st.subheader("📈 Evolução Mensal (Orçado vs Realizado)")
    # Agrupar dados mensais das contas para a linha do tempo
    df_evolucao = d[(d["Conta_Codigo"] != "Total") & (d["Mes"] != "Total") & (d["Mes"].isin(meses_disponiveis))]
    if not df_evolucao.empty:
        evol_piv = df_evolucao.pivot_table(index="Mes", columns="Tipo", values="Valor_Abs", aggfunc="sum").reset_index()
        if "Prev." in evol_piv.columns and "Real." in evol_piv.columns:
            evol_piv = evol_piv.rename(columns={"Prev.": "Orçado", "Real.": "Realizado"})
            fig_line = px.line(
                evol_piv, x="Mes", y=["Orçado", "Realizado"], markers=True,
                title="Evolução de Custos ao Longo do Ano",
                labels={"value": "Valor (R$)", "Mes": "Mês", "variable": "Tipo"}
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.write("Dados insuficientes para a linha do tempo.")
    else:
        st.write("Sem dados mensais para exibir.")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════
# TOP 5 CONTAS COM MAIORES DESVIOS / ESTOUROS
# ═════════════════════════════════════════════════════════════════════
st.subheader("🚨 Top Contas com Maiores Gastos / Desvios")

contas_analise = d[d["Conta_Codigo"] != "Total"].copy()
if mes_sel == "Todos os meses":
    p_an = contas_analise[(contas_analise["Tipo"] == "Prev.") & (contas_analise["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    r_an = contas_analise[(contas_analise["Tipo"] == "Real.") & (contas_analise["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})
else:
    p_an = contas_analise[(contas_analise["Tipo"] == "Prev.") & (contas_analise["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    r_an = contas_analise[(contas_analise["Tipo"] == "Real.") & (contas_analise["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})

top_df = p_an.merge(r_an, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
top_df["Saldo"] = top_df["Orcado"] - top_df["Realizado"]
top_df["% Consumido"] = top_df.apply(lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else 1.0, axis=1)
top_df["Conta"] = top_df["Conta_Codigo"].astype(str) + " | " + top_df["Conta_Descricao"].astype(str)
top_df = top_df.sort_values("Realizado", ascending=False).head(5)

st.dataframe(
    top_df[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido"]].style.format(
        {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
    ),
    use_container_width=True
)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════
# TABELA DETALHADA DE CONTAS + BOTÃO DE DOWNLOAD
# ═════════════════════════════════════════════════════════════════════
st.subheader("📋 Tabela Detalhada de Contas")

tab = top_df.copy() # Reaproveita o agrupamento ou recalcula completo para todas as contas
if mes_sel == "Todos os meses":
    prev = contas_analise[(contas_analise["Tipo"] == "Prev.") & (contas_analise["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas_analise[(contas_analise["Tipo"] == "Real.") & (contas_analise["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})
else:
    prev = contas_analise[(contas_analise["Tipo"] == "Prev.") & (contas_analise["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas_analise[(contas_analise["Tipo"] == "Real.") & (contas_analise["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})

tab_completa = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
tab_completa["Saldo"] = tab_completa["Orcado"] - tab_completa["Realizado"]
tab_completa["% Consumido"] = tab_completa.apply(
    lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0),
    axis=1,
)

def status_row(r):
    if r["Saldo"] < 0 or (r["Orcado"] == 0 and r["Realizado"] > 0) or r["% Consumido"] >= 1:
        return "Crítico"
    if r["% Consumido"] >= 0.8:
        return "Atenção"
    return "OK"

tab_completa["Status"] = tab_completa.apply(status_row, axis=1)
tab_completa["Conta"] = tab_completa["Conta_Codigo"].astype(str) + " | " + tab_completa["Conta_Descricao"].astype(str)
tab_completa = tab_completa.sort_values("Realizado", ascending=False)
tab_show = tab_completa[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]]

def colorir(row):
    if row["Status"] == "Crítico":
        return ["background-color: #EF9A9A"] * len(row)
    if row["Status"] == "Atenção":
        return ["background-color: #FFE082"] * len(row)
    return ["background-color: #C8E6C9"] * len(row)

st.dataframe(
    tab_show.style.apply(colorir, axis=1).format(
        {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
    ),
    use_container_width=True,
    height=400,
)

# Botão de Download em Excel dos dados filtrados
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    tab_show.to_excel(writer, index=False, sheet_name="Relatorio_Filtrado")
buffer.seek(0)

st.download_button(
    label="📥 Descarregar dados filtrados em Excel",
    data=buffer,
    file_name=f"Relatorio_Custos_Filtrado_{datetime.now().strftime('%Y%m%d')}.xlsx" if 'datetime' in globals() else "Relatorio_Custos_Filtrado.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")
st.caption("Painel desenvolvido em Python (Streamlit) — Atualizado automaticamente via script de relatórios.")