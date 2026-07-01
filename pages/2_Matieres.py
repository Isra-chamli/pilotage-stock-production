import streamlit as st
import pandas as pd
from core.calcul_risque import calculer_risque
from core.chargement_donnees import charger_excel
from core.style import appliquer_style

st.set_page_config(page_title="Matières", page_icon="📦", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Matières📦")

# Chargement des données
matieres = charger_excel("data/matieres.xlsx", "Matières")
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")

try:
    consommation = charger_excel("data/consommation.xlsx", "Consommation")
except Exception:
    consommation = pd.DataFrame(columns=["code_matiere", "conso_moyenne_jour"])

# Calcul du risque
resultats = calculer_risque(matieres, consommation, fournisseurs)

# ============================================
# Filtre par type
# ============================================
types_disponibles = ["Tous"] + resultats["type"].unique().tolist()
type_choisi = st.selectbox("Filtrer par type :", types_disponibles)

if type_choisi != "Tous":
    resultats = resultats[resultats["type"] == type_choisi]

# ============================================
# KPIs de synthèse
# ============================================
nb_matieres = len(resultats)
nb_sous_securite = len(resultats[resultats["stock_actuel"] < resultats["stock_securite"]])
stock_total = resultats["stock_actuel"].sum()

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.metric("📦 Matières affichées", nb_matieres)

with col2:
    with st.container(border=True):
        st.metric("⚠️ Sous le stock de sécurité", nb_sous_securite)

with col3:
    with st.container(border=True):
        st.metric("📊 Stock total (toutes unités)", f"{stock_total:.0f}")

st.divider()

# ============================================
# Graphique : stock actuel vs stock de sécurité
# ============================================
st.subheader("Stock actuel vs stock de sécurité")

graphique_stock = resultats[["designation", "stock_actuel", "stock_securite"]].set_index("designation")
graphique_stock.columns = ["Stock actuel", "Stock de sécurité"]

st.bar_chart(graphique_stock, color=["#2F5496", "#E84545"])

st.divider()

# ============================================
# Tableau détaillé — colonnes utiles uniquement
# ============================================
colonnes_a_afficher = [
    "code_matiere", "designation", "type",
    "stock_actuel", "stock_securite", "ratio_stock",
    "niveau_risque", "action_recommandee", "quantite_a_commander"
]

st.dataframe(
    resultats[colonnes_a_afficher],
    column_config={
        "code_matiere": "Code",
        "designation": "Désignation",
        "type": "Type",
        "stock_actuel": st.column_config.NumberColumn("Stock actuel", format="%.0f"),
        "stock_securite": st.column_config.NumberColumn("Stock sécurité", format="%.0f"),
        "ratio_stock": st.column_config.ProgressColumn(
            "Ratio stock", min_value=0, max_value=2, format="%.2f"
        ),
        "niveau_risque": "Risque",
        "action_recommandee": "Action recommandée",
        "quantite_a_commander": st.column_config.NumberColumn(
            "Qté à commander", format="%.0f"
        ),
    },
    hide_index=True,
)