# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import FilteredElementCollector, RevitLinkInstance, ImportInstance, Transaction, Grid, Level
from pyrevit import revit, script

# Configuration de la console
output = script.get_output()
doc = revit.doc

# 1. Collecte des éléments (Liens + Axes + Niveaux)
revit_links = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
dwg_links = FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()
grids = FilteredElementCollector(doc).OfClass(Grid).ToElements()
levels = FilteredElementCollector(doc).OfClass(Level).ToElements()

# Fusion de toutes les listes
all_elements = list(revit_links) + list(dwg_links) + list(grids) + list(levels)

# 2. Exécution
t = Transaction(doc, "Verrouiller Liens, Axes et Niveaux")
t.Start()

count = 0
print("--- Analyse et Verrouillage ---")

for item in all_elements:
    try:
        # --- RÉCUPÉRATION DU NOM SELON LE TYPE ---
        if isinstance(item, RevitLinkInstance):
            name = "Lien Revit: " + item.Name
        elif isinstance(item, ImportInstance):
            name = "Lien CAD: " + item.Category.Name
        elif isinstance(item, Grid):
            name = "Axe: " + item.Name
        elif isinstance(item, Level):
            name = "Niveau: " + item.Name
        else:
            name = "Élément inconnu"

        # --- VERROUILLAGE ---
        if not item.Pinned:
            item.Pinned = True
            print("[OK] Verrouillé : {}".format(name))
            count += 1
        # Optionnel : décommenter la ligne suivante pour voir les éléments déjà verrouillés
        # else:
        #     print("[INFO] Déjà verrouillé : {}".format(name))
            
    except Exception as e:
        print("[ERREUR] Impossible de traiter {} : {}".format(name, str(e)))

t.Commit()

print("\nTerminé : {} éléments verrouillés au total.".format(count))