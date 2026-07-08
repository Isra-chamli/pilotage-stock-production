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
    "nombre de jours fixe (paramétrable)."
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

st.divider()

# ============================================
# Filtres avancés
# ============================================
st.write("### 🔍 Recherche et filtres")

col1, col2, col3 = st.columns(3)

with col1:
    # Barre de recherche texte libre
    recherche = st.text_input(
        "Rechercher par code ou désignation",
        placeholder="Ex: ART001 ou galet..."
    )

with col2:
    # Filtre par type
    types_disponibles = ["Tous"] + sorted(matieres["type"].dropna().unique().tolist())
    type_choisi = st.selectbox("Type", types_disponibles)

with col3:
    # Filtre par niveau d'alerte
    alertes_disponibles = ["Tous", "🔴 Critique", "🟠 À surveiller", "🟡 Correct", "🟢 Confortable"]
    alerte_choisie = st.selectbox("Niveau d'alerte", alertes_disponibles)

# Filtre sur le stock actuel (slider de range)
col_min, col_max = st.columns(2)
with col_min:
    stock_min = st.number_input(
        "Stock actuel minimum",
        min_value=0,
        value=0,
        step=1
    )
with col_max:
    stock_max = st.number_input(
        "Stock actuel maximum",
        min_value=0,
        value=int(matieres["stock_actuel"].max()),
        step=1
    )

# ============================================
# Application des filtres
# ============================================
resultats = matieres.copy()

# Filtre texte (code ou désignation)
if recherche:
    masque = (
        resultats["code_matiere"].str.contains(recherche, case=False, na=False)
        | resultats["designation"].str.contains(recherche, case=False, na=False)
    )
    resultats = resultats[masque]

# Filtre type
if type_choisi != "Tous":
    resultats = resultats[resultats["type"] == type_choisi]

# Filtre alerte
if alerte_choisie != "Tous":
    resultats = resultats[resultats["alerte"] == alerte_choisie]

# Filtre stock actuel
resultats = resultats[
    (resultats["stock_actuel"] >= stock_min) &
    (resultats["stock_actuel"] <= stock_max)
]

st.divider()

# ============================================
# Résumé des filtres appliqués
# ============================================
st.caption(f"**{len(resultats)}** matière(s) affichée(s) sur {len(matieres)} au total")

# ============================================
# Affichage du tableau filtré
# ============================================
st.write("### Estimation des jours de stock restants par matière")

st.dataframe(
    resultats,
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

# ============================================
# Résumé des alertes sur les données filtrées
# ============================================
nb_critiques = (resultats["jours_restants"] <= 3).sum()
nb_surveiller = ((resultats["jours_restants"] > 3) & (resultats["jours_restants"] <= 7)).sum()

if nb_critiques > 0:
    st.error(f"⚠️ {nb_critiques} matière(s) en rupture critique (≤ 3 jours estimés)")
if nb_surveiller > 0:
    st.warning(f"👁️ {nb_surveiller} matière(s) à surveiller (entre 3 et 7 jours estimés)")