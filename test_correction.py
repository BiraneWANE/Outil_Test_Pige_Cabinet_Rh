"""Tests du module de correction, sans base de donnees."""
import json
import correction

banque = json.load(open("banque_questions.json", encoding="utf-8"))
par_code = {t["code"]: t for t in banque["tests"]}


def en_lignes(test):
    """Transforme la banque JSON en structures identiques a celles de la base."""
    qs, oid = [], 0
    for q in test["questions"]:
        opts = []
        for o in q["options"]:
            oid += 1
            opts.append({"id": oid, "lettre": o["lettre"], "texte": o["texte"],
                         "est_correcte": o["est_correcte"], "dimension": o["dimension"],
                         "est_vigilance": o["est_vigilance"], "lecture": o["lecture"]})
        qs.append({"id": q["numero"], "numero": q["numero"], "partie": q["partie"],
                   "format": q["format"], "enonce": q["enonce"],
                   "justification": q["justification"], "options": opts})
    return qs


# --- 1. Technique : un sans-faute doit donner le maximum -------------
t = par_code["QCM_COMPTA_JUNIOR"]
qs = en_lignes(t)
parfait = [{"question_id": q["id"], "option_id": o["id"]}
           for q in qs for o in q["options"] if o["est_correcte"]]
r = correction.corriger_technique(qs, parfait, 600)
assert r["score"] == len(qs), r["score"]
assert r["pourcentage"] == 100.0
print(f"sans-faute            : {r['score']}/{r['total_points']} -> {r['detail']['lecture']}")

# --- 2. Technique : reponse partielle = 0 sur la question ------------
qm = next(q for q in qs if q["format"] == "multiple")
partiel = [{"question_id": qm["id"],
            "option_id": next(o["id"] for o in qm["options"] if o["est_correcte"])}]
r2 = correction.corriger_technique(qs, partiel, 600)
assert r2["score"] == 0, "une reponse partielle ne doit rien rapporter"
print("reponse partielle     : 0 point, regle du tout ou rien respectee")

# --- 3. Technique : bonne reponse + une erreur = 0 -------------------
qu = next(q for q in qs if q["format"] == "unique")
mixte = [{"question_id": qu["id"], "option_id": o["id"]} for o in qu["options"]]
r3 = correction.corriger_technique(qs, mixte, 600)
assert r3["score"] == 0
print("tout coche            : 0 point")

# --- 4. Positionnement : la somme du profil vaut toujours 21 ---------
for code in ["POS_COMPTA_JUNIOR", "POS_COMPTA_CONFIRME",
             "POS_PAIE_JUNIOR", "POS_PAIE_CONFIRME"]:
    p = en_lignes(par_code[code])
    dims = correction.dimensions_du_test(p)
    assert len(dims) == 7, f"{code} : {len(dims)} dimensions"
    # le candidat coche systematiquement la proposition A
    rep = [{"question_id": q["id"], "option_id": q["options"][0]["id"]} for q in p]
    res = correction.calculer_positionnement(p, rep, dims, 900)
    somme = sum(d["total"] for d in res["detail"]["profil"])
    assert somme == 21, f"{code} : somme {somme}"
    # chaque dimension doit apparaitre exactement 6 fois sur l'ensemble des paires
    compte = {}
    for q in p:
        if q["partie"] == 1:
            for o in q["options"]:
                compte[o["dimension"]] = compte.get(o["dimension"], 0) + 1
    assert set(compte.values()) == {6}, f"{code} : {compte}"
    print(f"{code:<22}: 21 choix, 7 dimensions equilibrees, "
          f"{res['nb_vigilances']} vigilance(s)")

# --- 5. Positionnement : les vigilances sont bien comptees -----------
p = en_lignes(par_code["POS_PAIE_CONFIRME"])
dims = correction.dimensions_du_test(p)
pire = []
for q in p:
    cible = q["options"][0]
    if q["partie"] == 2:
        cible = next((o for o in q["options"] if o["est_vigilance"]), cible)
    pire.append({"question_id": q["id"], "option_id": cible["id"]})
res = correction.calculer_positionnement(p, pire, dims, 900)
assert res["nb_vigilances"] == 6, res["nb_vigilances"]
print(f"profil le plus risque : {res['nb_vigilances']} vigilances sur 6 situations")

print("\nTous les tests passent.")
