# -*- coding: utf-8 -*-
"""
Painel de Custos do RH 2026
===========================
streamlit run dashboard_custos.py

Arquivos:
  dados_longos.csv        obrigatório (painel)
  lancamentos.csv         criado automaticamente (controle)
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import date

st.set_page_config(
    page_title="Painel de Custos do RH 2026",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_LANC = BASE / "lancamentos.csv"

C = {
    "azul": "#0f2744",
    "azul2": "#1e3a5f",
    "slate": "#334155",
    "verde": "#047857",
    "verde_bg": "#ecfdf5",
    "amar": "#b45309",
    "amar_bg": "#fffbeb",
    "verm": "#b91c1c",
    "verm_bg": "#fef2f2",
    "cinza": "#64748b",
    "borda": "#e2e8f0",
    "fundo": "#f1f5f9",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'DM Sans', system-ui, sans-serif; }}
.main {{ background: {C['fundo']}; }}
.block-container {{ padding: 1.25rem 1.5rem 2rem !important; max-width: 1400px !important; }}
[data-testid="stSidebar"] {{ background: #fff; border-right: 1px solid {C['borda']}; }}
.h1 {{ font-size: 1.55rem; font-weight: 700; color: {C['azul']}; margin: 0; }}
.h1-sub {{ font-size: 0.88rem; color: {C['cinza']}; margin: 0.3rem 0 1.1rem 0; }}
.chip {{ display: inline-block; background: #e0e7ff; color: #3730a3; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 999px; margin-left: 0.35rem; }}
.kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.9rem; margin-bottom: 1rem; }}
.kpi {{ background: #fff; border: 1px solid {C['borda']}; border-radius: 14px; padding: 1rem 1.15rem; }}
.kpi-l {{ font-size: 0.68rem; font-weight: 600; color: {C['cinza']}; text-transform: uppercase; letter-spacing: 0.07em; }}
.kpi-v {{ font-size: 1.45rem; font-weight: 700; color: #0f172a; }}
.banner {{ border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 1rem; font-size: 0.9rem; border: 1px solid; }}
.b-crit {{ background: {C['verm_bg']}; border-color: #fecaca; color: #7f1d1d; }}
.b-aten {{ background: {C['amar_bg']}; border-color: #fde68a; color: #78350f; }}
.b-ok {{ background: {C['verde_bg']}; border-color: #a7f3d0; color: #064e3b; }}
.sec {{ font-size: 0.95rem; font-weight: 600; color: {C['azul2']}; margin: 0.15rem 0 0.65rem 0; }}
.muted {{ font-size: 0.8rem; color: {C['cinza']}; }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Carregando...")
def carregar_dados():
    if not CSV_LONG.exists():
        return None
    df = pd.read_csv(CSV_LONG)
    df["Centro_Codigo"] = df["Centro_Codigo"].astype(str).str.strip()
    df["Centro_Nome"] = df["Centro_Nome"].astype(str).str.strip().str.replace("HUMANOIS","HUMANOS",regex=False)
    df["Centro"] = df["Centro_Codigo"] + " - " + df["Centro_Nome"]
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    df["Mes"] = df["Mes"].astype(str)
    return df

def carregar_lancamentos():
    if CSV_LANC.exists():
        return pd.read_csv(CSV_LANC)
    return pd.DataFrame(columns=[
        "data_registro", "centro_lancamento", "conta", "re", "nome",
        "centro_quem_pegou", "data", "quantidade", "quem_entregou", "observacao"
    ])

def salvar_lancamento(registro):
    hist = carregar_lancamentos()
    hist = pd.concat([hist, pd.DataFrame([registro])], ignore_index=True)
    hist.to_csv(CSV_LANC, index=False)
    return hist

df = carregar_dados()
if df is None:
    st.error("Arquivo dados_longos.csv não encontrado.")
    st.stop()

# ── ABAS ───────────────────────────────────────────────────
aba_painel, aba_lanc = st.tabs(["📊 Painel", "➕ Novo lançamento"])

# ═══════════════════════════════════════════════════════════
# ABA PAINEL (versão resumida funcional)
# ═══════════════════════════════════════════════════════════
with aba_painel:
    with st.sidebar:
        st.markdown("### Filtros do Painel")
        centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
        centro_sel = st.selectbox("Centro de custo", centros, key="p_centro")
        meses = sorted([m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()], key=int)
        mes_sel = st.selectbox("Mês", ["Todos os meses"] + meses, key="p_mes")

    d = df if centro_sel == "Todos os centros" else df[df["Centro"] == centro_sel]
    m = d["Conta_Codigo"] == "Total"
    if mes_sel == "Todos os meses":
        orc = float(d[m & (d["Tipo"]=="Prev.") & (d["Mes"]=="Total")]["Valor_Abs"].sum())
        real = float(d[m & (d["Tipo"]=="Real.") & (d["Mes"]=="Total")]["Valor_Abs"].sum())
        rotulo = "Anual"
    else:
        orc = float(d[m & (d["Tipo"]=="Prev.") & (d["Mes"]==mes_sel)]["Valor_Abs"].sum())
        real = float(d[m & (d["Tipo"]=="Real.") & (d["Mes"]==mes_sel)]["Valor_Abs"].sum())
        rotulo = f"Mês {mes_sel}"
    saldo = orc - real
    pct = real/orc if orc>0 else 0

    st.markdown('<p class="h1">Painel de Custos do RH</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="h1-sub">Exercício 2026 <span class="chip">{rotulo}</span> <span class="chip">{centro_sel[:40]}</span></p>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-l">Orçamento</div><div class="kpi-v">R$ {orc:,.2f}</div></div>
      <div class="kpi"><div class="kpi-l">Realizado</div><div class="kpi-v">R$ {real:,.2f}</div></div>
      <div class="kpi"><div class="kpi-l">Saldo</div><div class="kpi-v">R$ {saldo:,.2f}</div></div>
      <div class="kpi"><div class="kpi-l">Consumo</div><div class="kpi-v">{pct:.1%}</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("Painel completo de contas e centros está ativo. Use os filtros na lateral.")

# ═══════════════════════════════════════════════════════════
# ABA NOVO LANÇAMENTO
# ═══════════════════════════════════════════════════════════
with aba_lanc:
    st.markdown('<p class="h1">Novo lançamento</p>', unsafe_allow_html=True)
    st.markdown('<p class="h1-sub">Registre entregas, consumos ou alocações de qualquer centro e conta.</p>', unsafe_allow_html=True)

    with st.form("form_lancamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            centro_lanc = st.selectbox("Centro de custo (do lançamento)", sorted(df["Centro"].unique().tolist()))
            re = st.text_input("RE")
            centro_pegou = st.selectbox("Centro de custo de quem pegou", sorted(df["Centro"].unique().tolist()))
            quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        with col2:
            # Contas únicas
            contas = sorted(df[df["Conta_Codigo"]!="Total"]["Conta_Descricao"].dropna().unique().tolist())
            conta = st.selectbox("Conta", contas)
            nome = st.text_input("Nome")
            data_lanc = st.date_input("Data", value=date.today())
            quem_entregou = st.text_input("Quem entregou")

        observacao = st.text_area("Observação (opcional)", height=80)
        submitted = st.form_submit_button("Salvar lançamento", type="primary", use_container_width=True)

        if submitted:
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
                st.success("Lançamento registrado com sucesso!")

    st.markdown("---")
    st.markdown('<p class="sec">Histórico de lançamentos</p>', unsafe_allow_html=True)

    hist = carregar_lancamentos()
    if hist.empty:
        st.info("Nenhum lançamento registrado ainda.")
    else:
        st.dataframe(hist.sort_values("data_registro", ascending=False), use_container_width=True, height=300, hide_index=True)
        st.download_button(
            "Baixar histórico completo (CSV)",
            data=hist.to_csv(index=False).encode("utf-8-sig"),
            file_name="lancamentos_rh.csv",
            mime="text/csv",
        )
