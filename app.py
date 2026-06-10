"""
Benchmark Materia Prima Gas&Power — Unione Industriali Torino
Dashboard Streamlit: confronto Convenzioni MMPOWER/MMGAS vs Top 10 offerte di mercato.

Esecuzione locale:
    streamlit run app.py

Deploy: https://share.streamlit.io  (repo Cornagli8/benchmark-energia-uitorino)
"""
import base64
import json
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# Config pagina + palette
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Benchmark Materia Prima Gas&Power — Unione Industriali Torino",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

C_CONV_ELE   = "#6BAED6"   # azzurro carta (Convenzione MMPOWER)
C_MERC_ELE   = "#2C5784"   # blu navy soft (Top 10 ELE)
C_CONV_GAS   = "#F0A35E"   # arancione pastello (Convenzione MMGAS)
C_MERC_GAS   = "#B4495C"   # granata/bordeaux (Top 10 GAS)
C_TEXT_DARK  = "#1F2937"
C_TEXT_MUTED = "#6B7280"

ICON_ELE = "⚡"
ICON_GAS = "🔥"

LABEL_CONV_ELE = "Convenzione MMPOWER"
LABEL_MERC_ELE = "Top 10 Offerte attive sul Mercato (ELE)"
LABEL_CONV_GAS = "Convenzione MMGAS"
LABEL_MERC_GAS = "Top 10 Offerte attive sul Mercato (GAS)"

# Ordini canonici
ORDINE_ELE = ["BT <=6 kW", "BT 6-50 kW", "BT >50 kW", "MT"]
ORDINE_GAS = ["Acqua Calda", "Riscaldamento + Acqua Calda",
              "Riscaldamento", "Uso Tecnologico + Riscaldamento"]

# Etichette abbreviate per leggibilita' grafici GAS (orizzontali, no diagonale)
GAS_LABEL_SHORT = {
    "Acqua Calda": "Acqua Calda",
    "Riscaldamento + Acqua Calda": "Risc. + Acqua Calda",
    "Riscaldamento": "Riscaldamento",
    "Uso Tecnologico + Riscaldamento": "Uso Tec. + Risc.",
}


def _short_gas(t):
    return GAS_LABEL_SHORT.get(t, t)


# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    """
<style>
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
    h1, h2, h3 { color: #0F172A; }
    h1 { border-bottom: 4px solid #6BAED6; padding-bottom: .4rem; margin-top: .6rem;
         text-align: center; }
    h2 { margin-top: 2.2rem; padding-left: .4rem; border-left: 5px solid #6BAED6; }
    h2.gas-section { border-left-color: #F0A35E; }

    /* Header loghi: 3 colonne con immagini centrate verticalmente, dimensioni
       indipendenti per ogni logo. MMPOWER spinto a sinistra, MMGAS a destra,
       UI centrato. */
    .logo-row {
        display: flex; justify-content: space-between; align-items: center;
        gap: 1rem; margin: .4rem 0 1.4rem 0; padding: 0 .5rem;
    }
    .logo-cell {
        flex: 1; display: flex; align-items: center; min-height: 140px;
    }
    .logo-cell img {
        display: block; max-width: 100%; height: auto;
        object-fit: contain;
    }
    .logo-cell.mmpower { justify-content: flex-start; }       /* a SINISTRA */
    .logo-cell.ui      { justify-content: center; }           /* CENTRO */
    .logo-cell.mmgas   { justify-content: flex-end; }         /* a DESTRA */
    .logo-cell.mmpower img { max-height: 115px; max-width: 280px; }
    .logo-cell.ui      img { max-height: 155px; max-width: 340px; } /* piu' grande */
    .logo-cell.mmgas   img { max-height: 115px; max-width: 280px; }

    .logo-pill {
        background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%);
        border: 1px solid #CBD5E1; border-radius: 10px;
        padding: .55rem 1.3rem; font-weight: 700;
        color: #1F2937; box-shadow: 0 1px 3px rgba(0,0,0,.05);
    }
    .logo-pill.mmpower { color: #2C5784; border-color: #6BAED6; }
    .logo-pill.ui-torino { color: #0F172A; background: #FFFFFF; font-size: 1.05rem;
                           padding: .55rem 1.6rem; border-color: #94A3B8; }
    .logo-pill.mmgas { color: #B4495C; border-color: #F0A35E; }

    /* Riquadro periodo */
    .periodo-box {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #CBD5E1; border-radius: 12px;
        padding: 1rem 1.4rem; margin: 1.2rem 0 1.6rem 0;
        display: flex; align-items: center; gap: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .periodo-label { font-size: .82rem; color: #6B7280; font-weight: 600;
                     text-transform: uppercase; letter-spacing: .5px; }
    .periodo-value { font-size: 1.3rem; font-weight: 700; color: #0F172A; margin-left:.4rem;}
    .periodo-meta { color: #6B7280; font-size: .9rem; margin-left:auto; }

    .desc-box {
        background-color: #F8FAFC; border-left: 3px solid #6BAED6;
        padding: .9rem 1.1rem; border-radius: 6px; margin: .8rem 0 1.4rem 0;
        color: #374151; font-size: .96rem;
    }
    .desc-box.gas { border-left-color: #F0A35E; }

    .footer-block {
        background-color: #F8FAFC; border: 1px solid #E5E7EB;
        border-radius: 10px; padding: 1.4rem 1.6rem; margin-top: 2.5rem;
    }

    .forn-pill {
        display: inline-block; padding: .3rem .7rem; margin: .25rem;
        background: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 999px;
        font-size: .88rem; color: #1F2937;
    }
    .forn-pill a { color: #2C5784; text-decoration: none; }
    .forn-pill a:hover { text-decoration: underline; }

    .num-evidenza {
        display: inline-block; background: linear-gradient(180deg,#F8FAFC,#E0E7FF);
        color: #1E3A8A; padding: .1rem .5rem; border-radius: 6px;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Caricamento dati
# ------------------------------------------------------------------
def carica_dati():
    p = Path(__file__).parent / "data" / "data.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


D = carica_dati()
if D is None:
    st.error(
        "⚠️ File `data/data.json` non trovato.\n\n"
        "Esegui la **cella 5.6** del notebook `Benchmark Confronto.ipynb` per generarlo, "
        "poi `git push` per aggiornare l'app online."
    )
    st.stop()

# Backward compatibility: se il data.json è in formato vecchio (no multi-mese),
# lo trasformiamo on-the-fly in formato v4 (mesi_disponibili / dati_per_mese)
if "dati_per_mese" not in D:
    _mese = D.get("meta", {}).get("mese_riferimento", "2026-03")
    D = {
        "version": 0,
        "meta": {
            "mese_default": _mese,
            "coeff_perdita_BT": D.get("meta", {}).get("coeff_perdita_BT", 0.10),
            "coeff_perdita_MT": D.get("meta", {}).get("coeff_perdita_MT", 0.038),
            "top_n": D.get("meta", {}).get("top_n", 10),
            "n_offerte_totali": D.get("meta", {}).get("n_offerte_totali", 0),
        },
        "mesi_disponibili": [_mese],
        "dati_per_mese": {_mese: {
            "meta_mese": {
                "mese": _mese,
                "PUN_eur_kWh": D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_TOT_eur_kWh": D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_BT_eur_kWh":  D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PUN_MT_eur_kWh":  D.get("meta", {}).get("PUN_eur_kWh", 0),
                "PSV_eur_Smc": D.get("meta", {}).get("PSV_eur_Smc", 0),
                "generazione_BT": D.get("meta", {}).get("generazione_BT", 0),
                "perdite_BT":     D.get("meta", {}).get("perdite_BT", 0),
                "mp_conv_BT":     D.get("meta", {}).get("mp_conv_BT", 0),
                "generazione_MT": D.get("meta", {}).get("generazione_MT", 0),
                "perdite_MT":     D.get("meta", {}).get("perdite_MT", 0),
                "mp_conv_MT":     D.get("meta", {}).get("mp_conv_MT", 0),
                "consumo_ele_totale_kwh": D.get("meta", {}).get("consumo_ele_totale_kwh", 0),
                "consumo_gas_totale_smc": D.get("meta", {}).get("consumo_gas_totale_smc", 0),
                "n_offerte_totali": D.get("meta", {}).get("n_offerte_totali", 0),
            },
            "confronto": D.get("confronto", []),
            "generale":  D.get("generale", []),
            "sensitivity": D.get("sensitivity", {"fattori": [1.0], "per_fascia": {}}),
        }},
        "offerte_tutte": D.get("offerte_tutte", []),
        "fornitori": D.get("fornitori", []),
        "fornitori_non_monitorati": D.get("fornitori_non_monitorati", []),
        "portali": D.get("portali", []),
    }

mesi_disp = D["mesi_disponibili"]
if not mesi_disp:
    st.warning("⚠️ Nessun mese disponibile nel file dati.")
    st.stop()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def mese_label(yyyymm: str) -> str:
    mesi = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    # Caso aggregato: ritorna stringa speciale
    if yyyymm == "__aggregato__" or "-" not in str(yyyymm):
        return "Tutti i mesi disponibili"
    y, m = yyyymm.split("-")
    return f"{mesi[int(m)]} {y}"


def _mese_aa(yyyymm: str) -> str:
    """Etichetta compatta 'mar-26'; per l'aggregato ritorna stringa vuota
    (il caption omette la parte 'mese-aa')."""
    ab = ["", "gen", "feb", "mar", "apr", "mag", "giu",
          "lug", "ago", "set", "ott", "nov", "dic"]
    if yyyymm == "__aggregato__" or "-" not in str(yyyymm):
        return ""
    y, m = yyyymm.split("-")
    return f"{ab[int(m)]}-{y[-2:]}"


def interp_sens(key: str, fattore: float, fallback_value: float = None) -> float:
    """Interpola linearmente il benchmark mercato sul fattore di consumo.
    Se per_fascia non disponibile (dati vecchi), usa il vettore totale ELE/GAS.
    Se nemmeno quello c'e', ritorna fallback_value."""
    fs = sens["fattori"]
    vs = sens.get("per_fascia", {}).get(key)
    if not vs:
        # Fallback: usa il vettore aggregato ELE o GAS (sens["ELE"]/sens["GAS"])
        comm = key.split("|")[0]
        vs = sens.get(comm)
    if not vs:
        return fallback_value
    if fattore <= fs[0]:
        return vs[0]
    if fattore >= fs[-1]:
        return vs[-1]
    for i in range(len(fs) - 1):
        if fs[i] <= fattore <= fs[i + 1]:
            t = (fattore - fs[i]) / (fs[i + 1] - fs[i])
            return vs[i] + t * (vs[i + 1] - vs[i])
    return vs[-1]


# ------------------------------------------------------------------
# HEADER: 3 loghi + titolo + periodo di osservazione
# ------------------------------------------------------------------
loghi_dir = Path(__file__).parent
logo_files = {
    "mmpower": loghi_dir / "logo_mmpower.png",
    "ui":      loghi_dir / "logo_ui.png",
    "mmgas":   loghi_dir / "logo_mmgas.png",
}


def _logo_img_or_placeholder(key, placeholder_html):
    p = logo_files[key]
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'<img src="data:image/png;base64,{b64}" alt="{key}" />'
    return placeholder_html


st.markdown(
    f"""
<div class="logo-row">
  <div class="logo-cell mmpower">{_logo_img_or_placeholder("mmpower",
       '<div class="logo-pill mmpower">⚡ MMPOWER</div>')}</div>
  <div class="logo-cell ui">{_logo_img_or_placeholder("ui",
       '<div class="logo-pill ui-torino">UNIONE INDUSTRIALI TORINO</div>')}</div>
  <div class="logo-cell mmgas">{_logo_img_or_placeholder("mmgas",
       '<div class="logo-pill mmgas">🔥 MMGAS</div>')}</div>
</div>
""",
    unsafe_allow_html=True,
)

mancanti = [k for k, p in logo_files.items() if not p.exists()]
if mancanti:
    st.caption(
        "<div style='text-align:center; color:#9CA3AF; font-size:.78rem;'>"
        "💡 Per sostituire i placeholder, salva "
        + ", ".join(f"<code>logo_{k}.png</code>" for k in mancanti)
        + " nella cartella <code>pubblica_grafici/</code>.</div>",
        unsafe_allow_html=True,
    )

# Titolo + descrizione introduttiva in un unico blocco con barra blu in fondo
st.markdown(
    """
<div style="text-align:center; border-bottom: 4px solid #6BAED6;
            padding-bottom: 1rem; margin: .6rem 0 1.6rem 0;">

  <h1 style="margin: 0 0 .7rem 0; padding: 0; border: none;
             font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI',
                          system-ui, -apple-system, 'Helvetica Neue', sans-serif;
             font-size: 2.9rem; font-weight: 800; letter-spacing: -0.025em;
             line-height: 1.1; color: #0F172A;">
    Benchmark Materia Prima Gas&amp;Power
  </h1>

  <p style="font-family: Georgia, 'Bookman Old Style', Cambria, serif;
            font-style: italic; font-size: 1.05rem; line-height: 1.55;
            color:#4B5563; margin: 0 auto; max-width: 880px;">
    Confronto fra il prezzo della materia prima delle Convenzioni
    <span style="color:#6BAED6; font-style:normal; font-weight:700;">MMPOWER</span> e
    <span style="color:#F0A35E; font-style:normal; font-weight:700;">MMGAS</span>
    dell'Unione Industriali Torino e le 10 migliori offerte indicizzate attive sul
    mercato libero italiano. Pagina interattiva con grafici per fascia&nbsp;/&nbsp;tipologia,
    simulatori di scenari personalizzati e schede operative delle convenzioni in essere.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- Funzione: calcola un mese sintetico 'aggregato' su tutti i mesi disponibili,
#               con prezzi mediati ponderando sui consumi del mese. ---
KEY_AGGREGATO = "__aggregato__"


def aggrega_mesi(D_in):
    """Ritorna un dict con la struttura di dati_per_mese[m] aggregato sui mesi
    disponibili. Pesi = consumi (kWh per ELE, Smc per GAS) di ciascun mese.
    consumo_mese di confronto = SOMMA dei consumi del mese per (commodity, tipologia);
    n_utenze = MEDIA arrotondata (le stesse utenze nei mesi)."""
    mesi_dict = D_in.get("dati_per_mese", {})
    if not mesi_dict:
        return None
    mesi_keys = sorted(mesi_dict.keys())
    metas = [mesi_dict[k]["meta_mese"] for k in mesi_keys]

    # Pesi totali ELE/GAS/BT/MT
    cons_ele = [float(m.get("consumo_ele_totale_kwh", 0)) for m in metas]
    cons_gas = [float(m.get("consumo_gas_totale_smc", 0)) for m in metas]
    cons_bt = []
    cons_mt = []
    for k in mesi_keys:
        ele_recs = [r for r in mesi_dict[k]["confronto"] if r["commodity"] == "ELE"]
        cons_bt.append(sum(float(r["consumo_mese"])
                            for r in ele_recs if str(r["tipologia"]).startswith("BT")))
        cons_mt.append(sum(float(r["consumo_mese"])
                            for r in ele_recs if r["tipologia"] == "MT"))
    tot_ele, tot_gas = sum(cons_ele), sum(cons_gas)
    tot_bt, tot_mt = sum(cons_bt), sum(cons_mt)

    def _wa(values, weights):
        s = sum(weights)
        if s == 0:
            return sum(values) / len(values) if values else 0.0
        return sum(v * w for v, w in zip(values, weights)) / s

    def _ele(key): return _wa([float(m.get(key, 0)) for m in metas], cons_ele)
    def _gas(key): return _wa([float(m.get(key, 0)) for m in metas], cons_gas)
    def _bt(key):  return _wa([float(m.get(key, 0)) for m in metas], cons_bt)
    def _mt(key):  return _wa([float(m.get(key, 0)) for m in metas], cons_mt)

    meta_aggr = {
        "mese": KEY_AGGREGATO,
        "PUN_eur_kWh":      _ele("PUN_eur_kWh"),
        "PSV_eur_Smc":      _gas("PSV_eur_Smc"),
        "generazione_BT":   _bt("generazione_BT"),
        "perdite_BT":       _bt("perdite_BT"),
        "mp_conv_BT":       _bt("mp_conv_BT"),
        "generazione_MT":   _mt("generazione_MT"),
        "perdite_MT":       _mt("perdite_MT"),
        "mp_conv_MT":       _mt("mp_conv_MT"),
        "consumo_ele_totale_kwh": tot_ele,
        "consumo_gas_totale_smc": tot_gas,
        "PUN_TOT_eur_kWh":  _ele("PUN_TOT_eur_kWh"),
        "PUN_BT_eur_kWh":   _bt("PUN_BT_eur_kWh"),
        "PUN_MT_eur_kWh":   _mt("PUN_MT_eur_kWh"),
        "PUN_F1_eur_kWh":   _ele("PUN_F1_eur_kWh"),
        "PUN_F2_eur_kWh":   _ele("PUN_F2_eur_kWh"),
        "PUN_F3_eur_kWh":   _ele("PUN_F3_eur_kWh"),
    }

    # Aggrega confronto per (commodity, tipologia)
    by_tip = {}
    for k in mesi_keys:
        for r in mesi_dict[k]["confronto"]:
            by_tip.setdefault((r["commodity"], r["tipologia"]), []).append(r)
    new_conf = []
    for (comm, tip), recs in by_tip.items():
        cons = [float(r["consumo_mese"]) for r in recs]
        mp_avg = _wa([float(r["materia_prima_conv"]) for r in recs], cons)
        merc_avg = _wa([float(r["benchmark_mercato"]) for r in recs], cons)
        n_avg = round(sum(int(r["n_utenze"]) for r in recs) / len(recs))
        new_conf.append({
            "commodity": comm, "tipologia": tip,
            "generazione_conv": None, "perdite_conv": None,
            "materia_prima_conv": round(mp_avg, 2), "unita_mp": recs[0]["unita_mp"],
            "consumo_mese": sum(cons), "n_utenze": int(n_avg),
            "benchmark_mercato": round(merc_avg, 2),
            "n_offerte_usate": recs[0].get("n_offerte_usate", 10),
            "delta_mercato_vs_conv": round(merc_avg - mp_avg, 2),
            "delta_%": round((merc_avg - mp_avg) / mp_avg * 100, 1) if mp_avg else 0,
        })

    # Generale aggregato
    new_gen = []
    ele_sub = [r for r in new_conf if r["commodity"] == "ELE"]
    gas_sub = [r for r in new_conf if r["commodity"] == "GAS"]
    if ele_sub:
        mp_c = sum(r["materia_prima_conv"] for r in ele_sub) / len(ele_sub)
        m_c = sum(r["benchmark_mercato"] for r in ele_sub) / len(ele_sub)
        new_gen.append({"commodity": "ELE", "unita": "€/MWh",
                         "MP_convenzione": round(mp_c, 2),
                         "benchmark_mercato": round(m_c, 2),
                         "criterio": "media semplice 4 fasce (BT/MT equo)",
                         "delta": round(m_c - mp_c, 2),
                         "delta_%": round((m_c - mp_c) / mp_c * 100, 1) if mp_c else 0})
    if gas_sub:
        w_tot = sum(r["consumo_mese"] for r in gas_sub)
        mp_c = sum(r["materia_prima_conv"] * r["consumo_mese"]
                    for r in gas_sub) / w_tot if w_tot else 0
        m_c = sum(r["benchmark_mercato"] * r["consumo_mese"]
                   for r in gas_sub) / w_tot if w_tot else 0
        new_gen.append({"commodity": "GAS", "unita": "c€/Smc",
                         "MP_convenzione": round(mp_c, 2),
                         "benchmark_mercato": round(m_c, 2),
                         "criterio": "media ponderata sui consumi",
                         "delta": round(m_c - mp_c, 2),
                         "delta_%": round((m_c - mp_c) / mp_c * 100, 1) if mp_c else 0})

    # Sensitivity per_fascia: media ponderata sui consumi della fascia attraverso i mesi
    fattori = mesi_dict[mesi_keys[0]].get("sensitivity", {}).get("fattori", [])
    sens_per = {}
    for (comm, tip), recs in by_tip.items():
        key = f"{comm}|{tip}"
        weights = [float(r["consumo_mese"]) for r in recs]
        all_vals = []
        for k in mesi_keys:
            v = mesi_dict[k].get("sensitivity", {}).get("per_fascia", {}).get(key)
            if v:
                all_vals.append(v)
        if not all_vals:
            continue
        # Allinea al numero di fattori del mese piu' breve
        n = min(len(v) for v in all_vals)
        agg_vals = []
        for i in range(n):
            vs = [v[i] for v in all_vals]
            ws = weights[:len(vs)]
            agg_vals.append(round(_wa(vs, ws), 3))
        sens_per[key] = agg_vals
    sens_aggr = {"fattori": fattori, "per_fascia": sens_per}

    return {"meta_mese": meta_aggr, "confronto": new_conf,
            "generale": new_gen, "sensitivity": sens_aggr}


# --- Lista mesi + opzione 'Tutti i mesi disponibili' ---
mesi_options = list(mesi_disp)
if len(mesi_disp) > 1:
    mesi_options.append(KEY_AGGREGATO)


def _label_mese_o_aggregato(m):
    if m == KEY_AGGREGATO:
        return f"📊 Tutti i mesi disponibili ({len(mesi_disp)})"
    return mese_label(m)


# --- Dropdown SELEZIONE MESE (in alto, governa tutti i grafici) ---
mese_default = D.get("meta", {}).get("mese_default", mesi_disp[-1])
if mese_default not in mesi_disp:
    mese_default = mesi_disp[-1]

col_sel_lbl, col_sel_drop, col_sel_fill = st.columns([1, 2, 2])
with col_sel_lbl:
    st.markdown(
        "<div style='padding-top:.55rem; font-weight:700; color:#1F2937;'>"
        "📅 Periodo di osservazione:</div>",
        unsafe_allow_html=True,
    )
with col_sel_drop:
    if len(mesi_options) > 1:
        mese_sel = st.selectbox(
            "Mese", mesi_options, index=mesi_options.index(mese_default),
            format_func=_label_mese_o_aggregato, key="mese_sel",
            label_visibility="collapsed",
        )
    else:
        mese_sel = mese_default
        st.markdown(
            f"<div style='padding-top:.55rem;color:#6B7280;'>"
            f"{mese_label(mese_sel)} <span style='color:#9CA3AF;font-size:.85rem;'>"
            f"(unico mese disponibile)</span></div>",
            unsafe_allow_html=True,
        )

# --- Estrai i dati del mese selezionato (o aggregato calcolato al volo) ---
if mese_sel == KEY_AGGREGATO:
    dati_mese = aggrega_mesi(D)
else:
    dati_mese = D["dati_per_mese"][mese_sel]
meta = dati_mese["meta_mese"]
df_conf = pd.DataFrame(dati_mese["confronto"])
df_gen = pd.DataFrame(dati_mese["generale"])
sens = dati_mese["sensitivity"]
meta["n_offerte_totali"] = meta.get("n_offerte_totali") or D["meta"].get("n_offerte_totali", 0)
meta["coeff_perdita_BT"] = D["meta"].get("coeff_perdita_BT", 0.10)
meta["coeff_perdita_MT"] = D["meta"].get("coeff_perdita_MT", 0.038)

if len(df_conf) == 0:
    st.warning(f"⚠️ Nessun dato per il mese {mese_label(mese_sel)}.")
    st.stop()

# --- Riquadro PERIODO DI OSSERVAZIONE ---
# Singolo mese: mostra i PUN ARERA per fasce orarie (F1/F2/F3) e il PSV.
# Aggregato 'Tutti i mesi': mostra PUN/PSV ponderati ai consumi.
_pun_tot = meta.get("PUN_TOT_eur_kWh") or meta.get("PUN_eur_kWh", 0)
_pun_bt  = meta.get("PUN_BT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_mt  = meta.get("PUN_MT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_f1  = meta.get("PUN_F1_eur_kWh") or 0
_pun_f2  = meta.get("PUN_F2_eur_kWh") or 0
_pun_f3  = meta.get("PUN_F3_eur_kWh") or 0
_is_aggregato = (mese_sel == KEY_AGGREGATO)

_label_pun = "PUN ponderato ai consumi per fasce" if _is_aggregato else "PUN per fasce"
_label_psv = "PSV ponderato ai consumi" if _is_aggregato else "PSV"

# IMPORTANTE: tutto l'HTML del riquadro deve stare su una sola riga (o senza
# indentazione iniziale) per non essere interpretato come code block da Streamlit.
_html_periodo = (
    f'<div class="periodo-box">'
    f'<div style="display:flex; flex-direction:column; flex:1;">'
    f'<span class="periodo-label">📅 Periodo di osservazione</span>'
    f'<span class="periodo-value">{mese_label(meta["mese"])}</span>'
    f'</div>'
    f'<div style="display:flex; flex-direction:column; gap:.25rem; text-align:right; '
    f'border-left:1px solid #CBD5E1; padding-left:1.2rem;">'
    f'<span style="color:#374151; font-size:.9rem;">'
    f'<span style="color:#6B7280;">{_label_pun}</span>&nbsp;&nbsp;'
    f'<b style="color:#16A34A;">F1 {_pun_f1:.4f}</b>&nbsp;·&nbsp;'
    f'<b style="color:#16A34A;">F2 {_pun_f2:.4f}</b>&nbsp;·&nbsp;'
    f'<b style="color:#16A34A;">F3 {_pun_f3:.4f}</b>&nbsp;'
    f'<b style="color:#16A34A;">€/kWh</b>'
    f'</span>'
    f'<span style="color:#374151; font-size:.9rem;">'
    f'<span style="color:#6B7280;">{_label_psv}</span>&nbsp;'
    f'<b style="color:#16A34A;">{meta["PSV_eur_Smc"]:.4f} €/Smc</b>'
    f'</span>'
    f'</div></div>'
)
st.markdown(_html_periodo, unsafe_allow_html=True)


# ------------------------------------------------------------------
# SEZIONE 1 — Confronto generale
# ------------------------------------------------------------------
st.header("1️⃣ Confronto generale")

st.markdown(
    """
<div class="desc-box">
Confronto a colpo d'occhio fra il <b>prezzo della materia prima riconosciuta dalle
Convenzioni</b> e il <b>benchmark</b> calcolato come media delle <b>10 migliori offerte
attive sul mercato libero</b>. Per ciascuna offerta il prezzo è ricostruito come
<i>PUN/PSV indicizzato + spread + eventuali corrispettivi fissi</i>; per il solo
<b>elettrico</b> si aggiungono le <b>perdite di rete</b>.
</div>
""",
    unsafe_allow_html=True,
)

ele_row = df_gen[df_gen["commodity"] == "ELE"].iloc[0]
gas_row = df_gen[df_gen["commodity"] == "GAS"].iloc[0]


def bar_confronto_v2(val_conv, val_merc, color_conv, color_merc, titolo,
                     label_conv, label_merc, unita):
    """Bar chart con legenda IN BASSO, barre piu' larghe, delta evidenziato."""
    delta = val_merc - val_conv
    delta_pct = (delta / val_conv * 100) if val_conv else 0
    color_delta = "#B4495C" if delta > 0 else "#2F855A"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[label_conv], y=[val_conv], name=label_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_conv:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.65,
    ))
    fig.add_trace(go.Bar(
        x=[label_merc], y=[val_merc], name=label_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_merc:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.65,
    ))
    fig.update_layout(
        title=dict(text=titolo, font=dict(size=16, color=C_TEXT_DARK)),
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.18, yanchor="top",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11),
        ),
        height=460, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        yaxis=dict(title=unita, gridcolor="#E5E7EB", zerolinecolor="#E5E7EB"),
        xaxis=dict(showticklabels=False, range=[-0.6, 1.6]),
        bargap=0.18,
        margin=dict(t=80, b=110, l=60, r=40),
        annotations=[
            dict(
                x=0.5, y=1.13, xref="paper", yref="paper",
                text=(f"<span style='color:{color_delta}; font-weight:700; "
                      f"font-size:1.05rem;'>Δ {delta:+.2f} {unita} "
                      f"({delta_pct:+.1f}%)</span>"),
                showarrow=False,
            ),
        ],
    )
    return fig


col_ele, col_gas = st.columns(2)
with col_ele:
    st.plotly_chart(bar_confronto_v2(
        ele_row["MP_convenzione"], ele_row["benchmark_mercato"],
        C_CONV_ELE, C_MERC_ELE,
        f"{ICON_ELE} Elettrico — €/MWh",
        LABEL_CONV_ELE, LABEL_MERC_ELE, "€/MWh",
    ), use_container_width=True)
with col_gas:
    st.plotly_chart(bar_confronto_v2(
        gas_row["MP_convenzione"], gas_row["benchmark_mercato"],
        C_CONV_GAS, C_MERC_GAS,
        f"{ICON_GAS} Gas — c€/Smc",
        LABEL_CONV_GAS, LABEL_MERC_GAS, "c€/Smc",
    ), use_container_width=True)


# ------------------------------------------------------------------
# Grafico a barre raggruppate (riusato in §2, §3, §4)
# ------------------------------------------------------------------
def bar_gruppi(x_labels, y_conv, y_merc, color_conv, color_merc,
               label_conv, label_merc, unita, height=480, xtickangle=0):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=label_conv, x=x_labels, y=y_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=1.5)),
        text=[f"<b>{v:.2f}</b>" for v in y_conv],
        textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
    ))
    fig.add_trace(go.Bar(
        name=label_merc, x=x_labels, y=y_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=1.5)),
        text=[f"<b>{v:.2f}</b>" for v in y_merc],
        textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
    ))
    fig.update_layout(
        barmode="group", height=height,
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        yaxis=dict(title=unita, gridcolor="#E5E7EB"),
        xaxis=dict(title="", tickangle=xtickangle), bargap=0.25, bargroupgap=0.08,
        # Legenda in basso al centro (stessa forma del grafico 1)
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.18, yanchor="top",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(t=40, b=110, l=60, r=40),
    )
    return fig


# ------------------------------------------------------------------
# SEZIONE 2 — Per fascia di potenza (Elettrico)
# ------------------------------------------------------------------
st.header(f"2️⃣ {ICON_ELE} Per fascia di potenza (Elettrico)")

# Prepara df_ele ordinato secondo ORDINE_ELE
df_ele = df_conf[df_conf["commodity"] == "ELE"].copy()
df_ele["_order"] = df_ele["tipologia"].apply(
    lambda t: ORDINE_ELE.index(t) if t in ORDINE_ELE else 99)
df_ele = df_ele.sort_values("_order").reset_index(drop=True)


st.markdown(
    """
<div class="desc-box">
Dettaglio per <b>classe di potenza impegnata</b>. Il Prezzo per la materia prima
della Convenzione è calcolato per ciascuna delle quattro classi di potenza (media
ponderata sui consumi dei POD di ciascuna classe); le <b>Top 10 di mercato</b>
sono invece ricalcolate per ciascuna classe di potenza, in quanto le migliori
offerte possono variare in funzione delle caratteristiche di consumo tipico
delle classi indicate.
</div>
""",
    unsafe_allow_html=True,
)

# 4 classi di potenza dirette dal df_ele (ordinato secondo ORDINE_ELE)
cat = df_ele["tipologia"].tolist()
y_c = df_ele["materia_prima_conv"].astype(float).tolist()
y_m = df_ele["benchmark_mercato"].astype(float).tolist()

st.plotly_chart(
    bar_gruppi(cat, y_c, y_m, C_CONV_ELE, C_MERC_ELE,
               LABEL_CONV_ELE, LABEL_MERC_ELE, "€/MWh"),
    use_container_width=True,
)


# ------------------------------------------------------------------
# SEZIONE 3 — Per tipologia d'uso (Gas)
# ------------------------------------------------------------------
st.markdown("<h2 class='gas-section'>3️⃣ 🔥 Per tipologia d'uso (Gas)</h2>",
            unsafe_allow_html=True)

st.markdown(
    """
<div class="desc-box gas">
Dettaglio per <b>tipologia d'uso del gas</b>. Il Prezzo per la materia prima
della Convenzione è calcolato distintamente <b>per ciascuna delle quattro
tipologie d'uso</b> (media ponderata sui consumi e importi reali del mese, per
ogni tipologia); le <b>Top 10 di mercato</b> sono ricalcolate per ciascuna
tipologia, in quanto le migliori offerte possono variare in funzione delle
caratteristiche di consumo tipico delle tipologie indicate.
</div>
""",
    unsafe_allow_html=True,
)

df_gas = df_conf[df_conf["commodity"] == "GAS"].copy()
df_gas["_order"] = df_gas["tipologia"].apply(
    lambda t: ORDINE_GAS.index(t) if t in ORDINE_GAS else 99)
df_gas = df_gas.sort_values("_order").reset_index(drop=True)

st.plotly_chart(
    bar_gruppi([_short_gas(t) for t in df_gas["tipologia"].tolist()],
               df_gas["materia_prima_conv"].tolist(),
               df_gas["benchmark_mercato"].tolist(),
               C_CONV_GAS, C_MERC_GAS, LABEL_CONV_GAS, LABEL_MERC_GAS, "c€/Smc"),
    use_container_width=True,
)


# ------------------------------------------------------------------
# SEZIONE 4 — Simulatore "per utenza media"
# ------------------------------------------------------------------
st.header("4️⃣ 🎚️ Simulatore per utenza media")

st.markdown(
    """
<div class="desc-box">
Questa sezione consente di <b>simulare scenari di mix di utenze</b> a partire dai
consumi medi reali del campione convenzionato. Selezionando il numero di utenze
desiderato per ciascuna classe o tipologia si ottiene una proiezione immediata di
quanto il prezzo della materia prima della Convenzione e del benchmark di mercato
varierebbero al variare della composizione del portafoglio di utenze,
mantenendo costanti i predetti consumi medi rilevati nel periodo di osservazione.
<ul>
  <li>per il <b>4.1 Elettrico</b>, il prezzo aggregato corrisponderà alla media
  ponderata sui consumi al variare del numero e della classe di tensione delle
  utenze indicate;</li>
  <li>per il <b>4.2 Gas</b>, il prezzo aggregato corrisponderà alla media ponderata
  sui consumi al variare del numero e della tipologia d'uso delle utenze indicate.</li>
</ul>
</div>
""",
    unsafe_allow_html=True,
)


# --- Helper: ricalcola benchmark Mercato in tempo reale dalle offerte_anonime ---
offerte_anon = D.get("offerte_anonime", [])


def _benchmark_mercato_singola(commodity: str, base_price: float,
                               cons_singolo: float, coeff_perdita: float,
                               top_n: int = 10):
    """Calcola il benchmark Mercato per UN tipo di utenza (BT, MT, o GAS aggregato).
    base_price: PUN (€/kWh) per ELE, PSV (€/Smc) per gas.
    cons_singolo: consumo medio mensile per POD/PDR (kWh o Smc).
    coeff_perdita: 0.10 (BT), 0.038 (MT), 0 (gas).
    Ritorna prezzo medio top-N in €/MWh (ELE) o c€/Smc (gas).
    """
    if cons_singolo <= 0 or not offerte_anon:
        return None
    prezzi = []
    for o in offerte_anon:
        if o["commodity"] != commodity:
            continue
        spread = float(o["spread"])
        quota = float(o["quota_eur_anno"])
        # quota fissa annua diluita sul consumo annuo singolo = quota/12 / cons_mese
        quota_unit = (quota / 12.0) / cons_singolo if cons_singolo else 0.0
        p = base_price + spread + (base_price + spread) * coeff_perdita + quota_unit
        prezzi.append(p)
    if not prezzi:
        return None
    prezzi.sort()
    top = prezzi[:min(top_n, len(prezzi))]
    media = sum(top) / len(top)
    return media * (1000 if commodity == "ELE" else 100)

# --------------- Helper formattazione + widget ---------------
def _fmt_thousands(n) -> str:
    """Formatta un intero con separatore migliaia stile italiano (punti)."""
    return f"{int(n):,}".replace(",", ".")


def _slider_intero(label, vmin, vmax, default, step, key_prefix, unit=""):
    """number_input + slider sincronizzati via session_state, con caption migliaia."""
    if vmax <= vmin:
        vmax = vmin + step
    default = max(vmin, min(vmax, int(round(default / step) * step)))
    sk = f"_v_{key_prefix}"
    cur = st.session_state.get(sk, default)
    cur = max(vmin, min(vmax, int(round(cur / step) * step)))
    st.session_state[sk] = cur

    nkey = f"num_{key_prefix}"
    skey = f"sl_{key_prefix}"

    def _from_num():
        v = max(vmin, min(vmax, int(round(st.session_state[nkey] / step) * step)))
        st.session_state[sk] = v
        st.session_state[skey] = v

    def _from_sl():
        v = max(vmin, min(vmax, int(round(st.session_state[skey] / step) * step)))
        st.session_state[sk] = v
        st.session_state[nkey] = v

    if nkey not in st.session_state:
        st.session_state[nkey] = cur
    if skey not in st.session_state:
        st.session_state[skey] = cur

    cols = st.columns([1, 2])
    with cols[0]:
        st.number_input(label, min_value=vmin, max_value=vmax, step=step,
                        key=nkey, on_change=_from_num)
    with cols[1]:
        st.slider(" ", min_value=vmin, max_value=vmax, step=step,
                  key=skey, on_change=_from_sl, label_visibility="collapsed")
    if unit:
        st.markdown(
            f"<div style='text-align:right; color:#1F2937; font-size:.92rem;'>"
            f"<b>{_fmt_thousands(st.session_state[sk])} {unit}</b></div>",
            unsafe_allow_html=True,
        )
    return st.session_state[sk]


# =====================================================================
# Consumi medi per POD - 4 classi di potenza distinte
# (BT <=3 kW / BT 4.5-40 kW / BT >40 kW / MT) come da df_ele.
# =====================================================================
def _stat_cat(tip):
    """Estrae (cons_totale, n_utenze, cons_medio) per la fascia indicata."""
    sub = df_conf[(df_conf["commodity"] == "ELE")
                   & (df_conf["tipologia"] == tip)]
    if sub.empty:
        return 0.0, 0, 0.0
    cons = float(sub["consumo_mese"].iloc[0])
    n = int(sub["n_utenze"].iloc[0])
    return cons, n, (cons / n if n else 0.0)


# 4 classi di potenza ELE: dati base
_cons_3,   _n_3,   cons_3_medio   = _stat_cat("BT <=6 kW")
_cons_40,  _n_40,  cons_40_medio  = _stat_cat("BT 6-50 kW")
_cons_btH, _n_btH, cons_btH_medio = _stat_cat("BT >50 kW")
_cons_mt,  _n_mt,  cons_mt_medio  = _stat_cat("MT")

# fallback di sicurezza per evitare slider con default=0
if cons_3_medio   == 0: cons_3_medio   = 300.0
if cons_40_medio  == 0: cons_40_medio  = 2500.0
if cons_btH_medio == 0: cons_btH_medio = 11000.0
if cons_mt_medio  == 0: cons_mt_medio  = 40000.0

n_pdr_real = int(df_conf[df_conf["commodity"] == "GAS"]["n_utenze"].sum())
cons_gas_tot_real = float(df_conf[df_conf["commodity"] == "GAS"]["consumo_mese"].sum())
cons_pdr_medio = cons_gas_tot_real / n_pdr_real if n_pdr_real else 2500.0


# =====================================================================
# 4.1 Elettrico — 4 slider (BT ≤3 / BT 4.5-40 / BT >40 / MT)
#   I consumi medi per POD sono FISSI (medi reali del mese selezionato).
# =====================================================================
st.subheader(f"4.1 {ICON_ELE} Elettrico — Simulatore Prezzo Materia prima per n° Utenze (per Tensione)")

st.markdown(
    f"""
<div style="background:#F8FAFC; border:1px solid #E5E7EB; border-radius:8px;
            padding:.8rem 1rem; margin: .4rem 0 1rem 0; font-size:.92rem;">
🧮 Consumo medio per Classe di Potenza del Periodo d'osservazione
<b>{mese_label(meta['mese'])}</b>
(media reale sulle utenze POD del campione):<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT ≤6 kW</b>:
{_fmt_thousands(round(cons_3_medio))} kWh<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT 6–50 kW</b>:
{_fmt_thousands(round(cons_40_medio))} kWh<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza <b>BT &gt;50 kW</b>:
{_fmt_thousands(round(cons_btH_medio))} kWh<br>
&nbsp;&nbsp;⚡ Consumo medio di un'Utenza in <b>Media Tensione (MT)</b>:
{_fmt_thousands(round(cons_mt_medio))} kWh
</div>
""",
    unsafe_allow_html=True,
)

cE1, cE2 = st.columns(2)
with cE1:
    n_bt3 = _slider_intero("BT ≤6 kW", vmin=0, vmax=2000,
                            default=1, step=1, key_prefix="n_bt3")
with cE2:
    n_bt40 = _slider_intero("BT 6–50 kW", vmin=0, vmax=2000,
                             default=1, step=1, key_prefix="n_bt40")
cE3, cE4 = st.columns(2)
with cE3:
    n_btH = _slider_intero("BT >50 kW", vmin=0, vmax=2000,
                            default=1, step=1, key_prefix="n_btH")
with cE4:
    n_mt = _slider_intero("MT", vmin=0, vmax=500,
                           default=1, step=1, key_prefix="n_mt")

if n_bt3 == 0 and n_bt40 == 0 and n_btH == 0 and n_mt == 0:
    st.warning("Seleziona almeno una utenza per visualizzare il confronto.")
else:
    pun_bt_val = float(meta.get("PUN_BT_eur_kWh") or meta.get("PUN_eur_kWh", 0))
    pun_mt_val = float(meta.get("PUN_MT_eur_kWh") or meta.get("PUN_eur_kWh", 0))
    mp_conv_bt = float(meta.get("mp_conv_BT", 0))
    mp_conv_mt = float(meta.get("mp_conv_MT", 0))
    coeff_BT = meta.get("coeff_perdita_BT", 0.10)
    coeff_MT = meta.get("coeff_perdita_MT", 0.038)

    # Benchmark di mercato a consumo medio della categoria
    bench_bt3  = _benchmark_mercato_singola("ELE", pun_bt_val, cons_3_medio,   coeff_perdita=coeff_BT)
    bench_bt40 = _benchmark_mercato_singola("ELE", pun_bt_val, cons_40_medio,  coeff_perdita=coeff_BT)
    bench_btH  = _benchmark_mercato_singola("ELE", pun_bt_val, cons_btH_medio, coeff_perdita=coeff_BT)
    bench_mt   = _benchmark_mercato_singola("ELE", pun_mt_val, cons_mt_medio,  coeff_perdita=coeff_MT)

    # Consumi totali simulati per categoria
    cons_bt3_sim  = n_bt3  * cons_3_medio
    cons_bt40_sim = n_bt40 * cons_40_medio
    cons_btH_sim  = n_btH  * cons_btH_medio
    cons_mt_sim   = n_mt   * cons_mt_medio
    cons_tot = cons_bt3_sim + cons_bt40_sim + cons_btH_sim + cons_mt_sim
    cons_bt_sim = cons_bt3_sim + cons_bt40_sim + cons_btH_sim  # tutte le BT

    attive_n = [n_bt3, n_bt40, n_btH, n_mt]
    attive = sum(1 for n in attive_n if n > 0)
    if attive == 1:
        if n_bt3 > 0:
            etichetta = f"⚡ Solo BT ≤6 kW ({n_bt3} POD × {_fmt_thousands(round(cons_3_medio))} kWh)"
            conv_v, merc_v = mp_conv_bt, (bench_bt3 or 0)
        elif n_bt40 > 0:
            etichetta = f"⚡ Solo BT 6–50 kW ({n_bt40} POD × {_fmt_thousands(round(cons_40_medio))} kWh)"
            conv_v, merc_v = mp_conv_bt, (bench_bt40 or 0)
        elif n_btH > 0:
            etichetta = f"⚡ Solo BT >50 kW ({n_btH} POD × {_fmt_thousands(round(cons_btH_medio))} kWh)"
            conv_v, merc_v = mp_conv_bt, (bench_btH or 0)
        else:
            etichetta = f"⚡ Solo MT ({n_mt} POD × {_fmt_thousands(round(cons_mt_medio))} kWh)"
            conv_v, merc_v = mp_conv_mt, (bench_mt or 0)
    else:
        # Aggregato: media ponderata sui consumi simulati
        if cons_tot > 0:
            conv_v = (mp_conv_bt * cons_bt_sim + mp_conv_mt * cons_mt_sim) / cons_tot
            bb_num = ((bench_bt3 or 0)  * cons_bt3_sim
                      + (bench_bt40 or 0) * cons_bt40_sim
                      + (bench_btH or 0)  * cons_btH_sim
                      + (bench_mt or 0)   * cons_mt_sim)
            merc_v = bb_num / cons_tot
        else:
            conv_v = merc_v = 0
        etichetta = (f"⚡ Aggregato {n_bt3} BT≤6 + {n_bt40} BT 6–50 + "
                     f"{n_btH} BT&gt;50 + {n_mt} MT "
                     f"({_fmt_thousands(round(cons_tot))} kWh totali)")
    unit = "€/MWh"

    st.markdown(
        "<h5 style='text-align:center; color:#1F2937; margin: 1.2rem 0 .3rem 0; "
        "font-weight:600;'>📊 Prezzo medio ponderato per singola utenza</h5>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        bar_gruppi([etichetta], [conv_v], [merc_v],
                   C_CONV_ELE, C_MERC_ELE,
                   LABEL_CONV_ELE, LABEL_MERC_ELE, unit, height=400),
        use_container_width=True,
    )

    _mese_aa_str = _mese_aa(meta["mese"])
    pezzi = []
    if n_bt3 > 0 and bench_bt3 is not None:
        pezzi.append(f"<b>BT ≤6</b>: {bench_bt3:.2f} €/MWh")
    if n_bt40 > 0 and bench_bt40 is not None:
        pezzi.append(f"<b>BT 6–50</b>: {bench_bt40:.2f} €/MWh")
    if n_btH > 0 and bench_btH is not None:
        pezzi.append(f"<b>BT &gt;50</b>: {bench_btH:.2f} €/MWh")
    if n_mt > 0 and bench_mt is not None:
        pezzi.append(f"<b>MT</b>: {bench_mt:.2f} €/MWh")
    if pezzi:
        _ts = f"{_mese_aa_str} " if _mese_aa_str else ""
        st.caption(
            f"<span style='color:#6B7280;'>Prezzo Materia Prima per Classe di Potenza "
            f"{_ts}&mdash; " + " · ".join(pezzi) + "</span>",
            unsafe_allow_html=True,
        )


# =================================================================
# 4.2 Gas — 4 slider, uno per ciascuna tipologia d'uso.
#   Per ogni tipologia: consumo medio per PDR e prezzo Convenzione FISSI dal mese.
#   L'aumento del numero di utenze sposta il mix (e quindi la media ponderata).
# =================================================================
st.subheader(f"4.2 {ICON_GAS} Gas — Simulatore Prezzo Materia prima per n° Utenze (per Tipologia d'uso)")

# Riferimenti per ciascuna tipologia gas dal mese selezionato
df_gas_loc = df_conf[df_conf["commodity"] == "GAS"].copy()
df_gas_loc["_order"] = df_gas_loc["tipologia"].apply(
    lambda t: ORDINE_GAS.index(t) if t in ORDINE_GAS else 99)
df_gas_loc = df_gas_loc.sort_values("_order").reset_index(drop=True)

gas_tipi = []  # lista di dict {tip, label_short, conv, cons_medio, n_real, key}
for _, r in df_gas_loc.iterrows():
    tip = r["tipologia"]
    n_r = int(r["n_utenze"]) if r["n_utenze"] else 1
    cons_r = float(r["consumo_mese"]) / n_r if n_r else 0.0
    gas_tipi.append({
        "tip": tip,
        "label_short": _short_gas(tip),
        "conv": float(r["materia_prima_conv"]),
        "cons_medio": cons_r,
        "n_real": n_r,
        "key": re.sub(r"[^a-z0-9]+", "_", tip.lower()).strip("_"),
    })

# Riquadro riferimenti
ref_rows = "<br>".join(
    f"&nbsp;&nbsp;🔥 Consumo medio di un'Utenza con <b>Tipologia {g['tip']}</b>: "
    f"{_fmt_thousands(round(g['cons_medio']))} Smc"
    for g in gas_tipi
)
st.markdown(
    f"""
<div style="background:#F8FAFC; border:1px solid #E5E7EB; border-radius:8px;
            padding:.8rem 1rem; margin: .4rem 0 1rem 0; font-size:.92rem;">
🧮 Consumo medio per tipologia d'uso del Periodo d'osservazione
<b>{mese_label(meta['mese'])}</b>
(media reale sulle utenze PDR del campione):<br>
{ref_rows}
</div>
""",
    unsafe_allow_html=True,
)

# 4 slider in 2 colonne (default 1 per tipologia). Le label usano i NOMI COMPLETI.
ggcols = st.columns(2)
n_gas = {}
for i, g in enumerate(gas_tipi):
    with ggcols[i % 2]:
        n_gas[g["tip"]] = _slider_intero(
            g["label_short"],
            vmin=0, vmax=1000, default=1, step=1,
            key_prefix=f"ng_{g['key']}",
        )

# Calcolo aggregato
psv_val = float(meta.get("PSV_eur_Smc", 0))
totale_n = sum(n_gas.values())
if totale_n == 0:
    st.warning("Seleziona almeno una utenza gas per visualizzare il confronto.")
else:
    # Per ciascuna tipologia: cons_tot, benchmark a consumo_medio_tipologia, peso
    cons_tot_gas_sim = 0.0
    num_c = num_m = 0.0
    den = 0.0
    pezzi_bench = []
    for g in gas_tipi:
        nn = n_gas[g["tip"]]
        if nn <= 0 or g["cons_medio"] <= 0:
            continue
        cons_sim = nn * g["cons_medio"]
        cons_tot_gas_sim += cons_sim
        # Benchmark Mercato a consumo medio della tipologia (top10 sulle 12 offerte gas)
        bench_tip = _benchmark_mercato_singola(
            "GAS", psv_val, g["cons_medio"], coeff_perdita=0.0,
        ) or g.get("conv", 0)
        num_c += g["conv"] * cons_sim
        num_m += bench_tip * cons_sim
        den += cons_sim
        pezzi_bench.append(
            f"<b>{g['label_short']}</b>: {bench_tip:.2f} c€/Smc "
            f"(a {_fmt_thousands(round(g['cons_medio']))} Smc/PDR)"
        )

    if den > 0:
        conv_gas_v = num_c / den
        merc_gas_v = num_m / den
    else:
        conv_gas_v = merc_gas_v = 0.0

    etichetta_gas = (f"🔥 {totale_n} PDR totali "
                     f"({_fmt_thousands(round(cons_tot_gas_sim))} Smc totali)")
    st.markdown(
        "<h5 style='text-align:center; color:#1F2937; margin: 1.2rem 0 .3rem 0; "
        "font-weight:600;'>📊 Prezzo medio ponderato per singola utenza</h5>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        bar_gruppi([etichetta_gas], [conv_gas_v], [merc_gas_v],
                   C_CONV_GAS, C_MERC_GAS,
                   LABEL_CONV_GAS, LABEL_MERC_GAS, "c€/Smc", height=400),
        use_container_width=True,
    )
    # Caption: SEMPRE i 4 bench per tipologia (anche se n_gas=0), in label abbreviato
    _mese_aa_g = _mese_aa(meta["mese"])

    pezzi_full = []
    for g in gas_tipi:
        b_tip = _benchmark_mercato_singola(
            "GAS", psv_val, g["cons_medio"], coeff_perdita=0.0,
        )
        if b_tip is not None:
            pezzi_full.append(f"<b>{g['label_short']}</b>: {b_tip:.2f} c€/Smc")
    if pezzi_full:
        _tg = f"{_mese_aa_g} " if _mese_aa_g else ""
        st.caption(
            f"<span style='color:#6B7280;'>Prezzo Materia Prima per Tipologia d'uso "
            f"{_tg}&mdash; " + " · ".join(pezzi_full) + "</span>",
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------------
# METODOLOGIA + BIBLIOGRAFIA
# ------------------------------------------------------------------
st.header("📚 Metodologia")

# Calcolo data estrazione e conteggi offerte prima del markdown
data_estr_str = D.get("meta", {}).get("data_estrazione")
if not data_estr_str:
    import os
    try:
        ts = os.path.getmtime(Path(__file__).parent / "data" / "data.json")
        data_estr_str = pd.Timestamp(ts, unit="s").strftime("%Y-%m-%d")
    except Exception:
        data_estr_str = ""
data_estr_it = ""
if data_estr_str:
    try:
        data_estr_it = pd.Timestamp(data_estr_str).strftime("%d/%m/%Y")
    except Exception:
        data_estr_it = data_estr_str

n_off_tot = meta.get("n_offerte_totali") or D.get("meta", {}).get("n_offerte_totali", 0)
n_off_ele = D.get("meta", {}).get("n_offerte_ele")
n_off_gas = D.get("meta", {}).get("n_offerte_gas")
if n_off_ele is None or n_off_gas is None:
    _ot = D.get("offerte_tutte", [])
    n_off_ele = sum(1 for o in _ot if o.get("commodity") == "ELE")
    n_off_gas = sum(1 for o in _ot if o.get("commodity") == "GAS")

# UN SOLO st.markdown con tutto dentro lo stesso footer-block
st.markdown(
    f"""
<div class="footer-block">

<h4 style="margin-top:0;">🔬 Come è costruito il benchmark</h4>

<ol style="line-height:1.6;">
<li style="margin-bottom: 1.2rem;"><b>Convenzione MMPOWER</b> — Il Prezzo della
Materia prima è composto dalle voci <i>Generazione</i> e <i>Perdite di rete</i>
calcolate a partire dai <b>dati reali</b> di fornitura delle aziende
convenzionate (media ponderata sui consumi effettivi del periodo di osservazione).</li>

<li style="margin-bottom: 1.2rem;"><b>Convenzione MMGAS</b> — Materia prima del
gas calcolata per ciascuna tipologia d'uso a partire dai <b>dati reali</b> di
fornitura delle aziende convenzionate (importo "materia prima" diviso per i Smc
consumati del mese).</li>

<li style="margin-bottom: 1.2rem;"><b>Mercato</b> — Per ogni offerta indicizzata
raccolta il prezzo è ricostruito distintamente per i due vettori:<br><br>
&nbsp;&nbsp;&nbsp;⚡ <b>Energia elettrica</b>:
<code>P = PUNx + spread + (PUNx + spread) × coeff_perdita + (quota_fissa_annua × n_utenze) ÷ (12 × consumo_mese)</code><br>
&nbsp;&nbsp;&nbsp;&nbsp;dove <code>coeff_perdita</code> = {meta['coeff_perdita_BT']*100:.0f}%
per le utenze BT e {meta['coeff_perdita_MT']*100:.1f}% per quelle MT.<br><br>
&nbsp;&nbsp;&nbsp;🔥 <b>Gas</b>:
<code>P = PSV + spread + (quota_fissa_annua × n_utenze) ÷ (12 × consumo_mese)</code>.</li>

<li style="margin-bottom: 1.2rem;"><b>PUNx: PUN Ponderato per Fasce</b> — Anziché
applicare il PUN monorario all'intero campione, viene utilizzato un <b>PUNx</b>
differenziato per classe di tensione (PUN BT, PUN MT) e un PUNx aggregato totale
(PUN TOT). Questo consente di rappresentare in modo più aderente alla realtà il
prezzo all'ingrosso del mercato elettrico italiano, riconoscendo che la
composizione oraria del consumo è strutturalmente diversa fra utenze a Bassa
Tensione e a Media Tensione: il PUNx così ponderato si avvicina di più al costo
effettivo che ciascun segmento sostiene per l'energia ritirata dal mercato.<br><br>
Per il periodo di osservazione <b>{mese_label(meta['mese'])}</b>:<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN TOT</b>: {_pun_tot:.4f} €/kWh — usato nel grafico Generale (sezione 1)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN BT</b>: {_pun_bt:.4f} €/kWh — usato per le classi BT (sezioni 2 e 4.1)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN MT</b>: {_pun_mt:.4f} €/kWh — usato per la classe MT (sezioni 2 e 4.1)<br><br>
Il <b>PUN TOT</b> è la media ponderata tra PUN BT e PUN MT sui consumi reali del
periodo di osservazione del campione corrente; i prezzi <b>PUN BT</b> e
<b>PUN MT</b> corrispondono alle medie ponderate dei prezzi PUN per fascia ARERA
per le percentuali dei consumi storici per fascia, del mese osservato, delle
utenze convenzionate.</li>

<li style="margin-bottom: 1.2rem;"><b>Fonte dei prezzi all'ingrosso</b> — I prezzi
PUN e PSV utilizzati nelle formule e nei calcoli del PUNx sono quelli pubblicati
da
<a href="https://www.arera.it/dati-e-statistiche/dettaglio/prezzi-finali-energia-elettrica-per-i-consumatori-domestici-tipo" target="_blank"><b>ARERA — PLACET</b></a>.</li>

<li style="margin-bottom: 1.2rem;"><b>Selezione del Top 10</b> — Per ciascuna
classe di potenza (elettrico) o tipologia d'uso (gas) si ordinano in modo crescente
tutti i prezzi ricostruiti delle offerte raccolte sul mercato e si selezionano le
<b>10 più convenienti</b>. La loro media aritmetica costituisce il valore di
benchmark di mercato esposto nei grafici.</li>

<li style="margin-bottom: 1.2rem;"><b>Offerte monitorate</b> — In data
<b>{data_estr_it or '—'}</b> sono state raccolte e analizzate complessivamente
<span class="num-evidenza">{n_off_tot} offerte indicizzate</span> attive sul
mercato libero italiano, provenienti sia dai siti istituzionali dei fornitori
sia dai principali portali comparatori, di cui <b>{n_off_ele}</b> per l'energia
elettrica e <b>{n_off_gas}</b> per il gas.</li>
</ol>

</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# BIBLIOGRAFIA: tutti i link a fornitori, offerte, portali
# ------------------------------------------------------------------
# ------------------------------------------------------------------
# CONVENZIONI IN ESSERE — schede + download news in PDF
# ------------------------------------------------------------------
st.header("📰 Le Convenzioni in essere")

st.markdown(
    """
<div class="desc-box">
Le Convenzioni MMPOWER e MMGAS sono contratti <b>riservati esclusivamente alle aziende
associate</b> all'Unione Industriali Torino. Si tratta di <b>contratti a tempo
determinato senza tacito rinnovo</b> e sono <b>tuttora attivi ed è possibile
aderirvi</b>. In prossimità della scadenza l'Area Gas &amp; Power proporrà, sempre
per le aziende associate e con priorità alle aziende già convenzionate, un nuovo
accordo per il biennio successivo perfezionato tramite gara tra i principali
fornitori del mercato.
</div>
""",
    unsafe_allow_html=True,
)

cN1, cN2 = st.columns(2)

# ---------- MMPOWER ----------
with cN1:
    st.markdown(
        """
<div style="border:1px solid #6BAED6; border-radius:12px; padding:1rem 1.2rem;
            background:linear-gradient(180deg,#FFFFFF,#F0F7FC);
            min-height:280px; display:flex; flex-direction:column;">
<h4 style="color:#2C5784; margin-top:0;">⚡ Convenzione MMPOWER 2026-2027</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Iren Mercato S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Soglia consumo</b>: <b>3.000.000 kWh/anno</b> per singola utenza</li>
<li><b>Periodo di fornitura</b>: <b>fino al 31/12/2027</b></li>
<li><b>Opzione 100% energia verde</b> (su richiesta del singolo cliente)</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    st.link_button(
        label="📰 Vai alla news completa MMPOWER *",
        url="https://www.ui.torino.it/unione-per-te/energia-commodity/notizia/101781/prezzi-energia-elettrica-20262027-nuova/",
        type="primary",
    )

# ---------- MMGAS ----------
with cN2:
    st.markdown(
        """
<div style="border:1px solid #F0A35E; border-radius:12px; padding:1rem 1.2rem;
            background:linear-gradient(180deg,#FFFFFF,#FCF5EE);
            min-height:280px; display:flex; flex-direction:column;">
<h4 style="color:#B4495C; margin-top:0;">🔥 Convenzione MMGAS 2025/26 — 2026/27</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Eni Plenitude S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Soglia consumo</b>: <b>200.000 Smc/anno</b> per singolo cliente</li>
<li><b>Periodo di fornitura</b>: <b>fino al 30/09/2027</b></li>
<li><b>Opzione 100% CO₂ compensata</b> (su richiesta del singolo cliente)</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    st.link_button(
        label="📰 Vai alla news completa MMGAS *",
        url="https://www.ui.torino.it/unione-per-te/energia-commodity/notizia/100897/gas-nuova-convenzione-biennale-unioneeni-plenitude/",
        type="primary",
    )

# Banner contatti DOPO i pulsanti di download
st.markdown(
    """
<p style="text-align:center; margin: 1.2rem 0 .6rem 0; padding:.8rem;
background:#F8FAFC; border-radius:8px; border:1px solid #E5E7EB;">
✉️ <b>Per informazioni o adesione alle Convenzioni, o per analisi e
confronti sulle offerte di mercato attive</b>:
<a href="mailto:s.cornagliotto@ui.torino.it">s.cornagliotto@ui.torino.it</a>
&nbsp;·&nbsp; ☎ 011 5718278
</p>
""",
    unsafe_allow_html=True,
)

# Nota con asterisco SUBITO dopo il banner contatti
st.markdown(
    """
<p style="color:#6B7280; font-size:.88rem; font-style:italic; margin-top:.6rem;">
* la scadenza di adesione indicata nelle news ufficiali si riferiva al solo avvio
della fornitura nel primo mese del biennio. È possibile aderire con avvio della
fornitura alla prima data utile prevista in accordo col fornitore.
</p>
""",
    unsafe_allow_html=True,
)


# Sezione Sitografia rimossa: i riferimenti rilevanti (ARERA PLACET) sono
# integrati nella Metodologia. Il PDF delle offerte resta riservato e disponibile
# solo all'Area Gas & Power (non pubblicato sulla pagina).

# ------------------------------------------------------------------
# METODOLOGIA APPROFONDITA (download PDF + sorgente .tex)
# ------------------------------------------------------------------
st.header("📘 Metodologia approfondita")

st.markdown(
    """
<div class="desc-box">
Per una descrizione completa di passaggi, formule e parametri utilizzati nel
benchmark, è disponibile un documento separato di metodologia. Il PDF include
anche l'elenco completo delle <b>offerte indicizzate raccolte</b>, in forma
<b>anonimizzata</b>: ciascuna offerta è identificata come <i>Offerta N EE</i>
(o <i>GAS</i>), con relativa <b>Fonte</b> (Sito Fornitore o Sito Comparatore)
e le condizioni economiche (spread e quota fissa).
È fornito anche il sorgente LaTeX <code>.tex</code> per chi voglia ricompilare
il documento (es. su <a href="https://overleaf.com" target="_blank">Overleaf</a>)
o modificarne il contenuto.
</div>
""",
    unsafe_allow_html=True,
)

_metodo_dir = Path(__file__).parent / "metodologia"
_pdf_path = _metodo_dir / "metodologia.pdf"
_tex_path = _metodo_dir / "metodologia.tex"

cM1, cM2 = st.columns(2)
with cM1:
    if _pdf_path.exists():
        st.download_button(
            label="📄 Scarica metodologia (PDF)",
            data=_pdf_path.read_bytes(),
            file_name="Metodologia_Benchmark_MateriaPrima.pdf",
            mime="application/pdf",
            type="primary",
            key="dl_metodo_pdf",
            use_container_width=True,
        )
    else:
        st.info("Metodologia PDF non disponibile.")
with cM2:
    if _tex_path.exists():
        st.download_button(
            label="📝 Scarica sorgente LaTeX (.tex)",
            data=_tex_path.read_text(encoding="utf-8").encode("utf-8"),
            file_name="Metodologia_Benchmark_MateriaPrima.tex",
            mime="text/x-tex",
            key="dl_metodo_tex",
            use_container_width=True,
        )
    else:
        st.info("Sorgente .tex non disponibile.")

st.markdown(
    f"""
<hr style="margin-top:2rem;">
<p style="text-align:center; color:#9CA3AF; font-size:.85rem;">
Unione Industriali Torino · Gas &amp; Power · Dashboard generata dal notebook
<code>Benchmark Confronto.ipynb</code> — periodo di osservazione {mese_label(meta['mese'])}
</p>
""",
    unsafe_allow_html=True,
)
