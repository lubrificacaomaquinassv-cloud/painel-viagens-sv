# -*- coding: utf-8 -*-
"""
SIG Frota de Veículos — PAINEL GERENCIAL (somente leitura / resumo)
Publicar como app.py no repo: sig-frota-painel-sv
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from io import BytesIO
from supabase import create_client

from sigcf_auth import exigir_acesso, logo_html

BUILD = "2026-07-18-painel-v2"
LOGO_URL = "https://i.postimg.cc/Y9X7ddnb/LOGO-BP.jpg"

st.set_page_config(
    page_title="SIG Frota de Veículos — Painel Gerencial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

exigir_acesso("SIG Frota — Painel Gerencial", "Gestão · viagens, destinos e fechamento — SIGCF SV")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
[data-testid="stAppViewContainer"]{background:#0a1409;}
[data-testid="stSidebar"]{background:#111c10;border-right:1px solid #1e2e1c;}
[data-testid="stHeader"]{background:#0a1409;}
h1,h2,h3,p,span,label{color:#e8edd0;}
.stCaption{color:#8aab80!important;}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
 letter-spacing:2px;text-transform:uppercase;color:#8aab80;
 border-left:4px solid #4a9e3f;padding-left:10px;margin:16px 0 10px;}
div[data-testid="metric-container"]{background:#111c10;border:1px solid #1e2e1c;border-radius:10px;padding:14px;}
div[data-testid="metric-container"] label{color:#8aab80!important;}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#6fcf60!important;
 font-family:'Barlow Condensed',sans-serif;}
.stTabs [data-baseweb="tab-list"]{background:#111c10;border-bottom:2px solid #1e2e1c;}
.stTabs [data-baseweb="tab"]{color:#8aab80;font-family:'Barlow Condensed',sans-serif;font-weight:700;}
.stTabs [aria-selected="true"]{color:#6fcf60!important;border-bottom:3px solid #4a9e3f!important;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid #c9a227;
 border-radius:12px;padding:5px;display:inline-block;}
.fechamento-box{background:#111c10;border:1px solid #4a9e3f;border-radius:12px;padding:18px;margin:8px 0;}
</style>
""", unsafe_allow_html=True)

