# -*- coding: utf-8 -*-
__title__ = "Audit & Synchroniser Gabarits"
__author__ = "Bobby Qc"

from pyrevit import revit, DB, forms
import clr
from os import path

clr.AddReference("PresentationFramework")
from System.Windows.Data import Binding
from System.Windows.Controls import DataGridTextColumn

class DataItem:
    def __init__(self, filtre, prop, ref, others):
        self.Filtre = filtre
        self.Prop = prop
        self.Ref = ref
        self.Others = others 
        self.fid = 0
        self.code = ""
        self.__getitem__ = lambda self, key: self.Others[key]

class MultiTemplateAuditWPF(forms.WPFWindow):
    def __init__(self, xaml_file):
        forms.WPFWindow.__init__(self, xaml_file)
        self._doc = revit.doc
        collector = DB.FilteredElementCollector(self._doc).OfClass(DB.View)
        self.t_map = {v.Name: v for v in collector if v.IsTemplate}
        
        self.ComboReference.ItemsSource = sorted(self.t_map.keys())
        self.TemplateList.ItemsSource = sorted(self.t_map.keys())
        
        self.BtnRefresh.Click += self.BtnRefresh_Click
        self.BtnApply.Click += self.BtnApply_Click
        self.SearchBox.TextChanged += self.SearchBox_TextChanged

    def SearchBox_TextChanged(self, sender, e):
        search_text = self.SearchBox.Text.lower()
        filtered = [name for name in sorted(self.t_map.keys()) if search_text in name.lower()]
        self.TemplateList.ItemsSource = filtered

    def _get_data(self, view):
        data = {}
        for fid in view.GetFilters():
            ov = view.GetFilterOverrides(fid)
            # Use appropriate getter methods for Revit 2025 compatibility
            data[fid.IntegerValue] = {
                "a": "V" if view.GetIsFilterEnabled(fid) else "X",
                "v": "On" if view.GetFilterVisibility(fid) else "Off",
                "l": str(ov.ProjectionLineWeight),
                "t": str(ov.Transparency) + "%"
            }
        return data

    def BtnRefresh_Click(self, sender, e):
        ref_n = self.ComboReference.SelectedItem
        selected_others = [item for item in self.TemplateList.SelectedItems if item != ref_n]
        if not ref_n: 
            forms.alert("Sélectionnez une référence.")
            return

        self.AuditGrid.Columns.Clear()
        for h, b in [("Filtre", "Filtre"), ("Prop", "Prop"), ("Ref", "REF: " + ref_n)]:
            col = DataGridTextColumn()
            col.Header = b
            col.Binding = Binding(h)
            self.AuditGrid.Columns.Add(col)

        for name in selected_others:
            col = DataGridTextColumn()
            col.Header = name
            col.Binding = Binding("Others[" + name + "]") 
            self.AuditGrid.Columns.Add(col)

        all_d = {n: self._get_data(self.t_map[n]) for n in [ref_n] + selected_others}
        rows = []
        for fid in self.t_map[ref_n].GetFilters():
            f_name = self._doc.GetElement(fid).Name
            for code, label in [("a", "Actif"), ("v", "Visib."), ("l", "Lignes"), ("t", "Transp.")]:
                item = DataItem(f_name, label, all_d[ref_n].get(fid.IntegerValue, {}).get(code, "-"), {})
                for n in selected_others:
                    item.Others[n] = all_d[n].get(fid.IntegerValue, {}).get(code, "-")
                item.fid = fid.IntegerValue
                item.code = code
                rows.append(item)
        
        self.AuditGrid.ItemsSource = rows

    def BtnApply_Click(self, sender, e):
        ref_n = self.ComboReference.SelectedItem
        if not ref_n or not self.TemplateList.SelectedItems: return
        
        if not forms.alert("Synchroniser vers les gabarits sélectionnés ?", ok=True, cancel=True):
            return

        with revit.Transaction("Sync Gabarits", self._doc):
            ref_view = self.t_map[ref_n]
            target_names = [n for n in self.TemplateList.SelectedItems if n != ref_n]
            
            for item in self.AuditGrid.ItemsSource:
                fid = DB.ElementId(item.fid)
                for name in target_names:
                    target = self.t_map[name]
                    
                    # Correct check for filter existence
                    if fid not in target.GetFilters():
                        continue
                    
                    if item.code == "a":
                        target.SetIsFilterEnabled(fid, ref_view.GetIsFilterEnabled(fid))
                    elif item.code == "v":
                        target.SetFilterVisibility(fid, ref_view.GetFilterVisibility(fid))
                    else:
                        ov = target.GetFilterOverrides(fid)
                        rv = ref_view.GetFilterOverrides(fid)
                        
                        if item.code == "l":
                            ov.SetProjectionLineWeight(rv.ProjectionLineWeight)
                        elif item.code == "t":
                            ov.SetSurfaceTransparency(rv.Transparency)
                            
                        target.SetFilterOverrides(fid, ov)
        
        forms.alert("Synchronisation réussie !")
        self.BtnRefresh_Click(None, None)

# Lancement
folder = path.dirname(path.abspath(__file__))
MultiTemplateAuditWPF(path.join(folder, "ui_window.xaml")).ShowDialog()