"""
Painel de acompanhamento de PLs — réplica em Streamlit do dashboard Tableau.

Telas:
  1. Visão Geral   (KPIs, evolução dos protocolos, top municípios, ranking 30 dias)
  2. Municípios    (KPIs municipais, mapa por UF, ranking 30 dias)
  3. Dados         (tabela interativa com busca, ordenação e download CSV)

Os filtros da barra lateral (Fonte, UF, Cidade, Vereador, Período) valem para as 3 telas.

Data de referência ("hoje" do painel) = maior "Data da última atualização" da base,
assim como o card "Última atualização" do Tableau. Todas as janelas de "últimos 30 dias"
são contadas a partir dela.
"""

import json
import urllib.request
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Configuração geral
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Painel de acompanhamento de PLs", page_icon="🏛️", layout="wide")

ARQUIVO = Path(__file__).parent / "dados_consolidados.csv"
GEOJSON_UF = ("https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
              "master/public/data/brazil-states.geojson")

# Paleta tirada dos prints do Tableau
VERDE_ESCURO = "#1E4D45"
VERDE_MEDIO = "#5E9C93"
VERDE_CLARO = "#BFD3CF"
SALMAO = "#E8806A"
FUNDO = "#F7F3EF"
MESES = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.",
         "jul.", "ago.", "set.", "out.", "nov.", "dez."]

# Nomes curtos para as colunas originais da planilha
COLUNAS = {
    "1. Número do PL\n (XXXX/AAAA)": "Número do PL",
    "2. Data do protocolo (DD/MM/AAAA)": "Data do protocolo",
    "3. Status do PL": "Status do PL",
    "4. Se aprovado, nº da Lei": "Nº da Lei",
    "5. Link para a Lei": "Link da Lei",
    "6. Data da aprovação (DD/MM/AAAA)": "Data da aprovação",
    "7. Se rejeitado, especifique a justificativa ou o motivo": "Motivo da rejeição",
    "8. Ementa": "Ementa",
    "9. Link do PDF": "Link do PDF",
    "10. Link do PL": "Link do PL",
}
COLUNAS_DATA = ["Data do protocolo", "Data da aprovação", "Data da última atualização"]

# ----------------------------------------------------------------------------
# Estilo (CSS) — cartões brancos arredondados, sidebar verde-escura, fundo bege
# ----------------------------------------------------------------------------
st.markdown(f"""
<style>
.stApp {{ background: {FUNDO}; }}
[data-testid="stSidebar"] {{ background: {VERDE_ESCURO}; }}
/* texto branco só em rótulos, markdown e menu — os campos de filtro mantêm texto escuro */
[data-testid="stSidebar"] label, [data-testid="stSidebar"] label *,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
[data-testid="stSidebarNav"] *, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #FFFFFF; }}
.card {{ background:#FFF; border-radius:14px; padding:14px 18px; box-shadow:0 1px 4px rgba(0,0,0,.08);
         text-align:center; height:100%; }}
.card .titulo {{ color:{VERDE_ESCURO}; font-size:1.35rem; font-weight:600; }}
.card .valor  {{ color:{VERDE_ESCURO}; font-size:2.4rem; font-weight:700; line-height:1.2; }}
.card .sub    {{ color:#4B5563; font-size:.8rem; }}
.card .verde  {{ color:#2E7D32; }}
.atualizacao {{ background:{SALMAO}; border-radius:10px; padding:10px; text-align:center; font-size:.85rem; }}
h3 {{ color:{VERDE_ESCURO}; }}
</style>
""", unsafe_allow_html=True)


def fmt(n):
    """Número no padrão brasileiro: 33.564"""
    return f"{n:,.0f}".replace(",", ".")


def pct(x, casas=1):
    """Percentual no padrão brasileiro: 0,33%"""
    return f"{x:.{casas}f}%".replace(".", ",")


