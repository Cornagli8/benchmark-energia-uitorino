"""
Benchmark Materia Prima Gas&Power — Unione Industriali Torino
Dashboard Streamlit: confronto Convenzioni MMPOWER/MMGAS vs Top 10 offerte di mercato.

Esecuzione locale:
    streamlit run app.py

Deploy: https://share.streamlit.io  (repo Cornagli8/benchmark-energia-uitorino)
"""
import base64
import json
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
ORDINE_ELE = ["BT <=3 kW", "BT 4.5-40 kW", "BT >40 kW", "MT"]
ORDINE_ELE_TEST = ["BT <=40 kW", "BT >40 kW", "MT"]
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
       indipendenti per ogni logo (UI piu' grande senza stretchare). */
    .logo-row {
        display: flex; justify-content: space-around; align-items: center;
        gap: 1.5rem; margin: .4rem 0 1.4rem 0; padding: 0 1rem;
    }
    .logo-cell {
        flex: 1; display: flex; justify-content: center; align-items: center;
        min-height: 120px;
    }
    .logo-cell img {
        display: block; max-width: 100%; height: auto;
        object-fit: contain;
    }
    .logo-cell.mmpower img { max-height: 90px; max-width: 220px; }
    .logo-cell.ui      img { max-height: 130px; max-width: 280px; } /* piu' grande */
    .logo-cell.mmgas   img { max-height: 90px; max-width: 220px; }

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
    y, m = yyyymm.split("-")
    return f"{mesi[int(m)]} {y}"


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

st.title("Benchmark Materia Prima Gas&Power")

# --- Dropdown SELEZIONE MESE (in alto, governa tutti i grafici) ---
mese_default = D.get("meta", {}).get("mese_default", mesi_disp[-1])
if mese_default not in mesi_disp:
    mese_default = mesi_disp[-1]

col_sel_lbl, col_sel_drop, col_sel_fill = st.columns([1, 2, 2])
with col_sel_lbl:
    st.markdown(
        "<div style='padding-top:.55rem; font-weight:700; color:#1F2937;'>"
        "📅 Mese di osservazione:</div>",
        unsafe_allow_html=True,
    )
with col_sel_drop:
    if len(mesi_disp) > 1:
        mese_sel = st.selectbox(
            "Mese", mesi_disp, index=mesi_disp.index(mese_default),
            format_func=mese_label, key="mese_sel", label_visibility="collapsed",
        )
    else:
        mese_sel = mese_default
        st.markdown(
            f"<div style='padding-top:.55rem;color:#6B7280;'>"
            f"{mese_label(mese_sel)} <span style='color:#9CA3AF;font-size:.85rem;'>"
            f"(unico mese disponibile)</span></div>",
            unsafe_allow_html=True,
        )

# --- Estrai i dati del mese selezionato ---
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

# --- Riquadro PERIODO DI OSSERVAZIONE (PUN + PSV su 2 righe, grassetto verde) ---
st.markdown(
    f"""
<div class="periodo-box">
  <div style="display:flex; flex-direction:column; flex:1;">
    <span class="periodo-label">📅 Periodo di osservazione</span>
    <span class="periodo-value">{mese_label(meta['mese'])}</span>
  </div>
  <div style="display:flex; flex-direction:column; gap:.15rem; text-align:right;
              border-left:1px solid #CBD5E1; padding-left:1.2rem;">
    <span style="color:#16A34A; font-weight:600;">
      <span style="color:#6B7280;font-weight:500;">PUN monorario</span>
      &nbsp;<b>{meta['PUN_eur_kWh']:.4f} €/kWh</b>
    </span>
    <span style="color:#16A34A; font-weight:600;">
      <span style="color:#6B7280;font-weight:500;">PSV</span>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
      <b>{meta['PSV_eur_Smc']:.4f} €/Smc</b>
    </span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# SEZIONE 1 — Confronto generale
# ------------------------------------------------------------------
st.header("1️⃣ Confronto generale")

st.markdown(
    """
<div class="desc-box">
Confronto a colpo d'occhio fra la <b>materia prima riconosciuta dalle Convenzioni</b>
e il <b>benchmark</b> calcolato come media delle 10 migliori offerte attive sul
mercato libero (PUN/PSV indicizzato + spread + quota fissa unitaria + perdite di rete).
Per l'elettrico è una media equa fra fasce BT e MT, per il gas una media ponderata sui
consumi delle 4 tipologie d'uso.
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
        # Legenda in basso al centro su UNA SOLA RIGA (i 2 valori non vanno a capo)
        legend=dict(
            orientation="h", x=0.5, xanchor="center",
            y=-0.22, yanchor="top",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11), itemwidth=30,
            entrywidth=0, entrywidthmode="fraction",
        ),
        margin=dict(t=40, b=120, l=60, r=40),
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


def _wmean(s, w):
    w = w.loc[s.index]
    return (s * w).sum() / w.sum() if w.sum() else 0.0


# Aggrega BT≤3 + BT 4.5-40 -> BT≤40 con media ponderata sui consumi
bt_low = df_ele[df_ele["tipologia"].isin(["BT <=3 kW", "BT 4.5-40 kW"])]
bt_high = df_ele[df_ele["tipologia"] == "BT >40 kW"]
mt_row = df_ele[df_ele["tipologia"] == "MT"]

bt_low_conv = _wmean(bt_low["materia_prima_conv"], bt_low["consumo_mese"])
bt_low_merc = _wmean(bt_low["benchmark_mercato"], bt_low["consumo_mese"])

cons_low_3 = float(df_ele[df_ele["tipologia"] == "BT <=3 kW"]["consumo_mese"].sum())
cons_low_40 = float(df_ele[df_ele["tipologia"] == "BT 4.5-40 kW"]["consumo_mese"].sum())

st.markdown(
    f"""
<div class="desc-box">
Dettaglio per <b>fascia di potenza impegnata</b>. La materia prima della Convenzione
è calcolata per ciascuna delle quattro fasce di potenza presenti nel report della
fornitura delle aziende convenzionate (media ponderata sui consumi dei POD di ogni
fascia). Per chiarezza espositiva, le due fasce BT ≤3 kW e BT 4,5–40 kW sono qui
<b>aggregate in BT ≤40 kW</b> usando una media ponderata sui consumi:<br>
<code>prezzo_BT≤40 = (prezzo_BT≤3 × consumo_BT≤3 + prezzo_BT4.5–40 × consumo_BT4.5–40) /
(consumo_BT≤3 + consumo_BT4.5–40)</code>.<br>
Anche il <b>Top 10 di mercato</b> è ricalcolato per ciascuna categoria, perché la quota fissa
dell'offerta pesa diversamente sul consumo medio di ognuna.
</div>
""",
    unsafe_allow_html=True,
)

cat = ["BT <=40 kW", "BT >40 kW", "MT"]
y_c = [bt_low_conv,
       float(bt_high["materia_prima_conv"].iloc[0]) if len(bt_high) else 0,
       float(mt_row["materia_prima_conv"].iloc[0]) if len(mt_row) else 0]
y_m = [bt_low_merc,
       float(bt_high["benchmark_mercato"].iloc[0]) if len(bt_high) else 0,
       float(mt_row["benchmark_mercato"].iloc[0]) if len(mt_row) else 0]

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
Dettaglio per <b>tipologia d'uso del gas</b>: la materia prima della Convenzione
varia per tipologia (calcolata sui consumi e importi reali del mese); il benchmark
di mercato è la media delle 10 migliori offerte indicizzate sul PSV.
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
# SEZIONE 4 — Sensitivity sul consumo (4.1 ELE + 4.2 GAS)
# ------------------------------------------------------------------
st.header("4️⃣ 🎚️ Sensitivity sul livello di consumo")

st.markdown(
    """
<div class="desc-box">
Lo slider parte dal <b>consumo reale totale del mese</b>. Se cambi il consumo:
<ul>
  <li>il <b>Mercato</b> ricalcola la quota fissa unitaria diluita sul nuovo consumo
  (offerte con quota fissa diventano più convenienti su consumi alti);</li>
  <li>la <b>Convenzione</b> si rapporta in modo proporzionale: <code>prezzo × consumo_origine
  / consumo_inserito</code>.</li>
</ul>
</div>
""",
    unsafe_allow_html=True,
)

# --------------- 4.1 Elettrico ---------------
st.subheader(f"4.1 {ICON_ELE} Elettrico (kWh)")
cons_ele_real = meta["consumo_ele_totale_kwh"]


def _fmt_thousands(n: int) -> str:
    """Formatta un intero con separatore migliaia stile italiano (punti)."""
    return f"{int(n):,}".replace(",", ".")


def _consumo_widget(label, real, step, key_prefix, unit, max_mult=6):
    """Coppia number_input + slider SINCRONIZZATI via session_state.
    Visualizza il valore corrente con separatore migliaia (stile italiano).
    Tutti i valori sono garantiti multipli di step e dentro [vmin, vmax]."""
    if not real or real <= 0:
        st.info(f"{label}: consumo reale non disponibile, slider disabilitato.")
        return 0

    vmin = max(step, int(round(real * 0.1 / step) * step))
    vmax = max(vmin + step, int(round(real * max_mult / step) * step))
    real_aligned = int(round(real / step) * step)
    real_aligned = max(vmin, min(vmax, real_aligned))

    sk = f"_cons_{key_prefix}"
    cur = st.session_state.get(sk, real_aligned)
    cur = int(round(cur / step) * step)
    cur = max(vmin, min(vmax, cur))
    st.session_state[sk] = cur

    nkey = f"num_{key_prefix}"
    skey = f"sl_{key_prefix}"

    # Sincronizzazione bidirezionale tramite callback
    def _from_num():
        v = int(round(st.session_state[nkey] / step) * step)
        v = max(vmin, min(vmax, v))
        st.session_state[sk] = v
        st.session_state[skey] = v   # aggiorna anche lo slider

    def _from_sl():
        v = int(round(st.session_state[skey] / step) * step)
        v = max(vmin, min(vmax, v))
        st.session_state[sk] = v
        st.session_state[nkey] = v   # aggiorna anche il number_input

    # Inizializzo le 2 chiavi se non presenti, cosi' partono allineate
    if nkey not in st.session_state:
        st.session_state[nkey] = cur
    if skey not in st.session_state:
        st.session_state[skey] = cur

    cols = st.columns([1, 2])
    with cols[0]:
        st.number_input(
            label, min_value=vmin, max_value=vmax, step=step,
            key=nkey, on_change=_from_num,
        )
    with cols[1]:
        st.slider(
            " ", min_value=vmin, max_value=vmax, step=step,
            key=skey, on_change=_from_sl,
            label_visibility="collapsed",
        )
    # Valore corrente sotto i widget, con separatore migliaia
    val_cur = st.session_state[sk]
    st.markdown(
        f"<div style='text-align:right; color:#1F2937; font-size:.95rem; "
        f"margin-top:.2rem;'>Consumo selezionato: "
        f"<b>{_fmt_thousands(val_cur)} {unit}</b></div>",
        unsafe_allow_html=True,
    )
    return val_cur


cons_ele_sel = _consumo_widget(
    "Consumo mensile ELE (kWh)", cons_ele_real, step=10_000,
    key_prefix="ele", unit="kWh",
)
fatt_ele = cons_ele_sel / cons_ele_real if cons_ele_real else 1.0
st.caption(
    f"<span style='color:#6B7280;'>Fattore vs consumo reale: <b>{fatt_ele:.2f}×</b> "
    f"(reale: {_fmt_thousands(cons_ele_real)} kWh)</span>",
    unsafe_allow_html=True,
)

# Calcolo per CIASCUNA delle 4 fasce, poi aggrego BT<=3+BT4.5-40 -> BT<=40 (3 categorie)
def _conv_scalata(r, fatt):
    cons_o = float(r["consumo_mese"])
    cons_n = cons_o * fatt
    if not cons_n:
        return 0.0
    return float(r["materia_prima_conv"]) * cons_o / cons_n


_conv_4 = {r["tipologia"]: _conv_scalata(r, fatt_ele) for _, r in df_ele.iterrows()}
_merc_4 = {r["tipologia"]: interp_sens(f"ELE|{r['tipologia']}", fatt_ele,
                                        fallback_value=float(r["benchmark_mercato"]))
           for _, r in df_ele.iterrows()}
_cons_4 = {r["tipologia"]: float(r["consumo_mese"]) for _, r in df_ele.iterrows()}

# Aggrego BT<=3 + BT4.5-40 -> BT<=40 con media pesata sui consumi originali
cons_bt_low_tot = _cons_4.get("BT <=3 kW", 0) + _cons_4.get("BT 4.5-40 kW", 0)
if cons_bt_low_tot:
    bt_low_conv_sc = (
        _conv_4.get("BT <=3 kW", 0) * _cons_4.get("BT <=3 kW", 0)
        + _conv_4.get("BT 4.5-40 kW", 0) * _cons_4.get("BT 4.5-40 kW", 0)
    ) / cons_bt_low_tot
    bt_low_merc_sc = (
        _merc_4.get("BT <=3 kW", 0) * _cons_4.get("BT <=3 kW", 0)
        + _merc_4.get("BT 4.5-40 kW", 0) * _cons_4.get("BT 4.5-40 kW", 0)
    ) / cons_bt_low_tot
else:
    bt_low_conv_sc = bt_low_merc_sc = 0.0

cat_ele_3 = ["BT <=40 kW", "BT >40 kW", "MT"]
y_conv_e_sc = [bt_low_conv_sc,
               _conv_4.get("BT >40 kW", 0),
               _conv_4.get("MT", 0)]
y_merc_e_sc = [bt_low_merc_sc,
               _merc_4.get("BT >40 kW", 0),
               _merc_4.get("MT", 0)]

st.plotly_chart(
    bar_gruppi(cat_ele_3, y_conv_e_sc, y_merc_e_sc,
               C_CONV_ELE, C_MERC_ELE, LABEL_CONV_ELE, LABEL_MERC_ELE, "€/MWh",
               height=420),
    use_container_width=True,
)

# --------------- 4.2 Gas ---------------
st.subheader(f"4.2 {ICON_GAS} Gas (Smc)")
cons_gas_real = meta["consumo_gas_totale_smc"]
cons_gas_sel = _consumo_widget(
    "Consumo mensile GAS (Smc)", cons_gas_real, step=1_000,
    key_prefix="gas", unit="Smc",
)
fatt_gas = cons_gas_sel / cons_gas_real if cons_gas_real else 1.0
st.caption(
    f"<span style='color:#6B7280;'>Fattore vs consumo reale: <b>{fatt_gas:.2f}×</b> "
    f"(reale: {_fmt_thousands(cons_gas_real)} Smc)</span>",
    unsafe_allow_html=True,
)

usi_gas = df_gas["tipologia"].tolist()
y_conv_g_sc = []
y_merc_g_sc = []
for _, r in df_gas.iterrows():
    cons_o = float(r["consumo_mese"])
    cons_n = cons_o * fatt_gas
    p_conv_sc = (float(r["materia_prima_conv"]) * cons_o / cons_n
                 if cons_n else 0)
    y_conv_g_sc.append(p_conv_sc)
    key = f"GAS|{r['tipologia']}"
    y_merc_g_sc.append(interp_sens(key, fatt_gas))

st.plotly_chart(
    bar_gruppi([_short_gas(t) for t in usi_gas],
               y_conv_g_sc, y_merc_g_sc,
               C_CONV_GAS, C_MERC_GAS, LABEL_CONV_GAS, LABEL_MERC_GAS, "c€/Smc",
               height=420),
    use_container_width=True,
)


# ------------------------------------------------------------------
# METODOLOGIA + BIBLIOGRAFIA
# ------------------------------------------------------------------
st.header("📚 Metodologia")

st.markdown(
    f"""
<div class="footer-block">

<h4>🔬 Come è costruito il benchmark</h4>

<ol>
<li><b>Convenzione MMPOWER</b> — Materia prima dell'energia elettrica composta dalle voci
<i>Generazione</i> e <i>Perdite di rete</i> riportate nel <b>report della fornitura
delle aziende convenzionate</b>. Il valore è differenziato per classe di tensione:
<b>BT</b> {meta['mp_conv_BT']:.2f} €/MWh, <b>MT</b> {meta['mp_conv_MT']:.2f} €/MWh.</li>

<li><b>Convenzione MMGAS</b> — Materia prima del gas calcolata per ciascuna tipologia
d'uso a partire dal medesimo report di fornitura delle aziende convenzionate
(importo "materia prima" diviso per i Smc consumati).</li>

<li><b>Mercato</b> — Per ogni offerta indicizzata raccolta, il prezzo è ricostruito come<br>
<code>(PUN o PSV) + spread + quota_fissa_annua / 12 × n_utenze / consumo_mese</code><br>
a cui si sommano le <b>perdite di rete</b> per l'elettrico:
<code>(PUN + spread) × {meta['coeff_perdita_BT']*100:.0f}%</code> per BT,
<code>× {meta['coeff_perdita_MT']*100:.1f}%</code> per MT.</li>

<li><b>Selezione del Top 10</b> — Per ciascuna fascia di potenza (elettrico) o tipologia
d'uso (gas) si ordinano in modo crescente tutti i prezzi ricostruiti delle offerte
raccolte sul mercato e si selezionano le <b>10 più convenienti</b>. La loro media
aritmetica costituisce il valore di benchmark di mercato esposto nei grafici.</li>
</ol>
""",
    unsafe_allow_html=True,
)

# --- Lista fornitori CON / SENZA offerte ---
fornitori_con  = D.get("fornitori_con_offerte")
fornitori_senza = D.get("fornitori_senza_offerte")
# Fallback per data.json di versione precedente
if fornitori_con is None or fornitori_senza is None:
    _alias = {
        "AGSM / Magis Energia": ["agsm", "magis"], "A2A Energia": ["a2a"],
        "Axpo Italia": ["axpo"], "Dolomiti Energia": ["dolomiti"],
        "Edison Energia": ["edison"], "Enel Energia": ["enel"],
        "Engie Italia": ["engie"], "Eni Plenitude": ["plenitude", "eni "],
        "Hera Comm": ["hera"], "Iren Mercato": ["iren"],
        "Repower Italia": ["repower"], "Sorgenia": ["sorgenia"],
    }
    _txt = " | ".join(str(o.get("offerta", "")) for o in D.get("offerte_tutte", [])).lower()
    fornitori_con = [n for n, a in _alias.items() if any(x in _txt for x in a)]
    fornitori_senza = [f["nome"] for f in D.get("fornitori", []) if f["nome"] not in fornitori_con]

# Data di estrazione (fallback alla mtime del data.json)
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

# Conteggi offerte ELE/GAS
n_off_tot = meta.get("n_offerte_totali") or D.get("meta", {}).get("n_offerte_totali", 0)
n_off_ele = D.get("meta", {}).get("n_offerte_ele")
n_off_gas = D.get("meta", {}).get("n_offerte_gas")
if n_off_ele is None or n_off_gas is None:
    _ot = D.get("offerte_tutte", [])
    n_off_ele = sum(1 for o in _ot if o.get("commodity") == "ELE")
    n_off_gas = sum(1 for o in _ot if o.get("commodity") == "GAS")


def _elenco_virgole(lst):
    if not lst: return ""
    if len(lst) == 1: return lst[0]
    return ", ".join(lst[:-1]) + " e " + lst[-1]


testo_con = _elenco_virgole(fornitori_con)
testo_senza = _elenco_virgole(fornitori_senza)

# Continuazione DENTRO il footer-block (apertura div + sezioni 1-4 sono sopra)
st.markdown(
    f"""
<h4>📊 Offerte raccolte</h4>
<p>In data <b>{data_estr_it or '—'}</b> sono state raccolte e analizzate
complessivamente <span class="num-evidenza">{n_off_tot} offerte indicizzate</span>
attive sul mercato libero italiano, provenienti sia dai siti istituzionali dei
fornitori sia dai principali portali comparatori, di cui
<b>{n_off_ele}</b> per l'energia elettrica e <b>{n_off_gas}</b> per il gas.</p>

<h4>🏢 Fornitori monitorati</h4>
<p>I fornitori per cui è stato possibile rilevare almeno una delle {n_off_tot}
offerte raccolte sono
{testo_con if testo_con else "<i>nessuno (rigenera i dati)</i>"}.
{("Sono stati monitorati ma non è stato possibile rilevare alcuna offerta "
  "indicizzata sul mercato per " + testo_senza + ".") if testo_senza else ""}</p>

</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# BIBLIOGRAFIA: tutti i link a fornitori, offerte, portali
# ------------------------------------------------------------------
st.header("🔗 Bibliografia")


def _link_lista(items):
    """Trasforma una lista di {nome,url} in HTML 'A, B e C' con i nomi linkati."""
    parts = [f'<a href="{x["url"]}" target="_blank">{x["nome"]}</a>' for x in items]
    if not parts: return ""
    if len(parts) == 1: return parts[0]
    return ", ".join(parts[:-1]) + " e " + parts[-1]


# 1) ARERA come PRIMA voce
arera_url = ("https://www.arera.it/dati-e-statistiche/dettaglio/prezzi-finali-"
             "energia-elettrica-per-i-consumatori-domestici-tipo")
st.markdown(
    f"""
<p><b>Fonte prezzi all'ingrosso:</b>
<a href="{arera_url}" target="_blank">ARERA — PLACET</a>
(PUN monorario per l'energia elettrica, PSV per il gas).</p>

<p><b>Portali comparatori monitorati:</b><br>
{_link_lista(D.get("portali", []))}.</p>

<p><b>Siti istituzionali dei fornitori monitorati:</b><br>
{_link_lista(D.get("fornitori", []))}.</p>
""",
    unsafe_allow_html=True,
)

# 2) PDF riservato delle offerte (download, no tabella inline)
pdf_path = Path(__file__).parent / (D.get("meta", {}).get("pdf_offerte_path")
                                     or "offerte_riservate.pdf")
st.markdown("<br><b>📄 Elenco completo delle offerte raccolte</b>",
            unsafe_allow_html=True)
if pdf_path.exists():
    pdf_bytes = pdf_path.read_bytes()
    st.markdown(
        "<p style='color:#6B7280; font-size:.92rem;'>Il dettaglio delle offerte "
        "indicizzate raccolte è disponibile in un documento PDF <b>riservato</b>, "
        "protetto da password. Per ottenere la password contattare l'Unione "
        "Industriali Torino — Gas & Power.</p>",
        unsafe_allow_html=True,
    )
    st.download_button(
        label="🔒 Scarica il PDF riservato delle offerte",
        data=pdf_bytes,
        file_name="offerte_indicizzate_riservate.pdf",
        mime="application/pdf",
        type="primary",
    )
else:
    st.info(
        "Il PDF riservato delle offerte non è ancora stato generato. "
        "Esegui la cella **5.6** del notebook per produrlo."
    )

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
