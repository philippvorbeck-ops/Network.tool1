import streamlit as st
import pandas as pd
import datetime
import feedparser
from google.cloud import firestore
from google.oauth2 import service_account
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Personal Intelligence", layout="wide", page_icon="🧠")

# --- FIREBASE VERBINDUNG ---
@st.cache_resource
def get_db():
    try:
        if "firebase" not in st.secrets:
            st.error("Secrets 'firebase' nicht gefunden. Bitte in Streamlit Cloud unter Settings -> Secrets hinterlegen.")
            return None
        
        key_dict = dict(st.secrets["firebase"])
        # Bereinigung des Private Keys (wichtig für Streamlit Cloud Hosting)
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"Fehler bei der Firebase-Verbindung: {e}")
        return None

db = get_db()

# --- HILFSFUNKTIONEN ---
def extract_tags(text):
    """Extrahiert einfache Schlagworte aus Nachrichtentexten"""
    if not isinstance(text, str) or len(text) < 5: return ""
    # Findet Worte, die mit Großbuchstaben beginnen (Eigennamen/Nomen)
    words = re.findall(r'\b[A-Z][a-z]{4,}\b', text)
    unique_tags = list(set(words))
    return ", ".join(unique_tags[:3])

def get_news(query):
    """RSS-Suche für News-Updates"""
    encoded_query = query.replace(" ", "%20")
    url = f"https://news.google.com/rss/search?q={encoded_query}+Juve+LTO+Wirtschaft&hl=de&gl=DE&ceid=DE:de"
    feed = feedparser.parse(url)
    return feed.entries[:2]

def fetch_contacts_from_db():
    """Lädt alle Kontakte aus der Firebase Cloud"""
    if db is None: return pd.DataFrame()
    try:
        docs = db.collection("kontakte").stream()
        data = []
        for doc in docs:
            d = doc.to_dict()
            d['Kontakt'] = doc.id
            data.append(d)
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

def save_contact_to_db(name, data_dict):
    """Speichert oder aktualisiert einen Kontakt in Firebase"""
    if db:
        db.collection("kontakte").document(name).set(data_dict, merge=True)

# --- HAUPT-PROGRAMM ---
st.title("🧠 My Network Intelligence")

# --- SIDEBAR: DATEN-IMPORT ---
with st.sidebar:
    st.header("📂 Daten-Import")
    st.write("Lade hier deine Export-Dateien hoch:")
    file_msg = st.file_uploader("LinkedIn messages.csv", type=['csv'])
    file_email = st.file_uploader("E-Mail Export (CSV)", type=['csv'])
    
    if (file_msg or file_email) and st.button("Daten synchronisieren"):
        with st.spinner("Verarbeite Daten und speichere in Cloud..."):
            # 1. LinkedIn Verarbeitung
            if file_msg:
                df_li = pd.read_csv(file_msg)
                df_li['DATE'] = pd.to_datetime(df_li['DATE'], errors='coerce')
                # Wer ist der Kontakt? (To, wenn From 'Vorbeck' ist, sonst From)
                df_li['Kontakt'] = df_li.apply(lambda x: x['TO'] if 'Vorbeck' in str(x['FROM']) else x['FROM'], axis=1)
                
                # Gruppierung nach Kontakt zur Extraktion des letzten Zeitpunkts
                for contact_name, group in df_li.groupby('Kontakt'):
                    name_str = str(contact_name)
                    if name_str != "nan" and name_str != "None":
                        last_date = group['DATE'].max()
                        content_concat = " ".join(group['CONTENT'].astype(str))
                        save_contact_to_db(name_str, {
                            "letzter_kontakt": last_date.strftime("%Y-%m-%d"),
                            "tags": extract_tags(content_concat),
                            "quelle": "LinkedIn"
                        })
