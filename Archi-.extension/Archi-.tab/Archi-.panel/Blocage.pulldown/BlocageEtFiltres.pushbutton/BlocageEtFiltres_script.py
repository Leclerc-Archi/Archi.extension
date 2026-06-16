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
nom_bloc = "M_BLOCAGE-2D" # nom de la famille de détails à utiliser pour les bloc 2D par défaut
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
# LISTE DES FAMILLES 2D DE LA MAQUETTE
familles = list(
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_DetailComponents))
noms_types = sorted([
    nom for fr in familles
    for nom in [fr.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()]
    if nom is not None
])
if not noms_types:
    TaskDialog.Show('Erreur', 'Aucune famille 2D trouvée')
    sys.exit()

# INDEX CORRESPONDANT À LA FAMILLE 2D PAR DÉFAUT
idx_nom = noms_types.index(nom_bloc) if nom_bloc in noms_types else 0

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
    {"nom": "famille de blocage 2D :", "type": "liste", "options": noms_types, "default": idx_nom},#0
    {"nom": "Chemin du fichier :", "type": "fichier", "default": chemin},#1
    {"nom": "Appliquer les filtres de couleur?", "type": "bool", "default": True},#2
    {"nom": "Appliquer un filtre de groupe?", "type": "bool", "default": False},#3
    {"nom": "Nom du filtre de groupe (si requis) :", "type": "texte", "default": None}#4
]

form = Formulaire(titre="Blocage 2D : données utilisateur", largeur=600, champs=champs)
if form.ShowDialog() == DialogResult.OK:
    data = form.valeurs()
    nom_famille = data["famille de blocage 2D :"]
    chemin_excel = data["Chemin du fichier :"]
    filtre_couleur_bool = data["Appliquer les filtres de couleur?"]
    filtre_bool = data["Appliquer un filtre de groupe?"]
    nom_filtre_gr = data["Nom du filtre de groupe (si requis) :"]
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
        nom_filtre_gr = data["Nom du filtre de groupe :"]
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

# TROISIÈME FORMULAIRE - APPLIQUER FILTRES AU GABARIT (CONDITIONNEL À UN GABARIT APPLIQUÉ À LA VUE COURANTE)
if view_gabarit and filtre_couleur_bool:
    nom_champ = str("Appliquer filtres au gabarit {}?".format(view_gabarit.Name))
    champs = [
        {"nom": nom_champ, "type": "bool"}
    ]
    form = Formulaire(titre="Gabarit en usage sur la vue courante", champs=champs, largeur=600)
    if form.ShowDialog() == DialogResult.OK:
        data = form.valeurs()
        gabarit_ok = data[nom_champ]
    else:
        script.exit

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
data_brut = vals_col(feuille_excel, liste_entetes, 0)
filtres = vals_col(feuille_excel, liste_filtres, 3)
for dept, couleur in filtres.values():
    dico_couleur[dept] = hex_a_rvb(couleur)

if filtre_couleur_bool:
    #------------------------------------------------------------------------------
    #           GESTION ET CRÉATION DES FILTRES REVIT PAR DÉPARTEMENT
    #------------------------------------------------------------------------------
    # VARIABLES DE TRAVAIL
    vals_filtres = sorted(dico_couleur.keys())# valeur du département utilisé pour appliquer le filtre
    param_filtre = 0

    dico_regles = {}# dictionnaire des règles existantes
    noms_regles_exist = []# liste des noms des règles existantes
    noms_filtres = []#liste des noms de filtre tel qu'ils apparaîtront dans les paramètres de vue
    dico_filtres = {}# dictionnaire des filtres de blocage et de leurs noms tel qu'ils apparaîtront dans les paramètres de vue

    # VARIABLES DE SUIVI
    nouveaux = []
    existants = []
    enusage = []
    effaces = []

    # COLLECTEURS REVIT
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
        if(param.Name == departement):# valeur pour le filtre
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

        # CHANGEMENT TEMPORAIRE DE LA VUE COURANTE POUR LA VUE DE GABARIT, LE CAS ÉCHÉANT
        if gabarit_ok: 
            view = view_gabarit

        # CRÉATION ET GESTION DES FILTRES
        for valeur, nom in dico_filtres.items():
            if nom not in noms_regles_exist:# valide si la règle existe déjà basé sur le nom
                regle = ParameterFilterRuleFactory.CreateContainsRule(param_filtre.Id, valeur, lst_categorie_typ)
                filtre = ParameterFilterElement.Create(doc, nom, lst_categorie_typ)

                # APPLICATION DE LA RÈGLE ET DU FILTRE
                nouvelle_regle = ElementParameterFilter(regle)
                filtre.SetElementFilter(nouvelle_regle)
                view.AddFilter(filtre.Id)
                nouveaux.append(Message(nom).suivi('nouveau filtre appliqué'))

            else:# récupère le filtre pré-existant, le cas échéant
                filtre = dico_regles[nom]
                try:# assigne le filtre existant à la vue courante - except s'il est déjà assigné
                    view.AddFilter(filtre.Id)
                    existants.append(Message(nom).suivi('filtre existant appliqué'))
                except:
                    enusage.append(Message(nom).suivi('filtre déjà en usage'))
            
            # APPLICATION DE LA COULEUR AU FILTRE
            pochage = view.GetFilterOverrides(filtre.Id)
            couleur_pochage = pochage.SetSurfaceForegroundPatternColor(dico_couleur[valeur])
            view.SetFilterOverrides(filtre.Id, couleur_pochage)
        
        champs = sorted(effaces + enusage + existants + nouveaux)
        description = 'Suivi des filtres supprimés, créés et existants'
        form = Dialogue_suivi('Suivi des filtres', description, champs)
        form.ShowDialog()

    # RÉASSIGNE LA VUE ACTIVE POUR L'ÉTAPE SUIVANTE
    view = doc.ActiveView
