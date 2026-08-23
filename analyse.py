"""
Couche analytique.

Trois usages :
  1. Analyse d'items  : la qualite de chaque question, mesuree sur les
                        passations reelles.
  2. Statistiques     : distribution des scores, durees, taux d'abandon.
  3. Anomalies        : signalements sur une passation individuelle.

Aucune de ces mesures n'est fiable sur un faible effectif. Chaque fonction
renvoie le nombre de passations utilisees : affichez-le toujours, et
mefiez-vous en dessous de trente.
"""
import statistics
from collections import Counter, defaultdict

EFFECTIF_MINIMUM = 30          # en deca, les indicateurs sont indicatifs
P_TROP_FACILE = 0.95           # reussie par presque tout le monde
P_TROP_DIFFICILE = 0.20        # ratee par presque tout le monde
R_FAIBLE = 0.10                # ne separe pas les bons des moins bons
TEMPS_SUSPECT = 3              # secondes : reponse sans lecture


# ==================================================================
# 1. Analyse d'items (tests techniques)
# ==================================================================

def _correlation_item_total(reussites_item, scores_totaux):
    """
    Correlation entre le fait de reussir cette question et le score global.
    Une valeur elevee signifie que la question separe bien les candidats
    solides des autres. Une valeur nulle ou negative signale une question
    ambigue, mal formulee, ou dont le corrige est faux.
    """
    n = len(reussites_item)
    if n < 3:
        return None
    try:
        moy_item = statistics.fmean(reussites_item)
        moy_total = statistics.fmean(scores_totaux)
        et_item = statistics.pstdev(reussites_item)
        et_total = statistics.pstdev(scores_totaux)
        if et_item == 0 or et_total == 0:
            return 0.0
        cov = sum((a - moy_item) * (b - moy_total)
                  for a, b in zip(reussites_item, scores_totaux)) / n
        return round(cov / (et_item * et_total), 3)
    except statistics.StatisticsError:
        return None


def analyser_items(lignes):
    """
    lignes : dictionnaires issus de v_reponses_analyse, pour UN test technique.
             Champs utilises : invitation_id, numero, juste, temps_question.
    """
    par_candidat = defaultdict(dict)
    temps = defaultdict(list)
    for l in lignes:
        if l["juste"] is None:
            continue
        par_candidat[l["invitation_id"]][l["numero"]] = 1 if l["juste"] else 0
        if l["temps_question"]:
            temps[l["numero"]].append(l["temps_question"])

    candidats = list(par_candidat)
    n = len(candidats)
    if n == 0:
        return {"effectif": 0, "fiable": False, "items": []}

    numeros = sorted({num for d in par_candidat.values() for num in d})
    scores = {c: sum(par_candidat[c].values()) for c in candidats}

    items = []
    for num in numeros:
        reussites = [par_candidat[c].get(num, 0) for c in candidats]
        totaux = [scores[c] for c in candidats]
        p = statistics.fmean(reussites)
        r = _correlation_item_total(reussites, totaux)
        t = temps.get(num, [])

        alertes = []
        if p >= P_TROP_FACILE:
            alertes.append("Trop facile : presque tous les candidats la reussissent")
        if p <= P_TROP_DIFFICILE:
            alertes.append("Trop difficile ou corrige a verifier")
        if r is not None and r < R_FAIBLE:
            alertes.append("Ne discrimine pas : enonce probablement ambigu")
        if t and statistics.median(t) <= TEMPS_SUSPECT:
            alertes.append("Temps de reponse tres court : question survolee")

        items.append({
            "numero": num,
            "taux_reussite": round(100 * p, 1),
            "correlation": r,
            "temps_median": round(statistics.median(t)) if t else None,
            "alertes": alertes,
        })

    return {
        "effectif": n,
        "fiable": n >= EFFECTIF_MINIMUM,
        "items": items,
        "a_revoir": [i["numero"] for i in items if i["alertes"]],
    }


# ==================================================================
# 2. Statistiques d'un test
# ==================================================================

