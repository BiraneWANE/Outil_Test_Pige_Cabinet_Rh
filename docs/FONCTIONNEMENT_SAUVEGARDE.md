# Les sauvegardes

Ce qui protège quoi, et comment remonter la base le jour où il le faut.

---

## 1. Deux copies, deux rôles

**La copie automatique** est fabriquée chaque jour et vit dans la base,
conservée trente jours. Elle rattrape une fausse manœuvre : une passation
supprimée par erreur, une purge lancée trop tôt.

Elle ne protège **pas** de la disparition de l'hébergeur de la base, puisqu'elle
disparaîtrait avec lui.

**Le fichier téléchargé** est le seul qui sorte des serveurs. C'est lui qui
protège du scénario redouté. Le back-office affiche un rappel au-delà de sept
jours sans téléchargement, sur la page des invitations comme sur celle des
sauvegardes.

C'est la distinction qui a motivé tout ce module : une sauvegarde rangée au
même endroit que l'original n'est pas une sauvegarde.

---

## 2. Ce que contient une archive

Un fichier `.zip` de quelques dizaines de kilo-octets, qui s'ouvre comme un
dossier compressé ordinaire.

| Dans l'archive | Contenu |
|---|---|
| `MANIFESTE.json` | Date, version, liste des tables et nombre de lignes |
| `donnees.json` | Toutes les données, table par table |
| `csv/<table>.csv` | Les mêmes, une feuille par table, lisibles dans Excel |
| `schema/*.sql` | La structure des tables |
| `restaurer.py` | Le script de restauration, embarqué |
| `RESTAURATION.md` | La marche à suivre, en clair |

L'archive est **autonome** : elle ne dépend ni du dépôt, ni de l'hébergeur, ni
de quoi que ce soit d'autre. Dans dix ans, avec Python et une base PostgreSQL
vide, elle se remonte.

Deux détails qui ont demandé de l'attention : les nombres décimaux sont écrits
en texte et non en flottants, faute de quoi un taux de 66,67 % revenait à
66,66999… ; et les CSV portent un BOM UTF-8, sans lequel Excel affiche les
accents de travers.

---

## 3. Le jour où il faut restaurer

Créer une base PostgreSQL vide chez n'importe quel hébergeur, décompresser
l'archive, puis :

```bash
pip install "psycopg[binary]"
export DATABASE_URL="postgresql://..."     # la nouvelle base
python restaurer.py
```

Le script recrée les tables, réinjecte les lignes dans l'ordre des dépendances
et recale les compteurs d'identifiants. Il **refuse d'écrire dans une base qui
contient déjà des passations**, sauf si on lui passe explicitement
`--ecraser` : on ne restaure pas par accident.

Il ne reste qu'à changer `DATABASE_URL` dans les variables d'environnement de
l'hébergeur de l'application, et à contrôler sur `/sante/base`.

Cette procédure a été essayée pour de vrai : dix tables restaurées à
l'identique dans une base vide.

---

## 4. À faire une fois par an

Restaurer une archive sur une base d'essai, ouvrir l'application dessus,
vérifier qu'un ancien résultat s'affiche, puis supprimer la base d'essai.

Dix minutes. Une sauvegarde jamais restaurée n'est pas une sauvegarde.

---

## 5. Un point d'attention : sauvegarde et purge RGPD

Les deux se croisent, et c'est voulu.

L'effacement des identités à 180 jours porte sur la base vivante. Une archive
fabriquée avant cette date contient encore les noms — c'est normal, une
sauvegarde qui s'effacerait toute seule ne servirait à rien.

C'est pourquoi les archives sont conservées **trente jours** et pas davantage :
au-delà, une identité effacée dans la base ressusciterait dans une copie. Le
délai est le compromis entre le droit à l'effacement et la protection contre
la perte.

Une demande d'effacement d'un candidat vaut aussi pour les archives : elle est
traitée en supprimant les copies concernées. Le point est documenté dans le
[registre des traitements](REGISTRE_TRAITEMENTS.md).

---

## 6. Les tables

| Table | Ce qu'elle contient |
|---|---|
| `sauvegarde` | Les archives, une par jour, avec leur contenu |
| `sauvegarde_telechargement` | La trace des téléchargements, pour le rappel |

Créées automatiquement au premier démarrage.
`schema_sauvegarde.sql` sert de référence.

---

## 7. Vérifier

```bash
python test_sauvegarde.py
```

Sans base de données. Le script contrôle la construction de l'archive, la
conversion des types (dates, décimaux, données binaires) et la relecture.
