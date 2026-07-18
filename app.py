# -*- coding: utf-8 -*-
"""
SIG Frota de Veículos — PAINEL GERENCIAL (somente leitura / resumo)
Publicar como app.py no repo: painel-viagens-sv
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from io import BytesIO
from supabase import create_client

from sigcf_auth import aplicar_tema_sigcf, dark_table, exigir_acesso, logo_html

BUILD = "2026-07-18-painel-v3"

st.set_page_config(
    page_title="SIG Frota — Painel Gerencial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

exigir_acesso("SIG Frota — Painel Gerencial", "Gestão · viagens, destinos e fechamento — SIGCF SV")
aplicar_tema_sigcf()

PDARK = dict(
    paper_bgcolor="rgba(13,24,12,0.9)",
    plot_bgcolor="rgba(10,20,9,0.85)",
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


# ── Cabeçalho ──
col_l, col_t = st.columns([1, 5])
with col_l:
    st.markdown(logo_html(100), unsafe_allow_html=True)
with col_t:
    st.markdown("## SIG Frota de Veículos")
    st.caption("Painel Gerencial · Controladoria Santa Virgínia · Build " + BUILD)

# ── Filtros (barra compacta — sem sidebar) ──
hoje = date.today()
f1, f2, f3, f4, f5 = st.columns([2, 1.2, 1.2, 1.2, 1.2])
with f1:
    preset = st.selectbox(
        "Período",
        ["Este mês", "Mês anterior", "Últimos 30 dias", "Últimos 7 dias", "Personalizado"],
    )
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
    with f2:
        d_ini = st.date_input("De", value=hoje.replace(day=1))
    with f3:
        d_fim = st.date_input("Até", value=hoje)
with f4:
    filtro_linha = st.multiselect("Linha", ["LEVE", "PESADA"], default=["LEVE", "PESADA"])
with f5:
    filtro_tipo = st.multiselect("Tipo", ["INTERNA", "EXTERNA"], default=["INTERNA", "EXTERNA"])

st.caption(f"Período: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}")

df = carregar_viagens(str(d_ini), str(d_fim))

if not df.empty:
    df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    if "locais_internos" not in df.columns and "retiros" in df.columns:
        df["locais_internos"] = df["retiros"]
    if "linha" in df.columns:
        df = df[df["linha"].isin(filtro_linha)]
    if "tipo_viagem" in df.columns:
        df = df[df["tipo_viagem"].isin(filtro_tipo)]

if df.empty:
    st.info("Nenhuma viagem no período selecionado. Os lançamentos aparecem aqui automaticamente.")
    st.stop()

# ── KPIs operacionais ──
km_total = float(df["km_percorrido"].sum()) if "km_percorrido" in df.columns else 0
n_viagens = len(df)
n_veiculos = df["placa"].nunique() if "placa" in df.columns else 0
n_int = len(df[df["tipo_viagem"] == "INTERNA"]) if "tipo_viagem" in df.columns else 0
n_ext = len(df[df["tipo_viagem"] == "EXTERNA"]) if "tipo_viagem" in df.columns else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Viagens", n_viagens)
m2.metric("KM percorridos", fmt_km(km_total))
m3.metric("Veículos", n_veiculos)
m4.metric("Internas / Externas", f"{n_int} / {n_ext}")

# ── Fechamento ──
st.markdown('<div class="sec">Fechamento do período</div>', unsafe_allow_html=True)
litros = float(df["litros_abastecidos"].sum()) if "litros_abastecidos" in df.columns else 0
v_abast = float(df["valor_abastecimento"].sum()) if "valor_abastecimento" in df.columns else 0
v_ped = float(df["valor_pedagio"].sum()) if "valor_pedagio" in df.columns else 0
v_manut = float(df["valor_manutencao"].sum()) if "valor_manutencao" in df.columns else 0
v_mot = float(df["valor_motorista"].sum()) if "valor_motorista" in df.columns else 0
custo_total = v_abast + v_ped + v_manut + v_mot

fc1, fc2, fc3, fc4 = st.columns(4)
fc1.metric("Volume abastecido", f"{litros:,.1f} L".replace(",", "."))
fc2.metric("Abastecimento", fmt_r(v_abast))
fc3.metric("Pedágio + Manutenção", fmt_r(v_ped + v_manut))
fc4.metric("Custo total", fmt_r(custo_total))

st.markdown(
    f'<div class="kpi-destaque">'
    f'<span style="color:#8aab80;font-size:12px;text-transform:uppercase;letter-spacing:1px;">'
    f'Custo médio por km</span><br>'
    f'<strong style="color:#6fcf60;font-size:1.4rem;font-family:Barlow Condensed,sans-serif;">'
    f'{fmt_r(custo_total / km_total if km_total > 0 else 0)}</strong>'
    f'<span style="color:#8aab80;font-size:12px;margin-left:12px;">'
    f'Motorista: {fmt_r(v_mot)}</span></div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(["Viagens", "Destinos", "Resumo", "Mapas"])

with tab1:
    st.markdown('<div class="sec">Viagens registradas</div>', unsafe_allow_html=True)
    show = df.copy()
    show["Data/Hora"] = show["data_hora"].dt.strftime("%d/%m/%Y %H:%M")
    show["Destino"] = show.apply(
        lambda r: ", ".join(r["locais_internos"])
        if isinstance(r.get("locais_internos"), list)
        else (r.get("destino_cidade") or r.get("destino_nome") or "—"),
        axis=1,
    )
    cols = [
        "Data/Hora", "placa", "linha", "tipo_viagem", "km_percorrido",
        "motivo", "motorista", "Destino",
    ]
    cols = [c for c in cols if c in show.columns or c in ("Data/Hora", "Destino")]
    rename = {
        "placa": "Placa", "linha": "Linha", "tipo_viagem": "Tipo",
        "km_percorrido": "KM", "motivo": "Motivo", "motorista": "Motorista",
    }
    tabela = show[[c for c in cols if c in show.columns]].rename(columns=rename)
    dark_table(tabela, height=320)
    st.download_button(
        "Exportar Excel",
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
            .agg(
                viagens=("id", "count") if "id" in df_ext.columns else ("km_percorrido", "count"),
                km=("km_percorrido", "sum"),
            )
            .reset_index()
            .sort_values("viagens", ascending=False)
        )
        dest.columns = ["Destino", "Viagens", "KM total"]
        dark_table(dest)
        fig_d = px.bar(dest.head(12), x="Viagens", y="Destino", orientation="h")
        fig_d.update_layout(**PDARK, title="Top destinos externos")
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
        dark_table(freq)
        fig_l = px.bar(freq.head(12), x="Visitas", y="Local", orientation="h")
        fig_l.update_layout(**PDARK, title="Retiros / locais")
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.info("Sem viagens internas no período.")

with tab3:
    st.markdown('<div class="sec">KM por placa</div>', unsafe_allow_html=True)
    if "placa" in df.columns:
        por_placa = (
            df.groupby(["placa", "linha"], as_index=False)
            .agg(
                viagens=("id", "count") if "id" in df.columns else ("km_percorrido", "count"),
                km=("km_percorrido", "sum"),
            )
            .sort_values("km", ascending=False)
        )
        fig_p = px.bar(
            por_placa, x="placa", y="km", color="linha",
            color_discrete_map={"LEVE": "#5b9bd5", "PESADA": "#ffc857"},
        )
        fig_p.update_layout(**PDARK, title="Quilometragem por veículo")
        st.plotly_chart(fig_p, use_container_width=True)

    st.markdown('<div class="sec">Evolução diária</div>', unsafe_allow_html=True)
    df_d = df.copy()
    df_d["dia"] = df_d["data_hora"].dt.date
    por_dia = df_d.groupby(["dia", "tipo_viagem"], as_index=False)["km_percorrido"].sum()
    fig_t = px.bar(
        por_dia, x="dia", y="km_percorrido", color="tipo_viagem",
        color_discrete_map={"INTERNA": "#4a9e3f", "EXTERNA": "#5b9bd5"},
    )
    fig_t.update_layout(**PDARK, title="KM por dia")
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
        dark_table(fech, height=280)

with tab4:
    st.info(
        "Mapas interativos (fazenda + viagens externas) serão habilitados na próxima versão. "
        "As coordenadas já são salvas via OpenStreetMap nos lançamentos externos."
    )
    com_coords = (
        df[df["destino_lat"].notna() & df["destino_lng"].notna()]
        if "destino_lat" in df.columns
        else pd.DataFrame()
    )
    if not com_coords.empty:
        st.caption(f"{len(com_coords)} viagens externas com coordenadas GPS registradas.")

st.caption("SIG Frota de Veículos · Painel Gerencial · Controladoria SV — MS")
