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
# ============================================
DELAIS_STANDARDS = {
    "local": 30,
    "étranger": 60,
}

# Vérifier si les colonnes existent, sinon les créer
if "origine" not in historique.columns:
    historique["origine"] = "local"
if "Pays" not in historique.columns:
    historique["Pays"] = "Tunisie"

# On ajoute le délai standard AVANT le groupby
historique["delai_standard"] = historique["origine"].map(DELAIS_STANDARDS).fillna(45)

synthese = historique.groupby(
    ["nom_fournisseur", "Pays", "origine"]
).agg(
    nb_commandes=("nom_fournisseur", "count"),
    delai_moyen_jours=("delai_moyen_jours", "mean"),
    delai_standard_jours=("delai_standard", "first"),
).reset_index()

synthese["delai_moyen_jours"] = synthese["delai_moyen_jours"].round(0)

# ============================================
# Nouvelle formule correcte :
# Si delai_reel <= delai_standard → score élevé (jusqu'à 100%)
# Si delai_reel > delai_standard → score qui baisse progressivement
# Exemple : 29j / standard 30j → 100% ✅
#           36j / standard 30j → 80%  ✅
#           74j / standard 60j → 77%  ✅
#           197j / standard 60j → 0%  ✅
# ============================================
synthese["score_fiabilite"] = synthese.apply(
    lambda row: round(
        max(0, min(100,
            100 - max(0, (row["delai_moyen_jours"] - row["delai_standard_jours"]))
            / row["delai_standard_jours"] * 100
        )),
        0
    ),
    axis=1
)

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
st.caption("Score de fiabilité : 100% si le fournisseur respecte le délai standard (30j locaux / 60j étrangers). Le score baisse proportionnellement au dépassement du délai.")

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