"""
Benchmark Materia Prima Gas&Power — Unione Industriali Torino
Dashboard Streamlit: confronto Convenzioni MMPOWER/MMGAS vs Top 10 offerte di mercato.

Esecuzione locale:
    streamlit run app.py

Deploy: https://share.streamlit.io  (repo Cornagli8/benchmark-energia-uitorino)
"""
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


# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    """
<style>
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
    h1, h2, h3 { color: #0F172A; }
    h1 { border-bottom: 4px solid #6BAED6; padding-bottom: .4rem; margin-top: .6rem; }
    h2 { margin-top: 2.2rem; padding-left: .4rem; border-left: 5px solid #6BAED6; }
    h2.gas-section { border-left-color: #F0A35E; }

    /* Header loghi */
    .logo-row {
        display: flex; justify-content: center; align-items: center;
        gap: 2.2rem; margin: 0 0 1.0rem 0;
    }
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

# Caricamento INDIPENDENTE: se uno dei loghi manca uso il placeholder solo per quello
cl1, cl2, cl3 = st.columns([1, 1, 1])
LOGO_WIDTH = 180


def _logo_or_placeholder(col, key, placeholder_html):
    p = logo_files[key]
    if p.exists():
        # vbox: immagine centrata verticalmente
        with col:
            col.markdown(
                "<div style='display:flex;justify-content:center;align-items:center;"
                "min-height:90px;'>",
                unsafe_allow_html=True,
            )
            col.image(str(p), width=LOGO_WIDTH)
            col.markdown("</div>", unsafe_allow_html=True)
    else:
        col.markdown(
            f"<div style='display:flex;justify-content:center;align-items:center;"
            f"min-height:90px;'>{placeholder_html}</div>",
            unsafe_allow_html=True,
        )


_logo_or_placeholder(cl1, "mmpower",
                     '<div class="logo-pill mmpower">⚡ MMPOWER</div>')
_logo_or_placeholder(cl2, "ui",
                     '<div class="logo-pill ui-torino">UNIONE INDUSTRIALI TORINO</div>')
_logo_or_placeholder(cl3, "mmgas",
                     '<div class="logo-pill mmgas">🔥 MMGAS</div>')

# Se mancano i loghi UI e/o MMGAS, suggerimento operativo (solo se serve)
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
    """Bar chart con legenda a destra e delta evidenziato."""
    delta = val_merc - val_conv
    delta_pct = (delta / val_conv * 100) if val_conv else 0
    color_delta = "#B4495C" if delta > 0 else "#2F855A"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[label_conv], y=[val_conv], name=label_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_conv:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.5,
    ))
    fig.add_trace(go.Bar(
        x=[label_merc], y=[val_merc], name=label_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_merc:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK), width=0.5,
    ))
    fig.update_layout(
        title=dict(text=titolo, font=dict(size=16, color=C_TEXT_DARK)),
        showlegend=True,
        legend=dict(
            orientation="v", x=1.02, xanchor="left", y=0.5, yanchor="middle",
            bgcolor="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1,
            font=dict(size=11),
        ),
        height=420, plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        yaxis=dict(title=unita, gridcolor="#E5E7EB", zerolinecolor="#E5E7EB"),
        xaxis=dict(showticklabels=False),
        margin=dict(t=80, b=40, l=60, r=180),
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
               label_conv, label_merc, unita, height=460):
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
        xaxis=dict(title=""), bargap=0.25, bargroupgap=0.08,
        legend=dict(orientation="v", x=1.02, xanchor="left", y=0.5,
                    yanchor="middle", bgcolor="#F8FAFC",
                    bordercolor="#CBD5E1", borderwidth=1, font=dict(size=11)),
        margin=dict(t=50, b=60, l=60, r=200),
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

st.caption(
    f"Aggregazione BT ≤40 kW: prezzo_BT≤3 × {cons_low_3:,.0f} kWh + "
    f"prezzo_BT4,5–40 × {cons_low_40:,.0f} kWh, diviso il totale "
    f"{cons_low_3 + cons_low_40:,.0f} kWh = <b>{bt_low_conv:.2f} €/MWh</b> per "
    f"la Convenzione.",
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
    bar_gruppi(df_gas["tipologia"].tolist(),
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
ce_max = int(cons_ele_real * 6)
ce_min = int(cons_ele_real * 0.1)
col_in_e, col_sl_e = st.columns([1, 2])
with col_in_e:
    cons_ele_sel = st.number_input(
        "Consumo mensile ELE (kWh)",
        min_value=ce_min, max_value=ce_max, value=int(cons_ele_real), step=10_000,
        key="num_ele",
    )
with col_sl_e:
    cons_ele_sel = st.slider(
        " ", min_value=ce_min, max_value=ce_max, value=int(cons_ele_sel),
        step=10_000, key="sl_ele", label_visibility="collapsed",
    )

fatt_ele = cons_ele_sel / cons_ele_real
st.caption(
    f"Consumo selezionato: <span class='num-evidenza'>{cons_ele_sel:,.0f} kWh</span> "
    f"({fatt_ele:.2f}× rispetto al consumo reale di {cons_ele_real:,.0f} kWh)",
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
cg_max = int(cons_gas_real * 6)
cg_min = max(1, int(cons_gas_real * 0.1))
col_in_g, col_sl_g = st.columns([1, 2])
with col_in_g:
    cons_gas_sel = st.number_input(
        "Consumo mensile GAS (Smc)",
        min_value=cg_min, max_value=cg_max, value=int(cons_gas_real), step=1_000,
        key="num_gas",
    )
with col_sl_g:
    cons_gas_sel = st.slider(
        " ", min_value=cg_min, max_value=cg_max, value=int(cons_gas_sel),
        step=1_000, key="sl_gas", label_visibility="collapsed",
    )

fatt_gas = cons_gas_sel / cons_gas_real
st.caption(
    f"Consumo selezionato: <span class='num-evidenza'>{cons_gas_sel:,.0f} Smc</span> "
    f"({fatt_gas:.2f}× rispetto al consumo reale di {cons_gas_real:,.0f} Smc)",
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
    bar_gruppi(usi_gas, y_conv_g_sc, y_merc_g_sc,
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

<h4>📊 Offerte raccolte</h4>
<p>Nel mese di <b>{mese_label(meta['mese'])}</b> sono state raccolte e
analizzate complessivamente <span class="num-evidenza">{meta['n_offerte_totali']}
offerte indicizzate</span> attive sul mercato libero italiano, provenienti sia dai
siti istituzionali dei fornitori sia dai principali portali comparatori.</p>

<h4>🏢 Fornitori monitorati</h4>
<p>Sono stati estratti i corrispettivi di spread e quota fissa pubblicati dai siti
istituzionali dei seguenti fornitori operanti sul mercato libero italiano:
""",
    unsafe_allow_html=True,
)

# Lista fornitori MONITORATI in forma descrittiva
nomi_monitorati = [f["nome"] for f in D["fornitori"]]
testo_monitorati = ", ".join(nomi_monitorati[:-1]) + " e " + nomi_monitorati[-1] + "."
st.markdown(f"<p>{testo_monitorati}</p>", unsafe_allow_html=True)

st.markdown("<h4>🚫 Fornitori non monitorati</h4>", unsafe_allow_html=True)
non_mon = D.get("fornitori_non_monitorati", [])
if non_mon:
    parti = []
    for f in non_mon:
        parti.append(f"<b>{f['nome']}</b>: {f['motivo']}")
    st.markdown(
        "<p>Per i seguenti fornitori non è stato possibile completare il monitoraggio "
        "automatico delle offerte: " + "; ".join(parti) + ".</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
<p style="margin-top:1rem; color:#6B7280; font-size:.88rem;">
Fonte prezzi all'ingrosso: <a href="https://www.arera.it/dati-e-statistiche/dettaglio/prezzi-finali-energia-elettrica-per-i-consumatori-domestici-tipo" target="_blank">ARERA — PLACET</a>
(PUN monorario per l'elettrico, PSV per il gas).
</p>

</div>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# BIBLIOGRAFIA: tutti i link a fornitori, offerte, portali
# ------------------------------------------------------------------
st.header("🔗 Bibliografia")

st.markdown(
    "<p style='color:#6B7280;'>Riferimenti per la verifica e l'aggiornamento "
    "manuale di offerte e corrispettivi.</p>",
    unsafe_allow_html=True,
)

st.markdown("**Portali comparatori**", unsafe_allow_html=True)
for p in D["portali"]:
    st.markdown(
        f'<span class="forn-pill"><a href="{p["url"]}" target="_blank">{p["nome"]} ↗</a></span>',
        unsafe_allow_html=True,
    )

st.markdown("<br>**Fornitori monitorati (siti istituzionali)**", unsafe_allow_html=True)
for f in D["fornitori"]:
    st.markdown(
        f'<span class="forn-pill"><a href="{f["url"]}" target="_blank">{f["nome"]} ↗</a></span>',
        unsafe_allow_html=True,
    )

st.markdown("<br>**Fornitori non monitorati (siti istituzionali)**", unsafe_allow_html=True)
for f in D.get("fornitori_non_monitorati", []):
    st.markdown(
        f'<span class="forn-pill"><a href="{f["url"]}" target="_blank">{f["nome"]} ↗</a></span>',
        unsafe_allow_html=True,
    )

# Offerte raccolte, raggruppate per commodity
offerte = D.get("offerte_tutte", [])
if offerte:
    df_off = pd.DataFrame(offerte)
    st.markdown(
        f"<br>**Offerte indicizzate raccolte ({len(df_off)})**",
        unsafe_allow_html=True,
    )
    tab_e, tab_g = st.tabs([f"{ICON_ELE} ELE ({(df_off['commodity']=='ELE').sum()})",
                            f"{ICON_GAS} GAS ({(df_off['commodity']=='GAS').sum()})"])
    with tab_e:
        sub = df_off[df_off["commodity"] == "ELE"].copy()
        sub = sub.sort_values("offerta").reset_index(drop=True)
        sub.index = sub.index + 1
        st.dataframe(
            sub[["offerta", "fonte", "spread", "quota_eur_anno"]]
                .rename(columns={"offerta": "Offerta", "fonte": "Fonte raccolta",
                                  "spread": "Spread €/kWh",
                                  "quota_eur_anno": "Quota fissa €/anno"}),
            use_container_width=True,
        )
    with tab_g:
        sub = df_off[df_off["commodity"] == "GAS"].copy()
        sub = sub.sort_values("offerta").reset_index(drop=True)
        sub.index = sub.index + 1
        st.dataframe(
            sub[["offerta", "fonte", "spread", "quota_eur_anno"]]
                .rename(columns={"offerta": "Offerta", "fonte": "Fonte raccolta",
                                  "spread": "Spread €/Smc",
                                  "quota_eur_anno": "Quota fissa €/anno"}),
            use_container_width=True,
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
