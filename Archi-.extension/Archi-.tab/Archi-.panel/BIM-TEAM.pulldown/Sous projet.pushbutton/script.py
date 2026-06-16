# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import Workset, WorksetKind, Transaction, FilteredWorksetCollector
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, script, forms

import csv

# Fonction pour lire les noms depuis un fichier CSV (colonne A)
def read_worksets_from_csv(filepath):
    try:
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            return [row[0].strip() for row in reader if row and row[0].strip()]
    except Exception as e:
        TaskDialog.Show("Erreur", "Impossible de lire le fichier CSV :\n\n{}".format(e))
        script.exit()

# Liste codée en dur (par défaut)
default_workset_names = [
    "00_AXES_NIVEAUX",
    "A_A10_FONDATIONS",
    "A_B10_SUPERSTRUCTURE",
    "A_B20_ENVELOPPE",
    "A_C10_CONSTRUCTION_INT",
    "A_C20_ESCALIERS",
    "A_C30_FINITIONS_INT",
    "A_D10_MOYENS_TRANSPORT",
    "A_E10_EQUIPEMENT",
    "A_E20_MOBILIER_FIXE",
    "A_E20_AMEUBLEMENT_MOBILE",
    "M_D20_PLOMBERIE",
    "M_D30_CVCA",
    "M_D40_PROTECTION_INCENDIE",
    "E_D50_ÉLECTRICITÉ", 
    "G_SITE",
    "G_PIECES_SURFACES",
    "G_PLAN_REFERENCES",
    "G_VOLUME_CONCEPTION",
    "G_ZONE_DEFINITION"
]

# Choix de la source
APP_TITLE = "BIM-TEAM — Gestionnaire de Sous-projets"

choice = forms.alert(
    "Quelle source veux-tu utiliser pour créer les sous-projets ?",
    options=["Sous-projets Archi-", "Fichier CSV"],
    title=APP_TITLE
)

if choice == "Fichier CSV":
    csv_path = forms.pick_file(file_ext='csv', title='Sélectionne un fichier CSV')
    if not csv_path:
        TaskDialog.Show("Annulé", "Aucun fichier sélectionné. Script interrompu.")
        script.exit()
    workset_names = read_worksets_from_csv(csv_path)
else:
    workset_names = default_workset_names

doc = revit.doc

if not doc.IsWorkshared:
    TaskDialog.Show("Erreur", "Le projet n'est pas en mode collaboratif. Active le partage de projet avant de créer des sous-projets.")
    script.exit()

existing_names = [ws.Name for ws in FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset)]
created = []

t = Transaction(doc, "Créer des sous-projets")
try:
    t.Start()
    for name in workset_names:
        if name and name not in existing_names:
            Workset.Create(doc, name)
            created.append(name)
    t.Commit()
except Exception as e:
    t.RollBack()
    TaskDialog.Show("Erreur", "Une erreur est survenue :\n\n{}".format(e))
    script.exit()

if created:
    TaskDialog.Show("Succès", "Sous-projets créés :\n\n" + "\n".join(created))
else:
    TaskDialog.Show("Info", "Tous les sous-projets existent déjà.")
