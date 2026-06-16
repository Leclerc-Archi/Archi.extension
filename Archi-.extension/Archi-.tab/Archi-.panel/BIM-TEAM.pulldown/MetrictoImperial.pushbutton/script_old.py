# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import forms

try:
    TaskDialog.Show("Debug", "Script started successfully.")
    uidoc = __revit__.ActiveUIDocument
    if uidoc is None:
        TaskDialog.Show("Erreur", "Aucun document Revit actif ouvert.")
        raise Exception("Aucun document actif")
    doc = uidoc.Document
    if doc.IsReadOnly or doc.IsFamilyDocument:
        TaskDialog.Show("Erreur", "Le document est en lecture seule ou est un document de famille.")
        raise Exception("Document non modifiable ou inapproprié")
    TaskDialog.Show("Debug", "Document accessed successfully.")
except Exception, ex:
    TaskDialog.Show("Erreur", "Impossible d'accéder au document actif. Détail : %s" % str(ex))
    raise


# ---------------- Paramètres interactifs ----------------
TARGET_SYSTEM = forms.SelectFromList.show(
    ["metric", "imperial"],
    title="Sélectionner le système d'unités",
    multiselect=False
)
if not TARGET_SYSTEM:
    raise Exception("Utilisateur a annulé la sélection")
TaskDialog.Show("Debug", "Unit system selected: %s" % TARGET_SYSTEM)

ROUND_PARAMETER_VALUES = forms.alert(
    "Voulez-vous arrondir toutes les longueurs pour éviter les fractions bizarres ?",
    yes=True, no=True
)
ROUND_DIGITS = 2
TaskDialog.Show("Debug", "Rounding enabled: %s" % str(ROUND_PARAMETER_VALUES))


# ---------------- Table de conversion échelles ----------------
SCALE_CONVERSION = {
    "metric_to_imperial": {5: 4, 10: 8, 20: 16, 25: 12, 50: 48, 75: 32, 100: 96, 200: 192},
    "imperial_to_metric": {4: 5, 8: 10, 16: 20, 12: 25, 48: 50, 32: 75, 96: 100, 192: 200}
}


# ---------------- Fonctions Debug ----------------
def debug_units(system_name):
    if system_name.lower() == "imperial":
        unitname = "Pieds / Pouces fractionnaires"
    else:
        unitname = "Millimètres"
    return unitname


def debug_round_length_parameters(doc):
    count = 0
    try:
        collector = FilteredElementCollector(doc).WhereElementIsNotElementType()
        for e in collector:
            if e is None:
                continue
            try:
                for p in e.Parameters:
                    if p is None or p.IsReadOnly or p.StorageType != StorageType.Double:
                        continue
                    try:
                        val = p.AsDouble()
                        if val is not None:
                            rounded = round(val, ROUND_DIGITS)
                            if val != rounded:
                                count += 1
                    except Exception, ex:
                        TaskDialog.Show("Avertissement", "Erreur sur le paramètre %s de l'élément %s : %s. Ignoré." % (p.Definition.Name if p.Definition else "inconnu", e.Id.IntegerValue if e.Id else "inconnu", str(ex)))
                        continue
            except Exception, ex:
                TaskDialog.Show("Avertissement", "Erreur d'accès aux paramètres de l'élément %s : %s. Ignoré." % (e.Id.IntegerValue if e.Id else "inconnu", str(ex)))
                continue
    except Exception, ex:
        TaskDialog.Show("Avertissement", "Erreur dans l'analyse des paramètres : %s" % str(ex))
    return count


def debug_view_scales(doc, system_name):
    count = 0
    try:
        views = FilteredElementCollector(doc).OfClass(View)
        for v in views:
            if v is None or v.IsTemplate:
                continue
            try:
                scale = v.Scale
                if scale is not None:
                    if system_name.lower() == "imperial":
                        target = SCALE_CONVERSION["metric_to_imperial"].get(scale, None)
                    else:
                        target = SCALE_CONVERSION["imperial_to_metric"].get(scale, None)
                    if target and scale != target:
                        count += 1
            except Exception, ex:
                TaskDialog.Show("Avertissement", "Erreur sur une vue %s : %s. Ignorée." % (v.Id.IntegerValue if v.Id else "inconnu", str(ex)))
                continue
    except Exception, ex:
        TaskDialog.Show("Avertissement", "Erreur dans l'analyse des vues : %s" % str(ex))
    return count


# ---------------- Exécution Debug ----------------
try:
    TaskDialog.Show("Debug", "Starting simulation.")
    unit_target = debug_units(TARGET_SYSTEM)
    changed = debug_round_length_parameters(doc) if ROUND_PARAMETER_VALUES else 0
    views_changed = debug_view_scales(doc, TARGET_SYSTEM)

    TaskDialog.Show(
        "Simulation conversion",
        "WARNING Aucune modification appliquée (mode debug)\n\n"
        "Unité cible : %s\n"
        "Paramètres qui seraient arrondis : %d\n"
        "Vues dont l'échelle changerait : %d" % (unit_target, changed, views_changed)
    )
except Exception, ex:
    TaskDialog.Show("Erreur Debug", "Échec de la simulation : %s" % str(ex))
