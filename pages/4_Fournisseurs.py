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
historique = charger_excel("data/historique_fournisseurs.xlsx", "Historique fournisseurs")

# ============================================
# Recalcul du score de fiabilité depuis l'historique réel
# Score basé sur la RÉGULARITÉ des délais (écart-type)
# Un fournisseur régulier (même délai à chaque fois) = fiable
# Un fournisseur imprévisible (délais très variables) = peu fiable
# ============================================
def calculer_score_fiabilite(groupe):
    """
    Score = max(0, 100 - (ecart_type / delai_moyen * 100))
    - Si écart_type = 0 (toujours le même délai) → score = 100%
    - Plus le délai varie, plus le score baisse
    """
    delai_moyen = groupe["delai_moyen_jours"].mean()
    ecart_type = groupe["delai_moyen_jours"].std()

    if delai_moyen == 0 or pd.isna(ecart_type):
        return 100  # un seul enregistrement = on lui accorde le bénéfice du doute

    coefficient_variation = ecart_type / delai_moyen
    score = max(0, 100 - (coefficient_variation * 100))
    return round(score, 0)

synthese = historique.groupby(
    ["nom_fournisseur", "Pays", "origine"]
).apply(
    lambda g: pd.Series({
        "nb_commandes": len(g),
        "delai_moyen_jours": round(g["delai_moyen_jours"].mean(), 0),
        "score_fiabilite": calculer_score_fiabilite(g),
    })
).reset_index()

def determiner_risque_fournisseur(score):
    if score >= 80:
        return "🟢 Fiable"
    elif score >= 60:
        return "🟡 Assez fiable"
    elif score >= 40:
        return "🟠 Peu fiable"
    else:
        return "🔴 Très peu fiable"

synthese["risque"] = synthese["score_fiabilite"].apply(determiner_risque_fournisseur)
synthese = synthese.sort_values("score_fiabilite", ascending=False)

st.write("### Synthèse par fournisseur")
st.caption("Score de fiabilité basé sur la régularité des délais de livraison (écart-type). Plus le délai est constant, plus le fournisseur est fiable.")

st.dataframe(
    synthese,
    column_config={
        "nom_fournisseur": "Fournisseur",
        "Pays": "Pays",
        "origine": "Origine",
        "nb_commandes": "Nb commandes",
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
# Graphique : évolution du délai moyen par mois
# ============================================
st.write("### Évolution du délai moyen de livraison (par mois)")

historique_valide = historique.dropna(subset=["date_reception"]).copy()

if len(historique_valide) == 0:
    st.info("Pas assez de données historiques pour tracer une évolution.")
else:
    historique_valide["mois"] = pd.to_datetime(
        historique_valide["date_reception"], errors="coerce"
    ).dt.strftime("%Y-%m")

    # 6 fournisseurs les plus actifs
    top_fournisseurs = (
        historique_valide["nom_fournisseur"].value_counts().head(6).index.tolist()
    )
    historique_top = historique_valide[
        historique_valide["nom_fournisseur"].isin(top_fournisseurs)
    ]

    evolution = (
        historique_top.groupby(["mois", "nom_fournisseur"])["delai_moyen_jours"]
        .mean()
        .reset_index()
    )

    evolution_pivot = evolution.pivot(
        index="mois", columns="nom_fournisseur", values="delai_moyen_jours"
    ).sort_index()

    st.caption("Délai moyen en jours pour les 6 fournisseurs les plus actifs. Une courbe qui monte = délais qui s'allongent.")
    st.line_chart(evolution_pivot)

st.divider()
st.write("### Historique détaillé des commandes")

historique_affichage = historique.copy()
for colonne_date in ["date_demande", "date_reception"]:
    if colonne_date in historique_affichage.columns:
        historique_affichage[colonne_date] = pd.to_datetime(
            historique_affichage[colonne_date], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

st.dataframe(historique_affichage)