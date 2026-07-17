import streamlit as st
import pandas as pd
import io
from datetime import date
from core.calcul_risque import calculer_risque
from core.chargement_donnees import charger_excel
from core.style import appliquer_style
from core.email_alertes import envoyer_alerte_rupture
from core.suivi_commandes import (
    charger_suivi, creer_commande, avancer_statut, statut_actif, est_traitee
)

st.set_page_config(page_title="Alertes", page_icon="🚨", layout="wide")

# ============================================
# Sidebar
# ============================================
st.sidebar.markdown("## 🏭 Pilotage Magasin")
st.sidebar.markdown("---")
appliquer_style()

st.title("Alertes de rupture🚨")


def fmt(valeur, suffixe=""):
    """Affiche un nombre proprement, ou 'N/D' si la donnée est manquante
    (évite d'afficher 'nan' à l'écran pour les matières sans historique
    de consommation / stock de sécurité connu)."""
    if pd.isna(valeur):
        return "N/D"
    return f"{valeur:.0f}{suffixe}"


# Chargement des données
matieres = charger_excel("data/matieres.xlsx", "Matières")
fournisseurs = charger_excel("data/fournisseurs.xlsx", "Fournisseurs")
besoins = charger_excel("data/besoins_production.xlsx", "Besoins de production")
suivi = charger_suivi()

try:
    consommation = charger_excel("data/consommation.xlsx", "Consommation")
except Exception:
    consommation = pd.DataFrame(columns=["code_matiere", "conso_moyenne_jour"])

try:
    liaison = charger_excel("data/liaison_matiere_fournisseur.xlsx", "Liaison matière-fournisseur")
except Exception:
    liaison = pd.DataFrame(columns=["code_matiere", "nom_fournisseur"])

# ============================================
# Hypothèse de couverture (utilisée seulement en repli, quand aucune
# consommation réelle n'est disponible pour une matière)
# ============================================
st.info(
    "ℹ️ Le nombre de jours restants utilise en priorité la **consommation réelle** "
    "calculée à partir de l'historique de commandes (`consommation.xlsx`). Quand elle "
    "n'existe pas pour une matière, une **estimation** basée sur le stock de sécurité "
    "est utilisée à la place."
)

delai_couverture = 15  # hypothèse fixe : stock de sécurité supposé couvrir 15 jours,
# utilisée uniquement en repli quand aucune consommation réelle n'existe pour la matière.
# À ajuster ici directement si besoin, une fois qu'on aura plus de recul sur la
# vraie consommation moyenne.

# Calcul du risque
resultats = calculer_risque(
    matieres, consommation, fournisseurs,
    liaison=liaison,
    delai_couverture_securite=delai_couverture
)

nb_sans_donnee = len(resultats[resultats["niveau_risque"] == "⚪ Donnée manquante"])
if nb_sans_donnee > 0:
    st.warning(
        f"⚪ {nb_sans_donnee} matière(s) n'ont ni consommation réelle ni stock de sécurité "
        f"renseigné : leur risque n'est pas calculable et elles n'apparaissent pas ci-dessous. "
        f"Complétez `matieres.xlsx` pour les inclure."
    )

# On ne garde que les matières à risque avéré (Élevé / Moyen).
# Les matières en "⚪ Donnée manquante" ne sont PAS affichées ici : leur
# risque réel est inconnu, on ne peut pas les classer comme urgentes.
# Elles restent visibles sur la page Estimation / la page d'accueil, où
# c'est signalé qu'il faut compléter leurs données.
alertes = resultats[resultats["niveau_risque"].isin(["🔴 Élevé", "🟠 Moyen"])].copy()

# ============================================
# On retire les matières déjà marquées "Livré" : une fois la commande
# reçue, la matière quitte la page Alertes et rejoint l'Historique des
# commandes, même si le risque calculé est encore élevé (le stock
# physique dans matieres.xlsx n'a peut-être pas encore été remis à jour).
# ============================================
alertes = alertes[~alertes["code_matiere"].apply(lambda c: est_traitee(suivi, c))]

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
alertes = alertes.sort_values("couverture_jours", na_position="last")

if len(alertes) == 0:
    st.success("Aucune alerte actuelle. Toutes les matières sont à un niveau normal, leur commande est déjà en cours de traitement, ou leurs demandes ont déjà été traitées.")
