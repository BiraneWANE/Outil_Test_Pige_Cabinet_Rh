# Registre des traitements

Plateforme de tests candidats.
Document à compléter par le cabinet avec sa raison sociale et son contact, puis
à conserver avec les autres pièces RGPD. Il correspond à l'article 30 du
règlement, dans sa forme allégée applicable aux structures de moins de
250 salariés.

Dernière mise à jour : août 2026.

---

## 1. Responsable du traitement

| | |
|---|---|
| Organisme | *à compléter : raison sociale du cabinet* |
| Adresse | *à compléter* |
| Contact pour les demandes des candidats | *à compléter : adresse électronique* |
| Personne chargée du suivi | La consultante en recrutement |

## 2. Finalité

Évaluer les compétences techniques (comptabilité, paie) et le positionnement
professionnel des candidats présentés aux cabinets clients, afin de préparer
l'entretien de recrutement.

Le test ne produit **aucune décision automatisée**. Il ne classe pas les
candidats entre eux et ne peut pas, à lui seul, écarter une candidature. Le
recruteur décide, le test documente l'entretien.

## 3. Personnes concernées

Candidats à un poste en cabinet d'expertise comptable ou en commissariat aux
comptes, à qui un lien de test est envoyé par le cabinet.

Volume attendu : environ douze passations par mois.

## 4. Données traitées

| Catégorie | Détail | Origine |
|---|---|---|
| Identification | Nom et prénom, adresse électronique, poste visé | Saisis par le recruteur, confirmés par le candidat au démarrage |
| Réponses | Options cochées à chaque question | Le candidat |
| Mesures de passation | Date, durée totale, temps passé par question, nombre d'affichages, sorties de page, tentatives de copie | Générées par l'application |
| Résultats | Score, pourcentage, profil par dimension, signalements automatiques | Calculés |
| Traçabilité | Horodatage de l'information RGPD, ouverture du lien, démarrage, soumission, purge | Générés par l'application |

Aucune donnée sensible au sens de l'article 9 n'est collectée : ni santé, ni
origine, ni opinions, ni situation familiale. Le questionnaire de
positionnement porte uniquement sur des comportements professionnels et n'est
pas un test psychométrique validé.

## 5. Destinataires

- La consultante en recrutement, seule titulaire de l'accès au back-office.
- Le cabinet client, qui reçoit le rapport PDF de la passation.

Aucune autre transmission, aucune revente, aucun profilage publicitaire.

## 6. Sous-traitants et hébergement

| Prestataire | Rôle | Localisation |
|---|---|---|
| Neon | Base de données PostgreSQL | Francfort, Union européenne |
| Render | Hébergement de l'application | Francfort, Union européenne |
| Anthropic | Génération facultative du guide d'entretien | États-Unis |

La fonction de guide d'entretien est facultative et désactivable. Quand elle
est utilisée, seuls le profil chiffré et les réponses aux mises en situation
sont transmis : **aucun nom, aucune adresse électronique, aucun poste**. Si le
cabinet préfère ne rien transmettre hors de l'Union européenne, il suffit de
laisser la clé d'API vide, et la fonction disparaît de l'interface.

## 7. Durées de conservation

| Donnée | Durée |
|---|---|
| Lien d'invitation | 7 jours, puis expiration automatique |
| Nom, adresse électronique, poste visé | 180 jours après la création de l'invitation |
| Guide d'entretien | Supprimé en même temps que les données nominatives |
| Réponses, temps, score, signalements | Conservés au-delà, sous forme anonyme |
| Copies de sauvegarde automatiques | 30 jours glissants, puis suppression |

Passé le délai de 180 jours, la passation est **anonymisée** : les champs
nominatifs sont vidés, le lien d'accès est neutralisé et le guide d'entretien
supprimé. Ce qui subsiste ne permet plus d'identifier le candidat et sert
uniquement à mesurer la qualité des questions.

La purge s'exécute automatiquement au démarrage du serveur puis, au plus une
fois par jour, à l'ouverture du back-office. Elle peut aussi être déclenchée à
la demande depuis la page « Données personnelles ». Chaque purge est inscrite
au journal.

## 8. Information et droits des candidats

L'information est affichée avant le démarrage du test, et son acceptation est
horodatée en base. Elle indique la finalité, la durée de conservation, le fait
que le temps par question et les sorties de page sont mesurés, et l'absence de
décision automatisée.

| Droit | Mise en œuvre |
|---|---|
| Accès | Le rapport PDF de la passation constitue la copie des données traitées |
| Rectification | Correction manuelle en base par la consultante |
| Effacement | Bouton « supprimer » du back-office, suppression définitive et immédiate |
| Opposition | Le candidat peut refuser de passer le test, sans avoir à se justifier |

