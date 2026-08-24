# Guide d'utilisation

Ce document s'adresse à la personne qui fait passer les tests. Aucune
connaissance technique n'est nécessaire.

**Adresse de l'application : https://tests-candidats.onrender.com/admin**

Mettez-la en favori. Le navigateur demande un identifiant et un mot de passe.
L'identifiant est libre, il sert seulement à savoir qui a créé l'invitation ; le
mot de passe vous a été transmis séparément et ne doit pas circuler par courriel.

L'application est disponible en permanence, pour vous comme pour les candidats.
Les pages s'ouvrent en quelques secondes, à toute heure.

---

## Faire passer un test à un candidat

1. Ouvrez l'application et identifiez-vous.
2. Dans l'encadré **Créer une invitation**, choisissez le test, saisissez le nom
   du candidat, puis cliquez sur **Générer le lien**.
3. La ligne apparaît dans le tableau. Copiez le lien affiché à droite et
   envoyez-le au candidat par courriel.

Un lien correspond à un candidat et à un seul test. Pour faire passer le test
technique **et** le questionnaire de positionnement à la même personne, créez
deux invitations et envoyez les deux liens.

Le lien reste valable **quatre jours**. Passé ce délai, il faut en générer un
nouveau. Tenez-en compte pour vos envois de fin de semaine : un lien envoyé le
vendredi soir n'est plus valable le mercredi suivant.

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

À droite de chaque ligne, un bouton **supprimer** efface définitivement la
passation. Voir plus bas, « Supprimer une passation ».

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

**Attention à l'effectif.** L'application se tait tant qu'elle n'a pas de quoi
parler, et c'est volontaire :

- **moins de dix passations** : aucun signalement n'est émis. Avec deux ou trois
  candidats, toute question réussie paraîtrait « trop facile » et toute question
  ratée « trop difficile ». Ce seraient des artefacts, pas des mesures. Les taux
  restent affichés à titre indicatif.
- **entre dix et trente** : les signalements apparaissent, accompagnés d'un
  avertissement. C'est une tendance, pas une mesure.
- **au-delà de trente** : les indicateurs deviennent exploitables.

Ne retirez jamais une question sur la base de cinq candidats. À votre volume,
une douzaine de passations par mois, comptez plusieurs mois avant que cette page
ne devienne vraiment parlante.

---

## L'export des données

Le lien **Télécharger les données au format CSV** produit un fichier sans aucune
identité : une ligne par question et par passation, avec les temps et les
résultats. Il sert à faire des analyses plus poussées dans un tableur ou un
carnet d'analyse.

---

## Les données personnelles

Le candidat est informé avant de démarrer et doit cocher une case. Cette
acceptation est horodatée.

Depuis le back-office, le lien **données personnelles** ouvre une page qui montre
en un coup d'œil combien de passations sont encore nominatives, combien sont déjà
anonymisées, et à quelle date tombe la prochaine échéance.

**L'effacement automatique.** Chaque invitation porte une date de suppression,
fixée à six mois. À l'échéance, le nom, l'adresse électronique et le poste visé
sont effacés, le lien d'accès est neutralisé et le guide d'entretien supprimé. Ce
qui reste, réponses, temps et score, ne permet plus d'identifier personne et sert
à mesurer la qualité des questions. Vous n'avez rien à faire : la purge se
déclenche toute seule. Le bouton **Lancer la purge maintenant** ne sert qu'à la
provoquer plus tôt, et ne touche jamais une passation dont le délai n'est pas
écoulé.

**Si un candidat demande l'accès à ses données**, le rapport PDF de sa passation
constitue la copie de ce qui est traité : téléchargez-le et envoyez-le lui.

**S'il demande leur effacement**, utilisez le bouton **supprimer** de sa ligne.
Vous n'avez plus besoin de faire remonter la demande.

Comptez un mois maximum pour répondre à ce type de demande.

---

## Supprimer une passation

À droite de chaque ligne du tableau, le bouton **supprimer** détruit
définitivement la passation : les réponses, le résultat, les signalements, le
rapport PDF et le guide d'entretien. Une confirmation est demandée.

**Il n'y a pas de corbeille et pas de retour en arrière.** Utilisez ce bouton
pour une demande d'effacement d'un candidat, ou pour retirer un essai. Dans le
doute, ne supprimez pas : les données partent d'elles-mêmes au bout de six mois.

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

**L'application ne répond plus.** C'est le seul cas qui demande une intervention
technique : signalez-le, la console de l'hébergeur dira ce qui se passe. Précisez
si c'est une page blanche, un message d'erreur, ou une attente sans fin.

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

Attention à la lecture : quitter la page ne prouve rien, et c'est encore plus vrai
sur téléphone, où verrouiller l'écran ou recevoir une notification suffit à
déclencher le compteur. Les absences de moins de deux secondes ne sont pas
comptées, et il en faut au moins huit pour que l'application parle d'« attention ».
Entre trois et sept, elle se contente de vous en informer. Dans tous les cas,
c'est une question à poser en entretien, jamais une conclusion.

**Ce qui fonctionne vraiment.** Reprendre en entretien trois questions du test et
demander au candidat d'expliquer son raisonnement. Celui qui a répondu seul le fait
sans effort. C'est la seule vérification réellement fiable, et elle prend cinq
minutes.

Un test non surveillé filtre, il ne prouve pas. C'est vrai de tous les tests à
distance, y compris ceux des éditeurs spécialisés.

---

## Votre prise en main, en dix minutes

À faire une fois, avec quelqu'un à côté de vous. Le mieux est de passer vous-même
un test en entier : vous verrez exactement ce que voit un candidat.

1. Ouvrez l'application, identifiez-vous, mettez l'adresse en favori.
2. Créez une invitation à votre nom, sur un test court.
3. Ouvrez le lien dans une autre fenêtre et passez le test jusqu'au bout.
4. Revenez au tableau, ouvrez le **détail** de votre résultat.
5. Téléchargez le **PDF** : c'est ce que recevra le client.
6. Ouvrez **données personnelles** et lisez les quatre compteurs.
7. Supprimez votre passation d'essai avec le bouton **supprimer**.

Si ces sept gestes vous sont familiers, vous savez tout faire.

---

## Questions à poser avant de commencer

- Quatre jours de validité pour les liens, est-ce le bon délai ?
- Six mois de conservation des données nominatives, faut-il raccourcir ?
- Voulez-vous la fonction de guide d'entretien automatique, ou préférez-vous
  qu'elle reste désactivée ?
- Le registre des traitements attend votre raison sociale et une adresse de
  contact pour les candidats.