PDARK = dict(
    paper_bgcolor="#111c10", plot_bgcolor="#0d180c",
    font=dict(color="#e8edd0", family="Barlow Condensed"),
    margin=dict(l=10, r=10, t=36, b=10),
)

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def fmt_r(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def fmt_km(v):
    try:
        return f"{float(v):,.0f} km".replace(",", ".")
    except (TypeError, ValueError):
        return "0 km"


@st.cache_data(ttl=60)
def carregar_viagens(data_ini: str, data_fim: str):
    try:
        res = (
            supabase.table("vw_sig_frota_painel")
            .select("*")
            .gte("data_hora", data_ini)
            .lte("data_hora", data_fim + "T23:59:59")
            .order("data_hora", desc=True)
            .execute()
        )
        return pd.DataFrame(res.data or [])
    except Exception:
        res = (
            supabase.table("viagem_veiculo")
            .select("*")
            .gte("data_hora", data_ini)
            .lte("data_hora", data_fim + "T23:59:59")
            .order("data_hora", desc=True)
            .execute()
        )
        return pd.DataFrame(res.data or [])


def gerar_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


# ── Sidebar: período ──
with st.sidebar:
    st.markdown(logo_html(90), unsafe_allow_html=True)
    st.markdown("### 📊 Painel Gerencial")
    st.caption(f"Build {BUILD}")
    st.divider()
    st.markdown("**Período de viagens**")
    hoje = date.today()
    preset = st.selectbox("Atalho", [
        "Este mês", "Mês anterior", "Últimos 30 dias", "Últimos 7 dias", "Personalizado",
    ])
    if preset == "Este mês":
        d_ini = hoje.replace(day=1)
        d_fim = hoje
    elif preset == "Mês anterior":
        primeiro = hoje.replace(day=1)
        d_fim = primeiro - timedelta(days=1)
        d_ini = d_fim.replace(day=1)
    elif preset == "Últimos 30 dias":
        d_ini = hoje - timedelta(days=30)
        d_fim = hoje
    elif preset == "Últimos 7 dias":
        d_ini = hoje - timedelta(days=7)
        d_fim = hoje
    else:
        d_ini = st.date_input("De", value=hoje.replace(day=1))
        d_fim = st.date_input("Até", value=hoje)

    filtro_linha = st.multiselect("Linha", ["LEVE", "PESADA"], default=["LEVE", "PESADA"])
    filtro_tipo = st.multiselect("Tipo", ["INTERNA", "EXTERNA"], default=["INTERNA", "EXTERNA"])
    st.divider()
    st.caption("Dados atualizados automaticamente · sem solicitar lançamentos")

df = carregar_viagens(str(d_ini), str(d_fim))

if not df.empty:
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    if "locais_internos" not in df.columns and "retiros" in df.columns:
        df["locais_internos"] = df["retiros"]
    if "linha" in df.columns:
        df = df[df["linha"].isin(filtro_linha)]
    if "tipo_viagem" in df.columns:
        df = df[df["tipo_viagem"].isin(filtro_tipo)]

# ── Header ──
col_l, col_t = st.columns([1, 5])
with col_l:
    st.markdown(logo_html(100), unsafe_allow_html=True)
with col_t:
    st.markdown("## 🚘 SIG Frota de Veículos — Painel Gerencial")
    st.caption(
        f"Período: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')} · "
        "SIGCF — Controladoria Santa Virgínia"
    )

if df.empty:
    st.info("Nenhuma viagem no período selecionado. Os lançamentos aparecem aqui automaticamente.")
    st.stop()

# ── KPIs principais ──
km_total = float(df["km_percorrido"].sum()) if "km_percorrido" in df.columns else 0
n_viagens = len(df)
n_veiculos = df["placa"].nunique() if "placa" in df.columns else 0
n_int = len(df[df["tipo_viagem"] == "INTERNA"]) if "tipo_viagem" in df.columns else 0
n_ext = len(df[df["tipo_viagem"] == "EXTERNA"]) if "tipo_viagem" in df.columns else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Viagens no período", n_viagens)
m2.metric("KM percorridos", fmt_km(km_total))
m3.metric("Veículos utilizados", n_veiculos)
m4.metric("Internas / Externas", f"{n_int} / {n_ext}")

# ── Fechamento ──
st.markdown('<div class="sec">💰 Fechamento do período</div>', unsafe_allow_html=True)
litros = float(df["litros_abastecidos"].sum()) if "litros_abastecidos" in df.columns else 0
v_abast = float(df["valor_abastecimento"].sum()) if "valor_abastecimento" in df.columns else 0
v_ped = float(df["valor_pedagio"].sum()) if "valor_pedagio" in df.columns else 0
v_manut = float(df["valor_manutencao"].sum()) if "valor_manutencao" in df.columns else 0
v_mot = float(df["valor_motorista"].sum()) if "valor_motorista" in df.columns else 0
custo_total = v_abast + v_ped + v_manut + v_mot

fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
fc1.metric("Volume abastecido", f"{litros:,.1f} L".replace(",", "."))
fc2.metric("Gasto abastecimento", fmt_r(v_abast))
fc3.metric("Pedágio", fmt_r(v_ped))
fc4.metric("Manutenção", fmt_r(v_manut))
fc5.metric("Motorista", fmt_r(v_mot))
fc6.metric("Custo total", fmt_r(custo_total))

st.markdown(
    f'<div class="fechamento-box"><span style="color:#8aab80;">Custo médio por km:</span> '
    f'<strong style="color:#6fcf60;font-size:1.2rem;">'
    f'{fmt_r(custo_total / km_total if km_total > 0 else 0)}</strong></div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🚗 Viagens da frota", "📍 Destinos", "📈 Resumo", "🗺️ Mapas (em breve)",
])

