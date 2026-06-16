# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from pyrevit import forms

# Initialisation du document
try:
    uidoc = __revit__.ActiveUIDocument
    if uidoc is None:
        TaskDialog.Show("Erreur", "Aucun document Revit actif ouvert.")
        raise Exception("Aucun document actif")
    doc = uidoc.Document
    if doc.IsReadOnly or doc.IsFamilyDocument:
        TaskDialog.Show("Erreur", "Le document est en lecture seule ou est un document de famille.")
        raise Exception("Document non modifiable ou inapproprié")
except Exception as ex:
    TaskDialog.Show("Erreur", "Impossible d'accéder au document actif. Détail : %s" % str(ex))
    raise

# ---------------- Paramètres interactifs ----------------
TARGET_SYSTEM = forms.SelectFromList.show(
    ["metric", "imperial"],
    title="Sélectionner le système d'unités",
    multiselect=False
)
if not TARGET_SYSTEM:
    TaskDialog.Show("Erreur", "Utilisateur a annulé la sélection")
    raise Exception("Utilisateur a annulé la sélection")

ROUND_PARAMETER_VALUES = forms.alert(
    "Voulez-vous arrondir toutes les longueurs pour éviter les fractions bizarres ?",
    yes=True, no=True
)
ROUND_DIGITS = 2

# Demander si l'utilisateur veut modifier les gabarits de vue
MODIFY_TEMPLATES = forms.alert(
    "Certaines vues peuvent être contrôlées par des gabarits de vue, ce qui empêche la modification de l'échelle.\n"
    "Voulez-vous modifier les échelles des gabarits de vue associés ?",
    yes=True, no=True
)

# ---------------- Table de conversion échelles ----------------
SCALE_CONVERSION = {
    "metric_to_imperial": {5: 4, 10: 8, 20: 16, 24: 19, 25: 12, 50: 48, 75: 32, 100: 96, 200: 192},  # Ajout de 24:19 (approximation pour 1:24)
    "imperial_to_metric": {4: 5, 8: 10, 16: 20, 19: 24, 12: 25, 48: 50, 32: 75, 96: 100, 192: 200}   # Ajout de 19:24
}

# ---------------- Fonctions ----------------
def get_unit_name(system_name):
    """Retourne le nom de l'unité pour le système sélectionné."""
    return "Pieds / Pouces fractionnaires" if system_name.lower() == "imperial" else "Millimètres"

def round_length_parameters(doc):
    """Arrondit les paramètres de longueur des éléments et retourne un résumé."""
    count_success = 0
    count_failed = 0
    failed_details = []
    
    t = Transaction(doc, "Arrondir les paramètres de longueur")
    t.Start()
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
                                p.Set(rounded)
                                count_success += 1
                    except Exception as ex:
                        count_failed += 1
                        failed_details.append(
                            "Paramètre %s de l'élément %s non arrondi : %s" % 
                            (p.Definition.Name if p.Definition else "inconnu", e.Id.IntegerValue, str(ex))
                        )
            except Exception as ex:
                count_failed += 1
                failed_details.append(
                    "Erreur d'accès aux paramètres de l'élément %s : %s" % 
                    (e.Id.IntegerValue if e.Id else "inconnu", str(ex))
                )
        t.Commit()
    except Exception as ex:
        t.RollBack()
        failed_details.append("Erreur lors de l'arrondi des paramètres : %s" % str(ex))
        count_failed += 1
    
    return {
        "success": count_success,
        "failed": count_failed,
        "details": failed_details
    }

