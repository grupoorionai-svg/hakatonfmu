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

        /* Texto branco por padrão para contraste sobre o fundo escuro */
        h1, h2, h3, h4, h5, h6, p, label, span, div, .css-1v0mbdj {{
            color: white !important;
        }}

        /* Sidebar translúcido */
        section[data-testid="stSidebar"] {{
            background: rgba(0,0,0,0.55) !important;
            color: white !important;
        }}

        /* Cards / blocos com leve fundo escuro e bordas arredondadas */
        .stMarkdown, .stFrame, .stTextInput, .stButton > button, .stSelectbox > div {{
            background: rgba(0,0,0,0.45) !important;
            border-radius: 10px;
        }}

        /* Aplica blur/transparência ao contêiner do gráfico Plotly para melhorar legibilidade */
        .stPlotlyChart > div {{
            background: rgba(0,0,0,0.45) !important;
            border-radius: 12px;
            padding: 8px;
            backdrop-filter: blur(4px);
        }}

        /* Ajustes gerais para evitar textos cortados */
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

# Chamar com RAW do GitHub (fallback caso /mnt/data não exista)
set_bg_from_url("https://raw.githubusercontent.com/grupoorionai-svg/hakatonfmu/main/1.jpeg")

# -----------------------------------------------------
# CABEÇALHO CENTRALIZADO (LOGO + TÍTULO) — usando base64 local
# -----------------------------------------------------
logo_path = "/mnt/data/1.jpeg"  # caminho local do arquivo que você enviou

# verifica se o arquivo existe e monta o base64
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_src = f"data:image/jpeg;base64,{logo_b64}"
else:
    # fallback para o RAW (caso não exista local) — ainda pode falhar por CORS
    logo_src = "https://raw.githubusercontent.com/grupoorionai-svg/hakatonfmu/main/1.jpeg"

