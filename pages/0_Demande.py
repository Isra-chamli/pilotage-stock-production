import streamlit as st
import pandas as pd
from datetime import date
from core.excel_utils import ecrire_excel_propre
from core.chargement_donnees import charger_excel
from core.style import appliquer_style

st.set_page_config(page_title="Demande de matière", page_icon="📝", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Créer une demande de matière première / consommable 📝")

# ============================================
# Chargement des données nécessaires au formulaire
# ============================================
matieres = charger_excel("data/matieres.xlsx", "Matières")
besoins = charger_excel("data/besoins_production.xlsx", "Besoins de production")

# Liste des matières disponibles pour le menu déroulant
matieres["affichage"] = matieres["code_matiere"] + " - " + matieres["designation"]

# ============================================
# Le formulaire
# ============================================
with st.form("formulaire_demande"):
    col1, col2 = st.columns(2)

    with col1:
        matiere_choisie = st.selectbox(
            "Matière / Consommable",
            options=matieres["affichage"].tolist(),
        )
        quantite = st.number_input("Quantité demandée", min_value=1, value=100)
        ligne_production = st.selectbox(
            "Ligne de production",
            options=["Ligne A", "Ligne B", "Ligne C"],
        )

    with col2:
        date_besoin = st.date_input("Date besoin", value=date.today())
        criticite = st.selectbox(
            "Criticité production",
            options=["Basse (1)", "Normale (2)", "Moyenne (3)", "Haute (4)", "Très Haute (5)"],
        )

    commentaire = st.text_area("Commentaire (optionnel)")

    bouton_envoye = st.form_submit_button("Enregistrer la demande")

# ============================================
# Traitement quand le formulaire est soumis
# ============================================
if bouton_envoye:
    code_matiere_choisi = matiere_choisie.split(" - ")[0]

    nouvelle_ligne = pd.DataFrame({
        "code_matiere": [code_matiere_choisi],
        "ligne_production": [ligne_production],
        "quantite_demandee": [quantite],
        "date_besoin": [date_besoin],
        "criticite": [criticite],
        "commentaire": [commentaire],
        "statut": ["À traiter"],
    })

    besoins_mis_a_jour = pd.concat([besoins, nouvelle_ligne], ignore_index=True)
    ecrire_excel_propre(besoins_mis_a_jour, "data/besoins_production.xlsx")

    st.success(f"Demande enregistrée : {quantite} unités de {matiere_choisie} pour {date_besoin}")