with tab1:
    st.markdown('<div class="sec">Viagens registradas</div>', unsafe_allow_html=True)
    show = df.copy()
    show["Data/Hora"] = show["data_hora"].dt.strftime("%d/%m/%Y %H:%M")
    show["Destino"] = show.apply(
        lambda r: ", ".join(r["locais_internos"]) if isinstance(r.get("locais_internos"), list)
        else (r.get("destino_cidade") or r.get("destino_nome") or "—"),
        axis=1,
    )
    cols = ["Data/Hora", "placa", "linha", "tipo_viagem", "km_percorrido", "motivo", "motorista", "Destino"]
    cols = [c for c in cols if c in show.columns or c == "Data/Hora" or c == "Destino"]
    rename = {"placa": "Placa", "linha": "Linha", "tipo_viagem": "Tipo",
              "km_percorrido": "KM", "motivo": "Motivo", "motorista": "Motorista"}
    tabela = show[[c for c in cols if c in show.columns]].rename(columns=rename)
    st.dataframe(tabela, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Exportar Excel",
        data=gerar_excel(tabela),
        file_name=f"sig_frota_viagens_{d_ini}_{d_fim}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with tab2:
    st.markdown('<div class="sec">Destinos — viagens externas</div>', unsafe_allow_html=True)
    df_ext = df[df["tipo_viagem"] == "EXTERNA"].copy() if "tipo_viagem" in df.columns else pd.DataFrame()
    if df_ext.empty:
        st.info("Sem viagens externas no período.")
    else:
        dest = (
            df_ext.groupby("destino_cidade", dropna=False)
            .agg(viagens=("id", "count") if "id" in df_ext.columns else ("km_percorrido", "count"),
                 km=("km_percorrido", "sum"))
            .reset_index()
            .sort_values("viagens", ascending=False)
        )
        dest.columns = ["Destino", "Viagens", "KM total"]
        st.dataframe(dest, use_container_width=True, hide_index=True)
        fig_d = px.bar(dest.head(12), x="Viagens", y="Destino", orientation="h", title="Top destinos externos")
        fig_d.update_layout(**PDARK)
        st.plotly_chart(fig_d, use_container_width=True)

    st.markdown('<div class="sec">Locais internos mais visitados</div>', unsafe_allow_html=True)
    df_int = df[df["tipo_viagem"] == "INTERNA"].copy() if "tipo_viagem" in df.columns else pd.DataFrame()
    locais = []
    for val in df_int.get("locais_internos", pd.Series(dtype=object)).dropna():
        if isinstance(val, list):
            locais.extend(val)
    if locais:
        freq = pd.Series(locais).value_counts().reset_index()
        freq.columns = ["Local", "Visitas"]
        st.dataframe(freq, use_container_width=True, hide_index=True)
        fig_l = px.bar(freq.head(12), x="Visitas", y="Local", orientation="h", title="Retiros / locais")
        fig_l.update_layout(**PDARK)
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.info("Sem viagens internas no período.")

with tab3:
    st.markdown('<div class="sec">KM por placa</div>', unsafe_allow_html=True)
    if "placa" in df.columns:
        por_placa = (
            df.groupby(["placa", "linha"], as_index=False)
            .agg(viagens=("id", "count") if "id" in df.columns else ("km_percorrido", "count"),
                 km=("km_percorrido", "sum"))
            .sort_values("km", ascending=False)
        )
        fig_p = px.bar(por_placa, x="placa", y="km", color="linha",
                       title="Quilometragem por veículo",
                       color_discrete_map={"LEVE": "#5b9bd5", "PESADA": "#ffc857"})
        fig_p.update_layout(**PDARK)
        st.plotly_chart(fig_p, use_container_width=True)

    st.markdown('<div class="sec">Evolução diária</div>', unsafe_allow_html=True)
    df_d = df.copy()
    df_d["dia"] = df_d["data_hora"].dt.date
    por_dia = df_d.groupby(["dia", "tipo_viagem"], as_index=False)["km_percorrido"].sum()
    fig_t = px.bar(por_dia, x="dia", y="km_percorrido", color="tipo_viagem",
                   title="KM por dia", color_discrete_map={"INTERNA": "#4a9e3f", "EXTERNA": "#5b9bd5"})
    fig_t.update_layout(**PDARK)
    st.plotly_chart(fig_t, use_container_width=True)

    st.markdown('<div class="sec">Fechamento por placa</div>', unsafe_allow_html=True)
    if "placa" in df.columns:
        fech = df.groupby("placa", as_index=False).agg(
            viagens=("id", "count") if "id" in df.columns else ("km_percorrido", "count"),
            km=("km_percorrido", "sum"),
            litros=("litros_abastecidos", "sum"),
            abast=("valor_abastecimento", "sum"),
            pedagio=("valor_pedagio", "sum"),
            manut=("valor_manutencao", "sum"),
            motorista=("valor_motorista", "sum"),
        )
        fech["custo_total"] = fech["abast"] + fech["pedagio"] + fech["manut"] + fech["motorista"]
        st.dataframe(fech, use_container_width=True, hide_index=True)

with tab4:
    st.info(
        "🗺️ Mapas interativos (fazenda + viagens externas) serão habilitados na próxima versão. "
        "As coordenadas já são salvas via OpenStreetMap nos lançamentos externos. "
        "Rode `python atualizar_geografia.py` para geocodificar os locais internos."
    )
    com_coords = df[df["destino_lat"].notna() & df["destino_lng"].notna()] if "destino_lat" in df.columns else pd.DataFrame()
    if not com_coords.empty:
        st.caption(f"{len(com_coords)} viagens externas com coordenadas GPS registradas.")

st.divider()
st.caption("SIG Frota de Veículos | Painel Gerencial | Controladoria SV — MS")
