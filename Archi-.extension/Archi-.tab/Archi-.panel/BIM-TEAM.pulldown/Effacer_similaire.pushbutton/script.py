# -*- coding: utf-8 -*-
__title__ = "Effacer\nDupliqués"
__author__ = "Bobby Qc"

from pyrevit import revit, DB, forms
from System.Collections.Generic import List
from System.Windows.Data import CollectionViewSource
from System.Windows.Input import Key, ModifierKeys, Keyboard
from collections import defaultdict
import os

# ──────────────────────────────────────────────────────────
# Modèle de données pour l'affichage WPF
# ──────────────────────────────────────────────────────────
class DuplicateItemViewModel(object):
    def __init__(self, display_label, element_id, group_index):
        self.DisplayLabel = display_label
        self.Id = element_id
        self.GroupIndex = group_index  # Pour regrouper visuellement les doublons

    def __str__(self):
        return self.DisplayLabel

# ──────────────────────────────────────────────────────────
# Contrôleur d'interface WPF
# ──────────────────────────────────────────────────────────
class DuplicateManagerWPF(forms.WPFWindow):
    def __init__(self, xaml_file_name, duplicates_data):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.selected_ids = []

        # Injection des données converties en ViewModel
        self.items_source = [
            DuplicateItemViewModel(d["label"], d["id"], d["group"])
            for d in duplicates_data
        ]
        self.DuplicateList.ItemsSource = self.items_source

        self._bind_events()

    def _bind_events(self):
        self.SearchBox.TextChanged += self.SearchBox_TextChanged
        self.DuplicateList.KeyDown += self.List_KeyDown
        self.DuplicateList.MouseDoubleClick += self.DuplicateList_DoubleClicked
        self.BtnSelectAll.Click += self.BtnSelectAll_Click
        self.BtnUnselectAll.Click += self.BtnUnselectAll_Click
        self.BtnDelete.Click += self.BtnDelete_Click

    def DuplicateList_DoubleClicked(self, sender, e):
        """Zoom sur l'élément sélectionné lors d'un double-clic"""
        if self.DuplicateList.SelectedItem:
            try:
                el_id = self.DuplicateList.SelectedItem.Id
                revit.uidoc.ShowElements(el_id)
                revit.uidoc.Selection.SetElementIds(List[DB.ElementId]([el_id]))
            except:
                pass

    def SearchBox_TextChanged(self, sender, e):
        search_query = self.SearchBox.Text.lower()
        view = CollectionViewSource.GetDefaultView(self.DuplicateList.ItemsSource)
        if view:
            view.Filter = lambda item: search_query in str(item).lower()

    def List_KeyDown(self, sender, e):
        if e.Key == Key.A and (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control:
            e.Handled = True
            for item in self.DuplicateList.Items:
                self.DuplicateList.SelectedItems.Add(item)

    def BtnSelectAll_Click(self, sender, e):
        self.DuplicateList.SelectAll()

    def BtnUnselectAll_Click(self, sender, e):
        self.DuplicateList.UnselectAll()

    def BtnDelete_Click(self, sender, e):
        self.selected_ids = [item.Id for item in self.DuplicateList.SelectedItems]
        if not self.selected_ids:
            forms.alert("Veuillez sélectionner au moins un élément.")
            return
        self.DialogResult = True
        self.Close()

# ──────────────────────────────────────────────────────────
# Logique métier
# ──────────────────────────────────────────────────────────
def get_signature(el):
    """
    Retourne une signature unique basée sur :
      - le type d'élément (GetTypeId)
      - la phase de création (CreatedPhaseId)
      - la position X, Y, Z arrondie à 3 décimales
    Deux éléments dans des phases différentes ne seront jamais
    considérés comme doublons, même à la même position.
    """
    try:
        loc = el.Location
        if not loc:
            return None
        if hasattr(loc, "Point"):
            pt = loc.Point
        elif hasattr(loc, "Curve"):
            pt = loc.Curve.GetEndPoint(0)
        else:
            return None
        if pt is None:
            return None
        return (
            el.GetTypeId(),
            el.CreatedPhaseId,
            round(pt.X, 3),
            round(pt.Y, 3),
            round(pt.Z, 3),
        )
    except:
        return None

def get_element_info(el, group_index):
    try:
        t_id = el.GetTypeId()
        elem_type = revit.doc.GetElement(t_id)
        t_name = (
            elem_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
            if elem_type
            else "Sans type"
        )
        cat_name = el.Category.Name if el.Category else "Sans catégorie"
        phase_name = (
            revit.doc.GetElement(el.CreatedPhaseId).Name
            if el.CreatedPhaseId != DB.ElementId.InvalidElementId
            else "Sans phase"
        )
        label = u"[Groupe {}] [{}] {} — Phase: {} (ID: {})".format(
            group_index, cat_name, t_name, phase_name, el.Id.IntegerValue
        )
        return {"id": el.Id, "label": label, "group": group_index}
    except:
        return {
            "id": el.Id,
            "label": u"[Groupe {}] ID: {} — Erreur lecture".format(
                group_index, el.Id.IntegerValue
            ),
            "group": group_index,
        }

# ──────────────────────────────────────────────────────────
# Point d'entrée principal
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    doc = revit.doc

    # Collecte de tous les éléments non-types et indépendants des vues
    col = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
    )

    # Regroupement par signature (type + phase + position)
    groups = defaultdict(list)
    for el in col:
        sig = get_signature(el)
        if sig:
            groups[sig].append(el)

    # On ne conserve que les groupes avec au moins 2 éléments (vrais doublons)
    duplicates_info = []
    group_index = 1
    for sig, elements in groups.items():
        if len(elements) > 1:
            for el in elements:
                duplicates_info.append(get_element_info(el, group_index))
            group_index += 1

    if not duplicates_info:
        forms.alert("Aucun doublon détecté.", title="BIM-TEAM")
    else:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ui_window.xaml"
        )
        if os.path.exists(path):
            dlg = DuplicateManagerWPF(path, duplicates_info)
            if dlg.ShowDialog():
                try:
                    with revit.Transaction("BIM-TEAM: Suppression Doublons"):
                        revit.doc.Delete(List[DB.ElementId](dlg.selected_ids))
                    forms.alert(
                        "{} éléments supprimés.".format(len(dlg.selected_ids)),
                        title="BIM-TEAM",
                    )
                except Exception as e:
                    forms.alert("Erreur lors de la suppression : {}".format(e))
        else:
            forms.alert("Fichier 'ui_window.xaml' non trouvé.")