import streamlit as st
import pandas as pd
import json
import mysql.connector
from collections import Counter

# Configurazione DB
MYSQL_HOST = "localhost"
MYSQL_USER = "VLZ6876"
MYSQL_PASSWORD = "+fil413DEA=!"
MYSQL_DATABASE = "sdac_crv_mem"  # Cambia con il nome del tuo DB

FILE_CANDIDATI = r"C:\0-Tools\0_SDAC\Caravaggio\nomi_cognomi_chiesa.csv"

def get_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=True
    )

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

def leggi_tematica():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tematica FROM tematica_votazione ORDER BY aggiornata_il DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return row[0]
    return ""

def salva_tematica(tematica):
    conn = get_connection()
    cursor = conn.cursor()
    # Inserisci nuova riga con la tematica aggiornata
    cursor.execute("INSERT INTO tematica_votazione (tematica) VALUES (%s)", (tematica,))
    cursor.close()
    conn.close()

def salva_voto(tematica, nickname, voti_lista):
    conn = get_connection()
    cursor = conn.cursor()
    voti_json = json.dumps(voti_lista, ensure_ascii=False)
    cursor.execute(
        "INSERT INTO voti (tematica, nickname, voti) VALUES (%s, %s, %s)",
        (tematica, nickname, voti_json)
    )
    cursor.close()
    conn.close()

def leggi_voti():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT tematica, nickname, voti FROM voti")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def main():
    st.title("Exit Poll MySQL - Voto Segreto")

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

    # Leggi tematica corrente dal DB
    tematica_corrente = leggi_tematica()

    # Inserimento/modifica tematica
    if not tematica_corrente:
        tematica_corrente = st.text_input("Inserisci la tematica della votazione", key="tematica_input")
        if tematica_corrente:
            salva_tematica(tematica_corrente)
        else:
            st.info("Per favore inserisci la tematica per poter procedere.")
            return

    st.write(f"**Tematica attuale:** {tematica_corrente}")

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

        nickname = st.text_input("Inserisci un tuo nickname unico", key="nickname_input")

        if st.button("Invia voto"):
            if not selezionati:
                st.error("Devi selezionare almeno un candidato.")
            elif not nickname:
                st.error("Devi inserire un nickname.")
            else:
                salva_voto(tematica_corrente, nickname.strip(), selezionati)
                st.session_state.ultimo_voto = {
                    "tematica": tematica_corrente,
                    "voti": selezionati
                }
                st.session_state.votato = True
                st.success(f"Voto registrato per {len(selezionati)} candidato{'i' if len(selezionati) > 1 else ''}. Grazie!")

    if st.session_state.votato:
        st.success("Hai già inviato il voto.")
        if st.button("Ricomincia exit poll"):
            st.session_state.votato = False
            st.session_state.ultimo_voto = []
            st.session_state.tematica = ""
            for candidato in candidati:
                key = f"check_{candidato}"
                if key in st.session_state:
                    del st.session_state[key]
            reload_page()

    st.markdown("---")

    if st.checkbox("Mostra report storico delle votazioni (tutte le sessioni)"):
        st.header("Report storico delle votazioni (tutte le sessioni)")
        voti = leggi_voti()
        if not voti:
            st.info("Nessun voto registrato.")
        else:
            # Raggruppa per tematica e candidato
            gruppi = {}
            for v in voti:
                t = v['tematica']
                if t not in gruppi:
                    gruppi[t] = Counter()
                voti_candidati = json.loads(v['voti'])
                gruppi[t].update(voti_candidati)

            for t, counter in gruppi.items():
                st.subheader(f"Tematica: {t}")
                totale = sum(counter.values())
                for candidato, count in counter.most_common():
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

if __name__ == "__main__":
    main()
