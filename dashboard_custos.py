# -*- coding: utf-8 -*-
"""
Painel Gerencial de Custos 2026
================================
streamlit run dashboard_custos.py

Arquivos na mesma pasta:
  dados_longos.csv        obrigatório
  base_calculada.csv      opcional
  detalhes_longos.csv     opcional
"""

from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Painel de Custos 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
CSV_LONG = BASE / "dados_longos.csv"
CSV_BASE = BASE / "base_calculada.csv"
CSV_DET = BASE / "detalhes_longos.csv"

# ── Design tokens ──────────────────────────────────────────
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
    "card": "#ffffff",
}

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', system-ui, sans-serif;
}}
.main {{ background: {C['fundo']}; }}
.block-container {{
    padding: 1.25rem 1.5rem 2rem !important;
    max-width: 1400px !important;
}}
[data-testid="stSidebar"] {{
    background: {C['card']};
    border-right: 1px solid {C['borda']};
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    font-size: 0.9rem;
}}
section[data-testid="stSidebar"] .stSelectbox label {{
    font-weight: 600; color: {C['slate']}; font-size: 0.85rem;
}}

/* Header */
.h1 {{
    font-size: 1.55rem; font-weight: 700; color: {C['azul']};
    margin: 0; letter-spacing: -0.03em; line-height: 1.2;
}}
.h1-sub {{
    font-size: 0.88rem; color: {C['cinza']}; margin: 0.3rem 0 1.1rem 0;
}}
.chip {{
    display: inline-block; background: #e0e7ff; color: #3730a3;
    font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.55rem;
    border-radius: 999px; margin-left: 0.35rem;
}}

/* KPI */
.kpi-row {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.9rem;
    margin-bottom: 1rem;
}}
.kpi {{
    background: {C['card']}; border: 1px solid {C['borda']};
    border-radius: 14px; padding: 1rem 1.15rem;
    box-shadow: 0 1px 3px rgba(15,23,42,.04);
}}
.kpi-l {{
    font-size: 0.68rem; font-weight: 600; color: {C['cinza']};
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.35rem;
}}
.kpi-v {{
    font-size: 1.45rem; font-weight: 700; color: #0f172a; line-height: 1.15;
}}
.kpi-h {{ font-size: 0.78rem; margin-top: 0.3rem; color: {C['cinza']}; }}

