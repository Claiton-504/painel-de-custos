# -*- coding: utf-8 -*-
"""
Painel de Custos do RH 2026
Inclui: painel, consulta detalhada por conta e novo lançamento.
"""
import hmac
import uuid
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

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

COLS_LANC = [
    "id", "data_registro", "centro_lancamento", "conta", "re", "nome",
    "centro_quem_pegou", "data", "quantidade", "quem_entregou", "observacao",
]
MESES_NOME = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
CORES_STATUS = {"Crítico": "#fef2f2", "Atenção": "#fffbeb", "OK": "#ecfdf5"}


# ───────────────────────── Acesso (senha opcional) ─────────────────────────
def checar_acesso():
    """Se existir APP_PASSWORD nos secrets do Streamlit, exige senha."""
    try:
        senha = st.secrets.get("APP_PASSWORD")
    except Exception:
        senha = None
    if not senha or st.session_state.get("autenticado"):
        return
    st.title("Painel de Custos do RH 2026")
    digitada = st.text_input("Senha de acesso", type="password")
    if digitada:
        if hmac.compare_digest(digitada, str(senha)):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()


checar_acesso()


# ───────────────────────────── Carga de dados ──────────────────────────────
def _normaliza_conta(serie: pd.Series) -> pd.Series:
    """Remove zeros à esquerda uma única vez, para todo o app."""
    s = serie.astype(str).str.strip()
    return s.where(s == "Total", s.str.lstrip("0").replace("", "0"))


@st.cache_data(show_spinner="Carregando...")
def carregar_dados():
    if not CSV_LONG.exists():
        return None, None

    df = pd.read_csv(CSV_LONG, dtype={"Centro_Codigo": str, "Conta_Codigo": str})
    df["Centro_Codigo"] = df["Centro_Codigo"].astype(str).str.strip()
    df["Centro_Nome"] = df["Centro_Nome"].astype(str).str.strip()
    df["Centro"] = df["Centro_Codigo"] + " - " + df["Centro_Nome"]
    df["Conta_Codigo"] = _normaliza_conta(df["Conta_Codigo"])
    df["Conta_Descricao"] = df["Conta_Descricao"].fillna("").astype(str).str.strip()
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["Valor_Abs"] = df["Valor"].abs()
    df["Mes"] = df["Mes"].astype(str).str.strip()

    det = None
    if CSV_DET.exists():
        det = pd.read_csv(CSV_DET, dtype={"Centro_Codigo": str, "Conta_Codigo": str})
        det["Centro_Codigo"] = det["Centro_Codigo"].astype(str).str.strip()
        det["Conta_Codigo"] = _normaliza_conta(det["Conta_Codigo"])
        det["Valor"] = pd.to_numeric(det["Valor"], errors="coerce").fillna(0)
        if "Mes_Trans" in det.columns:
            det["Mes_Trans"] = pd.to_numeric(det["Mes_Trans"], errors="coerce").fillna(0).astype(int)
    return df, det


def gravar_lancamentos(hist: pd.DataFrame):
    """Grava em arquivo temporário e troca, para não corromper o CSV."""
    tmp = CSV_LANC.with_suffix(".tmp")
    hist[COLS_LANC].to_csv(tmp, index=False)
    tmp.replace(CSV_LANC)


def carregar_lancamentos() -> pd.DataFrame:
    if not CSV_LANC.exists():
        return pd.DataFrame(columns=COLS_LANC)
    # dtype=str preserva zeros à esquerda do RE
    hist = pd.read_csv(CSV_LANC, dtype=str).fillna("")
    for c in COLS_LANC:
        if c not in hist.columns:
            hist[c] = ""
    # ids estáveis (o índice muda quando se remove uma linha)
    sem_id = hist["id"].eq("")
    if sem_id.any():
        hist.loc[sem_id, "id"] = [uuid.uuid4().hex[:8] for _ in range(sem_id.sum())]
        gravar_lancamentos(hist)
    hist["quantidade"] = pd.to_numeric(hist["quantidade"], errors="coerce").fillna(1).astype(int)
    return hist[COLS_LANC]


