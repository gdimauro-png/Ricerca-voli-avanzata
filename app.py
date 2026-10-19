import streamlit as st
import pandas as pd
import requests
import datetime, calendar, time

st.set_page_config(page_title="Radar Voli Free", page_icon="✈️", layout="wide")
st.title("⚡ Radar Voli Diretto (Server Aperto)")
st.markdown("Ricerca settimanale gratuita. Nessuna chiave API, nessuna installazione complessa, 100% stabile.")

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
    "BER (Berlino)", "FRA (Francoforte)", "MUC (Monaco)",
    "PRG (Praga)", "BUD (Budapest)", "VIE (Vienna)", "WAW (Varsavia)", 
    "OTP (Bucarest)", "SOF (Sofia)",
    "ATH (Atene)", "MLA (Malta)", "TFS (Tenerife)", "PMI (Palma di Maiorca)"
]

COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling"]

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

if st.button("🚀 Avvia Scansione Sicura", type="primary", use_container_width=True):
    if not lista_dest: st.error("Seleziona una destinazione."); st.stop()
        
    pax_api = min(passeggeri_reali, 9)
    progress_bar = st.progress(0)
    status = st.empty()
    dati = []
    
    totale_chiamate = len(lista_dest) * len(giorni_partenza)
    chiamata_attuale = 0
    
    # Intestazioni finte per evitare blocchi dai server gratuiti
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }

    for dest in lista_dest:
        for giorno in giorni_partenza:
            chiamata_attuale += 1
            status.text(f"Ricerca {chiamata_attuale}/{totale_chiamate} | {codice_origine} ➔ {dest}...")
            
            data_andata_str = datetime.date(anno, mese, giorno).strftime("%Y-%m-%d")
            data_ritorno_str = (datetime.date(anno, mese, giorno) + datetime.timedelta(days=giorni_viaggio - 1)).strftime("%Y-%m-%d")
            
            # API Aperta che non richiede registrazione per i voli in Europa
            url = f"https://api.skypicker.com/flights?flyFrom={codice_origine}&to={dest}&dateFrom={datetime.date(anno, mese, giorno).strftime('%d/%m/%Y')}&dateTo={datetime.date(anno, mese, giorno).strftime('%d/%m/%Y')}&returnFrom={(datetime.date(anno, mese, giorno) + datetime.timedelta(days=giorni_viaggio - 1)).strftime('%d/%m/%Y')}&returnTo={(datetime.date(anno, mese, giorno) + datetime.timedelta(days=giorni_viaggio - 1)).strftime('%d/%m/%Y')}&adults={pax_api}&directFlights=1&curr=EUR"
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    voli = response.json().get("data", [])
                    
                    for volo in voli:
                        # Estraiamo le compagnie del volo (Skypicker usa una lista di codici come 'FR' per Ryanair)
                        compagnie = volo.get("airlines", [])
                        
                        # Filtro manuale (FR=Ryanair, W6=Wizz, U2=EasyJet, VY=Vueling)
                        if any(c in ["FR", "W6", "W4", "U2", "VY"] for c in compagnie):
                            prz_totale = volo.get("price", 0)
                            prz_singolo = prz_totale / pax_api
                            
                            # Trasformo l'orario da timestamp a ore e minuti
                            dep_a = datetime.datetime.fromtimestamp(volo["route"][0]["dTime"]).strftime('%H:%M')
                            dep_r = datetime.datetime.fromtimestamp(volo["route"][1]["dTime"]).strftime('%H:%M')
                            
                            comp_nome = " / ".join(compagnie).replace("FR", "Ryanair").replace("W6", "Wizz Air").replace("U2", "EasyJet").replace("VY", "Vueling").replace("W4", "Wizz Air")
                            
                            dati.append({
                                "Andata": data_andata_str,
                                "Ritorno": data_ritorno_str,
                                "Tratta": f"{codice_origine} ⇄ {dest}",
                                "Vettori": comp_nome,
                                "Orario Andata": dep_a,
                                "Orario Ritorno": dep_r,
                                "1 Pax (A/R)": round(prz_singolo, 2),
                                f"Gruppo ({passeggeri_reali} pax)": round(prz_singolo * passeggeri_reali, 2)
                            })
                            break # Prende solo il più economico del giorno
            except Exception:
                pass
                
            progress_bar.progress(chiamata_attuale / totale_chiamate)
            time.sleep(1) # Pausa gentile
            
    status.text("✅ Scansione completata!")
    
    if dati:
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="1 Pax (A/R)")
        df_csv = df.copy()
        
        df["1 Pax (A/R)"] = df["1 Pax (A/R)"].apply(lambda x: f"{x} €")
        df[f"Gruppo ({passeggeri_reali} pax)"] = df[f"Gruppo ({passeggeri_reali} pax)"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Scarica CSV", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="voli_stabili.csv", mime="text/csv")
    else:
        st.warning("Nessuna combinazione diretta Low-Cost trovata per queste date.")
        
