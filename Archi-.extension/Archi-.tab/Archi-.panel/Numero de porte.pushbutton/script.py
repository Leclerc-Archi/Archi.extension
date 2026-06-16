# -*- coding: utf-8 -*-
import clr
import sys

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, forms

doc = revit.doc
if not doc:
    TaskDialog.Show('Erreur', 'Aucun document Revit actif.')
    sys.exit()

# --- Fonctions utilitaires ---

def list_all_phases():
    """Retourne toutes les phases du document"""
    phases = FilteredElementCollector(doc).OfClass(Phase).ToElements()
    return phases

def select_phases():
    """Affiche une boîte de dialogue pour sélectionner une ou plusieurs phases"""
    phases = list_all_phases()
    phase_names = [phase.Name for phase in phases]
    if not phase_names:
        TaskDialog.Show('Erreur', "Aucune phase trouvée dans le document.")
        sys.exit()
    
    selected_phases = forms.SelectFromList.show(
        phase_names,
        title="Sélectionner les phases",
        multiselect=True,
        button_name="Valider"
    )
    
    if not selected_phases:
        TaskDialog.Show('Erreur', "Aucune phase sélectionnée. Le script a été annulé.")
        sys.exit()
    
    selected_phase_objects = [phase for phase in phases if phase.Name in selected_phases]
    return selected_phase_objects

def get_room_number(room):
    """Retourne la valeur du paramètre 'Numéro' d'une pièce"""
    possible_names = ["Numéro", "Number", "Numéro de pièce", "Room Number"]
    for name in possible_names:
        param = room.LookupParameter(name)
        if param and param.HasValue and param.StorageType == StorageType.String:
            return param.AsString()
    return None

def get_connected_rooms(door, phases):
    """Retourne les pièces connectées à une porte et leurs numéros pour les phases spécifiées"""
    room_from = None
    room_to = None
    from_number = None
    to_number = None
    
    for phase in phases:
        try:
            room_from = door.FromRoom[phase] if hasattr(door, "FromRoom") else None
            room_to = door.ToRoom[phase] if hasattr(door, "ToRoom") else None
            
            if room_from or room_to:
                from_number = get_room_number(room_from) if room_from else None
                to_number = get_room_number(room_to) if room_to else None
                return (room_from, room_to, from_number, to_number)
        except Exception:
            pass
    
    return (None, None, None, None)

# --- Début du script ---

# Sélectionner les phases
selected_phases = select_phases()

# Collecter toutes les portes
doors = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElements()

room_door_map = {}

# 1. Identifier les pièces connectées et leurs numéros
for door in doors:
    room_from, room_to, from_number, to_number = get_connected_rooms(door, selected_phases)
    
    key = None
    if from_number and to_number:
        if from_number == "EXT" or to_number == "EXT":
            key = "P.{}".format(from_number if to_number == "EXT" else to_number)
        else:
            key = "P.{}".format(to_number)
    elif from_number:
        key = "P.{}".format(from_number)
    elif to_number:
        key = "P.{}".format(to_number)
    else:
        key = "P.EXT"
    
    if key not in room_door_map:
        room_door_map[key] = []
    
    room_door_map[key].append(door)

# 2. Appliquer les marques aux portes
t = Transaction(doc, "Numérotation des portes")
try:
    t.Start()
    
    for key in room_door_map:
        # Exclure les numéros commençant par "Pe"
        if key.startswith("P.Pe"):
            continue
            
        doors_in_room = room_door_map[key]
        if len(doors_in_room) == 1:
            door = doors_in_room[0]
            final_mark = key
            if key.startswith("P.") and "EXT" in get_connected_rooms(door, selected_phases)[3]:
                final_mark = "{}.1 EXT".format(key)
            mark_param = door.LookupParameter("Marque")
            if mark_param and not mark_param.IsReadOnly:
                mark_param.Set(final_mark)
            else:
                mark_param = door.LookupParameter("Commentaires")
                if mark_param and not mark_param.IsReadOnly:
                    mark_param.Set(final_mark)
        else:
            for i, door in enumerate(doors_in_room):
                suffix = ".{}".format(i + 1)
                final_mark = "{}{}".format(key, suffix)
                if key.startswith("P.") and "EXT" in get_connected_rooms(door, selected_phases)[3]:
                    final_mark = "{}{} EXT".format(key, suffix)
                mark_param = door.LookupParameter("Marque")
                if mark_param and not mark_param.IsReadOnly:
                    mark_param.Set(final_mark)
                else:
                    mark_param = door.LookupParameter("Commentaires")
                    if mark_param and not mark_param.IsReadOnly:
                        mark_param.Set(final_mark)
    
    t.Commit()
    TaskDialog.Show("Terminé", "Numérotation des portes terminée.")

except Exception as e:
    if t.HasStarted():
        t.RollBack()
    TaskDialog.Show("Erreur", "Erreur durant la transaction : {}".format(str(e)))