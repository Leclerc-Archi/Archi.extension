# Mettre à jour le menu Archi- dans Revit 2025

## Méthode simple (recommandée pour les utilisateurs)

1. Aller dans le dossier où le dépôt a été cloné.
2. Double-cliquer sur **`update.bat`**.
3. Une fenêtre noire s'ouvre, récupère les derniers changements, puis se ferme automatiquement.
4. Dans Revit 2025, cliquer sur **Reload** dans l'onglet pyRevit (ou fermer/rouvrir Revit).

C'est tout. Le script ne demande aucune information et ne supprime jamais de travail en cours : si des fichiers locaux ont été modifiés par erreur, ils sont mis de côté automatiquement (`git stash`) avant la mise à jour.

## Méthode manuelle (ligne de commande)

```bash
cd "chemin\vers\Archi.extension"
git pull origin main
```

Puis Reload dans pyRevit.

## Automatiser la mise à jour à l'ouverture de Revit (optionnel, avancé)

Pour que la mise à jour se fasse seule sans action de l'utilisateur :

1. Créer un raccourci vers `update.bat` dans le dossier de démarrage Windows :
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
2. Ou utiliser le **Planificateur de tâches Windows** pour lancer `update.bat` chaque matin avant l'ouverture des postes.

Dans les deux cas, ajouter `/min` ou exécuter en tâche planifiée "Caché" pour que l'utilisateur ne voie même pas la fenêtre.

## Première installation (à faire une seule fois par poste)

```bash
git clone https://github.com/VOTRE-USERNAME/Archi.extension.git "C:\pyRevit-Extensions\Archi.extension"
```

Puis dans pyRevit > Settings > Custom Extension Directories, ajouter :
```
C:\pyRevit-Extensions
```
(le dossier **parent**, pas `Archi.extension` lui-même)

## En cas de problème

- **"git n'est pas reconnu"** : installer Git pour Windows (https://git-scm.com/download/win), cocher l'option d'ajout au PATH durant l'installation.
- **Conflits après pull** : généralement causé par une modification locale d'un script. Le `update.bat` les met de côté automatiquement, mais si un conflit survient malgré tout, supprimer le dossier local et refaire un `git clone` propre est la solution la plus rapide.
- **Le bouton n'apparaît pas après update** : faire **Reload** dans pyRevit, ou redémarrer Revit complètement.
