# -*- coding: utf-8 -*-
# FICHIER DE DÉFITIONS POUR QUALITY OF LIFE DANS LES SCRIPTS #
import pyrevit

from System.Windows.Forms import *
from System.Drawing import Font, FontStyle
from System.Drawing import Point as SysPoint
from System.Drawing import Size as SysSize
from Autodesk.Revit.DB import Color

#--------------------------------------------------------------
#            CRÉATION DE FORMULAIRES MICROSOFT
#--------------------------------------------------------------
format_txt = Font("Microsoft Sans Serif", 9, FontStyle.Regular)
h_ligne = 30
h_champs = 25

#-------------DIALOGUE DE SUIVI DES TÂCHES---------------------
class Dialogue_suivi(Form):
    def __init__(self, titre="Nouveau dialogue", description=None, donnees=None, largeur=800, longueur=600):
        self.Text = titre
        self.Size = SysSize(largeur, longueur)
        self.Font = format_txt
        self.StartPosition = FormStartPosition.CenterScreen
        self.FormBorderStyle = FormBorderStyle.Sizable
        self.MaximizeBox = True
        self.MinimizeBox = False

        #valeurs de travail pour les donnees
        self.largeur = largeur
        self.longueur = longueur
        self.donnees = donnees or []
        self.description = description
        self._cree_dialogue()

    def _cree_dialogue(self):
        longueur = self.longueur
        largeur = self.largeur
        donnees = self.donnees
        x, y = 10, 10
        largeur_btn = 80

        if self.description:
            hauteur = h_ligne
            description = Label()
            description.Text = self.description
            description.Location = SysPoint(x, y)
            description.Size = SysSize(largeur-40, hauteur)
            self.Controls.Add(description)
            y = hauteur+h_ligne
            longueur -= y+(5*h_ligne)

        boite_texte = Panel()
        boite_texte.AutoScroll = True
        boite_texte.Location = SysPoint(x, y)
        boite_texte.Size = SysSize(largeur-40, longueur)
        y += longueur + h_ligne

        message = Label()
        message.Text = '\n'.join(donnees)
        message.AutoSize = True
        message.Location = SysPoint(0, 0)

        boite_texte.Controls.Add(message)
        self.Controls.Add(boite_texte)

        btn_ok = Button()
        btn_ok.Text = "Fermer"
        btn_ok.Location = SysPoint((largeur-largeur_btn)/2, y)
        btn_ok.Size = SysSize(largeur_btn, h_ligne)
        btn_ok.Click += self._on_ok
        self.Controls.Add(btn_ok)

    def _on_ok(self, sender, args):
        self.DialogResult = DialogResult.OK
        self.Close()


