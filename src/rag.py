def process_query(query, vectorstore):
    docs = vectorstore.similarity_search(query, k=3)

    resposta = "\n".join([d.page_content for d in docs])

    fontes = [{"texto": d.page_content} for d in docs]

    return resposta, fontes