def statistiques_test(resultats, invitations):
    """
    resultats   : lignes de la table resultat pour ce test
    invitations : toutes les invitations de ce test, quel que soit le statut
    """
    scores = [r["pourcentage"] for r in resultats if r["pourcentage"] is not None]
    durees = [r["duree_secondes"] for r in resultats if r["duree_secondes"]]

    envoyees = len(invitations)
    terminees = sum(1 for i in invitations if i["statut"] == "terminee")
    jamais = sum(1 for i in invitations if i["statut"] == "envoyee")
    abandons = sum(1 for i in invitations if i["statut"] in ("en_cours", "expiree"))

    stats = {
        "envoyees": envoyees,
        "terminees": terminees,
        "jamais_ouvertes": jamais,
        "abandons": abandons,
        "taux_completion": round(100 * terminees / envoyees, 1) if envoyees else None,
    }
    if scores:
        scores_tries = sorted(scores)
        stats.update({
            "score_moyen": round(statistics.fmean(scores), 1),
            "score_median": round(statistics.median(scores), 1),
            "score_min": round(min(scores), 1),
            "score_max": round(max(scores), 1),
            "ecart_type": round(statistics.pstdev(scores), 1) if len(scores) > 1 else 0,
            "quartile_bas": round(scores_tries[len(scores) // 4], 1),
            "quartile_haut": round(scores_tries[3 * len(scores) // 4], 1),
        })
    if durees:
        stats["duree_mediane_min"] = round(statistics.median(durees) / 60, 1)
        stats["temps_ecoule"] = sum(1 for d in durees if d >= 20 * 60 - 5)

    return stats


def distribution_scores(resultats, pas=10):
    """Repartition des scores par tranche, pour un histogramme."""
    tranches = Counter()
    for r in resultats:
        if r["pourcentage"] is None:
            continue
        borne = min(int(float(r["pourcentage"]) // pas) * pas, 100 - pas)
        tranches[borne] += 1
    return [{"tranche": f"{b} à {b + pas} %", "effectif": tranches.get(b, 0)}
            for b in range(0, 100, pas)]


# ==================================================================
# 3. Analyse des questionnaires de positionnement
# ==================================================================

def profils_agreges(resultats):
    """
    Moyenne de chaque dimension sur l'ensemble des candidats.
    Utile pour situer un candidat par rapport aux autres, ce que le
    profil individuel ne permet pas (il est relatif au candidat).
    """
    cumul = defaultdict(list)
    for r in resultats:
        for d in r["detail"].get("profil", []):
            cumul[(d["code"], d["nom"])].append(d["total"])
    lignes = []
    for (code, nom), valeurs in cumul.items():
        lignes.append({
            "code": code, "nom": nom,
            "moyenne": round(statistics.fmean(valeurs), 2),
            "mediane": statistics.median(valeurs),
            "effectif": len(valeurs),
        })
    lignes.sort(key=lambda x: -x["moyenne"])
    return lignes


def frequence_situations(resultats):
    """
    Pour chaque situation, la repartition des options choisies.
    Une option jamais choisie est un distracteur inutile : elle occupe
    une place sans rien apporter et merite d'etre reecrite.
    """
    compte = defaultdict(Counter)
    enonces = {}
    vigilance = defaultdict(int)
    for r in resultats:
        for s in r["detail"].get("situations", []):
            num = s["numero"]
            enonces[num] = s["enonce"]
            compte[num][s["lettre"] or "sans reponse"] += 1
            if s["vigilance"]:
                vigilance[num] += 1

    lignes = []
    for num in sorted(compte):
        total = sum(compte[num].values())
        repartition = [
            {"lettre": l, "effectif": n, "part": round(100 * n / total, 1)}
            for l, n in sorted(compte[num].items())
        ]
        jamais = [r["lettre"] for r in repartition if r["effectif"] == 0]
        lignes.append({
            "numero": num,
            "enonce": enonces[num],
            "repartition": repartition,
            "part_vigilance": round(100 * vigilance[num] / total, 1) if total else 0,
            "options_mortes": jamais,
        })
    return lignes


# ==================================================================
# 4. Anomalies sur une passation individuelle
# ==================================================================

def detecter_anomalies(invitation, resultat, vues, reponses_par_lettre,
                       comportement=None):
    """
    Signalements destines au recruteur. Aucun n'est disqualifiant :
    ce sont des sujets a evoquer en entretien, pas des verdicts.
    """
    a = []
    duree = resultat.get("duree_secondes") or 0
    alloue = invitation["duree_minutes"] * 60

    if duree and duree < 0.30 * alloue:
        a.append(("passation_rapide",
                  f"Test termine en {round(duree / 60)} minutes sur "
                  f"{invitation['duree_minutes']} : reponses possiblement survolees",
                  "attention"))

    if duree and duree >= alloue - 5:
        a.append(("temps_epuise",
                  "Le temps imparti a ete entierement consomme",
                  "info"))

    rapides = [v for v in vues if v["duree_secondes"] and v["duree_secondes"] <= TEMPS_SUSPECT]
    if len(rapides) >= max(3, 0.25 * len(vues)):
        a.append(("reponses_eclair",
                  f"{len(rapides)} question(s) repondues en moins de "
                  f"{TEMPS_SUSPECT} secondes",
                  "attention"))

    if reponses_par_lettre:
        total = sum(reponses_par_lettre.values())
        lettre, n = max(reponses_par_lettre.items(), key=lambda x: x[1])
        if total and n / total >= 0.80:
            a.append(("reponse_monotone",
                      f"{round(100 * n / total)} % des reponses sur la position "
                      f"{lettre} : reponse au hasard probable",
                      "attention"))

    c = comportement or {}
    sorties = c.get("sorties_page", 0)
    if sorties >= 3:
        a.append(("sorties_repetees",
                  f"Le candidat a quitte la page {sorties} fois pendant la passation",
                  "attention"))
    elif sorties > 0:
        a.append(("sorties_page",
                  f"Le candidat a quitte la page {sorties} fois",
                  "info"))

    if c.get("copies_tentees", 0) >= 2:
        a.append(("copies_tentees",
                  f"{c['copies_tentees']} tentative(s) de copie de l'enonce",
                  "attention"))

    detail = resultat.get("detail", {})
    if detail.get("type") == "positionnement":
        profil = detail.get("profil", [])
        if profil:
            ecart = profil[0]["total"] - profil[-1]["total"]
            if ecart <= 1:
                a.append(("profil_plat",
                          "Profil sans relief : le candidat a evite de se positionner",
                          "info"))
        if detail.get("non_repondues", 0) >= 3:
            a.append(("incomplet",
                      f"{detail['non_repondues']} question(s) sans reponse",
                      "attention"))
    else:
        sans = sum(1 for q in detail.get("questions", []) if not q["donne"])
        if sans >= max(2, 0.20 * len(detail.get("questions", []))):
            a.append(("incomplet",
                      f"{sans} question(s) sans reponse", "attention"))

    return [{"code": c, "libelle": l, "gravite": g} for c, l, g in a]
