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
        key_dict = dict(st.secrets["firebase"])
        # Bereinigung des Private Keys (wichtig für Streamlit Cloud)
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
    if not isinstance(text, str): return ""
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

def save_contact_to_db(name, data_dict):
    if db:
        db.collection("kontakte").document(name).set(data_dict, merge=True)

# --- HAUPT-PROGRAMM ---
st.title("🧠 My Network Intelligence")

# --- SIDEBAR: DATEN-UPLOAD ---
with st.sidebar:
    st.header("📂 Daten-Import")
    file_msg = st.file_uploader("LinkedIn messages.csv", type=['csv'])
    file_email = st.file_uploader("E-Mail Export (CSV)", type=['csv'])
    
    if (file_msg or file_email) and st.button("In Cloud-Datenbank speichern"):
        with st.spinner("Verarbeite Daten..."):
            # Verarbeitung LinkedIn
            if file_msg:
                df_li = pd.read_csv(file_msg)
                df_li['DATE'] = pd.to_datetime(df_li['DATE'], errors='coerce')
                df_li['Kontakt'] = df_li.apply(lambda x: x['TO'] if 'Vorbeck' in str(x['FROM']) else x['FROM'], axis=1)
                
                for _, row in df_li.groupby('Kontakt'):
                    name = str(row.name)
                    if name != "nan":
                        last_date = row['DATE'].max()
                        content_sample = " ".join(row['CONTENT'].astype(str))
                        save_contact_to_db(name, {
                            "letzter_kontakt": last_date.strftime("%Y-%m-%d"),
                            "tags": extract_tags(content_sample),
                            "quelle": "LinkedIn"
                        })
            st.success("Daten synchronisiert!")
            st.rerun()

# --- DASHBOARD ---
df_db = fetch_contacts_from_db()

if not df_db.empty:
    df_db['letzter_kontakt'] = pd.to_datetime(df_db['letzter_kontakt'])
    df_db['Tage vergangen'] = (datetime.datetime.now() - df_db['letzter_kontakt']).dt.days
    
    tab1, tab2, tab3 = st.tabs(["⏱️ Tracker", "🏷️ Memory", "📰 News Radar"])

    with tab1:
        st.subheader("Touchpoint Tracker")
        col1, col2 = st.columns(2)
        with col1:
            st.write("🔴 **Dringend (über 180 Tage)**")
            st.dataframe(df_db[df_db['Tage vergangen'] > 180][['Kontakt', 'letzter_kontakt']].sort_values('letzter_kontakt'))
        with col2:
            st.write("🟢 **Kürzlich**")
            st.dataframe(df_db[df_db['Tage vergangen'] <= 180][['Kontakt', 'letzter_kontakt']].sort_values('letzter_kontakt', ascending=False))

    with tab2:
        st.subheader("KI Memory Tags")
        suche = st.text_input("Suchen:")
        if suche:
            res = df_db[df_db['Kontakt'].str.contains(suche, case=False, na=False)]
            for _, r in res.iterrows():
                st.info(f"**{r['Kontakt']}** | Tags: `{r.get('tags', 'keine')}`")

    with tab3:
        if st.button("Netzwerk scannen"):
            for p in df_db['Kontakt'].tolist()[:5]:
                news = get_news(p)
                if news:
                    st.write(f"**{p}:**")
                    for n in news: st.write(f"- [{n.title}]({n.link})")
else:
    st.info("Datenbank leer. Bitte CSV hochladen.")
