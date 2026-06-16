# -*- coding: utf-8 -*-
from pyrevit import revit, forms
from Autodesk.Revit.DB import *
import os

doc = revit.doc
export_folder = r"K:\2-Protocoles\3-Standards dessins\1-Revit\04_Banque de details\01_Détails extraits de projets\_A trier"

if not os.path.exists(export_folder):
    os.makedirs(export_folder)

# 1. Demander le numéro de projet (Ex: 240101)
num_projet = forms.ask_for_string(
    title="BIM-TEAM - Configuration de l'export",
    prompt="Entrez le numéro de projet :",
    default="24-000"
)

if not num_projet:
    forms.alert("Opération annulée.", exitscript=True)

# 2. Collecter les vues potentielles (Drafting et Details)
filter_drafting = ElementClassFilter(ViewDrafting)
filter_section = ElementClassFilter(ViewSection)
combined_filter = LogicalOrFilter(filter_drafting, filter_section)
collector = FilteredElementCollector(doc).WherePasses(combined_filter).ToElements()

potential_views = [v for v in collector if not v.IsTemplate and (isinstance(v, ViewDrafting) or v.ViewType == ViewType.Detail)]

# 3. Fenêtre de sélection des vues
selected_views = forms.select_views(
    title="BIM-TEAM - Sélectionnez les vues à imprimer en PDF",
    filterfunc=lambda v: v.Id in [pv.Id for pv in potential_views],
    use_selection=True
)

if not selected_views:
    forms.alert("Aucune vue sélectionnée.", exitscript=True)

# 4. Exportation PDF
with revit.Transaction("Export PDF Typologie"):
    for view in selected_views:
        # Nettoyage du nom de la vue
        safe_name = "".join([c for c in view.Name if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        # --- LOGIQUE DE PRÉFIXE SELON LE TYPE DE VUE ---
        # VD_ pour les vues de dessin (Drafting)
        # V3D_ pour les vues de détails (ViewType.Detail / ViewSection)
        type_prefix = "VD_" if isinstance(view, ViewDrafting) else "V3D_"
        
        # Construction du nom final : [NumProjet]_[Type]_[Nom]
        # Exemple : 240101_V3D_Coupe de mur
        file_name_final = "{}_{}{}".format(num_projet, type_prefix, safe_name)
        
        # Configuration des options PDF
        options = PDFExportOptions()
        options.FileName = file_name_final
        options.AlwaysUseRaster = False 
        options.RasterQuality = RasterQualityType.High
        options.ColorDepth = ColorDepthType.Color
        options.ZoomType = ZoomType.FitToPage
        options.PaperFormat = ExportPaperFormat.Default
        options.HideUnreferencedViewTags = True

        # Liste d'ID pour l'export individuel
        from System.Collections.Generic import List
        view_ids = List[ElementId]()
        view_ids.Add(view.Id)

        try:
            doc.Export(export_folder, view_ids, options)
            print("Exporté : {}.pdf".format(file_name_final))
        except Exception as e:
            print("Erreur sur {} : {}".format(view.Name, str(e)))

# Ouverture du dossier final
os.startfile(export_folder)
print("--- Terminé : {} fichiers PDF créés ---".format(len(selected_views)))