# La pige des annonces

Comment elle marche, comment on la règle, et ce qu'elle écarte.

Le code tient dans un seul fichier, `pige.py`, et n'a demandé aucune
bibliothèque supplémentaire : les appels aux deux sources se font avec ce que
Python fournit déjà.

---

## 1. Les deux clés d'API

C'est la seule chose à faire pour que la collecte tourne. Quatre valeurs, dans
le `.env` en local **et** dans les variables d'environnement de l'hébergeur.

```
FT_CLIENT_ID=
FT_CLIENT_SECRET=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
```

**France Travail**, un quart d'heure. Sur `francetravail.io` : créer un
compte, déclarer une application, puis — c'est l'étape qu'on oublie —
**s'abonner à l'API « Offres d'emploi v2 »**. Sans cet abonnement, les
identifiants sont délivrés mais chaque appel répond `400 Bad Request`.

**Adzuna**, cinq minutes. Sur `developer.adzuna.com/signup` : créer un compte,
les deux valeurs sont affichées immédiatement. Gratuit jusqu'à 250 appels par
jour.

Sans ces clés, la page s'ouvre normalement et affiche un bandeau. Avec une
seule des deux sources, la collecte tourne quand même sur cette source.

---

## 2. Quand la collecte se lance

Toute seule, une fois par jour, au réveil du serveur. Un bouton
« Lancer la collecte maintenant » permet de la déclencher à la main ; compter
une à deux minutes.

Une ligne de la table `collecte` note chaque passage : l'heure, le résultat,
et l'erreur le cas échéant. C'est elle qui empêche de compter deux fois la
même journée.

---

## 3. Le périmètre

|  | Partie 1 | Partie 2 |
|---|---|---|
| Métier | Contrôle de gestion | Comptabilité et paie |
| Zone | Toute la France | Malakoff et 10 km |
| Contrats | Missions courtes seulement | Tous |
| Code ROME | M1204 | M1203, plus un mot-clé pour la paie |

**Partie 1, les missions courtes.** Le cabinet ne pige que de l'intérim, du
CDD et du management de transition : les codes `CDD,MIS,DDI,TTI` sont demandés
à France Travail, et le CDI est écarté. Une exception est prévue — un poste
annoncé en CDI passe quand même si son intitulé se décrit comme une mission,
ce qui est le cas du management de transition, souvent publié sans code de
contrat adapté.

**Partie 2, sans filtre de contrat.** Cabinet d'expertise comptable comme
entreprise, CDI comme CDD. La zone se change sans toucher au code, par deux
variables d'environnement : `PIGE_COMMUNE` (code INSEE, 92046 par défaut) et
`PIGE_DISTANCE` (10 par défaut).

Les métiers et les codes ROME sont en haut de `pige.py`, dans la liste
`RECHERCHES`.

---

## 4. Ce qui est écarté, et pourquoi

Sur 2 066 annonces collectées lors de la première campagne complète,
536 ont été retenues. Voici où sont passées les autres.

| Motif | Part |
|---|---|
| Hors des 10 km (partie 2) | 22,7 % |
| Cabinets de recrutement et agences d'intérim | 21,2 % |
| Secteur public | 11,9 % |
| Alternance et formation | 8,7 % |
| Entreprise non nommée | 7,0 % |
| Publiée il y a plus de 120 jours | 2,7 % |

**Les confrères.** Cabinets et agences recrutent pour une entreprise dont ils
taisent le nom : il n'y a personne à démarcher derrière l'annonce. Le tri se
fait sur une liste d'enseignes connues et sur des mots révélateurs de la
raison sociale.

**Le secteur public.** Une mairie, un hôpital ou un ministère ne choisit pas
librement son prestataire : il passe par marché public. Le démarchage n'y sert
à rien.

**Les annonces sans nom d'entreprise.** Inexploitables en prospection.

