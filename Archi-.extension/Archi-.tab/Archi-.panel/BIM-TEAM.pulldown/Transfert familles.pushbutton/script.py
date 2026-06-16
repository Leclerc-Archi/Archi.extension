# -*- coding: utf-8 -*-
"""
Upgrade sécurisé de fichiers Revit vers Revit 2025.
Permet de choisir le dossier Source et le dossier de Destination.
Inclusion des sous-dossiers et gestion des échecs avec mise en Quarantaine.
**Ajout de l'exclusion des dossiers et fichiers qui commencent par '_' (trait de soulignement).**
Testé et validé sur Revit 2025 + PyRevit
"""

import os
import clr
from System import DateTime
from System.IO import FileInfo
clr.AddReference("System.Windows.Forms")
# Ajout de MessageBox pour la confirmation
from System.Windows.Forms import FolderBrowserDialog, DialogResult, MessageBox, MessageBoxButtons, MessageBoxIcon

# Import Revit API
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.ApplicationServices import Application
# Import nécessaire pour ModelPath (chemin de fichier)
from Autodesk.Revit.DB import ModelPathUtils 

app = __revit__.Application

# ---------------------------------------------------------------
## 1. Interface Utilisateur
# ---------------------------------------------------------------
# --- SÉLECTION DU DOSSIER SOURCE ---
dlg_source = FolderBrowserDialog()
dlg_source.Description = "Sélectionner le **DOSSIER SOURCE** contenant les fichiers Revit à upgrader"
dlg_source.ShowNewFolderButton = False

if dlg_source.ShowDialog() != DialogResult.OK:
    raise Exception("Aucun dossier source sélectionné.")

SOURCE_FOLDER = dlg_source.SelectedPath

# --- SÉLECTION DU DOSSIER DE DESTINATION ---
dlg_dest = FolderBrowserDialog()
dlg_dest.Description = "Sélectionner le **DOSSIER DE DESTINATION** où sauvegarder les fichiers upgradés"
dlg_dest.SelectedPath = SOURCE_FOLDER
dlg_dest.ShowNewFolderButton = True 

if dlg_dest.ShowDialog() != DialogResult.OK:
    raise Exception("Aucun dossier de destination sélectionné.")

DESTINATION_FOLDER = dlg_dest.SelectedPath

# --- Choix d'inclusion des sous-dossiers ---
msg_result = MessageBox.Show(
    "Souhaitez-vous inclure les fichiers Revit dans tous les sous-dossiers de '{}' ?\n\n(Les dossiers et fichiers commençant par '_' seront exclus.)".format(os.path.basename(SOURCE_FOLDER)),
    "Inclusion des Sous-dossiers",
    MessageBoxButtons.YesNo,
    MessageBoxIcon.Question
)
INCLUDE_SUBFOLDERS = (msg_result == DialogResult.Yes)

# --- Configuration des chemins ---
LOG_FILE = os.path.join(DESTINATION_FOLDER, "Upgrade_Revit2025_log.txt")
QUARANTINE_FOLDER = os.path.join(DESTINATION_FOLDER, "Quarantaine_Fichiers_Echoues")

# ---------------------------------------------------------------
## 2. Fonctions de Log et Utilitaires
# ---------------------------------------------------------------
def log(msg):
    """Écrit le message dans la console et dans le fichier log en UTF-8."""
    timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
    line = "[{}] {}\n".format(timestamp, msg)
    print(msg)
    # Assure le répertoire de destination pour le log
    if not os.path.exists(DESTINATION_FOLDER):
         os.makedirs(DESTINATION_FOLDER)
    with open(LOG_FILE, "ab") as f:
        f.write(line.encode("utf-8"))

# S'assurer que le dossier de quarantaine existe
if not os.path.exists(QUARANTINE_FOLDER):
    try:
        os.makedirs(QUARANTINE_FOLDER)
    except:
        log("ATTENTION: Impossible de créer le dossier de quarantaine.")


def is_revit_file(filename):
    """Vérifie si l'extension est un fichier Revit (.rvt, .rfa, .rte)."""
    return filename.lower().endswith(('.rvt', '.rfa', '.rte'))

def get_all_revit_files(folder, recursive=False):
    """
    Récupère les chemins complets des fichiers Revit, en excluant les dossiers et fichiers
    qui commencent par '_'.
    """
    files = []
    
    if recursive:
        # Parcours récursif (avec exclusion des dossiers en '_')
        for root, dirs, filenames in os.walk(folder):
            
            # --- MODIFICATION POUR IGNORER LES SOUS-RÉPERTOIRES EN AGRÉGAT ---
            # Modifie la liste 'dirs' in-place pour que os.walk ne descende pas dans ces dossiers.
            dirs[:] = [d for d in dirs if not d.startswith('_')]
            # -----------------------------------------------------------------

            for f in filenames:
                filepath = os.path.join(root, f)
                # --- MODIFICATION POUR IGNORER LES FICHIERS EN AGRÉGAT ---
                if not f.startswith('_') and is_revit_file(f):
                    files.append(filepath)
                # ------------------------------------------------------
    else:
        # Parcours non-récursif (pas de changement majeur nécessaire, mais on garde la vérification de fichier)
        for f in os.listdir(folder):
            filepath = os.path.join(folder, f)
            # Vérifie si c'est un fichier ET si c'est un fichier Revit, et n'est pas en '_'
            if os.path.isfile(filepath) and is_revit_file(f) and not f.startswith('_'):
                files.append(filepath)
                
    return files

