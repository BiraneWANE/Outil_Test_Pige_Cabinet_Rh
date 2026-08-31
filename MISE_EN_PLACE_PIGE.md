# Pige des annonces : mise en place

Six fichiers, dont quatre nouveaux. Aucune table à créer à la main :
elles sont créées au premier usage, comme pour la sauvegarde.

## 1. Copier les fichiers dans le projet

Nouveaux :

| Fichier | Rôle |
|---|---|
| `pige.py` | Collecte, dédoublonnage, historisation, signaux |
| `schema_pige.sql` | Les trois tables et la vue de travail |
| `templates/pige.html` | La page du back-office |
| `templates/pige_entreprises.html` | Le classement des entreprises |
| `test_pige.py` | Tests, sans réseau ni base |

Modifiés :

| Fichier | Ce qui change |
|---|---|
| `main.py` | Import, collecte du jour au démarrage, quatre routes |
| `templates/admin.html` | Lien « pige des annonces » |
| `installer.py` | Exécute aussi `schema_pige.sql` |

## 2. Les clés d'API

C'est la seule chose qui manque pour que la collecte tourne. Quatre valeurs,
à mettre dans le `.env` en local **et** dans les variables d'environnement de
l'hébergeur.

    FT_CLIENT_ID=
    FT_CLIENT_SECRET=
    ADZUNA_APP_ID=
    ADZUNA_APP_KEY=

**France Travail**, un quart d'heure. Sur `francetravail.io` : créer un compte,
déclarer une application, s'abonner à l'API *Offres d'emploi v2*. L'identifiant
client et la clé secrète sont délivrés aussitôt.

**Adzuna**, cinq minutes. Sur `developer.adzuna.com/signup` : créer un compte,
les deux valeurs sont affichées immédiatement.

Sans ces clés, la page s'ouvre normalement et affiche un bandeau. Avec une seule
des deux sources, la collecte tourne quand même sur cette source.

## 3. Vérifier en local

    conda activate tests
    python test_pige.py
    python -m uvicorn main:app --reload

Puis `http://127.0.0.1:8000/admin/pige`, et le bouton « Lancer la collecte
maintenant ». Compter une à deux minutes.

## 4. Mettre en ligne

    git add pige.py schema_pige.sql test_pige.py templates/pige.html \
            templates/pige_entreprises.html main.py templates/admin.html \
            installer.py MISE_EN_PLACE_PIGE.md
    git commit -m "Pige des annonces : collecte quotidienne, historisation et signaux"
    git push

Puis ajouter les quatre variables dans les réglages Render, ce qui déclenche un
redéploiement. Au démarrage, le serveur crée les tables et lance la première
collecte.

## 5. Ce que la page montre

**L'ancienneté** de chaque annonce, en jours depuis sa publication. Une annonce
qui dure signale un recrutement qui peine.

**Les réapparitions**, c'est-à-dire les annonces disparues puis republiées.
Signal plus fort encore.

**Les entreprises les plus actives**, avec leur nombre de postes ouverts. Les
raisons sociales sont regroupées : « KPMG », « KPMG France » et « Cabinet KPMG »
comptent pour une seule entreprise.

Filtres par partie, métier et ancienneté. Export CSV de la liste filtrée.

## 6. Le périmètre, et comment le changer

| | Partie 1 | Partie 2 |
|---|---|---|
| Métier | Contrôle de gestion | Comptabilité et paie |
| Zone | Toute l'Île-de-France | Malakoff et 10 km |
| ROME | M1204 | M1203, plus M1501 pour la paie |

La zone de la partie 2 se change sans toucher au code, par deux variables
d'environnement : `PIGE_COMMUNE` (code INSEE, 92046 par défaut) et
`PIGE_DISTANCE` (10 par défaut).

Les métiers et les codes ROME sont en haut de `pige.py`, dans la liste
`RECHERCHES`.

## 7. Le point qui reste ouvert

Le code ROME du gestionnaire de paie n'est pas établi : selon les annonces il
relève de M1203 (comptabilité) ou de M1501 (assistanat RH). Les deux sont donc
interrogés, et un filtre sur l'intitulé écarte ce qui n'a rien à voir avec la
paie.

À trancher après la première vraie collecte : si l'un des deux codes ne rapporte
rien, il suffira de le retirer de `RECHERCHES` pour diviser par deux le nombre
d'appels.

## 8. Données personnelles

Les annonces sont des données d'entreprise. Un seul cas limite : certaines
mentionnent un contact nommé. Il est isolé dans la colonne `contact_nom`, jamais
affiché dans la liste, et effaçable par `pige.oublier_contact(id)`.

Le registre des traitements est à compléter d'un paragraphe sur ce point.
