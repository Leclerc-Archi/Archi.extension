# -*- coding: utf-8 -*-
import clr
import csv
import codecs
import datetime
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId, TaskDialogResult
from System.Windows.Forms import SaveFileDialog, OpenFileDialog, DialogResult, MessageBox

def action_import_revit():
    doc = __revit__.ActiveUIDocument.Document
    materials = FilteredElementCollector(doc).OfClass(Material)
    data = []
    
    for mat in materials:
        # Fonction utilitaire pour récupérer la valeur textuelle d'un paramètre
        def get_val(param_id):
            p = mat.get_Parameter(param_id)
            return p.AsString() if p and p.HasValue else ""
            
        # Extraction des données
        data.append([
            mat.Name, 
            mat.MaterialClass or "", 
            get_val(BuiltInParameter.ALL_MODEL_MARK),
            get_val(BuiltInParameter.ALL_MODEL_DESCRIPTION),
            get_val(BuiltInParameter.ALL_MODEL_MANUFACTURER),
            get_val(BuiltInParameter.ALL_MODEL_MODEL),
            get_val(BuiltInParameter.ALL_MODEL_COST),
            get_val(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        ])
    
    action_export(data)

def action_export(data):
    sfd = SaveFileDialog()
    sfd.Filter = "Fichiers CSV (*.csv)|*.csv"
    sfd.FileName = "Export_Materiaux_{}.csv".format(datetime.datetime.now().strftime("%Y-%m-%d"))
    
    if sfd.ShowDialog() == DialogResult.OK:
        try:
            with open(sfd.FileName, 'wb') as f:
                f.write(codecs.BOM_UTF8)
                writer = csv.writer(f, delimiter=';')
                # Mise à jour de l'en-tête
                writer.writerow(['Nom', 'Classe', 'Marque', 'Description', 'Fabricant', 'Modèle', 'Coût', 'Commentaires'])
                for row in data:
                    # Conversion en string sécurisée
                    writer.writerow([unicode(s).encode('utf-8') for s in row])
            MessageBox.Show("Fichier créé avec succès :\n" + sfd.FileName, "Succès")
        except Exception as e:
            MessageBox.Show("Erreur : " + str(e))

# --- MENU PRINCIPAL ---
td = TaskDialog("Gestion Matériaux")
td.MainInstruction = "Choisissez une action"
td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "1. Extraire les matériaux de Revit")
td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "2. Importer un fichier CSV")

result = td.Show()

if result == TaskDialogResult.CommandLink1:
    action_import_revit()
elif result == TaskDialogResult.CommandLink2:
    action_import_fichier()