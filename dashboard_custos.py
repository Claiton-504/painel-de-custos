# -*- coding: utf-8 -*-
"""
Painel de Custos do RH 2026
Inclui: painel, consulta detalhada por conta e novo lançamento.
"""
from pathlib import Path
import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Painel de Custos do RH 2026",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_DET = BASE / "detalhes_longos.csv"
CSV_LANC = BASE / "lancamentos.csv"


@st.cache_data(show_spinner="Carregando...")
def carregar_dados():
    if not CSV_LONG.exists():
        return None, None
    df = pd.read_csv(CSV_LONG)
    df["Centro_Codigo"] = df["Centro_Codigo"].astype(str).str.strip()
    df["Centro_Nome"] = df["Centro_Nome"].astype(str).str.strip()
    df["Centro"] = df["Centro_Codigo"] + " - " + df["Centro_Nome"]
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    df["Mes"] = df["Mes"].astype(str)

    det = None
    if CSV_DET.exists():
        det = pd.read_csv(CSV_DET)
        det["Centro_Codigo"] = det["Centro_Codigo"].astype(str).str.strip()
        det["Conta_Codigo"] = det["Conta_Codigo"].astype(str).str.strip()
        det["Valor"] = pd.to_numeric(det["Valor"], errors="coerce").fillna(0)
        if "Mes_Trans" in det.columns:
            det["Mes_Trans"] = pd.to_numeric(det["Mes_Trans"], errors="coerce").fillna(0).astype(int)
    return df, det


def carregar_lancamentos():
    cols = [
        "data_registro", "centro_lancamento", "conta", "re", "nome",
        "centro_quem_pegou", "data", "quantidade", "quem_entregou", "observacao",
    ]
    if CSV_LANC.exists():
        return pd.read_csv(CSV_LANC)
    return pd.DataFrame(columns=cols)


def salvar_lancamento(registro):
    hist = carregar_lancamentos()
    hist = pd.concat([hist, pd.DataFrame([registro])], ignore_index=True)
    hist.to_csv(CSV_LANC, index=False)
    return hist


df, det = carregar_dados()
if df is None:
    st.error("Arquivo dados_longos.csv não encontrado na pasta do app.")
    st.stop()

aba_painel, aba_detalhe, aba_lanc = st.tabs([
    "📊 Painel",
    "🔍 Consulta detalhada",
    "➕ Novo lançamento",
])

