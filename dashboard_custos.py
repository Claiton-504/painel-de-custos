# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit
====================================
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

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_BASE = BASE / "base_calculada.csv"
CSV_DETALHES = BASE / "detalhes_longos.csv"


@st.cache_data
def carregar_dados():
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


df, base, df_det = carregar_dados()

st.title("CUSTOS 2026  |  PAINEL DO GESTOR")
st.caption("Dashboard em Python (Streamlit)")

if df is None:
    st.error("Arquivo dados_longos.csv não encontrado.")
    st.stop()

# Filtros na barra lateral com a Legenda de Cores de volta
st.sidebar.header("Analisar um relatório")
centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
centro_sel = st.sidebar.selectbox("Centro de custo", centros)

meses_disponiveis = sorted(
    [m for m in df["Mes"].astype(str).unique().tolist() if m != "Total" and str(m).isdigit()],
    key=lambda x: int(x),
)
mes_sel = st.sidebar.selectbox("Mês", ["Todos os meses"] + meses_disponiveis)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Legenda**\n\n"
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
    pct_mes = (real_mes / orc_mes) if orc_mes > 0 else 0.0
else:
    orc_mes = real_mes = saldo_mes = pct_mes = None

# KPIs
st.subheader("Indicadores")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Orçamento anual", f"R$ {orc_anual:,.2f}")
c2.metric("Realizado acumulado", f"R$ {real_anual:,.2f}")
c3.metric("Saldo atual", f"R$ {saldo_anual:,.2f}")
c4.metric("Orçamento consumido", f"{pct_anual:.1%}")

if mes_sel != "Todos os meses":
    st.markdown(f"**Mês {mes_sel}**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Orçado no mês", f"R$ {orc_mes:,.2f}")
    m2.metric("Realizado no mês", f"R$ {real_mes:,.2f}")
    m3.metric("Saldo do mês", f"R$ {saldo_mes:,.2f}")
    m4.metric("% gasto no mês", f"{pct_mes:.1%}")

# ═════════════════════════════════════════════════════════════════════
# GRÁFICO DE PIZZA DE VOLTA
# ═════════════════════════════════════════════════════════════════════
st.subheader("Consumo do orçamento")
col_g, col_t = st.columns(2)
with col_g:
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
        fig = px.pie(
            pie_df,
            names="Fatia",
            values="Valor",
            title=f"Consumo — {titulo}",
            color="Fatia",
            color_discrete_map={
                "Realizado (gasto)": "#2874A6",
                "Disponível (saldo)": "#1E8449",
                "Estouro": "#922B21",
            },
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

with col_t:
    st.markdown(f"**Resumo ({titulo})**")
    st.write(f"- Realizado: **R$ {gasto:,.2f}**")
    st.write(f"- Disponível: **R$ {disponivel:,.2f}**")
    if estouro > 0:
        st.write(f"- Estouro: **R$ {estouro:,.2f}**")
        st.error("Estourou o orçamento")
    else:
        st.success("Dentro do orçamento")
    total = gasto + disponivel + estouro
    st.write(f"- Consumido: **{(gasto / total if total else 0):.1%}**")

# ═════════════════════════════════════════════════════════════════════
# TABELA PRINCIPAL DE CONTAS COM CORES E STATUS DE VOLTA
# ═════════════════════════════════════════════════════════════════════
st.subheader("Contas do centro / mês")
contas = d[d["Conta_Codigo"] != "Total"].copy()
if mes_sel == "Todos os meses":
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"] == "Total")].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})
else:
    prev = contas[(contas["Tipo"] == "Prev.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Orcado"})
    real = contas[(contas["Tipo"] == "Real.") & (contas["Mes"].astype(str) == mes_sel)].groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum().rename(columns={"Valor_Abs": "Realizado"})

tab = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
tab["Saldo"] = tab["Orcado"] - tab["Realizado"]
tab["% Consumido"] = tab.apply(lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0), axis=1)

def status_row(r):
    if r["Saldo"] < 0 or (r["Orcado"] == 0 and r["Realizado"] > 0) or r["% Consumido"] >= 1:
        return "Crítico"
    if r["% Consumido"] >= 0.8:
        return "Atenção"
    return "OK"

tab["Status"] = tab.apply(status_row, axis=1)
tab["Conta_Codigo_Fmt"] = tab["Conta_Codigo"].astype(str).str.zfill(10)
tab["Conta"] = tab["Conta_Codigo_Fmt"] + " | " + tab["Conta_Descricao"].astype(str)
tab = tab.sort_values("Realizado", ascending=False)
tab_show = tab[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status", "Conta_Codigo"]]

def colorir(row):
    if row["Status"] == "Crítico":
        return ["background-color: #EF9A9A"] * len(row)
    if row["Status"] == "Atenção":
        return ["background-color: #FFE082"] * len(row)
    return ["background-color: #C8E6C9"] * len(row)

event = st.dataframe(
    tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
        {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
    ),
    use_container_width=True,
    height=350,
    selection_mode="single-row",
    on_select="rerun",
    key="tabela_contas"
)

# ═════════════════════════════════════════════════════════════════════
# DETALHE ANALÍTICO POR CLIQUE (SÓ APARECE AO CLICAR NA CONTA)
# ═════════════════════════════════════════════════════════════════════
selected_rows = event.selection.get("rows", [])

if selected_rows:
    linha_selecionada = tab_show.iloc[selected_rows[0]]
    conta_codigo_clicada = str(linha_selecionada["Conta_Codigo"]).strip().lstrip('0')
    conta_nome_completo = linha_selecionada["Conta"]

    st.markdown("---")
    st.subheader(f"🔍 Detalhe Analítico de Lançamentos: {conta_nome_completo}")

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
            df_exibir = df_det_filtrado[cols_mostrar].copy()
            
            st.dataframe(
                df_exibir.style.format({"Valor": "R$ {:,.2f}"}),
                use_container_width=True,
                height=400
            )
            
            buffer_det = io.BytesIO()
            with pd.ExcelWriter(buffer_det, engine="openpyxl") as writer:
                df_exibir.to_excel(writer, index=False, sheet_name="Detalhes_Lancamentos")
            buffer_det.seek(0)
            
            st.download_button(
                label="📥 Descarregar Lançamentos Detalhados em Excel",
                data=buffer_det,
                file_name=f"Detalhes_Conta_{conta_codigo_clicada}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum lançamento detalhado encontrado para esta conta com os filtros atuais.")
    else:
        st.info("Nenhum dado detalhado encontrado.")
else:
    st.markdown("---")
    st.info("💡 **Dica:** **Clique em qualquer linha da tabela de contas acima** para revelar automaticamente o detalhe analítico dos lançamentos!")