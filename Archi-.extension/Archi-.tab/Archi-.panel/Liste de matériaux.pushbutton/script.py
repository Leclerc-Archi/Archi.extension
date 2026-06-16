# -*- coding: utf-8 -*-
import clr, sys, os, json, codecs, xlrd
clr.AddReference('System')
clr.AddReference('System.Windows.Forms')
clr.AddReference('RevitAPI')
clr.AddReference('RevitServices')

from System import Array, String
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, script
import System.Windows.Forms as WinForms

# chemin du fichier de paramètres
config_path = os.path.join(os.getenv('APPDATA'), 'pyrevit_config_tableau_materiaux.json')

# chargement des paramètres du fichier s'il existe
user_config = {}
if os.path.exists(config_path):
    try:
        with codecs.open(config_path, 'r', 'utf-8') as f:
            user_config = json.load(f)
    except:
        user_config = {}

# 1. document actif
doc = revit.doc
if not doc:
    TaskDialog.Show('Erreur', 'Aucun document Revit actif.')
    sys.exit()

# 2. sélection des nommenclatures dans Revit
nommenclatures = list(
    FilteredElementCollector(doc).OfClass(ViewSchedule)
)
noms_nomms = sorted([
    nm.Name for nm in nommenclatures
])
if not noms_nomms:
    TaskDialog.Show('Erreur', 'Aucun type de pochage trouvé.')
    sys.exit()

idx_nomm = noms_nomms.index('LISTE DES MATÉRIAUX ET FINIS') if 'LISTE DES MATÉRIAUX ET FINIS' in noms_nomms else 0

