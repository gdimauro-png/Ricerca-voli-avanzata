import streamlit as st
import pandas as pd
import datetime, calendar, time
from serpapi import GoogleSearch

st.set_page_config(page_title="Voli Gruppi Europa", page_icon="✈️", layout="wide")
st.title("✈️ Radar Voli Gruppi: Orizzonte Europa")
st.markdown("Genera preventivi e orari esatti per grandi gruppi combinando le low-cost.")

# --- DATABASE AMPLIATO ---
MACRO_AREE = {
    "NORD (MXP, BGY, VCE, TRN, BLQ, GOA...)": "BGY,MXP,LIN,TRN,VCE,TSF,VRN,BLQ,GOA",
    "CENTRO (FCO, CIA, PSA, FLR, PEG...)": "FCO,CIA,PSA,FLR,AOI,PEG",
    "SUD (NAP, BRI, BDS, SUF...)": "NAP,BRI,BDS,SUF,REG",
    "ISOLE (CTA, PMO, CAG, OLB...)": "CTA,PMO,TPS,CAG,OLB,AHO"
}

# 30+ Destinazioni principali Europee Low-Cost
TOP_EUROPA = [
    # Penisola Iberica
    "BCN (Barcellona)", "MAD (Madrid)", "ALC (Alicante)", "AGP (Malaga)", 
    "VLC (Valencia)", "LIS (Lisbona)", "OPO (Porto)",
    # Europa Occidentale / Nord
    "STN (Londra Stansted)", "LGW (Londra Gatwick)", "ORY (Parigi Orly)", 
    "BVA (Parigi Beauvais)", "AMS (Amsterdam)", "CRL (Bruxelles Charleroi)", 
    "BRU (Bruxelles Zaventem)", "BER (Berlino)", "FRA (Francoforte)", "MUC (Monaco)",
    # Est Europa
    "PRG (Praga)", "BUD (Budapest)", "VIE (Vienna)", "WAW (Varsavia)", 
    "OTP (Bucarest)", "SOF (Sofia)",
    # Mediterraneo e Isole
    "ATH (Atene)", "MLA (Malta)", "TFS (Tenerife)", "LPA (Gran Canaria)", 
    "PMI (Palma di Maiorca)", "IBZ (Ibiza)", "JMK (Mykonos)", "JTR (Santorini)"
]

COMPAGNIE_TARGET = ["Ryanair", "Wizz Air", "easyJet", "Vueling", "Buzz", "Malta"]

# --- INTERFACCIA LATERALE ---
st.sidebar.header("⚙️ 1. Credenziali")
api_key = st.sidebar.text_input("🔑 API Key SerpApi", type="password")

st.sidebar.header("🗺️ 2. Tratte")
origini = st.sidebar.multiselect("🛫 Da dove parti?", list(MACRO_AREE.keys()), default=[list(MACRO_AREE.keys())[0]])
dest_selezionate = st.sidebar.multiselect("🛬 Scegli Aeroporti Europei", TOP_EUROPA, default=["BCN (Barcellona)"])
dest_custom = st.sidebar.text_input("...o digita Codici IATA (es. DUB, ZAG)")

st.sidebar.header("📅 3. Periodo")
anno = st.sidebar.selectbox("Anno", [2026, 2027])
mese = st.sidebar.selectbox("Mese", list(range(1, 13)), index=10)
giorni_viaggio = st.sidebar.slider("Durata Viaggio (giorni)", 2, 14, 5)

st.sidebar.header("👥 4. Passeggeri")
passeggeri_reali = st.sidebar.number_input("Partecipanti totali", min_value=1, max_value=200, value=25)

# --- ELABORAZIONE ---
lista_dest = [d.split(" ")[0] for d in dest_selezionate]
if dest_custom:
    lista_dest.extend([d.strip().upper() for d in dest_custom.split(",") if d.strip()])
lista_dest = list(set(lista_dest))

