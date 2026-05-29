"""
Benchmark Materia Prima Energetica — UI Torino
Dashboard Streamlit: confronto Convenzioni MMPOWER/MMGAS vs Top 10 offerte di mercato.

Esecuzione locale:
    streamlit run app.py

Deploy: https://share.streamlit.io  (collega repo Cornagli8/benchmark-energia-uitorino)
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
    page_title="Benchmark Materia Prima — UI Torino",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Palette sfumata (richiesta utente)
C_CONV_ELE   = "#6BAED6"   # azzurro carta (MMPOWER)
C_MERC_ELE   = "#2C5784"   # blu navy soft (Top10 ELE)
C_CONV_GAS   = "#F0A35E"   # arancione pastello (MMGAS)
C_MERC_GAS   = "#B4495C"   # granata/bordeaux (Top10 GAS)
C_TEXT_DARK  = "#1F2937"
C_TEXT_MUTED = "#6B7280"
C_BG_SOFT    = "#F8FAFC"

ICON_ELE = "⚡"
ICON_GAS = "🔥"

LABEL_CONV_ELE = "Convenzione MMPOWER"
LABEL_MERC_ELE = "Top 10 Offerte attive sul Mercato (ELE)"
LABEL_CONV_GAS = "Convenzione MMGAS"
LABEL_MERC_GAS = "Top 10 Offerte attive sul Mercato (GAS)"


# ------------------------------------------------------------------
# CSS personalizzato
# ------------------------------------------------------------------
st.markdown(
    """
