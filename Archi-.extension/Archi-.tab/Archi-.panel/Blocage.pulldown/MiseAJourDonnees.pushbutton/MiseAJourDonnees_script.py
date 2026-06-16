# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#         SCRIPT DE CRÉATION DES BLOCS PROGRAMMATIQUES ET DES FILTRES
#------------------------------------------------------------------------------
#                                                      par Myriam N-M

import xlrd, math, os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packages.formulaires import * #package de fonctionnalitées utiles

from pyrevit import revit, script
from System.Collections.Generic import List
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog

#------------------------------------------------------------------------------
#                        PARAMÈTRES DE TRAVAIL DE DÉPART
#------------------------------------------------------------------------------
# INFORMATIONS MODÈLE REVIT
doc = revit.doc
view = doc.ActiveView
view_gabarit = doc.GetElement(view.ViewTemplateId)
gabarit_ok = False

# PARAMÈTRES DE LA FAMILLE 2D POUR CRÉATION ET ÉCRITURE
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
]

form = Formulaire(titre="Blocage 2D : données utilisateur", largeur=600, champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    chemin_excel = data["Chemin du fichier :"]
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
feuille_excel = fichier_excel.sheet_by_name(nom_feuille)

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

#------------------------------------------------------------------------------
#                    GESTION ET PRÉPARATION DES BLOCS 2D
#------------------------------------------------------------------------------
# VARIABLES DE SUIVI
erreur_param = set()# pour suivi des erreurs de assigner_val
ajour = []# contiendra tous les blocs existants mis à jour
erreur = []# contiendra tous les blocs pour lesquels une Erreur est survenue (devrait TOUJOURS être vide; là pour cas imprévisibles)

# VALIDATION ET CONVERSION DES UNITÉS, LE CAS ÉCHÉANT (API REVIT REQUIERT NATIF IMPÉRIAL)
unites = doc.GetUnits()
surf_format = unites.GetFormatOptions(SpecTypeId.Area)
surf_unite = surf_format.GetUnitTypeId()# format des univtés de surface Revit
imperial = surf_unite == UnitTypeId.SquareFeet

if not imperial:
    for d in data.values():
        sup = d[idx_donnees['sup']]
        sup = UnitUtils.Convert(sup, surf_unite, UnitTypeId.SquareFeet)
        d[idx_donnees['sup']] = sup
elif imperial:
    pass
else:
    TaskDialog.Show("Erreur", "Problème avec la conversion des unités de surface")
    script.exit()

# GESTION DES ÉLÉMENTS DE DÉTAILS EXISTANTS POUR LA MISE À JOUR
elements = FilteredElementCollector(doc, view.Id).OfCategory(
    BuiltInCategory.OST_DetailComponents).ToElements()

def assigner_val(fam, nom_fam, params, valeurs):
    for param, valeur in zip(params, valeurs):
        try:
            fam.LookupParameter(param).Set(valeur)
        except:
            erreur_param.add("{} - paramètre : {}, valeur : {}".format(nom_fam, param, valeur))

#------------------------------------------------------------------------------
#              MISE À JOUR ET GÉNÉRATION DES BLOCS 2D DANS REVIT
#------------------------------------------------------------------------------
with revit.Transaction("création des blocs"):
    dico_pieces = {}
    for id_i, [grp, dept, flt, num, nom, sup, nb] in sorted(data.items()):
        for i in range(int(nb)):
            nouveau_id = str(id_i) + str(i)
            dico_pieces[nouveau_id] = [grp, dept, flt, num, nom, sup, nb]

    # MISE À JOUR DE LA SURFACE RÉELLE POUR LES ÉLÉMENTS DE DÉTAILS EXISTANTS
    for e in elements:
        id_e = e.LookupParameter(identifiant).AsString()
        try:
            donnees = dico_pieces[id_e]
            grp = donnees[0] 
            dept = donnees[1]
            flt = donnees[2]
            num = donnees[3]
            nom = donnees[4]
            sup = donnees[5]
            nb = donnees[6]
            objet = '[{}] {} - {}'.format(id_e, num, nom)
            message_objet = Message(objet)

            #MISE À JOUR DE LA SURFACE RÉELLE POUR LES ÉLÉMENTS DE DÉTAILS EXISTANTS
            try:
                val = Parameter.AsDouble(e.LookupParameter('Surface'))
                e.LookupParameter(superficie_relle).Set(val)
                ajour.append(message_objet.suivi('surface à jour'))
            except:
                message_objet = Message(objet + ' : surface en lecture seule')

            #MISE À JOUR DES DONNÉES EXCEL POUR TOUS LES BLOCS
            try:
                assigner_val(e, nom, 
                             [numero_piece, nom_piece, departement, superficie_prog],
                             [num, nom, dept, sup])
                ajour.append(message_objet.suivi('données mise à jour'))
            except:
                erreur.append(message_objet.suivi('erreur de mise à jour des données'))  
        except:
            continue

#------------------------------------------------------------------------------
#                               SUIVI DES TÂCHES
#------------------------------------------------------------------------------
if ajour:
    description = 'Suivi des créations et mises à jour des pièces'
    form = Dialogue_suivi('Tâche complétée', description, ajour)
    form.ShowDialog()

if erreur:
    description = 'Suivi des erreurs de création et de mises à jour des pièces'
    form = Dialogue_suivi('Tâche incomplète', description, erreur)
    form.ShowDialog()

if erreur_param:
    description = "Les paramètres suivants n'ont pas étés mis à jour. Valider le nom du paramètre et la valeur à assigner"
    form = Dialogue_suivi('Avertissement', description, erreur_param)
    form.ShowDialog()