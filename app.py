import streamlit as st
import pandas as pd
import datetime, calendar, time
from fast_flights import get_flights, FlightData, Passenger

st.set_page_config(page_title="Radar Voli Free", page_icon="✈️", layout="wide")
st.title("⚡ Radar Voli Illimitato (No API Key)")
st.markdown("Ricerca settimanale gratuita usando i server open-source. **Nessun limite mensile.**")

# --- DATABASE ---
MACRO_AREE = {
    "BGY (Milano Bergamo)": "BGY", "MXP (Milano Malpensa)": "MXP",
    "FCO (Roma Fiumicino)": "FCO", "CIA (Roma Ciampino)": "CIA",
    "NAP (Napoli)": "NAP", "BLQ (Bologna)": "BLQ",
    "VCE (Venezia)": "VCE", "TSF (Treviso)": "TSF",
    "PSA (Pisa)": "PSA", "BRI (Bari)": "BRI",
    "CTA (Catania)": "CTA", "PMO (Palermo)": "PMO"
}

TOP_EUROPA = [
    "BCN (Barcellona)", "MAD (Madrid)", "ALC (Alicante)", "AGP (Malaga)", 
    "VLC (Valencia)", "LIS (Lisbona)", "OPO (Porto)",
    "STN (Londra Stansted)", "LGW (Londra Gatwick)", "ORY (Parigi Orly)", 
    "BVA (Parigi Beauvais)", "AMS (Amsterdam)", "CRL (Bruxelles Charleroi)", 
    "BRU (Bruxelles Zaventem)", "BER (Berlino)", "FRA (Francoforte)", "MUC (Monaco)",
    "PRG (Praga)", "BUD (Budapest)", "VIE (Vienna)", "WAW (Varsavia)", 
    "OTP (Bucarest)", "SOF (Sofia)",
    "ATH (Atene)", "MLA (Malta)", "TFS (Tenerife)", "LPA (Gran Canaria)", 
    "PMI (Palma di Maiorca)", "IBZ (Ibiza)"
]

COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling", "Buzz", "Malta"]

# --- MENU LATERALE ---
st.sidebar.header("🗺️ 1. Tratte")
partenza_scelta = st.sidebar.selectbox("🛫 Aeroporto di Partenza", list(MACRO_AREE.keys()))
dest_selezionate = st.sidebar.multiselect("🛬 Scegli Aeroporti Europei", TOP_EUROPA, default=["BCN (Barcellona)"])

st.sidebar.header("📅 2. Periodo (Settimane)")
anno = st.sidebar.selectbox("Anno", [2026, 2027])
mese = st.sidebar.selectbox("Mese", list(range(1, 13)), index=10)

fascia_mese = st.sidebar.radio(
    "Fascia mensile",
    ("Prima Settimana (1-7)", "Seconda Settimana (8-14)", "Terza Settimana (15-21)", "Quarta Settimana (22+)")
)
giorni_viaggio = st.sidebar.slider("Durata Viaggio (giorni)", 2, 14, 5)
passeggeri_reali = st.sidebar.number_input("Partecipanti totali", min_value=1, max_value=200, value=25)

# --- CALCOLO DATE ---
giorni_nel_mese = calendar.monthrange(anno, mese)[1]
if fascia_mese == "Prima Settimana (1-7)": start_day, end_day = 1, 7
elif fascia_mese == "Seconda Settimana (8-14)": start_day, end_day = 8, 14
elif fascia_mese == "Terza Settimana (15-21)": start_day, end_day = 15, 21
else: start_day, end_day = 22, giorni_nel_mese - giorni_viaggio + 1

giorni_partenza = list(range(start_day, end_day + 1))
lista_dest = [d.split(" ")[0] for d in dest_selezionate]
codice_origine = MACRO_AREE[partenza_scelta]

st.markdown("---")

if st.button("🚀 Avvia Scansione Gratuita", type="primary", use_container_width=True):
    if not lista_dest: st.error("Seleziona una destinazione."); st.stop()
        
    pax_api = min(passeggeri_reali, 9)
    progress_bar = st.progress(0)
    status = st.empty()
    dati = []
    
    totale_chiamate = len(lista_dest) * len(giorni_partenza)
    chiamata_attuale = 0
    
    for dest in lista_dest:
        for giorno in giorni_partenza:
            chiamata_attuale += 1
            status.text(f"Scansione {chiamata_attuale}/{totale_chiamate} | {codice_origine} ➔ {dest}...")
            
            data_a = datetime.date(anno, mese, giorno).strftime("%Y-%m-%d")
            data_r = (datetime.date(anno, mese, giorno) + datetime.timedelta(days=giorni_viaggio - 1)).strftime("%Y-%m-%d")
            
            try:
                # Nuova chiamata corretta per la libreria fast-flights
                risultato = get_flights(
                    flight_data=[FlightData(date=data_a, from_airport=codice_origine, to_airport=dest),
                                 FlightData(date=data_r, from_airport=dest, to_airport=codice_origine)],
                    passengers=Passenger(adults=pax_api, children=0, infants_in_seat=0, infants_on_lap=0)
                )
                
                # Se la libreria restituisce dei voli
                if risultato and risultato.flights:
                    for volo in risultato.flights:
                        compagnie_volo = volo.name
                        
                        # Filtriamo per verificare che siano Low-Cost
                        if any(t.lower() in compagnie_volo.lower() for t in COMPAGNIE_TARGET):
                            prz_singolo = volo.price / pax_api
                            
                            dati.append({
                                "Data Andata": data_a,
                                "Data Ritorno": data_r,
                                "Tratta": f"{codice_origine} ⇄ {dest}",
                                "Vettori": compagnie_volo,
                                "Orari A/R": volo.departure + " - " + volo.arrival,
                                "1 Pax (A/R)": round(prz_singolo, 2),
                                f"Gruppo ({passeggeri_reali} pax)": round(prz_singolo * passeggeri_reali, 2)
                            })
                            # Trovata l'opzione più economica per questo giorno, passa al giorno successivo
                            break 
            except Exception as e:
                pass
            
            progress_bar.progress(chiamata_attuale / totale_chiamate)
            time.sleep(2) # Pausa per non farsi bloccare
            
    status.text("✅ Scansione gratuita completata!")
    
    if dati:
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="1 Pax (A/R)")
        df_csv = df.copy()
        
        df["1 Pax (A/R)"] = df["1 Pax (A/R)"].apply(lambda x: f"{x} €")
        df[f"Gruppo ({passeggeri_reali} pax)"] = df[f"Gruppo ({passeggeri_reali} pax)"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Scarica CSV", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="voli_free.csv", mime="text/csv")
    else:
        st.warning("Nessuna combinazione diretta trovata o ritardo dei server.")
        st.warning("Nessuna combinazione diretta trovata o i server di Google hanno momentaneamente ritardato la risposta.")
        
