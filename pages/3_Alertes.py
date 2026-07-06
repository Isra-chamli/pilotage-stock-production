import streamlit as st
import pandas as pd
from core.calcul_risque import calculer_risque
from core.chargement_donnees import charger_excel
from core.style import appliquer_style

st.set_page_config(page_title="Alertes", page_icon="🚨", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Alertes de rupture🚨")

# Chargement des données
matieres = charger_excel("data/matieres.xlsx", "Matières")
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")
besoins = charger_excel("data/besoins_production.xlsx", "Besoins de production")

try:
    consommation = charger_excel("data/consommation.xlsx", "Consommation")
except Exception:
    consommation = pd.DataFrame(columns=["code_matiere", "conso_moyenne_jour"])

# Calcul du risque
resultats = calculer_risque(matieres, consommation, fournisseurs)

# On ne garde que les matières à risque
alertes = resultats[resultats["niveau_risque"] != "🟢 Normal"].copy()

# ============================================
# On retire les matières dont TOUTES les demandes sont traitées
# ============================================
def matiere_a_encore_une_demande_active(code_matiere):
    demandes_de_cette_matiere = besoins[besoins["code_matiere"] == code_matiere]
    if len(demandes_de_cette_matiere) == 0:
        return True
    return (demandes_de_cette_matiere["statut"] != "Traitée").any()

alertes["a_une_demande_active"] = alertes["code_matiere"].apply(matiere_a_encore_une_demande_active)
alertes = alertes[alertes["a_une_demande_active"]]

# Tri par ratio_stock (le plus critique en premier)
alertes = alertes.sort_values("ratio_stock")

if len(alertes) == 0:
    st.success("Aucune alerte actuelle. Toutes les matières sont à un niveau normal, ou leurs demandes ont déjà été traitées.")
else:
    # ============================================
    # KPIs de synthèse
    # ============================================
    nb_alertes = len(alertes)
    ratio_min = alertes["ratio_stock"].min()
    quantite_totale_a_commander = alertes["quantite_a_commander"].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric("🚨 Matières en alerte", nb_alertes)

    with col2:
        with st.container(border=True):
            st.metric("📦 Quantité totale à commander", f"{quantite_totale_a_commander:.0f}")

    st.divider()

    st.warning(f"{len(alertes)} matière(s) nécessitent une attention.")

    for _, ligne in alertes.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**{ligne['niveau_risque']} — {ligne['designation']}** ({ligne['code_matiere']})")
                st.write(f"Action recommandée : {ligne['action_recommandee']}")
                st.write(f"Quantité à commander : **{ligne['quantite_a_commander']:.0f}**")

            with col2:
                ratio = ligne["ratio_stock"]
                st.write(f"Stock actuel : {ligne['stock_actuel']:.0f}")
                st.write(f"Seuil de sécurité : {ligne['stock_securite']:.0f}")
                st.write(f"Ratio stock : {ratio*100:.0f}% du seuil")

    st.divider()
    st.write("### Vue tableau complète")
    colonnes_a_masquer = ["a_une_demande_active", "couverture_jours", 
                       "conso_moyenne_jour", "nom_fournisseur"]
colonnes_affichees = [c for c in alertes.columns 
                      if c not in colonnes_a_masquer]
st.dataframe(alertes[colonnes_affichees])