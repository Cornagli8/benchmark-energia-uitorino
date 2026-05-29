# Benchmark Materia Prima Energetica · UI Torino

Dashboard di confronto tra le Convenzioni **MMPOWER / MMGAS** di UI Torino e le top 10 offerte attive sul mercato libero italiano (energia elettrica e gas).

## Componenti del repo

| File / cartella | Cos'è |
|---|---|
| `app.py` | App Streamlit (dashboard interattiva) |
| `data/data.json` | Risultati aggregati generati dal notebook (`Benchmark Confronto.ipynb`, cella 5.6) |
| `requirements.txt` | Dipendenze Python per Streamlit Community Cloud |
| `.streamlit/config.toml` | Tema dell'app |
| `index.html` | Landing page statica (fallback) |
| `grafico_confronto_*.html` | Versioni statiche dei grafici (Plotly standalone) |

## Eseguire localmente

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## Aggiornare i dati

Quando i dati di partenza cambiano (nuovo mese, nuove offerte):

1. Esegui le celle `5.1 → 5.6` del notebook `BENCHMARK/Benchmark Confronto.ipynb`. La cella **5.6** riscrive `data/data.json`.
2. Commit & push:
   ```powershell
   cd pubblica_grafici
   git add data/data.json
   git commit -m "aggiorna dati mese YYYY-MM"
   git push
   ```
3. Streamlit Community Cloud rigenera l'app automaticamente in ~1 minuto.

## Deploy su Streamlit Community Cloud

1. Vai su <https://share.streamlit.io>
2. Login con GitHub (account `Cornagli8`)
3. **New app** → seleziona repo `Cornagli8/benchmark-energia-uitorino`, branch `main`, main file `app.py`
4. Ottieni l'URL pubblico (es. `https://benchmark-energia-uitorino.streamlit.app/`)
