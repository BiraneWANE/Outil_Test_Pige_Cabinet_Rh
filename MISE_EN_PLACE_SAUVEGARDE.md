# Sauvegarde de la base : mise en place

Neuf fichiers, dont cinq nouveaux. Rien à créer à la main dans la base :
les deux tables nécessaires sont créées toutes seules au premier usage.

## 1. Copier les fichiers dans le projet

Nouveaux :

| Fichier | Rôle |
|---|---|
| `sauvegarde.py` | Construit l'archive, gère les copies quotidiennes |
| `restaurer.py` | Remet une archive dans une base vide. Il est copié **dans** chaque archive |
| `schema_sauvegarde.sql` | Les deux tables de service |
| `test_sauvegarde.py` | Tests, sans base de données |
| `templates/sauvegardes.html` | La page du back-office |

Modifiés :

| Fichier | Ce qui change |
|---|---|
| `main.py` | Import, copie du jour au démarrage, trois routes, état passé au back-office |
| `templates/admin.html` | Lien « sauvegardes » et bandeau de rappel |
| `installer.py` | Exécute aussi `schema_sauvegarde.sql` |
| `REGISTRE_TRAITEMENTS.md` | Durée de conservation des copies, effet sur la purge |

## 2. Vérifier en local

    conda activate tests
    python test_sauvegarde.py
    uvicorn main:app --reload

Puis ouvrir `http://127.0.0.1:8000/admin/sauvegardes` et télécharger une
archive. Elle doit peser quelques dizaines de kilo-octets et s'ouvrir comme
un dossier compressé ordinaire.

## 3. Mettre en ligne

    git add sauvegarde.py restaurer.py schema_sauvegarde.sql test_sauvegarde.py \
            templates/sauvegardes.html main.py templates/admin.html installer.py \
            REGISTRE_TRAITEMENTS.md MISE_EN_PLACE_SAUVEGARDE.md
    git commit -m "Sauvegarde complete de la base, telechargeable depuis le back-office"
    git push

L'hébergeur redéploie tout seul. Au démarrage, le serveur crée les deux
tables et enregistre la première copie du jour.

## 4. Ce qui protège quoi

**Les copies automatiques** vivent dans la base, une par jour, conservées
30 jours. Elles rattrapent une fausse manœuvre : une passation supprimée par
erreur, une purge lancée trop tôt. Elles ne protègent **pas** de la
disparition de l'hébergeur de la base, puisqu'elles disparaîtraient avec lui.

**Le fichier téléchargé** est le seul qui sorte des serveurs. C'est lui qui
protège du scénario redouté. Au-delà de 7 jours sans téléchargement, le
back-office affiche un bandeau, sur la page des invitations comme sur la page
des sauvegardes.

## 5. Le jour où il faut restaurer

Créer une base PostgreSQL vide chez n'importe quel hébergeur, décompresser
l'archive, puis :

    pip install "psycopg[binary]"
    export DATABASE_URL="postgresql://..."     # la nouvelle base
    python restaurer.py

Le script recrée les tables, réinjecte les lignes dans l'ordre des
dépendances et recale les compteurs d'identifiants. Il refuse d'écrire dans
une base qui contient déjà des passations.

Il ne reste qu'à changer `DATABASE_URL` dans les variables d'environnement de
l'hébergeur de l'application, et à contrôler sur `/sante/base`.

## 6. À faire une fois par an

Restaurer une archive sur une base d'essai, ouvrir l'application dessus,
vérifier qu'un ancien résultat s'affiche, puis supprimer la base d'essai.
Dix minutes. Une sauvegarde jamais restaurée n'est pas une sauvegarde.
