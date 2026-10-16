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
