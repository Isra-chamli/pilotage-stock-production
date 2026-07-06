"""
Logique métier : calcul du risque de rupture de stock
Adapté aux vraies données Maklada :
- Pas de consommation historique disponible
  → consommation journalière ESTIMÉE à partir du stock de sécurité,
    en supposant qu'il couvre un nombre de jours donné (paramétrable)
- Pas de liaison code_matiere dans le fichier fournisseurs
  → délai moyen global calculé depuis l'historique des commandes
"""

import pandas as pd


def calculer_risque(matieres, consommation, fournisseurs, delai_couverture_securite=15):
    """
    Calcule le niveau de risque de rupture pour chaque matière.

    delai_couverture_securite : hypothèse (en jours) sur le nombre de jours
    que le stock de sécurité est censé couvrir. Sert à estimer une
    consommation journalière en l'absence d'historique réel.

    Évolution future (quand une vraie consommation sera disponible) :
    - Remplir conso_moyenne_jour dans consommation.xlsx avec des valeurs > 0
    - La fonction utilisera automatiquement ces vraies valeurs à la place
      de l'estimation.
    """

    df = matieres.copy()

    # ============================================
    # Étape 1 : consommation moyenne journalière
    # Priorité à une vraie consommation si elle existe et est renseignée,
    # sinon on ESTIME à partir du stock de sécurité
    # ============================================
    if "conso_moyenne_jour" in df.columns and (df["conso_moyenne_jour"].fillna(0) > 0).any():
        df["conso_moyenne_jour"] = df["conso_moyenne_jour"].fillna(0)
        df["conso_est_estimee"] = df["conso_moyenne_jour"] == 0
    else:
        # Estimation : le stock de sécurité couvre X jours de consommation
        df["conso_moyenne_jour"] = df["stock_securite"] / delai_couverture_securite
        # Évite une division par zéro si stock_securite = 0
        df["conso_moyenne_jour"] = df["conso_moyenne_jour"].replace(0, 0.01)
        df["conso_est_estimee"] = True

    # ============================================
    # Étape 2 : délai fournisseur
    # ============================================
    if "delai_moyen_jours" in fournisseurs.columns and len(fournisseurs) > 0:
        delai_global = fournisseurs["delai_moyen_jours"].mean()
    else:
        delai_global = 30

    df["delai_moyen_jours"] = delai_global
    df["nom_fournisseur"] = "Voir fichier fournisseurs"

    # ============================================
    # Étape 3 : couverture en jours (= jours restants estimés)
    # ============================================
    df["couverture_jours"] = (df["stock_actuel"] / df["conso_moyenne_jour"]).round(1)

    # Ratio stock conservé uniquement pour information / tri secondaire
    df["ratio_stock"] = df.apply(
        lambda ligne: ligne["stock_actuel"] / ligne["stock_securite"]
        if ligne["stock_securite"] > 0
        else 9999,
        axis=1
    )

    # ============================================
    # Étape 4 : niveau de risque basé sur les jours restants
    # ============================================
    def determiner_niveau(ligne):
        if ligne["couverture_jours"] < ligne["delai_moyen_jours"]:
            return "🔴 Élevé"
        elif ligne["couverture_jours"] < ligne["delai_moyen_jours"] * 1.5:
            return "🟠 Moyen"
        else:
            return "🟢 Normal"

    df["niveau_risque"] = df.apply(determiner_niveau, axis=1)

    # ============================================
    # Étape 5 : action recommandée
    # ============================================
    def determiner_action(ligne):
        if ligne["niveau_risque"] == "🔴 Élevé":
            return f"Commander en urgence – stock estimé à {ligne['couverture_jours']:.0f} j, délai fournisseur {ligne['delai_moyen_jours']:.0f} j"
        elif ligne["niveau_risque"] == "🟠 Moyen":
            return f"Anticiper la commande – stock estimé à {ligne['couverture_jours']:.0f} j"
        else:
            return "Aucune action nécessaire"

    df["action_recommandee"] = df.apply(determiner_action, axis=1)

    # ============================================
    # Étape 6 : quantité à commander (point de commande classique)
    # ============================================
    df["quantite_a_commander"] = (
        df["conso_moyenne_jour"] * df["delai_moyen_jours"]
        + df["stock_securite"]
        - df["stock_actuel"]
    ).clip(lower=0)

    return df


def calculer_priorites(resultats_risque, besoins):
    """
    Combine les résultats de risque par matière avec les demandes
    de production (besoins) pour calculer un score de priorité
    par demande.
    """
    from datetime import date

    df = besoins.merge(
        resultats_risque[[
            "code_matiere", "designation", "niveau_risque",
            "ratio_stock", "couverture_jours", "stock_actuel",
            "conso_moyenne_jour", "delai_moyen_jours"
        ]],
        on="code_matiere",
        how="left",
    )

    def points_risque(niveau):
        if niveau == "🔴 Élevé":
            return 50
        elif niveau == "🟠 Moyen":
            return 30
        else:
            return 10

    def points_criticite(criticite_texte):
        try:
            niveau_numerique = int(str(criticite_texte).split("(")[1].replace(")", ""))
            if niveau_numerique >= 4:
                return 30
            elif niveau_numerique == 3:
                return 20
            else:
                return 10
        except Exception:
            return 10

    def points_urgence_date(date_besoin):
        try:
            date_besoin = pd.to_datetime(date_besoin).date()
            jours_restants = (date_besoin - date.today()).days
            if jours_restants <= 3:
                return 20
            elif jours_restants <= 7:
                return 10
            else:
                return 0
        except Exception:
            return 0

    df["score_priorite"] = (
        df["niveau_risque"].apply(points_risque)
        + df["criticite"].apply(points_criticite)
        + df["date_besoin"].apply(points_urgence_date)
    )

    df = df.sort_values("score_priorite", ascending=False)

    return df