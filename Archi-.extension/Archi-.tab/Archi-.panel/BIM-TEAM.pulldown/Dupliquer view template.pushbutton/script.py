# -*- coding: utf-8 -*-
__title__ = "Gestion\nGabarits"
__author__ = "BIM-TEAM Archi-"

from pyrevit import revit, DB, forms, script
import os
import re
from System.Collections.Generic import List
from System.Windows.Data import CollectionViewSource
from System.Windows.Input import Key, ModifierKeys, Keyboard

class TemplateManagerWPF(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._doc = revit.doc
        
        self.template_maps = {}
        self.all_template_names = []
        
        self._setup_initial_data()
        self._bind_events()

    def _setup_initial_data(self):
        """Récupère et trie les gabarits de vues présents dans le projet"""
        all_views = DB.FilteredElementCollector(self._doc).OfClass(DB.View).ToElements()
        view_templates = [v for v in all_views if v.IsTemplate]

        if not view_templates:
            forms.alert("Aucun gabarit de vue trouvé dans le projet.")
            self.Close()
            script.exit()

        # Dictionnaire de mappage { Nom: ObjetÉlément }
        self.template_maps = {t.Name: t for t in view_templates}
        self.all_template_names = sorted(self.template_maps.keys())
        
        # Liaison des données à la ListBox
        self.TemplateList.ItemsSource = self.all_template_names

    def _bind_events(self):
        # Filtrage en direct de la barre de recherche
        self.SearchBox.TextChanged += self.SearchBox_TextChanged
        
        # Raccourci Ctrl+A pour sélectionner tous les éléments filtrés
        self.TemplateList.KeyDown += self.TemplateList_KeyDown
        
        # Liaison du clic du bouton d'exécution
        self.BtnExecute.Click += self.BtnExecute_Click

    def SearchBox_TextChanged(self, sender, e):
        """Filtre dynamiquement la liste des gabarits à la saisie"""
        search_query = self.SearchBox.Text.lower()

        def apply_filter(item):
            return search_query in str(item).lower()

        if self.TemplateList.ItemsSource:
            view = CollectionViewSource.GetDefaultView(self.TemplateList.ItemsSource)
            if view:
                view.Filter = apply_filter

    def TemplateList_KeyDown(self, sender, e):
        """Permet la sélection globale par Ctrl+A des gabarits affichés"""
        is_ctrl_pressed = (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control
        if e.Key == Key.A and is_ctrl_pressed:
            e.Handled = True
            if self.TemplateList.ItemsSource:
                self.TemplateList.UnselectAll()
                filtered_view = CollectionViewSource.GetDefaultView(self.TemplateList.ItemsSource)
                for item in filtered_view:
                    self.TemplateList.SelectedItems.Add(item)

    def BtnExecute_Click(self, sender, e):
        """Exécute l'opération de renommage ou duplication"""
        selected_names = list(self.TemplateList.SelectedItems)
        search_text = self.TxtSearch.Text
        replace_text = self.TxtReplace.Text

        # Validations de sécurité
        if not selected_names:
            forms.alert("Veuillez sélectionner au moins un gabarit.")
            return
        if not search_text:
            forms.alert("Veuillez indiquer le texte à rechercher.")
            return
        if replace_text is None:
            replace_text = ""

        # Détermination du mode choisi
        is_duplicate_mode = self.RadioDuplicate.IsChecked
        mode_label = "Dupliquer" if is_duplicate_mode else "Renommer"

        processed_count = 0

        # Lancement de la transaction Revit unique
        with revit.Transaction("BIM-TEAM | {} Gabarits".format(mode_label)):
            for name in selected_names:
                template = self.template_maps[name]

                # Vérification de la présence de la chaîne (Insensible à la casse)
                if search_text.lower() in template.Name.lower():
                    pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                    new_name = pattern.sub(replace_text, template.Name)

                    try:
                        target_element = None

                        # --- LOGIQUE DE DUPLICATION ---
                        if is_duplicate_mode:
                            ids_to_copy = List[DB.ElementId]([template.Id])
                            copied_ids = DB.ElementTransformUtils.CopyElements(self._doc, ids_to_copy, DB.XYZ.Zero)
                            if copied_ids:
                                target_element = self._doc.GetElement(copied_ids[0])
                        # --- LOGIQUE DE RENOMMAGE DIRECT ---
                        else:
                            target_element = template

                        # Affectation du nom et boucle pour éviter les doublons existants
                        if target_element:
                            final_name = new_name
                            suffix = 1
                            while True:
                                try:
                                    target_element.Name = final_name
                                    break
                                except:
                                    final_name = "{} ({})".format(new_name, suffix)
                                    suffix += 1

                            print("SUCCÈS : {} -> {}".format(name, final_name))
                            processed_count += 1

                    except Exception as ex:
                        print("ERREUR sur {} : {}".format(template.Name, ex))
                else:
                    print("IGNORÉ : '{}' ne contient pas '{}'".format(template.Name, search_text))

        self.Close()
        forms.alert("{} gabarits ont été traités (Mode: {}).".format(processed_count, mode_label), title="BIM-TEAM")


if __name__ == "__main__":
    folder = os.path.dirname(os.path.abspath(__file__))
    xaml_files = [f for f in os.listdir(folder) if f.lower().endswith('.xaml')]
    
    if xaml_files:
        xaml_path = os.path.join(folder, xaml_files[0])
        try:
            TemplateManagerWPF(xaml_path).ShowDialog()
        except Exception as ex:
            print("Erreur d'interface fatale : {}".format(str(ex)))
    else:
        forms.alert("Aucun fichier .xaml trouvé dans le répertoire.")