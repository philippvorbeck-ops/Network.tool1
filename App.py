import streamlit as st
import pandas as pd
import datetime
import feedparser
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- KONFIGURATION ---
st.set_page_config(page_title="Personal Intelligence", layout="wide", page_icon="🧠")

# --- FIREBASE VERBINDUNG ---
@st.cache_resource
def get_db():
    # Holt den Schlüssel sicher aus den Streamlit Secrets
    key_dict = dict(st.secrets["firebase"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    db = firestore.Client(credentials=creds, project=key_dict["project_id"])
    return db

db = get_db()

# --- HILFSFUNKTIONEN ---
def get_news(query):
    encoded_query = query.replace(" ", "%20")
    url = f"https://news.google.com/rss/search?q={encoded_query}+Juve+LTO+Wirtschaft&hl=de&gl=DE&ceid=DE:de"
    feed = feedparser.parse(url)
    return feed.entries[:2]

def fetch_contacts_from_db():
    """Holt alle Kontakte aus Firebase"""
    kontakte_ref = db.collection("kontakte")
    docs = kontakte_ref.stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d['Kontakt'] = doc.id
        data.append(d)
    return pd.DataFrame(data)

def save_contact_to_db(name, data_dict):
    """Speichert einen Kontakt dauerhaft in Firebase"""
    db.collection("kontakte").document(name).set(data_dict, merge=True)

# --- HAUPT-PROGRAMM ---
st.title("🧠 My Network Intelligence")

# --- SIDEBAR: DATEN-UPLOAD ZU FIREBASE ---
with st.sidebar:
    st.header("📂 Daten in die Cloud laden")
    st.write("Lade hier deine Dateien hoch, um die Datenbank zu füllen.")
    file_msg = st.file_uploader("LinkedIn messages.csv", type=['csv'])
    
    if file_msg:
        with st.spinner("Speichere in Firebase..."):
            df_li = pd.read_csv(file_msg)
            if 'DATE' in df_li.columns and 'FROM' in df_li.columns:
                df_li['DATE'] = pd.to_datetime(df_li['DATE'], errors='coerce')
                # Kontakt identifizieren
                df_li['Kontakt'] = df_li.apply(lambda x: x['TO'] if 'Vorbeck' in str(x['FROM']) else x['FROM'], axis=1)
                
                # Letztes Datum pro Kontakt finden
                df_contacts = df_li.groupby('Kontakt')['DATE'].max().reset_index()
                
                # In Datenbank schreiben
                for _, row in df_contacts.iterrows():
                    kontakt_name = str(row['Kontakt'])
                    if kontakt_name and kontakt_name != "nan":
                        save_contact_to_db(kontakt_name, {
                            "letzter_kontakt": row['DATE'].strftime("%Y-%m-%d"),
                            "quelle": "LinkedIn"
                        })
            st.success("Erfolgreich in Firebase gespeichert! Du kannst die CSV jetzt löschen.")

# --- DATEN AUS FIREBASE LADEN ---
df_db = fetch_contacts_from_db()

if not df_db.empty:
    df_db['letzter_kontakt'] = pd.to_datetime(df_db['letzter_kontakt'])
    df_db['Tage vergangen'] = (datetime.datetime.now() - df_db['letzter_kontakt']).dt.days
    
    tab1, tab2 = st.tabs(["⏱️ Touchpoint Tracker", "📰 News Radar"])

    with tab1:
        st.header("Automated Touchpoint Tracker")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔴 Dringend melden (> 180 Tage)")
            df_urgent = df_db[df_db['Tage vergangen'] > 180].sort_values('Tage vergangen', ascending=False)
            st.dataframe(df_urgent[['Kontakt', 'letzter_kontakt', 'Tage vergangen']].head(10), use_container_width=True)
            
        with col2:
            st.subheader("🟢 Kürzlich in Kontakt")
            df_recent = df_db[df_db['Tage vergangen'] <= 180].sort_values('Tage vergangen')
            st.dataframe(df_recent[['Kontakt', 'letzter_kontakt', 'Tage vergangen']].head(10), use_container_width=True)

    with tab2:
        st.header("Fokussiertes News-Radar")
        if st.button("Netzwerk nach News scannen"):
            with st.spinner("Durchsuche Fachportale..."):
                top_kontakte = df_db['Kontakt'].tolist()[:10]
                gefunden = False
                for person in top_kontakte:
                    if person in ["LinkedIn Member", ""]: continue
                    news = get_news(person)
                    if news:
                        gefunden = True
                        st.markdown(f"### 📰 Treffer für: **{person}**")
                        for item in news:
                            st.write(f"- [{item.title}]({item.link})")
                if not gefunden:
                    st.success("Keine aktuellen Nachrichten zu deinen Kontakten.")
else:
    st.info("Deine Datenbank ist noch leer. Lade links eine messages.csv hoch, um sie zu füllen!")..")
    
    if st.button("Notiz speichern"):
        st.toast(f"Notiz für {selected_person} gespeichert!", icon="✅")
        # Hier würde in der Pro-Version die Datenbank-Anbindung stehen.
