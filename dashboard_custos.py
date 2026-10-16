# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Painel Executivo Premium)
==============================================================
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Custos 2026 | Painel do Gestor",
    page_icon="📊",
    layout="wide",
)

# Estilização CSS Avançada para um visual corporativo moderno
st.markdown("""
    <style>
    /* Fundo geral e tipografia limpa */
    .main {
        background-color: #f4f6f9;
    }
    
    /* Cartões de Métricas Executivas */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #1e293b;
    }
    
    /* Cabeçalhos de secção estilizados */
    h3 {
        color: #1e293b;
        font-weight: 600;
        padding-top: 10px;
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

# Cabeçalho Principal com design limpo
st.markdown("## 📊 Gestão Executiva de Custos | FY2026")
st.markdown("Painel analítico para acompanhamento orçamental e controlo de despesas.")

if df is None:
    st.error("Arquivo dados_longos.csv não encontrado ou inválido na pasta do projeto.")
    st.stop()

# Filtros na barra lateral com estilo executivo
st.sidebar.markdown("### ⚙️ Filtros Globais")
centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
centro_sel = st.sidebar.selectbox("Centro de Custo", centros)

meses_disponiveis = sorted(
    [m for m in df["Mes"].astype(str).unique().tolist() if m != "Total" and str(m).isdigit()],
    key=lambda x: int(x),
)
mes_sel = st.sidebar.selectbox("Período (Mês)", ["Todos os meses"] + meses_disponiveis)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Legenda de Status**\n\n"
    "- 🟢 **OK** — dentro do previsto\n"
    "- 🟡 **Atenção** — ≥ 80%\n"
    "- 🔴 **Crítico** — estourou / saldo negativo"
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
    pct_mes = (real_mes / orc_mes) if real_mes > 0 else 0.0
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
tab_contas["% Consumido"] = tab_contas.apply(lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0), axis=1)

def status_row(r):
    if r["Saldo"] < 0 or (r["Orcado"] == 0 and r["Realizado"] > 0) or r["% Consumido"] >= 1:
        return "🔴 Crítico"
    if r["% Consumido"] >= 0.8:
        return "🟡 Atenção"
    return "🟢 OK"

tab_contas["Status"] = tab_contas.apply(status_row, axis=1)
tab_contas["Conta_Codigo_Fmt"] = tab_contas["Conta_Codigo"].astype(str).str.zfill(10)
tab_contas["Conta"] = tab_contas["Conta_Codigo_Fmt"] + " | " + tab_contas["Conta_Descricao"].astype(str)
tab_contas = tab_contas.sort_values("Realizado", ascending=False)
tab_show = tab_contas[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status", "Conta_Codigo"]]

def colorir(row):
    if "Crítico" in row["Status"]:
        return ["background-color: #FEE2E2"] * len(row)
    if "Atenção" in row["Status"]:
        return ["background-color: #FEF3C7"] * len(row)
    return ["background-color: #DCFCE7"] * len(row)

aba1, aba2, aba3 = st.tabs([
    "📊 Visão Geral & KPIs", 
    "📈 Gráficos & Comparativo", 
    "📋 Contas & Detalhe Analítico"
])

with aba1:
    st.markdown("### 📈 Indicadores Principais (Anual)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Orçamento Anual</div><div class="metric-value">R$ {orc_anual:,.2f}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Realizado Acumulado</div><div class="metric-value">R$ {real_anual:,.2f}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Saldo Atual</div><div class="metric-value">R$ {saldo_anual:,.2f}</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-title">Orçamento Consumido</div><div class="metric-value">{pct_anual:.1%}</div></div>""", unsafe_allow_html=True)

    if mes_sel != "Todos os meses":
        st.markdown(f"### 📅 Desempenho no Mês {mes_sel}")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Orçado no Mês</div><div class="metric-value">R$ {orc_mes:,.2f}</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Realizado no Mês</div><div class="metric-value">R$ {real_mes:,.2f}</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">Saldo do Mês</div><div class="metric-value">R$ {saldo_mes:,.2f}</div></div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">% Gasto no Mês</div><div class="metric-value">{pct_mes:.1%}</div></div>""", unsafe_allow_html=True)
        
    st.divider()
    st.markdown("### 📋 Resumo Executivo das Contas")
    st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True,
        height=380,
    )

with aba2:
    st.markdown("### 📊 Análise Gráfica de Consumo")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if mes_sel == "Todos os meses":
            gasto, disponivel, estouro = real_anual, max(0.0, saldo_anual), max(0.0, -saldo_anual)
            titulo = "Anual"
        else:
            gasto, disponivel, estouro = real_mes, max(0.0, saldo_mes), max(0.0, -saldo_mes)
            titulo = f"Mês {mes_sel}"
            
        pie_df = pd.DataFrame(
            {"Fatia": ["Realizado (gasto)", "Disponível (saldo)", "Estouro"], "Valor": [gasto, disponivel, estouro]}
        )
        pie_df = pie_df[pie_df["Valor"] > 0]
        if not pie_df.empty:
            fig_pie = px.pie(
                pie_df, names="Fatia", values="Valor", title=f"Distribuição do Orçamento — {titulo}",
                color="Fatia", color_discrete_map={"Realizado (gasto)": "#0284c7", "Disponível (saldo)": "#10b981", "Estouro": "#ef4444"}
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        st.markdown(f"### 📌 Sumário do Período ({titulo})")
        st.write(f"- Realizado: **R$ {gasto:,.2f}**")
        st.write(f"- Disponível: **R$ {disponivel:,.2f}**")
        if estouro > 0:
            st.write(f"- Estouro: **R$ {estouro:,.2f}**")
            st.error("⚠️ Orçamento Estourado no Período!")
        else:
            st.success("✅ Operação dentro do orçamento previsto.")

    st.divider()
    st.markdown("### 📊 Orçado vs. Realizado por Conta")
    if not tab_contas.empty:
        df_barras = tab_contas.melt(id_vars=["Conta_Descricao"], value_vars=["Orcado", "Realizado"], var_name="Tipo", value_name="Valor")
        fig_bar = px.bar(
            df_barras, x="Conta_Descricao", y="Valor", color="Tipo", barmode="group",
            title="Comparativo por Conta", color_discrete_map={"Orcado": "#93c5fd", "Realizado": "#0284c7"}
        )
        fig_bar.update_layout(xaxis_title="Conta", yaxis_title="Valor (R$)", xaxis_tickangle=-45, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

with aba3:
    st.markdown("### 🔍 Consulta Analítica de Lançamentos")
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
            st.markdown(f"#### 🔎 Lançamentos da Conta: {conta_nome_completo}")
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
                    st.dataframe(df_det_filtrado[cols_mostrar].style.format({"Valor": "R$ {:,.2f}"}), use_container_width=True, height=400)
                else:
                    st.info("Nenhum lançamento analítico encontrado para esta conta com os filtros atuais.")
            else:
                st.warning("Ficheiro detalhes_longos.csv não disponível.")
    except Exception as e:
        st.info("Selecione uma linha na tabela acima para visualizar os lançamentos analíticos detalhados.")
