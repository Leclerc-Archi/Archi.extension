# -*- coding: utf-8 -*-
from pyrevit import script, forms
import clr
import sys
import os

# Accès à l'application Revit via pyRevit
app = __revit__.Application

# Infos Revit
revit_version = app.VersionNumber
revit_build = app.VersionBuild

# Infos Dynamo (si installé)
dynamo_versions = []
try:
    dyn_folder = os.path.join(os.getenv("APPDATA"), "Dynamo", "Dynamo Revit")
    if os.path.exists(dyn_folder):
        dynamo_versions = os.listdir(dyn_folder)
except:
    dynamo_versions = ["Non détecté"]

# Infos pyRevit
pyrevit_version = script.get_pyrevit_version()

# Python engine
python_engine = sys.version
python_runtime = "IronPython" if "IronPython" in python_engine else "CPython"

# Message final
message = "=== ENVIRONNEMENT REVIT ===\n\n"
message += "🧱 Revit : {} ({})\n".format(revit_version, revit_build)
message += "🧠 Dynamo : {}\n".format(", ".join(dynamo_versions) or "Aucune version détectée")
message += "🛠 pyRevit : {}\n".format(pyrevit_version)
message += "🐍 Python : {} ({})".format(python_runtime, python_engine)

# Affichage
forms.alert(message, title="BIM-TEAM - Diagnostic Environnement Revit", ok=True)
