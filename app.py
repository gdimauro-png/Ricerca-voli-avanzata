import streamlit as st
import pandas as pd
import datetime, calendar, time
from serpapi import GoogleSearch

st.set_page_config(page_title="Voli Gruppi", page_icon="✈️", layout="wide")
st.title("⚡ Radar Voli Veloce: 100% Orari Garantiti")
st.markdown("Divisione per settimane con estrazione forzata del volo di ritorno.")

# --- DATABASE ---
MACRO_AREE = {
    "NORD (MXP, BGY, VCE, TRN, BLQ...)": "BGY,MXP,LIN,TRN,VCE,TSF,VRN,BLQ,GOA",
    "CENTRO (FCO, CIA, PSA, FLR...)": "FCO,CIA,PSA,FLR,AOI,PEG",
    "SUD (NAP, BRI, BDS, SUF...)": "NAP,BRI,BDS,SUF,REG",
    "ISOLE (CTA, PMO, CAG, OLB...)": "CTA,PMO,TPS,CAG,OLB,AHO"
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
    "PMI (Palma di Maiorca)", "IBZ (Ibiza)", "JMK (Mykonos)", "JTR (Santorini)"
]

COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling", "Buzz", "Malta"]

# --- MENU LATERALE ---
st.sidebar.header("⚙️ 1. Credenziali")
api_key = st.sidebar.text_input("🔑 API Key SerpApi", type="password")

st.sidebar.header("🗺️ 2. Tratte")
origini = st.sidebar.multiselect("🛫 Da dove parti?", list(MACRO_AREE.keys()), default=[list(MACRO_AREE.keys())[0]])
dest_selezionate = st.sidebar.multiselect("🛬 Scegli Aeroporti Europei", TOP_EUROPA, default=["BCN (Barcellona)"])
dest_custom = st.sidebar.text_input("...o digita Codici IATA (es. DUB)")

st.sidebar.header("📅 3. Periodo (Settimane)")
anno = st.sidebar.selectbox("Anno", [2026, 2027])
mese = st.sidebar.selectbox("Mese", list(range(1, 13)), index=10)

fascia_mese = st.sidebar.radio(
    "In che periodo del mese vuoi partire?",
    ("Mese Intero", "Prima Settimana (1-7)", "Seconda Settimana (8-14)", "Terza Settimana (15-21)", "Quarta Settimana (22+)")
)
giorni_viaggio = st.sidebar.slider("Durata Viaggio (giorni)", 2, 14, 5)
passeggeri_reali = st.sidebar.number_input("Partecipanti totali", min_value=1, max_value=200, value=25)

# --- CALCOLO DATE ---
giorni_nel_mese = calendar.monthrange(anno, mese)[1]

if fascia_mese == "Prima Settimana (1-7)": start_day, end_day = 1, 7
elif fascia_mese == "Seconda Settimana (8-14)": start_day, end_day = 8, 14
elif fascia_mese == "Terza Settimana (15-21)": start_day, end_day = 15, 21
elif fascia_mese == "Quarta Settimana (22+)": start_day, end_day = 22, giorni_nel_mese - giorni_viaggio + 1
else: start_day, end_day = 1, giorni_nel_mese - giorni_viaggio + 1

giorni_partenza = list(range(start_day, end_day + 1))

lista_dest = [d.split(" ")[0] for d in dest_selezionate]
if dest_custom: lista_dest.extend([d.strip().upper() for d in dest_custom.split(",") if d.strip()])
lista_dest = list(set(lista_dest))

totale_chiamate_base = len(origini) * len(lista_dest) * len(giorni_partenza)
st.markdown("---")
st.info(f"Ricerca in corso. Potrebbe richiedere extra-chiamate automatiche per forzare i dettagli dei voli di ritorno.")

