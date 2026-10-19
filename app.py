import streamlit as st
import pandas as pd
import datetime, calendar, time
from serpapi import GoogleSearch

# Configurazione della pagina
st.set_page_config(page_title="Scanner Voli Low-Cost", page_icon="✈️")

st.title("✈️ Scanner Voli Low-Cost Diretti")
st.markdown("Cerca le migliori combinazioni Andata/Ritorno per intero mese su **Ryanair, Wizz Air, EasyJet e Vueling** da tutta Italia.")

# Menu laterale per i parametri
st.sidebar.header("⚙️ Parametri di Ricerca")
api_key = st.sidebar.text_input("🔑 La tua API Key (SerpApi)", type="password", help="Inserisci la chiave presa da serpapi.com")
destinazione = st.sidebar.text_input("📍 Destinazione (Es: BCN, MAD, STN)", "BCN").upper()
anno = st.sidebar.selectbox("📅 Anno", [2026, 2027])
mese = st.sidebar.selectbox("🗓️ Mese", list(range(1, 13)), index=10) # Default Novembre
giorni_viaggio = st.sidebar.slider("⏳ Durata Viaggio (giorni)", min_value=2, max_value=14, value=5)
passeggeri = st.sidebar.slider("👥 Numero Passeggeri", min_value=1, max_value=9, value=9)

AEROPORTI_ITALIANI = "BGY,MXP,FCO,NAP,BLQ,VCE,PSA"
COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling", "Buzz", "Malta"]

# Bottone per avviare
if st.sidebar.button("🚀 Avvia Ricerca", use_container_width=True):
    if not api_key:
        st.error("⚠️ Inserisci la tua API Key di SerpApi nel menu laterale per iniziare!")
        st.stop()
        
    st.info(f"Ricerca in corso per voli di {giorni_viaggio} giorni verso {destinazione} nel mese {mese}/{anno}...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    giorni_nel_mese = calendar.monthrange(anno, mese)[1]
    giorni_da_testare = giorni_nel_mese - giorni_viaggio + 2
    dati_estratti = []

    # Ciclo di ricerca
    for index, giorno in enumerate(range(1, giorni_da_testare)):
        data_andata = datetime.date(anno, mese, giorno)
        data_ritorno = data_andata + datetime.timedelta(days=giorni_viaggio - 1)
        str_andata, str_ritorno = data_andata.strftime("%Y-%m-%d"), data_ritorno.strftime("%Y-%m-%d")
        
        status_text.text(f"Controllo date: {str_andata} ➔ {str_ritorno}...")
        
        params = {
            "engine": "google_flights",
            "departure_id": AEROPORTI_ITALIANI,
            "arrival_id": destinazione,
            "outbound_date": str_andata,
            "return_date": str_ritorno,
            "type": 1,
            "adults": passeggeri,
            "stops": 1,
            "currency": "EUR",
            "hl": "it",
            "api_key": api_key
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            tutti = results.get("best_flights", []) + results.get("other_flights", [])
            
            for opzione in tutti:
                if "flights" in opzione and len(opzione["flights"]) > 0:
                    andata = opzione["flights"][0]
                    vettore = andata.get("airline", "")
                    if any(t.lower() in vettore.lower() for t in COMPAGNIE_TARGET):
                        prezzo = opzione.get("price", 0)
                        if prezzo > 0:
                            dati_estratti.append({
                                "Date Viaggio": f"{str_andata} ➔ {str_ritorno}",
                                "Da": andata["departure_airport"]["id"],
                                "Compagnia": vettore,
                                f"Prezzo Totale ({passeggeri} pax)": prezzo,
                                "Prezzo Singolo A/R": round(prezzo / passeggeri, 2)
                            })
        except Exception as e:
            pass # Ignora gli errori tecnici di Google per quella data
        
        # Aggiorna la barra di caricamento
        progress_bar.progress((index + 1) / (giorni_da_testare - 1))
        time.sleep(1.2) # Pausa per non bloccarsi
        
    status_text.text("✅ Scansione completata!")
    
    # Mostrare i risultati
    if dati_estratti:
        df = pd.DataFrame(dati_estratti).drop_duplicates().sort_values(by="Prezzo Singolo A/R")
        
        # Copia per il download (solo numeri puliti)
        df_csv = df.copy()
        
        # Formattazione per la visualizzazione a schermo
        df["Prezzo Singolo A/R"] = df["Prezzo Singolo A/R"].apply(lambda x: f"{x} €")
        df[f"Prezzo Totale ({passeggeri} pax)"] = df[f"Prezzo Totale ({passeggeri} pax)"].apply(lambda x: f"{x} €")
        
        st.success(f"Trovate {len(df)} combinazioni valide!")
        st.dataframe(df, use_container_width=True) # Mostra la tabella bella
        
        # Tasto per scaricare in CSV
        csv = df_csv.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Scarica risultati completi (Excel/CSV)",
            data=csv,
            file_name=f"voli_{destinazione}_{mese}_{anno}.csv",
            mime="text/csv",
        )
    else:
        st.warning("Nessuna tariffa low-cost trovata per queste impostazioni.")
