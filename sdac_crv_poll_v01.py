import streamlit as st
import pandas as pd
import json
import os
from collections import Counter

FILE_CANDIDATI = r"C:\0-Tools\0_SDAC\Caravaggio\nomi_cognomi_chiesa.csv"
#FILE_VOTI = r"C:\0-Tools\0_SDAC\Caravaggio\voti_exit_poll.json"
FILE_CANDIDATI_URL = "https://raw.githubusercontent.com/jcvr6876/sdac_crv/main/nomi_cognomi_chiesa.csv"



@st.cache_data
def carica_candidati(file_path):
    df = pd.read_csv(file_path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "cognome" not in df.columns or "nome" not in df.columns:
        st.error("Il CSV deve contenere almeno le colonne 'cognome' e 'nome'.")
        return []

    df_sorted = df.sort_values(by=["nome", "cognome"])
    candidati = (df_sorted["nome"].str.strip() + " " + df_sorted["cognome"].str.strip()).tolist()
    return candidati

def carica_voti():
    if os.path.exists(FILE_VOTI):
        try:
            with open(FILE_VOTI, "r", encoding="utf-8") as f:
                contenuto = f.read().strip()
                if not contenuto:
                    return []
                return json.loads(contenuto)
        except (json.JSONDecodeError, IOError):
            with open(FILE_VOTI, "w", encoding="utf-8") as f:
                f.write("[]")
            return []
    else:
        return []

def salva_voti(tematica, voti_lista):
    voti = carica_voti()
    voti.append({
        "tematica": tematica,
        "voti": voti_lista
    })
    with open(FILE_VOTI, "w", encoding="utf-8") as f:
        json.dump(voti, f, ensure_ascii=False, indent=2)

def mostra_report_storico():
    voti = carica_voti()
    if not voti:
        st.info("Nessun voto registrato ancora.")
        return

    for sessione in voti:
        st.markdown("---")
        tematica = sessione.get("tematica", "Tematica non definita")
        st.write(f"**Tematica della votazione:** {tematica}")
        contatore = Counter(sessione.get("voti", []))
        totale = sum(contatore.values())
        for candidato, count in contatore.most_common():
            percentuale = (count / totale) * 100 if totale > 0 else 0
            st.write(f"{candidato}: {count} voto{'i' if count > 1 else ''} ({percentuale:.1f}%)")

def reload_page():
    try:
        st.experimental_rerun()
    except AttributeError:
        params = dict(st.query_params)
        cont = int(params.get("r", ["0"])[0])
        cont += 1
        params["r"] = str(cont)
        st.query_params = params

def main():
    st.title("Exit Poll Votazione Candidati - Voto Segreto")

    if not os.path.exists(FILE_CANDIDATI):
        st.error(f"File '{FILE_CANDIDATI}' non trovato. Caricalo nella stessa cartella.")
        return

    candidati = carica_candidati(FILE_CANDIDATI)
    if not candidati:
        st.warning("Nessun candidato trovato o errore nel file CSV.")
        return

    if "tematica" not in st.session_state:
        st.session_state.tematica = ""

    if "votato" not in st.session_state:
        st.session_state.votato = False

    if "ultimo_voto" not in st.session_state:
        st.session_state.ultimo_voto = []

    # Inserimento tematica
    if not st.session_state.tematica:
        tematica = st.text_input("Inserisci la tematica della votazione", key="tematica_input")
        if tematica:
            st.session_state.tematica = tematica
        else:
            st.info("Per favore inserisci la tematica per poter procedere.")
            return

    st.write(f"**Tematica attuale:** {st.session_state.tematica}")

    if not st.session_state.votato:
        st.write("Seleziona uno o più candidati flaggando la casella accanto al nome:")

        num_col = 4
        num_righe = (len(candidati) + num_col - 1) // num_col
        selezionati = []

        for r in range(num_righe):
            cols = st.columns(num_col)
            for c in range(num_col):
                idx = r * num_col + c
                if idx < len(candidati):
                    candidato = candidati[idx]
                    with cols[c]:
                        flag = st.checkbox(candidato, key=f"check_{candidato}")
                        if flag:
                            selezionati.append(candidato)

        if st.button("Invia voto"):
            if not selezionati:
                st.error("Devi selezionare almeno un candidato.")
            else:
                salva_voti(st.session_state.tematica, selezionati)
                st.session_state.ultimo_voto = {
                    "tematica": st.session_state.tematica,
                    "voti": selezionati
                }
                st.success(f"Voto registrato per {len(selezionati)} candidato{'i' if len(selezionati) > 1 else ''}. Grazie per aver partecipato!")
                st.session_state.votato = True

    if st.session_state.votato:
        st.success("Hai già inviato il voto.")
        if st.button("Ricomincia exit poll"):
            st.session_state.votato = False
            st.session_state.ultimo_voto = []
            st.session_state.tematica = ""
            # resetta checkbox
            for candidato in candidati:
                key = f"check_{candidato}"
                if key in st.session_state:
                    del st.session_state[key]
            reload_page()

    st.markdown("---")

    if st.checkbox("Mostra report storico delle votazioni (tutte le sessioni)"):
        st.header("Report storico delle votazioni (tutte le sessioni)")
        mostra_report_storico()

    st.markdown("---")

    if st.checkbox("Mostra report ultimo voto (sessione corrente)"):
        st.subheader("Report voti sessione corrente")
        ultimo = st.session_state.get("ultimo_voto", None)
        if not ultimo:
            st.info("Nessun voto inviato in questa sessione.")
        else:
            tematica = ultimo.get("tematica", "Tematica non definita")
            voti = ultimo.get("voti", [])
            st.write(f"**Tematica della votazione:** {tematica}")
            tot = len(voti)
            counts = Counter(voti)
            for candidato, count in counts.most_common():
                perc = (count / tot) * 100 if tot > 0 else 0
                st.write(f"{candidato}: {count} voto{'i' if count > 1 else ''} ({perc:.1f}%)")

if __name__ == "__main__":
    main()
