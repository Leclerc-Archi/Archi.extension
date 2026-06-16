# -*- coding: utf-8 -*-
import xlrd
fichier_excel = xlrd.open_workbook('25-000 Tableau de programme.xlsx')
feuille_excel = fichier_excel.sheet_by_name('LISTE DES LOCAUX')

def vals_col(feuille, valeurs):
    val_dict = {}
    col_idx = []
    headers = feuille.row_values(0)
    for valeur in valeurs:
        if valeur in headers:
            col_idx.append(headers.index(valeur))
    for idx in col_idx:
        for row_idx in range(1, feuille.nrows):
            id_val = feuille.cell_value(row_idx, 0)
            cell_val = feuille.cell_value(row_idx, idx)
            if id_val and cell_val != None and id_val != 'ID':
                if id_val in val_dict:
                    val_dict[id_val].append(cell_val)
                else:
                    val_dict[id_val] = [cell_val]
    return val_dict

def hex_to_rgb(hex_color):

    hex_color = hex_color.lstrip('#')  # Remove '#' if present
    r_hex = hex_color[0:2]
    g_hex = hex_color[2:4]
    b_hex = hex_color[4:6]

    r = int(r_hex, 16)
    g = int(g_hex, 16)
    b = int(b_hex, 16)

    print(r, g, b)

liste_donnees = ['groupe', 'dept', 'filtre', 'num', 'nom', 'sup', 'nb']
idx_donnee = 0
idx_donnees = {}
for i in liste_donnees:
    idx_donnees[i] = idx_donnee
    idx_donnee += 1
print(idx_donnees)

donnees = vals_col(feuille_excel, liste_donnees)

suivi = []

for key, val in donnees.items():
    suivi.append(key + ' : ' + val[idx_donnees['nom']])

print(sorted(suivi))