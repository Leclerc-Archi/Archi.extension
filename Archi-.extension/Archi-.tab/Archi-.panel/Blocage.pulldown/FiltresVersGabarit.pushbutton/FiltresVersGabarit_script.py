# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#         SCRIPT D'APPLICATION DES FILTRES À UN GABARIT DE VUE REVIT
#------------------------------------------------------------------------------
#                                                      par Myriam N-M

import xlrd, os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packages.formulaires import * #package de fonctionnalitées utiles

from pyrevit import revit, script
from System.Collections.Generic import List
from Autodesk.Revit.DB import *

#------------------------------------------------------------------------------
#                     PARAMÈTRES DE TRAVAIL DE DÉPART
#------------------------------------------------------------------------------
# INFORMATIONS REVIT
doc = revit.doc

# GABARITS REVIT
gabarits = [
    g for g in FilteredElementCollector(doc).OfClass(View)
    if g.IsTemplate
]

gabarits_liste = []
for g in gabarits:
    gabarits_liste.append(g.Name)

gabarits_liste = sorted(gabarits_liste)
dico_gabarits = {g.Name:g for g in gabarits}

# PARAMÈTRES MODÈLE REVIT - SÉLECTION VALEURS PAR DÉFAUT FORMULAIRE
nom_param = "INF_CHEMIN DU FICHIER PROGRAMME EXCEL" # nom du param projet qui contient le chemin du fichier excel
nom_onglet = "LISTE DES LOCAUX"

# LOG DE SUIVI
class Message():
    def __init__(self, objet):
        self.objet = objet
    def suivi(self, message):
        return "{} : {}".format(self.objet, message)

#------------------------------------------------------------------------------
#                 VALEURS DE DÉPART POUR FORMULAIRE USAGER
#------------------------------------------------------------------------------
# CHEMIN DU FICHIER EXCEL DU PROGRAMME - EXISTANT
try:
    info_chemin = doc.ProjectInformation.LookupParameter(nom_param).AsString()
    if len(info_chemin) < 3:
        chemin = "C:\\"
    else:
        chemin = info_chemin
except:
    chemin = "C:\\"

#------------------------------------------------------------------------------
#            FORMULAIRE UTILISATEUR POUR LES DONNÉES DE TRAVAIL
#------------------------------------------------------------------------------
# PREMIER FORMULAIRE - CHEMIN DU FICHIER | GABARIT DE VUE
champs = [
    {"nom": "Chemin du fichier :", "type": "fichier", "default": chemin},#0
    {"nom": "Gabarit de vue :", "type": "liste", "options": gabarits_liste, "default": 0}
]

