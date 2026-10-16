# -*- coding: utf-8 -*-
"""
Painel Gerencial de Custos 2026 — Streamlit
==========================================
Publicar: streamlit run dashboard_custos.py

Arquivos na mesma pasta:
  - dados_longos.csv          (obrigatório)
  - base_calculada.csv        (opcional — resumo por centro)
  - detalhes_longos.csv       (opcional — lançamentos analíticos)
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Painel de Custos 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",  # filtros sempre visíveis
)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_BASE = BASE / "base_calculada.csv"
CSV_DET = BASE / "detalhes_longos.csv"

# Cores
AZUL = "#1e3a5f"
AZUL_M = "#334155"
VERDE = "#059669"
VERDE_BG = "#ecfdf5"
AMAR = "#d97706"
AMAR_BG = "#fffbeb"
VERM = "#dc2626"
VERM_BG = "#fef2f2"
CINZA = "#64748b"
FUNDO = "#f8fafc"

st.markdown(
    f"""
<style>
    .main {{ background-color: {FUNDO}; }}
    .block-container {{ padding-top: 1.2rem !important; max-width: 1200px !important; }}
    [data-testid="stSidebar"] {{
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }}
    .hdr-title {{
        font-size: 1.6rem; font-weight: 700; color: {AZUL}; margin: 0;
        letter-spacing: -0.02em;
    }}
    .hdr-sub {{
        font-size: 0.9rem; color: {CINZA}; margin: 0.25rem 0 1.25rem 0;
    }}
    .kpi-grid {{
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
        margin-bottom: 1.25rem;
    }}
    .kpi {{
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 1.1rem 1.25rem; box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}
    .kpi-label {{
        font-size: 0.7rem; font-weight: 600; color: {CINZA};
        text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem;
    }}
    .kpi-val {{
        font-size: 1.55rem; font-weight: 700; color: #0f172a; line-height: 1.15;
    }}
    .kpi-hint {{ font-size: 0.8rem; margin-top: 0.35rem; color: {CINZA}; }}
    .alert-box {{
        border-radius: 10px; padding: 0.85rem 1.1rem; margin-bottom: 1rem;
        border: 1px solid; font-size: 0.9rem;
    }}
    .alert-crit {{ background: {VERM_BG}; border-color: #fecaca; color: #991b1b; }}
    .alert-aten {{ background: {AMAR_BG}; border-color: #fde68a; color: #92400e; }}
    .alert-ok {{ background: {VERDE_BG}; border-color: #a7f3d0; color: #065f46; }}
    .sec-title {{
        font-size: 1.05rem; font-weight: 600; color: {AZUL_M};
        margin: 0.5rem 0 0.75rem 0;
    }}
    div[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# DADOS
# ═══════════════════════════════════════════════════════════
@st.cache_data
def carregar():
    if not CSV_LONG.exists():
        return None, None, None
    df = pd.read_csv(CSV_LONG)
    df["Centro_Codigo"] = df["Centro_Codigo"].astype(str).str.strip()
    df["Centro_Nome"] = df["Centro_Nome"].astype(str).str.strip()
    df["Centro"] = df["Centro_Codigo"] + " - " + df["Centro_Nome"]
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    df["Mes"] = df["Mes"].astype(str)

    base = None
    if CSV_BASE.exists():
        base = pd.read_csv(CSV_BASE)
        if "Centro" not in base.columns and "Centro_Codigo" in base.columns:
            base["Centro"] = (
                base["Centro_Codigo"].astype(str) + " - " + base["Centro_Nome"].astype(str)
            )

    det = None
    if CSV_DET.exists():
        det = pd.read_csv(CSV_DET)
        det["Centro_Codigo"] = det["Centro_Codigo"].astype(str).str.strip()
        det["Conta_Codigo"] = det["Conta_Codigo"].astype(str).str.strip()
        det["Valor"] = pd.to_numeric(det["Valor"], errors="coerce").fillna(0)
        if "Mes_Trans" in det.columns:
            det["Mes_Trans"] = pd.to_numeric(det["Mes_Trans"], errors="coerce").fillna(0).astype(int)

    return df, base, det


df, base, det = carregar()
if df is None:
    st.error(
        "**dados_longos.csv** não encontrado nesta pasta.\n\n"
        "Rode o script de atualização mensal e publique o CSV junto com o app."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════
# FILTROS (sidebar sempre aberta)
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Filtros")
    st.caption("Escolha centro e período. Tudo na tela atualiza na hora.")

    centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
    centro_sel = st.selectbox("Centro de custo", centros, index=0)

    meses = sorted(
        [m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()],
        key=lambda x: int(x),
    )
    mes_sel = st.selectbox("Mês", ["Todos os meses"] + meses, index=0)

    st.markdown("---")
    st.markdown("**Status das contas**")
    st.markdown(
        f"""
<span style="color:{VERDE}">●</span> **OK** — abaixo de 80%<br>
<span style="color:{AMAR}">●</span> **Atenção** — 80% a 100%<br>
<span style="color:{VERM}">●</span> **Crítico** — acima de 100% ou saldo negativo
""",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("Cada centro é analisado isoladamente. Não compare estruturas diferentes entre si.")


# ═══════════════════════════════════════════════════════════
# CÁLCULOS
# ═══════════════════════════════════════════════════════════
d = df.copy()
if centro_sel != "Todos os centros":
    d = d[d["Centro"] == centro_sel]

# Totais do centro (linha Total)
mask_tot = d["Conta_Codigo"] == "Total"
d_prev_a = d[mask_tot & (d["Tipo"] == "Prev.") & (d["Mes"] == "Total")]
d_real_a = d[mask_tot & (d["Tipo"] == "Real.") & (d["Mes"] == "Total")]
orc_anual = float(d_prev_a["Valor_Abs"].sum())
real_anual = float(d_real_a["Valor_Abs"].sum())
saldo_anual = orc_anual - real_anual
pct_anual = real_anual / orc_anual if orc_anual > 0 else 0.0

visao_mensal = mes_sel != "Todos os meses"
if visao_mensal:
    d_prev_m = d[mask_tot & (d["Tipo"] == "Prev.") & (d["Mes"] == mes_sel)]
    d_real_m = d[mask_tot & (d["Tipo"] == "Real.") & (d["Mes"] == mes_sel)]
    orc_ref = float(d_prev_m["Valor_Abs"].sum())
    real_ref = float(d_real_m["Valor_Abs"].sum())
    saldo_ref = orc_ref - real_ref
    pct_ref = real_ref / orc_ref if orc_ref > 0 else 0.0
    rotulo = f"Mês {mes_sel}"
else:
    orc_ref, real_ref, saldo_ref, pct_ref = orc_anual, real_anual, saldo_anual, pct_anual
    rotulo = "Anual"


def status_conta(orc, real, saldo, pct):
    if saldo < 0 or (orc == 0 and real > 0) or pct >= 1:
        return "Crítico"
    if pct >= 0.8:
        return "Atenção"
    return "OK"


def montar_contas_por_centro(frame, mes):
    """Tabela de contas de UM centro (nunca mistura centros)."""
    c = frame[frame["Conta_Codigo"] != "Total"].copy()
    if mes == "Todos os meses":
        prev = (
            c[(c["Tipo"] == "Prev.") & (c["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum()
            .rename(columns={"Valor_Abs": "Orcado"})
        )
        real = (
            c[(c["Tipo"] == "Real.") & (c["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum()
            .rename(columns={"Valor_Abs": "Realizado"})
        )
    else:
        prev = (
            c[(c["Tipo"] == "Prev.") & (c["Mes"] == mes)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum()
            .rename(columns={"Valor_Abs": "Orcado"})
        )
        real = (
            c[(c["Tipo"] == "Real.") & (c["Mes"] == mes)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"]
            .sum()
            .rename(columns={"Valor_Abs": "Realizado"})
        )

    t = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
    t["Saldo"] = t["Orcado"] - t["Realizado"]
    t["Pct"] = t.apply(
        lambda r: r["Realizado"] / r["Orcado"]
        if r["Orcado"] > 0
        else (1.0 if r["Realizado"] > 0 else 0.0),
        axis=1,
    )
    t["Status"] = t.apply(
        lambda r: status_conta(r["Orcado"], r["Realizado"], r["Saldo"], r["Pct"]), axis=1
    )
    # Esconde linhas sem movimento
    t = t[~((t["Orcado"] == 0) & (t["Realizado"] == 0))]
    t["Conta"] = t["Conta_Codigo"].astype(str).str.zfill(10) + " | " + t["Conta_Descricao"].astype(str)
    # Críticos primeiro, depois atenção, depois maior realizado
    ordem = {"Crítico": 0, "Atenção": 1, "OK": 2}
    t["_ord"] = t["Status"].map(ordem)
    t = t.sort_values(["_ord", "Realizado"], ascending=[True, False]).drop(columns="_ord")
    return t


def montar_resumo_centros(frame, mes):
    """Uma linha por centro — visão consolidada sem misturar contas."""
    rows = []
    for centro in sorted(frame["Centro"].unique()):
        sub = frame[frame["Centro"] == centro]
        m_tot = sub["Conta_Codigo"] == "Total"
        if mes == "Todos os meses":
            orc = float(sub[m_tot & (sub["Tipo"] == "Prev.") & (sub["Mes"] == "Total")]["Valor_Abs"].sum())
            real = float(sub[m_tot & (sub["Tipo"] == "Real.") & (sub["Mes"] == "Total")]["Valor_Abs"].sum())
        else:
            orc = float(sub[m_tot & (sub["Tipo"] == "Prev.") & (sub["Mes"] == mes)]["Valor_Abs"].sum())
            real = float(sub[m_tot & (sub["Tipo"] == "Real.") & (sub["Mes"] == mes)]["Valor_Abs"].sum())
        saldo = orc - real
        pct = real / orc if orc > 0 else (1.0 if real > 0 else 0.0)
        rows.append(
            {
                "Centro": centro,
                "Orcado": orc,
                "Realizado": real,
                "Saldo": saldo,
                "Pct": pct,
                "Status": status_conta(orc, real, saldo, pct),
            }
        )
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════
# CABEÇALHO
# ═══════════════════════════════════════════════════════════
st.markdown('<p class="hdr-title">Painel Gerencial de Custos · 2026</p>', unsafe_allow_html=True)
filtro_txt = f"{centro_sel}  ·  {mes_sel}"
st.markdown(
    f'<p class="hdr-sub">Acompanhamento orçamentário por centro de custo. Filtro ativo: <b>{filtro_txt}</b></p>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════
cor_saldo = VERDE if saldo_ref >= 0 else VERM
txt_saldo = "Dentro do orçamento" if saldo_ref >= 0 else "Acima do orçamento"

st.markdown(
    f"""
<div class="kpi-grid">
  <div class="kpi">
    <div class="kpi-label">Orçamento · {rotulo}</div>
    <div class="kpi-val">R$ {orc_ref:,.2f}</div>
    <div class="kpi-hint">Valor orçado no período</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Realizado · {rotulo}</div>
    <div class="kpi-val">R$ {real_ref:,.2f}</div>
    <div class="kpi-hint">{pct_ref:.1%} do orçamento</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Saldo · {rotulo}</div>
    <div class="kpi-val" style="color:{cor_saldo}">R$ {saldo_ref:,.2f}</div>
    <div class="kpi-hint" style="color:{cor_saldo}">{txt_saldo}</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Consumo · {rotulo}</div>
    <div class="kpi-val">{pct_ref:.1%}</div>
    <div class="kpi-hint">Percentual utilizado</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# KPIs anuais de apoio quando visão é mensal
if visao_mensal and centro_sel != "Todos os centros":
    with st.expander(f"Referência anual do centro (até o acumulado disponível)", expanded=False):
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Orçamento anual", f"R$ {orc_anual:,.2f}")
        a2.metric("Realizado acum.", f"R$ {real_anual:,.2f}")
        a3.metric("Saldo anual", f"R$ {saldo_anual:,.2f}")
        a4.metric("% anual", f"{pct_anual:.1%}")


# ═══════════════════════════════════════════════════════════
# ALERTAS
# ═══════════════════════════════════════════════════════════
if centro_sel == "Todos os centros":
    resumo = montar_resumo_centros(df, mes_sel)
    n_crit = int((resumo["Status"] == "Crítico").sum())
    n_aten = int((resumo["Status"] == "Atenção").sum())
    if n_crit:
        st.markdown(
            f'<div class="alert-box alert-crit"><b>{n_crit} centro(s) em situação crítica</b> no filtro atual. '
            f"Selecione o centro na barra lateral para ver as contas.</div>",
            unsafe_allow_html=True,
        )
    elif n_aten:
        st.markdown(
            f'<div class="alert-box alert-aten"><b>{n_aten} centro(s) em atenção</b> (≥ 80% consumido).</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="alert-box alert-ok">Nenhum centro crítico no filtro atual.</div>',
            unsafe_allow_html=True,
        )
else:
    tab = montar_contas_por_centro(d, mes_sel)
    n_crit = int((tab["Status"] == "Crítico").sum())
    n_aten = int((tab["Status"] == "Atenção").sum())
    if n_crit:
        top = tab[tab["Status"] == "Crítico"].head(3)["Conta"].tolist()
        nomes = "; ".join(top)
        st.markdown(
            f'<div class="alert-box alert-crit"><b>{n_crit} conta(s) crítica(s)</b>'
            f"{' — ex.: ' + nomes if top else ''}.</div>",
            unsafe_allow_html=True,
        )
    elif n_aten:
        st.markdown(
            f'<div class="alert-box alert-aten"><b>{n_aten} conta(s) em atenção</b> (≥ 80%).</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="alert-box alert-ok">Nenhuma conta crítica neste centro/período.</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════
# GRÁFICO + TABELA
# ═══════════════════════════════════════════════════════════
col_g, col_t = st.columns([2, 3], gap="large")

with col_g:
    st.markdown(f'<p class="sec-title">Composição do orçamento · {rotulo}</p>', unsafe_allow_html=True)
    gasto = real_ref
    disponivel = max(0.0, saldo_ref)
    estouro = max(0.0, -saldo_ref)
    pie = pd.DataFrame(
        {"Fatia": ["Realizado", "Disponível", "Estouro"], "Valor": [gasto, disponivel, estouro]}
    )
    pie = pie[pie["Valor"] > 0]
    if pie.empty:
        st.info("Sem valores para o gráfico neste filtro.")
    else:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=pie["Fatia"],
                    values=pie["Valor"],
                    hole=0.55,
                    marker_colors=[
                        AZUL_M if f == "Realizado" else VERDE if f == "Disponível" else VERM
                        for f in pie["Fatia"]
                    ],
                    textinfo="percent",
                    textposition="inside",
                    hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>",
                )
            ]
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
        )
        st.plotly_chart(fig, use_container_width=True)

with col_t:
    if centro_sel == "Todos os centros":
        st.markdown(
            f'<p class="sec-title">Resumo por centro de custo · {rotulo}</p>',
            unsafe_allow_html=True,
        )
        st.caption("Visão consolidada: um centro por linha. Selecione um centro para ver as contas.")
        resumo = montar_resumo_centros(df, mes_sel)
        ordem = {"Crítico": 0, "Atenção": 1, "OK": 2}
        resumo["_o"] = resumo["Status"].map(ordem)
        resumo = resumo.sort_values(["_o", "Realizado"], ascending=[True, False]).drop(columns="_o")

        def cor_res(row):
            if row["Status"] == "Crítico":
                return [f"background-color: {VERM_BG}; color: #991b1b"] * len(row)
            if row["Status"] == "Atenção":
                return [f"background-color: {AMAR_BG}; color: #92400e"] * len(row)
            return [f"background-color: {VERDE_BG}; color: #065f46"] * len(row)

        show = resumo.rename(columns={"Pct": "% Consumido"})[
            ["Centro", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]
        ]
        st.dataframe(
            show.style.apply(cor_res, axis=1).format(
                {
                    "Orcado": "R$ {:,.2f}",
                    "Realizado": "R$ {:,.2f}",
                    "Saldo": "R$ {:,.2f}",
                    "% Consumido": "{:.1%}",
                }
            ),
            use_container_width=True,
            height=340,
            hide_index=True,
        )
    else:
        st.markdown(
            f'<p class="sec-title">Contas · {centro_sel.split(" - ")[0]} · {rotulo}</p>',
            unsafe_allow_html=True,
        )
        tab = montar_contas_por_centro(d, mes_sel)

        def cor_tab(row):
            if row["Status"] == "Crítico":
                return [f"background-color: {VERM_BG}; color: #991b1b"] * len(row)
            if row["Status"] == "Atenção":
                return [f"background-color: {AMAR_BG}; color: #92400e"] * len(row)
            return [f"background-color: {VERDE_BG}; color: #065f46"] * len(row)

        show = tab.rename(columns={"Pct": "% Consumido"})[
            ["Conta", "Orcado", "Realizado", "Saldo", "% Consumido", "Status"]
        ]
        st.dataframe(
            show.style.apply(cor_tab, axis=1).format(
                {
                    "Orcado": "R$ {:,.2f}",
                    "Realizado": "R$ {:,.2f}",
                    "Saldo": "R$ {:,.2f}",
                    "% Consumido": "{:.1%}",
                }
            ),
            use_container_width=True,
            height=340,
            hide_index=True,
        )


# ═══════════════════════════════════════════════════════════
# DETALHE DE LANÇAMENTOS (se houver detalhes_longos.csv)
# ═══════════════════════════════════════════════════════════
if centro_sel != "Todos os centros" and det is not None and not det.empty:
    st.markdown("---")
    st.markdown('<p class="sec-title">Lançamentos analíticos</p>', unsafe_allow_html=True)
    st.caption("Opcional: escolha uma conta para ver documentos/itens (quando o arquivo de detalhes existir).")

    tab = montar_contas_por_centro(d, mes_sel)
    opcoes = ["—"] + tab["Conta"].tolist()
    conta_sel = st.selectbox("Conta", opcoes, index=0)

    if conta_sel != "—":
        cod = conta_sel.split(" | ")[0].lstrip("0")
        c_codigo = centro_sel.split(" - ")[0].strip()
        det_f = det[det["Centro_Codigo"] == c_codigo].copy()
        det_f = det_f[det_f["Conta_Codigo"].astype(str).str.lstrip("0") == cod]
        if visao_mensal and "Mes_Trans" in det_f.columns:
            det_f = det_f[det_f["Mes_Trans"] == int(mes_sel)]
        cols = [c for c in ["DOC", "Data", "Clifor", "Item", "Valor"] if c in det_f.columns]
        if det_f.empty or not cols:
            st.info("Nenhum lançamento encontrado para esta conta com os filtros atuais.")
        else:
            st.dataframe(
                det_f[cols].sort_values("Valor", ascending=False).style.format({"Valor": "R$ {:,.2f}"}),
                use_container_width=True,
                height=280,
                hide_index=True,
            )


# ═══════════════════════════════════════════════════════════
# RODAPÉ
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.caption(
    "Painel Gerencial de Custos 2026 · Dados a partir dos relatórios mensais de centro de custo. "
    "Atualize o CSV no repositório para refrescar este painel."
)