# 3. données utilisateur
def afficher_formulaire():
    posX = 10
    posY = 10
    ligneH = 30
    form = WinForms.Form(Text='Liste des matériaux')
    form.Width, form.Height = 500, 450
    form.StartPosition = WinForms.FormStartPosition.CenterScreen

    # sélecteur de nommenclature
    form.Controls.Add(
        WinForms.Label(Text='Sélectionner la nommenclature :',
                    Left=posX, Top=posY, Height=ligneH, Width=340))

    posY += 40
    comboNomm = WinForms.ComboBox(Left=posX, Top=posY, Height=ligneH, Width=460, DropDownStyle=WinForms.ComboBoxStyle.DropDownList)
    comboNomm.Items.AddRange(Array[String](noms_nomms))

    # récupération comboNomm s'il existe
    prev_nomm = user_config.get('comboNomm')
    if prev_nomm and prev_nomm in noms_nomms:
        comboNomm.SelectedIndex = noms_nomms.index(prev_nomm)
    else:
        comboNomm.SelectedIndex = idx_nomm
    form.Controls.Add(comboNomm)

    # sélecteur de fichier Excel
    posY += 60
    form.Controls.Add(
        WinForms.Label(Text='Fichier excel :',
                       Left=posX, Top=posY, Height=ligneH, Width=340))
    posY += 40
    txtPath = WinForms.TextBox(Left=posX, Top=posY, Height=ligneH, Width=460, ReadOnly=True)
    txtPath.Text = user_config.get('txtPath', '')
    form.Controls.Add(txtPath)

    def browse_click(sender, arg):
        dlg = WinForms.OpenFileDialog(
            Filter='Fichiers Excel (*.xlsx;*.xls)|*.xlsx;*.xls')
        if dlg.ShowDialog() != WinForms.DialogResult.OK:
            return
        txtPath.Text = dlg.FileName
        # lecture des noms de feuilles
        try:
            wb = xlrd.open_workbook(txtPath.Text, encoding_override='utf-8')
            noms_feuilles = wb.sheet_names()
        except Exception as e:
            WinForms.MessageBox.Show('Erreur lecture Excel :\n{}'.format(str(e)))
            noms_feuilles = []
        finally:
            comboFeuille.Items.Clear()

        if noms_feuilles:
            comboFeuille.Items.AddRange(Array[String](noms_feuilles))
            if 'PROJET' in noms_feuilles:
                idx_feuille = noms_feuilles.index('PROJET')
            else:
                idx_feuille = 0
            comboFeuille.SelectedIndex = idx_feuille

    # bouton 'Parcourir'
    posY += -40
    btnBrowse = WinForms.Button(
        Text=u'Parcourir',
        Left=posX + 360, Top=posY, Height=ligneH, Width=100)
    btnBrowse.Click += browse_click
    form.Controls.Add(btnBrowse)

    # sélecteur de feuille
    posY += 100
    form.Controls.Add(
        WinForms.Label(Text=u'Feuille :',
                    Left=posX, Top=posY, Height=ligneH, Width=460))

    posY += 40
    comboFeuille = WinForms.ComboBox(Left=posX, Top=posY, Height=ligneH, Width=460, DropDownStyle=WinForms.ComboBoxStyle.DropDownList)

    # récupération comboFeuille s'il existe
    prev_feuille = user_config.get('comboFeuille')
    if prev_feuille:
        comboFeuille.Items.Add(prev_feuille)
        comboFeuille.SelectedIndex = 0

    form.Controls.Add(comboFeuille)

    # bouton OK
    posY += 60
    btnOK = WinForms.Button(Text='OK',
                            DialogResult=WinForms.DialogResult.OK,
                            Left=posX + 185, Top=posY,
                            Height=ligneH, Width=80)
    form.AcceptButton = btnOK
    form.Controls.Add(btnOK)

    if form.ShowDialog() == WinForms.DialogResult.OK:
        # enregistrement des paramètres format UTF-8
        new_data = {
            'comboNomm': comboNomm.Text,
            'txtPath': txtPath.Text,
            'comboFeuille': comboFeuille.Text
        }
        with codecs.open(config_path, 'w', 'utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False)
        return (comboNomm.Text, txtPath.Text, comboFeuille.Text)
    return None, None, None

# 4. récupération des données utilisateur
nom_nomm, path_fichier_excel, nom_feuille_excel = afficher_formulaire()
if not all([nom_nomm, path_fichier_excel, nom_feuille_excel]):
    sys.exit()

# 5. valeurs excel
fichier_excel = xlrd.open_workbook(path_fichier_excel, encoding_override='utf-8')
feuille_excel = fichier_excel.sheet_by_name(nom_feuille_excel)

header_idx = 3
headers = feuille_excel.row_values(header_idx)

num = headers.index('CODE')
descr = headers.index('DESCRIPTION')
rev = headers.index('REV.')

data = []

def valeur_cell(row_idx, col_idx):
    return feuille_excel.cell_value(row_idx, col_idx)

for row in range(5, feuille_excel.nrows):
    data.append([valeur_cell(row, num), valeur_cell(row, descr), valeur_cell(row, rev)])

# 6. nommenclature et écriture
ajour, erreur, tbshoot = [], [], []
nbLignes = len(data)

with revit.Transaction('écriture nommenclature'):
    for nm in nommenclatures:
        if str(nm.Name) == nom_nomm:
            elements = FilteredElementCollector(doc, nm.Id).ToElements()
            for e in elements:
                doc.Delete(e.Id)

            for i in range(nbLignes):
                table = nm.GetTableData()
                tableSection = table.GetSectionData(SectionType.Body)
                newe = tableSection.InsertRow(0)

            newElements = FilteredElementCollector(doc, nm.Id).ToElements()

            nb = 0
            for num, descr, rev in data:
                ligne = newElements[nb]
                nb = nb + 1
                try:
                    ligne.LookupParameter('Nom de la clé').Set(num or '')
                    ligne.LookupParameter('Commentaires').Set(descr or '')
                    ligne.LookupParameter('RÉVISION').Set(rev or '')
                    if num and num[-2:] == "xx":
                        ligne.LookupParameter('SECTION').Set("xx")
                    if num is not None:
                        ajour.append('  {0} - {1}\n'.format(num, descr))
                except:
                    if num is None:
                        pass
                    else:
                        erreur.append('  {0} - {1}\n'.format(num, descr))

TaskDialog.Show('Tâche complétée',
    'Liste des matériaux à jour')