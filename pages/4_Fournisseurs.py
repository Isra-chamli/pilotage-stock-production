import streamlit as st
import pandas as pd
from core.chargement_donnees import charger_excel
from core.style import appliquer_style

st.set_page_config(page_title="Fournisseurs", page_icon="🚚", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Analyse des fournisseurs")

# Chargement des données
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")
historique = charger_excel("data/historique_fournisseurs.xlsx", "Historique fournisseurs")

# ============================================
# Synthèse par fournisseur (déjà calculée dans fournisseurs.xlsx)
# ============================================
synthese = fournisseurs.copy()


def determiner_risque_fournisseur(score):
    if score >= 90:
        return "🟢 Faible"
    elif score >= 70:
        return "🟡 Moyen"
    elif score >= 50:
        return "🟠 Élevé"
    else:
        return "🔴 Très élevé"


synthese["risque"] = synthese["score_fiabilite"].apply(determiner_risque_fournisseur)

st.write("### Synthèse par fournisseur")

colonnes_dispo = [c for c in [
    "nom_fournisseur", "pays", "origine", "nb_commandes_historique",
    "delai_moyen_jours", "score_fiabilite", "risque",
] if c in synthese.columns]

st.dataframe(
    synthese[colonnes_dispo],
    column_config={
        "nom_fournisseur": "Fournisseur",
        "pays": "Pays",
        "origine": "Origine",
        "nb_commandes_historique": "Nb commandes",
        "delai_moyen_jours": st.column_config.NumberColumn(
            "Délai moyen (jours)", format="%.0f j"
        ),
        "score_fiabilite": st.column_config.ProgressColumn(
            "Score fiabilité", min_value=0, max_value=100, format="%.0f%%"
        ),
        "risque": "Niveau de risque",
    },
    hide_index=True,
)

st.divider()

# ============================================
# Graphique : évolution mensuelle du taux de livraison à temps
# calculé directement depuis l'historique réel des commandes
# ============================================
st.write("### Évolution du taux de livraison à temps (par mois)")

# On ne garde que les commandes avec une date de réception connue
historique_valide = historique.dropna(subset=["date_reception"]).copy()

if len(historique_valide) == 0 or "dans_les_delais" not in historique_valide.columns:
    st.info("Pas assez de données historiques datées pour tracer une évolution.")
else:
    historique_valide["mois"] = pd.to_datetime(
        historique_valide["date_reception"]
    ).dt.strftime("%Y-%m")

    # On ne garde que les fournisseurs les plus actifs pour un graphique lisible
    top_fournisseurs = (
        historique_valide["nom_fournisseur"].value_counts().head(6).index.tolist()
    )
    historique_top = historique_valide[
        historique_valide["nom_fournisseur"].isin(top_fournisseurs)
    ]

    # Taux de livraison à temps = moyenne de dans_les_delais (True/False -> 1/0), en %
    evolution = (
        historique_top.groupby(["mois", "nom_fournisseur"])["dans_les_delais"]
        .mean()
        .reset_index()
    )
    evolution["taux_pourcent"] = evolution["dans_les_delais"] * 100

    evolution_pivot = evolution.pivot(
        index="mois", columns="nom_fournisseur", values="taux_pourcent"
    ).sort_index()

    st.caption("Affiché pour les 6 fournisseurs les plus actifs (par nombre de commandes).")
    st.line_chart(evolution_pivot)

st.divider()
st.write("### Historique détaillé des commandes")

# On nettoie les colonnes de dates avant affichage : Streamlit/Arrow
# n'accepte pas une colonne qui mélange dates et texte/valeurs vides.
historique_affichage = historique.copy()
for colonne_date in ["date_demande", "date_reception"]:
    if colonne_date in historique_affichage.columns:
        historique_affichage[colonne_date] = pd.to_datetime(
            historique_affichage[colonne_date], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

st.dataframe(historique_affichage)