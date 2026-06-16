# -*- coding: utf-8 -*-
from pyrevit import revit, DB
from pyrevit import script
from Autodesk.Revit.UI import TaskDialog

doc = revit.doc

if doc is None:
    TaskDialog.Show("Erreur", "Aucun document Revit actif. Veuillez ouvrir un projet.")
    raise Exception("Document Revit non actif.")

sheets = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).ToElements()

index_param_exists = any(
    sheet.LookupParameter("FEUILLES_INDEX") is not None for sheet in sheets
)

if not index_param_exists:
    TaskDialog.Show("Erreur", "Le paramètre 'FEUILLES_INDEX' est introuvable sur les feuilles.")
    raise Exception("Paramètre 'FEUILLES_INDEX' manquant.")

# Préparer des listes de rapport
a000_sheets = []
a_range_sheets = []
ad_sheets = []
a90plus_sheets = []

with revit.Transaction("Mettre à jour le paramètre FEUILLES_INDEX"):
    for sheet in sheets:
        param = sheet.LookupParameter("FEUILLES_INDEX")
        if not param:
            continue

        number = sheet.SheetNumber.upper().strip()

        # Cas A000
        if number == "A000":
            param.Set(0)
            a000_sheets.append(number)

        # Cas A001 à A089 ou A090+
        elif number.startswith("A") and len(number) == 4:
            try:
                num = int(number[1:])  # extrait 001 à 999
                if 1 <= num <= 89:
                    param.Set(1)
                    a_range_sheets.append(number)
                    continue
                elif num >= 90:
                    param.Set(3)
                    a90plus_sheets.append(number)
                    continue
            except:
                pass

        # Cas AD*
        elif number.startswith("AD"):
            param.Set(2)
            ad_sheets.append(number)

        # Sinon : on ignore

# Construction du message final avec tri uniquement pour l'affichage
message = "Paramètre 'FEUILLES_INDEX' mis à jour.\n\n"

message += "A000 (index 0) :\n"
if a000_sheets:
    for s in sorted(a000_sheets):
        message += "  - {}\n".format(s)
else:
    message += "  - Aucune\n"

message += "A001-A089 (index 1) :\n"
if a_range_sheets:
    for s in sorted(a_range_sheets):
        message += "  - {}\n".format(s)
else:
    message += "  - Aucune\n"

message += "Feuilles AD* (index 2) :\n"
if ad_sheets:
    for s in sorted(ad_sheets):
        message += "  - {}\n".format(s)
else:
    message += "  - Aucune\n"

message += "A090 et plus (index 3) :\n"
if a90plus_sheets:
    for s in sorted(a90plus_sheets):
        message += "  - {}\n".format(s)
else:
    message += "  - Aucune\n"

# Afficher dans une boîte de dialogue
TaskDialog.Show("Résumé des mises à jour", message)
