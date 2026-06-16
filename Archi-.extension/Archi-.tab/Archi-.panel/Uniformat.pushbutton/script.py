# -*- coding: utf-8 -*-
import os
import subprocess

# Path to the PDF file
pdf_path = r"K:\3-Références\1-Codes, normes, réglements\Uniformat\Annexe-B-UniformatII_niveaux3et4.pdf"

# Open the PDF with the system default app
try:
    os.startfile(pdf_path)  # Only works on Windows
except Exception:
    subprocess.call(['cmd', '/c', 'start', '', pdf_path])
