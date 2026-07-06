import streamlit as st
import pandas as pd
from core.chargement_donnees import charger_excel

st.title("Estimation des jours restants de stock")

# ============================================
# Chargement des données
# ============================================
matieres = charger_excel("data/matieres.xlsx", "Matières")

# ============================================
# Hypothèse de couverture du stock de sécurité
# ============================================
st.info(
    "⚠️ Aucun historique réel de consommation n'est disponible. "
    "L'estimation ci-dessous suppose que le stock de sécurité couvre un "
    "nombre de jours fixe (paramétrable). Cette hypothèse peut être affinée "
    "dès que des données de consommation réelles seront disponibles."
)

delai_couverture = st.slider(
    "Délai de couverture supposé du stock de sécurité (jours)",
    min_value=5, max_value=45, value=15, step=1,
)

# ============================================
# Calcul de la consommation journalière estimée
# ============================================
matieres["conso_journaliere_estimee"] = (
    matieres["stock_securite"] / delai_couverture
)

# Éviter division par zéro si stock_securite = 0
matieres["conso_journaliere_estimee"] = matieres["conso_journaliere_estimee"].replace(0, 0.01)

matieres["jours_restants"] = (
    matieres["stock_actuel"] / matieres["conso_journaliere_estimee"]
).round(1)

# ============================================
# Niveau d'alerte
# ============================================
def determiner_alerte(jours):
    if jours <= 3:
        return "🔴 Critique"
    elif jours <= 7:
        return "🟠 À surveiller"
    elif jours <= 15:
        return "🟡 Correct"
    else:
        return "🟢 Confortable"

matieres["alerte"] = matieres["jours_restants"].apply(determiner_alerte)
matieres = matieres.sort_values("jours_restants")

# ============================================
# Affichage
# ============================================
st.write("### Estimation des jours de stock restants par matière")

st.dataframe(
    matieres,
    column_config={
        "code_matiere": "Code",
        "designation": "Désignation",
        "type": "Type",
        "stock_actuel": st.column_config.NumberColumn("Stock actuel"),
        "stock_securite": st.column_config.NumberColumn("Stock sécurité"),
        "conso_journaliere_estimee": st.column_config.NumberColumn(
            "Conso/jour (estimée)", format="%.2f"
        ),
        "jours_restants": st.column_config.NumberColumn(
            "Jours restants (estimé)", format="%.1f j"
        ),
        "alerte": "Alerte",
    },
    hide_index=True,
)

nb_critiques = (matieres["jours_restants"] <= 3).sum()
if nb_critiques > 0:
    st.error(f"⚠️ {nb_critiques} matière(s) en rupture critique (≤ 3 jours estimés)")