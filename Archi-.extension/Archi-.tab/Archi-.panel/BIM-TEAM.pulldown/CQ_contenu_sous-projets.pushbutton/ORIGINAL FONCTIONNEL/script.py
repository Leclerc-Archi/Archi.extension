# coding: utf-8
import clr
import sys

clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System")

from pyrevit import revit
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List
from collections import defaultdict

# Obtenir le document actif via pyRevit
doc = revit.doc

# Vérification du document
if not doc:
    TaskDialog.Show("Erreur", "Aucun document Revit actif. Veuillez ouvrir un projet Revit et réessayer.")
    sys.exit()

# Dictionnaire de correspondance
mapping = {
    "Walls": [
        ("m", "A_B20_ENVELOPPE_EXT"),
        ("p", "A_B20_ENVELOPPE_EXT"),
        ("cp", "A_C30_FINITIONS_INT")
    ],
    "Stairs": [
        ("", "A_C20_ESCALIERS")
    ],
    "Railings": [
        ("", "A_C20_ESCALIERS")
    ],
    "Furniture": [
        ("", "A_E20_MOBILIERS")
    ]
}

# Correspondance des catégories Revit
category_map = {
    "Walls": BuiltInCategory.OST_Walls,
    "Stairs": BuiltInCategory.OST_Stairs,
    "Railings": BuiltInCategory.OST_StairsRailing,
    "Furniture": BuiltInCategory.OST_Furniture
}

def get_or_create_workset(doc, name):
    try:
        worksets = FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset).ToWorksets()
        for ws in worksets:
            if ws.Name == name:
                return ws.Id
        return Workset.Create(doc, name).Id
    except Exception as e:
        raise Exception("Erreur lors de la création du sous-projet '{}': {}".format(name, str(e)))

def find_elements_by_category(doc, category):
    try:
        return FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType().ToElements()
    except Exception as e:
        raise Exception("Erreur lors de la collecte des éléments pour la catégorie : {}".format(str(e)))

def get_element_prefix_and_type(elem, category_name):
    try:
        type_elem = doc.GetElement(elem.GetTypeId())
        if type_elem and type_elem.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM):
            type_name = type_elem.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
            if type_name and len(type_name) > 0:
                if category_name == "Walls":
                    if len(type_name) >= 2 and type_name[:2].lower() == "cp":
                        prefix = type_name[:2]
                        return prefix.lower(), prefix.upper(), type_name
                    prefix = type_name[0]
                    return prefix.lower(), prefix.upper(), type_name
                else:
                    return "", "", type_name
    except:
        pass
    return "", "", "Inconnu"

t = Transaction(doc, "Affecter les éléments aux sous-projets")
try:
    t.Start()
except Exception as e:
    TaskDialog.Show("Erreur", "Impossible de démarrer la transaction : {}. Vérifiez que le document est modifiable.".format(str(e)))
    sys.exit()

report_by_workset = defaultdict(list)
non_assigned = []

try:
    for category_name, mappings in mapping.items():
        if category_name not in category_map:
            report_by_workset["Non affectés"].append("- {} : Catégorie non reconnue".format(category_name))
            continue

        elements = find_elements_by_category(doc, category_map[category_name])
        
        if not elements:
            report_by_workset["Non affectés"].append("- {} : Aucun élément trouvé".format(category_name))
            continue

        for elem in elements:
            prefix_lower, prefix_upper, type_name = get_element_prefix_and_type(elem, category_name)
            workset_name = None
            for map_prefix, map_workset in mappings:
                if prefix_lower == map_prefix or (map_prefix == "" and prefix_lower == ""):
                    workset_name = map_workset
                    break
            
            if not workset_name:
                if category_name == "Walls":
                    non_assigned.append("- {} (type: {}, préfixe: {})".format(category_name, type_name, prefix_upper))
                else:
                    non_assigned.append("- {} (type: {})".format(category_name, type_name))
                continue

            workset_id = get_or_create_workset(doc, workset_name)
            param = elem.get_Parameter(BuiltInParameter.ELEM_PARTITION_PARAM)
            if param and not param.IsReadOnly:
                param.Set(workset_id.IntegerValue)
                if category_name == "Walls":
                    report_by_workset[workset_name].append("- {} (type: {}, préfixe: {})".format(category_name, type_name, prefix_upper))
                else:
                    report_by_workset[workset_name].append("- {} (type: {})".format(category_name, type_name))
            else:
                if category_name == "Walls":
                    non_assigned.append("- {} (type: {}, préfixe: {}) : Paramètre de sous-projet non modifiable".format(category_name, type_name, prefix_upper))
                else:
                    non_assigned.append("- {} (type: {}) : Paramètre de sous-projet non modifiable".format(category_name, type_name))

except Exception as e:
    TaskDialog.Show("Erreur", "Une erreur s'est produite : {}".format(str(e)))
    t.RollBack()
else:
    t.Commit()

report_lines = []
for workset_name, items in report_by_workset.items():
    report_lines.append("{} :".format(workset_name))
    report_lines.extend(items)

if non_assigned:
    report_lines.append("Non affectés :")
    report_lines.extend(non_assigned)

if report_lines:
    TaskDialog.Show("Résumé des affectations", "\n".join(report_lines))
else:
    TaskDialog.Show("Résumé des affectations", "Aucun élément trouvé pour les catégories spécifiées.")
