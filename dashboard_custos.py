# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Painel Executivo Premium de Alto Nível)
========================================================================
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# Configuração da página para layout profissional
st.set_page_config(
    page_title="Custos 2026 | Painel do Gestor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- SISTEMA DE DESIGN CSS AVANÇADO ---
st.markdown("""
    <style>
    /* Reset e Fundo Profissional */
    .main {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 95% !important;
    }

    /* Cabeçalho do Painel Executivo */
    .dashboard-header {
        color: #1e293b;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }
    .dashboard-subheader {
        color: #64748b;
        font-size: 15px;
        margin-bottom: 25px;
    }

    /* Cartões de Métricas Executivas (KPIs) */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1.25rem;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    .kpi-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 800;
        color: #0f172a;
        line-height: 1;
    }
    .kpi-trend {
        font-size: 14px;
        font-weight: 500;
        margin-top: 5px;
    }

    /* Sidebar Limpa */
    [data-testid="stSidebar"] {
        background-color: #f1f5f9;
        border-right: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_DETALHES = BASE / "detalhes_longos.csv"

@st.cache_data
def carregar_dados():
    try:
        if not CSV_LONG.exists():
            return None, None
            
        df = pd.read_csv(CSV_LONG)
        df["Centro"] = df["Centro_Codigo"].astype(str) + " - " + df["Centro_Nome"].astype(str)
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        df["Valor_Abs"] = df["Valor"].abs()
        
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
            
        return df, df_det
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return None, None

df, df_det = carregar_dados()

if df is None:
    st.error("Arquivo dados_longos.csv não encontrado ou inválido na pasta do projeto.")
    st.stop()

# --- BARRA LATERAL (Sidebar) ---
with st.sidebar:
    st.markdown("### ⚙️ Parâmetros do Painel")
    centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
    centro_sel = st.selectbox("Centro de Custo", centros)

    meses_disponiveis = sorted(
        [m for m in df["Mes"].astype(str).unique().tolist() if m != "Total" and str(m).isdigit()],
        key=lambda x: int(x),
    )
    mes_sel = st.selectbox("Período (Mês)", ["Todos os meses"] + meses_disponiveis)

    st.markdown("---")
    st.markdown("### 📌 Legenda")
    st.markdown("🟢 **OK**: < 80%\n\n🟡 **Atenção**: ≥ 80%\n\n🔴 **Crítico**: > 100%")

# --- PROCESSAMENTO DE DADOS ---
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
    titulo_periodo = f"Mês {mes_sel}"
else:
    orc_mes = real_mes = saldo_mes = pct_mes = None
    titulo_periodo = "Anual"

contas = d[d["Conta_Codigo"] != "Total"].copy()
if mes_sel == "Todos os meses":
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})
else:
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})

tab_contas = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
tab_contas["Saldo"] = tab_contas["Orcado"] - tab_contas["Realizado"]
tab_contas["% Consumido"] = tab_contas.apply(lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0), axis=1)

def status_row(r):
    if r["Saldo"] < 0 or (r["Orcado"] == 0 and r["Realizado"] > 0) or r["% Consumido"] > 1: return "🔴 Crítico"
    if r["% Consumido"] >= 0.8: return "🟡 Atenção"
    return "🟢 OK"

tab_contas["Status"] = tab_contas.apply(status_row, axis=1)
tab_contas["Conta_Codigo_Fmt"] = tab_contas["Conta_Codigo"].astype(str).str.zfill(10)
tab_contas["Conta"] = tab_contas["Conta_Codigo_Fmt"] + " | " + tab_contas["Conta_Descricao"].astype(str)
tab_contas = tab_contas.sort_values("Realizado", ascending=False)
tab_show = tab_contas[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status", "Conta_Codigo"]]

def colorir_tabela(row):
    if "Crítico" in row["Status"]: return ["background-color: #fef2f2; color: #991b1b"] * len(row)
    if "Atenção" in row["Status"]: return ["background-color: #fffbeb; color: #92400e"] * len(row)
    return ["background-color: #f0fdf4; color: #166534"] * len(row)

# --- LAYOUT DO DASHBOARD ---

st.markdown('<div class="dashboard-header">📈 Relatório Analítico de Custos | FY2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="dashboard-subheader">Visão de BI para acompanhamento orçamental e controlo de despesas. Filtros: {centro_sel} | {mes_sel}</div>', unsafe_allow_html=True)

# 1. KPIs
gasto_exibir, orc_exibir, saldo_exibir, pct_exibir = (real_anual, orc_anual, saldo_anual, pct_anual) if mes_sel == "Todos os meses" else (real_mes, orc_mes, saldo_mes, pct_mes)
tendencia_cor = "#166534" if saldo_exibir >= 0 else "#991b1b"
tendencia_txt = "dentro do previsto" if saldo_exibir >= 0 else "excesso orçamental"

st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Orçamento Global ({titulo_periodo})</div>
            <div class="kpi-value">R$ {orc_exibir:,.2f}</div>
            <div class="kpi-trend" style="color: #64748b;">valor total orçado</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Realizado Acumulado ({titulo_periodo})</div>
            <div class="kpi-value">R$ {gasto_exibir:,.2f}</div>
            <div class="kpi-trend" style="color: {tendencia_cor};">{pct_exibir:.1%} consumido</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Saldo Disponível ({titulo_periodo})</div>
            <div class="kpi-value" style="color: {tendencia_cor};">R$ {saldo_exibir:,.2f}</div>
            <div class="kpi-trend" style="color: {tendencia_cor};">{tendencia_txt}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Eficiência Orçamental ({titulo_periodo})</div>
            <div class="kpi-value">{pct_exibir:.1%}</div>
            <div class="kpi-trend" style="color: {tendencia_cor};">taxa de consumo</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 2. Gráficos e Tabela
col_graficos, col_tabela = st.columns([2, 3])

with col_graficos:
    st.subheader(f"📊 Composição — {titulo_periodo}")
    gasto, disponivel, estouro = gasto_exibir, max(0.0, saldo_exibir), max(0.0, -saldo_exibir)
    pie_df = pd.DataFrame({"Fatia": ["Realizado", "Disponível", "Estouro"], "Valor": [gasto, disponivel, estouro]})
    pie_df = pie_df[pie_df["Valor"] > 0]
    if not pie_df.empty:
        fig_pie = px.pie(pie_df, names="Fatia", values="Valor", color="Fatia", hole=0.5,
                         color_discrete_map={"Realizado": "#475569", "Disponível": "#10b981", "Estouro": "#ef4444"})
        fig_pie.update_traces(textposition="inside", textinfo="percent")
        fig_pie.update_layout(margin=dict(t=20, b=20, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

with col_tabela:
    st.subheader(f"📋 Relatório Executivo das Contas — {titulo_periodo}")
    st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir_tabela, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True,
        height=380,
    )

st.divider()

# 3. Consulta Detalhada de Lançamentos
st.subheader("🔍 Consulta Detalhada de Lançamentos")
try:
    event = st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir_tabela, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True, height=250, selection_mode="single-row", on_select="rerun", key="tabela_detalhe_aba3"
    )
    
    selected_rows = getattr(event, "selection", {}).get("rows", [])
    if selected_rows:
        linha_selecionada = tab_show.iloc[selected_rows[0]]
        conta_codigo_clicada = str(linha_selecionada["Conta_Codigo"]).strip().lstrip('0')
        conta_nome_completo = linha_selecionada["Conta"]
        st.markdown(f"#### Lançamentos Analíticos da Conta: {conta_nome_completo}")
        if df_det is not None and not df_det.empty:
            df_det_filtrado = df_det.copy()
            if centro_sel != "Todos os centros":
                c_codigo = centro_sel.split(" - ")[0].strip()
                df_det_filtrado = df_det_filtrado[df_det_filtrado["Centro_Codigo"] == c_codigo]
            df_det_filtrado = df_det_filtrado[df_det_filtrado["Conta_Codigo"].astype(str).str.lstrip('0') == conta_codigo_clicada]
            if mes_sel != "Todos os meses":
                df_det_filtrado = df_det_filtrado[df_det_filtrado["Mes_Trans"] == int(mes_sel)]
            if not df_det_filtrado.empty:
                cols_mostrar = [c for c in ["DOC", "Data", "Clifor", "Item", "Valor"] if c in df_det_filtrado.columns]
                st.dataframe(df_det_filtrado[cols_mostrar].sort_values("Valor", ascending=False).style.format({"Valor": "R$ {:,.2f}"}), use_container_width=True, height=300)
            else:
                st.info("Nenhum lançamento analítico encontrado para esta conta com os filtros atuais.")
except Exception as e:
    st.info("Selecione uma linha na tabela executiva acima para visualizar os lançamentos analíticos detalhados.")
