# -*- coding: utf-8 -*-
from pyrevit import revit, DB, script

# Initialisation de la sortie (output) pour afficher les résultats
output = script.get_output()

# 1. Récupérer tous les nuages de révision dans le projet
revision_clouds = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

# Préparation de l'affichage dans un tableau
output.print_md("## LISTE DES NUAGES DE RÉVISION")
header = ["ID", "Description de la Révision", "Commentaires du Nuage", "Feuille (Numéro - Nom)"]
data = []

for cloud in revision_clouds:
    # 2. Récupérer la révision associée au nuage pour avoir la description
    rev_id = cloud.RevisionId
    revision = revit.doc.GetElement(rev_id)
    rev_desc = revision.Description if revision else "N/A"
    
    # 3. Récupérer le commentaire spécifique du nuage
    cloud_comment = cloud.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).AsString()
    if not cloud_comment:
        cloud_comment = "-"

    # 4. Trouver la feuille (Sheet) correspondante
    # Le nuage peut être sur une vue ou directement sur la feuille
    owner_view = revit.doc.GetElement(cloud.OwnerViewId)
    
    sheet_info = "Non placé sur une feuille"
    
    if isinstance(owner_view, DB.ViewSheet):
        sheet_info = "{} - {}".format(owner_view.SheetNumber, owner_view.Name)
    elif hasattr(owner_view, "GenLevel"): # Si c'est une vue en plan, etc.
        # On cherche si la vue est sur une feuille
        sheet_number_param = owner_view.get_Parameter(DB.BuiltInParameter.VIEWPORT_SHEET_NUMBER)
        sheet_name_param = owner_view.get_Parameter(DB.BuiltInParameter.VIEWPORT_SHEET_NAME)
        
        if sheet_number_param and sheet_number_param.AsString():
            sheet_info = "{} - {}".format(sheet_number_param.AsString(), sheet_name_param.AsString())

    # Ajouter les données à la liste
    data.append([
        output.linkify(cloud.Id), 
        rev_desc, 
        cloud_comment, 
        sheet_info
    ])

# 5. Affichage sous forme de tableau interactif
output.print_table(
    table_data=data,
    title="Récapitulatif des Nuages",
    columns=header
)