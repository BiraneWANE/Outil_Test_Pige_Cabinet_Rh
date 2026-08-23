"""Tests du garde-fou sur les sorties du modele, sans appel reseau."""
import ia

# --- sorties conformes : doivent passer ------------------------------
bonnes = [
    """## Ce que le profil met en avant
La personne declare privilegier la rigueur et le respect des echeances.
Elle place la relation client en retrait lorsqu'il faut arbitrer.

## Questions a poser
1. Racontez-moi une situation ou vous avez du expliquer un point technique.
2. Comment organisez-vous une semaine chargee ?

## Points a verifier
- Confirmer l'aisance en relation directe avec un client.

## Rappel
Ce guide prepare l'entretien et ne remplace ni l'entretien, ni le test technique.""",
]
for t in bonnes:
    ok, motif = ia.controler(t)
    assert ok, f"rejete a tort : {motif}"
print("sorties conformes                 : acceptees")

# --- sorties a rejeter ----------------------------------------------
mauvaises = {
    "verdict d'embauche": "Je recommande de ne pas recruter cette personne.",
    "profil a ecarter": "Profil a ecarter compte tenu du manque de rigueur observe.",
    "profil a risque": "Il s'agit d'un profil a risque pour ce poste.",
    "comparaison": "Ce candidat est mieux que la moyenne des postulants.",
    "note globale": "Note globale du candidat : 14 sur 20.",
    "candidat ideal": "C'est le candidat ideal pour ce poste.",
    "inadaptation": "Ce profil ne convient pas au poste propose.",
}
for nom, texte in mauvaises.items():
    ok, motif = ia.controler(texte)
    assert not ok, f"NON detecte : {nom}"
    print(f"{nom:<34}: rejete")

# --- la charge utile ne doit contenir aucune identite ----------------
detail = {
    "type": "positionnement",
    "profil": [{"code": "R", "nom": "Rigueur", "total": 5, "lecture": "dominante"}],
    "situations": [{"numero": 22, "enonce": "Un manager demande un salaire.",
                    "lettre": "A", "texte": "Je refuse.",
                    "vigilance": False, "lecture": "Tient la confidentialite."}],
}
charge = ia._charge_utile(detail, {"poste": "Gestionnaire de paie",
                                   "niveau": "confirme", "domaine": "paie"})
for interdit in ["Karim", "Benali", "@", "candidat_nom", "token"]:
    assert interdit not in charge, f"donnee sensible transmise : {interdit}"
assert "Rigueur" in charge and "Situation 22" in charge
print("charge utile                      : anonyme, profil et situations presents")

# --- sans cle configuree, aucune exception ---------------------------
sauvegarde = ia.CLE
ia.CLE = None
texte, erreur = ia.generer(detail, {})
assert texte is None and "cle" in erreur.lower()
ia.CLE = sauvegarde
print("absence de cle                    : degradation propre, pas d'erreur")

# --- un test technique ne declenche pas de guide ---------------------
texte, erreur = ia.generer({"type": "technique"}, {})
assert texte is None
print("test technique                    : guide refuse, comme prevu")

print("\nTous les tests passent.")
