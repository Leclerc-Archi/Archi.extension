# -*- coding: utf-8 -*-
import os
import tempfile
from pyrevit import forms
from Autodesk.Revit.DB import *

# Classe pour gérer automatiquement le remplacement des familles
class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True
    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues.Value = True
        return True

def run():
    # 1. Sélection des fichiers sources
    file_paths = forms.pick_file(file_ext="rvt", multi_file=True, title="BIM-TEAM - Sélectionnez les projets sources")
    if not file_paths:
        return

    doc_dest = __revit__.ActiveUIDocument.Document
    total_imported = 0
    temp_dir = tempfile.gettempdir()

    # 2. Traitement des fichiers
    for file_path in file_paths:
        try:
            model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(file_path)
            options = OpenOptions()
            options.DetachFromCentralOption = DetachFromCentralOption.DetachAndPreserveWorksets
            
            doc_source = __revit__.Application.OpenDocumentFile(model_path, options)
            
            # Récupérer les familles éditables
            collector = FilteredElementCollector(doc_source).OfClass(Family)
            all_families = {f.Name: f for f in collector if f.IsEditable}
            
            # Sélection utilisateur
            selected_names = forms.SelectFromList.show(
                sorted(all_families.keys()),
                title="Familles à importer",
                multiselect=True
            )
            
            # 3. Importation
            if selected_names:
                with Transaction(doc_dest, "Importer Familles") as t:
                    t.Start()
                    for name in selected_names:
                        fam = all_families[name]
                        doc_fam = doc_source.EditFamily(fam)
                        temp_rfa = os.path.join(temp_dir, "{}.rfa".format(name.replace("/", "_")))
                        
                        doc_fam.SaveAs(temp_rfa, SaveAsOptions())
                        doc_fam.Close(False)
                        
                        doc_dest.LoadFamily(temp_rfa, FamilyLoadOptions())
                        
                        if os.path.exists(temp_rfa):
                            os.remove(temp_rfa)
                        total_imported += 1
                    t.Commit()
            
            doc_source.Close(False)
            
        except Exception as e:
            print("Erreur critique sur {}: {}".format(os.path.basename(file_path), e))

    # 4. Confirmation de fin
    print("--- Script terminé ---")
    if total_imported > 0:
        forms.alert("Importation terminée.\n\nNombre de familles importées : {}".format(total_imported), title="Succès")
    else:
        forms.alert("Aucune famille n'a été importée.", title="BIM-TEAM - Information")



run()