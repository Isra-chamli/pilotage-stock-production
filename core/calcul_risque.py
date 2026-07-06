"""
Logique métier : calcul du risque de rupture de stock
Adapté aux vraies données Maklada :
- Pas de consommation historique disponible
  → consommation journalière ESTIMÉE à partir du stock de sécurité,
    en supposant qu'il couvre un nombre de jours donné (paramétrable)
- Liaison matiere -> fournisseur réel disponible dans
  data/liaison_matiere_fournisseur.xlsx
  → si une matière y est renseignée, on utilise son vrai fournisseur
    et son vrai délai ; sinon on retombe sur le délai moyen global
"""

import pandas as pd


def calculer_risque(matieres, consommation, fournisseurs, liaison=None, delai_couverture_securite=15):
    """
    Calcule le niveau de risque de rupture pour chaque matière.

    liaison : DataFrame optionnel avec colonnes code_matiere, nom_fournisseur
    permettant de lier chaque matière à son fournisseur réel.
    Si absent ou non renseigné pour une matière, on retombe sur le
    délai moyen global.

    delai_couverture_securite : hypothèse (en jours) sur le nombre de jours
    que le stock de sécurité est censé couvrir. Sert à estimer une
    consommation journalière en l'absence d'historique réel.
    """

    df = matieres.copy()

    # ============================================
    # Étape 1 : consommation moyenne journalière
    # ============================================
    if "conso_moyenne_jour" in df.columns and (df["conso_moyenne_jour"].fillna(0) > 0).any():
        df["conso_moyenne_jour"] = df["conso_moyenne_jour"].fillna(0)
        df["conso_est_estimee"] = df["conso_moyenne_jour"] == 0
    else:
        df["conso_moyenne_jour"] = df["stock_securite"] / delai_couverture_securite
        df["conso_moyenne_jour"] = df["conso_moyenne_jour"].replace(0, 0.01)
        df["conso_est_estimee"] = True

    # ============================================
    # Étape 2 : délai fournisseur
    # Priorité au fournisseur réel (via liaison), sinon délai global
    # ============================================
    if "delai_moyen_jours" in fournisseurs.columns and len(fournisseurs) > 0:
        delai_global = fournisseurs["delai_moyen_jours"].mean()
    else:
        delai_global = 30

    df["delai_moyen_jours"] = delai_global
    df["nom_fournisseur"] = "Non identifié (délai moyen global)"
    df["fournisseur_identifie"] = False

    if liaison is not None and len(liaison) > 0 and "nom_fournisseur" in liaison.columns:
        liaison_valide = liaison.dropna(subset=["nom_fournisseur"]).copy()
        liaison_valide["nom_fournisseur"] = liaison_valide["nom_fournisseur"].astype(str).str.strip()
        liaison_valide = liaison_valide[liaison_valide["nom_fournisseur"] != ""]

        if len(liaison_valide) > 0:
            liaison_avec_delai = liaison_valide.merge(
                fournisseurs[["nom_fournisseur", "delai_moyen_jours"]],
                on="nom_fournisseur",
                how="left",
            )

            df = df.merge(
                liaison_avec_delai[["code_matiere", "nom_fournisseur", "delai_moyen_jours"]],
                on="code_matiere",
                how="left",
                suffixes=("", "_reel"),
            )

            a_un_fournisseur = df["nom_fournisseur_reel"].notna()
            df.loc[a_un_fournisseur, "nom_fournisseur"] = df.loc[a_un_fournisseur, "nom_fournisseur_reel"]
            df.loc[a_un_fournisseur, "delai_moyen_jours"] = df.loc[a_un_fournisseur, "delai_moyen_jours_reel"]
            df.loc[a_un_fournisseur, "fournisseur_identifie"] = True

            df = df.drop(columns=["nom_fournisseur_reel", "delai_moyen_jours_reel"])

    # ============================================
    # Étape 3 : couverture en jours (= jours restants estimés)
    # ============================================
    df["couverture_jours"] = (df["stock_actuel"] / df["conso_moyenne_jour"]).round(1)

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