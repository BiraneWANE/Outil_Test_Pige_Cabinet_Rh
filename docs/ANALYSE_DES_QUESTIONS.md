# Mesurer la qualité des questions

Un test qui n'est jamais évalué finit par mesurer autre chose que ce qu'on
croit. Ce module regarde les passations réelles et dit quelles questions
fonctionnent.

---

## 1. Ce qui est collecté

La table `vue_question` enregistre, pour chaque candidat et chaque question,
le **temps passé** et le **nombre de retours**.

Sans cette donnée, aucune analyse d'items n'est possible : c'est elle qui
distingue une question difficile — sur laquelle on s'attarde et qu'on rate —
d'une question survolée.

---

## 2. L'analyse d'items — `/admin/analyse/{test_id}`

Trois indicateurs par question.

**Le taux de réussite** (`p`) : la part des candidats qui valident la
question. Signalé au-dessus de 95 % et en dessous de 20 %.

Une question réussie par tout le monde n'apporte aucune information : elle
occupe du temps sans rien distinguer. Une question ratée par tout le monde est
soit hors programme, soit — plus souvent — mal formulée, voire mal corrigée.

**La corrélation item-total** (`r`) : la corrélation entre la réussite à cette
question et le score global. Signalée en dessous de 0,10.

C'est l'indicateur le plus utile et le moins intuitif. Il répond à la
question : *les candidats qui réussissent ce test réussissent-ils aussi cette
question ?* Si la réponse est non, quelque chose cloche — soit l'énoncé est
ambigu et se joue au hasard, soit il mesure autre chose que le reste du test.
Une question peut avoir un taux de réussite parfaitement raisonnable et une
corrélation nulle : c'est la signature typique d'un piège involontaire.

**Le temps médian** : une médiane de trois secondes ou moins signale une
question systématiquement expédiée. Soit elle est triviale, soit elle est
tellement longue que les candidats renoncent à la lire.

---

## 3. Le seuil de fiabilité

Trente passations. En dessous, l'interface affiche un avertissement explicite
plutôt que des chiffres.

Ce n'est pas de la prudence de façade : sur dix passations, une corrélation
peut passer de 0,05 à 0,45 parce qu'un seul candidat a répondu autrement.
Afficher le chiffre sans le contexte, c'est inviter à supprimer une bonne
question.

---

## 4. Les questionnaires de positionnement

Ils n'ont pas de note, donc pas de taux de réussite. Deux mesures les
remplacent.

**Le profil agrégé** : moyenne et médiane de chaque dimension sur l'ensemble
des candidats. C'est le seul moyen de situer un candidat par rapport aux
autres, puisque son profil individuel est relatif — les sept dimensions
totalisent toujours 21 points, quel que soit le candidat.

**La répartition des situations** : la part de chaque option choisie, et la
part de candidats ayant retenu un point de vigilance. Une option que personne
ne choisit jamais est un distracteur inutile : elle est signalée comme telle.

---

## 5. Les signalements individuels

Calculés à la validation et stockés dans `anomalie`.

| Code | Détection |
|---|---|
| `passation_rapide` | Moins de 30 % du temps imparti |
| `reponses_eclair` | Un quart des questions traitées en 3 secondes ou moins |
| `reponse_monotone` | 80 % des réponses sur la même position |
| `profil_plat` | Écart de 1 point ou moins entre la dimension haute et la basse |
| `incomplet` | Un cinquième des questions sans réponse |
| `temps_epuise` | Le temps imparti a été entièrement consommé |

Ces signalements alimentent l'entretien : ils donnent une question à poser, pas
une conclusion. Ils ne sont jamais disqualifiants, et l'interface le rappelle
au recruteur à chaque affichage.

Un `profil_plat`, par exemple, veut souvent dire que le candidat a répondu ce
qu'il pensait attendu plutôt que ce qu'il fait vraiment. Cela se discute très
bien en entretien ; cela n'écarte personne.

---

## 6. L'export — `/admin/export.csv`

Une ligne par question et par passation, **sans aucune donnée nominative** :
identifiant de passation, test, numéro de question, temps passé, réussite,
score global, durée totale, jour.

Exploitable directement dans pandas. C'est ce fichier qui permettrait, avec du
recul, les analyses décrites plus bas.

---

## 7. Ce qui deviendra possible avec du volume

À partir d'une cinquantaine de recrutements suivis dans le temps, ces données
permettent de croiser le score obtenu avec la réussite en poste — et donc de
savoir si le test prédit réellement quelque chose.

C'est la seule question qui compte vraiment pour un test de recrutement, et
c'est aussi la plus rarement posée.

Tant que ce recul n'existe pas, aucun modèle prédictif ne serait honnête : on
apprendrait du bruit et on l'appellerait un résultat. Le schéma de la base est
conçu pour accueillir cette analyse le jour où les données existeront, pas pour
la simuler aujourd'hui.

---

## 8. Vérifier

```bash
python test_correction.py   # la logique de correction
python test_analyse.py      # l'analyse d'items et les signalements
```

Le second fabrique soixante passations simulées, dont deux questions
volontairement défectueuses — une trop facile, une sans corrélation — et
vérifie que l'analyse les repère **sans** accuser les questions saines. C'est
le seul moyen de tester un outil de mesure : lui donner un défaut connu et
regarder s'il le trouve.
