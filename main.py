import streamlit as st
import pandas as pd
from core.calcul_risque import calculer_risque
from core.chargement_donnees import charger_excel
from core.style import appliquer_style

st.set_page_config(page_title="Pilotage Intelligent du Magasin", page_icon="🏭", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

# ============================================
# En-tête de l'application
# ============================================
st.title("🏭 Pilotage Intelligent du Magasin")
st.caption("Réduction des arrêts de production liés aux ruptures de matières consommables")

st.divider()

# Chargement sécurisé des données
matieres = charger_excel("data/matieres.xlsx", "Matières")
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")

try:
    consommation = charger_excel("data/consommation.xlsx", "Consommation")
except Exception:
    consommation = pd.DataFrame(columns=["code_matiere", "conso_moyenne_jour"])

resultats = calculer_risque(matieres, consommation, fournisseurs)

nb_total = len(resultats)
nb_risque_eleve = len(resultats[resultats["niveau_risque"] == "🔴 Élevé"])
nb_risque_moyen = len(resultats[resultats["niveau_risque"] == "🟠 Moyen"])
nb_normal = len(resultats[resultats["niveau_risque"] == "🟢 Normal"])

# ============================================
# Indicateurs clés, dans des cartes avec bordure
# ============================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.metric("📦 Matières suivies", nb_total)

with col2:
    with st.container(border=True):
        st.metric("🔴 Risque élevé", nb_risque_eleve)

with col3:
    with st.container(border=True):
        st.metric("🟠 Risque moyen", nb_risque_moyen)

with col4:
    with st.container(border=True):
        st.metric("🟢 Niveau normal", nb_normal)

st.divider()


st.markdown("### 📊 Dashboard Power BI")
st.write("Consultez la version Power BI du pilotage de stock, avec vue Synthèse, Matières et Fournisseurs.")

st.link_button(
    "Ouvrir le dashboard Power BI",
    "https://app.powerbi.com/links/AOQAiVtNHh?ctid=dbd6664d-4eb9-46eb-99d8-5c43ba153c61&pbi_source=linkShare"
)


# ============================================
# Graphique : répartition des matières par niveau de risque
# ============================================
st.subheader("Répartition des matières par niveau de risque")

repartition = resultats["niveau_risque"].value_counts().reset_index()
repartition.columns = ["niveau_risque", "nombre"]

ordre_risque = ["🔴 Élevé", "🟠 Moyen", "🟢 Normal"]
repartition["niveau_risque"] = pd.Categorical(
    repartition["niveau_risque"], categories=ordre_risque, ordered=True
)
repartition = repartition.sort_values("niveau_risque")

st.bar_chart(
    repartition.set_index("niveau_risque"),
    color="#2F5496",
)

st.divider()

# ============================================
# Aperçu rapide des alertes les plus urgentes
# ============================================
st.subheader("Aperçu des priorités")

alertes_urgentes = resultats[resultats["niveau_risque"] == "🔴 Élevé"].sort_values("ratio_stock")

if len(alertes_urgentes) == 0:
    st.success("Aucune matière en risque élevé actuellement.")
else:
    for _, ligne in alertes_urgentes.head(3).iterrows():
        ratio = ligne["ratio_stock"]
        st.warning(
            f"**{ligne['designation']}** ({ligne['code_matiere']}) — "
            f"stock à {ratio*100:.0f}% du seuil de sécurité "
            f"(stock actuel : {ligne['stock_actuel']:.0f} / seuil : {ligne['stock_securite']:.0f})"
        )

st.page_link("pages/3_Alertes.py", label="Voir toutes les alertes en détail", icon="🚨")

st.divider()
st.caption("Utilise le menu à gauche pour naviguer entre les différentes fonctionnalités de l'application.")





