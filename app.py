import streamlit as st
import tempfile
import base64
import requests

# Banco JSON
from json_db import init_db, load_db

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


# -----------------------------------------------------
# Inicializar banco ao iniciar o app
# -----------------------------------------------------
init_db()

st.set_page_config(page_title="aiia | BANK", layout="wide")


# -----------------------------------------------------
# FUNDO PERSONALIZADO — usando imagem do GitHub RAW
# -----------------------------------------------------
def set_bg_from_url(img_url):
    """Baixa a imagem do GitHub RAW e define como fundo."""
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
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Texto branco para contraste */
        h1, h2, h3, h4, h5, h6, p, label, span, div {{
            color: white !important;
        }}

        /* Caixas sem fundo sólido */
        .stMarkdown, .stTextInput>div, .stSelectbox>div, .stButton>button {{
            background: rgba(0,0,0,0.40) !important;
            border-radius: 8px;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: rgba(0,0,0,0.55) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


set_bg_from_url("https://raw.githubusercontent.com/grupoorionai-svg/hakatonfmu/main/1.jpeg")


# -----------------------------------------------------
# TÍTULO NO ESTILO DA MARCA
# -----------------------------------------------------
st.markdown(
    """
    <h1 style="color:white; font-size:44px; font-weight:700; margin-top:-10px;">
        aiia | BANK
    </h1>
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
# ADICIONAR SALDO DE TESTE
# -----------------------------------------------------
if st.sidebar.button("💰 Adicionar saldo de teste (+ R$ 2.000)"):
    from json_db import load_db, save_db
    db = load_db()
    db["saldo"] += 2000
    save_db(db)
    st.sidebar.success("Saldo de teste adicionado!")
    st.rerun()


# -----------------------------------------------------
# BOTÃO DE RESET GERAL
# -----------------------------------------------------
if st.sidebar.button("🔄 Resetar Sistema (Limpar tudo)"):
    from json_db import save_db
    save_db({"saldo": 0.0, "transacoes": []})
    st.sidebar.success("Sistema resetado com sucesso!")
    st.rerun()



# =====================================================
#                     D A S H B O A R D
# =====================================================
if menu == "Dashboard":
    st.header("📊 Dashboard Financeiro Inteligente")

    data = load_db()
    transacoes = data["transacoes"]

    st.metric("Saldo atual", f"R$ {data['saldo']:.2f}")
    st.markdown("---")

    # ======================================================
    #   DASHBOARD PRO — GASTOS POR CATEGORIA (DINÂMICO)
    # ======================================================
    st.subheader("📊 Gastos por Categoria (PRO)")

    import plotly.graph_objects as go

    categoria_totais = {}
    for t in transacoes:
        if t["valor"] < 0:
            cat = t.get("categoria", "outros")
            categoria_totais[cat] = categoria_totais.get(cat, 0) + abs(t["valor"])

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

        lista_cores = [cores.get(cat, "#7f8c8d") for cat in labels]

        fig = go.Figure(
            data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=lista_cores),
                textinfo="label+percent",
                textfont=dict(size=14, color="white")
            )]
        )

        fig.update_layout(
            title="Distribuição dos Gastos",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5,
                font=dict(color="white")
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📌 Detalhamento por Categoria")

        for categoria, valor in categoria_totais.items():
            percentual = (valor / total) * 100
            cor = cores.get(categoria, "#7f8c8d")

            st.markdown(f"""
            <div style='margin-bottom:15px;'>
                <b style='color:white; font-size:18px;'>{categoria.capitalize()}</b>
                <span style='color:#ddd;'> — R$ {valor:.2f} ({percentual:.1f}%)</span>
                <div style='background:{cor}; height:14px; width:{percentual}%; border-radius:8px; margin-top:5px;'></div>
            </div>
            """, unsafe_allow_html=True)

        maior_categoria = max(categoria_totais, key=categoria_totais.get)
        st.markdown(f"""
        <div style='background:rgba(0,0,0,0.45); padding:15px; border-radius:10px; margin-top:20px; color:white;'>
            💡 Sua categoria mais cara é <b>{maior_categoria.capitalize()}</b>, 
            totalizando <b>R$ {categoria_totais[maior_categoria]:.2f}</b>.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Nenhuma despesa encontrada para gerar gráficos.")

    st.markdown("---")

    st.subheader("💸 Maiores gastos")
    despesas = [t for t in transacoes if t["valor"] < 0]

    if despesas:
        maiores = sorted(despesas, key=lambda x: x["valor"])[:5]
        for t in maiores:
            st.write(f"**{t['descricao']}** — R$ {abs(t['valor'])} — categoria: {t['categoria']}")
    else:
        st.info("Nenhuma despesa registrada.")

    st.markdown("---")

    st.subheader("📜 Últimas transações")
    for t in reversed(transacoes[-10:]):
        st.write(f"- **{t['tipo']}** — {t['descricao']} — R$ {t['valor']} — categoria: {t['categoria']}")


# =====================================================
#                  ENVIAR PDF
# =====================================================
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


# =====================================================
#                    PERGUNTA RAG
# =====================================================
elif menu == "Fazer Pergunta (RAG)":
    st.header("🧠 Pergunte algo sobre os PDFs")

    pergunta = st.text_input("Digite sua pergunta:")

    if st.button("Enviar"):
        if not st.session_state.vectorstore:
            st.error("Nenhum PDF carregado ainda.")
        else:
            resposta, fontes = process_query(pergunta, st.session_state.vectorstore)
            st.markdown("### Resposta")
            st.write(resposta)

            st.markdown("### Fontes utilizadas")
            for f in fontes:
                st.write(f["texto"])


# =====================================================
#                     PIX
# =====================================================
elif menu == "PIX":
    st.header("⚡ Fazer PIX")

    chave = st.text_input("Chave PIX")
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Enviar PIX"):
        ok, msg = enviar_pix(chave, valor)
        st.success(msg) if ok else st.error(msg)


# =====================================================
#                   PAGAMENTOS
# =====================================================
elif menu == "Pagamentos":
    st.header("💳 Pagamento de Boleto")

    codigo = st.text_input("Código do boleto")
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Pagar"):
        ok, msg = pagar_boleto(codigo, valor)
        st.success(msg) if ok else st.error(msg)


# =====================================================
#                     RECARGAS
# =====================================================
elif menu == "Recargas":
    st.header("📱 Recarga de celular")

    numero = st.text_input("Número")
    operadora = st.selectbox("Operadora", ["Vivo", "Claro", "TIM", "Oi"])
    valor = st.number_input("Valor", min_value=1.0)

    if st.button("Recarregar"):
        ok, msg = fazer_recarga(numero, operadora, valor)
        st.success(msg) if ok else st.error(msg)


# =====================================================
#                   EMPRÉSTIMOS
# =====================================================
elif menu == "Empréstimos":
    st.header("🏦 Simulação de Empréstimo")

    valor = st.number_input("Valor desejado", min_value=100.0)

    if st.button("Contratar"):
        ok, total = contratar_emprestimo(valor)
        if ok:
            st.success(f"Empréstimo aprovado! Total final: R$ {total}")
        else:
            st.error(total)