else:
    pass

#------------------------------------------------------------------------------
#                    GESTION ET PRÉPARATION DES BLOCS 2D
#------------------------------------------------------------------------------
# VARIABLES DE TRAVAIL
numeros = []
data = {}# données nettoyées
dico_elements = {}
x, y = 0, 0# positions en x et y pour la génération du point d'insertion
ratio_l, ratio_p = 5, 4# ratios largeur / profondeur pour la génération des pièces
ratio = ratio_l*ratio_p

# VARIABLES DE SUIVI
erreur_param = set()# pour suivi des erreurs de assigner_val
ajour = []# contiendra tous les blocs existants mis à jour
erreur = []# contiendra tous les blocs pour lesquels une Erreur est survenue (devrait TOUJOURS être vide; là pour cas imprévisibles)

# VALIDATION ET CONVERSION DES UNITÉS, LE CAS ÉCHÉANT (API REVIT REQUIERT NATIF IMPÉRIAL)
unites = doc.GetUnits()
surf_format = unites.GetFormatOptions(SpecTypeId.Area)
surf_unite = surf_format.GetUnitTypeId()# format des univtés de surface Revit
imperial = surf_unite == UnitTypeId.SquareFeet

for k, d in data_brut.items():
    if isinstance(d[idx_donnees['nb']], (int, float)) and isinstance(d[idx_donnees['sup']], (int, float)):
        data[k]= d
    else:
        continue

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

# FAMILLE 2D SÉLECTIONNÉE PAR L'USAGER
famille_id = next(
    (f.Id for f in familles
     if f.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
     .AsString() == nom_famille), None)

if famille_id is None:
    TaskDialog.Show("Erreur", "famille '{}' est introuvable".format(nom_famille))
    script.exit()

famille_type = doc.GetElement(famille_id)

# GESTION DES ÉLÉMENTS DE DÉTAILS EXISTANTS POUR LA MISE À JOUR
elements = FilteredElementCollector(doc, view.Id).OfCategory(
    BuiltInCategory.OST_DetailComponents).ToElements()

for e in elements:
    id_e = e.LookupParameter(identifiant)
    id_ref = Parameter.AsString(id_e)
    dico_elements[id_ref] = e

def assigner_val(fam, nom_fam, params, valeurs):
    for param, valeur in zip(params, valeurs):
        try:
            fam.LookupParameter(param).Set(valeur)
        except:
            erreur_param.add("{} - paramètre : {}, valeur : {}".format(nom_fam, param, valeur))

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

#------------------------------------------------------------------------------
#              MISE À JOUR ET GÉNÉRATION DES BLOCS 2D DANS REVIT
#------------------------------------------------------------------------------
with revit.Transaction("création des blocs"):
    for id_i, [grp, dept, flt, num, nom, sup, nb] in sorted(data.items()):
        numeros.append(num)
        for i in range(int(nb)):
            largeur = math.sqrt(sup/ratio)*ratio_l
            profondeur = math.sqrt(sup/ratio)*ratio_p
            nouveau_id = str(id_i) + str(i)
            objet = '[{}] {} - {}'.format(nouveau_id, num, nom)
            message_objet = Message(objet)
            
            # MISE À JOUR DE LA SURFACE RÉELLE POUR LES ÉLÉMENTS DE DÉTAILS EXISTANTS
            try:
                fam = dico_elements[nouveau_id]
                try:
                    val = Parameter.AsDouble(fam.LookupParameter("Surface"))
                    fam.LookupParameter(superficie_relle).Set(val)
                    ajour.append(message_objet.suivi('surface à jour'))
                except:
                    message_objet = Message(objet + ' : surface en lecture seule')
            
            # CRÉATION DES BLOCS DE PROGRAMME QUI N'ONT PAS D'ÉLÉMENT DE DÉTAIL CORRESPONDANT
            except:
                try:
                    loc = XYZ(x, y, 0)
                    fam = doc.Create.NewFamilyInstance(loc, famille_type, view)
                    assigner_val(fam, nom, [identifiant, largeur_fam, profondeur_fam], [nouveau_id, largeur, profondeur])
                    message_objet = Message(objet + ' : nouvelle pièce créée')
                except: #doit toujours être vide; si sort des données, un troubleshoot est nécessaire. Contacter une personne ressource si requis (ie. Myriam)
                    message_objet = Message(objet + ' : erreur de création')
            # ÉCRITURE DES DONNÉES EXCEL POUR LES TOUS LES BLOCS (EXISTANTS ET NOUVEAUX)
            try:
                assigner_val(fam, nom, 
                             [numero_piece, nom_piece, departement, superficie_prog],
                             [num, nom, dept, sup])
                ajour.append(message_objet.suivi('données mise à jour'))
            except:
                erreur.append(message_objet.suivi('erreur de mise à jour des données'))
            y -= profondeur + 5
        x += largeur + 5
        y = 0

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