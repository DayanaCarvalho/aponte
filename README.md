# Painel de acompanhamento de PLs (Streamlit)

## Rodar localmente
1. Coloque a planilha na mesma pasta do `app.py` com o nome **`dados_consolidados.csv`**.
2. No terminal, dentro da pasta:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Abre em http://localhost:8501

## Publicar no Streamlit Community Cloud
1. Crie um repositório no GitHub e suba `app.py`, `requirements.txt` e `dados_consolidados.csv`
   (o CSV tem ~16 MB, abaixo do limite de 100 MB do GitHub).
2. Acesse https://share.streamlit.io → **Create app** → escolha o repositório, branch `main`
   e arquivo principal `app.py` → **Deploy**.
3. Para atualizar os dados, basta fazer commit de um novo `dados_consolidados.csv`.

> Atenção: repositório público = dados públicos. Se a base não puder ser exposta,
> use repositório privado (o Community Cloud aceita) ou outro servidor.
