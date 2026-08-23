# Plateforme de tests candidats

Application web permettant d'envoyer à un candidat un lien unique vers un test
chronométré, puis de consulter le résultat corrigé automatiquement.

Huit tests sont fournis : test technique et questionnaire de positionnement,
en comptabilité et en paie, niveaux junior et confirmé.

Tout le code est en Python. Aucune autre technologie n'est nécessaire.

---

## 1. Ce dont vous avez besoin

- Python 3.11 ou plus récent
- Une base PostgreSQL. Le plus simple est un service hébergé : Neon ou Supabase
  proposent une offre gratuite suffisante. **Choisissez une région européenne**,
  les réponses des candidats sont des données personnelles.

## 2. Installation

```bash
pip install -r requirements.txt
```

Définissez les variables d'environnement :

```bash
export DATABASE_URL="postgresql://utilisateur:motdepasse@hote/base?sslmode=require"
export MOT_DE_PASSE_RECRUTEUR="un-mot-de-passe-long-et-unique"
export URL_PUBLIQUE="https://tests.votre-cabinet.fr"
export JOURS_VALIDITE=7           # durée de vie d'un lien d'invitation
export JOURS_CONSERVATION=180     # avant purge des données du candidat
```

Créez les tables puis chargez les questions :

```bash
psql "$DATABASE_URL" -f schema.sql
psql "$DATABASE_URL" -f schema_analyse.sql
python charger_banque.py
```

## 3. Lancement

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

- Back-office recruteur : `/admin` (identifiant libre, mot de passe ci-dessus)
- Lien candidat : généré depuis le back-office, de la forme `/t/{token}`

## 4. Utilisation au quotidien

1. Ouvrez `/admin`.
2. Choisissez le test, saisissez le nom du candidat, générez le lien.
3. Copiez le lien affiché dans la colonne de droite et envoyez-le au candidat.
4. Le résultat apparaît dans le tableau dès que le candidat a validé.

Un lien correspond à un candidat et à un test. Pour faire passer les deux tests
à la même personne, générez deux liens.

## 5. Points de fonctionnement à connaître

**Le chronomètre est calculé par le serveur.** L'heure de démarrage est
enregistrée en base au premier clic sur « Démarrer ». Recharger la page, fermer
le navigateur ou modifier le compte à rebours affiché ne prolonge pas le test.
Le temps continue de s'écouler même si le candidat s'interrompt.

**Les réponses sont enregistrées question par question.** Si la connexion est
perdue, le candidat revient sur son lien et reprend où il en était.

**Un test validé ne peut plus être rouvert.** Le lien devient inutilisable.

**Le token fait 22 caractères tirés aléatoirement.** Il n'est pas devinable, mais
il n'est pas secret pour autant : toute personne disposant du lien peut passer le
test. Ne le publiez pas et ne le mettez pas en copie d'un message collectif.

## 6. Correction

*Tests techniques.* Une question est validée uniquement si toutes les bonnes
réponses sont cochées et qu'aucune réponse erronée ne l'est. Pas de point négatif,
pas de point partiel.

*Questionnaires de positionnement.* Aucune note. La partie 1 produit un profil
sur sept dimensions, dont les totaux s'additionnent toujours à 21 : le profil est
**relatif à chaque candidat** et ne permet pas de comparer deux candidats entre
eux. La partie 2 relève les choix faits en situation et signale les points de
vigilance.

Ces questionnaires ne sont pas des tests psychométriques validés. Ils préparent
l'entretien et ne doivent jamais servir seuls à écarter une candidature.

## 7. Données personnelles

- Le candidat est informé avant de démarrer et doit cocher une case.
- La colonne `purge_apres` fixe la date de suppression, calculée à la création.
- La table `journal` conserve la trace des événements (ouverture, démarrage,
  soumission, expiration).

Purge à programmer une fois par jour :

```sql
UPDATE invitation
   SET candidat_nom = NULL, candidat_email = NULL, token = 'purge_' || id
 WHERE purge_apres < CURRENT_DATE;
```

Les résultats sont conservés sans identité, ce qui permet de garder des
statistiques sans conserver de données personnelles.

## 8. Modifier une question

Le fichier `banque_questions.json` est la source unique : c'est lui qui alimente
la base. Modifiez-le, puis relancez :

```bash
python charger_banque.py
```

Le script remplace proprement les tests concernés. Les invitations déjà passées
conservent leurs résultats.

## 9. Vérifier que tout fonctionne

```bash
python test_correction.py
```

Ce script contrôle la logique de correction sur la banque réelle : règle du tout
ou rien, équilibre des sept dimensions, comptage des points de vigilance.

---

## 10. Couche analytique

L'application ne se contente pas de corriger : elle mesure la qualité de ses
propres questions à partir des passations réelles.

### Ce qui est collecté

La table `vue_question` enregistre, pour chaque candidat et chaque question, le
temps passé et le nombre de retours. Sans cette donnée, aucune analyse d'items
n'est possible : c'est elle qui distingue une question difficile d'une question
survolée.

### Analyse d'items — `/admin/analyse/{test_id}`

Pour chaque question, trois indicateurs :