# ---------------------------------------------------------------
## 3. Options API Revit
# ---------------------------------------------------------------
# Options d'ouverture
open_opt = OpenOptions()
open_opt.Audit = True                       # ESSAYE DE RÉPARER LA CORRUPTION
open_opt.DetachFromCentralOption = DetachFromCentralOption.DetachAndPreserveWorksets

# Options de sauvegarde
saveas_opt = SaveAsOptions()
saveas_opt.OverwriteExistingFile = True

# Gestionnaire pour supprimer les avertissements/erreurs non bloquants
def suppress_failures(sender, args):
    args.SetProcessingResult(FailureProcessingResult.Continue)

# Enregistre le gestionnaire d'événements
app.FailuresProcessing += suppress_failures

log("=== DÉBUT UPGRADE VERS REVIT 2025 ===")
log("Dossier Source : {}".format(SOURCE_FOLDER))
log("Dossier Destination : {}".format(DESTINATION_FOLDER))
log("Dossier Quarantaine : {}".format(QUARANTINE_FOLDER))
log("Mode de recherche : {}".format("Récursif" if INCLUDE_SUBFOLDERS else "Non-récursif"))
if INCLUDE_SUBFOLDERS:
    log("Note : Les dossiers et fichiers commençant par '_' sont ignorés.")


# ---------------------------------------------------------------
## 4. Traitement des Fichiers
# ---------------------------------------------------------------
files = get_all_revit_files(SOURCE_FOLDER, INCLUDE_SUBFOLDERS)
total = len(files)
log("Fichiers Revit détectés : {} ".format(total))

for i, filepath_source in enumerate(files, 1):
    filename = os.path.basename(filepath_source)
    log("({}/{}) Traitement : {}".format(i, total, filename))

    # Redondance : la fonction get_all_revit_files devrait déjà exclure ceci, 
    # mais c'est une vérification de sécurité simple.
    if filename.startswith('_'):
        log("  Fichier ignoré (commence par '_')")
        continue

    if FileInfo(filepath_source).IsReadOnly:
        log("  Fichier en lecture seule → ignoré")
        continue

    # Déterminer le chemin de destination (maintien de l'arborescence)
    if INCLUDE_SUBFOLDERS:
        relative_path = os.path.relpath(os.path.dirname(filepath_source), SOURCE_FOLDER)
        folder_destination = os.path.join(DESTINATION_FOLDER, relative_path)
    else:
        folder_destination = DESTINATION_FOLDER
        
    # Assurer que le répertoire de destination existe
    if not os.path.exists(folder_destination):
        os.makedirs(folder_destination)
        
    filepath_destination = os.path.join(folder_destination, filename)
    doc = None
    
    try:
        # --- Ouverture ---
        model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(filepath_source)
        # La ligne suivante lève une exception en cas de corruption sévère
        doc = app.OpenDocumentFile(model_path, open_opt) 

        current_save_opt = saveas_opt

        # Logique Worksharing
        if doc.IsWorkshared:
            log("  Fichier partagé détecté, sauvegarde comme Central.")
            ws_save_opt = WorksharingSaveAsOptions()
            ws_save_opt.SaveAsCentral = True
            current_save_opt = SaveAsOptions()
            current_save_opt.OverwriteExistingFile = True
            current_save_opt.SetWorksharingOptions(ws_save_opt)

        # --- Sauvegarde ---
        doc.SaveAs(filepath_destination, current_save_opt)
        
        # Fermeture réussie
        doc.Close(False)
        log("  SUCCÈS → Upgradé et sauvegardé dans : {}".format(folder_destination))

    except Exception as ex:
        # --- GESTION DE L'ÉCHEC ET QUARANTAINE ---
        error_message = str(ex)
        log("  ÉCHEC FATAL à l'ouverture/sauvegarde de {}.".format(filename))
        log("  ERREUR DÉTAILLÉE : {}".format(error_message))
        
        # 2. Déplacer le fichier source problématique en quarantaine
        try:
            quarantine_path = os.path.join(QUARANTINE_FOLDER, filename)
            # Tenter de déplacer le fichier source vers la quarantaine
            os.rename(filepath_source, quarantine_path)
            log("  → Le fichier source original a été DÉPLACÉ en quarantaine pour audit manuel.")
        except Exception as move_ex:
            log("  ÉCHEC DU DÉPLACEMENT en quarantaine : Le fichier original RESTE dans la source.")
            log("  Erreur de déplacement : {}".format(str(move_ex)))
        
        pass 
    finally:
        # S'assurer que le document est fermé même en cas d'erreur
        if doc and doc.IsValidObject:
            try:
                doc.Close(False)
            except:
                pass

# ---------------------------------------------------------------
## 5. Nettoyage Final
# ---------------------------------------------------------------
try:
    app.FailuresProcessing -= suppress_failures
except:
    pass
    
log("=== FIN DE L'UPGRADE ===")
log("Log complet : {}".format(LOG_FILE))
print("\nUpgrade terminé ! Voir le log pour les détails et la liste des fichiers en quarantaine :\n{}".format(LOG_FILE))