form = Formulaire(titre="Filtres programmatique : données utilisateur", largeur=600, champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    chemin_excel = data["Chemin du fichier :"]
    nom_gabarit = data["Gabarit de vue :"]
else:
    script.exit()

# DEUXIÈME FORMULAIRE - SÉLECTION DE LA FEUILLE DANS LE FICHIER EXCEL
# Récuper la liste des feuilles dans le fichier excel pour la sélection
try:
    fichier_excel = xlrd.open_workbook(chemin_excel)
    noms_feuilles = fichier_excel.sheet_names()
except Exception as e:
    TaskDialog.Show("Erreur", "Erreur de lecture du fichier excel\nValider le chemin et le type du fichier")
    script.exit()

feuille_idx = noms_feuilles.index(nom_onglet) or 0
champs = [
    {"nom": "Onglet de programme :", "type": "liste", "options": noms_feuilles, "default": feuille_idx}
]

# Formulaire de sélection
form = Formulaire(titre="Chosir l'onglet de programme", largeur=600, champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    nom_feuille = data["Onglet de programme :"]
else:
    script.exit()

#------------------------------------------------------------------------------
#          LECTURE ET TRAITEMENT DES DONNÉES DE LA FEUILLE EXCEL
#------------------------------------------------------------------------------
# VARIABLES DE TRAVAIL
dico_couleur = {}# dictionnaire des couleurs de filtre

# LECTURE FEUILLE EXCEL
feuille_excel = fichier_excel.sheet_by_name(nom_feuille)# lecture de la feuille excel

# NOMS DES ENTÊTES POUR RÉCUPÉRER LES DONNÉES
liste_filtres = ['dept', 'filtre']

# TRAITEMENT DES DONNÉES (VOIR PACKAGE FORMULAIRES)
filtres = vals_col(feuille_excel, liste_filtres, 3)
for dept, couleur in filtres.values():
    dico_couleur[dept] = hex_a_rvb(couleur)

#------------------------------------------------------------------------------
#           GESTION ET CRÉATION DES FILTRES REVIT PAR DÉPARTEMENT
#------------------------------------------------------------------------------
# VARIABLES DE TRAVAIL
vals_filtres = sorted(dico_couleur.keys())# valeur du département utilisé pour appliquer le filtre
param_filtre = 0
view = dico_gabarits[nom_gabarit]

dico_regles = {}# dictionnaire des règles existantes
noms_regles_exist = []# liste des noms des règles existantes
noms_filtres = []#liste des noms de filtre tel qu'ils apparaîtront dans les paramètres de vue
dico_filtres = {}# dictionnaire des filtres de blocage et de leurs noms tel qu'ils apparaîtront dans les paramètres de vue

# VARIABLES DE SUIVI
nouveaux = []
existants = []
enusage = []
effaces = []

# DONNÉES REVIT
params_partages = FilteredElementCollector(doc).OfClass(SharedParameterElement)
regles_existantes = FilteredElementCollector(doc).OfClass(ParameterFilterElement)


# DICTIONNAIRE DES FILTRES EXISTANTS PAR NOM
for regle in regles_existantes:
    nom_regle_exist = regle.Name
    noms_regles_exist.append(nom_regle_exist)
    dico_regles[nom_regle_exist] = regle

# CRÉATION DES NOMS DE FILTRE & DICO PAR NOM DE DÉPARTEMENT 
for valeur in vals_filtres:
    nom_filtre = 'BLOCAGE - ' + valeur 
    noms_filtres.append(nom_filtre)# nom pour le filtre
    dico_filtres[valeur] = nom_filtre

# RÉCUPÈRE LE PARAMÈTRE PARTAGÉ AUQUEL EST ASSOCIÉ LA RÈGLE DE FILTRE
for param in params_partages:
    if(param.Name == 'DÉPARTEMENT'):# valeur pour le filtre
        param_filtre = param

# SÉLECTION DE LA CATÉGORIE DE FAMILLES AFFECTÉE PAR LE FILTRE (COMPOSANTS DE DÉTAILS)
categorie = Category.GetCategory(doc, BuiltInCategory.OST_DetailComponents).Id

# CAST
liste_categorie = [categorie]
lst_categorie_typ = List[ElementId](liste_categorie)

#------------------------------------------------------------------------------
#                     APPLICATION DES FILTRES DANS REVIT
#------------------------------------------------------------------------------
with revit.Transaction('création des filtres'):
    # NETTOYAGE DES FILTRES EXISTANTS
    for nom_regle in dico_regles.keys():
        if 'BLOCAGE' in nom_regle and nom_regle not in noms_filtres:
            doc.Delete(dico_regles[nom_regle].Id)
            effaces.append(Message(nom_regle).suivi('filtre supprimé'))

    # CRÉATION ET GESTION DES FILTRES
    for valeur, nom in dico_filtres.items():
        if nom not in noms_regles_exist:# valide si la règle existe déjà basé sur le nom
            regle = ParameterFilterRuleFactory.CreateContainsRule(param_filtre.Id, valeur, lst_categorie_typ)
            filtre = ParameterFilterElement.Create(doc, nom, lst_categorie_typ)

            # APPLICATION DE LA RÈGLE ET DU FILTRE
            nouvelle_regle = ElementParameterFilter(regle)
            filtre.SetElementFilter(nouvelle_regle)
            view.AddFilter(filtre.Id)
            nouveaux.append(Message(nom).suivi('nouveau filtre'))

        else:# récupère le filtre pré-existant, le cas échéant
            filtre = dico_regles[nom]
            try:# assigne le filtre existant à la vue courante - except s'il est déjà assigné
                view.AddFilter(filtre.Id)
                existants.append(Message(nom).suivi('filtre existant'))
            except:
                enusage.append(Message(nom).suivi('filtre déjà en usage'))
        
        # APPLICATION DE LA COULEUR AU FILTRE
        pochage = view.GetFilterOverrides(filtre.Id)
        couleur_pochage = pochage.SetSurfaceForegroundPatternColor(dico_couleur[valeur])
        view.SetFilterOverrides(filtre.Id, couleur_pochage)
    

#------------------------------------------------------------------------------
#                               SUIVI DES TÂCHES
#------------------------------------------------------------------------------
champs = sorted(effaces + enusage + existants + nouveaux)
description = 'Suivi des filtres supprimés, créés et existants'
form = Dialogue_suivi('Suivi des filtres', description, champs)
form.ShowDialog()