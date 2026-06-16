# coding: utf-8
import clr

clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from pyrevit import revit
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

doc = revit.doc
uidoc = revit.uidoc

# ------------------------------------------------------------
# CONFIGURATION DES WORKSETS
# ------------------------------------------------------------

WS_NAMES = {
    "AXES": "00_AXES_NIVEAUX",
    "FONDATIONS": "A_A10_FONDATIONS",
    "SUPERSTRUCTURE": "A_B10_SUPERSTRUCTURE",
    "ENVELOPPE": "A_B20_ENVELOPPE",
    "CONST_INT": "A_C10_CONSTRUCTION_INT",
    "ESCALIERS": "A_C20_ESCALIERS",
    "MOBILIER_MOB": "A_E20_AMEUBLEMENT_MOBILE",
    "MOBILIER_FIXE": "A_E20_AMEUBLEMENT_FIXE",
    "G_SITE": "G_SITE"
}

# ------------------------------------------------------------
# FONCTION WORKSET
# ------------------------------------------------------------

def get_or_create_workset_id(doc, name):
    for ws in FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset):
        if ws.Name == name:
            return ws.Id

    new_ws = Workset.Create(doc, name)
    return new_ws.Id

# ------------------------------------------------------------
# LOGIQUE DE CLASSEMENT
# ------------------------------------------------------------

def starts_with_env(value):
    """Vérifie si une chaîne commence par ENV_ (insensible à la casse)."""
    return value and value.upper().startswith("ENV_")

def is_env_element(elem):
    """
    Retourne True si l'élément doit être classé dans G_SITE.
    Vérifie : nom de famille, nom du type, et nom/marque de l'instance.
    """
    symbol = doc.GetElement(elem.GetTypeId())

    # 1. Nom de famille
    if symbol:
        family_name = getattr(symbol, "FamilyName", None)
        if starts_with_env(family_name):
            return True

        # 2. Nom du type
        type_name_param = symbol.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if type_name_param:
            type_name = type_name_param.AsString()
            if starts_with_env(type_name):
                return True

    # 3. Marque de l'instance
    mark_param = elem.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
    if mark_param:
        mark = mark_param.AsString()
        if starts_with_env(mark):
            return True

    # 4. Nom de l'instance (paramètre générique)
    name_param = elem.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if name_param:
        name = name_param.AsString()
        if starts_with_env(name):
            return True

    return False

def get_target_workset_name(elem):
    if not elem.Category:
        return None

    # --- PRIORITÉ ABSOLUE : tout ce qui commence par ENV_ → G_SITE ---
    if is_env_element(elem):
        return WS_NAMES["G_SITE"]

    cat_id = elem.Category.Id.IntegerValue
    symbol = doc.GetElement(elem.GetTypeId())

    # 2. MURS
    if cat_id == int(BuiltInCategory.OST_Walls):
        wall_type = symbol
        if wall_type:
            func_param = wall_type.get_Parameter(BuiltInParameter.FUNCTION_PARAM)
            if func_param:
                func = func_param.AsInteger()
                if func == 2:
                    return WS_NAMES["FONDATIONS"]
                if func == 1:
                    return WS_NAMES["ENVELOPPE"]

        struct_param = elem.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_USAGE_PARAM)
        if struct_param and struct_param.AsInteger() > 0:
            return WS_NAMES["SUPERSTRUCTURE"]

        return WS_NAMES["CONST_INT"]

    # 3. PORTES / FENÊTRES
    if cat_id in [int(BuiltInCategory.OST_Doors), int(BuiltInCategory.OST_Windows)]:
        if elem.Host:
            return get_target_workset_name(elem.Host)
        return WS_NAMES["ENVELOPPE"]

    # 4. MAPPING PAR CATÉGORIE
    mapping = {
        int(BuiltInCategory.OST_Stairs):    WS_NAMES["ESCALIERS"],
        int(BuiltInCategory.OST_Furniture): WS_NAMES["MOBILIER_MOB"],
        int(BuiltInCategory.OST_Casework):  WS_NAMES["MOBILIER_FIXE"],
        int(BuiltInCategory.OST_Floors):    WS_NAMES["SUPERSTRUCTURE"],
        int(BuiltInCategory.OST_Grids):     WS_NAMES["AXES"],
        int(BuiltInCategory.OST_Levels):    WS_NAMES["AXES"]
    }

    return mapping.get(cat_id)

# ------------------------------------------------------------
# EXÉCUTION
# ------------------------------------------------------------

t = Transaction(doc, "Classement automatique des éléments")
t.Start()

# Création ou récupération des worksets
ws_cache = {}
for key, name in WS_NAMES.items():
    ws_cache[name] = get_or_create_workset_id(doc, name)

# Collecte des catégories ciblées
cats = List[BuiltInCategory]()
cats.Add(BuiltInCategory.OST_Walls)
cats.Add(BuiltInCategory.OST_Doors)
cats.Add(BuiltInCategory.OST_Windows)
cats.Add(BuiltInCategory.OST_Floors)
cats.Add(BuiltInCategory.OST_Furniture)
cats.Add(BuiltInCategory.OST_Stairs)
cats.Add(BuiltInCategory.OST_Casework)
cats.Add(BuiltInCategory.OST_Grids)
cats.Add(BuiltInCategory.OST_Levels)

collector = (
    FilteredElementCollector(doc)
    .WherePasses(ElementMulticategoryFilter(cats))
    .WhereElementIsNotElementType()
)
elements = collector.ToElements()

count = 0
for elem in elements:
    # Ignorer les éléments dans un groupe
    if elem.GroupId != ElementId.InvalidElementId:
        continue

    target_name = get_target_workset_name(elem)
    if not target_name:
        continue

    target_ws_id = ws_cache.get(target_name)
    if not target_ws_id:
        continue

    param = elem.get_Parameter(BuiltInParameter.ELEM_PARTITION_PARAM)
    if param and not param.IsReadOnly:
        if param.AsInteger() != target_ws_id.IntegerValue:
            param.Set(target_ws_id.IntegerValue)
            count += 1

t.Commit()
TaskDialog.Show("pyRevit", "Terminé.\n\nÉléments classés : {}".format(count))