else:
    # ============================================
    # KPIs de synthèse
    # ============================================
    nb_alertes = len(alertes)
    jours_min = alertes["couverture_jours"].min()
    quantite_totale_a_commander = alertes["quantite_a_commander"].sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric("🚨 Matières en alerte", nb_alertes)

    with col2:
        with st.container(border=True):
            st.metric("⏳ Jours restants (min.)", fmt(jours_min, " j"))

    with col3:
        with st.container(border=True):
            st.metric("📦 Quantité totale à commander", fmt(quantite_totale_a_commander))

    st.divider()

    # ============================================
    # Export Excel et CSV
    # ============================================
    colonnes_a_masquer = [
        "a_une_demande_active", "ratio_stock",
        "conso_source", "donnee_insuffisante", "fournisseur_identifie", "delai_fiable"
    ]
    colonnes_affichees = [c for c in alertes.columns if c not in colonnes_a_masquer]
    alertes_export = alertes[colonnes_affichees].copy()

    col_export1, col_export2 = st.columns(2)

    with col_export1:
        # Export Excel
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
            alertes_export.to_excel(writer, index=False, sheet_name="Alertes")
        buffer_excel.seek(0)

        st.download_button(
            label="📥 Télécharger le rapport Excel",
            data=buffer_excel,
            file_name=f"rapport_alertes_{date.today().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_export2:
        # Export CSV
        csv = alertes_export.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            label="📥 Télécharger le rapport CSV",
            data=csv,
            file_name=f"rapport_alertes_{date.today().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
        )

    st.divider()

    # ============================================
    # Envoi email d'alerte
    # ============================================
    st.write("### 📧 Envoyer le rapport par email")

    col_email1, col_email2 = st.columns([2, 1])

    with col_email1:
        st.caption(
            "Envoie un email de résumé des alertes au responsable magasin "
            "et au directeur."
        )

    with col_email2:
        if st.button("📧 Envoyer l'alerte par email", type="primary"):
            with st.spinner("Envoi en cours..."):
                colonnes_email = [
                    "code_matiere", "designation", "niveau_risque",
                    "stock_actuel", "stock_securite",
                    "quantite_a_commander", "nom_fournisseur"
                ]
                colonnes_dispo = [c for c in colonnes_email if c in alertes.columns]
                succes, message = envoyer_alerte_rupture(alertes[colonnes_dispo])

            if succes:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")

    st.warning(f"{len(alertes)} matière(s) nécessitent une attention.")

    for _, ligne in alertes.iterrows():
        code = ligne["code_matiere"]
        statut_courant = statut_actif(suivi, code)

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"**{ligne['niveau_risque']} — {ligne['designation']}** ({code})")
                st.write(f"Action recommandée : {ligne['action_recommandee']}")
                st.write(f"Quantité à commander : **{fmt(ligne['quantite_a_commander'])}**")

            with col2:
                st.write(f"Stock actuel : {fmt(ligne['stock_actuel'])}")
                st.write(f"Jours restants estimés : **{fmt(ligne['couverture_jours'], ' j')}**")
                st.write(f"Fournisseur : **{ligne['nom_fournisseur']}**")
                delai_txt = fmt(ligne['delai_moyen_jours'], ' j')
                if not ligne.get("delai_fiable", True):
                    delai_txt += " ⚠️ (délai non vérifiable pour ce fournisseur)"
                st.write(f"Délai fournisseur : {delai_txt}")

            with col3:
                st.write("**Suivi de la commande**")

                if statut_courant is None:
                    if st.button("🛒 Commander", key=f"commander_{code}"):
                        suivi = creer_commande(
                            suivi, code, ligne["designation"],
                            ligne["quantite_a_commander"], ligne["nom_fournisseur"]
                        )
                        st.rerun()

                elif statut_courant == "Commandé":
                    st.markdown("🛒 **Commandé**")
                    if st.button("🚚 Marquer en cours de livraison", key=f"livraison_{code}"):
                        suivi = avancer_statut(suivi, code)
                        st.rerun()

                elif statut_courant == "En cours de livraison":
                    st.markdown("🚚 **En cours de livraison**")
                    if st.button("✅ Marquer comme livré", key=f"livre_{code}"):
                        suivi = avancer_statut(suivi, code)
                        st.success("Livraison enregistrée — déplacée vers l'Historique des commandes.")
                        st.rerun()

    st.divider()
    st.write("### Vue tableau complète")
    st.dataframe(alertes_export)