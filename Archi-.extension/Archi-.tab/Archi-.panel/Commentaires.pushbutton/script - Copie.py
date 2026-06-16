# -*- coding: utf-8 -*-
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog   # <--- ajouté ici
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

# Lignes de détail internes
used_line_style_ids = set()
for elem in FilteredElementCollector(doc).OfClass(CurveElement).WhereElementIsNotElementType():
    if isinstance(elem, DetailLine) and elem.LineStyle and "interne" in elem.LineStyle.Name.lower():
        used_line_style_ids.add(elem.LineStyle.Id)
style_ligne = ", ".join(doc.GetElement(i).Name for i in used_line_style_ids if doc.GetElement(i)) or "Aucun"

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
       "Agit sur toutes les vues + elements directement sur les feuilles\n\n"
       "Que voulez-vous faire ?").format(style_text, style_ligne, style_cote)

choice = forms.alert(msg,
                     title="Masquer / Reveler elements internes",
                     options=["Masquer les elements internes", "Reveler les elements internes"],
                     warn_icon=False)
if not choice:
    sys.exit()

masquer = (choice == "Masquer les elements internes")

# ==============================================================
views_dict  = {}   # ViewId  -> List[ElementId]
sheets_dict = {}   # SheetId -> List[ElementId]

def ajouter_element(elem):
    vid = elem.OwnerViewId
    if vid != ElementId.InvalidElementId:
        views_dict.setdefault(vid, List[ElementId]()).Add(elem.Id)
    else:
        # element directement sur une feuille
        for sheet in FilteredElementCollector(doc).OfClass(ViewSheet).ToElements():
            if elem.Id in sheet.GetDependentElements(None):
                sheets_dict.setdefault(sheet.Id, List[ElementId]()).Add(elem.Id)
                return

# TextNotes
for tn in FilteredElementCollector(doc).OfClass(TextNote).WhereElementIsNotElementType():
    if tn.GetTypeId() in text_type_ids:
        ajouter_element(tn)

# Detail Lines
for elem in FilteredElementCollector(doc).OfClass(CurveElement).WhereElementIsNotElementType():
    if isinstance(elem, DetailLine) and elem.LineStyle and elem.LineStyle.Id in used_line_style_ids:
        ajouter_element(elem)

# Dimensions
for dim in FilteredElementCollector(doc).OfClass(Dimension).WhereElementIsNotElementType():
    if dim.GetTypeId() in dim_type_ids:
        ajouter_element(dim)

# ==============================================================
nb_ok = nb_ignore = 0

with revit.Transaction("Masquer/Reveler elements internes"):
    # 1. Vues (plans, coupes, legendes, vues dependantes)
    for view_id, elem_ids in views_dict.items():
        view = doc.GetElement(view_id)
        if not view or isinstance(view, ViewSchedule):
            continue

        vues_a_traiter = [view]
        for v in FilteredElementCollector(doc).OfClass(View).WhereElementIsNotElementType():
            if hasattr(v, "GetPrimaryViewId") and v.GetPrimaryViewId() == view_id:
                vues_a_traiter.append(v)

        for v in vues_a_traiter:
            try:
                if masquer:
                    v.HideElements(elem_ids)
                else:
                    v.UnhideElements(elem_ids)
                nb_ok += elem_ids.Count
            except:
                nb_ignore += elem_ids.Count

    # 2. Elements directement sur les feuilles
    for sheet_id, elem_ids in sheets_dict.items():
        sheet = doc.GetElement(sheet_id)
        if not sheet:
            continue
        try:
            if masquer:
                sheet.HideElementsTemporary(elem_ids)
            else:
                sheet.UnhideElements(elem_ids)
            nb_ok += elem_ids.Count
        except:
            nb_ignore += elem_ids.Count

# ==============================================================
TaskDialog.Show("Termine !",
    "Operation terminee avec succes !\n\n"
    "Texte interne  : {}\n"
    "Ligne interne  : {}\n"
    "Cote interne   : {}\n\n"
    "Elements traites   : {}\n"
    "Elements ignores   : {}".format(
        style_text, style_ligne, style_cote, nb_ok, nb_ignore))