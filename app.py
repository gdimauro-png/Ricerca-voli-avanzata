import streamlit as st
import pandas as pd
import datetime, calendar, time
from serpapi import GoogleSearch

st.set_page_config(page_title="Voli Gruppi Italia-Europa", page_icon="🌍", layout="wide")

st.title("🌍 Radar Voli: Grandi Gruppi & Multi-Destinazione")
st.markdown("Combina macro-aree italiane e destinazioni europee. Ideale per organizzare viaggi di gruppo aziendali o vacanze numerose.")

# --- DATI E MACRO-AREE ---
MACRO_AREE = {
    "NORD Italia (MXP, BGY, VCE, TRN, BLQ, ecc.)": "BGY,MXP,LIN,TRN,VCE,TSF,VRN,BLQ,GOA",
    "CENTRO Italia (FCO, CIA, PSA, FLR, ecc.)": "FCO,CIA,PSA,FLR,AOI,PEG",
    "SUD Italia (NAP, BRI, BDS, ecc.)": "NAP,BRI,BDS,SUF,REG",
    "ISOLE (CTA, PMO, CAG, OLB, ecc.)": "CTA,PMO,TPS,CAG,OLB,AHO"
}

TOP_EUROPA = [
    "BCN (Barcellona)", "MAD (Madrid)", "STN (Londra)", "ORY (Parigi)", 
    "BER (Berlino)", "AMS (Amsterdam)", "PRG (Praga)", "BUD (Budapest)", 
    "VIE (Vienna)", "LIS (Lisbona)", "ATH (Atene)", "DUB (Dublino)", 
    "CRL (Bruxelles)", "MLA (Malta)", "TFS (Tenerife)", "IBZ (Ibiza)"
]

COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling", "Buzz", "Malta"]

# --- BARRA LATERALE (MENU) ---
st.sidebar.header("⚙️ 1. Credenziali")
api_key = st.sidebar.text_input("🔑 API Key SerpApi", type="password", help="Indispensabile per accedere a Google Flights.")

st.sidebar.header("🗺️ 2. Tratte")
origini = st.sidebar.multiselect("🛫 Da dove parti? (Macro-aree)", list(MACRO_AREE.keys()), default=[list(MACRO_AREE.keys())[0]])
dest_selezionate = st.sidebar.multiselect("🛬 Seleziona Hub Europei", TOP_EUROPA, default=["BCN (Barcellona)"])
dest_custom = st.sidebar.text_input("...oppure scrivi codici IATA liberi (es. LHR, PMI separati da virgola)")

st.sidebar.header("📅 3. Periodo")
anno = st.sidebar.selectbox("Anno", [2026, 2027])
mese = st.sidebar.selectbox("Mese", list(range(1, 13)), index=10)
giorni_viaggio = st.sidebar.slider("Durata Viaggio (giorni)", 2, 14, 5)

st.sidebar.header("👥 4. Dimensione Gruppo")
passeggeri_reali = st.sidebar.number_input("Numero totale dei partecipanti", min_value=1, max_value=150, value=15)

# --- MOTORE LOGICO ---
# Estrapola solo la sigla (es. "BCN") dalle destinazioni
lista_dest = [d.split(" ")[0] for d in dest_selezionate]
if dest_custom:
    lista_dest.extend([d.strip().upper() for d in dest_custom.split(",") if d.strip()])
lista_dest = list(set(lista_dest))

# Calcolo del costo API prima di partire
giorni_nel_mese = calendar.monthrange(anno, mese)[1]
giorni_da_testare = giorni_nel_mese - giorni_viaggio + 2
totale_chiamate = len(origini) * len(lista_dest) * giorni_da_testare

st.markdown("---")
st.info(f"💡 **SALVAVITA CONSUMI API:** Questa configurazione necessita di **{totale_chiamate} ricerche** contemporanee.")

if totale_chiamate > 100:
    st.warning("⚠️ **ATTENZIONE:** Il piano gratuito SerpApi supporta 100 ricerche/mese. Con questa mole di dati finirai i crediti in pochi secondi! Ti consiglio di ridurre le destinazioni selezionate o limitarti a una sola area d'Italia per volta.")

# --- AVVIO RICERCA ---
if st.button("🚀 Avvia Scansione Globale", type="primary", use_container_width=True):
    if not api_key:
        st.error("Inserisci la tua API Key nella barra laterale a sinistra!")
        st.stop()
    if not origini or not lista_dest:
        st.error("Seleziona almeno un'origine e una destinazione.")
        st.stop()
        
    pax_api = min(passeggeri_reali, 9) # Il motore "sonda" un blocco massimo di 9 persone
    
    progress_bar = st.progress(0)
    status = st.empty()
    dati = []
    chiamata_attuale = 0
    
    for origine_nome in origini:
        codici_origine = MACRO_AREE[origine_nome]
        for dest in lista_dest:
            for giorno in range(1, giorni_da_testare):
                chiamata_attuale += 1
                status.text(f"Ricerca {chiamata_attuale}/{totale_chiamate} | Esplorazione: {origine_nome.split(' ')[0]} ➔ {dest}...")
                
                data_andata = datetime.date(anno, mese, giorno)
                data_ritorno = data_andata + datetime.timedelta(days=giorni_viaggio - 1)
                
                params = {
                    "engine": "google_flights",
                    "departure_id": codici_origine,
                    "arrival_id": dest,
                    "outbound_date": data_andata.strftime("%Y-%m-%d"),
                    "return_date": data_ritorno.strftime("%Y-%m-%d"),
                    "type": 1,
                    "adults": pax_api,
                    "stops": 1,
                    "currency": "EUR",
                    "hl": "it",
                    "api_key": api_key
                }
                
                try:
                    res = GoogleSearch(params).get_dict()
                    tutti = res.get("best_flights", []) + res.get("other_flights", [])
                    for opz in tutti:
                        if "flights" in opz and opz["flights"]:
                            andata = opz["flights"][0]
                            comp = andata.get("airline", "")
                            prz = opz.get("price", 0)
                            
                            if prz > 0 and any(t.lower() in comp.lower() for t in COMPAGNIE_TARGET):
                                prz_singolo = prz / pax_api # Prezzo per 1 persona
                                
                                dati.append({
                                    "Date": f"{data_andata.strftime('%d/%m')} - {data_ritorno.strftime('%d/%m')}",
                                    "Da": andata["departure_airport"]["id"],
                                    "Verso": dest,
                                    "Vettore": comp,
                                    "Costo 1 Pax": round(prz_singolo, 2),
                                    f"Preventivo Gruppo ({passeggeri_reali} pax)": round(prz_singolo * passeggeri_reali, 2)
                                })
                except:
                    pass
                
                # Avanzamento e micro-pausa anti-blocco
                progress_bar.progress(chiamata_attuale / totale_chiamate)
                time.sleep(1.2)
                
    status.text("✅ Scansione dell'Europa completata!")
    
    if dati:
        # Formattazione per la visuale
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="Costo 1 Pax")
        df_csv = df.copy() # Copia pura per il download Excel
        
        df["Costo 1 Pax"] = df["Costo 1 Pax"].apply(lambda x: f"{x} €")
        df[f"Preventivo Gruppo ({passeggeri_reali} pax)"] = df[f"Preventivo Gruppo ({passeggeri_reali} pax)"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "📥 Scarica il report in CSV", 
            data=df_csv.to_csv(index=False).encode('utf-8'), 
            file_name="voli_gruppi_europa.csv", 
            mime="text/csv"
        )
    else:
        st.warning("Nessun volo low-cost diretto trovato con le impostazioni richieste.")
