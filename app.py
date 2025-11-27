# app.py
import streamlit as st
import tempfile
import base64
import requests
import os

# Banco JSON
from json_db import init_db, load_db, save_db

# PDFs e RAG
from src.pdf_loader import load_and_index_pdfs
from src.rag import process_query
from financeiro import extrair_transacoes_do_texto, salvar_transacoes_extraidas
from langchain_community.document_loaders import PyPDFLoader

# Serviços financeiros
from services.pix import enviar_pix
from services.pagamentos import pagar_boleto
from services.recargas import fazer_recarga
from services.emprestimos import contratar_emprestimo

# Visualização
import plotly.graph_objects as go

# -----------------------------------------------------
# Inicializar banco ao iniciar o app
# -----------------------------------------------------
init_db()

st.set_page_config(page_title="aiia | BANK", layout="wide")

# -----------------------------------------------------
# FUNDO PERSONALIZADO — usando imagem do GitHub RAW
# -----------------------------------------------------
def set_bg_from_url(img_url):
    """Baixa a imagem do GitHub RAW e define como fundo (base64)."""
    try:
        resp = requests.get(img_url, timeout=10)
        resp.raise_for_status()
        encoded = base64.b64encode(resp.content).decode()
    except Exception as e:
        st.error(f"Não foi possível carregar a imagem de fundo: {e}")
        return

    st.markdown(
        f"""
        <style>
        /* Fundo da aplicação */
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Texto branco por padrão */
        h1, h2, h3, h4, h5, h6, p, label, span, div {{
            color: white !important;
        }}

        /* Sidebar translúcido */
        section[data-testid="stSidebar"] {{
            background: rgba(0,0,0,0.55) !important;
            color: white !important;
        }}

        .stMarkdown, .stFrame, .stTextInput, .stButton > button, .stSelectbox > div {{
            background: rgba(0,0,0,0.45) !important;
            border-radius: 10px;
        }}

        .stPlotlyChart > div {{
            background: rgba(0,0,0,0.45) !important;
            border-radius: 12px;
            padding: 8px;
            backdrop-filter: blur(4px);
        }}

        .element-container, .block-container {{
            padding-top: 8px !important;
            padding-left: 18px !important;
            padding-right: 18px !important;
            padding-bottom: 18px !important;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

# Chama o fundo
set_bg_from_url("https://raw.githubusercontent.com/grupoorionai-svg/hakatonfmu/main/1.jpeg")

# -----------------------------------------------------
# CABEÇALHO CENTRALIZADO — APENAS TEXTO
# -----------------------------------------------------
st.markdown(
    """
    <style>
        .title-box {
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 22px 0;
            background: rgba(0,0,0,0.45);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .title-box h1 {
            font-size: 48px;
            font-weight: 800;
            margin: 0;
            color: white !important;
            letter-spacing: 1px;
        }
    </style>

    <div class="title-box">
        <h1>aiia | BANK</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------
# ESTADO GLOBAL
# -----------------------------------------------------
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = []

# -----------------------------------------------------
# MENU LATERAL
# -----------------------------------------------------
menu = st.sidebar.radio(
    "Menu",
    ["Dashboard", "Enviar PDF", "Fazer Pergunta (RAG)", "PIX", "Pagamentos", "Recargas", "Empréstimos"]
)

# -----------------------------------------------------
# ADICIONAR SALDO
# -----------------------------------------------------
if st.sidebar.button("💰 Adicionar saldo de teste (+ R$ 2.000)"):
    db = load_db()
    db["saldo"] += 2000
    save_db(db)
    st.sidebar.success("Saldo de teste adicionado!")
    st.rerun()

# -----------------------------------------------------
# RESET
# -----------------------------------------------------
if st.sidebar.button("🔄 Resetar Sistema (Limpar tudo)"):
    save_db({"saldo": 0.0, "transacoes": []})
    st.sidebar.success("Sistema resetado com sucesso!")
    st.rerun()

# ============================
# DASHBOARD
# ============================
if menu == "Dashboard":
    st.header("📊 Dashboard Financeiro Inteligente")

    data = load_db()
    transacoes = data.get("transacoes", [])

    col1, col2, col3 = st.columns([1.5, 1, 1])
    with col1:
        st.metric("Saldo atual", f"R$ {data.get('saldo', 0.0):.2f}")
    with col2:
        entradas = sum(t["valor"] for t in transacoes if t["valor"] > 0)
        st.metric("Entradas (últimos)", f"R$ {entradas:.2f}")
    with col3:
        saidas = sum(abs(t["valor"]) for t in transacoes if t["valor"] < 0)
        st.metric("Saídas (últimos)", f"R$ {saidas:.2f}")

    st.markdown("---")

    # GASTOS POR CATEGORIA
    st.subheader("📊 Gastos por Categoria (PRO)")

    categoria_totais = {}
    for t in transacoes:
        if t["valor"] < 0:
            categoria = t.get("categoria", "outros")
            categoria_totais[categoria] = categoria_totais.get(categoria, 0) + abs(t["valor"])

    if categoria_totais:
        categoria_totais = dict(sorted(categoria_totais.items(), key=lambda x: x[1], reverse=True))

        labels = list(categoria_totais.keys())
        values = list(categoria_totais.values())
        total = sum(values)

        cores = {
            "luz": "#f39c12",
            "água": "#3498db",
            "educação": "#9b59b6",
            "internet": "#1abc9c",
            "saúde": "#e74c3c",
            "lazer": "#e67e22",
            "alimentação": "#2ecc71",
            "supermercado": "#6a5acd",
            "transporte": "#ff79c6",
            "pagamentos": "#8be9fd",
            "pix": "#bd93f9",
            "outros": "#7f8c8d"
        }

        fig = go.Figure(
            data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=[cores.get(i, "#7f8c8d") for i in labels]),
                textinfo="percent",
                textfont=dict(size=16, color="white"),
                hoverinfo="label+value+percent",
                textposition="outside"
            )]
        )

        fig.update_layout(
            title="Distribuição dos Gastos",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Nenhuma despesa encontrada para gerar gráficos.")

    st.markdown("---")

    # MAIORES GASTOS
    st.subheader("💸 Maiores gastos")
    despesas = [t for t in transacoes if t["valor"] < 0]

    if despesas:
        maiores = sorted(despesas, key=lambda x: x["valor"])[:5]
        for t in maiores:
            st.write(
                f"**{t['descricao']}** — R$ {abs(t['valor']):.2f} — categoria: {t.get('categoria','outros')}"
            )
    else:
        st.info("Nenhuma despesa registrada.")

    st.markdown("---")

    # ÚLTIMAS TRANSAÇÕES
    st.subheader("📜 Últimas transações")
    for t in reversed(transacoes[-10:]):
        st.write(
            f"- **{t.get('tipo','')}** — {t.get('descricao','')} — R$ {t.get('valor',0):.2f} — categoria: {t.get('categoria','')}"
        )

# ============================
# ENVIAR PDF
# ============================
elif menu == "Enviar PDF":
    st.header("📁 Enviar PDFs de extratos, faturas ou comprovantes")

    uploaded = st.file_uploader("Envie PDFs", type=["pdf"], accept_multiple_files=True)

    if uploaded:
        st.session_state.pdf_bytes = [u.getvalue() for u in uploaded]

        with st.spinner("Lendo e indexando PDFs..."):
            st.session_state.vectorstore = load_and_index_pdfs(st.session_state.pdf_bytes)

        st.success("PDFs carregados com sucesso!")
        st.subheader("🔍 Extraindo transações dos PDFs...")

        for u in uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(u.getvalue())
                tmp.flush()

                loader = PyPDFLoader(tmp.name)
                paginas = loader.load()

                texto = "\n".join([p.page_content for p in paginas])

                st.write("📄 Texto extraído:", texto[:1000])

                trans = extrair_transacoes_do_texto(texto)

                st.write("🔍 Transações encontradas:", trans)

                salvar_transacoes_extraidas(trans)

        st.success("Transações adicionadas ao banco!")

# ============================
# RAG
# ============================
elif menu == "Fazer Pergunta (RAG)":
    st.header("🧠 Pergunte algo sobre os PDFs")

    pergunta = st.text_input("Digite sua pergunta:")

    if st.button("Enviar"):
        if not st.session_state.vectorstore:
            st.error("Nenhum PDF carregado ainda.")
        else:
            resposta, fontes = process_query(pergunta, st.session_state.vectorstore)
            st.write("### Resposta")
            st.write(resposta)
            st.write("### Fontes utilizadas")
            for f in fontes:
                st.write(f.get("texto", ""))

# ============================
# PIX
# ============================
elif menu == "PIX":
    st.header("⚡ Fazer PIX")
    chave = st.text_input("Chave PIX")
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Enviar PIX"):
        ok, msg = enviar_pix(chave, valor)
        st.success(msg) if ok else st.error(msg)

# ============================
# PAGAMENTOS
# ============================
elif menu == "Pagamentos":
    st.header("💳 Pagamento de Boleto")
    codigo = st.text_input("Código do boleto")
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Pagar"):
        ok, msg = pagar_boleto(codigo, valor)
        st.success(msg) if ok else st.error(msg)

# ============================
# RECARGAS
# ============================
elif menu == "Recargas":
    st.header("📱 Recarga de celular")
    numero = st.text_input("Número")
    operadora = st.selectbox("Operadora", ["Vivo", "Claro", "TIM", "Oi"])
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Recarregar"):
        ok, msg = fazer_recarga(numero, operadora, valor)
        st.success(msg) if ok else st.error(msg)

# ============================
# EMPRÉSTIMOS
# ============================
elif menu == "Empréstimos":
    st.header("🏦 Simulação de Empréstimo")
    valor = st.number_input("Valor desejado", min_value=100.0)

    if st.button("Contratar"):
        ok, total = contratar_emprestimo(valor)
        st.success(f"Empréstimo aprovado! Total final: R$ {total}") if ok else st.error(total)
