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
            st.error("Secrets 'firebase' fehlen! Gehe in Streamlit auf 'Settings' -> 'Secrets'.")
            return None
        key_dict = dict(st.secrets["firebase"])
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"Verbindungsfehler: {e}")
        return None

db = get_db()

# --- HILFSFUNKTIONEN ---
def extract_tags(text):
    if not isinstance(text, str) or len(text) < 5: return ""
    words = re.findall(r'\b[A-Z][a-z]{4,}\b', text)
    return ", ".join(list(set(words))[:3])

def get_news(query):
    encoded_query = query.replace(" ", "%20")
    url = f"https://news.google.com/rss/search?q={encoded_query}+Juve+LTO+Wirtschaft&hl=de&gl=DE&ceid=DE:de"
    feed = feedparser.parse(url)
    return feed.entries[:2]

def fetch_contacts_from_db():
    if db is None: return pd.DataFrame()
    docs = db.collection("kontakte").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d['Kontakt'] = doc.id
        data.append(d)
    return pd.DataFrame(data)

# --- HAUPT-PROGRAMM ---
st.title("🧠 My Network Intelligence")

with st.sidebar:
    st.header("📂 Daten-Import")
    file_msg = st.file_uploader("LinkedIn messages.csv hochladen", type=['csv'])
    
    if file_msg is not None:
        st.success("Datei geladen! Klicke jetzt auf den Button unten.")
        # Vorschau der Daten anzeigen, um sicherzugehen, dass sie gelesen werden
        df_preview = pd.read_csv(file_msg).head(3)
        st.write("Vorschau der Datei:")
        st.dataframe(df_preview[['FROM', 'TO', 'DATE']])

        if st.button("🚀 JETZT IN CLOUD SPEICHERN"):
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            try:
                df_li = pd.read_csv(file_msg)
                df_li['DATE'] = pd.to_datetime(df_li['DATE'], errors='coerce')
                df_li['Kontakt'] = df_li.apply(lambda x: x['TO'] if 'Vorbeck' in str(x['FROM']) else x['FROM'], axis=1)
                
                groups = list(df_li.groupby('Kontakt'))
                total = len(groups)
                
                for i, (contact_name, group) in enumerate(groups):
                    name_str = str(contact_name)
                    if name_str not in ["nan", "None", "LinkedIn Member"]:
                        status_text.text(f"Verarbeite: {name_str} ({i+1}/{total})")
                        last_date = group['DATE'].max()
                        content_concat = " ".join(group['CONTENT'].astype(str))
                        
                        # In Firebase schreiben
                        db.collection("kontakte").document(name_str).set({
                            "letzter_kontakt": last_date.strftime("%Y-%m-%d") if not pd.isna(last_date) else "2000-01-01",
                            "tags": extract_tags(content_concat),
                            "quelle": "LinkedIn"
                        }, merge=True)
                        progress_bar.progress((i + 1) / total)
                
                st.success("✅ Alles gespeichert! Die App lädt neu...")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Verarbeiten: {e}")

# --- DASHBOARD ---
df_db = fetch_contacts_from_db()

if not df_db.empty:
    df_db['letzter_kontakt'] = pd.to_datetime(df_db['letzter_kontakt'])
    df_db['Tage vergangen'] = (datetime.datetime.now() - df_db['letzter_kontakt']).dt.days
    
    tab1, tab2 = st.tabs(["⏱️ Tracker", "📰 News Radar"])
    with tab1:
        st.subheader("Touchpoint Tracker")
        st.dataframe(df_db[['Kontakt', 'letzter_kontakt', 'Tage vergangen']].sort_values('letzter_kontakt'))
    with tab2:
        st.subheader("News Radar")
        if st.button("Nach News suchen"):
            for p in df_db['Kontakt'].tolist()[:5]:
                news = get_news(p)
                if news:
                    st.write(f"**{p}:**")
                    for n in news: st.write(f"- [{n.title}]({n.link})")
else:
    st.info("Datenbank leer. Lade eine Datei hoch und klicke auf 'In Cloud speichern'.")
