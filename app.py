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

# Titolo + descrizione introduttiva in un unico blocco con barra blu in fondo
st.markdown(
    """
<div style="text-align:center; border-bottom: 4px solid #6BAED6;
            padding-bottom: 1rem; margin: .6rem 0 1.6rem 0;">

  <div style="font-family: 'Segoe UI', system-ui, sans-serif;
              font-size: .78rem; font-weight: 600; letter-spacing: .22em;
              color:#94A3B8; text-transform: uppercase; margin-bottom: .35rem;">
    Unione Industriali Torino &nbsp;·&nbsp; Area Gas &amp; Power
  </div>

  <h1 style="margin: 0 0 .65rem 0; padding: 0; border: none;
             font-family: 'Segoe UI', 'Helvetica Neue', system-ui, -apple-system, sans-serif;
             font-size: 2.9rem; font-weight: 800; letter-spacing: -0.02em;
             line-height: 1.1;
             background: linear-gradient(135deg, #2C5784 0%, #4A6FA5 35%,
                                                 #C97950 65%, #B4495C 100%);
             -webkit-background-clip: text; background-clip: text;
             -webkit-text-fill-color: transparent; color: transparent;
             text-shadow: 0 1px 0 rgba(0,0,0,0.02);">
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

# --- Riquadro PERIODO DI OSSERVAZIONE (PUN per fasce ARERA + PSV) ---
# Mostro i PUN ARERA per fascia oraria del mese (F1, F2, F3) e il PSV gas.
# I PUN ponderati TOT/BT/MT sono mostrati in dettaglio in Metodologia.
_pun_tot = meta.get("PUN_TOT_eur_kWh") or meta.get("PUN_eur_kWh", 0)
_pun_bt  = meta.get("PUN_BT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_mt  = meta.get("PUN_MT_eur_kWh")  or meta.get("PUN_eur_kWh", 0)
_pun_f1  = meta.get("PUN_F1_eur_kWh") or 0
_pun_f2  = meta.get("PUN_F2_eur_kWh") or 0
_pun_f3  = meta.get("PUN_F3_eur_kWh") or 0

st.markdown(
    f"""
<div class="periodo-box">
  <div style="display:flex; flex-direction:column; flex:1;">
    <span class="periodo-label">📅 Periodo di osservazione</span>
    <span class="periodo-value">{mese_label(meta['mese'])}</span>
  </div>
  <div style="display:flex; flex-direction:column; gap:.25rem; text-align:right;
              border-left:1px solid #CBD5E1; padding-left:1.2rem;">
    <span style="color:#374151; font-size:.9rem;">
      <span style="color:#6B7280;">PUN per fasce</span>
      &nbsp;&nbsp;
      <b style="color:#16A34A;">F1 {_pun_f1:.4f}</b>
      &nbsp;·&nbsp;
      <b style="color:#16A34A;">F2 {_pun_f2:.4f}</b>
      &nbsp;·&nbsp;
      <b style="color:#16A34A;">F3 {_pun_f3:.4f}</b>
      <span style="color:#9CA3AF;font-size:.85rem;">&nbsp;€/kWh</span>
    </span>
    <span style="color:#374151; font-size:.9rem;">
      <span style="color:#6B7280;">PSV</span>
      &nbsp;<b style="color:#16A34A;">{meta['PSV_eur_Smc']:.4f} €/Smc</b>
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
Confronto a colpo d'occhio fra il <b>prezzo della materia prima riconosciuta dalle
Convenzioni</b> e il <b>benchmark</b> calcolato come media delle <b>10 migliori offerte
attive sul mercato libero</b>. Per ciascuna offerta il prezzo è ricostruito come
<i>PUN/PSV indicizzato + spread + quota fissa unitaria</i>; per il solo <b>elettrico</b>
si aggiungono le <b>perdite di rete</b>.
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
è calcolata per ciascuna delle tre fasce di potenza presenti nel report della
fornitura delle aziende convenzionate (media ponderata sui consumi dei POD di
ciascuna fascia); le <b>Top 10 di mercato</b> sono invece ricalcolate per ciascuna
categoria, in quanto le offerte migliori possono variare a seconda della fascia di
potenza presa come riferimento.
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
Dettaglio per <b>tipologia d'uso del gas</b>. La materia prima della Convenzione
è calcolata distintamente <b>per ciascuna delle quattro tipologie d'uso</b>
(media ponderata sui consumi e importi reali del mese, per ogni categoria); le
<b>Top 10 di mercato</b> sono ricalcolate per ciascuna categoria, in quanto le
offerte migliori possono variare a seconda della tipologia d'uso presa come
riferimento.
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
desiderato per ciascuna categoria si ottiene una proiezione immediata di quanto la
materia prima Convenzione e il benchmark di mercato si sposterebbero al variare
della composizione del portafoglio di utenze, mantenendo costanti i consumi medi
per POD/PDR rilevati nel periodo di osservazione.
<ul>
  <li>per il <b>4.1 Elettrico</b>, il prezzo aggregato corrisponderà alla media
  ponderata sui consumi al variare del numero e della fascia di potenza delle
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


# Consumi MEDI reali per POD/PDR del mese selezionato (FISSI, non modificabili).
# Sono i valori di "una singola utenza media" della propria categoria.
n_bt_real = int(df_conf[(df_conf["commodity"] == "ELE")
                        & (df_conf["tipologia"].str.startswith("BT", na=False))]["n_utenze"].sum())
n_mt_real = int(df_conf[(df_conf["commodity"] == "ELE")
                        & (df_conf["tipologia"] == "MT")]["n_utenze"].sum())
cons_bt_tot_real = float(df_conf[(df_conf["commodity"] == "ELE")
                                  & (df_conf["tipologia"].str.startswith("BT", na=False))]["consumo_mese"].sum())
cons_mt_tot_real = float(df_conf[(df_conf["commodity"] == "ELE")
                                  & (df_conf["tipologia"] == "MT")]["consumo_mese"].sum())
cons_bt_medio = cons_bt_tot_real / n_bt_real if n_bt_real else 2000.0
cons_mt_medio = cons_mt_tot_real / n_mt_real if n_mt_real else 40000.0

n_pdr_real = int(df_conf[df_conf["commodity"] == "GAS"]["n_utenze"].sum())
cons_gas_tot_real = float(df_conf[df_conf["commodity"] == "GAS"]["consumo_mese"].sum())
cons_pdr_medio = cons_gas_tot_real / n_pdr_real if n_pdr_real else 2500.0


# =================================================================
# 4.1 Elettrico — 2 slider (n_BT, n_MT) sui numeri di utenze.
#   I consumi medi per POD sono FISSI (medi reali del mese selezionato).
#   Si parte con 1 BT + 1 MT (utenze medie).
# =================================================================
st.subheader(f"4.1 {ICON_ELE} Elettrico — simulatore per utenza media")

st.markdown(
    f"""
<div style="background:#F8FAFC; border:1px solid #E5E7EB; border-radius:8px;
            padding:.8rem 1rem; margin: .4rem 0 1rem 0; font-size:.92rem;">
🧮 <b>Riferimento "utenza media" del mese selezionato</b>
(media reale sulle utenze POD del campione):<br>
&nbsp;&nbsp;⚡ <b>Utenza in Bassa Tensione (BT)</b>:
{_fmt_thousands(round(cons_bt_medio))} kWh/mese per POD<br>
&nbsp;&nbsp;⚡ <b>Utenza in Media Tensione (MT)</b>:
{_fmt_thousands(round(cons_mt_medio))} kWh/mese per POD
</div>
""",
    unsafe_allow_html=True,
)

cE1, cE2 = st.columns(2)
with cE1:
    n_bt = _slider_intero("BT", vmin=0, vmax=2000,
                           default=1, step=1, key_prefix="n_bt")
with cE2:
    n_mt = _slider_intero("MT", vmin=0, vmax=500,
                           default=1, step=1, key_prefix="n_mt")

if n_bt == 0 and n_mt == 0:
    st.warning("Seleziona almeno una utenza BT o MT per visualizzare il confronto.")
else:
    # Uso PUN_BT e PUN_MT pesati (sui consumi storici per fascia oraria)
    pun_bt_val = float(meta.get("PUN_BT_eur_kWh") or meta.get("PUN_eur_kWh", 0))
    pun_mt_val = float(meta.get("PUN_MT_eur_kWh") or meta.get("PUN_eur_kWh", 0))
    mp_conv_bt = float(meta.get("mp_conv_BT", 0))    # €/MWh, fisso
    mp_conv_mt = float(meta.get("mp_conv_MT", 0))

    # Benchmark di mercato a consumo medio fisso (per fascia)
    bench_bt = _benchmark_mercato_singola(
        "ELE", pun_bt_val, cons_bt_medio,
        coeff_perdita=meta.get("coeff_perdita_BT", 0.10),
    )
    bench_mt = _benchmark_mercato_singola(
        "ELE", pun_mt_val, cons_mt_medio,
        coeff_perdita=meta.get("coeff_perdita_MT", 0.038),
    )

    # Consumi totali simulati
    cons_bt_sim = n_bt * cons_bt_medio
    cons_mt_sim = n_mt * cons_mt_medio
    cons_tot = cons_bt_sim + cons_mt_sim

    # Caso "solo BT" o "solo MT": una singola barra (no media ponderata)
    if n_bt > 0 and n_mt == 0:
        etichetta = f"⚡ Solo BT ({n_bt} POD × {_fmt_thousands(round(cons_bt_medio))} kWh)"
        conv_v, merc_v, unit = mp_conv_bt, (bench_bt or 0), "€/MWh"
    elif n_mt > 0 and n_bt == 0:
        etichetta = f"⚡ Solo MT ({n_mt} POD × {_fmt_thousands(round(cons_mt_medio))} kWh)"
        conv_v, merc_v, unit = mp_conv_mt, (bench_mt or 0), "€/MWh"
    else:
        # Aggregato BT + MT (media ponderata sui consumi simulati)
        conv_v = (mp_conv_bt * cons_bt_sim + mp_conv_mt * cons_mt_sim) / max(cons_tot, 1)
        if bench_bt is not None and bench_mt is not None:
            merc_v = (bench_bt * cons_bt_sim + bench_mt * cons_mt_sim) / max(cons_tot, 1)
        else:
            merc_v = bench_bt or bench_mt or 0
        etichetta = (f"⚡ Aggregato {n_bt} BT + {n_mt} MT "
                     f"({_fmt_thousands(round(cons_tot))} kWh totali)")
        unit = "€/MWh"

    st.plotly_chart(
        bar_gruppi([etichetta], [conv_v], [merc_v],
                   C_CONV_ELE, C_MERC_ELE,
                   LABEL_CONV_ELE, LABEL_MERC_ELE, unit, height=400),
        use_container_width=True,
    )

    # Etichetta mese-anno compatta (es. mar-26)
    _MESI_AB = ["", "gen", "feb", "mar", "apr", "mag", "giu",
                "lug", "ago", "set", "ott", "nov", "dic"]
    _y, _m = map(int, meta["mese"].split("-"))
    _mese_aa = f"{_MESI_AB[_m]}-{str(_y)[-2:]}"

    pezzi = []
    if n_bt > 0 and bench_bt is not None:
        pezzi.append(f"<b>BT</b>: {bench_bt:.2f} €/MWh")
    if n_mt > 0 and bench_mt is not None:
        pezzi.append(f"<b>MT</b>: {bench_mt:.2f} €/MWh")
    if pezzi:
        st.caption(
            f"<span style='color:#6B7280;'>Prezzo Materia Prima per potenza "
            f"{_mese_aa} &mdash; " + " · ".join(pezzi) + "</span>",
            unsafe_allow_html=True,
        )


# =================================================================
# 4.2 Gas — 4 slider, uno per ciascuna tipologia d'uso.
#   Per ogni tipologia: consumo medio per PDR e prezzo Convenzione FISSI dal mese.
#   L'aumento del numero di utenze sposta il mix (e quindi la media ponderata).
# =================================================================
st.subheader(f"4.2 {ICON_GAS} Gas — simulatore per utenza media (per tipologia d'uso)")

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
    f"&nbsp;&nbsp;🔥 <b>Utenza con Tipologia {g['tip']}</b>: "
    f"{_fmt_thousands(round(g['cons_medio']))} Smc/mese per PDR"
    for g in gas_tipi
)
st.markdown(
    f"""
<div style="background:#F8FAFC; border:1px solid #E5E7EB; border-radius:8px;
            padding:.8rem 1rem; margin: .4rem 0 1rem 0; font-size:.92rem;">
🧮 <b>Riferimenti "utenza media gas" per tipologia d'uso del mese selezionato</b>
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
            g["tip"],
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
    st.plotly_chart(
        bar_gruppi([etichetta_gas], [conv_gas_v], [merc_gas_v],
                   C_CONV_GAS, C_MERC_GAS,
                   LABEL_CONV_GAS, LABEL_MERC_GAS, "c€/Smc", height=400),
        use_container_width=True,
    )
    # Caption: SEMPRE i 4 bench per tipologia (anche se n_gas=0), in label abbreviato
    _MESI_AB_G = ["", "gen", "feb", "mar", "apr", "mag", "giu",
                  "lug", "ago", "set", "ott", "nov", "dic"]
    _yg, _mg = map(int, meta["mese"].split("-"))
    _mese_aa_g = f"{_MESI_AB_G[_mg]}-{str(_yg)[-2:]}"

    pezzi_full = []
    for g in gas_tipi:
        b_tip = _benchmark_mercato_singola(
            "GAS", psv_val, g["cons_medio"], coeff_perdita=0.0,
        )
        if b_tip is not None:
            pezzi_full.append(f"<b>{g['label_short']}</b>: {b_tip:.2f} c€/Smc")
    if pezzi_full:
        st.caption(
            f"<span style='color:#6B7280;'>Prezzo Materia Prima per Tipologia "
            f"{_mese_aa_g} &mdash; " + " · ".join(pezzi_full) + "</span>",
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------------
# METODOLOGIA + BIBLIOGRAFIA
# ------------------------------------------------------------------
st.header("📚 Metodologia")

# ----- Sotto-sezione 1: come è costruito il benchmark -----
st.markdown(
    f"""
<div class="footer-block">

<h4 style="margin-top:0;">🔬 Come è costruito il benchmark</h4>

<ol style="line-height:1.6;">
<li style="margin-bottom: 1.2rem;"><b>Convenzione MMPOWER</b> — Materia prima dell'energia elettrica composta dalle
voci <i>Generazione</i> e <i>Perdite di rete</i> calcolate a partire dai
<b>dati reali</b> di fornitura delle aziende convenzionate (media ponderata sui
consumi effettivi del periodo di osservazione).</li>

<li style="margin-bottom: 1.2rem;"><b>Convenzione MMGAS</b> — Materia prima del gas calcolata per ciascuna tipologia
d'uso a partire dai <b>dati reali</b> di fornitura delle aziende
convenzionate (importo "materia prima" diviso per i Smc consumati del mese).</li>

<li style="margin-bottom: 1.2rem;"><b>Mercato</b> — Per ogni offerta indicizzata raccolta il prezzo è ricostruito
distintamente per i due vettori:<br><br>
&nbsp;&nbsp;&nbsp;⚡ <b>Energia elettrica</b>:
<code>P = PUNx + spread + (PUNx + spread) × coeff_perdita + (quota_fissa_annua × n_utenze) ÷ (12 × consumo_mese)</code><br>
&nbsp;&nbsp;&nbsp;&nbsp;dove <code>coeff_perdita</code> = {meta['coeff_perdita_BT']*100:.0f}%
per le utenze BT e {meta['coeff_perdita_MT']*100:.1f}% per quelle MT.<br><br>
&nbsp;&nbsp;&nbsp;🔥 <b>Gas</b>:
<code>P = PSV + spread + (quota_fissa_annua × n_utenze) ÷ (12 × consumo_mese)</code>.</li>

<li style="margin-bottom: 1.2rem;"><b>PUNx: PUN Ponderato per Fasce</b> — Anziché applicare il PUN monorario
all'intero campione, viene utilizzato un <b>PUNx</b> differenziato per classe di
tensione (PUN BT, PUN MT) e un PUNx aggregato totale (PUN TOT). Questo consente di
rappresentare in modo più aderente alla realtà il prezzo all'ingrosso
dell'elettrico, riconoscendo che la composizione oraria del consumo è
strutturalmente diversa fra utenze a Bassa Tensione e a Media Tensione: il PUNx
così ponderato si avvicina di più al costo effettivo che ciascun segmento sostiene
per l'energia ritirata dal mercato.<br><br>
Per il mese di <b>{mese_label(meta['mese'])}</b>:<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN TOT</b>: {_pun_tot:.4f} €/kWh — usato nel grafico Generale (sezione 1)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN BT</b>: {_pun_bt:.4f} €/kWh — usato per le fasce BT (sezioni 2 e 4.1)<br>
&nbsp;&nbsp;&nbsp;&nbsp;⚡ <b>PUN MT</b>: {_pun_mt:.4f} €/kWh — usato per la fascia MT (sezioni 2 e 4.1)<br><br>
Il <b>PUN TOT</b> è la media ponderata tra PUN BT e PUN MT sui consumi reali del mese
in osservazione del campione corrente; i prezzi <b>PUN BT</b> e <b>PUN MT</b>
corrispondono alle medie ponderate dei prezzi PUN per fascia ARERA per le percentuali
dei consumi storici per fascia, del mese osservato, delle utenze convenzionate.</li>

<li style="margin-bottom: 1.2rem;"><b>Selezione del Top 10</b> — Per ciascuna fascia di potenza (elettrico) o
tipologia d'uso (gas) si ordinano in modo crescente tutti i prezzi ricostruiti
delle offerte raccolte sul mercato e si selezionano le <b>10 più convenienti</b>.
La loro media aritmetica costituisce il valore di benchmark di mercato esposto nei
grafici.</li>
</ol>

</div>
""",
    unsafe_allow_html=True,
)

# ----- Sotto-sezione 2: offerte e fornitori monitorati -----
# Calcolo i dati Python prima, poi un UNICO st.markdown con tutto il contenuto
# dentro lo stesso div.footer-block (cosi' il sottotitolo e i paragrafi sono
# visivamente uniti nella stessa box).

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

# UN UNICO blocco markdown per garantire che tutto sia dentro il footer-block
st.markdown(
    f"""
<div class="footer-block" style="margin-top:1rem;">

<h4 style="margin-top:0;">🏢 Offerte e Fornitori monitorati</h4>

<p>In data <b>{data_estr_it or '—'}</b> sono state raccolte e analizzate
complessivamente <span class="num-evidenza">{n_off_tot} offerte indicizzate</span>
attive sul mercato libero italiano, provenienti sia dai siti istituzionali dei
fornitori sia dai principali portali comparatori, di cui
<b>{n_off_ele}</b> per l'energia elettrica e <b>{n_off_gas}</b> per il gas.</p>

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
            min-height:430px; display:flex; flex-direction:column;">
<h4 style="color:#2C5784; margin-top:0;">⚡ Convenzione MMPOWER 2026-2027</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Iren Mercato S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Prezzo materia prima</b>: indicizzato al <b>PUN Index GME</b> mensile <b>per fasce
orarie</b> (F1, F2, F3), maggiorato di uno spread fisso
<b>2,70 €/MWh</b>, invariabile per tutto il biennio di fornitura</li>
<li><b>Commercializzazione e vendita</b>: <b>nessun corrispettivo aggiuntivo</b></li>
<li><b>Soglia consumo</b>: <b>3.000.000 kWh/anno</b> per singola utenza</li>
<li><b>Periodo di fornitura</b>: <b>fino al 31/12/2027</b></li>
<li><b>Opzione 100% energia verde</b> (su richiesta del singolo cliente):
+1,40 €/MWh nel 2026, +1,70 €/MWh nel 2027</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    pdf_mmp = Path(__file__).parent / "News_Convenzione_MMPOWER_2026-2027.pdf"
    if pdf_mmp.exists():
        st.download_button(
            label="📄 Scarica la news completa MMPOWER *",
            data=pdf_mmp.read_bytes(),
            file_name="News_Convenzione_MMPOWER_2026-2027.pdf",
            mime="application/pdf",
            type="primary",
            key="dl_mmp",
        )

# ---------- MMGAS ----------
with cN2:
    st.markdown(
        """
<div style="border:1px solid #F0A35E; border-radius:12px; padding:1rem 1.2rem;
            background:linear-gradient(180deg,#FFFFFF,#FCF5EE);
            min-height:430px; display:flex; flex-direction:column;">
<h4 style="color:#B4495C; margin-top:0;">🔥 Convenzione MMGAS 2025/26 — 2026/27</h4>
<p style="color:#6B7280; margin:.2rem 0 1rem 0; font-size:.9rem;">
Fornitore: <b>Eni Plenitude S.p.A.</b></p>

<ul style="font-size:.95rem; line-height:1.5; flex:1;">
<li><b>Prezzo materia prima</b>: indicizzato al <b>CMEM</b> (media mensile
quotazioni Day Ahead PSV) maggiorato di uno spread fisso
<b>0,023 €/Smc</b>, invariabile per tutto il biennio di fornitura</li>
<li><b>Commercializzazione e vendita</b>: corrispettivo fisso <b>7 €/mese</b>
+ variabile <b>0,007946 €/Smc</b></li>
<li><b>Soglia consumo</b>: <b>200.000 Smc/anno</b> per singolo cliente</li>
<li><b>Periodo di fornitura</b>: <b>fino al 30/09/2027</b></li>
<li><b>Opzione 100% CO₂ compensata</b> (su richiesta del singolo cliente):
+ 0,0263 €/Smc</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
    pdf_mmg = Path(__file__).parent / "News_Convenzione_MMGAS_2025-26_2026-27.pdf"
    if pdf_mmg.exists():
        st.download_button(
            label="📄 Scarica la news completa MMGAS *",
            data=pdf_mmg.read_bytes(),
            file_name="News_Convenzione_MMGAS_2025-26_2026-27.pdf",
            mime="application/pdf",
            type="primary",
            key="dl_mmg",
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


# ------------------------------------------------------------------
# SITOGRAFIA
# ------------------------------------------------------------------
st.header("🔗 Sitografia")


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
