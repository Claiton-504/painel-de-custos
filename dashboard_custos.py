# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Painel Executivo de BI)
===========================================================
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import io

st.set_page_config(
    page_title="Custos 2026 | Painel do Gestor",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    </style>
""", unsafe_allow_html=True)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_BASE = BASE / "base_calculada.csv"
CSV_DETALHES = BASE / "detalhes_longos.csv"

@st.cache_data
def carregar_dados():
    try:
        if not CSV_LONG.exists():
            return None, None, None
            
        df = pd.read_csv(CSV_LONG)
        df["Centro"] = df["Centro_Codigo"].astype(str) + " - " + df["Centro_Nome"].astype(str)
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        df["Valor_Abs"] = df["Valor"].abs()
        
        base = None
        if CSV_BASE.exists():
            base = pd.read_csv(CSV_BASE)
            if "Centro" not in base.columns and "Centro_Codigo" in base.columns:
                base["Centro"] = base["Centro_Codigo"].astype(str) + " - " + base["Centro_Nome"].astype(str)
                
        df_det = None
        if CSV_DETALHES.exists():
            df_det = pd.read_csv(CSV_DETALHES)
            df_det["Centro_Codigo"] = df_det["Centro_Codigo"].astype(str).str.strip()
            df_det["Conta_Codigo"] = df_det["Conta_Codigo"].astype(str).str.strip()
            
            if "Conta_Nome" not in df_det.columns:
                df_det["Conta_Nome"] = "Conta " + df_det["Conta_Codigo"]
                
            df_det["Conta_Completa"] = df_det["Conta_Codigo"] + " - " + df_det["Conta_Nome"].astype(str)
            df_det["Valor"] = pd.to_numeric(df_det["Valor"], errors="coerce").fillna(0)
            df_det["Mes_Trans"] = pd.to_numeric(df_det["Mes_Trans"], errors="coerce").fillna(0).astype(int)
            
        return df, base, df_det
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return None, None, None

df, base, df_det = carregar_dados()

st.title("CUSTOS 2026  |  PAINEL DO GESTOR")
st.caption("Dashboard Executivo de Business Intelligence")

if df is None:
    st.error("Arquivo dados_longos.csv não encontrado ou inválido na pasta do projeto.")
    st.stop()

# Filtros na barra lateral
st.sidebar.header("Filtros Globais")
centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
centro_sel = st.sidebar.selectbox("Centro de custo", centros)

meses_disponiveis = sorted(
    [m for m in df["Mes"].astype(str).unique().tolist() if m != "Total" and str(m).isdigit()],
    key=lambda x: int(x),
)
mes_sel = st.sidebar.selectbox("Mês", ["Todos os meses"] + meses_disponiveis)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Legenda de Status**\n\n"
    "- 🟢 **OK** — dentro do previsto\n"
    "- 🟡 **Atenção** — ≥ 80%\n"
    "- 🔴 **Crítico** — estourou / saldo negativo\n"
    "- ⚫ **Sem orçamento** — houve gasto sem valor orçado"
)

# Filtrar dados principais
d = df.copy()
if centro_sel != "Todos os centros":
    d = d[d["Centro"] == centro_sel]

d_prev_total = d[(d["Tipo"] == "Prev.") & (d["Mes"] == "Total") & (d["Conta_Codigo"] == "Total")]
d_real_total = d[(d["Tipo"] == "Real.") & (d["Mes"] == "Total") & (d["Conta_Codigo"] == "Total")]

orc_anual = float(d_prev_total["Valor_Abs"].sum())
real_anual = float(d_real_total["Valor_Abs"].sum())
saldo_anual = orc_anual - real_anual
pct_anual = (real_anual / orc_anual) if orc_anual > 0 else 0.0

if mes_sel != "Todos os meses":
    d_prev_mes = d[(d["Tipo"] == "Prev.") & (d["Mes"].astype(str) == mes_sel) & (d["Conta_Codigo"] == "Total")]
    d_real_mes = d[(d["Tipo"] == "Real.") & (d["Mes"].astype(str) == mes_sel) & (d["Conta_Codigo"] == "Total")]
    orc_mes = float(d_prev_mes["Valor_Abs"].sum())
    real_mes = float(d_real_mes["Valor_Abs"].sum())
    saldo_mes = orc_mes - real_mes
    pct_mes = (real_mes / orc_mes) if orc_mes > 0 else 0.0
else:
    orc_mes = real_mes = saldo_mes = pct_mes = None

contas = d[d["Conta_Codigo"] != "Total"].copy()
if mes_sel == "Todos os meses":
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})
else:
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})

tab_contas = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
tab_contas["Saldo"] = tab_contas["Orcado"] - tab_contas["Realizado"]
tab_contas["% Consumido"] = tab_contas.apply(
    lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else None, axis=1
)

def status_row(r):
    if r["Orcado"] == 0 and r["Realizado"] > 0:
        return "⚫ Sem orçamento"
    if r["Saldo"] < 0 or (r["Orcado"] > 0 and r["Realizado"] >= r["Orcado"]):
        return "🔴 Crítico"
    if r["Orcado"] > 0 and r["% Consumido"] >= 0.8:
        return "🟡 Atenção"
    return "🟢 OK"

tab_contas["Status"] = tab_contas.apply(status_row, axis=1)
tab_contas["Conta_Codigo_Fmt"] = tab_contas["Conta_Codigo"].astype(str).str.zfill(10)
tab_contas["Conta"] = tab_contas["Conta_Codigo_Fmt"] + " | " + tab_contas["Conta_Descricao"].astype(str)
ordem_status = {"🔴 Crítico": 0, "⚫ Sem orçamento": 1, "🟡 Atenção": 2, "🟢 OK": 3}
tab_contas["_ordem_status"] = tab_contas["Status"].map(ordem_status).fillna(4)
tab_contas = tab_contas.sort_values(["_ordem_status", "Realizado"], ascending=[True, False]).drop(columns="_ordem_status")
tab_show = tab_contas[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status", "Conta_Codigo"]]

def colorir(row):
    status = str(row.get("Status", ""))
    if "Crítico" in status:
        return ["background-color: #EF9A9A"] * len(row)
    if "Atenção" in status:
        return ["background-color: #FFE082"] * len(row)
    if "Sem orçamento" in status:
        return ["background-color: #E0E0E0"] * len(row)
    return ["background-color: #C8E6C9"] * len(row)


def moeda_br(valor):
    if pd.isna(valor):
        return "—"
    return ("R$ " + f"{float(valor):,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

def percentual_br(valor):
    if pd.isna(valor):
        return "—"
    return f"{float(valor) * 100:.1f}%".replace(".", ",")

# Apenas as 3 abas de BI essenciais (sem aba de assistente IA)
aba1, aba2, aba3 = st.tabs([
    "📊 Visão Geral & KPIs", 
    "📈 Gráficos & Comparativo", 
    "📋 Contas & Detalhe Analítico"
])

with aba1:
    st.subheader("Indicadores Principais")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orçamento anual", moeda_br(orc_anual))
    c2.metric("Realizado acumulado", moeda_br(real_anual))
    c3.metric("Saldo atual", moeda_br(saldo_anual))
    c4.metric("Orçamento consumido", percentual_br(pct_anual))

    if mes_sel != "Todos os meses":
        st.markdown(f"**Desempenho no Mês {mes_sel}**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Orçado no mês", moeda_br(orc_mes))
        m2.metric("Realizado no mês", moeda_br(real_mes))
        m3.metric("Saldo do mês", moeda_br(saldo_mes))
        m4.metric("% gasto no mês", percentual_br(pct_mes))
        
    st.divider()
    st.subheader("Resumo Executivo das Contas")
    st.caption("Contas críticas e sem orçamento aparecem primeiro, seguidas das contas em atenção e das contas dentro do previsto.")
    st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True,
        height=350,
    )

with aba2:
    st.subheader("Análise de Gastos e Pontos de Atenção")
    st.caption("Listas para identificar rapidamente os maiores gastos e os riscos do orçamento.")

    sem_orcamento = tab_contas[(tab_contas["Orcado"] == 0) & (tab_contas["Realizado"] > 0)].copy()
    criticas = tab_contas[tab_contas["Status"] == "🔴 Crítico"].copy()
    atencao = tab_contas[tab_contas["Status"] == "🟡 Atenção"].copy()
    maiores = tab_contas.sort_values("Realizado", ascending=False).head(5).copy()

    k1, k2, k3 = st.columns(3)
    k1.metric("Contas críticas", len(criticas))
    k2.metric("Contas em atenção", len(atencao))
    k3.metric("Gastos sem orçamento", len(sem_orcamento))

    colunas = ["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]
    formatos = {"Orcado": moeda_br, "Realizado": moeda_br, "Saldo": moeda_br, "% Consumido": percentual_br}

    st.divider()
    st.subheader("Maiores gastos do período")
    st.dataframe(maiores[colunas].style.format(formatos), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Contas que precisam de atenção")
    if not criticas.empty:
        st.markdown("**Críticas — orçamento estourado ou saldo negativo**")
        st.dataframe(criticas[colunas].style.apply(colorir, axis=1).format(formatos), use_container_width=True, hide_index=True)
    if not sem_orcamento.empty:
        st.markdown("**Gastos sem orçamento**")
        st.dataframe(sem_orcamento[colunas].style.apply(colorir, axis=1).format(formatos), use_container_width=True, hide_index=True)
    if not atencao.empty:
        st.markdown("**Em atenção — 80% ou mais do orçamento consumido**")
        st.dataframe(atencao[colunas].style.apply(colorir, axis=1).format(formatos), use_container_width=True, hide_index=True)
    if criticas.empty and sem_orcamento.empty and atencao.empty:
        st.success("Nenhuma conta exige atenção com os filtros selecionados.")

with aba3:
    st.subheader("Detalhamento por Conta e Lançamentos Analíticos")
    st.caption("Selecione uma conta na tabela para consultar os lançamentos que compõem o valor realizado.")
    try:
        event = st.dataframe(
            tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
                {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
            ),
            use_container_width=True, height=380, selection_mode="single-row", on_select="rerun", key="tabela_contas_aba3"
        )
        
        selected_rows = getattr(event, "selection", {}).get("rows", [])
        if selected_rows:
            linha_selecionada = tab_show.iloc[selected_rows[0]]
            conta_codigo_clicada = str(linha_selecionada["Conta_Codigo"]).strip().lstrip('0')
            conta_nome_completo = linha_selecionada["Conta"]
            st.markdown("---")
            st.subheader(f"🔍 Detalhe Analítico: {conta_nome_completo}")
            if df_det is not None and not df_det.empty:
                df_det_filtrado = df_det.copy()
                if centro_sel != "Todos os centros":
                    c_codigo = centro_sel.split(" - ")[0].strip()
                    df_det_filtrado = df_det_filtrado[df_det_filtrado["Centro_Codigo"] == c_codigo]
                df_det_filtrado = df_det_filtrado[df_det_filtrado["Conta_Codigo"].astype(str).str.lstrip('0') == conta_codigo_clicada]
                if mes_sel != "Todos os meses":
                    df_det_filtrado = df_det_filtrado[df_det_filtrado["Mes_Trans"] == int(mes_sel)]
                if not df_det_filtrado.empty:
                    cols_mostrar = [c for c in ["Centro_Codigo", "DOC", "Data", "Clifor", "Item", "QT", "Mes_Trans", "Valor"] if c in df_det_filtrado.columns]
                    st.dataframe(df_det_filtrado[cols_mostrar].style.format({"Valor": moeda_br}), use_container_width=True, height=400)
                else:
                    st.info("Nenhum lançamento analítico encontrado para esta conta com os filtros atuais.")
            else:
                st.warning("Ficheiro detalhes_longos.csv não disponível.")
    except Exception as e:
        st.info("Selecione uma linha na tabela acima para visualizar os lançamentos analíticos detalhados.")