- **Taux de réussite** (`p`) : part des candidats qui valident la question.
  Signalée au-dessus de 95 % (n'apporte aucune information) et en dessous de
  20 % (trop difficile, ou corrigé erroné).
- **Corrélation item-total** (`r`) : corrélation entre la réussite à cette
  question et le score global. En dessous de 0,10, la question ne sépare pas les
  candidats solides des autres — c'est la signature d'un énoncé ambigu.
- **Temps médian** : une médiane de trois secondes ou moins signale une question
  systématiquement expédiée.

Le seuil de fiabilité est fixé à trente passations. En dessous, l'interface
affiche un avertissement explicite.

### Questionnaires de positionnement

- **Profil agrégé** : moyenne et médiane de chaque dimension sur l'ensemble des
  candidats. C'est le seul moyen de situer un candidat par rapport aux autres,
  puisque son profil individuel est relatif.
- **Répartition des situations** : part de chaque option choisie et part de
  candidats ayant retenu un point de vigilance. Une option jamais choisie est un
  distracteur inutile, signalé comme tel.

### Signalements individuels

Calculés à la validation et stockés dans `anomalie` :

| Code | Détection |
|---|---|
| `passation_rapide` | Moins de 30 % du temps imparti |
| `reponses_eclair` | Un quart des questions traitées en 3 secondes ou moins |
| `reponse_monotone` | 80 % des réponses sur la même position |
| `profil_plat` | Écart de 1 point ou moins entre la dimension haute et basse |
| `incomplet` | Un cinquième des questions sans réponse |
| `temps_epuise` | Le temps imparti a été entièrement consommé |

Ces signalements alimentent l'entretien. Ils ne sont jamais disqualifiants et
l'interface le rappelle au recruteur.

### Export — `/admin/export.csv`

Une ligne par question et par passation, sans aucune donnée nominative :
identifiant de passation, test, numéro de question, temps passé, réussite, score
global, durée totale, jour. Exploitable directement dans pandas.

### Ce qui deviendra possible avec du volume

À partir d'une cinquantaine de recrutements suivis dans le temps, les données
collectées permettent de croiser le score obtenu avec la réussite en poste, et
donc de savoir si le test prédit réellement quelque chose. Tant que ce recul
n'existe pas, aucun modèle prédictif ne serait honnête : le schéma est conçu pour
l'accueillir, pas pour le simuler.

### Vérification

```bash
python test_correction.py   # logique de correction
python test_analyse.py      # analyse d'items et signalements
```

Le second simule soixante passations dont deux questions volontairement
défectueuses, et vérifie que l'analyse les repère sans signaler les questions
saines.

---

## 11. Guide d'entretien genere automatiquement

Fonction facultative, desactivee par defaut. Elle transforme un profil de
positionnement en questions a poser en entretien.

### Ce que la fonction fait et ne fait pas

Le modele **ne produit aucune evaluation du candidat**. Il ne dit pas si le profil
convient, ne recommande rien, ne compare personne. Il reformule un profil deja
calcule en guide de preparation. La decision reste entierement au recruteur.

Ce cadrage n'est pas cosmetique. Une evaluation automatisee de personne en
recrutement releve du RGPD sur les decisions automatisees et du reglement europeen
sur l'IA, qui classe cet usage a haut risque. Un outil qui se contente de proposer
des questions ne tombe pas dans ce champ.

### Garde-fous techniques

1. **Aucune donnee nominative transmise.** Seuls le profil chiffre, les choix en
   situation, le poste vise et le niveau partent chez le fournisseur. Ni nom, ni
   adresse, ni identifiant.
2. **Consigne contraignante.** Le modele recoit l'interdiction explicite de porter
   un jugement, de noter, de classer ou de recommander.
3. **Controle de la sortie.** Avant enregistrement, le texte est verifie contre une
   liste de formulations interdites (recommandation d'embauche, profil a ecarter,
   note globale, comparaison entre candidats). En cas de detection, la generation
   est rejetee et rien n'est enregistre.
4. **Declenchement manuel.** Le guide n'est jamais produit automatiquement : le
   recruteur clique.
5. **Tracabilite.** Le modele utilise, l'auteur de la demande et la date sont
   conserves dans `guide_entretien`, et l'evenement est journalise.

### Configuration

Dans le fichier `.env` :

```
IA_FOURNISSEUR=anthropic     # ou openai
IA_CLE_API=votre_cle
IA_MODELE=claude-haiku-4-5-20251001
```

Sans cle, la fonction reste invisible et l'application fonctionne normalement.

### Cout

Chaque generation envoie environ 1 500 tokens et en recoit 900, soit moins d'un
centime avec Haiku 4.5 et environ un centime avec Sonnet 5.

Seuls les questionnaires de positionnement declenchent une generation : les tests
techniques sont corriges par le code, sans appel a l'IA. Un cabinet qui fait passer
six entretiens par mois consomme donc de l'ordre de dix centimes mensuels.

Les credits prepayes expirent un an apres l'achat. Le minimum de 5 dollars couvre
largement plusieurs annees a ce rythme : n'achetez pas davantage.

Verifiez la tarification en vigueur, elle evolue.

### Verification

```bash
python test_ia.py
```

Le script controle que sept formulations inacceptables sont bien rejetees, que la
charge utile ne contient aucune identite, et que l'absence de cle degrade
proprement sans faire tomber l'application.
