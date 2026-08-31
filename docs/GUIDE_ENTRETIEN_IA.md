# Le guide d'entretien généré automatiquement

Fonction facultative, désactivée par défaut. Elle transforme un profil de
positionnement en questions à poser en entretien.

C'est le seul endroit du projet où une donnée sort de l'Union européenne, et
le seul où un modèle de langage intervient. Les deux méritaient d'être
encadrés.

---

## 1. Ce que la fonction fait, et ne fait pas

Le modèle **ne produit aucune évaluation du candidat**. Il ne dit pas si le
profil convient, ne recommande rien, ne compare personne, ne note pas. Il
reformule un profil déjà calculé par le code en guide de préparation
d'entretien. La décision reste entièrement au recruteur.

Ce cadrage n'est pas cosmétique.

Une évaluation automatisée de personne en recrutement relève de l'article 22
du RGPD, sur les décisions individuelles automatisées, et du règlement européen
sur l'intelligence artificielle, qui classe explicitement l'usage en
recrutement parmi les usages à haut risque. Les obligations qui en découlent —
analyse d'impact, documentation, supervision humaine formalisée — sont hors de
portée d'un cabinet de trois personnes.

Un outil qui se contente de proposer des questions ne tombe pas dans ce champ.
Encore faut-il s'y tenir, et pouvoir le montrer. D'où ce qui suit.

---

## 2. Les cinq garde-fous

**Aucune donnée nominative n'est transmise.** Seuls le profil chiffré, les
choix faits en situation, le poste visé et le niveau partent chez le
fournisseur. Ni nom, ni adresse, ni identifiant de passation.

**La consigne est contraignante.** Le modèle reçoit l'interdiction explicite de
porter un jugement, de noter, de classer ou de recommander.

**La sortie est contrôlée.** Avant enregistrement, le texte produit est vérifié
contre une liste de formulations interdites : recommandation d'embauche, profil
à écarter, note globale, comparaison entre candidats. En cas de détection, la
génération est rejetée et **rien n'est enregistré**. Le recruteur voit un
message, pas un guide douteux.

C'est le garde-fou le plus important, parce qu'il ne fait pas confiance à la
consigne. Une instruction bien écrite réduit le risque ; elle ne le supprime
pas.

**Le déclenchement est manuel.** Le guide n'est jamais produit automatiquement :
le recruteur clique, ou rien ne se passe.

**Tout est tracé.** Le modèle utilisé, l'auteur de la demande et la date sont
conservés dans `guide_entretien`, et l'événement est journalisé. Le guide
disparaît en même temps que l'identité du candidat, à 180 jours.

---

## 3. Configuration

Dans le fichier `.env` :

```
IA_FOURNISSEUR=anthropic     # ou openai
IA_CLE_API=votre_cle
IA_MODELE=claude-haiku-4-5-20251001
IA_DELAI=60
```

Sans clé, la fonction reste **invisible** dans l'interface et l'application
fonctionne normalement. Ce n'est pas un mode dégradé avec des boutons morts :
l'option n'apparaît pas.

---

## 4. Le coût

Chaque génération envoie environ 1 500 tokens et en reçoit 900, soit moins
d'un centime avec un modèle Haiku, environ un centime avec un modèle Sonnet.

Seuls les questionnaires de positionnement déclenchent une génération : les
tests techniques sont corrigés par le code, sans aucun appel à un modèle. Un
cabinet qui fait passer six entretiens par mois consomme donc de l'ordre de
dix centimes mensuels.

Les crédits prépayés expirent un an après l'achat. Le minimum de 5 dollars
couvre largement plusieurs années à ce rythme : **n'achetez pas davantage.**

Vérifiez la tarification en vigueur, elle évolue.

---

## 5. Vérifier

```bash
python test_ia.py
```

Le script contrôle trois choses : que sept formulations inacceptables sont
bien rejetées par le filtre de sortie, que la charge utile envoyée ne contient
aucune identité, et que l'absence de clé dégrade proprement sans faire tomber
l'application.
