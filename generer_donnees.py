"""
Script qui génère UNIQUEMENT le fichier besoins_production.xlsx
avec des demandes de test basées sur de VRAIS codes ART
(issus de ton vrai fichier matieres.xlsx).

⚠️ Important : ce script ne touche plus à matieres.xlsx, fournisseurs.xlsx,
historique_fournisseurs.xlsx ni consommation.xlsx — ces fichiers contiennent
maintenant tes vraies données Dynamics AX, on ne veut surtout pas les écraser.
"""

import pandas as pd
from core.excel_utils import ecrire_excel_propre

# ============================================
# Table des besoins de production (données de TEST)
# Codes ART réels choisis parmi tes 110 vraies matières,
# couvrant différents niveaux de risque :
#   - ART059 : rupture totale (stock = 0)
#   - ART001, ART005 : risque élevé (ratio stock ~0.4)
#   - ART002, ART003 : risque moyen (ratio stock ~0.6)
#   - ART006 : niveau normal (ratio stock ~4.4)
# ============================================
besoins_production = pd.DataFrame({
    "code_matiere": ["ART059", "ART001", "ART005", "ART002", "ART006"],
    "ligne_production": ["Ligne A", "Ligne B", "Ligne A", "Ligne C", "Ligne B"],
    "quantite_demandee": [50, 20, 15, 10, 30],
    "date_besoin": ["2026-07-03", "2026-07-05", "2026-07-08", "2026-07-15", "2026-07-20"],
    "criticite": ["Haute (5)", "Haute (4)", "Moyenne (3)", "Normale (2)", "Basse (1)"],
    "commentaire": ["", "", "", "", ""],
    "statut": ["À traiter", "À traiter", "À traiter", "À traiter", "À traiter"],
})

# ============================================
# Écriture du fichier, avec mise en forme automatique
# ============================================
ecrire_excel_propre(besoins_production, "data/besoins_production.xlsx")

print("Le fichier besoins_production.xlsx a été créé avec des codes ART réels.")