# --- FUNZIONE DI RICERCA SINGOLA (PER IL RITORNO) ---
def cerca_volo_singolo(da, verso, data, pax, chiave):
    params = {
        "engine": "google_flights", "departure_id": da, "arrival_id": verso,
        "outbound_date": data, "type": 2, "adults": pax, "stops": 1,
        "currency": "EUR", "hl": "it", "api_key": chiave
    }
    try:
        res = GoogleSearch(params).get_dict()
        tutti = res.get("best_flights", []) + res.get("other_flights", [])
        voli_trovati = []
        for opz in tutti:
            if "flights" in opz and opz["flights"]:
                volo = opz["flights"][0]
                comp = volo.get("airline", "")
                if any(t.lower() in comp.lower() for t in COMPAGNIE_TARGET):
                    prz = opz.get("price", 0)
                    orario = volo.get("departure_airport", {}).get("time", "N/D")
                    num_volo = volo.get("flight_number", "")
                    voli_trovati.append({"compagnia": comp, "orario": f"{orario} ({comp} {num_volo})", "prezzo": prz})
        if voli_trovati:
            # Ordina per prezzo e restituisce il più economico
            voli_trovati.sort(key=lambda x: x["prezzo"])
            return voli_trovati[0]
    except: pass
    return None

# --- ESECUZIONE ---
if st.button("🚀 Avvia Scansione", type="primary", use_container_width=True):
    if not api_key: st.error("Inserisci la chiave API."); st.stop()
    if not origini or not lista_dest: st.error("Seleziona origini e destinazioni."); st.stop()
        
    pax_api = min(passeggeri_reali, 9)
    progress_bar = st.progress(0)
    status = st.empty()
    dati = []
    chiamata_attuale = 0
    
    for origine_nome in origini:
        codici_origine = MACRO_AREE[origine_nome]
        for dest in lista_dest:
            for giorno in giorni_partenza:
                chiamata_attuale += 1
                status.text(f"Scansione Andata {chiamata_attuale}/{totale_chiamate_base} | {origine_nome.split(' ')[0]} ➔ {dest}...")
                
                data_andata_obj = datetime.date(anno, mese, giorno)
                data_ritorno_obj = data_andata_obj + datetime.timedelta(days=giorni_viaggio - 1)
                str_andata, str_ritorno = data_andata_obj.strftime("%Y-%m-%d"), data_ritorno_obj.strftime("%Y-%m-%d")
                
                # Cerco l'andata singola invece che l'A/R (per essere certo di avere tutti i dati puliti)
                andata_info = cerca_volo_singolo(codici_origine, dest, str_andata, pax_api, api_key)
                
                if andata_info:
                    status.text(f"Volo di Andata trovato! Forzo la ricerca per il Ritorno: {dest} ➔ {origine_nome.split(' ')[0]}...")
                    time.sleep(1) # Pausa di sicurezza per l'API
                    
                    # Interrogo il ritorno esattamente da quell'aeroporto specifico trovato all'andata
                    ritorno_info = cerca_volo_singolo(dest, codici_origine, str_ritorno, pax_api, api_key)
                    
                    if ritorno_info:
                        prezzo_totale = andata_info["prezzo"] + ritorno_info["prezzo"]
                        prz_singolo = prezzo_totale / pax_api
                        
                        dati.append({
                            "Data Andata": data_andata_obj.strftime("%d/%m/%y"),
                            "Data Ritorno": data_ritorno_obj.strftime("%d/%m/%y"),
                            "A / Da": dest,
                            "Andata": andata_info["orario"],
                            "Ritorno": ritorno_info["orario"],
                            "1 Pax": round(prz_singolo, 2),
                            f"Gruppo ({passeggeri_reali} pax)": round(prz_singolo * passeggeri_reali, 2)
                        })
                
                progress_bar.progress(chiamata_attuale / totale_chiamate_base)
                time.sleep(1)
                
    status.text("✅ Scansione completata!")
    
    if dati:
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="1 Pax")
        df_csv = df.copy()
        
        df["1 Pax"] = df["1 Pax"].apply(lambda x: f"{x} €")
        df[f"Gruppo ({passeggeri_reali} pax)"] = df[f"Gruppo ({passeggeri_reali} pax)"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Scarica CSV", data=df_csv.to_csv(index=False).encode('utf-8'), file_name="voli_dettagliati.csv", mime="text/csv")
    else:
        st.warning("Nessuna combinazione andata + ritorno diretta trovata.")