def update_view_scales(doc, system_name, modify_templates):
    """Met à jour les échelles des vues et des gabarits de vue, retourne un résumé."""
    count_success = 0
    count_failed = 0
    failed_details = []
    templates_modified = {}
    
    t = Transaction(doc, "Mettre à jour les échelles des vues et gabarits")
    t.Start()
    try:
        views = FilteredElementCollector(doc).OfClass(View)
        for v in views:
            if v is None or v.IsTemplate or v.ViewType in [ViewType.Legend, ViewType.Schedule, ViewType.SystemBrowser, ViewType.ProjectBrowser]:
                continue
            try:
                scale = v.Scale
                if scale is not None:
                    scale_param = v.get_Parameter(BuiltInParameter.VIEW_SCALE)
                    view_template = v.get_Parameter(BuiltInParameter.VIEW_TEMPLATE).AsElementId()
                    template_name = "Aucun" if view_template.IntegerValue == -1 else doc.GetElement(view_template).Name
                    
                    if scale_param and not scale_param.IsReadOnly:
                        # Cas 1 : Le paramètre d'échelle est modifiable directement
                        if system_name.lower() == "imperial":
                            target = SCALE_CONVERSION["metric_to_imperial"].get(scale, None)
                        else:
                            target = SCALE_CONVERSION["imperial_to_metric"].get(scale, None)
                        if target and scale != target:
                            scale_param.Set(target)
                            count_success += 1
                        elif not target:
                            count_failed += 1
                            failed_details.append(
                                "Échelle %s de la vue %s non modifiée : échelle non trouvée dans la table de conversion" % 
                                (scale, v.Name if v.Name else v.Id.IntegerValue)
                            )
                    else:
                        # Cas 2 : Le paramètre est en lecture seule
                        count_failed += 1
                        # Vérifier si c'est une vue dépendante
                        is_dependent = v.IsDependent
                        if is_dependent:
                            failed_details.append(
                                "Impossible de modifier l'échelle de la vue %s : vue dépendante (gabarit : %s)" % 
                                (v.Name if v.Name else v.Id.IntegerValue, template_name)
                            )
                        elif view_template.IntegerValue != -1 and modify_templates:
                            # Tenter de modifier le gabarit de vue
                            template = doc.GetElement(view_template)
                            if template:
                                template_scale_param = template.get_Parameter(BuiltInParameter.VIEW_SCALE)
                                if template_scale_param and not template_scale_param.IsReadOnly:
                                    if system_name.lower() == "imperial":
                                        target = SCALE_CONVERSION["metric_to_imperial"].get(scale, None)
                                    else:
                                        target = SCALE_CONVERSION["imperial_to_metric"].get(scale, None)
                                    if target and scale != target:
                                        template_scale_param.Set(target)
                                        count_success += 1
                                        templates_modified[template.Id.IntegerValue] = template.Name
                                        failed_details.append(
                                            "Échelle de la vue %s modifiée via le gabarit %s" % 
                                            (v.Name if v.Name else v.Id.IntegerValue, template.Name)
                                        )
                                    else:
                                        failed_details.append(
                                            "Échelle %s du gabarit %s non modifiée : échelle non trouvée" % 
                                            (scale, template.Name)
                                        )
                                else:
                                    failed_details.append(
                                        "Impossible de modifier l'échelle du gabarit %s pour la vue %s : paramètre en lecture seule" % 
                                        (template.Name, v.Name if v.Name else v.Id.IntegerValue)
                                    )
                            else:
                                failed_details.append(
                                    "Vue %s en lecture seule (gabarit %s non accessible)" % 
                                    (v.Name if v.Name else v.Id.IntegerValue, template_name)
                                )
                        else:
                            failed_details.append(
                                "Impossible de modifier l'échelle de la vue %s : paramètre en lecture seule (gabarit : %s)" % 
                                (v.Name if v.Name else v.Id.IntegerValue, template_name)
                            )
            except Exception as ex:
                count_failed += 1
                failed_details.append(
                    "Erreur sur la vue %s : %s" % 
                    (v.Name if v.Name else v.Id.IntegerValue, str(ex))
                )
        t.Commit()
    except Exception as ex:
        t.RollBack()
        failed_details.append("Erreur lors de la mise à jour des échelles : %s" % str(ex))
        count_failed += 1
    
    return {
        "success": count_success,
        "failed": count_failed,
        "details": failed_details,
        "templates_modified": templates_modified
    }

# ---------------- Exécution ----------------
try:
    # Récupérer le nom de l'unité cible
    unit_target = get_unit_name(TARGET_SYSTEM)
    
    # Arrondir les paramètres de longueur (si activé)
    param_summary = {"success": 0, "failed": 0, "details": []}
    if ROUND_PARAMETER_VALUES:
        param_summary = round_length_parameters(doc)
    
    # Mettre à jour les échelles des vues
    view_summary = update_view_scales(doc, TARGET_SYSTEM, MODIFY_TEMPLATES)
    
    # Construire le résumé
    resume = []
    resume.append("=== Résumé des actions ===")
    resume.append("Unité cible : %s" % unit_target)
    resume.append("\n--- Arrondi des paramètres de longueur ---")
    resume.append("Paramètres arrondis avec succès : %d" % param_summary["success"])
    resume.append("Paramètres non arrondis : %d" % param_summary["failed"])
    if param_summary["details"]:
        resume.append("Détails des échecs :")
        resume.extend(["  - %s" % detail for detail in param_summary["details"]])
    else:
        resume.append("Aucun échec détecté.")
    
    resume.append("\n--- Modification des échelles des vues ---")
    resume.append("Vues modifiées avec succès : %d" % view_summary["success"])
    resume.append("Vues non modifiées : %d" % view_summary["failed"])
    if view_summary["templates_modified"]:
        resume.append("Gabarits de vue modifiés :")
        resume.extend(["  - %s" % name for id, name in view_summary["templates_modified"].items()])
    if view_summary["details"]:
        resume.append("Détails des échecs :")
        resume.extend(["  - %s" % detail for detail in view_summary["details"]])
    else:
        resume.append("Aucun échec détecté.")
    
    # Afficher le résumé
    TaskDialog.Show("Résumé de la conversion", "\n".join(resume))

except Exception as ex:
    TaskDialog.Show("Erreur", "Échec de la conversion : %s" % str(ex))