"""
Guide d'entretien genere automatiquement a partir d'un profil de positionnement.

Principe : le modele ne juge pas le candidat. Il transforme un profil deja
calcule en questions a poser. Il ne produit ni verdict, ni recommandation
d'embauche, ni classement.

Deux garde-fous techniques :
  - aucune donnee nominative n'est transmise au fournisseur ;
  - la consigne interdit explicitement toute appreciation sur la personne,
    et la sortie est controlee avant affichage.

Fournisseurs pris en charge : anthropic, openai.
Sans cle d'API configuree, la fonction renvoie None et l'application
continue de fonctionner normalement.
"""
import json
import os
import re
import urllib.error
import urllib.request

FOURNISSEUR = os.environ.get("IA_FOURNISSEUR", "anthropic").lower()
CLE = os.environ.get("IA_CLE_API")
# Haiku suffit largement pour reformuler un profil en questions d'entretien,
# et coute environ deux fois moins cher que Sonnet.
MODELE = os.environ.get("IA_MODELE") or (
    "claude-haiku-4-5-20251001" if FOURNISSEUR == "anthropic" else "gpt-4o-mini"
)
DELAI = int(os.environ.get("IA_DELAI", "45"))

CONSIGNE = """Tu aides un cabinet de recrutement a preparer un entretien.

On te transmet le resultat d'un questionnaire de positionnement professionnel,
sous forme anonyme. Ce questionnaire n'est PAS un test psychometrique valide.
Il decrit seulement ce que la personne a declare privilegier dans son travail.

Ta tache : produire un guide d'entretien.

REGLES ABSOLUES
- Tu ne portes aucun jugement sur la personne. Jamais.
- Tu n'ecris jamais qu'un candidat est bon, mauvais, adapte, inadapte, a risque,
  recommande ou a ecarter.
- Tu ne produis ni note, ni score, ni classement, ni comparaison.
- Tu n'inventes aucune information absente des donnees fournies.
- Tu ne deduis rien sur la sante, l'age, l'origine, la situation familiale,
  les opinions ou quoi que ce soit de personnel.
- Tu rappelles que seul le recruteur decide.

Le profil est RELATIF : les totaux s'additionnent toujours a 21. Une dimension
basse signifie que la personne a privilegie autre chose lorsqu'il fallait
choisir, pas qu'elle en est depourvue. Formule toujours en ce sens.

FORMAT ATTENDU, en francais, sans titre general :

## Ce que le profil met en avant
Deux a quatre phrases, descriptives, au conditionnel ou avec des formules du
type "declare privilegier". Aucune appreciation.

## Questions a poser
Cinq a sept questions ouvertes, numerotees, demandant des exemples vecus.
Chaque question doit se rattacher a une dimension ou a une situation precise.

## Points a verifier
Trois points concrets a confirmer pendant l'entretien, formules comme des
verifications et non comme des soupcons.

## Rappel
Une phrase indiquant que ce guide prepare l'entretien et ne remplace ni
l'entretien lui-meme, ni le test technique, ni la prise de references.

N'ajoute rien d'autre. Pas d'introduction, pas de conclusion."""

# Formulations interdites en sortie : si l'une apparait, la generation est rejetee.
INTERDITS = [
    r"\bne (?:pas )?recommand", r"\brecommande de (?:ne pas )?(?:recruter|embaucher)",
    r"\ba ecarter\b", r"\bprofil a risque\b", r"\bcandidat ideal\b",
    r"\bnote globale\b", r"\bmieux que\b", r"\bclasse[rz]? les candidats\b",
    r"\bne convient pas\b", r"\binadapte au poste\b",
]


def _charge_utile(detail, contexte):
    """Construit le texte envoye au modele. Aucune donnee nominative."""
    profil = "\n".join(
        f"- {p['nom']} : {p['total']} sur 6 ({p['lecture']})"
        for p in detail.get("profil", [])
    )
    situations = []
    for s in detail.get("situations", []):
        situations.append(
            f"Situation {s['numero']} : {s['enonce']}\n"
            f"  Reponse choisie : {s['texte'] or 'sans reponse'}\n"
            f"  Lecture prevue par la grille : {s['lecture'] or '-'}"
            + ("\n  (option signalee comme point de vigilance)" if s.get("vigilance") else "")
        )
    return (
        f"Poste vise : {contexte.get('poste') or 'non precise'}\n"
        f"Niveau du questionnaire : {contexte.get('niveau') or 'non precise'}\n"
        f"Domaine : {contexte.get('domaine') or 'non precise'}\n\n"
        f"PROFIL (total toujours egal a 21)\n{profil}\n\n"
        f"MISES EN SITUATION\n" + "\n\n".join(situations)
    )


def _appel_anthropic(texte):
    corps = json.dumps({
        "model": MODELE,
        "max_tokens": 1400,
        "system": CONSIGNE,
        "messages": [{"role": "user", "content": texte}],
    }).encode("utf-8")
    requete = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=corps,
        headers={
            "content-type": "application/json",
            "x-api-key": CLE,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
        donnees = json.loads(reponse.read())
    return "".join(b.get("text", "") for b in donnees.get("content", []))


def _appel_openai(texte):
    corps = json.dumps({
        "model": MODELE,
        "max_tokens": 1400,
        "messages": [
            {"role": "system", "content": CONSIGNE},
            {"role": "user", "content": texte},
        ],
    }).encode("utf-8")
    requete = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=corps,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {CLE}",
        },
    )
    with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
        donnees = json.loads(reponse.read())
    return donnees["choices"][0]["message"]["content"]


def controler(texte):
    """Rejette une sortie qui contiendrait une appreciation ou une recommandation."""
    minuscule = texte.lower()
    for motif in INTERDITS:
        if re.search(motif, minuscule):
            return False, motif
    return True, None


def disponible():
    return bool(CLE)


def generer(detail, contexte):
    """
    Renvoie (texte, erreur). L'un des deux est None.
    Ne leve jamais d'exception : l'application doit fonctionner sans l'IA.
    """
    if not CLE:
        return None, "Aucune cle d'API configuree (variable IA_CLE_API)."
    if detail.get("type") != "positionnement":
        return None, "Le guide d'entretien ne concerne que les questionnaires de positionnement."

    texte_envoye = _charge_utile(detail, contexte)
    try:
        if FOURNISSEUR == "anthropic":
            sortie = _appel_anthropic(texte_envoye)
        elif FOURNISSEUR == "openai":
            sortie = _appel_openai(texte_envoye)
        else:
            return None, f"Fournisseur inconnu : {FOURNISSEUR}"
    except urllib.error.HTTPError as e:
        return None, f"Le service a repondu {e.code}. Verifiez la cle d'API et le modele."
    except Exception as e:
        return None, f"Appel impossible : {e}"

    sortie = (sortie or "").strip()
    if len(sortie) < 80:
        return None, "Reponse trop courte, generation abandonnee."

    ok, motif = controler(sortie)
    if not ok:
        return None, ("La reponse contenait une appreciation sur le candidat, "
                      "elle a ete rejetee. Relancez la generation.")
    return sortie, None
