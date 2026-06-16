# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, forms
from System.Collections.Generic import List
import sys

doc = revit.doc
if not doc:
    forms.alert("Aucun document Revit ouvert.")
    sys.exit()

# ==============================================================
# 1. Détection des styles "interne"

# Textes internes
text_types_interne = [t for t in FilteredElementCollector(doc).OfClass(TextNoteType).ToElements()
                      if t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME) and
                         "interne" in t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString().lower()]
text_type_ids = {t.Id for t in text_types_interne}
style_text = ", ".join(t.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString() for t in text_types_interne) or "Aucun"

# TOUTES les lignes (Détail + Modèle) internes
used_line_style_ids = set()
for elem in FilteredElementCollector(doc).OfClass(CurveElement).WhereElementIsNotElementType():
    # On vérifie le style de ligne pour tout élément de courbe
    line_style = doc.GetElement(elem.LineStyle.Id)
    if line_style and "interne" in line_style.Name.lower():
        used_line_style_ids.add(line_style.Id)

style_ligne = ", ".join(doc.GetElement(i).Name for i in used_line_style_ids) or "Aucun"

# Cotes internes
dim_types_interne = [dt for dt in FilteredElementCollector(doc).OfClass(DimensionType).ToElements()
                    if dt.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME) and
                       "interne" in dt.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString().lower()]
dim_type_ids = {dt.Id for dt in dim_types_interne}
style_cote = ", ".join(dt.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString() for dt in dim_types_interne) or "Aucun"

# ==============================================================
msg = ("ELEMENTS INTERNES DETECTES\n\n"
       "Texte interne  : {}\n"
       "Ligne interne  : {}\n"
       "Cote interne   : {}\n\n"
       "Que voulez-vous faire ?").format(style_text, style_ligne, style_cote)

choice = forms.alert(msg,
                     title="Masquer / Reveler elements internes",
                     options=["Masquer les elements internes", "Reveler les elements internes"],
                     warn_icon=False)
if not choice:
    sys.exit()

masquer = (choice == "Masquer les elements internes")

# ==============================================================
views_dict  = {}  
sheets_dict = {}  

def ajouter_element(elem):
    vid = elem.OwnerViewId
    if vid != ElementId.InvalidElementId:
        views_dict.setdefault(vid, List[ElementId]()).Add(elem.Id)
    else:
        # Cas des Model Lines (pas d'OwnerViewId) ou éléments sur feuilles
        for sheet in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements():
            if elem.Id in sheet.GetDependentElements(None):
                sheets_dict.setdefault(sheet.Id, List[ElementId]()).Add(elem.Id)
                return

# Collecte des éléments
# TextNotes
for tn in FilteredElementCollector(doc).OfClass(TextNote).WhereElementIsNotElementType():
    if tn.GetTypeId() in text_type_ids:
        ajouter_element(tn)

# CurveElements (Lignes de détail ET lignes de modèle)
for elem in FilteredElementCollector(doc).OfClass(CurveElement).WhereElementIsNotElementType():
    if elem.LineStyle.Id in used_line_style_ids:
        ajouter_element(elem)

# Dimensions
for dim in FilteredElementCollector(doc).OfClass(Dimension).WhereElementIsNotElementType():
    if dim.GetTypeId() in dim_type_ids:
        ajouter_element(dim)

# ==============================================================
nb_ok = nb_ignore = 0

with revit.Transaction("Masquer/Reveler elements internes"):
    # 1. Traitement des Vues
    for view_id, elem_ids in views_dict.items():
        view = doc.GetElement(view_id)
        if not view or isinstance(view, ViewSchedule): continue

        try:
            if masquer:
                view.HideElements(elem_ids)
            else:
                view.UnhideElements(elem_ids)
            nb_ok += elem_ids.Count
        except:
            nb_ignore += elem_ids.Count

    # 2. Traitement des Feuilles
    for sheet_id, elem_ids in sheets_dict.items():
        sheet = doc.GetElement(sheet_id)
        if not sheet: continue
        try:
            if masquer:
                sheet.HideElements(elem_ids) # HideElements fonctionne aussi sur les feuilles
            else:
                sheet.UnhideElements(elem_ids)
            nb_ok += elem_ids.Count
        except:
            nb_ignore += elem_ids.Count

# ==============================================================
TaskDialog.Show("Termine !",
    "Operation terminee !\n\n"
    "Elements traites   : {}\n"
    "Elements ignores   : {}".format(nb_ok, nb_ignore))