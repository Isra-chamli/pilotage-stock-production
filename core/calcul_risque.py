"""
Logique métier : calcul du risque de rupture de stock
Adapté aux vraies données Maklada :
- Pas de consommation historique disponible pour l'instant
  → risque calculé sur le ratio stock_actuel / stock_securite
- Pas de liaison code_matiere dans le fichier fournisseurs
  → délai moyen global calculé depuis l'historique des commandes
"""

import pandas as pd


def calculer_risque(matieres, consommation, fournisseurs):
    """
    Calcule le niveau de risque de rupture pour chaque matière.
    
    Mode actuel (sans consommation historique) :
    - Risque basé sur le ratio stock_actuel / stock_securite
    - Délai fournisseur = délai moyen global de tous les fournisseurs
    
    Évolution future (quand consommation disponible) :
    - Ajouter conso_moyenne_jour dans matieres.xlsx
    - La logique bascule automatiquement en mode "couverture en jours"
    """

    # On travaille directement sur les matières
    df = matieres.copy()

    # ============================================
    # Étape 1 : consommation moyenne
    # Si la colonne existe et contient des valeurs > 0, on l'utilise
    # Sinon, on reste en mode "ratio de stock"
    # ============================================
    if "conso_moyenne_jour" not in df.columns:
        df["conso_moyenne_jour"] = 0
    else:
        df["conso_moyenne_jour"] = df["conso_moyenne_jour"].fillna(0)

    # ============================================
    # Étape 2 : délai fournisseur
    # On calcule le délai moyen global depuis le fichier fournisseurs
    # (pas de liaison par code_matiere dans les vraies données)
    # ============================================
    if "delai_moyen_jours" in fournisseurs.columns and len(fournisseurs) > 0:
        delai_global = fournisseurs["delai_moyen_jours"].mean()
    else:
        delai_global = 30  # valeur par défaut prudente si pas de données

    df["delai_moyen_jours"] = delai_global
    df["nom_fournisseur"] = "Voir fichier fournisseurs"

    # ============================================
    # Étape 3 : calcul du ratio de stock et couverture
    # ============================================
    # Ratio stock actuel / stock de sécurité
    df["ratio_stock"] = df.apply(
        lambda ligne: ligne["stock_actuel"] / ligne["stock_securite"]
        if ligne["stock_securite"] > 0
        else 9999,
        axis=1
    )

    # Couverture en jours (disponible seulement si conso > 0)
    df["couverture_jours"] = df.apply(
        lambda ligne: ligne["stock_actuel"] / ligne["conso_moyenne_jour"]
        if ligne["conso_moyenne_jour"] > 0
        else 9999,
        axis=1
    )

    # ============================================
    # Étape 4 : niveau de risque
    # Mode principal : ratio de stock (toujours disponible)
    # Mode secondaire : couverture en jours (si conso disponible)
    # ============================================
    def determiner_niveau(ligne):
        # Si on a des données de consommation, on utilise la couverture en jours
        if ligne["conso_moyenne_jour"] > 0:
            if ligne["couverture_jours"] < ligne["delai_moyen_jours"]:
                return "🔴 Élevé"
            elif ligne["couverture_jours"] < ligne["delai_moyen_jours"] * 1.5:
                return "🟠 Moyen"
            else:
                return "🟢 Normal"
        # Sinon, on utilise le ratio stock actuel / stock de sécurité
        else:
            if ligne["ratio_stock"] < 0.5:
                return "🔴 Élevé"
            elif ligne["ratio_stock"] < 1.0:
                return "🟠 Moyen"
            else:
                return "🟢 Normal"

    df["niveau_risque"] = df.apply(determiner_niveau, axis=1)

    # ============================================
    # Étape 5 : action recommandée
    # ============================================
    def determiner_action(ligne):
        if ligne["niveau_risque"] == "🔴 Élevé":
            return "Commander en urgence – stock inférieur à 50% du seuil de sécurité"
        elif ligne["niveau_risque"] == "🟠 Moyen":
            return "Anticiper la commande – stock entre 50% et 100% du seuil de sécurité"
        else:
            return "Aucune action nécessaire"

    df["action_recommandee"] = df.apply(determiner_action, axis=1)

    # ============================================
    # Étape 6 : quantité à commander
    # Si conso disponible : formule du point de commande classique
    # Sinon : quantité pour revenir au double du stock de sécurité
    # ============================================
    def calculer_quantite(ligne):
        if ligne["conso_moyenne_jour"] > 0:
            qte = (
                ligne["conso_moyenne_jour"] * ligne["delai_moyen_jours"]
                + ligne["stock_securite"]
                - ligne["stock_actuel"]
            )
        else:
            # On recommande de commander assez pour revenir
            # à 2x le stock de sécurité (règle prudente)
            qte = (2 * ligne["stock_securite"]) - ligne["stock_actuel"]
        return max(0, qte)

    df["quantite_a_commander"] = df.apply(calculer_quantite, axis=1)

    return df


def calculer_priorites(resultats_risque, besoins):
    """
    Combine les résultats de risque par matière avec les demandes
    de production (besoins) pour calculer un score de priorité
    par demande.
    """
    from datetime import date

    # On fusionne chaque demande avec les infos de risque de sa matière
    df = besoins.merge(
        resultats_risque[[
            "code_matiere", "designation", "niveau_risque",
            "ratio_stock", "couverture_jours", "stock_actuel",
            "conso_moyenne_jour", "delai_moyen_jours"
        ]],
        on="code_matiere",
        how="left",
    )

    # ---- Points liés au risque de la matière ----
    def points_risque(niveau):
        if niveau == "🔴 Élevé":
            return 50
        elif niveau == "🟠 Moyen":
            return 30
        else:
            return 10

    # ---- Points liés à la criticité production ----
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
            return 10  # valeur par défaut si le format est inattendu

    # ---- Points liés à l'urgence de la date de besoin ----
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