st.markdown(
    f"""
    <style>
      /* garante prioridade ao header */
      .custom-header {{
        width:100% !important;
        display:flex !important;
        justify-content:center !important;
        align-items:center !important;
        padding:18px 0 !important;
      }}
      .custom-header-inner {{
        width:100% !important;
        max-width:1200px !important;
        display:flex !important;
        align-items:center !important;
        justify-content:center !important;
        gap:20px !important;
        background: rgba(0,0,0,0.45) !important;
        padding:18px 28px !important;
        border-radius:12px !important;
      }}
      .custom-header img {{
        height:72px !important;
        width:auto !important;
        object-fit:contain !important;
        border-radius:8px !important;
      }}
      .custom-header h1 {{
        color:white !important;
        font-size:48px !important;
        font-weight:800 !important;
        margin:0 !important;
        letter-spacing:1px !important;
      }}
    </style>

    <div class="custom-header">
      <div class="custom-header-inner">
        <img src="{logo_src}" alt="aiia | BANK"/>
        <h1>aiia | BANK</h1>
      </div>
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
# ADICIONAR SALDO DE TESTE
# -----------------------------------------------------
if st.sidebar.button("💰 Adicionar saldo de teste (+ R$ 2.000)"):
    db = load_db()
    db["saldo"] += 2000
    save_db(db)
    st.sidebar.success("Saldo de teste adicionado!")
    st.rerun()

# -----------------------------------------------------
# BOTÃO DE RESET GERAL
# -----------------------------------------------------
if st.sidebar.button("🔄 Resetar Sistema (Limpar tudo)"):
    save_db({"saldo": 0.0, "transacoes": []})
    st.sidebar.success("Sistema resetado com sucesso!")
    st.rerun()

# =====================================================
#                     D A S H B O A R D
# =====================================================
if menu == "Dashboard":
    st.header("📊 Dashboard Financeiro Inteligente")

    data = load_db()
    transacoes = data.get("transacoes", [])

    # Exibe saldo com st.metric (já existente)
    col1, col2, col3 = st.columns([1.5,1,1])
    with col1:
        st.metric("Saldo atual", f"R$ {data.get('saldo', 0.0):.2f}")
    with col2:
        entradas = sum(t.get("valor",0.0) for t in transacoes if t.get("valor",0.0) > 0)
        st.metric("Entradas (últimos)", f"R$ {entradas:.2f}")
    with col3:
        saidas = sum(abs(t.get("valor",0.0)) for t in transacoes if t.get("valor",0.0) < 0)
        st.metric("Saídas (últimos)", f"R$ {saidas:.2f}")

    st.markdown("---")

    # ======================================================
    #   DASHBOARD PRO — GASTOS POR CATEGORIA (DINÂMICO)
    # ======================================================
    st.subheader("📊 Gastos por Categoria (PRO)")

    # 1. SOMA DOS GASTOS POR CATEGORIA
    categoria_totais = {}
    for t in transacoes:
        if t.get("valor", 0.0) < 0:
            cat = t.get("categoria", "outros")
            categoria_totais[cat] = categoria_totais.get(cat, 0) + abs(t.get("valor", 0.0))

    if categoria_totais:
        categoria_totais = dict(sorted(categoria_totais.items(), key=lambda x: x[1], reverse=True))

        labels = list(categoria_totais.keys())
        values = list(categoria_totais.values())
        total = sum(values) if values else 1.0

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

        # pull: destaque nas 3 maiores fatias (pequeno deslocamento)
        pull = []
        for i, v in enumerate(values):
            if i < 3:
                pull.append(0.08)  # destaque pequeno para as 3 maiores
            else:
                pull.append(0.0)

        # Figura Plotly — Donut mais legível com labels externos e linhas
        fig = go.Figure(
            data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=lista_cores, line=dict(color="black", width=1)),
                textinfo="percent",                 # mostra só percentual nas fatias
                textfont=dict(size=16, color="white"),
                hoverinfo="label+value+percent",
                sort=False,
                pull=pull,
                direction="clockwise",
                textposition="outside"
            )]
        )

        # Atualizações seguras e compatíveis (apenas parâmetros suportados pelo Pie)
        fig.update_traces(
            hoverlabel=dict(font_size=16),
        )

        fig.update_layout(
            title=dict(
                text="Distribuição dos Gastos",
                font=dict(size=26, color="white"),
                x=0.5
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=80, b=20),

            # Legenda mais limpa e grande
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.30,
                xanchor="center",
                x=0.5,
                font=dict(size=14, color="white")
            )
        )

        # Renderiza o gráfico (uso de container para aplicar o CSS blur)
        st.plotly_chart(fig, use_container_width=True)

        # 3. LISTAGEM DETALHADA (com barras visuais)
        st.markdown("### 📌 Detalhamento por Categoria")
        for categoria, valor in categoria_totais.items():
            percentual = (valor / total) * 100
            cor = cores.get(categoria, "#7f8c8d")
            st.markdown(f"""
            <div style='margin-bottom:12px;'>
                <div style='display:flex; justify-content:space-between; align-items:center; gap:8px;'>
                    <div style='display:flex; align-items:center; gap:10px;'>
                        <div style='width:12px; height:12px; background:{cor}; border-radius:3px;'></div>
                        <b style='color:white; font-size:16px;'>{categoria.capitalize()}</b>
                    </div>
                    <span style='color:#ddd;'>R$ {valor:.2f} — {percentual:.1f}%</span>
                </div>
                <div style='background:rgba(255,255,255,0.08); height:12px; width:100%; border-radius:8px; margin-top:6px;'>
                    <div style='background:{cor}; height:12px; width:{percentual}%; border-radius:8px;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 4. CATEGORIA MAIS CARA
        maior_categoria = max(categoria_totais, key=categoria_totais.get)
        st.markdown(f"""
        <div style='background:rgba(0,0,0,0.45); padding:12px; border-radius:10px; margin-top:8px; color:white;'>
            💡 Sua categoria mais cara é <b>{maior_categoria.capitalize()}</b>, 
            com um total de <b>R$ {categoria_totais[maior_categoria]:.2f}</b>.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Nenhuma despesa encontrada para gerar gráficos.")

    st.markdown("---")

    # --------------------------
    # Maiores gastos
    # --------------------------
    st.subheader("💸 Maiores gastos")
    despesas = [t for t in transacoes if t.get("valor", 0.0) < 0]

    if despesas:
        maiores = sorted(despesas, key=lambda x: x.get("valor",0.0))[:5]
        for t in maiores:
            st.write(f"**{t.get('descricao','(sem descrição)')}** — R$ {abs(t.get('valor',0.0)):.2f} — categoria: {t.get('categoria','outros')}")
    else:
        st.info("Nenhuma despesa registrada.")

    st.markdown("---")

    # --------------------------
    # Últimas transações
    # --------------------------
    st.subheader("📜 Últimas transações")
    for t in reversed(transacoes[-10:]):
        st.write(f"- **{t.get('tipo','') }** — {t.get('descricao','')} — R$ {t.get('valor',0.0):.2f} — categoria: {t.get('categoria','')}")

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
                st.write(f.get("texto",""))

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