# ───────────────────────────── Funções de cálculo ──────────────────────────
def totais(d: pd.DataFrame, mes):
    """Orçado e realizado a partir das linhas 'Total' (mes=None → anual)."""
    mes_ref = "Total" if mes is None else mes
    t = d[(d["Conta_Codigo"] == "Total") & (d["Mes"] == mes_ref)]
    orc = float(t.loc[t["Tipo"] == "Prev.", "Valor_Abs"].sum())
    real = float(t.loc[t["Tipo"] == "Real.", "Valor_Abs"].sum())
    return orc, real


def resumo_contas(d: pd.DataFrame, mes) -> pd.DataFrame:
    """Tabela por conta: orçado, realizado, saldo, % e status."""
    mes_ref = "Total" if mes is None else mes
    base = d[
        (d["Conta_Codigo"] != "Total")
        & (d["Mes"] == mes_ref)
        & d["Tipo"].isin(["Prev.", "Real."])
    ]
    tab = base.pivot_table(
        index=["Conta_Codigo", "Conta_Descricao"],
        columns="Tipo", values="Valor_Abs", aggfunc="sum", fill_value=0,
    ).reset_index()
    tab = tab.rename(columns={"Prev.": "Orcado", "Real.": "Realizado"})
    for c in ("Orcado", "Realizado"):
        if c not in tab.columns:
            tab[c] = 0.0

    tab = tab[~((tab["Orcado"] == 0) & (tab["Realizado"] == 0))].copy()
    tab["Saldo"] = tab["Orcado"] - tab["Realizado"]

    tem_orc = tab["Orcado"] > 0
    tab["%"] = np.where(
        tem_orc,
        tab["Realizado"] / tab["Orcado"].where(tem_orc, 1),
        (tab["Realizado"] > 0).astype(float),  # sem orçamento mas com gasto = 100%
    )
    tab["Status"] = np.select(
        [tab["%"] >= 1, tab["%"] >= 0.8], ["Crítico", "Atenção"], default="OK"
    )
    tab["Conta"] = tab["Conta_Codigo"].str.zfill(10) + " | " + tab["Conta_Descricao"]

    ordem = {"Crítico": 0, "Atenção": 1, "OK": 2}
    tab = tab.assign(_o=tab["Status"].map(ordem)).sort_values(
        ["_o", "Realizado"], ascending=[True, False]
    )
    return tab[["Conta", "Orcado", "Realizado", "Saldo", "%", "Status"]]


def serie_mensal(d: pd.DataFrame) -> pd.DataFrame:
    """Orçado x realizado por mês (para o gráfico)."""
    t = d[
        (d["Conta_Codigo"] == "Total")
        & d["Tipo"].isin(["Prev.", "Real."])
        & d["Mes"].str.isdigit()
    ]
    if t.empty:
        return pd.DataFrame()
    piv = t.pivot_table(index="Mes", columns="Tipo", values="Valor_Abs", aggfunc="sum", fill_value=0)
    piv.index = [f"{int(m):02d}-{MESES_NOME.get(int(m), m)}" for m in piv.index]
    return piv.sort_index().rename(columns={"Prev.": "Orçado", "Real.": "Realizado"})


def colorir(row):
    return [f"background-color: {CORES_STATUS[row['Status']]}"] * len(row)


def moeda(v) -> str:
    """R$ no padrão brasileiro: 1.234,56"""
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────── Dados base ────────────────────────────────
df, det = carregar_dados()
if df is None:
    st.error("Arquivo dados_longos.csv não encontrado na pasta do app.")
    st.stop()

mapa_centro = (
    df[["Centro_Codigo", "Centro"]].drop_duplicates().set_index("Centro_Codigo")["Centro"].to_dict()
)
codigos_centro = sorted(mapa_centro)
meses_validos = sorted([m for m in df["Mes"].unique() if m.isdigit()], key=int)


def nome_mes(m):
    return "Todos os meses" if m is None else MESES_NOME.get(int(m), m)


