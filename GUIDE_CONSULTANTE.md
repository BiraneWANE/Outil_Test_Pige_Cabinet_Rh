# Guide d'utilisation

Ce document s'adresse à la personne qui fait passer les tests. Aucune
connaissance technique n'est nécessaire.

---

## Faire passer un test à un candidat

1. Ouvrez l'adresse de l'application suivie de `/admin`. Le navigateur demande un
   identifiant et un mot de passe. L'identifiant est libre, il sert seulement à
   savoir qui a créé l'invitation.
2. Dans l'encadré **Créer une invitation**, choisissez le test, saisissez le nom
   du candidat, puis cliquez sur **Générer le lien**.
3. La ligne apparaît dans le tableau. Copiez le lien affiché à droite et
   envoyez-le au candidat par courriel.

Un lien correspond à un candidat et à un seul test. Pour faire passer le test
technique **et** le questionnaire de positionnement à la même personne, créez
deux invitations et envoyez les deux liens.

Le lien reste valable une semaine. Passé ce délai, il faut en générer un nouveau.

---

## Suivre les passations

La colonne **Statut** indique où en est chaque candidat :

| Statut | Signification |
|---|---|
| envoyee | Le lien a été créé, le candidat ne l'a pas encore ouvert |
| en_cours | Le test est commencé et pas encore validé |
| terminee | Le candidat a validé, le résultat est disponible |
| expiree | Le lien a dépassé sa durée de validité |

Le résultat apparaît automatiquement dès la validation. Cliquez sur **détail**
pour ouvrir la fiche complète.

---

## Lire un résultat de test technique

Vous voyez le score, le pourcentage et une phrase d'interprétation, puis le
détail question par question. Les lignes en rouge sont les questions ratées, avec
la justification de la bonne réponse.

En haut de la fiche, une **synthèse** décrit le résultat en quelques phrases :
combien de questions validées, sur quels thèmes les réponses sont entièrement
justes, sur lesquels la maîtrise est partielle, et lesquels ont été majoritairement
manqués. Le tableau **Résultat par thème** donne le détail, avec les numéros des
questions ratées.

C'est ce qui distingue deux candidats à 12 sur 15 : l'un peut avoir un trou net sur
toute la TVA, l'autre des erreurs éparpillées. Le score seul ne le dit pas, la
synthèse si.

Cette synthèse est calculée, pas rédigée par une IA. Elle ne porte aucun jugement
sur la personne : elle décrit uniquement ce que le test mesure, c'est-à-dire des
connaissances à un instant donné.

Une question compte pour un point entier ou pour rien : si le candidat coche deux
bonnes réponses sur trois, il n'a pas le point. C'est volontaire, cela évite
qu'un candidat gagne des points en cochant toutes les cases.

---

## Lire un questionnaire de positionnement

**Il n'y a pas de note.** Ne cherchez pas de score, il n'y en a pas.

*Le profil.* Sept dimensions, chacune notée de 0 à 6. Les totaux font toujours 21
au total. C'est important : cela signifie que le profil est **relatif au
candidat**. Il vous dit ce que cette personne met en avant en priorité, pas si
elle est plus rigoureuse qu'une autre. Ne comparez donc pas deux candidats
dimension par dimension.

*Les mises en situation.* Chaque choix est commenté. Les encadrés bordés de rouge
signalent un point de vigilance : une réponse qui mérite d'être creusée en
entretien. Ce n'est jamais un motif d'élimination à lui seul.

*Ce qu'il faut en faire.* Reprenez deux ou trois réponses en entretien et
demandez un exemple vécu. Un candidat qui a coché ce qu'il croyait attendu peine
à fournir l'exemple.

---

## Transmettre un résultat à un client

Depuis la fiche d'un candidat, le bouton **Télécharger le PDF** produit un rapport
complet, prêt à être envoyé par courriel.

Le PDF contient l'identité du candidat, le test passé, la date, la durée, le
résultat détaillé et les signalements automatiques. Pour un questionnaire de
positionnement, il reprend aussi l'encadré rappelant qu'il ne s'agit pas d'un test
psychométrique validé. Cette mention doit rester dans le document transmis : elle
protège le cabinet autant que le candidat.

Chaque page porte en bas la mention « Document confidentiel ». Ce rapport contient
des données personnelles : ne le diffusez qu'aux personnes qui participent
réellement à la décision de recrutement.

Depuis le tableau des invitations, le lien **PDF** de chaque ligne fait la même
chose sans passer par la fiche.

Le lien **Télécharger tous les résultats (CSV)** produit un tableau récapitulatif
de toutes les passations, à ouvrir dans Excel : un candidat par ligne, avec le
test, le statut, la date et le score. Utile pour un suivi mensuel ou pour préparer
un point avec un client.

---

## Les signalements automatiques

En haut de certaines fiches, un encadré signale des points relevés
automatiquement : test terminé beaucoup trop vite, questions expédiées en
quelques secondes, réponses presque toutes sur la même position, questionnaire
incomplet.

Ce sont des indices sur la manière dont le candidat a répondu, pas des jugements
sur la personne. Rien ne justifie d'écarter quelqu'un sur cette seule base.

---

## L'analyse des tests

Depuis le back-office, cliquez sur **analyse des tests**, puis choisissez un test.