giorni_nel_mese = calendar.monthrange(anno, mese)[1]
giorni_da_testare = giorni_nel_mese - giorni_viaggio + 2
totale_chiamate = len(origini) * len(lista_dest) * giorni_da_testare

st.markdown("---")
st.info(f"💡 Il sistema eseguirà **{totale_chiamate} ricerche automatiche** (Controlla i tuoi crediti API mensili).")

if st.button("🚀 Avvia Scansione Completa", type="primary", use_container_width=True):
    if not api_key:
        st.error("Inserisci la chiave API a sinistra.")
        st.stop()
    if not origini or not lista_dest:
        st.error("Seleziona un'origine e una destinazione.")
        st.stop()
        
    pax_api = min(passeggeri_reali, 9)
    progress_bar = st.progress(0)
    status = st.empty()
    dati = []
    chiamata_attuale = 0
    
    for origine_nome in origini:
        codici_origine = MACRO_AREE[origine_nome]
        for dest in lista_dest:
            for giorno in range(1, giorni_da_testare):
                chiamata_attuale += 1
                status.text(f"Ricerca {chiamata_attuale}/{totale_chiamate} | {origine_nome.split(' ')[0]} ➔ {dest}...")
                
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
                        if "flights" in opz and len(opz["flights"]) > 0:
                            andata = opz["flights"][0]
                            comp_a = andata.get("airline", "")
                            
                            # Filtro low-cost
                            if any(t.lower() in comp_a.lower() for t in COMPAGNIE_TARGET):
                                prz = opz.get("price", 0)
                                if prz > 0:
                                    prz_singolo = prz / pax_api
                                    
                                    # Formattazione orario e volo Andata
                                    orario_andata = andata.get("departure_airport", {}).get("time", "N/D")
                                    volo_andata = andata.get("flight_number", "")
                                    info_andata = f"{orario_andata} ({comp_a} {volo_andata})"
                                    
                                    # Tentativo di estrazione info Ritorno (se esposto dalle API)
                                    info_ritorno = "Vedi sito ufficiale"
                                    if len(opz["flights"]) > 1:
                                        ritorno = opz["flights"][1]
                                        comp_r = ritorno.get("airline", comp_a)
                                        orario_ritorno = ritorno.get("departure_airport", {}).get("time", "N/D")
                                        volo_ritorno = ritorno.get("flight_number", "")
                                        info_ritorno = f"{orario_ritorno} ({comp_r} {volo_ritorno})"
                                    
                                    dati.append({
                                        "Data Andata": data_andata.strftime("%d/%m"),
                                        "Data Ritorno": data_ritorno.strftime("%d/%m"),
                                        "Da": andata["departure_airport"]["id"],
                                        "A": dest,
                                        "Dettagli Andata": info_andata,
                                        "Dettagli Ritorno": info_ritorno,
                                        "Costo 1 Pax": round(prz_singolo, 2),
                                        f"Preventivo ({passeggeri_reali} pax)": round(prz_singolo * passeggeri_reali, 2)
                                    })
                except:
                    pass
                
                progress_bar.progress(chiamata_attuale / totale_chiamate)
                time.sleep(1.2)
                
    status.text("✅ Scansione completata!")
    
    if dati:
        df = pd.DataFrame(dati).drop_duplicates().sort_values(by="Costo 1 Pax")
        df_csv = df.copy()
        
        df["Costo 1 Pax"] = df["Costo 1 Pax"].apply(lambda x: f"{x} €")
        df[f"Preventivo ({passeggeri_reali} pax)"] = df[f"Preventivo ({passeggeri_reali} pax)"].apply(lambda x: f"{x} €")
        
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "📥 Scarica Excel (CSV)", 
            data=df_csv.to_csv(index=False).encode('utf-8'), 
            file_name="voli_gruppi_orari.csv", 
            mime="text/csv"
        )
    else:
        st.warning("Nessuna combinazione diretta trovata.")