# ───────────────────────── Filtros (valem p/ Painel e Consulta) ────────────
with st.sidebar:
    st.header("Filtros")
    centro_sel = st.selectbox(
        "Centro de custo",
        [None] + codigos_centro,
        format_func=lambda c: "Todos os centros" if c is None else mapa_centro[c],
    )
    mes_sel = st.selectbox("Mês", [None] + meses_validos, format_func=nome_mes)
    st.caption("Os filtros valem para as abas Painel e Consulta detalhada.")

d = df if centro_sel is None else df[df["Centro_Codigo"] == centro_sel]
rotulo_centro = "Todos os centros" if centro_sel is None else mapa_centro[centro_sel]

aba_painel, aba_detalhe, aba_lanc = st.tabs([
    "📊 Painel", "🔍 Consulta detalhada", "📋 Lançamentos",
])

# ═══════════════════════════════════════════════════════════
# PAINEL
# ═══════════════════════════════════════════════════════════
with aba_painel:
    st.title("Painel de Custos do RH")
    rotulo = "Anual" if mes_sel is None else f"Mês {nome_mes(mes_sel)}"
    st.caption(f"Exercício 2026 · {rotulo} · {rotulo_centro}")

    orc, real = totais(d, mes_sel)
    saldo = orc - real
    pct = real / orc if orc > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orçamento", moeda(orc))
    c2.metric("Realizado", moeda(real))
    c3.metric("Saldo", moeda(saldo))
    c4.metric("Consumo", f"{pct:.1%}")
    st.progress(min(pct, 1.0))

    mensal = serie_mensal(d)
    if not mensal.empty:
        st.subheader("Evolução mensal")
        st.bar_chart(mensal, height=280)

    st.subheader("Contas")
    tab = resumo_contas(d, mes_sel)
    filtro_status = st.multiselect(
        "Mostrar status", ["Crítico", "Atenção", "OK"], default=["Crítico", "Atenção", "OK"]
    )
    tab = tab[tab["Status"].isin(filtro_status)]

    if tab.empty:
        st.info("Nenhuma conta para os filtros selecionados.")
    else:
        st.dataframe(
            tab.style.apply(colorir, axis=1).format({
                "Orcado": moeda, "Realizado": moeda, "Saldo": moeda, "%": "{:.1%}",
            }),
            use_container_width=True,
            height=420,
            hide_index=True,
        )
        st.download_button(
            "⬇️ Baixar tabela de contas",
            data=tab.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="contas_resumo.csv",
            mime="text/csv",
        )
    st.caption("Use a aba Consulta detalhada para ver os lançamentos de uma conta.")

