# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#            SCRIPT D'ÉCRITURE DU CHEMIN DE FICHIER VERS REVIT
#------------------------------------------------------------------------------
#                                                      par Myriam N-M

import os, sys

from pyrevit import revit, script

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from packages.formulaires import *

#------------------------------------------------------------------------------
#      INFORMATIONS REVIT - DOC ET VARIABLES PARAMÈTRE + PARAMÈTRE TEXTE
#------------------------------------------------------------------------------
# INFORMATIONS MODÈLE REVIT
doc = revit.doc
projetinfo = doc.ProjectInformation

# VARIABLES DE TRAVAIL
param = ""
paramsprojet_list = []
suivi = "Tâche annulée"

# LISTE DES PARAMÈTRES PROJET DISPONIBLES DANS LA MAQUETTE
try:
    paramsprojet = projetinfo.Parameters
    for i in  paramsprojet:
        i = i.Definition.Name
        if "CHEMIN" in i:
            paramsprojet_list.append(i)

    # INDEX DU PARAMÈTRE PAR DÉFAUT
    param_id = paramsprojet_list.index("INF_CHEMIN DU FICHIER PROGRAMME EXCEL")
except:
    suivi="Aucun paramètre de projet disponible. Référez-vous à votre responsable BIM pour ajouter le paramètre requis."

    form = Dialogue_suivi(titre="Suivi", description=suivi, largeur=400, longueur=200)
    form.ShowDialog()    
    script.exit()

#------------------------------------------------------------------------------
#          FORMULAIRE UTILISATEUR POUR LES DONNÉES DE TRAVAIL
#------------------------------------------------------------------------------
champs = [
    {"nom": "nom du champs :", "type": "liste", "options": paramsprojet_list, "default": param_id},#0
    {"nom": "chemin du fichier :", "type": "fichier", "default": "C:\\"}#1
]

form = Formulaire(titre="Chemin du fichier excel de programme", champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    nom_param = data["nom du champs :"]
    chemin_fichier = data["chemin du fichier :"]

else:
    script.exit()


param = projetinfo.LookupParameter(nom_param)

#------------------------------------------------------------------------------
#        ÉCRITURE DU CHEMIN DE FICHIER DANS LA PARAMÈTRE PROJET REVIT
#------------------------------------------------------------------------------
with revit.Transaction("récupérer chemin fichier"):

    param.Set(str(chemin_fichier))
    suivi="Tâche complétée"

form = Dialogue_suivi(titre="Suivi", description=suivi, largeur=300, longueur=200)
form.ShowDialog()