Délai de réponse visé : un mois à compter de la demande.

## 9. Mesures de sécurité

- Accès au back-office protégé par mot de passe, transmis en HTTPS.
- Lien candidat composé d'un jeton aléatoire de 22 caractères, à usage unique
  et à durée limitée.
- Chronomètre calculé côté serveur : le candidat ne peut pas prolonger son
  temps depuis son navigateur.
- Base de données isolée, accessible uniquement par l'application.
- Mots de passe et clés hors du code source, dans les variables
  d'environnement de l'hébergeur.
- Copie des énoncés désactivée, et tentatives enregistrées.
- Sauvegarde quotidienne automatique de la base, conservée 30 jours, et
  téléchargement d'une copie complète depuis le back-office.

### Effet de la sauvegarde sur la purge

Une copie prise avant une purge contient encore les données nominatives que
la purge a effacées depuis. Trois dispositions encadrent ce décalage :

- la copie du jour est faite **après** la purge, jamais avant ;
- les copies automatiques sont détruites au bout de 30 jours, ce qui borne le
  décalage à un mois ;
- lors d'une demande d'effacement, la suppression définitive s'applique à la
  base ; les copies encore présentes s'effacent d'elles-mêmes dans le mois.

Les copies téléchargées par le cabinet sortent du périmètre de l'application.
Elles contiennent des données nominatives et relèvent de la responsabilité du
cabinet : elles doivent être conservées dans un espace protégé et détruites
quand elles ne servent plus.

---

# Second traitement : prospection commerciale

Ce traitement est distinct du précédent. Il ne concerne pas les candidats mais
les entreprises qui publient des offres d'emploi.

## Finalité

Identifier les entreprises qui recrutent sur les métiers du cabinet, afin de leur
présenter ses services. Une prospection professionnelle, adressée à des personnes
morales dans le cadre de leur activité.

## Données traitées

| Catégorie | Détail | Origine |
|---|---|---|
| Annonce | Intitulé, commune, type de contrat, date de publication, lien | API France Travail et Adzuna |
| Entreprise | Raison sociale | Idem |
| Contact | Adresse électronique publiée avec l'offre, exceptionnellement un nom | API France Travail |

## Base légale et changement de finalité

L'intérêt légitime du cabinet à faire connaître ses services (article 6.1.f).

Le point sensible est assumé : ces adresses ont été publiées par les employeurs
**pour recevoir des candidatures**. Les utiliser à des fins de prospection est un
usage second. Il est admis en démarchage professionnel, sous réserve des mesures
ci-dessous, qui sont toutes mises en œuvre.

## Mesures prises

**Adresses de fonction par défaut.** Seules les adresses génériques du type
`contact@`, `recrutement@` ou `rh@` sont retenues dans le fichier d'envoi. Elles
désignent une fonction et non une personne. Les adresses nominatives sont
identifiées, comptées à part et exclues des envois sauf décision expresse.

**Information dès le premier message.** Chaque courriel indique la provenance de
l'adresse, la finalité et la fréquence, ainsi que le droit d'opposition. C'est
l'obligation d'information de l'article 14, et c'est ce qui distingue une
prospection régulière d'une collecte détournée.

**Opposition effective et définitive.** Chaque destinataire dispose d'un lien de
désinscription personnel, accessible sans authentification. L'opposition est
enregistrée pour toujours : l'adresse est écartée de tous les envois suivants,
même si l'entreprise republie une offre. Les oppositions reçues par téléphone ou
par réponse au courriel sont saisies à la main dans le même registre.

**Fréquence limitée.** Un envoi par an et par adresse.

**Aucun démarchage des intermédiaires.** Les cabinets de recrutement et agences
d'intérim sont écartés de la collecte : leurs adresses ne sont pas enregistrées.

## Durée de conservation

Trois ans à compter du dernier contact, conformément à la recommandation de la
CNIL en matière de prospection. Les adresses désinscrites sont conservées
au-delà, sous la seule forme nécessaire pour ne plus jamais les solliciter.

## Point à revoir

Si le volume de prospection augmente ou si la fréquence dépasse un envoi par an,
ce traitement devra être réexaminé.

---

## 10. Points à revoir

- Ouvrir un accès distinct par consultante le jour où elles seront plusieurs,
  plutôt qu'un mot de passe partagé.
- Réexaminer la durée de 180 jours avec le cabinet : elle peut être raccourcie
  sans rien changer au code, par la variable `JOURS_CONSERVATION`.
- Formaliser la relation de sous-traitance avec les cabinets clients si le
  cabinet agit pour leur compte.
- Vérifier une fois par an qu'une sauvegarde téléchargée se restaure
  réellement, sur une base d'essai. Une sauvegarde jamais restaurée n'est pas
  une sauvegarde.
