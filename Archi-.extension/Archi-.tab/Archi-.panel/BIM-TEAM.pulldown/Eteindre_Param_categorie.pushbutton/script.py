# -*- coding: utf-8 -*-
__title__ = "Gestion\nVisibilite"
__author__ = "BIM-TEAM Archi-"

from pyrevit import revit, DB, forms
import os
from System.Windows.Data import CollectionViewSource
from System.Windows.Input import Key, ModifierKeys, Keyboard

class SubCategoryViewModel(object):
    """Classe conteneur pour l'affichage des colonnes de la sous-catégorie"""
    def __init__(self, display_name, subcat_id, status_text="N/A", status_color="#666666"):
        self.DisplayName = display_name
        self.Id = subcat_id
        self.StatusText = status_text    # "Affiché", "Masqué" ou "Mixte"
        self.StatusColor = status_color  # Couleur hexadécimale correspondante

    def __str__(self):
        # Nécessaire pour que le filtre de recherche de la SearchBox fonctionne toujours sur le texte
        return self.DisplayName


class DiRootsStyleManager(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._doc = revit.doc
        
        self.all_cat_names = []
        self.all_subcat_items = []  # Contiendra les objets SubCategoryViewModel
        self.all_template_names = []
        
        self._setup_initial_data()
        self._bind_events()

    def _setup_initial_data(self):
        self.all_cats = {c.Name: c for c in self._doc.Settings.Categories 
                         if c.SubCategories and not c.SubCategories.IsEmpty}
        self.all_cat_names = sorted(self.all_cats.keys())
        self.CatList.ItemsSource = self.all_cat_names

        all_views = DB.FilteredElementCollector(self._doc).OfClass(DB.View).ToElements()
        self.all_template_names = sorted([v.Name for v in all_views if v.IsTemplate])
        self.TemplateList.ItemsSource = self.all_template_names

    def _bind_events(self):
        self.CatList.SelectionChanged += self.CatList_SelectionChanged
        # Événement ajouté : recalculer les statuts si la sélection de gabarits change
        self.TemplateList.SelectionChanged += self.TemplateList_SelectionChanged
        
        self.SearchBox.TextChanged += self.SearchBox_TextChanged
        
        self.CatList.KeyDown += self.List_KeyDown
        self.SubCatList.KeyDown += self.List_KeyDown
        self.TemplateList.KeyDown += self.List_KeyDown

        self.BtnHide.Click += self.BtnHide_Click
        self.BtnShow.Click += self.BtnShow_Click

    def _update_subcategories_status(self):
        """Calcule le statut de visibilité des sous-catégories selon les gabarits sélectionnés"""
        selected_templates_names = list(self.TemplateList.SelectedItems)
        
        if not selected_templates_names:
            for item in self.all_subcat_items:
                item.StatusText = "Sélectionnez Gabarit"
                item.StatusColor = "#666666" # Gris
            return

        # Récupérer les instances réelles des gabarits sélectionnés
        all_views = DB.FilteredElementCollector(self._doc).OfClass(DB.View).ToElements()
        selected_templates = [v for v in all_views if v.IsTemplate and v.Name in selected_templates_names]

        for item in self.all_subcat_items:
            hidden_states = []
            for t in selected_templates:
                if t.CanCategoryBeHidden(item.Id):
                    hidden_states.append(t.GetCategoryHidden(item.Id))
            
            # Détermination du statut croisé
            if not hidden_states:
                item.StatusText = "Invalide"
                item.StatusColor = "#94a3b8" # Gris clair
            elif all(hidden_states):
                item.StatusText = "Masqué ❌"
                item.StatusColor = "#ef4444" # Rouge
            elif not any(hidden_states):
                item.StatusText = "Affiché  "
                item.StatusColor = "#22c55e" # Vert
            else:
                item.StatusText = "Mixte ⚠️"
                item.StatusColor = "#f59e0b" # Orange

    def CatList_SelectionChanged(self, sender, e):
        """Régénère la liste d'objets sous-catégories"""
        selected_cats = list(self.CatList.SelectedItems)
        self.all_subcat_items = []

        for c_name in selected_cats:
            if c_name in self.all_cats:
                parent_cat = self.all_cats[c_name]
                for sub in parent_cat.SubCategories:
                    label = "{} : {}".format(c_name, sub.Name)
                    # Création de l'objet de données
                    self.all_subcat_items.append(SubCategoryViewModel(label, sub.Id))
        
        self.all_subcat_items.sort(key=lambda x: x.DisplayName)
        
        # Calculer le statut avant affichage
        self._update_subcategories_status()
        
        self.SubCatList.ItemsSource = self.all_subcat_items
        self.SearchBox_TextChanged(None, None)

    def TemplateList_SelectionChanged(self, sender, e):
        """Rafraîchit dynamiquement les statuts si l'utilisateur change de gabarit cible"""
        if self.all_subcat_items:
            self._update_subcategories_status()
            # Force WPF à rafraîchir le rendu visuel des éléments
            view = CollectionViewSource.GetDefaultView(self.SubCatList.ItemsSource)
            if view:
                view.Refresh()

    def SearchBox_TextChanged(self, sender, e):
        search_text = self.SearchBox.Text.lower()

        def apply_filter(item):
            # Le str(item) appelle automatiquement la méthode __str__ de SubCategoryViewModel
            return search_text in str(item).lower()

        for list_box in [self.CatList, self.SubCatList, self.TemplateList]:
            if list_box.ItemsSource:
                view = CollectionViewSource.GetDefaultView(list_box.ItemsSource)
                if view:
                    view.Filter = apply_filter

    def List_KeyDown(self, sender, e):
        is_ctrl_pressed = (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control
        if e.Key == Key.A and is_ctrl_pressed:
            e.Handled = True
            
            list_box = sender
            if list_box.ItemsSource:
                list_box.UnselectAll()
                filtered_view = CollectionViewSource.GetDefaultView(list_box.ItemsSource)
                for item in filtered_view:
                    list_box.SelectedItems.Add(item)

    def apply_visibility(self, state):
        # Extraction des objets sélectionnés (on récupère .Id et .DisplayName de nos modèles)
        selected_sub_items = list(self.SubCatList.SelectedItems)
        selected_templates = list(self.TemplateList.SelectedItems)

        if not selected_sub_items or not selected_templates:
            forms.alert("Sélection incomplète : Vérifiez les étapes 2 et 3.")
            return

        try:
            with revit.Transaction("Archi- | Gestion Visibilité"):
                for t_name in selected_templates:
                    template = next(v for v in DB.FilteredElementCollector(self._doc).OfClass(DB.View) 
                                    if v.Name == t_name)
                    
                    for item in selected_sub_items:
                        if template.CanCategoryBeHidden(item.Id):
                            template.SetCategoryHidden(item.Id, state)
            
            self.Close()
            forms.alert("Succès ! Les modifications ont été appliquées.", title="BIM-TEAM")
        except Exception as ex:
            forms.alert("Erreur lors de la transaction Revit :\n" + str(ex))

    def BtnHide_Click(self, sender, e): self.apply_visibility(True)
    def BtnShow_Click(self, sender, e): self.apply_visibility(False)


if __name__ == "__main__":
    folder = os.path.dirname(os.path.abspath(__file__))
    xaml_files = [f for f in os.listdir(folder) if f.lower().endswith('.xaml')]
    
    if xaml_files:
        xaml_path = os.path.join(folder, xaml_files[0])
        try:
            DiRootsStyleManager(xaml_path).ShowDialog()
        except Exception as ex:
            print("Erreur d'interface fatale : {}".format(str(ex)))
    else:
        forms.alert("Aucun fichier .xaml n'a été trouvé dans :\n" + folder)