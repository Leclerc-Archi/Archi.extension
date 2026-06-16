# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#         SCRIPT D'OUVERTURE DU DOSSIER RÉFÉRENCE POUR BLOCAGE 2D
#------------------------------------------------------------------------------

import os
import subprocess

# CHEMIN DU FICHIER
folder_path = r"K:\2-Protocoles\2-Standards textes\2-Projet"

# VÉRIFIE EXISTANCE DU FICHIER, PUIS L'OUVRE
if os.path.exists(folder_path):
    subprocess.Popen('explorer "{}"'.format(folder_path))
else:
    print("Le fichier n'existe pas:", folder_path)