#-------------FORMULAIRE DE DONNÉES UTILISATEUR-----------------
class Formulaire(Form):
    def __init__(self, titre="Nouveau formulaire", largeur=400, champs=None):
        #données de départ
        ratio_marge = 3*h_ligne
        marge = ratio_marge + h_ligne

        self.Text = titre
        self.Width = largeur
        self.Height = marge + (h_ligne * len(champs or []))
        self.Font = format_txt
        self.StartPosition = FormStartPosition.CenterScreen
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.MinimizeBox = False
        self.pos_boutons = self.Height - ratio_marge

        #valeurs de travail pour les champs
        self.largeur = largeur
        self.champs = champs or []
        self.entrees = {}
        self._cree_formulaire()

    def _cree_formulaire(self):
        y = h_ligne/2
        l = self.largeur
        ratio_etiquette = .40
        ratio_entree = 1-ratio_etiquette
        p_entree = l*ratio_etiquette
        l_etiquette = l*ratio_etiquette-20
        l_entree = l*ratio_entree-40
        
        #traitement des champs d'entrées
        for champ in self.champs:
            nom = champ["nom"]
            ftype = champ.get("type", "texte")
            options = champ.get("options", [])
            default = champ.get("default", "")

            etiquette = Label()
            etiquette.Text = nom
            etiquette.Location = SysPoint(10, y + 3)
            etiquette.Size = SysSize(l_etiquette, h_champs)
            self.Controls.Add(etiquette)

            if ftype == "texte":
                entree_ctrl = TextBox()
                entree_ctrl.Text = default
                entree_ctrl.Location = SysPoint(p_entree, y)
                entree_ctrl.Size = SysSize(l_entree, h_champs)

            elif ftype == "liste":
                entree_ctrl = ComboBox()
                entree_ctrl.Items.AddRange(tuple(options))
                entree_ctrl.SelectedIndex = default if default else 0 if options else -1
                entree_ctrl.Location = SysPoint(p_entree, y)
                entree_ctrl.Size = SysSize(l_entree, h_champs)

            elif ftype == "couleur":
                entree_ctrl = Button()
                entree_ctrl.Text = "Choisir Couleur"
                entree_ctrl.Tag = default or Color.White
                entree_ctrl.BackColor = entree_ctrl.Tag
                entree_ctrl.Location = SysPoint(p_entree, y)
                entree_ctrl.Size = SysSize(l_entree, h_champs)
                entree_ctrl.Click += self._choisir_couleur

            elif ftype == "bool":
                entree_ctrl = CheckBox()
                entree_ctrl.Checked = bool(default)
                entree_ctrl.Location = SysPoint(p_entree, y)
                entree_ctrl.Size = SysSize(20, 20)

            elif ftype == "fichier":
                textbox = TextBox()
                textbox.Text = default
                textbox.Location = SysPoint(p_entree, y)
                textbox.Size = SysSize(l*.25, h_champs)

                browse_btn = Button()
                browse_btn.Text = "Parcourir"
                browse_btn.Tag = textbox
                browse_btn.Location = SysPoint(p_entree+(l*.25)+10, y - 1)
                browse_btn.Size = SysSize(l*.25, h_champs)
                browse_btn.Click += self._choisir_fichier

                self.Controls.Add(textbox)
                self.Controls.Add(browse_btn)
                entree_ctrl = textbox  # use textbox as main entree

            else:
                continue  # skip unsupported

            self.Controls.Add(entree_ctrl)
            self.entrees[nom] = entree_ctrl
            y += h_ligne

        # OK / Annuler
        btn_ok = Button()
        btn_ok.Text = "Confirmer"
        btn_ok.Location = SysPoint(l*.20, self.pos_boutons)
        btn_ok.Size = SysSize(l*.25, h_champs)
        btn_ok.Click += self._on_ok
        self.Controls.Add(btn_ok)

        btn_annuler = Button()
        btn_annuler.Text = "Annuler"
        btn_annuler.Location = SysPoint(l*.50, self.pos_boutons)
        btn_annuler.Size = SysSize(l*.25, h_champs)
        btn_annuler.Click += self._on_annuler
        self.Controls.Add(btn_annuler)

    def _choisir_couleur(self, sender, event):
        dlg = ColorDialog()
        if dlg.ShowDialog() == DialogResult.OK:
            sender.BackColor = dlg.Color
            sender.Tag = dlg.Color

    def _choisir_fichier(self, sender, event):
        dlg = OpenFileDialog()
        if dlg.ShowDialog() == DialogResult.OK:
            sender.Tag.Text = dlg.FileName

    def _on_ok(self, sender, args):
        self.DialogResult = DialogResult.OK
        self.Close()

    def _on_annuler(self, sender, args):
        self.DialogResult = DialogResult.Cancel
        self.Close()
    
    def _on_fermer(self, sender, event):
        if self.DialogResult != DialogResult.OK:
            self.DialogResult = DialogResult.Cancel

    def valeurs(self):
        results = {}
        for nom, ctrl in self.entrees.items():
            if isinstance(ctrl, TextBox):
                results[nom] = ctrl.Text
            elif isinstance(ctrl, ComboBox):
                results[nom] = ctrl.SelectedItem
            elif isinstance(ctrl, Button) and hasattr(ctrl, "Tag"):
                results[nom] = ctrl.Tag  # Color
            elif isinstance(ctrl, CheckBox):
                results[nom] = ctrl.Checked
        return results

# fonction pour convertir les valeurs hexadecimales en rvb
def hex_a_rvb(hex_code):

    hex_code = hex_code.lstrip('#')  # supprime '#' du code
    r_hex = hex_code[0:2]
    v_hex = hex_code[2:4]
    b_hex = hex_code[4:6]

    try:
        r = int(r_hex, 16)
        v = int(v_hex, 16)
        b = int(b_hex, 16)
    
    except:
        r, v, b = 0, 0, 0

    return (Color(r, v, b))

# fonction pour récupérer les valeurs selon les noms d'entêtes donnés
def vals_col(feuille, valeurs, id_idx):
    val_dict = {}
    col_idx = []
    headers = feuille.row_values(0)
    for valeur in valeurs:
        if valeur in headers:
            col_idx.append(headers.index(valeur))
    for idx in col_idx:
        for row_idx in range(1, feuille.nrows):
            id_val = feuille.cell_value(row_idx, id_idx)
            cell_val = feuille.cell_value(row_idx, idx)
            if id_val and cell_val is not None and id_val != 'ID':
                if id_val in val_dict:
                    val_dict[id_val].append(cell_val)
                else:
                    val_dict[id_val] = [cell_val]
    return val_dict