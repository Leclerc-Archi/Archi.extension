# Archi- — Extension pyRevit

Extension pyRevit personnalisée pour Revit 2025, contenant les outils internes de la firme **Archi-**.

## Contenu

L'onglet **Archi-** dans Revit regroupe deux panneaux :

- **Archi-** : outils internes (gestion de blocage, familles, matériaux, audit de programme, impression de détails, transfert de familles, etc.)
- **Favoris PYrevit** : outils complémentaires (Match, ColorSplasher, Keynotes, Preflight Checks, gestion des révisions, etc.)

53 outils au total, organisés en sous-menus déroulants (pulldowns) par catégorie.

## Installation (premier déploiement)

1. Installer [pyRevit](https://github.com/pyrevitlabs/pyRevit/releases) si ce n'est pas déjà fait, pour Revit 2025.
2. Cloner ce dépôt à un emplacement fixe sur ton poste ou un lecteur réseau partagé, par exemple :
   ```
   git clone https://github.com/VOTRE-USERNAME/Archi.extension.git "C:\pyRevit-Extensions\Archi.extension"
   ```
3. Ouvrir **pyRevit > Settings > Custom Extension Directories**, et ajouter le dossier où le dépôt a été cloné (le dossier qui *contient* `Archi-.extension`, pas le dossier lui-même).
4. Cliquer sur **Reload** dans l'onglet pyRevit, ou redémarrer Revit 2025.

## Mise à jour

Pour récupérer les dernières modifications du menu sans tout réinstaller, utilise le script `update.bat` (Windows) fourni à la racine de ce dépôt. Voir [UPDATE.md](UPDATE.md) pour les détails.

En résumé :
```
git pull
```
puis clic sur **Reload** dans pyRevit (ou redémarrer Revit).

## Structure du projet

```
Archi.extension/
├── Archi-.extension/
│   └── Archi-.tab/
│       ├── Archi-.panel/          (outils internes BIM, blocage, familles...)
│       └── Favoris PYrevit.panel/ (outils complémentaires)
├── extension.json
├── update.bat
├── README.md
└── UPDATE.md
```

## Contribuer / modifier un outil

Chaque outil est un dossier `*.pushbutton` contenant au minimum :
- `script.py` : le code exécuté au clic
- `bundle.yaml` : le titre, l'infobulle et le contexte du bouton
- `icon.png` / `icon.dark.png` : les icônes claire/sombre

Après modification, fais un commit et un push ; les utilisateurs récupèrent les changements avec `git pull` ou en lançant `update.bat`.
