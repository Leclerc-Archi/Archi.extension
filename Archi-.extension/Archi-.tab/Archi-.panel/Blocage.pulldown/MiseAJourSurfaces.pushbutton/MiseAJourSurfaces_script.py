# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#         SCRIPT DE MISE À JOUR DES SURFACES POUR ZONES DE POCHAGES
#------------------------------------------------------------------------------
#                                                      par Myriam N-M

import sys, os

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packages.formulaires import * #package de fonctionnalitées utiles

#------------------------------------------------------------------------------
#                        PARAMÈTRES DE TRAVAIL DE DÉPART
#------------------------------------------------------------------------------
# INFORMATIONS MODÈLE REVIT
doc = revit.doc
if not doc:
    TaskDialog.Show('Erreur', 'Aucun document Revit actif.')
    sys.exit()
view = doc.ActiveView

#------------------------------------------------------------------------------
#    RÉCUPÉRATION ZONES DE POCHAGE ET PARAMÈTRES DISPONIBLES POUR ÉCRITURE
#------------------------------------------------------------------------------
# PARAMÈTRES MODÈLE REVIT - SÉLECTION VALEURS PAR DÉFAUT FORMULAIRE
txtSup = 'SUPERFICIE-NETTE-RÉELLE'

# SÉLECTION DES ZONES DE POCHAGE - EXCLUSION DES ZONES INCLUES DANS DES GROUPES
exclu = 0
elements = []
allregions = FilteredElementCollector(doc, view.Id).OfClass(FilledRegion).ToElements()
for el in allregions:
    if el.GroupId == ElementId.InvalidElementId:
        elements.append(el)
    else:
        exclu += 1  # composants dans groupes

if len(elements) > 0:
    e = elements[0]
    params = [param.Definition.Name for param in e.Parameters]
else:
    TaskDialog.Show('Erreur', 'Aucune zone de pochage dans la vue active.')
    sys.exit()   

#------------------------------------------------------------------------------
#          MISE À JOUR DU PARAMÈTRE DE SUPERFICIE RÉELLE DANS REVIT
#------------------------------------------------------------------------------
#VARIABLES DE TRAVAIL
ajour, erreur = 0, 0

with revit.Transaction('mise à jour des surfaces'):
    for e in elements:
        try:
            val = Parameter.AsDouble(e.LookupParameter('Surface'))
            e.LookupParameter(txtSup).Set(val)
            ajour += 1
        except:
            erreur += 1

#------------------------------------------------------------------------------
#                               SUIVI DES TÂCHES
#------------------------------------------------------------------------------
form = Dialogue_suivi(titre="Suivi de la tâche", 
                      donnees=('Suivi de la mise à jour des pochages','\n\nSURFACES MISES À JOUR : {}\n'.format(ajour), 'ERREURS : {}'.format(erreur)),
                      largeur=400,
                      longueur=200
                      )
form.ShowDialog()

form = Dialogue_suivi(titre='RAPPEL',
                      donnees=('IMPORTANT', '\nNe pas oublier de synchroniser la maquette pour ne pas bloquer\nles autres usagers',
                               '\nLes surfaces incluses dans des groupes ne sont pas mises à jour\n\nSURFACES DANS DES GROUPES : {}'.format(exclu)),
                      largeur=400,
                      longueur=200
                      )
form.ShowDialog()