**Le hors-rayon.** France Travail sait filtrer par commune et rayon. Adzuna
ignore le rayon dès qu'il ne reconnaît pas la ville, et renvoie alors la
France entière : la vérification se fait donc côté plateforme.

**Les trop anciennes.** Au-delà de 120 jours, le poste est probablement
pourvu et l'annonce simplement oubliée en ligne.

Rien n'est supprimé. Les annonces écartées restent en base avec leur motif et
se consultent depuis la page, en choisissant « les annonces écartées » dans le
filtre. Aucun tri automatique n'est parfait : si un vrai prospect s'y trouve,
il suffit d'ajuster les listes en haut de `pige.py`.

---

## 5. Ce que la page montre

**L'ancienneté** de chaque annonce, en jours depuis sa publication. Une
annonce qui dure signale un recrutement qui peine.

**Les réapparitions**, c'est-à-dire les annonces disparues puis republiées.
Signal plus fort encore : le poste a été pourvu puis a été libéré, ou bien le
recrutement a échoué.

**Les entreprises les plus actives**, avec leur nombre de postes ouverts. Les
raisons sociales sont regroupées : « KPMG », « KPMG France » et
« Cabinet KPMG » comptent pour une seule entreprise.

Filtres par partie, par métier et par ancienneté. Export CSV de la liste
filtrée.

---

## 6. Le dédoublonnage

Deux annonces sont la même offre si elles portent la même entreprise, le même
intitulé et la même commune. Une empreinte les résume — le condensé SHA-1 de
ces trois éléments normalisés — et sert de clé unique en base.

« Normalisé » fait le gros du travail : les accents sont aplatis, la
ponctuation retirée, les formes juridiques (SA, SAS, SARL) et les mots vides
supprimés. Sans quoi « KPMG S.A.S. » et « KPMG SAS » seraient deux
entreprises différentes.

Sur la première collecte, les deux sources ne se recouvraient presque pas :
62,5 % des prospects venaient d'Adzuna seul, 36,6 % de France Travail seul, et
0,9 % des deux.

---

## 7. Les contacts de prospection

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

Le [registre des traitements](REGISTRE_TRAITEMENTS.md) décrit ce second
traitement en détail.

---

## 8. Données personnelles

Les annonces sont des données d'entreprise. Deux cas limites :

- certaines mentionnent un **contact nommé**. Il est isolé dans la colonne
  `contact_nom`, jamais affiché dans la liste, et effaçable par
  `pige.oublier_contact(id)` ;
- les **adresses de contact**, traitées à la section précédente.

---

## 9. Le point qui reste ouvert

Le code ROME du gestionnaire de paie n'est pas établi : selon les annonces il
relève de M1203 (comptabilité) ou de M1501 (assistanat RH). À l'essai, M1203
donnait 8 résultats et M1501 un seul, tandis qu'une recherche par mot-clé sur
« paie » en donnait 211. C'est donc le mot-clé qui est utilisé.

Attention au passage à un piège de l'API France Travail : plusieurs mots-clés
séparés par des virgules sont combinés en **ET**, pas en OU. `paie,gestionnaire
de paie,payroll` ne renvoyait qu'une annonce ; `paie` seul en renvoie 211.

---

## 10. Les tables

| Table | Ce qu'elle contient |
|---|---|
| `annonce` | Une ligne par offre distincte, écartée ou non |
| `observation` | Une ligne par annonce et par jour où elle a été revue |
| `collecte` | Le journal des passages |
| `contact_pige` | Les adresses, leur jeton et leur désinscription |

Plus une vue, `v_prospects`, qui recalcule l'ancienneté à chaque lecture — de
sorte qu'elle est juste tous les jours sans qu'on ait rien à mettre à jour.

Elles sont créées automatiquement au premier démarrage.
`schema_pige.sql` sert de référence.

---

## 11. Vérifier

```bash
python test_pige.py
```

Sans réseau ni base de données. Le script contrôle le dédoublonnage, la
normalisation des raisons sociales, les filtres de tri et le calcul du
périmètre.
