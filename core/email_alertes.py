"""
Module d'envoi d'emails d'alerte de rupture de stock.
Utilise Gmail via SMTP avec App Password (stocké dans st.secrets).
"""

import smtplib
import streamlit as st
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date


# ============================================
# Configuration email — lue depuis .streamlit/secrets.toml
# (jamais de mot de passe écrit en dur dans le code)
# ============================================
EMAIL_EXPEDITEUR = st.secrets["email"]["smtp_user"]
APP_PASSWORD = st.secrets["email"]["smtp_password"]

# Destinataires — à modifier avec les vrais emails
DESTINATAIRES = [
    "chamliisra622@gmail.com",   # à remplacer
    "wezzine@maklada.com",              # à remplacer
]


def envoyer_alerte_rupture(alertes_df):
    """
    Envoie un email de résumé des alertes de rupture.
    alertes_df : DataFrame contenant les matières en alerte
    """
    if len(alertes_df) == 0:
        return False, "Aucune alerte à envoyer."

    # ============================================
    # Construction du contenu HTML de l'email
    # ============================================
    aujourd_hui = date.today().strftime("%d/%m/%Y")

    lignes_tableau = ""
    for _, ligne in alertes_df.iterrows():
        couleur = "#ff4444" if "Élevé" in str(ligne.get("niveau_risque", "")) else "#ff8800"
        lignes_tableau += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{ligne.get('code_matiere', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{ligne.get('designation', '')}</td>
            <td style="padding:8px; border:1px solid #ddd; color:{couleur}; font-weight:bold;">
                {ligne.get('niveau_risque', '')}
            </td>
            <td style="padding:8px; border:1px solid #ddd;">{ligne.get('stock_actuel', '')}</td>
            <td style="padding:8px; border:1px solid #ddd;">{ligne.get('stock_securite', '')}</td>
            <td style="padding:8px; border:1px solid #ddd; font-weight:bold;">
                {ligne.get('quantite_a_commander', 0):.0f}
            </td>
            <td style="padding:8px; border:1px solid #ddd;">{ligne.get('nom_fournisseur', '')}</td>
        </tr>
        """

    contenu_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background-color: #2F5496; padding: 20px; border-radius: 8px;">
            <h2 style="color: white; margin: 0;">
                🏭 Pilotage Intelligent du Magasin — Maklada
            </h2>
            <p style="color: #ccc; margin: 5px 0 0 0;">
                Rapport d'alertes de rupture du {aujourd_hui}
            </p>
        </div>

        <div style="padding: 20px;">
            <div style="background-color: #fff3cd; border: 1px solid #ffc107;
                        padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                ⚠️ <strong>{len(alertes_df)} matière(s)</strong> nécessitent
                une attention immédiate.
            </div>

            <table style="width:100%; border-collapse:collapse; font-size:13px;">
                <thead>
                    <tr style="background-color: #2F5496; color: white;">
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Code</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Désignation</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Risque</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Stock actuel</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Stock sécurité</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Qté à commander</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Fournisseur</th>
                    </tr>
                </thead>
                <tbody>
                    {lignes_tableau}
                </tbody>
            </table>

            <p style="margin-top: 20px; color: #666; font-size: 12px;">
                Cet email a été généré automatiquement par l'application
                Pilotage Intelligent du Magasin — Maklada.<br>
                Ne pas répondre à cet email.
            </p>
        </div>
    </body>
    </html>
    """

    # ============================================
    # Envoi de l'email
    # ============================================
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Alerte rupture stock — {len(alertes_df)} matière(s) — {aujourd_hui}"
        msg["From"] = EMAIL_EXPEDITEUR
        msg["To"] = ", ".join(DESTINATAIRES)

        msg.attach(MIMEText(contenu_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
            serveur.login(EMAIL_EXPEDITEUR, APP_PASSWORD.replace(" ", ""))
            serveur.sendmail(EMAIL_EXPEDITEUR, DESTINATAIRES, msg.as_string())

        return True, f"Email envoyé avec succès à {len(DESTINATAIRES)} destinataire(s)."

    except Exception as erreur:
        return False, f"Erreur lors de l'envoi : {erreur}"