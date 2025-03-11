import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    /* Forçar a largura máxima da página */
    .main .block-container {
        max-width: 100vw !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    /* Fundo branco e texto azul */
    .stApp {
        background-color: #FFFFFF; /* Fundo branco */
        color: #201747; /* Letras azul (R32, G23, B71) */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #201747; /* Títulos em azul */
        text-align: center; /* Centralizar títulos */
    }
    /* Garantir que todo texto, incluindo st.text, fique azul e centralizado */
    .stMarkdown, [data-testid="stMarkdown"] p, [data-testid="stText"], .stText {
        color: #201747 !important; /* Texto em azul */
        text-align: center !important; /* Centralizar texto */
    }
    /* Ajustar tabelas */
    [data-testid="stDataframe"] table {
        font-size: 12px;
        color: #201747; /* Texto das tabelas em azul */
        margin-left: auto;
        margin-right: auto;
    }
    [data-testid="stDataframe"] th {
        background-color: #201747; /* Cabeçalhos das tabelas em azul */
        color: #FFFFFF; /* Texto dos cabeçalhos em branco */
        text-align: center; /* Centralizar cabeçalhos */
    }
    [data-testid="stDataframe"] td {
        color: #201747;
        text-align: center; /* Centralizar conteúdo das células */
    }
    </style>
    """,
    unsafe_allow_html=True
)

col_logo1, col_logo2, col_logo3 = st.columns([3, 4, 1])
with col_logo1:
    st.image("logo_VLF.png", width=190)
with col_logo3:
    st.image("logo_cenibra.png", width=100)

@st.cache_data
def obter_dados_processo(url, headers, numero_processo):
    payload = {
        "query": {
            "term": {
                "numeroProcesso": numero_processo
            }
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.write(f"Erro ao buscar processo {numero_processo}: {response.status_code}")
        return None

# Mapeamento dos 4 últimos dígitos para cidades/comarcas
codigo_comarcas = {
    "0034": "Coronel Fabriciano",
    "0089": "Coronel Fabriciano",
    "0033": "Coronel Fabriciano",
    "0097": "Coronel Fabriciano",
    "0090": "Guanhães",
    "0064": "João Monlevade",
    "0102": "João Monlevade",
    "0091": "Nova Lima"
}

def extrair_cidade(orgao, numero_processo):
    cidades = ["Coronel Fabriciano", "Guanhães", "João Monlevade", "Belo Horizonte", "Caratinga", "Itabira", "Ouro Preto"]
    for cidade in cidades:
        if cidade.upper() in orgao.upper():
            return cidade
    codigo = numero_processo[-4:]
    return codigo_comarcas.get(codigo, "Desconhecida")

def formatar_numero_cnj(numero):
    """Formata o número do processo no padrão CNJ: XXXXXXX-XX.XXXX.X.XX.XXXX"""
    if len(numero) == 20:  # Verifica se o número tem o tamanho esperado
        return f"{numero[:7]}-{numero[7:9]}.{numero[9:13]}.{numero[13:14]}.{numero[14:16]}.{numero[16:20]}"
    return numero  # Retorna sem formatação se não tiver 20 dígitos

arquivo = "Base de Dados CENIBRA.xlsx"
base_dados = pd.read_excel(arquivo)
base_dados["Numero_Limpo"] = base_dados["Número do Processo"].str.replace(r'\D', '', regex=True)

url = "https://api-publica.datajud.cnj.jus.br/api_publica_trt3/_search"
headers = {
    "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
    "Content-Type": "application/json"
}

resultados = []
numeros_encontrados = []
for numero in base_dados["Numero_Limpo"]:
    dados = obter_dados_processo(url, headers, numero)
    if dados and "hits" in dados and dados["hits"]["hits"]:
        processo = dados["hits"]["hits"][0]["_source"]
        info = {
            "numeroProcesso": processo.get("numeroProcesso", ""),
            "classe": processo.get("classe", {}).get("nome", ""),
            "tribunal": processo.get("tribunal", ""),
            "grau": processo.get("grau", ""),
            "ultimo_movimento": processo.get("movimentos", [{}])[-1].get("nome", "") if processo.get("movimentos") else "",
            "sentenca_acordao": any(mov.get("nome", "").lower() in [
                "procedência", "procedência em parte", "improcedência",
                "provimento", "provimento em parte", "não-provimento",
                "homologação de acordo em execução ou em cumprimento de sentença",
                "homologação de transação", "extinção da execução ou do cumprimento da sentença"
            ] for mov in processo.get("movimentos", [])),
            "orgaoJulgador": processo.get("orgaoJulgador", {}).get("nome", ""),
            "audiencia_marcada": any(mov.get("nome", "").lower() == "audiência" for mov in processo.get("movimentos", [])),
            "assuntos": ", ".join([assunto.get("nome", "") for assunto in processo.get("assuntos", [])])
        }
        resultados.append(info)
        numeros_encontrados.append(numero)

# Filtrar processos ausentes e criar DataFrame com formatação
processos_ausentes = base_dados[~base_dados["Numero_Limpo"].isin(numeros_encontrados)][["Numero_Limpo"]]
processos_ausentes["Numero_Processo_Formatado"] = processos_ausentes["Numero_Limpo"].apply(formatar_numero_cnj)

df_processos = pd.DataFrame(resultados)
df_processos["Cidade"] = df_processos.apply(lambda row: extrair_cidade(row["orgaoJulgador"], row["numeroProcesso"]), axis=1)
df_processos["Numero_Processo_Formatado"] = df_processos["numeroProcesso"].apply(formatar_numero_cnj)

contagem_cidades = df_processos["Cidade"].value_counts().reset_index()
contagem_cidades.columns = ["Cidade", "Quantidade"]

coordenadas = {
    "Belo Horizonte": [-19.9173, -43.9345],
    "Coronel Fabriciano": [-19.5186, -42.6289],
    "Guanhães": [-18.7750, -42.9325],
    "João Monlevade": [-19.8100, -43.1736],
    "Caratinga": [-19.7911, -42.1392],
    "Itabira": [-19.6193, -43.2269],
    "Ouro Preto": [-20.3948, -43.5052],
    "Nova Lima": [-19.9856, -43.8469]
}
contagem_cidades["Latitude"] = contagem_cidades["Cidade"].map(lambda x: coordenadas.get(x, [None, None])[0])
contagem_cidades["Longitude"] = contagem_cidades["Cidade"].map(lambda x: coordenadas.get(x, [None, None])[1])

contagem_cidades_mapa = contagem_cidades.dropna(subset=['Latitude', 'Longitude'])

st.title("Panorama Processos CENIBRA - Minas Gerais")
st.subheader("Uma visão abrangente dos processos envolvendo a CENIBRA perante o Tribunal Regional do Trabalho da 3ª Região")
st.markdown(
    "<p style='text-align: center; color: #201747; font-size: 16px;'>"
    "Os processos listados abaixo foram retirados da certidão pública do TRT3 e atualizado pelo banco de dados digital do CNJ. "
    "Não estão incluídos processos em segredo de justiça. "
    "A base de dados do CNJ não é atualizada diariamente, ocasionando divergências em algumas informações"
    "</p>",
    unsafe_allow_html=True
)

# Criar o mapa
fig = go.Figure()
fig.add_trace(go.Scattermapbox(
    lat=contagem_cidades_mapa["Latitude"],
    lon=contagem_cidades_mapa["Longitude"],
    mode="markers+text",
    marker=dict(size=10, color="blue"),
    text=contagem_cidades_mapa["Cidade"],
    hovertemplate="<b>%{text}</b><br>Processos: %{customdata}<extra></extra>",
    customdata=contagem_cidades_mapa["Quantidade"],
    textposition="top center"
))

fig.update_layout(
    mapbox=dict(
        style="open-street-map",
        center=dict(lat=-19.9, lon=-43.9),
        zoom=6
    ),
    title="Distribuição de Processos por Cidade (TRT3)",
    showlegend=False
)

# Criar duas colunas no Streamlit com proporções ajustadas
col1, col2 = st.columns([2, 1])

# Mapa na coluna da esquerda
with col1:
    st.plotly_chart(fig, use_container_width=True)

# Ranking na coluna da direita
with col2:
    st.subheader("Processos por Cidade")
    ranking = contagem_cidades.sort_values(by="Quantidade", ascending=False)
    ranking = ranking.reset_index(drop=True)
    ranking.index = range(1, len(ranking) + 1)
    selecionado = st.dataframe(
        ranking[["Cidade", "Quantidade"]],
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        column_config={
            "Cidade": st.column_config.TextColumn("Cidade"),
            "Quantidade": st.column_config.NumberColumn(
                "Nº de Processos",
                width="small"
            )
        }
    )

# Exibir processos da cidade clicada
st.subheader("Processos da Cidade Selecionada")
if selecionado["selection"]["rows"]:
    indice_selecionado = selecionado["selection"]["rows"][0]
    cidade_clicada = ranking.iloc[indice_selecionado]["Cidade"]
    processos_cidade = df_processos[df_processos["Cidade"] == cidade_clicada][["Numero_Processo_Formatado", "classe", "ultimo_movimento"]]
    st.write(f"Processos em {cidade_clicada}:")
    st.dataframe(
        processos_cidade,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Numero_Processo_Formatado": st.column_config.TextColumn('Número do Processo'),
            "classe": st.column_config.TextColumn('Classe'),
            "ultimo_movimento": st.column_config.TextColumn('Último Andamento')
        }
    )
else:
    st.write("Clique em uma cidade no ranking para ver os processos.")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Pedidos Mais Recorrentes")
    todos_assuntos = df_processos["assuntos"].str.split(", ").explode().str.strip()
    contagem_assuntos = todos_assuntos.value_counts().reset_index()
    contagem_assuntos.columns = ["Pedido", "Quantidade"]
    contagem_assuntos = contagem_assuntos[contagem_assuntos["Pedido"] != ""]
    st.dataframe(
        contagem_assuntos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pedido": st.column_config.TextColumn("Pedido"),
            "Quantidade": st.column_config.NumberColumn("Incidência", width="small")
        }
    )

# Ranking de processos por grau de julgamento
with col4:
    st.subheader("Processos por Grau de Julgamento")
    contagem_graus = df_processos["grau"].value_counts().reset_index()
    contagem_graus.columns = ["Grau", "Quantidade"]
    contagem_graus["Grau"] = contagem_graus["Grau"].replace({"G1": "Primeiro Grau", "G2": "Segundo Grau"})
    st.dataframe(
        contagem_graus,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Grau": st.column_config.TextColumn("Grau"),
            "Quantidade": st.column_config.NumberColumn("Quantidade", width="small")
        }
    )

with st.expander("Processos Não Encontrados"):
    st.write(f"{len(processos_ausentes)} processos não foram encontrados na base de dados do CNJ.")
    st.dataframe(
        processos_ausentes[["Numero_Processo_Formatado"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Numero_Processo_Formatado": st.column_config.TextColumn("Número do Processo")
        }
    )