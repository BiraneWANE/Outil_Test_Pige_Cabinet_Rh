"""Correction des tests techniques et calcul des profils de positionnement."""

SEUILS_TECHNIQUE = [
    (0.85, "Très bon niveau technique, autonomie rapide sur un portefeuille"),
    (0.70, "Bon niveau, base solide à consolider sur quelques points"),
    (0.50, "Niveau moyen, accompagnement technique nécessaire"),
    (0.00, "Bases insuffisantes pour une prise de poste sans formation interne"),
]


def _lecture_technique(pourcentage):
    for seuil, texte in SEUILS_TECHNIQUE:
        if pourcentage >= seuil * 100:
            return texte
    return SEUILS_TECHNIQUE[-1][1]


def corriger_technique(questions, reponses, duree_secondes):
    """
    Une question est validee si et seulement si toutes les bonnes reponses
    sont cochees et qu'aucune reponse erronee ne l'est. Aucun point negatif.
    """
    cochees = {}
    for r in reponses:
        cochees.setdefault(r["question_id"], set()).add(r["option_id"])

    score = 0
    detail = []
    for q in questions:
        attendues = {o["id"] for o in q["options"] if o["est_correcte"]}
        donnees = cochees.get(q["id"], set())
        juste = donnees == attendues and len(donnees) > 0
        if juste:
            score += 1

        lettres = {o["id"]: o["lettre"] for o in q["options"]}
        detail.append({
            "numero": q["numero"],
            "enonce": q["enonce"],
            "format": q["format"],
            "attendu": sorted(lettres[i] for i in attendues),
            "donne": sorted(lettres[i] for i in donnees),
            "juste": juste,
            "justification": q["justification"],
        })

    total = len(questions)
    pourcentage = round(100 * score / total, 2) if total else 0
    synthese = synthese_technique(questions, detail, score, total) or {}
    return {
        "score": score,
        "total_points": total,
        "pourcentage": pourcentage,
        "duree_secondes": duree_secondes,
        "nb_vigilances": None,
        "detail": {
            "type": "technique",
            "lecture": _lecture_technique(pourcentage),
            "synthese": synthese.get("texte"),
            "themes": synthese.get("themes"),
            "questions": detail,
        },
    }


# ------------------------------------------------------------------
# Synthese par theme (tests techniques)
# ------------------------------------------------------------------

def _accorde(nb, singulier, pluriel):
    return singulier if nb <= 1 else pluriel


def synthese_technique(questions, detail_questions, score, total):
    """
    Regroupe les questions par theme et redige une synthese factuelle.

    Aucune appreciation sur la personne : on decrit uniquement ce que le
    test mesure, c'est-a-dire des connaissances a un instant donne.
    """
    juste_par_num = {q["numero"]: q["juste"] for q in detail_questions}

    themes = {}
    for q in questions:
        nom = q.get("theme")
        if not nom:
            continue
        t = themes.setdefault(nom, {"theme": nom, "total": 0, "reussies": 0,
                                    "ratees": []})
        t["total"] += 1
        if juste_par_num.get(q["numero"]):
            t["reussies"] += 1
        else:
            t["ratees"].append(q["numero"])

    lignes = []
    for t in themes.values():
        part = t["reussies"] / t["total"]
        if part == 1:
            niveau = "acquis"
        elif part >= 0.5:
            niveau = "partiel"
        else:
            niveau = "a consolider"
        lignes.append({**t, "part": round(100 * part), "niveau": niveau})

    if not lignes:
        # aucun theme rattache : on ne produit pas de synthese plutot que
        # d'en produire une vide
        return None

    lignes.sort(key=lambda x: (-x["part"], x["theme"]))

    acquis = [l["theme"] for l in lignes if l["niveau"] == "acquis"]
    partiels = [l["theme"] for l in lignes if l["niveau"] == "partiel"]
    fragiles = [l["theme"] for l in lignes if l["niveau"] == "a consolider"]

    phrases = []
    pourcentage = round(100 * score / total) if total else 0
    phrases.append(
        f"Le candidat valide {score} question{_accorde(score, '', 's')} sur {total}, "
        f"soit {pourcentage} %, sur {len(lignes)} thème{_accorde(len(lignes), '', 's')} "
        f"couverts par ce test."
    )

    if acquis:
        phrases.append(
            f"Les réponses sont entièrement justes sur : {', '.join(acquis)}."
        )
    if partiels:
        phrases.append(
            f"La maîtrise est partielle sur : {', '.join(partiels)}. "
            f"Ces points méritent d'être repris en entretien."
        )
    if fragiles:
        phrases.append(
            f"Les questions ont majoritairement été manquées sur : "
            f"{', '.join(fragiles)}."
        )
    if not acquis and not partiels:
        phrases.append(
            "Aucun thème n'est maîtrisé de façon complète sur ce test."
        )
    elif not fragiles and not partiels:
        phrases.append("Aucun thème ne ressort en difficulté.")

    phrases.append(
        "Ce test mesure des connaissances techniques à un instant donné. "
        "Il ne préjuge ni de la capacité d'apprentissage, ni de la tenue "
        "du poste, qui s'apprécient en entretien."
    )

    return {"texte": " ".join(phrases), "themes": lignes}


