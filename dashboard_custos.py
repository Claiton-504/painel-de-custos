# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Versão BI Profissional + Assistente IA)
=============================================================================
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
st.caption("Dashboard Executivo Inteligente (Streamlit)")

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

# Preparação dos dados das contas
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


# Organização em Abas Profissionais (Incluindo o Assistente IA)
aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Visão Geral & KPIs", 
    "📈 Gráficos & Comparativo", 
    "📋 Contas & Detalhe Analítico",
    "🤖 Assistente IA / Tirar Dúvidas"
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
                pie_df,
                names="Fatia",
                values="Valor",
                title=f"Distribuição do Orçamento — {titulo}",
                color="Fatia",
                color_discrete_map={
                    "Realizado (gasto)": "#2874A6",
                    "Disponível (saldo)": "#1E8449",
                    "Estouro": "#922B21",
                },
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
        total = gasto + disponivel + estouro
        st.write(f"- Consumido: **{(gasto / total if total else 0):.1%}**")

    st.divider()
    
    st.subheader("Comparativo: Orçado vs. Realizado por Conta")
    if not tab_contas.empty:
        df_barras = tab_contas.melt(
            id_vars=["Conta_Descricao"],
            value_vars=["Orcado", "Realizado"],
            var_name="Tipo",
            value_name="Valor"
        )
        fig_bar = px.bar(
            df_barras,
            x="Conta_Descricao",
            y="Valor",
            color="Tipo",
            barmode="group",
            title="Orçado vs Realizado por Conta",
            color_discrete_map={"Orcado": "#AED6F1", "Realizado": "#2874A6"}
        )
        fig_bar.update_layout(xaxis_title="Conta", yaxis_title="Valor (R$)", xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)

with aba3:
    st.subheader("Detalhamento por Conta e Lançamentos Analíticos")
    st.info("💡 **Como usar:** Clique numa linha da tabela abaixo para expandir e ver os itens, fornecedores e documentos correspondentes.")
    
    event = st.dataframe(
        tab_show[["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]].style.apply(colorir, axis=1).format(
            {"Orcado": "R$ {:,.2f}", "Realizado": "R$ {:,.2f}", "Saldo": "R$ {:,.2f}", "% Consumido": "{:.1%}"}
        ),
        use_container_width=True,
        height=380,
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_contas_aba3"
    )

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
            st.info("Nenhum dado detalhado encontrado na pasta 'detalhes'.")

with aba4:
    st.subheader("🤖 Assistente IA de Custos")
    st.markdown("Tem alguma dúvida sobre os lançamentos, desvios ou contas? Pergunte diretamente ao assistente abaixo:")

    # Inicializar histórico de chat no session_state do Streamlit
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Olá! Sou o seu assistente financeiro de custos. Como posso ajudar na auditoria ou análise dos relatórios hoje?"}
        ]

    # Exibir mensagens anteriores do chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Entrada de texto do chat
    if prompt := st.chat_input("Ex: Qual foi a conta que mais estourou o orçamento?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Resposta inteligente baseada nos dados atuais carregados
        with st.chat_message("assistant"):
            with st.spinner("Analisando dados do painel..."):
                # Lógica de resposta baseada no contexto atual do filtro
                resposta = f"Com base no filtro atual (**Centro:** {centro_sel}, **Mês:** {mes_sel}), analisei os dados financeiros:\n\n"
                
                prompt_lower = prompt.lower()
                if "maior" in prompt_lower or "estourou" in prompt_lower or "crítico" in prompt_lower or "gasto" in prompt_lower:
                    criticas = tab_show[tab_show["Status"].str.contains("Crítico|Atenção")]
                    if not criticas.empty:
                        top_conta = criticas.iloc[0]
                        resposta += f"A conta com maior atenção/estouro no momento é a **{top_conta['Conta']}**, com um realizado de **R$ {top_conta['Realizado']:,.2f}** frente a um orçamento de **R$ {top_conta['Orcado']:,.2f}** ({top_conta['% Consumido']:.1%} consumido)."
                    else:
                        resposta += "Parabéns! No filtro atual não existem contas em estado crítico ou de atenção."
                elif "resumo" in prompt_lower or "total" in prompt_lower:
                    resposta += f"O orçamento total é de **R$ {orc_anual:,.2f}**, com um realizado acumulado de **R$ {real_anual:,.2f}**, resultando num saldo de **R$ {saldo_anual:,.2f}** ({pct_anual:.1%} consumido)."
                else:
                    resposta += f"Recebi a sua pergunta sobre: *'{prompt}'*. O centro selecionado é **{centro_sel}** e o orçamento consumido total é de **{pct_anual:.1%}**. Pode detalhar a conta específica que gostaria de inspecionar na aba anterior."

                st.markdown(resposta)
                st.session_state.messages.append({"role": "assistant", "content": resposta})
