import streamlit as st
import pandas as pd
from core.calcul_risque import calculer_risque, calculer_priorites
from core.chargement_donnees import charger_excel
from core.excel_utils import ecrire_excel_propre
from core.style import appliquer_style

st.set_page_config(page_title="Priorités magasin", page_icon="🎯", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Priorités magasin (automatiques)🎯")

# ============================================
# Chargement des données
# ============================================
matieres = charger_excel("data/matieres.xlsx", "Matières")
consommation = charger_excel("data/consommation.xlsx", "Consommation")
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")
besoins = charger_excel("data/besoins_production.xlsx", "Besoins de production")

try:
    liaison = charger_excel("data/liaison_matiere_fournisseur.xlsx", "Liaison matière-fournisseur")
except Exception:
    liaison = pd.DataFrame(columns=["code_matiere", "nom_fournisseur"])

# Hypothèse de repli identique à celle de la page Alertes : utilisée
# uniquement quand aucune consommation réelle n'existe pour une matière.
delai_couverture = 15

# On uniformise le format de la date
besoins["date_besoin"] = pd.to_datetime(besoins["date_besoin"]).dt.strftime("%Y-%m-%d")

# ============================================
# Fonction pour faire progresser un statut
# ============================================
def statut_suivant(statut_actuel):
    if statut_actuel == "À traiter":
        return "En cours"
    elif statut_actuel == "En cours":
        return "Traitée"
    else:
        return "Traitée"


def faire_progresser_statut(index_ligne):
    besoins_actuels = charger_excel("data/besoins_production.xlsx", "Besoins de production")
    besoins_actuels.loc[index_ligne, "statut"] = statut_suivant(besoins_actuels.loc[index_ligne, "statut"])
    ecrire_excel_propre(besoins_actuels, "data/besoins_production.xlsx")


# ============================================
# Calculs
# ============================================
# On passe liaison et delai_couverture_securite pour rester cohérent
# avec le calcul fait sur la page Alertes (même fournisseur résolu,
# même hypothèse de repli en cas d'absence de consommation réelle).
resultats_risque = calculer_risque(
    matieres, consommation, fournisseurs,
    liaison=liaison,
    delai_couverture_securite=delai_couverture
)

if len(besoins) == 0:
    st.info("Aucune demande de production enregistrée pour le moment.")
else:
    priorites = calculer_priorites(resultats_risque, besoins)

    # ============================================
    # KPIs de synthèse
    # ============================================
    nb_demandes = len(priorites)
    nb_urgentes = len(priorites[priorites["score_priorite"] >= 70])
    score_moyen = priorites["score_priorite"].mean()

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric("📋 Demandes totales", nb_demandes)

    with col2:
        with st.container(border=True):
            st.metric("🔥 Demandes urgentes (score ≥ 70)", nb_urgentes)

    with col3:
        with st.container(border=True):
            st.metric("📊 Score moyen", f"{score_moyen:.0f} /100")

    st.divider()

    # ============================================
    # Graphique : score de priorité par demande
    # ============================================
    st.subheader("Score de priorité par demande")

    graphique_priorites = priorites[["designation", "score_priorite"]].set_index("designation")
    st.bar_chart(graphique_priorites, color="#2F5496")

    st.divider()

    # ============================================
    # Tableau interactif avec bouton "Traiter"
    # ============================================
    st.subheader("Liste des demandes")

    entetes = st.columns([2, 1, 1, 1, 1, 1, 1, 1])
    libelles_entetes = ["Matière", "Ligne", "Demande", "Date besoin", "Criticité", "Score", "Statut", "Action"]
    for colonne, libelle in zip(entetes, libelles_entetes):
        colonne.markdown(f"**{libelle}**")

    for index_ligne, ligne in priorites.iterrows():
        colonnes = st.columns([2, 1, 1, 1, 1, 1, 1, 1])

        colonnes[0].write(f"{ligne['designation']} ({ligne['code_matiere']})")
        colonnes[1].write(ligne["ligne_production"])
        colonnes[2].write(f"{ligne['quantite_demandee']:.0f}")
        colonnes[3].write(ligne["date_besoin"])
        colonnes[4].write(ligne["niveau_risque"])
        colonnes[5].write(f"{ligne['score_priorite']:.0f}/100")

        if ligne["statut"] == "À traiter":
            colonnes[6].markdown("🔵 À traiter")
        elif ligne["statut"] == "En cours":
            colonnes[6].markdown("🟡 En cours")
        else:
            colonnes[6].markdown("✅ Traitée")

        if ligne["statut"] != "Traitée":
            if colonnes[7].button("Traiter", key=f"traiter_{index_ligne}"):
                faire_progresser_statut(index_ligne)
                st.rerun()
        else:
            colonnes[7].write("—")