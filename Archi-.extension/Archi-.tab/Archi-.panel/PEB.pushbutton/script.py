import os
import subprocess

# Path to the PDF file
pdf_path = r"K:\2-Protocoles\3-Standards dessins\1-Revit\14_PEB\Archi-_PEB.pdf"

# Open the PDF with the system default app
try:
    os.startfile(pdf_path)  # Only works on Windows
except Exception:
    subprocess.call(['cmd', '/c', 'start', '', pdf_path])
