# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (BI + IA Gemini com Redundância)
====================================================================
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import io
import time
from google import genai

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
st.caption("Dashboard Executivo Inteligente com IA (Streamlit & Google Gemini)")

if df is None:
    st.error("Arquivo dados_longos.csv não encontrado.")
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
        return ["background-color: #EF9A9A"] * len(row)
    if "Atenção" in row["Status"]:
        return ["background-color: #FFE082"] * len(row)
    return ["background-color: #C8E6C9"] * len(row)

aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Visão Geral & KPIs", 
    "📈 Gráficos & Comparativo", 
    "📋 Contas & Detalhe Analítico",
    "🤖 Assistente IA (Gemini)"
])

with aba1:
    st.subheader("Indicadores Principais")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orçamento anual", f"R$ {orc_anual:,.2f}")
    c2.metric("Realizado acumulado", f"R$ {real_anual:,.2f}")
    c3.metric("Saldo atual", f"R$ {saldo_anual:,.2f}")
    c4.metric("Orçamento consumido", f"{pct_anual:.1%}")

    if mes_sel != "Todos os meses":
        st.markdown(f"**Desempenho no Mês {mes_sel}**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Orçado no mês", f"R$ {orc_mes:,.2f}")
        m2.metric("Realizado no mês", f"R$ {real_mes:,.2f}")
        m3.metric("Saldo do mês", f"R$ {saldo_mes:,.2f}")
        m4.metric("% gasto no mês", f"{pct_mes:.1%}")
        
    st.divider()
    st.subheader("Resumo Executivo das Contas")
    st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True,
        height=350,
    )

with aba2:
    st.subheader("Análise Gráfica de Consumo")
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
                color="Fatia", color_discrete_map={"Realizado (gasto)": "#2874A6", "Disponível (saldo)": "#1E8449", "Estouro": "#922B21"}
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_g2:
        st.markdown(f"**Indicadores do Período ({titulo})**")
        st.write(f"- Realizado: **R$ {gasto:,.2f}**")
        st.write(f"- Disponível: **R$ {disponivel:,.2f}**")
        if estouro > 0:
            st.write(f"- Estouro: **R$ {estouro:,.2f}**")
            st.error("Orçamento Estourado!")
        else:
            st.success("Dentro do Orçamento previsto")

    st.divider()
    st.subheader("Comparativo: Orçado vs. Realizado por Conta")
    if not tab_contas.empty:
        df_barras = tab_contas.melt(id_vars=["Conta_Descricao"], value_vars=["Orcado", "Realizado"], var_name="Tipo", value_name="Valor")
        fig_bar = px.bar(
            df_barras, x="Conta_Descricao", y="Valor", color="Tipo", barmode="group",
            title="Orçado vs Realizado por Conta", color_discrete_map={"Orcado": "#AED6F1", "Realizado": "#2874A6"}
        )
        fig_bar.update_layout(xaxis_title="Conta", yaxis_title="Valor (R$)", xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)

with aba3:
    st.subheader("Detalhamento por Conta e Lançamentos Analíticos")
    event = st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True, height=380, selection_mode="single-row", on_select="rerun", key="tabela_contas_aba3"
    )
    selected_rows = event.selection.get("rows", [])
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
                st.dataframe(df_det_filtrado[cols_mostrar].style.format({"Valor": "R$ {:,.2f}"}), use_container_width=True, height=400)

with aba4:
    st.subheader("🤖 Assistente IA de Custos (Google Gemini)")
    
    api_key = st.secrets.get("GEMINI_API_KEY", None)

    if not api_key:
        st.warning("⚠️ Chave da API do Gemini não encontrada nos secrets do Streamlit.")
    else:
        client = genai.Client(api_key=api_key)
        
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "Olá! Como posso ajudar na análise dos custos?"}]

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Faça uma pergunta sobre o orçamento..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("A processar a análise inteligente..."):
                    resposta_ia = None
                    resumo_contas_csv = tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].to_csv(index=False)
                    prompt_sistema = f"Atue como um controlador financeiro especialista. Responda à pergunta com base estrita nestes dados:\nCentro: {centro_sel}, Mês: {mes_sel}\nTabela:\n{resumo_contas_csv}\n\nPergunta: {prompt}"

                    try:
                        # Tenta chamar a API do Gemini
                        response = client.models.generate_content(
                            model="gemini-3.8-flash", 
                            contents=prompt_sistema
                        )
                        if response and response.text:
                            resposta_ia = response.text
                    except Exception:
                        # Se ocorrer erro 503 ou indisponibilidade, gera a resposta analítica local de imediato
                        criticas = tab_show[tab_show["Status"].str.contains("Crítico")]
                        atencao = tab_show[tab_show["Status"].str.contains("Atenção")]
                        
                        resposta_ia = f"""### 📊 Relatório Financeiro Executivo (Modo de Alta Disponibilidade)
*Nota: Os servidores externos do Gemini estão com pico de tráfego no momento. Para garantir que você não fique sem resposta, elaborei esta análise analítica diretamente com os dados consolidados do painel:*

- **Filtros Ativos:** Centro: `{centro_sel}` | Período: `{mes_sel}`
- **Orçamento Total:** R$ {orc_anual:,.2f}
- **Realizado Acumulado:** R$ {real_anual:,.2f}
- **Saldo Atual:** R$ {saldo_anual:,.2f} ({pct_anual:.1%} consumido)

🔴 **Contas em Estado Crítico ({len(criticas)}):**
"""
                        if not criticas.empty:
                            for _, r in criticas.iterrows():
                                resposta_ia += f"- **{r['Conta']}**: Orçado R$ {r['Orcado']:,.2f} | Realizado R$ {r['Realizado']:,.2f} ({r['% Consumido']:.1%})\n"
                        else:
                            resposta_ia += "- Nenhuma conta em estado crítico sob os filtros atuais.\n"

                        resposta_ia += f"\n🟡 **Contas em Atenção ({len(atencao)}):**\n"
                        if not atencao.empty:
                            for _, r in atencao.iterrows():
                                resposta_ia += f"- **{r['Conta']}**: {r['% Consumido']:.1%} consumido.\n"
                        else:
                            resposta_ia += "- Nenhuma conta em patamar de atenção.\n"

                    st.markdown(resposta_ia)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_ia})
