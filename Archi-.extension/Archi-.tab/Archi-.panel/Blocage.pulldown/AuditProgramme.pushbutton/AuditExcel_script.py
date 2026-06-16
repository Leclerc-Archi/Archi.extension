# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#        AUDIT DES BLOCS 2D MODÉLISÉS DANS LA VUE COURANTE (QUANTITÉS)
#------------------------------------------------------------------------------
#                                                      par Myriam N-M

import xlrd, math, os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packages.formulaires import * #package de fonctionnalitées utiles

from pyrevit import revit, script
from collections import Counter
from System.Collections.Generic import List
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog

#------------------------------------------------------------------------------
#                     PARAMÈTRES DE TRAVAIL DE DÉPART
#------------------------------------------------------------------------------
# INFORMATIONS REVIT
doc = revit.doc
view = doc.ActiveView

# PARAMÈTRES DE LA FAMILLE 2D
identifiant = 'ELD_ID'
nom_piece = 'NOM-DE-PIÈCE'
numero_piece = 'NUMÉRO'
departement = 'DÉPARTEMENT'
superficie_prog = 'SUPERFICIE-NETTE-PFT'
superficie_relle = 'SUPERFICIE-NETTE-RÉELLE'
largeur_fam = 'LARGEUR'
profondeur_fam = 'PROFONDEUR'

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
# PREMIER FORMULAIRE - FAMILLE 2D | CHEMIN DU FICHIER | FILTRE & NOM DE FILTRE
champs = [
    {"nom": "Chemin du fichier :", "type": "fichier", "default": chemin},#1
    {"nom": "Filtre de groupe?", "type": "bool", "default": False},#2
    {"nom": "Nom du filtre :", "type": "texte", "default": None}#3
]

form = Formulaire(titre="Blocage 2D : données utilisateur", largeur=600, champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    chemin_excel = data["Chemin du fichier :"]
    filtre_bool = data["Filtre de groupe?"]
    nom_filtre_gr = data["Nom du filtre :"]
else:
    script.exit()

# ROUTINE POUR DEMANDER NOM DU FILTRE SI OPTION COCHÉ MAIS AUCUN NOM ENTRÉ
while filtre_bool and nom_filtre_gr == '':
    champs = [
        {"nom": "Nom du filtre :", "type": "texte", "default": None}
    ]
    form = Formulaire(titre="Indiquer le nom du filtre", largeur=600, champs=champs)
    if form.ShowDialog() == DialogResult.OK:
        data = form.valeurs()
        nom_filtre_gr = data["Nom du filtre :"]
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
data = []# données pour la création des pièces
dico_couleur = {}# dictionnaire des couleurs de filtre

# LECTURE FEUILLE EXCEL
feuille_excel = fichier_excel.sheet_by_name(nom_feuille)# lecture de la feuille excel

# NOMS DES ENTÊTES POUR RÉCUPÉRER LES DONNÉES
liste_entetes = ['groupe', 'dept', 'filtre', 'num', 'nom', 'sup', 'nb']
liste_filtres = ['dept', 'filtre']
idx_donnee = 0 #compteur d'index
idx_donnees = {}
for entete in liste_entetes:
    idx_donnees[entete] = idx_donnee
    idx_donnee += 1

# TRAITEMENT DES DONNÉES (VOIR PACKAGE FORMULAIRES)
data = vals_col(feuille_excel, liste_entetes, 0)
filtres = vals_col(feuille_excel, liste_filtres, 3)
for dept, couleur in filtres.values():
    dico_couleur[dept] = hex_a_rvb(couleur)

#------------------------------------------------------------------------------
#                    GESTION ET PRÉPARATION DES BLOCS 2D
#------------------------------------------------------------------------------
# VARIABLES DE TRAVAIL
numeros = []
dico_elements = []
doublons = []
orphelins = []
suivi_doublons = []
suivi_orphelins = []
suivi = ""

# VARIABLES DE SUIVI
erreur_param = set()# pour suivi des erreurs de assigner_val
ajour = []# contiendra tous les blocs existants mis à jour
erreur = []# contiendra tous les blocs pour lesquels une Erreur est survenue (devrait TOUJOURS être vide; là pour cas imprévisibles)

# GESTION DES ÉLÉMENTS DE DÉTAILS EXISTANTS POUR LA MISE À JOUR
elements = FilteredElementCollector(doc, view.Id).OfCategory(
    BuiltInCategory.OST_DetailComponents).ToElements()

for e in elements:
    id_e = e.LookupParameter(identifiant)
    nom_e = e.LookupParameter(nom_piece)
    id_ref = Parameter.AsString(id_e)
    nom_ref = Parameter.AsString(nom_e)
    doublons.append('{} - {}'.format(id_ref, nom_ref))
    if id_ref not in dico_elements:
        dico_elements.append(id_ref)

compte_valeurs = Counter(doublons)

# FILTRE DES VALEURS QUI ONT PLUS D'UNE OCCURENCE
valeurs_en_double = [valeur for valeur, compte in compte_valeurs.items() if compte > 1]

for valeur, compte in compte_valeurs.items():
    if compte > 1:
        texte = "{} apparaît {} fois".format(valeur, compte)
        suivi_doublons.append(texte)

# APPLICATION DU FILTRE DE GROUPE AUX DONNÉES EXCEL, LE CAS ÉCHÉANT
if filtre_bool:
    suivi_filtre = []
    for key, value in data.items():
        if nom_filtre_gr not in value[idx_donnees['groupe']]:
            del data[key]
            suivi_filtre.append("[{}] {}".format(key, value[idx_donnees['nom']]))
    description = 'Les pièces suivantes sont exclues par le filtre de groupe'
    form = Dialogue_suivi("Filtre de groupe", description, suivi_filtre)
    form.ShowDialog()

# FILTRE DES VALEURS QUI N'ONT PAS D'OCCURENCE (DIT 'ORPHELIN')
for id_i, [grp, dept, flt, num, nom, sup, nb] in sorted(data.items()):
        numeros.append(num)
        for i in range(int(nb)):
            nouveau_id = str(id_i) + str(i)
            orphelins.append([nouveau_id, '{} - {} est manquant'.format(nouveau_id, nom)])

for id_ref, texte in orphelins:
    if id_ref not in dico_elements:
        suivi_orphelins.append(texte)

#------------------------------------------------------------------------------
#                               SUIVI DE L'AUDIT
#------------------------------------------------------------------------------
if suivi_doublons:
    suivi += 'SUIVI DES DOUBLONS\n\n'
    suivi += '\n'.join(suivi_doublons)
    suivi += '\n\n\n'

if suivi_orphelins:
    suivi += "SUIVI DES ÉLÉMENTS MANQUANTS\n\n"
    suivi += '\n'.join(suivi_orphelins)

if suivi != "":
    form = Dialogue_suivi(titre="Audit du programme",
                          description="Résultats de l'audit :",
                          donnees=("",suivi),
                          largeur=600,
                          longueur=400)

else:
    form = Dialogue_suivi(titre="Audit du programme",
                          description="Résultats de l'audit :",
                          donnees=("","Rien à signaler!"),
                          largeur=300,
                          longueur=300)

form.ShowDialog()