*Les cartes du haut* donnent les volumes : invitations envoyées, terminées, taux
de complétion, score médian, durée médiane. Un taux de complétion bas signifie
souvent que le lien arrive mal ou que la consigne n'est pas claire.

*La distribution des scores* montre comment les candidats se répartissent. Si
tout le monde obtient à peu près la même chose, le test ne sert pas à
grand-chose : il ne sépare personne.

*La qualité des questions* est la partie la plus utile. Pour chaque question :

- **Réussite** : la part de candidats qui la valident. Une question réussie par
  tout le monde n'apporte aucune information. Une question ratée par tout le
  monde est soit trop difficile, soit mal corrigée.
- **Discrimination** : le lien entre réussir cette question et bien réussir
  l'ensemble du test. Si cette valeur est proche de zéro, les bons candidats la
  ratent autant que les autres, ce qui trahit presque toujours un énoncé ambigu.
- **Temps médian** : une question expédiée en trois secondes n'a pas été lue.

Les questions problématiques sont surlignées et récapitulées en bas.

**Attention à l'effectif.** En dessous de trente passations, l'application vous
affiche un avertissement. Ces indicateurs deviennent fiables avec du volume : ne
retirez jamais une question sur la base de cinq candidats.

---

## L'export des données

Le lien **Télécharger les données au format CSV** produit un fichier sans aucune
identité : une ligne par question et par passation, avec les temps et les
résultats. Il sert à faire des analyses plus poussées dans un tableur ou un
carnet d'analyse.

---

## Les données personnelles

Le candidat est informé avant de démarrer et doit cocher une case.

Chaque invitation porte une date de suppression, fixée à six mois par défaut. Une
tâche automatique efface alors le nom et l'adresse électronique, en conservant le
résultat sans identité pour les statistiques.

Si un candidat demande l'accès à ses réponses ou leur effacement, c'est possible :
la demande se traite depuis la base, faites-la remonter.

---

## En cas de problème

**Un candidat dit que son lien ne fonctionne pas.** Vérifiez le statut. S'il est
« terminee », il a déjà validé et ne peut plus revenir. S'il est « expiree »,
générez une nouvelle invitation.

**Un candidat a été coupé en pleine passation.** Il peut rouvrir son lien et
reprendre où il en était. Le temps a continué de s'écouler pendant l'interruption :
c'est volontaire, sinon la durée ne voudrait plus rien dire.

**Le score paraît anormal.** Ouvrez le détail : la justification de chaque
question y figure. Si une question vous semble mal corrigée, signalez-la, elle se
modifie dans le fichier des questions.

**L'application ne répond plus.** Elle est hébergée : il faut la relancer depuis
la console de l'hébergeur. C'est le seul cas qui demande une intervention
technique.

---

## Le guide d'entretien automatique

Sur la fiche d'un questionnaire de positionnement, un bouton **Générer un guide
d'entretien** produit une liste de questions à poser, construite à partir du
profil du candidat.

**Ce que ce guide est.** Une aide à la préparation : des questions ouvertes
demandant des exemples vécus, et des points à vérifier pendant l'échange.

**Ce qu'il n'est pas.** Une évaluation. Vous n'y trouverez jamais « ce candidat
convient » ou « profil à écarter », et c'est volontaire : un outil automatique ne
doit pas porter de jugement sur une personne. Si vous voyez apparaître une phrase
de ce type, signalez-la, c'est un dysfonctionnement.

**Comment l'utiliser.** Lisez-le, gardez les questions qui vous parlent, écartez
les autres. C'est un point de départ, pas un script à dérouler.

**Relisez toujours avant de vous en servir.** Le texte est produit
automatiquement et peut contenir une maladresse ou une question mal formulée.

Ce guide ne part jamais dans le PDF transmis au client : il reste un document de
travail interne.

---

## Peut-on empêcher un candidat d'utiliser une IA ?

Non, et il vaut mieux le savoir.

**Ce qui a été mis en place.** La copie des énoncés est désactivée, ainsi que le
clic droit et la sélection de texte. Le candidat est prévenu, sur la page
d'accueil, que le test doit être passé seul.

**Ce qui reste impossible.** Aucune application web ne peut empêcher une capture
d'écran, et rien n'empêche un candidat de lire la question à l'écran pour la
retaper sur son téléphone. Le blocage de la copie est un frein au geste réflexe,
pas une protection.

**Ce qui est mesuré à la place.** L'application enregistre le nombre de fois où le
candidat quitte la page pendant l'épreuve, ainsi que les tentatives de copie. Ces
éléments apparaissent dans les signalements automatiques de la fiche de résultat.

Attention à la lecture : quitter la page ne prouve rien. Un candidat peut avoir
répondu au téléphone ou basculé sur sa messagerie. Six sorties sur un test de vingt
minutes méritent une question en entretien, pas une conclusion.

**Ce qui fonctionne vraiment.** Reprendre en entretien trois questions du test et
demander au candidat d'expliquer son raisonnement. Celui qui a répondu seul le fait
sans effort. C'est la seule vérification réellement fiable, et elle prend cinq
minutes.

Un test non surveillé filtre, il ne prouve pas. C'est vrai de tous les tests à
distance, y compris ceux des éditeurs spécialisés.
