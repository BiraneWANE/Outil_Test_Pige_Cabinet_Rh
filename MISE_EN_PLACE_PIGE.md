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
| Zone | Toute la France | Malakoff et 10 km |
| Contrats | Missions courtes seulement | Tous |
| ROME | M1204 | M1203, plus M1501 pour la paie |

**Partie 1, les missions courtes.** Le cabinet ne pige que de l'intérim, du CDD et
du management de transition : les codes de contrat `CDD,MIS,DDI,TTI` sont demandés
à France Travail, et le CDI est écarté. Une exception est prévue : un poste annoncé
en CDI passe quand même si son intitulé se décrit comme une mission, ce qui est le
cas du management de transition, souvent publié sans code de contrat adapté.

**Partie 2, sans filtre de contrat.** Cabinet d'expertise comptable comme
entreprise, CDI comme CDD. La zone se change sans toucher au code, par deux
variables d'environnement : `PIGE_COMMUNE` (code INSEE, 92046 par défaut) et
`PIGE_DISTANCE` (10 par défaut).

Les métiers et les codes ROME sont en haut de `pige.py`, dans la liste
`RECHERCHES`.

## 7. Ce qui est écarté du tri, et pourquoi

Trois catégories d'annonces sont mises de côté à la collecte :

**Les cabinets de recrutement et les agences d'intérim.** Ce sont des confrères,
pas des clients : ils recrutent pour une entreprise dont ils taisent le nom, il
n'y a donc personne à démarcher derrière l'annonce. Le tri se fait sur une liste
d'enseignes connues et sur des mots révélateurs de la raison sociale
(`ENSEIGNES_INTERMEDIAIRE` et `MOTS_INTERMEDIAIRE` en haut de `pige.py`).

**Les annonces sans nom d'entreprise.** Inexploitables en prospection.

**Les annonces hors des 10 kilomètres**, pour la partie 2. France Travail sait
filtrer par commune et rayon, mais Adzuna ignore le rayon dès qu'il ne reconnaît
pas la ville et renvoie la France entière. La vérification se fait donc côté
plateforme, sur la liste `COMMUNES_PARTIE_2`.

Rien n'est supprimé. Les annonces écartées restent en base avec leur motif et
se consultent depuis la page, en choisissant « les annonces écartées » dans le
filtre. Aucun tri automatique n'est parfait : si un vrai prospect s'y trouve,
il suffit d'ajuster les listes en haut de `pige.py`.

## 8. Le point qui reste ouvert

Le code ROME du gestionnaire de paie n'est pas établi : selon les annonces il
relève de M1203 (comptabilité) ou de M1501 (assistanat RH). Les deux sont donc
interrogés, et un filtre sur l'intitulé écarte ce qui n'a rien à voir avec la
paie.

À trancher après la première vraie collecte : si l'un des deux codes ne rapporte
rien, il suffira de le retirer de `RECHERCHES` pour diviser par deux le nombre
d'appels.

## 9. Les contacts de prospection

Les offres France Travail portent parfois une adresse de contact. Elle est
collectée, mais encadrée, parce qu'elle a été publiée pour recevoir des
candidatures et non pour être démarchée.

Page `/admin/pige/contacts`. Le fichier d'envoi ne contient par défaut que les
adresses **génériques** (`contact@`, `recrutement@`, `rh@`), qui désignent une
fonction et non une personne. Les nominatives sont comptées à part.

Chaque adresse a son **lien de désinscription**, fourni dans l'export et à
placer dans le courriel. La page `/desinscription/{jeton}` est publique, sans
mot de passe : un clic suffit, et l'opposition tient même si l'entreprise
republie une offre plus tard.

La **mention d'information** à recopier dans le courriel est affichée sur la
page. Elle n'est pas décorative : c'est elle qui rend l'envoi régulier.

Le registre des traitements décrit ce second traitement en détail.

## 10. Données personnelles des candidats

Les annonces sont des données d'entreprise. Un seul cas limite : certaines
mentionnent un contact nommé. Il est isolé dans la colonne `contact_nom`, jamais
affiché dans la liste, et effaçable par `pige.oublier_contact(id)`.

Le registre des traitements est à compléter d'un paragraphe sur ce point.
