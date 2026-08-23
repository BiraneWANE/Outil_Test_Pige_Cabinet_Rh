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

## 10. Points à revoir

- Ouvrir un accès distinct par consultante le jour où elles seront plusieurs,
  plutôt qu'un mot de passe partagé.
- Réexaminer la durée de 180 jours avec le cabinet : elle peut être raccourcie
  sans rien changer au code, par la variable `JOURS_CONSERVATION`.
- Formaliser la relation de sous-traitance avec les cabinets clients si le
  cabinet agit pour leur compte.
