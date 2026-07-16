import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.chargement_donnees import charger_excel

st.title("Estimation des jours restants de stock")

# ============================================
# Chargement des données
# ============================================
matieres = charger_excel("data/matieres.xlsx", "Matières")

# ============================================
# Hypothèse de couverture du stock de sécurité
# ============================================
delai_couverture = 15  # jours de couverture supposés du stock de sécurité

st.info(
    "⚠️ Aucun historique réel de consommation n'est disponible pour cette estimation. "
    f"Elle suppose que le stock de sécurité couvre {delai_couverture} jours."
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

# ============================================
# ANALYSE ABC
# Basée sur le stock actuel (critère de valeur disponible)
# A : 80% du stock cumulé → articles les plus importants
# B : 15% du stock cumulé → articles intermédiaires
# C : 5% du stock cumulé → articles peu critiques
# ============================================
matieres_abc = matieres.copy()
matieres_abc = matieres_abc.sort_values("stock_actuel", ascending=False)
matieres_abc["stock_cumule"] = matieres_abc["stock_actuel"].cumsum()
stock_total = matieres_abc["stock_actuel"].sum()
matieres_abc["pourcentage_cumule"] = matieres_abc["stock_cumule"] / stock_total * 100

def determiner_classe_abc(pct):
    if pct <= 80:
        return "A"
    elif pct <= 95:
        return "B"
    else:
        return "C"

matieres_abc["classe_ABC"] = matieres_abc["pourcentage_cumule"].apply(determiner_classe_abc)

# On remet la classe ABC dans le dataframe principal
matieres = matieres.merge(
    matieres_abc[["code_matiere", "classe_ABC", "pourcentage_cumule"]],
    on="code_matiere",
    how="left"
)

matieres = matieres.sort_values("jours_restants")

st.divider()

# ============================================
# SECTION ANALYSE ABC + PARETO
# ============================================
st.write("## 📊 Analyse ABC des stocks")
st.caption(
    "Classification ABC basée sur le stock actuel. "
    "Classe A = articles qui représentent 80% du stock total (priorité maximale). "
    "Classe B = 15% suivants. Classe C = 5% restants."
)

# KPIs ABC
nb_A = (matieres["classe_ABC"] == "A").sum()
nb_B = (matieres["classe_ABC"] == "B").sum()
nb_C = (matieres["classe_ABC"] == "C").sum()

col_a, col_b, col_c = st.columns(3)
with col_a:
    with st.container(border=True):
        st.metric("🔴 Classe A — Priorité haute", f"{nb_A} articles",
                  help="Représentent 80% du stock total")
with col_b:
    with st.container(border=True):
        st.metric("🟡 Classe B — Priorité moyenne", f"{nb_B} articles",
                  help="Représentent 15% du stock total")
with col_c:
    with st.container(border=True):
        st.metric("🟢 Classe C — Priorité faible", f"{nb_C} articles",
                  help="Représentent 5% du stock total")

st.divider()

# ============================================
# DIAGRAMME DE PARETO
# ============================================
st.write("### 📈 Diagramme de Pareto des stocks")

# On prend les 20 premiers articles pour lisibilité
pareto_data = matieres_abc.head(20).copy()

fig = go.Figure()

# Barres : stock actuel par article
fig.add_trace(go.Bar(
    x=pareto_data["code_matiere"],
    y=pareto_data["stock_actuel"],
    name="Stock actuel",
    marker_color=[
        "#e74c3c" if c == "A" else "#f39c12" if c == "B" else "#27ae60"
        for c in pareto_data["classe_ABC"]
    ],
    yaxis="y1",
))

# Courbe : pourcentage cumulé
fig.add_trace(go.Scatter(
    x=pareto_data["code_matiere"],
    y=pareto_data["pourcentage_cumule"],
    name="% cumulé",
    mode="lines+markers",
    line=dict(color="#2F5496", width=2),
    marker=dict(size=6),
    yaxis="y2",
))

# Ligne de référence 80%
fig.add_hline(
    y=80,
    line_dash="dash",
    line_color="red",
    annotation_text="Seuil 80% (Classe A)",
    annotation_position="right",
    yref="y2",
)

fig.update_layout(
    title="Diagramme de Pareto — Top 20 articles par stock actuel",
    xaxis_title="Code article",
    yaxis=dict(title="Stock actuel", side="left"),
    yaxis2=dict(
        title="% cumulé",
        side="right",
        overlaying="y",
        range=[0, 110],
        ticksuffix="%",
    ),
    legend=dict(x=0.01, y=0.99),
    height=450,
    plot_bgcolor="white",
    paper_bgcolor="white",
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================
# Filtres avancés
# ============================================
st.write("### 🔍 Recherche et filtres")

col1, col2, col3, col4 = st.columns(4)

with col1:
    recherche = st.text_input(
        "Rechercher par code ou désignation",
        placeholder="Ex: ART001 ou galet..."
    )

with col2:
    types_disponibles = ["Tous"] + sorted(matieres["type"].dropna().unique().tolist())
    type_choisi = st.selectbox("Type", types_disponibles)

with col3:
    alertes_disponibles = ["Tous", "🔴 Critique", "🟠 À surveiller", "🟡 Correct", "🟢 Confortable"]
    alerte_choisie = st.selectbox("Niveau d'alerte", alertes_disponibles)

with col4:
    # Nouveau filtre par classe ABC
    classes_disponibles = ["Tous", "A", "B", "C"]
    classe_choisie = st.selectbox("Classe ABC", classes_disponibles)

col_min, col_max = st.columns(2)
with col_min:
    stock_min = st.number_input("Stock actuel minimum", min_value=0, value=0, step=1)
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

if recherche:
    masque = (
        resultats["code_matiere"].str.contains(recherche, case=False, na=False)
        | resultats["designation"].str.contains(recherche, case=False, na=False)
    )
    resultats = resultats[masque]

if type_choisi != "Tous":
    resultats = resultats[resultats["type"] == type_choisi]

if alerte_choisie != "Tous":
    resultats = resultats[resultats["alerte"] == alerte_choisie]

if classe_choisie != "Tous":
    resultats = resultats[resultats["classe_ABC"] == classe_choisie]

resultats = resultats[
    (resultats["stock_actuel"] >= stock_min) &
    (resultats["stock_actuel"] <= stock_max)
]

st.divider()

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
        "classe_ABC": "Classe ABC",
        "pourcentage_cumule": st.column_config.NumberColumn(
            "% cumulé", format="%.1f%%"
        ),
    },
    hide_index=True,
)

nb_critiques = (resultats["jours_restants"] <= 3).sum()
nb_surveiller = ((resultats["jours_restants"] > 3) & (resultats["jours_restants"] <= 7)).sum()

if nb_critiques > 0:
    st.error(f"⚠️ {nb_critiques} matière(s) en rupture critique (≤ 3 jours estimés)")
if nb_surveiller > 0:
    st.warning(f"👁️ {nb_surveiller} matière(s) à surveiller (entre 3 et 7 jours estimés)")