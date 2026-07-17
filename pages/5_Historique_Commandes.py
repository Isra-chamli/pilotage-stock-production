import streamlit as st
import pandas as pd
from core.style import appliquer_style
from core.suivi_commandes import charger_suivi

st.set_page_config(page_title="Historique des commandes", page_icon="📜", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Historique des commandes 📜")
st.caption(
    "Suivi de toutes les commandes déclenchées depuis la page Alertes : "
    "de la commande initiale jusqu'à la livraison."
)

suivi = charger_suivi()

if len(suivi) == 0:
    st.info("Aucune commande n'a encore été créée depuis la page Alertes.")
else:
    # ============================================
    # KPIs de synthèse
    # ============================================
    nb_commandees = len(suivi[suivi["statut"] == "Commandé"])
    nb_en_livraison = len(suivi[suivi["statut"] == "En cours de livraison"])
    nb_livrees = len(suivi[suivi["statut"] == "Livré"])

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("🛒 Commandées", nb_commandees)
    with col2:
        with st.container(border=True):
            st.metric("🚚 En cours de livraison", nb_en_livraison)
    with col3:
        with st.container(border=True):
            st.metric("✅ Livrées", nb_livrees)

    st.divider()

    # ============================================
    # Filtre par statut
    # ============================================
    statuts_disponibles = ["Tous", "Commandé", "En cours de livraison", "Livré"]
    statut_choisi = st.selectbox("Filtrer par statut", statuts_disponibles)

    affichage = suivi.copy()
    if statut_choisi != "Tous":
        affichage = affichage[affichage["statut"] == statut_choisi]

    affichage = affichage.sort_values("date_creation", ascending=False)

    st.dataframe(
        affichage,
        column_config={
            "code_matiere": "Code",
            "designation": "Désignation",
            "statut": "Statut",
            "quantite_a_commander": st.column_config.NumberColumn("Quantité"),
            "nom_fournisseur": "Fournisseur",
            "date_creation": "Alerte détectée le",
            "date_commande": "Commandé le",
            "date_debut_livraison": "En livraison depuis le",
            "date_livraison": "Livré le",
        },
        hide_index=True,
        use_container_width=True,
    )