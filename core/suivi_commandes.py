"""
Suivi du cycle de vie d'une commande déclenchée depuis une alerte de rupture.

Statuts possibles, dans l'ordre :
    "Commandé" -> "En cours de livraison" -> "Livré"

Tant qu'une matière n'est pas au statut "Livré", elle reste visible sur la
page Alertes (avec le bouton correspondant à l'étape suivante).
Dès qu'elle passe à "Livré", elle disparaît de la page Alertes et
n'apparaît plus que dans l'Historique des commandes.

Toutes les commandes (en cours et livrées) sont conservées dans
data/suivi_commandes.xlsx pour garder une trace complète.
"""

import pandas as pd
from datetime import date
import os

from core.excel_utils import ecrire_excel_propre

CHEMIN_FICHIER = "data/suivi_commandes.xlsx"

COLONNES = [
    "code_matiere",
    "designation",
    "statut",
    "quantite_a_commander",
    "nom_fournisseur",
    "date_creation",
    "date_commande",
    "date_debut_livraison",
    "date_livraison",
]


def charger_suivi():
    """Charge le fichier de suivi des commandes, ou renvoie un tableau
    vide avec les bonnes colonnes s'il n'existe pas encore."""
    if os.path.exists(CHEMIN_FICHIER):
        df = pd.read_excel(CHEMIN_FICHIER)
        for colonne in COLONNES:
            if colonne not in df.columns:
                df[colonne] = pd.NA
        df = df[COLONNES]
    else:
        df = pd.DataFrame(columns=COLONNES)

    # Les colonnes de date peuvent être rechargées par pandas en dtype
    # float64 quand elles ne contiennent que des NaN (aucune commande
    # livrée pour l'instant, par exemple). Les pandas récents (2.x/3.x)
    # refusent alors d'y écrire une chaîne de caractères avec .loc et
    # lèvent un TypeError. On force ces colonnes en dtype "object" pour
    # pouvoir toujours y stocker une date au format texte.
    colonnes_dates = ["date_creation", "date_commande", "date_debut_livraison", "date_livraison"]
    for colonne in colonnes_dates:
        df[colonne] = df[colonne].astype("object")

    return df


def sauvegarder_suivi(suivi):
    ecrire_excel_propre(suivi, CHEMIN_FICHIER)


def _derniere_ligne_index(suivi, code_matiere):
    """Index de la commande la plus récente pour cette matière, ou None
    si aucune commande n'a jamais été créée pour elle."""
    lignes = suivi[suivi["code_matiere"] == code_matiere]
    if len(lignes) == 0:
        return None
    return lignes.index[-1]


def statut_actif(suivi, code_matiere):
    """Statut de la commande EN COURS pour cette matière :
    None si aucune commande n'a été créée, ou si la dernière commande
    créée est déjà "Livrée" (dans ce cas la matière est considérée
    comme sans commande active — un nouveau cycle peut redémarrer si
    une nouvelle alerte apparaît plus tard)."""
    index = _derniere_ligne_index(suivi, code_matiere)
    if index is None:
        return None
    statut = suivi.loc[index, "statut"]
    return None if statut == "Livré" else statut


def est_traitee(suivi, code_matiere):
    """True si la dernière commande connue pour cette matière est
    déjà marquée comme livrée : dans ce cas on ne la ré-affiche plus
    sur la page Alertes tant qu'aucune nouvelle commande n'est créée."""
    index = _derniere_ligne_index(suivi, code_matiere)
    if index is None:
        return False
    return suivi.loc[index, "statut"] == "Livré"


def creer_commande(suivi, code_matiere, designation, quantite, nom_fournisseur):
    """Crée une nouvelle commande au statut "Commandé" pour cette matière."""
    nouvelle_ligne = pd.DataFrame([{
        "code_matiere": code_matiere,
        "designation": designation,
        "statut": "Commandé",
        "quantite_a_commander": quantite,
        "nom_fournisseur": nom_fournisseur,
        "date_creation": date.today().isoformat(),
        "date_commande": date.today().isoformat(),
        "date_debut_livraison": pd.NA,
        "date_livraison": pd.NA,
    }])
    suivi = pd.concat([suivi, nouvelle_ligne], ignore_index=True)
    sauvegarder_suivi(suivi)
    return suivi


def avancer_statut(suivi, code_matiere):
    """Fait progresser la commande active de cette matière à l'étape
    suivante : Commandé -> En cours de livraison -> Livré."""
    index = _derniere_ligne_index(suivi, code_matiere)
    if index is None:
        return suivi

    statut_actuel = suivi.loc[index, "statut"]

    # Sécurité supplémentaire : on force le dtype "object" juste avant
    # d'écrire, au cas où le DataFrame recevrait la colonne dans un état
    # numérique (toutes les valeurs encore NaN) d'une façon qu'on
    # n'aurait pas anticipée dans charger_suivi().
    suivi["date_debut_livraison"] = suivi["date_debut_livraison"].astype("object")
    suivi["date_livraison"] = suivi["date_livraison"].astype("object")

    if statut_actuel == "Commandé":
        suivi.loc[index, "statut"] = "En cours de livraison"
        suivi.loc[index, "date_debut_livraison"] = date.today().isoformat()
    elif statut_actuel == "En cours de livraison":
        suivi.loc[index, "statut"] = "Livré"
        suivi.loc[index, "date_livraison"] = date.today().isoformat()

    sauvegarder_suivi(suivi)
    return suivi