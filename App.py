import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import feedparser
import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Network Intelligence", layout="wide", page_icon="🌐")

# --- STYLE CSS (OPTIONAL) ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKTIONEN ---

def get_news(query):
    """Sucht echte News via Google News RSS Feed"""
    encoded_query = query.replace(" ", "%20")
    url = f"https://news.google.com/rss/search?q={encoded_query}+Juve+LTO+Wirtschaft&hl=de&gl=DE&ceid=DE:de"
    feed = feedparser.parse(url)
    return feed.entries[:3] # Nur die top 3 News

def draw_network(contacts):
    """Zeichnet das Beziehungsgeflecht"""
    G = nx.Graph()
    G.add_node("ICH", color='red', size=3000)
    
    # Knoten & Kanten aus Daten
    for c in contacts:
        G.add_node(c['Name'], color='skyblue', size=2000)
        G.add_edge("ICH", c['Name'], weight=2)
        if c['Firma']:
            G.add_node(c['Firma'], color='gold', size=1500)
            G.add_edge(c['Name'], c['Firma'], weight=1)

    # Hardcodierte Querverbindung zur Demo
    if len(contacts) > 1:
        G.add_edge(contacts[0]['Name'], contacts[1]['Firma'], weight=0.5, style='dashed')

    pos = nx.spring_layout(G, k=0.8) # Layout berechnen
    
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw(G, pos, with_labels=True, node_color='lightgrey', 
            node_size=2500, font_size=10, font_weight='bold', edge_color='gray')
    st.pyplot(fig)

# --- HAUPT-PROGRAMM ---

st.title("🚀 Mein Personal CRM & Intelligence")

# 1. SIDEBAR (STEUERUNG)
with st.sidebar:
    st.header("🎛️ Steuerung")
    st.write("Lade hier monatlich deine LinkedIn-Daten hoch.")
    uploaded_file = st.file_uploader("Kontakt-Liste (CSV)", type=['csv'])
    
    # Dummy-Daten, falls nichts hochgeladen ist
    if uploaded_file is None:
        st.info("Demo-Modus aktiv (keine Datei hochgeladen)")
        df = pd.DataFrame([
            {"Name": "Jan Müller", "Firma": "Kanzlei X", "Position": "Partner", "Priorität": "Hoch"},
            {"Name": "Thomas von Quadriga", "Firma": "Quadriga Capital", "Position": "MD", "Priorität": "Mittel"},
            {"Name": "Steffi", "Firma": "Eigene Praxis", "Position": "Inhaberin", "Priorität": "Privat"}
        ])
    else:
        df = pd.read_csv(uploaded_file)
        st.success(f"{len(df)} Kontakte geladen!")

# 2. DASHBOARD TABS
tab1, tab2, tab3 = st.tabs(["📊 Übersicht & News", "🕸️ Netzwerkanalyse", "📝 Notizen"])

with tab1:
    st.header("Dein tägliches Briefing")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Kontakte Total", len(df))
    with col2:
        st.metric("Dringende Follow-ups", "2", delta="-1")

    st.subheader("📰 Live News-Radar")
    st.caption("Scannt Google News, Juve, LTO nach deinen Top-Kontakten")
    
    if st.button("Jetzt News scannen"):
        with st.spinner('Scanne das Web...'):
            found_news = False
            for index, row in df.iterrows():
                name = row['Name']
                news_items = get_news(name)
                if news_items:
                    found_news = True
                    with st.expander(f"Neuigkeiten zu: {name}", expanded=True):
                        for item in news_items:
                            st.write(f"**{item.title}**")
                            st.write(f"LINK: {item.link}")
                            st.caption(f"Quelle: {item.source.title} | {item.published}")
            if not found_news:
                st.warning("Keine aktuellen Nachrichten zu deinen Kontakten gefunden.")

with tab2:
    st.header("Wer kennt wen?")
    st.markdown("Diese Karte zeigt Verbindungen zwischen Personen und Firmen.")
    draw_network(df.to_dict('records'))
    st.info("Tipp: Die gestrichelte Linie zeigt eine indirekte Verbindung (Chance für Intro!)")

with tab3:
    st.header("Private Gesprächsnotizen")
    selected_person = st.selectbox("Wähle Person", df['Name'])
    
    # Einfache Notiz-Logik (Achtung: Im Demo-Modus nicht dauerhaft gespeichert!)
    note = st.text_area(f"Notiz zu {selected_person}", height=150, 
                        placeholder="Z.B.: Hat Interesse an Immobilienrecht, Kinder heißen Max & Moritz...")
    
    if st.button("Notiz speichern"):
        st.toast(f"Notiz für {selected_person} gespeichert!", icon="✅")
        # Hier würde in der Pro-Version die Datenbank-Anbindung stehen.
