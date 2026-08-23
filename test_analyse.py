"""Tests de la couche analytique sur des passations simulees."""
import json
import random

import analyse

random.seed(42)
banque = json.load(open("banque_questions.json", encoding="utf-8"))
par_code = {t["code"]: t for t in banque["tests"]}


def simuler_technique(test, n=60):
    """Chaque candidat a un niveau propre. Deux questions sont volontairement
    degradees pour verifier que l'analyse les repere."""
    numeros = [q["numero"] for q in test["questions"]]
    q_facile = numeros[2]      # tout le monde la reussit
    q_ambigue = numeros[5]     # reussite au hasard, sans lien avec le niveau
    lignes = []
    for c in range(n):
        niveau = random.uniform(0.25, 0.95)
        for num in numeros:
            if num == q_facile:
                juste = True
            elif num == q_ambigue:
                juste = random.random() < 0.5
            else:
                juste = random.random() < niveau
            lignes.append({
                "invitation_id": c, "numero": num, "juste": juste,
                "temps_question": random.randint(20, 90),
            })
    return lignes, q_facile, q_ambigue


t = par_code["QCM_COMPTA_JUNIOR"]
lignes, q_facile, q_ambigue = simuler_technique(t)
res = analyse.analyser_items(lignes)

assert res["effectif"] == 60
assert res["fiable"] is True
par_num = {i["numero"]: i for i in res["items"]}

assert "Trop facile" in " ".join(par_num[q_facile]["alertes"]), par_num[q_facile]
print(f"question {q_facile} (facile a dessein)  -> {par_num[q_facile]['taux_reussite']} % reussite, reperee")

assert par_num[q_ambigue]["correlation"] < 0.10, par_num[q_ambigue]
assert "discrimine" in " ".join(par_num[q_ambigue]["alertes"])
print(f"question {q_ambigue} (ambigue a dessein) -> correlation "
      f"{par_num[q_ambigue]['correlation']}, reperee")

saines = [n for n in par_num if n not in (q_facile, q_ambigue) and not par_num[n]["alertes"]]
print(f"questions saines non signalees        : {len(saines)} sur {len(par_num) - 2}")

# --- effectif insuffisant ------------------------------------------
petit, _, _ = simuler_technique(t, n=8)
r2 = analyse.analyser_items(petit)
assert r2["fiable"] is False
print(f"effectif de 8                         : marque comme non fiable")

# --- statistiques ---------------------------------------------------
resultats = [{"pourcentage": random.uniform(20, 100), "duree_secondes": random.randint(400, 1200),
              "detail": {}} for _ in range(40)]
invitations = ([{"statut": "terminee"}] * 40 + [{"statut": "envoyee"}] * 7
               + [{"statut": "expiree"}] * 3)
st = analyse.statistiques_test(resultats, invitations)
assert st["envoyees"] == 50 and st["terminees"] == 40
assert st["taux_completion"] == 80.0
print(f"statistiques                          : {st['taux_completion']} % de completion, "
      f"mediane {st['score_median']} %")

d = analyse.distribution_scores(resultats)
assert sum(x["effectif"] for x in d) == 40
print(f"distribution                          : {len(d)} tranches, 40 candidats repartis")

# --- anomalies ------------------------------------------------------
inv = {"duree_minutes": 20}
resultat_rapide = {"duree_secondes": 180, "detail": {"type": "technique", "questions":
                   [{"donne": ["A"]} for _ in range(15)]}}
vues = [{"duree_secondes": 2} for _ in range(10)]
a = analyse.detecter_anomalies(inv, resultat_rapide, vues, {"A": 14, "B": 1})
codes = {x["code"] for x in a}
assert "passation_rapide" in codes and "reponses_eclair" in codes and "reponse_monotone" in codes
print(f"candidat expedie                      : {sorted(codes)}")

resultat_plat = {"duree_secondes": 900, "detail": {"type": "positionnement",
                 "profil": [{"total": 3} for _ in range(7)], "non_repondues": 0}}
a2 = analyse.detecter_anomalies(inv, resultat_plat, [{"duree_secondes": 40}] * 27,
                                {"A": 14, "B": 13})
assert "profil_plat" in {x["code"] for x in a2}
print(f"profil sans relief                    : detecte")

serieux = {"duree_secondes": 950, "detail": {"type": "technique", "questions":
           [{"donne": ["A"]} for _ in range(15)]}}
a3 = analyse.detecter_anomalies(inv, serieux, [{"duree_secondes": 55}] * 15,
                                {"A": 5, "B": 4, "C": 6})
assert not any(x["gravite"] == "attention" for x in a3), a3
print(f"candidat serieux                      : aucun signalement d'attention")

print("\nTous les tests passent.")