def card(titulo, valor, sub="", sub2=""):
    st.markdown(f"""<div class="card"><div class="titulo">{titulo}</div>
        <div class="valor">{valor}</div><div class="sub">{sub}</div><div class="sub">{sub2}</div></div>""",
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Leitura dos dados (com cache)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando planilha...")
def carregar(caminho):
    df = pd.read_csv(caminho, dtype=str).rename(columns=COLUNAS)
    # A planilha mistura "05/06/2026" e "5/3/2026": dayfirst + format="mixed" resolve os dois
    for c in COLUNAS_DATA:
        df[c] = pd.to_datetime(df[c], dayfirst=True, format="mixed", errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def carregar_geojson():
    with urllib.request.urlopen(GEOJSON_UF, timeout=10) as r:
        return json.load(r)


if not ARQUIVO.exists():
    st.error(f"Arquivo de dados não encontrado: `{ARQUIVO.name}`. "
             "Coloque a planilha CSV na mesma pasta do app.py com esse nome.")
    st.stop()

try:
    base = carregar(ARQUIVO)
except Exception as e:
    st.error(f"Não foi possível ler a planilha: {e}")
    st.stop()

# Data de referência = última atualização da base inteira (não muda com filtros)
REF = base["Data da última atualização"].max()
INI_30 = REF - pd.Timedelta(days=30)
INI_60 = REF - pd.Timedelta(days=60)

# ----------------------------------------------------------------------------
# Barra lateral: navegação + filtros globais
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🏛️ Painel de acompanhamento de PLs")
    st.caption("Base SAPL / CR2")

pagina = st.navigation([
    st.Page(lambda: None, title="Visão Geral", icon="🏠", url_path="visao-geral", default=True),
    st.Page(lambda: None, title="Municípios", icon="🏛️", url_path="municipios"),
    st.Page(lambda: None, title="Dados", icon="📋", url_path="dados"),
])

with st.sidebar:
    st.markdown("---\n#### Filtros")
    f_fonte = st.multiselect("Fonte", sorted(base["Fonte"].dropna().unique()), placeholder="(Tudo)")
    f_uf = st.multiselect("UF", sorted(base["UF"].dropna().unique()), placeholder="(Tudo)")
    cidades = base[base["UF"].isin(f_uf)] if f_uf else base   # cidade depende da UF escolhida
    f_cidade = st.multiselect("Cidade", sorted(cidades["Cidade"].dropna().unique()), placeholder="(Tudo)")
    f_vereador = st.text_input("Vereador", placeholder="Digite parte do nome")

    # Período: limitado a datas plausíveis (a base tem alguns protocolos com ano 206, 1899, 2029)
    datas_ok = base["Data do protocolo"].between(pd.Timestamp("2000-01-01"), REF)
    dmin, dmax = base.loc[datas_ok, "Data do protocolo"].min().date(), REF.date()
    f_periodo = st.date_input("Período do protocolo", (dmin, dmax), min_value=dmin, max_value=dmax,
                              format="DD/MM/YYYY")

    st.markdown(f'<div class="atualizacao">Última atualização<br><b>{REF:%d/%m/%Y}</b></div>',
                unsafe_allow_html=True)

# Aplica os filtros
df = base
if f_fonte:
    df = df[df["Fonte"].isin(f_fonte)]
if f_uf:
    df = df[df["UF"].isin(f_uf)]
if f_cidade:
    df = df[df["Cidade"].isin(f_cidade)]
if f_vereador:
    df = df[df["Vereador"].str.contains(f_vereador, case=False, na=False)]
# Só filtra se o usuário alterar o intervalo padrão — assim linhas com data de protocolo
# vazia/inválida continuam contando nos totais. Com só a 1ª data escolhida, o filtro fica inativo.
if len(f_periodo) == 2 and tuple(f_periodo) != (dmin, dmax):
    ini, fim = pd.Timestamp(f_periodo[0]), pd.Timestamp(f_periodo[1])
    df = df[df["Data do protocolo"].between(ini, fim)]

if df.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# Recortes usados em mais de uma tela
ult30 = df[df["Data do protocolo"].between(INI_30, REF)]
ant30 = df[df["Data do protocolo"].between(INI_60, INI_30, inclusive="left")]
em_tram = (df["Status do PL"] == "Em tramitação").sum()

# Layout de gráfico padrão (fundo transparente, fonte escura)
LAYOUT = dict(margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
              plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#374151"), separators=",.")

# ============================================================================
# TELA 1 — VISÃO GERAL
# ============================================================================
if pagina.title == "Visão Geral":
    st.markdown(f"#### 📍 {df['Cidade'].nunique()} cidades | {df['UF'].nunique()} UFs")

    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Total Ementas", fmt(df["Ementa"].notna().sum()))
    with c2: card("Em tramitação", fmt(em_tram))
    with c3: card("Não tramitando", fmt(len(df) - em_tram))
    with c4: card("Vereadores", fmt(df["Vereador"].nunique()))
    st.write("")

    g1, g2, g3 = st.columns([2.2, 1.2, 1.2])

    # Evolução dos protocolos: soma por mês do ano (jan–dez), todos os anos juntos, como no Tableau
    with g1, st.container(border=True):
        st.markdown("**Evolução dos protocolos**")
        mes = (df["Data do protocolo"].dt.month.value_counts()
               .reindex(range(1, 13), fill_value=0).reset_index())
        mes.columns = ["mes", "qtd"]
        mes["Mês"] = [MESES[m - 1] for m in mes["mes"]]
        fig = px.area(mes, x="Mês", y="qtd", markers=True)
        fig.update_traces(line_color=VERDE_ESCURO, fillcolor="rgba(30,77,69,.28)",
                          hovertemplate="%{x}: %{y:,.0f} protocolos<extra></extra>")
        fig.update_layout(**LAYOUT, height=330, xaxis_title=None, yaxis_title=None)
        fig.update_yaxes(tickformat="~s", gridcolor="#EEE")
        st.plotly_chart(fig, width="stretch")

    # Top municípios: % do total de PLs (o Tableau mostra ~15 barras com rolagem)
    with g2, st.container(border=True):
        st.markdown("**Top municípios**")
        top = df["Cidade"].value_counts(normalize=True).head(15).sort_values().reset_index()
        top.columns = ["Cidade", "pct"]
        fig = px.bar(top, x="pct", y="Cidade", orientation="h",
                     text=[pct(v * 100, 3) for v in top["pct"]])
        fig.update_traces(marker_color=VERDE_MEDIO, textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}: %{text}<extra></extra>")
        fig.update_layout(**LAYOUT, height=330, xaxis_visible=False, yaxis_title=None,
                          xaxis_range=[0, top["pct"].max() * 1.6])   # espaço para os rótulos
        st.plotly_chart(fig, width="stretch")

    # Ranking 30 dias como tabela com barra de progresso (equivale ao "heat table" do Tableau)
    with g3, st.container(border=True):
        st.markdown("**Ranking municípios últimos 30 dias**")
        rk = ult30["Cidade"].value_counts().reset_index()
        rk.columns = ["Município", "Qtd"]
        rk["Barra"] = rk["Qtd"]   # coluna só visual: barra proporcional ao valor
        st.dataframe(rk, hide_index=True, height=330, width="stretch", column_config={
            "Qtd": st.column_config.NumberColumn("Qtd", width="small"),
            "Barra": st.column_config.ProgressColumn(" ", format=" ", color=VERDE_MEDIO, min_value=0,
                                                     max_value=int(rk["Qtd"].max() or 1))})

    k1, k2, k3, _ = st.columns([1.1, 1.1, 1.1, 1.2])
    with k1: card("Matérias nos últimos 30 dias", fmt(len(ult30)), "📅 atividade recente")
    with k2: card("Vereadores últimos 30 dias", fmt(ult30["Vereador"].nunique()),
                  "👤 vereadores com atividade recente")
    with k3: card("Cidades ativas últimos 30 dias", fmt(ult30["Cidade"].nunique()),
                  "🏙️ cidades com atividade recente")

# ============================================================================
# TELA 2 — MUNICÍPIOS
# ============================================================================
elif pagina.title == "Municípios":
    st.markdown("### 🏙️ Municípios\nPanorama e análise da atividade municipal")

    n_cid = df["Cidade"].nunique()
    ativos, ativos_ant = ult30["Cidade"].nunique(), ant30["Cidade"].nunique()

    # "Sem atualização": municípios cuja última atualização é anterior a REF-30 dias.
    # Comparação: mesma conta feita 30 dias antes (referência = REF-30).
    ult_atual = df.groupby("Cidade")["Data da última atualização"].max()
    sem_atu = (ult_atual < INI_30).sum()
    sem_atu_ant = (ult_atual[ult_atual < INI_30] < INI_60).sum()
    var_sem = (sem_atu / sem_atu_ant - 1) * 100 if sem_atu_ant else 0

    # Variação mensal: protocolos do mês de referência vs mês anterior
    p = df["Data do protocolo"].dt.to_period("M")
    mes_ref = REF.to_period("M")
    n_mes, n_mes_ant = (p == mes_ref).sum(), (p == mes_ref - 1).sum()
    var_mes = (n_mes / n_mes_ant - 1) * 100 if n_mes_ant else 0

    seta = lambda v: "↑" if v >= 0 else "↓"
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Municípios ativos", fmt(ativos),
                  f'<span class="verde">de {n_cid} monitorados</span>',
                  f"{seta(ativos - ativos_ant)} {ativos - ativos_ant:+d} vs. período anterior")
    with c2: card("Municípios sem atualização", fmt(sem_atu),
                  f'<span class="verde">de {n_cid} monitorados</span> · há mais de 30 dias',
                  f"{seta(var_sem)} {pct(var_sem, 0)} vs. período anterior")
    with c3: card("Taxa de tramitação", pct(em_tram / len(df) * 100, 2),
                  "das matérias seguem em tramitação")
    with c4: card("Variação mensal", pct(var_mes, 0), "de protocolos",
                  f"{seta(var_mes)} {MESES[mes_ref.month - 1]} vs. mês anterior")
    st.write("")

    m1, m2 = st.columns([1, 1.15])

    # Mapa coroplético por UF — protocolos nos últimos 30 dias
    with m1, st.container(border=True):
        st.markdown("**Distribuição geográfica dos municípios monitorados**")
        uf30 = ult30["UF"].value_counts().reset_index()
        uf30.columns = ["UF", "Protocolos 30d"]
        try:
            geo = carregar_geojson()
            fig = px.choropleth(uf30, geojson=geo, locations="UF", featureidkey="properties.sigla",
                                color="Protocolos 30d",
                                color_continuous_scale=["#D7ECE9", "#6FA9B5", "#3E6A99"])
            fig.update_geos(fitbounds="locations", showcountries=True, countrycolor="#BDBDBD",
                            showland=True, landcolor="#E5E5E5", showocean=False,
                            showframe=False, showcoastlines=False, bgcolor="rgba(0,0,0,0)")
            fig.update_layout(**LAYOUT, height=420, coloraxis_colorbar=dict(
                title="Qtd protocolos 30d", orientation="h", y=-0.05, thickness=10))
            st.plotly_chart(fig, width="stretch")
        except Exception:
            # Sem internet para baixar o contorno dos estados: mostra barras por UF
            st.info("Mapa indisponível (sem acesso ao arquivo de contornos). Exibindo por UF.")
            fig = px.bar(uf30, x="UF", y="Protocolos 30d", color_discrete_sequence=[VERDE_MEDIO])
            fig.update_layout(**LAYOUT, height=420)
            st.plotly_chart(fig, width="stretch")

    # Ranking de municípios com atividade recente
    with m2, st.container(border=True):
        st.markdown("**Ranking de municípios com atividade recente**  \núltimos 30 dias")
        rk = ult30.groupby(["Cidade", "UF"]).size().sort_values(ascending=False).reset_index(name="Qtd")
        rk.insert(0, "#", range(1, len(rk) + 1))
        st.dataframe(rk, hide_index=True, height=420, width="stretch")

# ============================================================================
# TELA 3 — DADOS (tabela interativa)
# ============================================================================
else:
    st.markdown("### 📋 Dados\nConsulta aos projetos de lei (respeita os filtros da barra lateral)")

    b1, b2, b3 = st.columns([2, 1, 2])
    busca = b1.text_input("🔎 Busca geral", placeholder="Procura o texto em todas as colunas")
    col_filtro = b2.selectbox("Filtrar coluna", ["(nenhuma)"] + list(df.columns))
    txt_filtro = b3.text_input("Contém", disabled=col_filtro == "(nenhuma)")

    tab = df
    if busca:
        mask = tab.astype(str).apply(lambda s: s.str.contains(busca, case=False, regex=False)).any(axis=1)
        tab = tab[mask]
    if col_filtro != "(nenhuma)" and txt_filtro:
        tab = tab[tab[col_filtro].astype(str).str.contains(txt_filtro, case=False, regex=False)]

    st.caption(f"{fmt(len(tab))} registros · clique no cabeçalho de uma coluna para ordenar")

    # Ordenação: clique no cabeçalho (nativo do st.dataframe). Datas exibidas em dd/mm/aaaa.
    cfg = {c: st.column_config.DateColumn(c, format="DD/MM/YYYY") for c in COLUNAS_DATA}
    cfg |= {c: st.column_config.LinkColumn(c, display_text="abrir")
            for c in ["Link da Lei", "Link do PDF", "Link do PL"]}
    cfg["ID"] = None   # oculta o ID técnico
    st.dataframe(tab, hide_index=True, width="stretch", height=560, column_config=cfg)

    # Download: ; como separador e utf-8-sig para abrir certo no Excel em português
    saida = tab.copy()
    for c in COLUNAS_DATA:
        saida[c] = saida[c].dt.strftime("%d/%m/%Y")
    st.download_button("⬇️ Baixar dados filtrados (CSV)",
                       saida.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="pls_filtrados.csv", mime="text/csv")