# ═══════════════════════════════════════════════════════════
# CONSULTA DETALHADA
# ═══════════════════════════════════════════════════════════
with aba_detalhe:
    st.title("Consulta detalhada")
    st.caption(f"Centro: {rotulo_centro} · Mês: {nome_mes(mes_sel)} (ajuste na barra lateral)")

    contas_opts = (
        d[d["Conta_Codigo"] != "Total"][["Conta_Codigo", "Conta_Descricao"]]
        .drop_duplicates()
        .sort_values("Conta_Descricao")
    )
    contas_opts["Label"] = contas_opts["Conta_Codigo"].str.zfill(10) + " | " + contas_opts["Conta_Descricao"]
    label_para_cod = dict(zip(contas_opts["Label"], contas_opts["Conta_Codigo"]))

    conta_escolhida = st.selectbox(
        "Conta",
        [None] + list(label_para_cod),
        format_func=lambda x: "— selecione uma conta —" if x is None else x,
    )

    if conta_escolhida:
        cod = label_para_cod[conta_escolhida]
        st.subheader(f"Lançamentos · {conta_escolhida}")

        if det is not None and not det.empty:
            f = det[det["Conta_Codigo"] == cod]
            if centro_sel is not None:
                f = f[f["Centro_Codigo"] == centro_sel]
            if mes_sel is not None and "Mes_Trans" in f.columns:
                f = f[f["Mes_Trans"] == int(mes_sel)]

            cols = [c for c in ["Centro_Codigo", "DOC", "Data", "Clifor", "Item", "QT", "Mes_Trans", "Valor"] if c in f.columns]
            if f.empty or not cols:
                st.info("Nenhum lançamento analítico encontrado para esta conta com os filtros atuais.")
            else:
                f = f[cols].sort_values("Valor", ascending=False)
                st.metric("Total dos lançamentos", moeda(f["Valor"].sum()))
                st.dataframe(
                    f.style.format({"Valor": moeda}),
                    use_container_width=True, height=400, hide_index=True,
                )
                st.download_button(
                    "⬇️ Baixar lançamentos",
                    data=f.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                    file_name=f"lancamentos_conta_{cod}.csv",
                    mime="text/csv",
                )
        else:
            st.warning("Arquivo detalhes_longos.csv não encontrado. Mostrando valores mensais da conta.")
            sub = d[(d["Conta_Codigo"] == cod) & d["Tipo"].isin(["Prev.", "Real."]) & (d["Mes"] != "Total")]
            if sub.empty:
                st.info("Sem dados mensais para esta conta.")
            else:
                piv = sub.pivot_table(index="Mes", columns="Tipo", values="Valor_Abs", aggfunc="sum").reset_index()
                st.dataframe(piv, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════
# LANÇAMENTOS
# ═══════════════════════════════════════════════════════════
centros_labels = [mapa_centro[c] for c in codigos_centro]
contas_lista = sorted(
    df[df["Conta_Codigo"] != "Total"]["Conta_Descricao"].replace("", np.nan).dropna().unique().tolist()
)


@st.dialog("Novo lançamento", width="large")
def dialogo_novo_lancamento():
    """Janela que abre ao clicar em 'Novo lançamento'."""
    st.caption("Registre entregas, consumos ou alocações de qualquer centro e conta.")
    with st.form("form_lanc"):
        c1, c2 = st.columns(2)
        with c1:
            centro_lanc = st.selectbox("Centro de custo (do lançamento)", centros_labels)
            matricula = st.text_input("RE")
            centro_pegou = st.selectbox("Centro de custo de quem pegou", centros_labels)
            quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
        with c2:
            conta = st.selectbox("Conta", contas_lista)
            nome = st.text_input("Nome")
            data_lanc = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            quem_entregou = st.text_input("Quem entregou")

        observacao = st.text_area("Observação (opcional)", height=70)
        ok = st.form_submit_button("Salvar lançamento", type="primary", use_container_width=True)

    if ok:
        if not matricula.strip() or not nome.strip() or not quem_entregou.strip():
            st.error("Preencha RE, Nome e Quem entregou.")
        else:
            registro = {
                "id": uuid.uuid4().hex[:8],
                "data_registro": date.today().isoformat(),
                "centro_lancamento": centro_lanc,
                "conta": conta,
                "re": matricula.strip(),
                "nome": nome.strip(),
                "centro_quem_pegou": centro_pegou,
                "data": data_lanc.isoformat(),
                "quantidade": int(quantidade),
                "quem_entregou": quem_entregou.strip(),
                "observacao": observacao.strip(),
            }
            hist_atual = carregar_lancamentos()
            hist_atual = pd.concat([hist_atual, pd.DataFrame([registro])], ignore_index=True)
            gravar_lancamentos(hist_atual)
            st.session_state["aviso"] = "Lançamento registrado com sucesso."
            st.rerun()  # fecha a janela e atualiza o histórico


with aba_lanc:
    if "aviso" in st.session_state:
        st.toast(st.session_state.pop("aviso"), icon="✅")

    st.title("Lançamentos")

    col_tit, col_btn = st.columns([4, 1])
    col_tit.subheader("Histórico de lançamentos")
    if col_btn.button("➕ Novo lançamento", type="primary", use_container_width=True):
        dialogo_novo_lancamento()
    hist = carregar_lancamentos()

    if hist.empty:
        st.info("Nenhum lançamento registrado ainda.")
    else:
        busca = st.text_input("Buscar (nome, RE, conta...)", key="busca_lanc")
        vis = hist
        if busca.strip():
            mask = hist.astype(str).apply(lambda col: col.str.contains(busca.strip(), case=False, na=False)).any(axis=1)
            vis = hist[mask]

        st.dataframe(
            vis.sort_values("data_registro", ascending=False),
            use_container_width=True, height=280, hide_index=True,
        )

        st.markdown("**Gerenciar lançamento**")
        rotulos = {
            r["id"]: f"{r['data']} | {r['nome']} | {r['conta']} | Qtd {r['quantidade']}"
            for _, r in hist.iterrows()
        }
        escolha = st.selectbox("Selecione um lançamento", list(rotulos), format_func=rotulos.get, key="sel_lanc")

        col_ed, col_rm, col_dl = st.columns(3)
        with col_ed:
            if st.button("✏️ Editar", use_container_width=True):
                st.session_state["editando"] = escolha
                st.session_state.pop("removendo", None)
        with col_rm:
            if st.button("🗑️ Remover", use_container_width=True):
                st.session_state["removendo"] = escolha
                st.session_state.pop("editando", None)
        with col_dl:
            st.download_button(
                "⬇️ Baixar histórico",
                data=hist.to_csv(index=False).encode("utf-8-sig"),
                file_name="lancamentos_rh.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Confirmação de remoção
        if st.session_state.get("removendo") in hist["id"].values:
            rid = st.session_state["removendo"]
            st.warning(f"Remover definitivamente: {rotulos[rid]}?")
            cs, cn = st.columns(2)
            if cs.button("Sim, remover", type="primary"):
                gravar_lancamentos(hist[hist["id"] != rid])
                st.session_state.pop("removendo", None)
                st.success("Lançamento removido.")
                st.rerun()
            if cn.button("Cancelar"):
                st.session_state.pop("removendo", None)
                st.rerun()

        # Edição
        if st.session_state.get("editando") in hist["id"].values:
            eid = st.session_state["editando"]
            row = hist[hist["id"] == eid].iloc[0]

            def opcoes_com(valor, lista):
                """Garante que o valor atual (mesmo antigo) esteja nas opções."""
                return lista if valor in lista else [valor] + lista

            data_atual = pd.to_datetime(row["data"], errors="coerce")
            data_atual = date.today() if pd.isna(data_atual) else data_atual.date()

            st.markdown("---")
            st.markdown(f"**Editando lançamento {eid}**")
            with st.form("form_editar"):
                e1, e2 = st.columns(2)
                with e1:
                    op_c = opcoes_com(row["centro_lancamento"], centros_labels)
                    e_centro = st.selectbox("Centro (lançamento)", op_c, index=op_c.index(row["centro_lancamento"]))
                    e_re = st.text_input("RE", value=row["re"])
                    op_p = opcoes_com(row["centro_quem_pegou"], centros_labels)
                    e_centro_pegou = st.selectbox("Centro de quem pegou", op_p, index=op_p.index(row["centro_quem_pegou"]))
                    e_qtd = st.number_input("Quantidade", min_value=1, value=int(row["quantidade"]), step=1)
                with e2:
                    op_k = opcoes_com(row["conta"], contas_lista)
                    e_conta = st.selectbox("Conta", op_k, index=op_k.index(row["conta"]))
                    e_nome = st.text_input("Nome", value=row["nome"])
                    e_data = st.date_input("Data", value=data_atual, format="DD/MM/YYYY")
                    e_quem = st.text_input("Quem entregou", value=row["quem_entregou"])
                e_obs = st.text_area("Observação", value=row["observacao"])

                if st.form_submit_button("Salvar edição", type="primary"):
                    if not e_re.strip() or not e_nome.strip() or not e_quem.strip():
                        st.error("Preencha RE, Nome e Quem entregou.")
                    else:
                        novo = hist.copy()
                        i = novo.index[novo["id"] == eid][0]
                        novo.loc[i, ["centro_lancamento", "conta", "re", "nome", "centro_quem_pegou",
                                     "data", "quantidade", "quem_entregou", "observacao"]] = [
                            e_centro, e_conta, e_re.strip(), e_nome.strip(), e_centro_pegou,
                            e_data.isoformat(), int(e_qtd), e_quem.strip(), e_obs.strip(),
                        ]
                        gravar_lancamentos(novo)
                        st.session_state.pop("editando", None)
                        st.success("Lançamento atualizado.")
                        st.rerun()
            if st.button("Cancelar edição"):
                st.session_state.pop("editando", None)
                st.rerun()
