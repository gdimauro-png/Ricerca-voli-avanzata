import streamlit as st
import pandas as pd
import datetime, calendar, time
from serpapi import GoogleSearch

st.set_page_config(page_title="Voli Gruppi Italia-Europa", page_icon="✈️", layout="wide")
st.title("⚡ Radar Voli Gruppi: Orari & Scali Precisi")
st.markdown("Tratte dirette con indicazione dello scalo italiano esatto di partenza e ritorno garantito sullo stesso aeroporto.")

# --- DATABASE MACRO-AREE ---
MACRO_AREE = {
    "NORD (BGY, MXP, LIN, VCE, TSF, VRN, BLQ, TRN, GOA)": "BGY,MXP,LIN,TRN,VCE,TSF,VRN,BLQ,GOA",
    "CENTRO (FCO, CIA, PSA, FLR, AOI, PEG)": "FCO,CIA,PSA,FLR,AOI,PEG",
    "SUD (NAP, BRI, BDS, SUF, REG)": "NAP,BRI,BDS,SUF,REG",
    "ISOLE (CTA, PMO, TPS, CAG, OLB, AHO)": "CTA,PMO,TPS,CAG,OLB,AHO"
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
origini = st.sidebar.multiselect("🛫 Da dove parti? (Macro-aree)", list(MACRO_AREE.keys()), default=[list(MACRO_AREE.keys())[0]])
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
st.info(f"💡 Il sistema ricercherà i voli di andata e bloccherà automaticamente il ritorno sullo stesso aeroporto italiano.")

# --- FUNZIONE DI RICERCA VOLO SINGOLO ---
def cerca_volo_singolo(da, verso, data, pax, chiave):
    params = {
        "engine": "google_flights", 
        "departure_id": da, 
        "arrival_id": verso,
        "outbound_date": data, 
        "type": 2, # Solo Andata
        "adults": pax, 
        "stops": 1,
        "currency": "EUR", 
        "hl": "it", 
        "api_key": chiave
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
                    dep_info = volo.get("departure_airport", {})
                    arr_info = volo.get("arrival_airport", {})
                    
                    orario = dep_info.get("time", "N/D")
                    num_volo = volo.get("flight_number", "")
                    scalo_dep = dep_info.get("id", da)
                    scalo_arr = arr_info.get("id", verso)
                    
                    voli_trovati.append({
                        "compagnia": comp,
                        "orario_dettaglio": f"{orario} ({comp} {num_volo})",
                        "prezzo": prz,
                        "scalo_partenza": scalo_dep,
                        "scalo_arrivo": scalo_arr
                    })
        if voli_trovati:
            # Ordina per tariffa più bassa
            voli_trovati.sort(key=lambda x: x["prezzo"])
            return voli_trovati[0]
    except: 
        pass
    return None

# --- ESECUZIONE ---
if st.button("🚀 Avvia Scansione Completa", type="primary", use_container_width=True):
    if not api_key: st.error("Inserisci la chiave API a sinistra."); st.stop()
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
                status.text(f"Controllo {chiamata_attuale}/{totale_chiamate_base} | {origine_nome.split(' ')[0]} ➔ {dest}...")
                
                data_andata_obj = datetime.date(anno, mese, giorno)
                data_ritorno_obj = data_andata_obj + datetime.timedelta(days=giorni_viaggio - 1)
                str_andata = data_andata_obj.strftime("%Y-%m-%d")
                str_ritorno = data_ritorno_obj.strftime("%Y-%m-%d")
                
                # 1. Ricerca del volo di Andata da tutta la macro-area
                andata_info = cerca_volo_singolo(codici_origine, dest, str_andata, pax_api, api_key)
                
                if andata_info:
                    aeroporto_partenza_reale = andata_info["scalo_partenza"] # Es. BGY o FCO
                    status.text(f"Trovata andata da {aeroporto_partenza_reale}! Verifico ritorno da {dest} a {aeroporto_partenza_reale}...")
                    time.sleep(1)
                    
                    # 2. Ricerca del Ritorno forzato sullo STESSO aeroporto italiano di partenza
                    ritorno_info = cerca_volo_singolo(dest, aeroporto_partenza_reale, str_ritorno, pax_api, api_key)
                    
                    # Se non trova il ritorno sullo stesso scalo esatto, cerca in tutta la macro-area
                    if not ritorno_info:
                        ritorno_info = cerca_volo_singolo(dest, codici_origine, str_ritorno, pax_api, api_key)
                    
                    if ritorno_info:
                        prezzo_totale = andata_info["prezzo"] + ritorno_info["prezzo"]
                        prz_singolo = prezzo_totale / pax_api
                        
                        aeroporto_ritorno_reale = ritorno_info["scalo_arrivo"]
                        
                        dati.append({
                            "Data Andata": data_andata_obj.strftime("%d/%m/%y"),
                            "Data Ritorno": data_ritorno_obj.strftime("%d/%m/%y"),
                            "Aeroporto Partenza (IT)": aeroporto_partenza_reale,
                            "Destinazione (UE)": dest,
                            "Aeroporto Ritorno (IT)": aeroporto_ritorno_reale,
                            "Volo Andata": andata_info["orario_dettaglio"],
                            "Volo Ritorno": ritorno_info["orario_dettaglio"],
                            "1 Pax (A/R)": round(prz_singolo, 2),
                            f"Gruppo {passeggeri_reali} Pax": round(prz_singolo * passeggeri_reali, 2)
                        })
                
                progress_bar.progress(chiamata_attuale / totale_chiamate_base)
                time.sleep(1)
                
    status.text("✅ Scansione completata!")
    
    if dati:
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="1 Pax (A/R)")
        df_csv = df.copy()
        
        df["1 Pax (A/R)"] = df["1 Pax (A/R)"].apply(lambda x: f"{x} €")
        df[f"Gruppo {passeggeri_reali} Pax"] = df[f"Gruppo {passeggeri_reali} Pax"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "📥 Scarica CSV Completo", 
            data=df_csv.to_csv(index=False).encode('utf-8'), 
            file_name="voli_dettagliati_gruppo.csv", 
            mime="text/csv"
        )
    else:
        st.warning("Nessuna combinazione diretta andata/ritorno trovata per i criteri selezionati.")
