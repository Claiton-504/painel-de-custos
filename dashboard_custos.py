# -*- coding: utf-8 -*-
"""
Painel de Custos do RH 2026
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

# ── Design ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}
.main {
    background: #f8fafc;
}
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px !important;
}
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #0f172a;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: #f1f5f9;
    padding: 6px;
    border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
}

/* Header */
.h1 {
    font-size: 1.75rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
}
.h1-sub {
    font-size: 0.95rem;
    color: #64748b;
    margin: 0 0 1.5rem 0;
}

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.kpi {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.25rem 1.35rem;
    box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.kpi-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.1;
}
.kpi-hint {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.35rem;
}

/* Status colors */
.status-ok { color: #047857; }
.status-aten { color: #b45309; }
.status-crit { color: #b91c1c; }

/* Section titles */
.sec-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e293b;
    margin: 1.5rem 0 0.75rem 0;
}

/* Dataframe container */
div[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Carregando dados…")
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
    st.error("Arquivo **dados_longos.csv** não encontrado.")
    st.stop()

# ── Abas ───────────────────────────────────────────────────
aba_painel, aba_detalhe, aba_lanc = st.tabs([
    "📊  Painel",
    "🔍  Consulta detalhada",
    "➕  Novo lançamento",
])

# ═══════════════════════════════════════════════════════════
# PAINEL
# ═══════════════════════════════════════════════════════════
with aba_painel:
    with st.sidebar:
        st.markdown("### Filtros")
        centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
        centro_sel = st.selectbox("Centro de custo", centros, key="p_centro")
        meses = sorted(
            [m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()],
            key=lambda x: int(x),
        )
        mes_sel = st.selectbox("Mês", ["Todos os meses"] + meses, key="p_mes")
        st.markdown("---")
        st.caption("🟢 OK 🟡 Atenção 🔴 Crítico")

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

    st.markdown('<p class="h1">Painel de Custos do RH</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="h1-sub">Exercício 2026 &nbsp;·&nbsp; {rotulo} &nbsp;·&nbsp; {centro_sel}</p>',
        unsafe_allow_html=True,
    )

    cor_saldo = "#047857" if saldo >= 0 else "#b91c1c"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">Orçamento</div>
        <div class="kpi-value">R$ {orc:,.2f}</div>
        <div class="kpi-hint">Valor previsto</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Realizado</div>
        <div class="kpi-value">R$ {real:,.2f}</div>
        <div class="kpi-hint">{pct:.1%} consumido</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Saldo</div>
        <div class="kpi-value" style="color:{cor_saldo}">R$ {saldo:,.2f}</div>
        <div class="kpi-hint">{'Dentro do orçamento' if saldo >= 0 else 'Acima do orçamento'}</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">Consumo</div>
        <div class="kpi-value">{pct:.1%}</div>
        <div class="kpi-hint">Realizado ÷ orçamento</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabela de contas
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

    def colorir(row):
        if row["Status"] == "Crítico":
            return ["background-color: #fef2f2; color: #7f1d1d"] * len(row)
        if row["Status"] == "Atenção":
            return ["background-color: #fffbeb; color: #78350f"] * len(row)
        return ["background-color: #ecfdf5; color: #064e3b"] * len(row)

    st.markdown('<p class="sec-title">Contas</p>', unsafe_allow_html=True)
    st.dataframe(
        tab[["Conta", "Orcado", "Realizado", "Saldo", "%", "Status"]].style.apply(colorir, axis=1).format({
            "Orcado": "R$ {:,.2f}",
            "Realizado": "R$ {:,.2f}",
            "Saldo": "R$ {:,.2f}",
            "%": "{:.1%}",
        }),
        use_container_width=True,
        height=440,
        hide_index=True,
    )

# ═══════════════════════════════════════════════════════════
# CONSULTA DETALHADA
# ═══════════════════════════════════════════════════════════
with aba_detalhe:
    st.markdown('<p class="h1">Consulta detalhada</p>', unsafe_allow_html=True)
    st.markdown('<p class="h1-sub">Pesquise uma conta e veja os lançamentos que a compõem.</p>', unsafe_allow_html=True)

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
        st.markdown(f'<p class="sec-title">Lançamentos · {conta_escolhida}</p>', unsafe_allow_html=True)

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
                    height=420,
                    hide_index=True,
                )
        else:
            st.info("Arquivo de detalhes não encontrado. Mostrando valores mensais da conta.")
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
    st.markdown('<p class="h1">Novo lançamento</p>', unsafe_allow_html=True)
    st.markdown('<p class="h1-sub">Registre entregas, consumos ou alocações de qualquer centro e conta.</p>', unsafe_allow_html=True)

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

        observacao = st.text_area("Observação (opcional)", height=80)
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

    st.markdown('<p class="sec-title">Histórico de lançamentos</p>', unsafe_allow_html=True)
    hist = carregar_lancamentos()
    if hist.empty:
        st.info("Nenhum lançamento registrado ainda.")
    else:
        st.dataframe(
            hist.sort_values("data_registro", ascending=False),
            use_container_width=True,
            height=340,
            hide_index=True,
        )
        st.download_button(
            "Baixar histórico (CSV)",
            data=hist.to_csv(index=False).encode("utf-8-sig"),
            file_name="lancamentos_rh.csv",
            mime="text/csv",
        )
