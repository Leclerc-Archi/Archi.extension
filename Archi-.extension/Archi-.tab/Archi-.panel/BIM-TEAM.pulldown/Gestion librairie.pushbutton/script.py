# -*- coding: utf-8 -*-
import os
import clr
import sys # Import nécessaire pour quitter le script proprement

# Chargement Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

# Import pour la gestion des listes .NET
clr.AddReference('System')
from System.Collections.Generic import List

# Accès au document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = doc.Application

# --- CONFIGURATION ---
base_path = r'C:\Export_Revit_2025'

def safe_folder(folder_name):
    invalid = '<>:"/\\|?*'
    for char in invalid:
        folder_name = folder_name.replace(char, '_')
    path = os.path.join(base_path, folder_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

# --- 1. CONFIRMATION AVANT DEMARRAGE ---
ask = TaskDialog.Show("Exportateur de Familles", 
                      "Voulez-vous lancer l'exportation des familles et vues ?", 
                      TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No)

# SI NON : On quitte immédiatement
if ask == TaskDialogResult.No:
    sys.exit() 

# --- EXÉCUTION ---
try:
    save_opts = SaveAsOptions()
    save_opts.OverwriteExistingFile = True

    # Récupération des données
    families = [f for f in FilteredElementCollector(doc).OfClass(Family) if f.IsEditable]
    drafting_views = FilteredElementCollector(doc).OfClass(ViewDrafting).ToElements()
    
    total_steps = len(families) + (1 if drafting_views else 0)
    
    # --- 2. BARRE DE PROGRESSION (Supporte ESC) ---
    pb = ProgressManager.GetProgressManager()
    pb.Start(total_steps)
    pb.SetCaption("Export en cours...")

    count = 0
    # --- EXPORT DES FAMILLES ---
    for fam in families:
        # Vérification si Echap/Annuler est pressé
        if pb.IsCancelled():
            break
            
        cat_name = fam.FamilyCategory.Name if fam.FamilyCategory else "Sans_Categorie"
        folder = safe_folder(cat_name)
        
        try:
            fam_doc = doc.EditFamily(fam)
            path = os.path.join(folder, fam.Name + ".rfa")
            fam_doc.SaveAs(path, save_opts)
            fam_doc.Close(False)
        except:
            pass 
        
        count += 1
        pb.Increment(1)
        pb.SetCaption("Export Familles : {}/{}".format(count, len(families)))

    # --- EXPORT DES VUES DE DESSIN ---
    if drafting_views and not pb.IsCancelled():
        pb.SetCaption("Export des Vues de Dessin...")
        view_folder = safe_folder("Vues_de_Dessin")
        new_doc = app.NewProjectDocument(UnitSystem.Metric)
        
        ids_to_copy = List[ElementId]()
        for v in drafting_views:
            ids_to_copy.Add(v.Id)
            
        t = Transaction(new_doc, "Export Vues")
        t.Start()
        ElementTransformUtils.CopyElements(doc, ids_to_copy, new_doc, None, CopyPasteOptions())
        t.Commit()
        
        new_doc.SaveAs(os.path.join(view_folder, "Export_Vues.rvt"), save_opts)
        new_doc.Close(False)
        pb.Increment(1)

    pb.Stop()

    if not pb.IsCancelled():
        TaskDialog.Show("Terminé", "L'opération a été complétée.")

except Exception as e:
    if 'pb' in locals(): pb.Stop()
    print("Erreur : {}".format(str(e)))