"""
Fonctions pour charger les fichiers Excel de façon sécurisée,
avec des messages d'erreur clairs si un fichier est manquant ou corrompu.
"""

import pandas as pd
import streamlit as st


def charger_excel(chemin_fichier, nom_affiche=None):
    """
    Charge un fichier Excel en gérant les erreurs courantes.
    Si le fichier est introuvable ou illisible, affiche un message
    clair dans l'application au lieu de faire planter le programme.
    """
    nom_affiche = nom_affiche or chemin_fichier

    try:
        return pd.read_excel(chemin_fichier)
    except FileNotFoundError:
        st.error(f"Fichier introuvable : {nom_affiche}. Vérifiez qu'il existe bien dans le dossier data/.")
        st.stop()
    except Exception as erreur:
        st.error(f"Erreur lors de la lecture de {nom_affiche} : {erreur}")
        st.stop()