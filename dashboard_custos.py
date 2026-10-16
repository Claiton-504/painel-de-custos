# -*- coding: utf-8 -*-
"""
Dashboard de Custos 2026 — Streamlit (Versão BI Profissional)
=============================================================
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
    df