/* Alerts */
.banner {{
    border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 1rem;
    font-size: 0.9rem; border: 1px solid; display: flex; gap: 0.6rem; align-items: flex-start;
}}
.b-crit {{ background: {C['verm_bg']}; border-color: #fecaca; color: #7f1d1d; }}
.b-aten {{ background: {C['amar_bg']}; border-color: #fde68a; color: #78350f; }}
.b-ok   {{ background: {C['verde_bg']}; border-color: #a7f3d0; color: #064e3b; }}

.sec {{
    font-size: 0.95rem; font-weight: 600; color: {C['azul2']};
    margin: 0.15rem 0 0.65rem 0;
}}
.muted {{ font-size: 0.8rem; color: {C['cinza']}; margin-bottom: 0.5rem; }}

/* Status pills in caption */
.leg span {{ margin-right: 0.85rem; font-size: 0.8rem; }}

div[data-testid="stDataFrame"] {{
    border: 1px solid {C['borda']}; border-radius: 12px; overflow: hidden;
}}
footer {{ visibility: hidden; }}
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Carregando dados…")
def carregar():
    if not CSV_LONG.exists():
        return None, None, None
    df = pd.read_csv(CSV_LONG)
    df["Centro_Codigo"] = df["Centro_Codigo"].astype(str).str.strip()
    df["Centro_Nome"] = (
        df["Centro_Nome"].astype(str).str.strip()
        .str.replace("HUMANOIS", "HUMANOS", regex=False)
        .str.replace("SELEÇÃPOmes 10", "SELEÇÃO", regex=False)
        .str.replace("SELEÇÃOmes 10", "SELEÇÃO", regex=False)
    )
    df["Centro"] = df["Centro_Codigo"] + " - " + df["Centro_Nome"]
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    df["Mes"] = df["Mes"].astype(str)

    base = pd.read_csv(CSV_BASE) if CSV_BASE.exists() else None
    if base is not None and "Centro" not in base.columns and "Centro_Codigo" in base.columns:
        base["Centro"] = base["Centro_Codigo"].astype(str) + " - " + base["Centro_Nome"].astype(str)

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
    st.error("**dados_longos.csv** não encontrado. Inclua o arquivo na pasta do app / repositório.")
    st.stop()


def status_de(orc, real, saldo, pct):
    if saldo < 0 or (orc <= 0 and real > 0) or pct >= 1:
        return "Crítico"
    if pct >= 0.8:
        return "Atenção"
    return "OK"


def totais_periodo(frame, mes):
    """Orçado/realizado da linha Total."""
    m = frame["Conta_Codigo"] == "Total"
    if mes == "Todos os meses":
        orc = float(frame[m & (frame["Tipo"] == "Prev.") & (frame["Mes"] == "Total")]["Valor_Abs"].sum())
        real = float(frame[m & (frame["Tipo"] == "Real.") & (frame["Mes"] == "Total")]["Valor_Abs"].sum())
    else:
        orc = float(frame[m & (frame["Tipo"] == "Prev.") & (frame["Mes"] == mes)]["Valor_Abs"].sum())
        real = float(frame[m & (frame["Tipo"] == "Real.") & (frame["Mes"] == mes)]["Valor_Abs"].sum())
    saldo = orc - real
    pct = real / orc if orc > 0 else (1.0 if real > 0 else 0.0)
    return orc, real, saldo, pct


def tabela_contas(frame, mes):
    c = frame[frame["Conta_Codigo"] != "Total"].copy()
    if mes == "Todos os meses":
        prev = (
            c[(c["Tipo"] == "Prev.") & (c["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum()
            .rename(columns={"Valor_Abs": "Orcado"})
        )
        real = (
            c[(c["Tipo"] == "Real.") & (c["Mes"] == "Total")]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum()
            .rename(columns={"Valor_Abs": "Realizado"})
        )
    else:
        prev = (
            c[(c["Tipo"] == "Prev.") & (c["Mes"] == mes)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum()
            .rename(columns={"Valor_Abs": "Orcado"})
        )
        real = (
            c[(c["Tipo"] == "Real.") & (c["Mes"] == mes)]
            .groupby(["Conta_Codigo", "Conta_Descricao"], as_index=False)["Valor_Abs"].sum()
            .rename(columns={"Valor_Abs": "Realizado"})
        )
    t = prev.merge(real, on=["Conta_Codigo", "Conta_Descricao"], how="outer").fillna(0)
    t["Saldo"] = t["Orcado"] - t["Realizado"]
    t["%"] = t.apply(
        lambda r: r["Realizado"] / r["Orcado"] if r["Orcado"] > 0 else (1.0 if r["Realizado"] > 0 else 0.0),
        axis=1,
    )
    t["Status"] = t.apply(lambda r: status_de(r["Orcado"], r["Realizado"], r["Saldo"], r["%"]), axis=1)
    t = t[~((t["Orcado"] == 0) & (t["Realizado"] == 0))]
    t["Conta"] = t["Conta_Codigo"].astype(str).str.zfill(10) + " | " + t["Conta_Descricao"].astype(str)
    ord_map = {"Crítico": 0, "Atenção": 1, "OK": 2}
    t["_"] = t["Status"].map(ord_map)
    return t.sort_values(["_", "Realizado"], ascending=[True, False]).drop(columns="_")


def resumo_centros(frame, mes):
    rows = []
    for centro in sorted(frame["Centro"].unique()):
        orc, real, saldo, pct = totais_periodo(frame[frame["Centro"] == centro], mes)
        rows.append({
            "Centro": centro, "Orcado": orc, "Realizado": real,
            "Saldo": saldo, "%": pct, "Status": status_de(orc, real, saldo, pct),
        })
    t = pd.DataFrame(rows)
    ord_map = {"Crítico": 0, "Atenção": 1, "OK": 2}
    t["_"] = t["Status"].map(ord_map)
    return t.sort_values(["_", "Realizado"], ascending=[True, False]).drop(columns="_")


def serie_mensal(frame):
    """Realizado e orçado por mês (linha Total)."""
    m = frame[(frame["Conta_Codigo"] == "Total") & (frame["Mes"] != "Total")].copy()
    m = m[m["Mes"].str.isdigit()]
    piv = (
        m.pivot_table(index="Mes", columns="Tipo", values="Valor_Abs", aggfunc="sum")
        .reindex([f"{i:02d}" for i in range(1, 13)])
        .fillna(0)
    )
    return piv


def style_status(df_show):
    def row_style(row):
        s = row.get("Status", "")
        if s == "Crítico":
            return [f"background-color: {C['verm_bg']}; color: #7f1d1d"] * len(row)
        if s == "Atenção":
            return [f"background-color: {C['amar_bg']}; color: #78350f"] * len(row)
        return [f"background-color: {C['verde_bg']}; color: #064e3b"] * len(row)

    return df_show.style.apply(row_style, axis=1).format({
        "Orcado": "R$ {:,.2f}",
        "Realizado": "R$ {:,.2f}",
        "Saldo": "R$ {:,.2f}",
        "%": "{:.1%}",
    })


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Filtros")
    st.caption("Alterar centro ou mês atualiza todo o painel.")

    centros = ["Todos os centros"] + sorted(df["Centro"].unique().tolist())
    # Preferir 247 se existir
    default_i = 0
    for i, c in enumerate(centros):
        if c.startswith("247"):
            default_i = i
            break
    centro_sel = st.selectbox("Centro de custo", centros, index=default_i)

    meses = sorted(
        [m for m in df["Mes"].unique() if m != "Total" and str(m).isdigit()],
        key=int,
    )
    mes_sel = st.selectbox("Mês", ["Todos os meses"] + meses)

    st.markdown("---")
    st.markdown(
        f"""
<div class="leg">
<span style="color:{C['verde']}">● OK</span>
<span style="color:{C['amar']}">● Atenção ≥80%</span>
<span style="color:{C['verm']}">● Crítico</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption("Cada centro é analisado de forma isolada.")


# ═══════════════════════════════════════════════════════════
# FILTRO + MÉTRICAS
# ═══════════════════════════════════════════════════════════
d = df if centro_sel == "Todos os centros" else df[df["Centro"] == centro_sel]
orc, real, saldo, pct = totais_periodo(d, mes_sel)
rotulo = "Anual" if mes_sel == "Todos os meses" else f"Mês {mes_sel}"
visao_todos = centro_sel == "Todos os centros"

# Header
st.markdown('<p class="h1">Painel Gerencial de Custos</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="h1-sub">Exercício 2026'
    f'<span class="chip">{rotulo}</span>'
    f'<span class="chip">{centro_sel if len(centro_sel) < 42 else centro_sel[:40]+"…"}</span></p>',
    unsafe_allow_html=True,
)

# KPIs
cor_s = C["verde"] if saldo >= 0 else C["verm"]
txt_s = "Dentro do orçamento" if saldo >= 0 else "Acima do orçamento"
st.markdown(
    f"""
<div class="kpi-row">
  <div class="kpi">
    <div class="kpi-l">Orçamento · {rotulo}</div>
    <div class="kpi-v">R$ {orc:,.2f}</div>
    <div class="kpi-h">Valor previsto</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Realizado · {rotulo}</div>
    <div class="kpi-v">R$ {real:,.2f}</div>
    <div class="kpi-h">{pct:.1%} consumido</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Saldo · {rotulo}</div>
    <div class="kpi-v" style="color:{cor_s}">R$ {saldo:,.2f}</div>
    <div class="kpi-h" style="color:{cor_s}">{txt_s}</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Taxa de consumo</div>
    <div class="kpi-v">{pct:.1%}</div>
    <div class="kpi-h">Realizado ÷ orçamento</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Banner
if visao_todos:
    res = resumo_centros(df, mes_sel)
    nc, na = int((res["Status"] == "Crítico").sum()), int((res["Status"] == "Atenção").sum())
    if nc:
        st.markdown(
            f'<div class="banner b-crit"><span>⚠</span><div><b>{nc} centro(s) crítico(s)</b> neste período. '
            f"Abra o centro na barra lateral para ver as contas.</div></div>",
            unsafe_allow_html=True,
        )
    elif na:
        st.markdown(
            f'<div class="banner b-aten"><span>●</span><div><b>{na} centro(s) em atenção</b> (≥ 80% do orçamento).</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="banner b-ok"><span>✓</span><div>Nenhum centro em situação crítica neste filtro.</div></div>',
            unsafe_allow_html=True,
        )
else:
    tab = tabela_contas(d, mes_sel)
    nc, na = int((tab["Status"] == "Crítico").sum()), int((tab["Status"] == "Atenção").sum())
    if nc:
        ex = "; ".join(tab[tab["Status"] == "Crítico"].head(2)["Conta"].str.split(" | ").str[-1].tolist())
        st.markdown(
            f'<div class="banner b-crit"><span>⚠</span><div><b>{nc} conta(s) crítica(s)</b>'
            f"{' — ' + ex if ex else ''}.</div></div>",
            unsafe_allow_html=True,
        )
    elif na:
        st.markdown(
            f'<div class="banner b-aten"><span>●</span><div><b>{na} conta(s) em atenção</b> (≥ 80%).</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="banner b-ok"><span>✓</span><div>Nenhuma conta crítica neste centro e período.</div></div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════
# LINHA DO TEMPO (quando 1 centro)
# ═══════════════════════════════════════════════════════════
if not visao_todos:
    serie = serie_mensal(d)
    if "Real." in serie.columns or "Prev." in serie.columns:
        st.markdown('<p class="sec">Evolução mensal do centro</p>', unsafe_allow_html=True)
        fig_l = go.Figure()
        if "Prev." in serie.columns:
            fig_l.add_trace(go.Scatter(
                x=serie.index, y=serie["Prev."], name="Orçado",
                mode="lines+markers", line=dict(color="#94a3b8", width=2, dash="dot"),
                marker=dict(size=6),
            ))
        if "Real." in serie.columns:
            fig_l.add_trace(go.Scatter(
                x=serie.index, y=serie["Real."], name="Realizado",
                mode="lines+markers", line=dict(color=C["azul2"], width=2.5),
                marker=dict(size=6),
                fill="tozeroy", fillcolor="rgba(30,58,95,0.08)",
            ))
        fig_l.update_layout(
            height=220, margin=dict(t=8, b=8, l=8, r=8),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.12, x=0),
            xaxis=dict(title="", gridcolor="#e2e8f0", tickfont=dict(size=11)),
            yaxis=dict(title="", gridcolor="#e2e8f0", tickprefix="R$ ", tickfont=dict(size=11)),
            hovermode="x unified",
        )
        st.plotly_chart(fig_l, use_container_width=True)


# ═══════════════════════════════════════════════════════════
# DONUT + TABELA
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
# DONUT + TABELA (tabela em largura total — sem rolagem lateral)
# ═══════════════════════════════════════════════════════════
g1, g2 = st.columns([1, 1], gap="large")

with g1:
    st.markdown(f'<p class="sec">Composição · {rotulo}</p>', unsafe_allow_html=True)
    labels, values, colors = [], [], []
    if real > 0:
        labels.append("Realizado"); values.append(real); colors.append(C["slate"])
    if saldo > 0:
        labels.append("Disponível"); values.append(saldo); colors.append(C["verde"])
    if saldo < 0:
        labels.append("Estouro"); values.append(-saldo); colors.append(C["verm"])
    if values:
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.62,
            marker=dict(colors=colors, line=dict(color="#fff", width=2)),
            textinfo="percent", textposition="inside",
            hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            height=260, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center", font=dict(size=12)),
            annotations=[dict(
                text=f"<b>{pct:.0%}</b><br><span style='font-size:11px'>consumido</span>",
                x=0.5, y=0.5, font=dict(size=16, color=C["azul"]), showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem valores para o gráfico.")

with g2:
    st.markdown(f'<p class="sec">Leitura rápida · {rotulo}</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:1.1rem 1.25rem;">
  <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.5rem;">Síntese do filtro</div>
  <div style="font-size:1.05rem;font-weight:600;color:#0f172a;margin-bottom:0.35rem;">
    Orçado R$ {orc:,.2f} · Realizado R$ {real:,.2f}
  </div>
  <div style="font-size:0.9rem;color:{'#047857' if saldo>=0 else '#b91c1c'};">
    Saldo R$ {saldo:,.2f} ({pct:.1%} consumido)
  </div>
  <div style="font-size:0.8rem;color:#64748b;margin-top:0.75rem;">
    Use a tabela abaixo para detalhar centros ou contas. Críticos aparecem primeiro.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# Tabela em largura total
st.markdown("")
if visao_todos:
    st.markdown(f'<p class="sec">Centros de custo · {rotulo}</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="muted">Um centro por linha. Selecione um centro na lateral para abrir as contas.</p>',
        unsafe_allow_html=True,
    )
    show = resumo_centros(df, mes_sel)[["Centro", "Orcado", "Realizado", "Saldo", "%", "Status"]]
    st.dataframe(
        style_status(show),
        use_container_width=True,
        height=min(56 + 38 * max(len(show), 1), 420),
        hide_index=True,
        column_config={
            "Centro": st.column_config.TextColumn("Centro de custo", width="large"),
            "Orcado": st.column_config.NumberColumn("Orçado", width="medium"),
            "Realizado": st.column_config.NumberColumn("Realizado", width="medium"),
            "Saldo": st.column_config.NumberColumn("Saldo", width="medium"),
            "%": st.column_config.NumberColumn("%", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )
else:
    st.markdown(
        f'<p class="sec">Contas · {centro_sel.split(" - ")[0]} · {rotulo}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="muted">Ordenado por criticidade. Contas sem movimento ocultas.</p>',
        unsafe_allow_html=True,
    )
    tab = tabela_contas(d, mes_sel)
    show = tab[["Conta", "Orcado", "Realizado", "Saldo", "%", "Status"]]
    st.dataframe(
        style_status(show),
        use_container_width=True,
        height=min(56 + 36 * max(len(show), 1), 480),
        hide_index=True,
        column_config={
            "Conta": st.column_config.TextColumn("Conta", width="large"),
            "Orcado": st.column_config.NumberColumn("Orçado", width="medium"),
            "Realizado": st.column_config.NumberColumn("Realizado", width="medium"),
            "Saldo": st.column_config.NumberColumn("Saldo", width="medium"),
            "%": st.column_config.NumberColumn("%", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )
    csv_bytes = show.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Baixar contas (CSV)",
        data=csv_bytes,
        file_name=f"contas_{centro_sel.split(' - ')[0]}_{mes_sel}.csv",
        mime="text/csv",
    )

# ═══════════════════════════════════════════════════════════
# TOP CRÍTICOS (lista curta)
# ═══════════════════════════════════════════════════════════
if not visao_todos:
    tab = tabela_contas(d, mes_sel)
    criticos = tab[tab["Status"].isin(["Crítico", "Atenção"])]
    if len(criticos):
        with st.expander(f"Contas que exigem atenção ({len(criticos)})", expanded=nc > 0):
            for _, r in criticos.iterrows():
                cor = C["verm"] if r["Status"] == "Crítico" else C["amar"]
                st.markdown(
                    f"<span style='color:{cor};font-weight:600'>{r['Status']}</span> · "
                    f"**{r['Conta'].split(' | ')[-1]}** — "
                    f"Realizado R$ {r['Realizado']:,.2f} / Orçado R$ {r['Orcado']:,.2f} "
                    f"({r['%']:.0%})",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════
# LANÇAMENTOS
# ═══════════════════════════════════════════════════════════
if not visao_todos and det is not None and not det.empty:
    st.markdown("---")
    st.markdown('<p class="sec">Lançamentos analíticos</p>', unsafe_allow_html=True)
    tab = tabela_contas(d, mes_sel)
    op = ["— selecione uma conta —"] + tab["Conta"].tolist()
    escolha = st.selectbox("Conta", op, label_visibility="collapsed")
    if not escolha.startswith("—"):
        cod = escolha.split(" | ")[0].lstrip("0")
        cc = centro_sel.split(" - ")[0].strip()
        f = det[det["Centro_Codigo"] == cc]
        f = f[f["Conta_Codigo"].astype(str).str.lstrip("0") == cod]
        if mes_sel != "Todos os meses" and "Mes_Trans" in f.columns:
            f = f[f["Mes_Trans"] == int(mes_sel)]
        cols = [c for c in ["DOC", "Data", "Clifor", "Item", "Valor"] if c in f.columns]
        if f.empty or not cols:
            st.info("Nenhum lançamento para esta conta nos filtros atuais.")
        else:
            st.dataframe(
                f[cols].sort_values("Valor", ascending=False)
                .style.format({"Valor": "R$ {:,.2f}"}),
                use_container_width=True, height=260, hide_index=True,
            )


st.markdown("---")
st.caption(
    "Painel Gerencial de Custos 2026 · Fonte: relatórios mensais por centro de custo. "
    "Atualize o CSV no repositório para refrescar os números."
)
