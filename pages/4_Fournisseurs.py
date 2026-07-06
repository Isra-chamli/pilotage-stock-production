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
# Délais standards par origine
# (basés sur les normes industrielles pour une usine tunisienne)
# ============================================
DELAIS_STANDARDS = {
    "local": 30,      # fournisseur tunisien : délai acceptable = 30 jours
    "étranger": 60,   # fournisseur européen : délai acceptable = 60 jours
}

def calculer_score_fournisseur(groupe):
    """
    Score basé sur la performance réelle vs délai standard attendu.
    score = max(0, (delai_standard - delai_reel) / delai_standard * 100)
    - Fournisseur livre avant le délai standard → score élevé
    - Fournisseur livre exactement au délai standard → score moyen
    - Fournisseur livre après le délai standard → score bas ou 0
    """
    origine = groupe["origine"].iloc[0]
    delai_standard = DELAIS_STANDARDS.get(origine, 45)
    delai_reel_moyen = groupe["delai_moyen_jours"].mean()

    score = ((delai_standard - delai_reel_moyen) / delai_standard) * 100
    score = max(0, min(100, score))
    return round(score, 0)

synthese = historique.groupby(
    ["nom_fournisseur", "Pays", "origine"]
).apply(
    lambda g: pd.Series({
        "nb_commandes": len(g),
        "delai_moyen_jours": round(g["delai_moyen_jours"].mean(), 0),
        "delai_standard_jours": DELAIS_STANDARDS.get(g["origine"].iloc[0], 45),
        "score_fiabilite": calculer_score_fournisseur(g),
    })
).reset_index()

def determiner_risque_fournisseur(score):
    if score >= 75:
        return "🟢 Fiable"
    elif score >= 50:
        return "🟡 Acceptable"
    elif score >= 25:
        return "🟠 Lent"
    else:
        return "🔴 Très lent"

synthese["risque"] = synthese["score_fiabilite"].apply(determiner_risque_fournisseur)
synthese = synthese.sort_values("score_fiabilite", ascending=False)

st.write("### Synthèse par fournisseur")
st.caption("Score basé sur le délai réel vs délai standard attendu (30j fournisseurs locaux / 60j fournisseurs étrangers). Score 100% = livraison bien avant le délai standard.")

st.dataframe(
    synthese,
    column_config={
        "nom_fournisseur": "Fournisseur",
        "Pays": "Pays",
        "origine": "Origine",
        "nb_commandes": "Nb commandes",
        "delai_moyen_jours": st.column_config.NumberColumn(
            "Délai réel moyen", format="%.0f j"
        ),
        "delai_standard_jours": st.column_config.NumberColumn(
            "Délai standard", format="%.0f j"
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