def _lecture_dimension(total):
    if total >= 5:
        return "dominante"
    if total >= 3:
        return "presente"
    return "en retrait"


def calculer_positionnement(questions, reponses, dimensions, duree_secondes):
    """
    Partie 1 : chaque choix compte pour une dimension. Total de 0 a 6.
               Profil relatif : la somme des dimensions vaut toujours 21.
    Partie 2 : aucun score. On releve les choix et les points de vigilance.
    """
    cochees = set(r["option_id"] for r in reponses)

    totaux = {code: 0 for code in dimensions}
    choix_partie2 = []
    vigilances = 0
    non_repondues = 0

    for q in questions:
        selection = [o for o in q["options"] if o["id"] in cochees]

        if q["partie"] == 1:
            if not selection:
                non_repondues += 1
                continue
            dim = selection[0]["dimension"]
            if dim in totaux:
                totaux[dim] += 1
        else:
            if not selection:
                non_repondues += 1
                choix_partie2.append({
                    "numero": q["numero"], "enonce": q["enonce"],
                    "lettre": None, "texte": None,
                    "vigilance": False, "lecture": "Sans reponse",
                })
                continue
            opt = selection[0]
            if opt["est_vigilance"]:
                vigilances += 1
            choix_partie2.append({
                "numero": q["numero"],
                "enonce": q["enonce"],
                "lettre": opt["lettre"],
                "texte": opt["texte"],
                "vigilance": opt["est_vigilance"],
                "lecture": opt["lecture"],
            })

    profil = [
        {
            "code": code,
            "nom": libelle,
            "total": totaux[code],
            "lecture": _lecture_dimension(totaux[code]),
        }
        for code, libelle in dimensions.items()
    ]
    profil.sort(key=lambda d: -d["total"])

    return {
        "score": None,
        "total_points": None,
        "pourcentage": None,
        "duree_secondes": duree_secondes,
        "nb_vigilances": vigilances,
        "detail": {
            "type": "positionnement",
            "avertissement": (
                "Ce questionnaire n'est pas un test psychométrique validé. "
                "Il prépare l'entretien et ne doit jamais servir seul à écarter "
                "une candidature. Le profil est relatif : les totaux s'additionnent "
                "toujours à 21, ne comparez pas deux candidats entre eux."
            ),
            "profil": profil,
            "situations": choix_partie2,
            "non_repondues": non_repondues,
        },
    }


DIMENSIONS_PAR_DEFAUT = {
    "R": "Rigueur et fiabilité",
    "O": "Organisation et priorités",
    "A": "Autonomie et initiative",
    "C": "Relation et communication",
    "S": "Gestion de la charge et du stress",
    "E": "Éthique et confidentialité",
    "N": "Ouverture et apprentissage",
}


def dimensions_du_test(questions):
    """Reconstruit le libelle des dimensions a partir des options de la partie 1."""
    dims = {}
    for q in questions:
        if q["partie"] != 1:
            continue
        for o in q["options"]:
            if o["dimension"] and o["dimension"] not in dims:
                dims[o["dimension"]] = o["lecture"] or DIMENSIONS_PAR_DEFAUT.get(
                    o["dimension"], o["dimension"]
                )
    return dims or DIMENSIONS_PAR_DEFAUT
