# -*- coding: utf-8 -*-
import sys
from pyrevit import revit, forms
import Autodesk.Revit.DB as DB

doc = revit.doc

def get_drafting_view_type(target_doc):
    collector = DB.FilteredElementCollector(target_doc).OfClass(DB.ViewFamilyType)
    for vft in collector:
        if vft.ViewFamily == DB.ViewFamily.Drafting:
            return vft.Id
    return DB.ElementId.InvalidElementId

def import_multiple_details():
    # 1. Sélection du fichier bibliothèque
    source_path = forms.pick_file(file_ext='rvt', title="BIM-TEAM - Sélectionner la bibliothèque")
    if not source_path:
        return

    # 2. Ouverture en arrière-plan
    source_doc = None
    try:
        source_doc = doc.Application.OpenDocumentFile(source_path)
    except Exception as e:
        forms.alert("Erreur d'ouverture : {}".format(e))
        return

    # 3. Collecte des vues
    col = DB.FilteredElementCollector(source_doc).OfClass(DB.View)
    drafting_names = sorted([v.Name for v in col if v.ViewType == DB.ViewType.DraftingView and not v.IsTemplate])
    detail_names = sorted([v.Name for v in col if v.ViewType == DB.ViewType.Detail and not v.IsTemplate])

    context = {'VUES DE DESSIN (2D)': drafting_names, 'VUES DE DÉTAILS (SECTIONS)': detail_names}

    # 4. Interface
    selected_names = forms.SelectFromList.show(
        context, title="BIM-TEAM - Sélectionner les détails", multiselect=True, group_selector=True
    )

    if not selected_names:
        source_doc.Close(False)
        return

    # 5. Importation
    target_drafting_type = get_drafting_view_type(doc)
    
    with revit.Transaction("Import Détails"):
        options = DB.CopyPasteOptions()
        all_source_views = DB.FilteredElementCollector(source_doc).OfClass(DB.View).ToElements()

        for name in selected_names:
            try:
                s_view = next(v for v in all_source_views if v.Name == name)
                dest_view = DB.ViewDrafting.Create(doc, target_drafting_type)
                
                # Nommage identique à la source
                try:
                    dest_view.Name = s_view.Name
                except:
                    dest_view.Name = s_view.Name + "(1)"
                
                # --- CLASSEMENT DANS LE PARAMÈTRE "SECTION" ---
                # On utilise le nom exact en majuscules
                p_section = dest_view.LookupParameter("SECTION")
                
                if p_section and not p_section.IsReadOnly:
                    p_section.Set("Archi-Détails")
                elif not p_section:
                    # Si SECTION n'est pas trouvé, on affiche un message d'aide
                    print("Note : Le paramètre 'SECTION' n'existe pas sur la vue {}. Vérifiez vos paramètres de projet.".format(dest_view.Name))

                # Copie du contenu graphique
                el_ids = DB.FilteredElementCollector(source_doc, s_view.Id).ToElementIds()
                if el_ids:
                    DB.ElementTransformUtils.CopyElements(s_view, el_ids, dest_view, None, options)
                    
            except Exception as e:
                print("Erreur sur {}: {}".format(name, str(e)))

    source_doc.Close(False)
    forms.toast("Détails importés dans SECTION : Archi-Détails")

if __name__ == "__main__":
    import_multiple_details()
    sys.exit()