# ═══════════════════════════════════════════════════════════
# PAINEL
# ═══════════════════════════════════════════════════════════
with aba_painel:
    with st.sidebar:
        st.header("Filtros")
        centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
        centro_sel = st.selectbox("Centro de custo", centros, key="p_centro")
        meses = sorted(
            [m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()],
            key=lambda x: int(x),
        )
        mes_sel = st.selectbox("Mês", ["Todos os meses"] + meses, key="p_mes")

    d = df if centro_sel == "Todos os centros" else df[df["Centro"] == centro_sel]
    m = d["Conta_Codigo"] == "Total"

    if mes_sel == "Todos os meses":
        orc = float(d[m & (d["Tipo"] == "Prev.") & (d["Mes"] == "Total")]["Valor_Abs"].sum())
        real = float(d[m & (d["Tipo"] == "Real.") & (d["Mes"] == "Total")]["Valor_Abs"].sum())
        rotulo = "Anual"
    else:
        orc = float(d[m & (d["Tipo"] == "Prev.") & (d["Mes"] == mes_sel)]["Valor_Abs"].sum())
        real = float(d[m & (d["Tipo"] == "Real.") & (d["Mes"] == mes_sel)]["Valor_Abs"].sum())
        rotulo = f"Mês {mes_sel}"

    saldo = orc - real
    pct = real / orc if orc > 0 else 0.0

    st.title("Painel de Custos do RH")
    st.caption(f"Exercício 2026 · {rotulo} · {centro_sel}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orçamento", f"R$ {orc:,.2f}")
    c2.metric("Realizado", f"R$ {real:,.2f}")
    c3.metric("Saldo", f"R$ {saldo:,.2f}")
    c4.metric("Consumo", f"{pct:.1%}")

    contas = d[d["Conta_Codigo"] != "Total"].copy()
    if mes_sel == "Todos os meses":
        prev = (
            contas[(contas["Tipo"] == "Prev.") & (contas["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum().rename(columns={"Valor_Abs": "Orcado"})
        )
        real_df = (
            contas[(contas["Tipo"] == "Real.") & (contas["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum().rename(columns={"Valor_Abs": "Realizado"})
        )
    else:
        prev = (
            contas[(contas["Tipo"] == "Prev.") & (contas["Mes"] == mes_sel)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum().rename(columns={"Valor_Abs": "Orcado"})
        )
        real_df = (
            contas[(contas["Tipo"] == "Real.") & (contas["Mes"] == mes_sel)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum().rename(columns={"Valor_Abs": "Realizado"})
        )

    tab = prev.merge(real_df, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
    tab["Saldo"] = tab["Orcado"] - tab["Realizado"]
    tab["%"] = tab.apply(
        lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0),
        axis=1,
    )

    def status_row(r):
        if r["Saldo"] < 0 or (r["Orcado"] == 0 and r["Realizado"] > 0) or r["%"] >= 1:
            return "Crítico"
        if r["%"] >= 0.8:
            return "Atenção"
        return "OK"

    tab["Status"] = tab.apply(status_row, axis=1)
    tab["Conta"] = tab["Conta_Codigo"].astype(str).str.zfill(10) + " | " + tab["Conta_Descricao"].astype(str)
    tab = tab[~((tab["Orcado"] == 0) & (tab["Realizado"] == 0))]
    ordem = {"Crítico": 0, "Atenção": 1, "OK": 2}
    tab["_o"] = tab["Status"].map(ordem)
    tab = tab.sort_values(["_o", "Realizado"], ascending=[True, False])

    show = tab[["Conta", "Orcado", "Realizado", "Saldo", "%", "Status", "Conta_Codigo"]]

    def colorir(row):
        if row["Status"] == "Crítico":
            return ["background-color: #fef2f2"] * len(row)
        if row["Status"] == "Atenção":
            return ["background-color: #fffbeb"] * len(row)
        return ["background-color: #ecfdf5"] * len(row)

    st.subheader("Contas")
    st.caption("Use a aba Consulta detalhada para pesquisar uma conta e ver os lançamentos.")
    st.dataframe(
        show[["Conta", "Orcado", "Realizado", "Saldo", "%", "Status"]].style.apply(colorir, axis=1).format({
            "Orcado": "R$ {:,.2f}",
            "Realizado": "R$ {:,.2f}",
            "Saldo": "R$ {:,.2f}",
            "%": "{:.1%}",
        }),
        use_container_width=True,
        height=420,
        hide_index=True,
    )

# ═══════════════════════════════════════════════════════════
# CONSULTA DETALHADA (conta por conta + lançamentos)
# ═══════════════════════════════════════════════════════════
with aba_detalhe:
    st.title("Consulta detalhada")
    st.caption("Pesquise uma conta e veja os lançamentos que compõem o valor.")

    centros_d = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
    colf1, colf2 = st.columns(2)
    with colf1:
        centro_d = st.selectbox("Centro de custo", centros_d, key="d_centro")
    with colf2:
        mes_d = st.selectbox("Mês", ["Todos os meses"] + sorted(
            [m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()],
            key=lambda x: int(x),
        ), key="d_mes")

    d2 = df if centro_d == "Todos os centros" else df[df["Centro"] == centro_d]
    contas_opts = (
        d2[d2["Conta_Codigo"] != "Total"][["Conta_Codigo", "Conta_Descricao"]]
        .drop_duplicates()
        .sort_values("Conta_Descricao")
    )
    contas_opts["Label"] = contas_opts["Conta_Codigo"].astype(str).str.zfill(10) + " | " + contas_opts["Conta_Descricao"]
    opcoes = ["— selecione uma conta —"] + contas_opts["Label"].tolist()
    conta_escolhida = st.selectbox("Conta", opcoes)

    if not conta_escolhida.startswith("—"):
        cod_raw = conta_escolhida.split(" | ")[0].lstrip("0")
        st.subheader(f"Lançamentos · {conta_escolhida}")

        if det is not None and not det.empty:
            f = det.copy()
            if centro_d != "Todos os centros":
                cc = centro_d.split(" - ")[0].strip()
                f = f[f["Centro_Codigo"] == cc]
            f = f[f["Conta_Codigo"].astype(str).str.lstrip("0") == cod_raw]
            if mes_d != "Todos os meses" and "Mes_Trans" in f.columns:
                f = f[f["Mes_Trans"] == int(mes_d)]

            cols = [c for c in ["Centro_Codigo", "DOC", "Data", "Clifor", "Item", "QT", "Mes_Trans", "Valor"] if c in f.columns]
            if f.empty or not cols:
                st.info("Nenhum lançamento analítico encontrado para esta conta com os filtros atuais.")
            else:
                st.dataframe(
                    f[cols].sort_values("Valor", ascending=False).style.format({"Valor": "R$ {:,.2f}"}),
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                )
        else:
            # Fallback: mostra valores mensais da conta a partir de dados_longos
            st.warning("Arquivo detalhes_longos.csv não encontrado. Mostrando valores mensais da conta.")
            sub = d2[(d2["Conta_Codigo"].astype(str).str.lstrip("0") == cod_raw) & (d2["Tipo"].isin(["Prev.", "Real."]))]
            sub = sub[sub["Mes"] != "Total"]
            if sub.empty:
                st.info("Sem dados mensais para esta conta.")
            else:
                piv = sub.pivot_table(index="Mes", columns="Tipo", values="Valor_Abs", aggfunc="sum").reset_index()
                st.dataframe(piv, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════
# NOVO LANÇAMENTO
# ═══════════════════════════════════════════════════════════
with aba_lanc:
    st.title("Novo lançamento")
    st.caption("Registre entregas, consumos ou alocações de qualquer centro e conta.")

    with st.form("form_lanc", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            centro_lanc = st.selectbox(
                "Centro de custo (do lançamento)",
                sorted(df["Centro"].unique().tolist()),
            )
            re = st.text_input("RE")
            centro_pegou = st.selectbox(
                "Centro de custo de quem pegou",
                sorted(df["Centro"].unique().tolist()),
            )
            quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        with c2:
            contas_lista = sorted(
                df[df["Conta_Codigo"] != "Total"]["Conta_Descricao"].dropna().unique().tolist()
            )
            conta = st.selectbox("Conta", contas_lista)
            nome = st.text_input("Nome")
            data_lanc = st.date_input("Data", value=date.today())
            quem_entregou = st.text_input("Quem entregou")

        observacao = st.text_area("Observação (opcional)", height=70)
        ok = st.form_submit_button("Salvar lançamento", type="primary", use_container_width=True)

        if ok:
            if not re.strip() or not nome.strip() or not quem_entregou.strip():
                st.error("Preencha RE, Nome e Quem entregou.")
            else:
                registro = {
                    "data_registro": date.today().isoformat(),
                    "centro_lancamento": centro_lanc,
                    "conta": conta,
                    "re": re.strip(),
                    "nome": nome.strip(),
                    "centro_quem_pegou": centro_pegou,
                    "data": data_lanc.isoformat(),
                    "quantidade": int(quantidade),
                    "quem_entregou": quem_entregou.strip(),
                    "observacao": observacao.strip(),
                }
                salvar_lancamento(registro)
                st.success("Lançamento registrado com sucesso.")

    st.divider()
    st.subheader("Histórico de lançamentos")
    hist = carregar_lancamentos()
    if hist.empty:
        st.info("Nenhum lançamento registrado ainda.")
    else:
        st.dataframe(
            hist.sort_values("data_registro", ascending=False),
            use_container_width=True,
            height=320,
            hide_index=True,
        )
        st.download_button(
            "Baixar histórico (CSV)",
            data=hist.to_csv(index=False).encode("utf-8-sig"),
            file_name="lancamentos_rh.csv",
            mime="text/csv",
        )