<style>
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
    h1, h2, h3 { color: #0F172A; }
    h1 { border-bottom: 4px solid #6BAED6; padding-bottom: .4rem; }
    h2 { margin-top: 2.2rem; padding-left: .4rem; border-left: 5px solid #6BAED6; }
    h2.gas-section { border-left-color: #F0A35E; }
    .kpi-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,.04);
    }
    .kpi-label { font-size: .85rem; color: #6B7280; font-weight: 500; margin-bottom: .3rem; }
    .kpi-value { font-size: 1.7rem; font-weight: 700; color: #0F172A; }
    .kpi-delta-pos { color: #B4495C; font-weight: 600; font-size: .95rem; }
    .kpi-delta-neg { color: #2F855A; font-weight: 600; font-size: .95rem; }
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
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Caricamento dati
# ------------------------------------------------------------------
def carica_dati():
    # Niente cache: il file viene riletto a ogni rerun (size <100 KB, costo trascurabile).
    # Evita problemi di stale cache dopo un git push del nuovo data.json.
    p = Path(__file__).parent / "data" / "data.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


D = carica_dati()
if D is None:
    st.error(
        "⚠️ File `data/data.json` non trovato.\n\n"
        "Esegui la **cella 5.6** del notebook `Benchmark Confronto.ipynb` "
        "per generarlo, poi `git push` per aggiornare l'app online."
    )
    st.stop()

meta = D["meta"]
df_conf = pd.DataFrame(D["confronto"])
df_gen = pd.DataFrame(D["generale"])
df_top = pd.DataFrame(D["top10"])
sens = D["sensitivity"]

# Guardia: data.json placeholder (vuoto/zeri) -> mostra messaggio, non crashare
_is_placeholder = (
    meta.get("_placeholder") is True
    or len(df_conf) == 0
    or meta.get("n_offerte_totali", 0) == 0
)
if _is_placeholder:
    st.warning(
        "⚠️ **Dati non ancora caricati.** Il file `data/data.json` è in stato "
        "placeholder. Per popolarlo:\n\n"
        "1. Apri `Benchmark Confronto.ipynb` ed esegui le celle 5.1 → 5.6\n"
        "2. Esegui i comandi:\n"
        "   ```powershell\n"
        "   cd pubblica_grafici\n"
        "   git add data/data.json\n"
        "   git commit -m \"aggiorna dati\"\n"
        "   git push\n"
        "   ```\n"
        "3. Aspetta ~1 minuto: Streamlit Cloud rigenera l'app."
    )
    st.stop()


# ------------------------------------------------------------------
# HERO HEADER
# ------------------------------------------------------------------
st.title("⚡🔥 Benchmark Materia Prima Energetica")
st.markdown(
    f"""
**Confronto fra le Convenzioni MMPOWER / MMGAS di UI Torino e il mercato libero**
italiano (top 10 offerte indicizzate sui maggiori comparatori e fornitori).
Mese di riferimento: **{meta['mese_riferimento']}** —
PUN monorario `{meta['PUN_eur_kWh']:.4f} €/kWh` · PSV `{meta['PSV_eur_Smc']:.4f} €/Smc`.
"""
)


# ------------------------------------------------------------------
# KPI CARDS
# ------------------------------------------------------------------
def kpi_card(col, label, valore, unita, delta_pct=None, icona=""):
    delta_html = ""
    if delta_pct is not None:
        cls = "kpi-delta-pos" if delta_pct > 0 else "kpi-delta-neg"
        seg = "▲" if delta_pct > 0 else "▼"
        delta_html = f'<div class="{cls}">{seg} {abs(delta_pct):.1f}% vs Convenzione</div>'
    col.markdown(
        f"""
<div class="kpi-card">
  <div class="kpi-label">{icona} {label}</div>
  <div class="kpi-value">{valore:.2f} <span style="font-size:.85rem; color:#6B7280;">{unita}</span></div>
  {delta_html}
</div>
""",
        unsafe_allow_html=True,
    )


ele_row = df_gen[df_gen["commodity"] == "ELE"].iloc[0]
gas_row = df_gen[df_gen["commodity"] == "GAS"].iloc[0]

k1, k2, k3, k4 = st.columns(4)
kpi_card(k1, LABEL_CONV_ELE, ele_row["MP_convenzione"], "€/MWh", icona=ICON_ELE)
kpi_card(k2, LABEL_MERC_ELE, ele_row["benchmark_mercato"], "€/MWh",
         delta_pct=ele_row["delta_%"], icona=ICON_ELE)
kpi_card(k3, LABEL_CONV_GAS, gas_row["MP_convenzione"], "c€/Smc", icona=ICON_GAS)
kpi_card(k4, LABEL_MERC_GAS, gas_row["benchmark_mercato"], "c€/Smc",
         delta_pct=gas_row["delta_%"], icona=ICON_GAS)

st.caption(
    f"Convenzione ELE = Generazione ({meta['generazione_conv_ele_eur_MWh']:.2f}) "
    f"+ Perdite di rete ({meta['perdite_conv_ele_eur_MWh']:.2f}) = "
    f"{meta['generazione_conv_ele_eur_MWh'] + meta['perdite_conv_ele_eur_MWh']:.2f} €/MWh. "
    f"Mercato ELE include perdite di rete: {meta['coeff_perdita_BT']*100:.0f}% BT, "
    f"{meta['coeff_perdita_MT']*100:.1f}% MT."
)


# ------------------------------------------------------------------
# SEZIONE 1 — Confronto Generale
# ------------------------------------------------------------------
st.header("1️⃣ Confronto generale")

st.markdown(
    """
<div class="desc-box">
Confronto a colpo d'occhio fra la <b>materia prima</b> riconosciuta in Convenzione
e il <b>benchmark</b> calcolato come <b>media delle 10 migliori offerte</b> di mercato indicizzate
(PUN/PSV + spread + quota fissa unitaria + perdite di rete).
Per l'<b>elettrico</b> è una media <i>equa</i> delle 4 fasce di potenza (BT≤3 kW, BT 4,5–40 kW, BT&gt;40 kW, MT);
per il <b>gas</b> è una media ponderata sui consumi delle 4 tipologie d'uso.
</div>
""",
    unsafe_allow_html=True,
)

col_ele, col_gas = st.columns(2)


def bar_confronto(label_conv, val_conv, label_merc, val_merc, color_conv, color_merc,
                  titolo, unita):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[label_conv], y=[val_conv], name=label_conv,
        marker=dict(color=color_conv, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_conv:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK),
    ))
    fig.add_trace(go.Bar(
        x=[label_merc], y=[val_merc], name=label_merc,
        marker=dict(color=color_merc, line=dict(color="#FFFFFF", width=2)),
        text=[f"<b>{val_merc:.2f}</b>"], textposition="outside",
        textfont=dict(size=15, color=C_TEXT_DARK),
    ))
    delta = val_merc - val_conv
    delta_pct = (delta / val_conv * 100) if val_conv else 0
    fig.update_layout(
        title=dict(text=titolo, font=dict(size=16, color=C_TEXT_DARK)),
        showlegend=False, height=380,
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        yaxis=dict(title=unita, gridcolor="#E5E7EB", zerolinecolor="#E5E7EB"),
        xaxis=dict(tickfont=dict(size=11)),
        margin=dict(t=70, b=80, l=50, r=30),
        annotations=[dict(
            x=0.5, y=1.13, xref="paper", yref="paper",
            text=(f"<span style='color:{'#B4495C' if delta > 0 else '#2F855A'};font-weight:600;'>"
                  f"Δ {delta:+.2f} {unita} ({delta_pct:+.1f}%)</span>"),
            showarrow=False, font=dict(size=13),
        )],
    )
    return fig


with col_ele:
    fig_e = bar_confronto(
        LABEL_CONV_ELE, ele_row["MP_convenzione"],
        LABEL_MERC_ELE, ele_row["benchmark_mercato"],
        C_CONV_ELE, C_MERC_ELE,
        f"{ICON_ELE} Elettrico — €/MWh", "€/MWh",
    )
    st.plotly_chart(fig_e, use_container_width=True)

with col_gas:
    fig_g = bar_confronto(
        LABEL_CONV_GAS, gas_row["MP_convenzione"],
        LABEL_MERC_GAS, gas_row["benchmark_mercato"],
        C_CONV_GAS, C_MERC_GAS,
        f"{ICON_GAS} Gas — c€/Smc", "c€/Smc",
    )
    st.plotly_chart(fig_g, use_container_width=True)


# ------------------------------------------------------------------
# SEZIONE 2 — Per fascia di potenza ELE
# ------------------------------------------------------------------
st.header(f"2️⃣ {ICON_ELE} Per fascia di potenza (Elettrico)")

st.markdown(
    """
<div class="desc-box">
Dettaglio per <b>fascia di potenza impegnata</b>: ogni colonna confronta la materia prima
della Convenzione MMPOWER (uguale per tutte le fasce: <b>Generazione + Perdite di rete</b>)
con la media delle <b>10 migliori offerte di mercato</b> ricostruite per quella fascia
(spread + quota fissa unitaria diluita sul consumo medio della fascia +
perdite di rete del 10%, ridotte a 3,8% per la MT).
</div>
""",
    unsafe_allow_html=True,
)

df_ele = df_conf[df_conf["commodity"] == "ELE"].sort_values("tipologia").reset_index(drop=True)
fasce = df_ele["tipologia"].tolist()
fascia_sel = st.selectbox("Filtra fascia di potenza:", ["Tutte"] + fasce, key="filtro_ele")
df_ele_v = df_ele if fascia_sel == "Tutte" else df_ele[df_ele["tipologia"] == fascia_sel]

fig_ele_tip = go.Figure()
fig_ele_tip.add_trace(go.Bar(
    name=LABEL_CONV_ELE,
    x=df_ele_v["tipologia"], y=df_ele_v["materia_prima_conv"],
    marker=dict(color=C_CONV_ELE, line=dict(color="#FFFFFF", width=1.5)),
    text=[f"<b>{v:.2f}</b>" for v in df_ele_v["materia_prima_conv"]],
    textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
))
fig_ele_tip.add_trace(go.Bar(
    name=LABEL_MERC_ELE,
    x=df_ele_v["tipologia"], y=df_ele_v["benchmark_mercato"],
    marker=dict(color=C_MERC_ELE, line=dict(color="#FFFFFF", width=1.5)),
    text=[f"<b>{v:.2f}</b>" for v in df_ele_v["benchmark_mercato"]],
    textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
))
fig_ele_tip.update_layout(
    barmode="group", height=460,
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    yaxis=dict(title="€/MWh", gridcolor="#E5E7EB"),
    xaxis=dict(title=""), bargap=0.25, bargroupgap=0.08,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    margin=dict(t=70, b=60, l=50, r=30),
)
st.plotly_chart(fig_ele_tip, use_container_width=True)


# ------------------------------------------------------------------
# SEZIONE 3 — Per tipologia d'uso GAS
# ------------------------------------------------------------------
st.markdown("<h2 class='gas-section'>3️⃣ 🔥 Per tipologia d'uso (Gas)</h2>",
            unsafe_allow_html=True)

st.markdown(
    """
<div class="desc-box gas">
Dettaglio per <b>tipologia d'uso del gas</b>: confronto fra materia prima della Convenzione
MMGAS (calcolata sui consumi reali del mese) e media delle <b>10 migliori offerte di mercato</b>
indicizzate sul PSV con spread e quota fissa unitaria.
</div>
""",
    unsafe_allow_html=True,
)

df_gas = df_conf[df_conf["commodity"] == "GAS"].reset_index(drop=True)
usi = df_gas["tipologia"].tolist()
uso_sel = st.selectbox("Filtra tipologia d'uso gas:", ["Tutte"] + usi, key="filtro_gas")
df_gas_v = df_gas if uso_sel == "Tutte" else df_gas[df_gas["tipologia"] == uso_sel]

fig_gas_tip = go.Figure()
fig_gas_tip.add_trace(go.Bar(
    name=LABEL_CONV_GAS,
    x=df_gas_v["tipologia"], y=df_gas_v["materia_prima_conv"],
    marker=dict(color=C_CONV_GAS, line=dict(color="#FFFFFF", width=1.5)),
    text=[f"<b>{v:.2f}</b>" for v in df_gas_v["materia_prima_conv"]],
    textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
))
fig_gas_tip.add_trace(go.Bar(
    name=LABEL_MERC_GAS,
    x=df_gas_v["tipologia"], y=df_gas_v["benchmark_mercato"],
    marker=dict(color=C_MERC_GAS, line=dict(color="#FFFFFF", width=1.5)),
    text=[f"<b>{v:.2f}</b>" for v in df_gas_v["benchmark_mercato"]],
    textposition="outside", textfont=dict(size=12, color=C_TEXT_DARK),
))
fig_gas_tip.update_layout(
    barmode="group", height=460,
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    yaxis=dict(title="c€/Smc", gridcolor="#E5E7EB"),
    xaxis=dict(title=""), bargap=0.25, bargroupgap=0.08,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    margin=dict(t=70, b=60, l=50, r=30),
)
st.plotly_chart(fig_gas_tip, use_container_width=True)


# ------------------------------------------------------------------
# SEZIONE 4 — Sensitivity ai consumi
# ------------------------------------------------------------------
st.header("4️⃣ 🎚️ Sensitivity sul livello di consumo")

st.markdown(
    """
<div class="desc-box">
La <b>quota fissa</b> dell'offerta di mercato (€/anno per utenza) viene diluita sul
consumo: più kWh/Smc consumi, meno pesa per unità di energia. Lo slider mostra come
cambia il benchmark al variare del livello di consumo (×0,25 fino a ×4 rispetto al
consumo reale di marzo 2026).
</div>
""",
    unsafe_allow_html=True,
)

fattori = sens["fattori"]
fatt_idx = st.slider(
    "Moltiplicatore consumo (1× = consumo reale marzo 2026)",
    min_value=0, max_value=len(fattori) - 1, value=fattori.index(1.0),
    format="", key="slider_consumo",
)
fatt_val = fattori[fatt_idx]
st.caption(f"Fattore selezionato: **{fatt_val}×**")

merc_ele_at = sens["ELE"][fatt_idx]
merc_gas_at = sens["GAS"][fatt_idx]

c1, c2 = st.columns(2)
with c1:
    fig_s_e = bar_confronto(
        LABEL_CONV_ELE, ele_row["MP_convenzione"],
        LABEL_MERC_ELE, merc_ele_at,
        C_CONV_ELE, C_MERC_ELE,
        f"{ICON_ELE} Elettrico a consumo {fatt_val}×", "€/MWh",
    )
    st.plotly_chart(fig_s_e, use_container_width=True)
with c2:
    fig_s_g = bar_confronto(
        LABEL_CONV_GAS, gas_row["MP_convenzione"],
        LABEL_MERC_GAS, merc_gas_at,
        C_CONV_GAS, C_MERC_GAS,
        f"{ICON_GAS} Gas a consumo {fatt_val}×", "c€/Smc",
    )
    st.plotly_chart(fig_s_g, use_container_width=True)


# ------------------------------------------------------------------
# SEZIONE 5 — Top 10 offerte attive
# ------------------------------------------------------------------
st.header("5️⃣ 🏆 Top 10 Offerte attive sul Mercato (per tipologia)")

st.markdown(
    """
<div class="desc-box">
Le 10 offerte più convenienti calcolate per ciascuna fascia di potenza (ELE) o
tipologia d'uso (GAS), già normalizzate sul consumo medio reale della categoria.
La media di questi 10 prezzi è il <b>benchmark</b> usato nei grafici precedenti.
</div>
""",
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs([f"{ICON_ELE} Elettrico", f"{ICON_GAS} Gas"])

with tab1:
    fasce_top = df_top[df_top["commodity"] == "ELE"]["tipologia"].unique()
    for f in sorted(fasce_top):
        with st.expander(f"⚡ {f}", expanded=False):
            sub = df_top[(df_top["commodity"] == "ELE") & (df_top["tipologia"] == f)] \
                    .reset_index(drop=True)
            sub.index = sub.index + 1
            sub = sub.rename(columns={"prezzo": "€/MWh", "offerta": "Offerta", "fonte": "Fonte"})
            st.dataframe(sub[["Fonte", "Offerta", "€/MWh"]], use_container_width=True)

with tab2:
    usi_top = df_top[df_top["commodity"] == "GAS"]["tipologia"].unique()
    for u in sorted(usi_top):
        with st.expander(f"🔥 {u}", expanded=False):
            sub = df_top[(df_top["commodity"] == "GAS") & (df_top["tipologia"] == u)] \
                    .reset_index(drop=True)
            sub.index = sub.index + 1
            sub = sub.rename(columns={"prezzo": "c€/Smc", "offerta": "Offerta", "fonte": "Fonte"})
            st.dataframe(sub[["Fonte", "Offerta", "c€/Smc"]], use_container_width=True)


# ------------------------------------------------------------------
# FOOTER — Metodologia + Fornitori
# ------------------------------------------------------------------
st.header("📚 Metodologia & fornitori monitorati")

st.markdown(
    f"""
<div class="footer-block">

<h4>🔬 Come è costruito il benchmark</h4>

<ol>
<li><b>Convenzione MMPOWER (ELE)</b> — Materia prima = <b>Generazione + Perdite di rete</b>
    estratte dal foglio <i>Report Costi</i> di UI Torino (mese {meta['mese_riferimento']}):
    {meta['generazione_conv_ele_eur_MWh']:.2f} + {meta['perdite_conv_ele_eur_MWh']:.2f}
    = <b>{meta['generazione_conv_ele_eur_MWh'] + meta['perdite_conv_ele_eur_MWh']:.2f} €/MWh</b>.
    Valore unico applicato a tutte le 4 fasce di potenza.</li>

<li><b>Convenzione MMGAS</b> — Materia prima per tipologia d'uso, calcolata dal foglio
    <i>Dettaglio</i> di MMGAS (importo "materia prima" / consumo Smc × 100 = c€/Smc).</li>

<li><b>Mercato</b> — Per ogni offerta indicizzata: prezzo ricostruito come<br>
    <code>(PUN o PSV) + spread + quota_fissa_annua / 12 × n_utenze / consumo_mese</code><br>
    a cui si aggiungono le <b>perdite di rete</b> per l'elettrico:
    <code>(PUN + spread) × {meta['coeff_perdita_BT']*100:.0f}%</code> per BT,
    <code>× {meta['coeff_perdita_MT']*100:.1f}%</code> per MT.</li>

<li><b>Top 10 + media</b> — Per ciascuna fascia/uso si selezionano le 10 offerte più convenienti
    fra le {meta['n_offerte_totali']} totali raccolte, se ne calcola la media: questo è il "Mercato".</li>

<li><b>Confronto generale</b> — ELE: media semplice delle 4 fasce (peso BT/MT pari).
    GAS: media ponderata sui consumi delle 4 tipologie d'uso.</li>
</ol>

<h4>🏢 Fornitori monitorati</h4>
<p style="color:#6B7280; font-size:.92rem;">
12 fornitori italiani (CVA esclusa, opera solo in Val d'Aosta).
Le offerte vengono estratte sia direttamente dai siti dei fornitori, sia dai principali
portali comparatori.
</p>
""",
    unsafe_allow_html=True,
)

st.markdown("<div>", unsafe_allow_html=True)
forn = D["fornitori"]
for f in forn:
    st.markdown(
        f'<span class="forn-pill"><a href="{f["url"]}" target="_blank">{f["nome"]} ↗</a></span>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    """
<h4 style="margin-top:1.4rem;">🔎 Portali comparatori</h4>
""",
    unsafe_allow_html=True,
)
for p in D["portali"]:
    st.markdown(
        f'<span class="forn-pill"><a href="{p["url"]}" target="_blank">{p["nome"]} ↗</a></span>',
        unsafe_allow_html=True,
    )

st.markdown(
    """
<p style="margin-top:1.2rem; color:#6B7280; font-size:.88rem;">
Fonte prezzi all'ingrosso: <a href="https://www.arera.it/dati-e-statistiche/dettaglio/prezzi-finali-energia-elettrica-per-i-consumatori-domestici-tipo" target="_blank">ARERA — PLACET</a>
(PUN monorario per l'elettrico, PSV per il gas).
</p>

</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<hr style="margin-top:2rem;">
<p style="text-align:center; color:#9CA3AF; font-size:.85rem;">
UI Torino · Gas &amp; Power · Dashboard generata automaticamente dal notebook
<code>Benchmark Confronto.ipynb</code> · mese {meta['mese_riferimento']}
</p>
""",
    unsafe_allow_html=True,
)
