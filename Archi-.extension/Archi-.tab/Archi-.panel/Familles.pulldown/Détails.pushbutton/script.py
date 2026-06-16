import os
import subprocess

# Replace this with your folder path (can be dynamic too)
folder_path = r"K:\2-Protocoles\3-Standards dessins\1-Revit\04_Banque de details"

# Check if folder exists, then open
if os.path.exists(folder_path):
   subprocess.Popen('explorer "{}"'.format(folder_path))
else:
    print("Folder does not exist:", folder_path)

