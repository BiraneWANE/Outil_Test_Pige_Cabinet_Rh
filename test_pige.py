"""
Tests de la pige, sans réseau ni base de données.

On vérifie ici ce qui décide de la qualité de la liste de prospects :
le regroupement des raisons sociales, le dédoublonnage entre sources,
la traduction des deux formats d'API, et le filtre paie.
"""
from datetime import date

import pige


# --- 1. Regroupement des raisons sociales ------------------------------
# Sans cela, le classement des entreprises les plus actives compterait
# « KPMG » trois fois au lieu d'une.
memes = ["KPMG", "KPMG France", "Cabinet KPMG", "KPMG S.A.S.", "kpmg  sas"]
cles = {pige.cle_entreprise(n) for n in memes}
assert cles == {"kpmg"}, cles

assert pige.cle_entreprise("Fiduciaire de l'Ouest") == "fiduciaire de ouest"
assert pige.cle_entreprise(None) == ""
# Deux entreprises différentes ne doivent pas fusionner.
assert pige.cle_entreprise("Mazars") != pige.cle_entreprise("Deloitte")


# --- 2. Empreinte : la même offre chez deux sources ---------------------
ft = {"entreprise": "KPMG France", "intitule": "Comptable général H/F",
      "commune": "Malakoff"}
ad = {"entreprise": "Cabinet KPMG",  "intitule": "comptable général (h/f)",
      "commune": "MALAKOFF"}
assert pige.empreinte(ft) == pige.empreinte(ad)

# Un poste différent dans la même entreprise reste une annonce distincte.
autre = {"entreprise": "KPMG", "intitule": "Contrôleur de gestion",
         "commune": "Malakoff"}
assert pige.empreinte(ft) != pige.empreinte(autre)

# La même offre dans une autre commune aussi.
ailleurs = dict(ft, commune="Vanves")
assert pige.empreinte(ft) != pige.empreinte(ailleurs)


# --- 3. Traduction d'une offre France Travail --------------------------
offre_ft = {
    "id": "184XKQZ",
    "intitule": "Contrôleur de gestion (H/F)",
    "dateCreation": "2026-07-02T09:12:31.000Z",
    "lieuTravail": {"libelle": "92 - MALAKOFF", "codePostal": "92240",
                    "commune": "92046"},
    "entreprise": {"nom": "GROUPE ALPHA"},
    "typeContrat": "CDI",
    "typeContratLibelle": "Contrat à durée indéterminée",
    "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/184XKQZ"},
    "contact": {"nom": "Mme MARTIN"},
}
a = pige.convertir_france_travail(offre_ft, 2, "comptabilite")
assert a["entreprise"] == "GROUPE ALPHA"
assert a["commune"] == "MALAKOFF"          # le « 92 - » est retiré
assert a["code_postal"] == "92240"
assert a["departement"] == "92"
assert a["publiee_le"] == date(2026, 7, 2)
assert a["type_contrat"] == "Contrat à durée indéterminée"
assert a["contact_nom"] == "Mme MARTIN"    # isolé, effaçable à la demande
assert a["source"] == "france_travail"

# Une offre sans entreprise ni contact ne doit pas faire tomber la collecte.
minimale = pige.convertir_france_travail(
    {"intitule": "Comptable", "lieuTravail": {}}, 2, "comptabilite")
assert minimale["entreprise"] is None and minimale["publiee_le"] is None


# --- 4. Traduction d'une offre Adzuna ----------------------------------
offre_ad = {
    "id": "4711",
    "title": "Gestionnaire de paie",
    "created": "2026-08-01T07:00:00Z",
    "company": {"display_name": "FIDUCIAL"},
    "location": {"display_name": "Malakoff, Hauts-de-Seine",
                 "area": ["France", "Île-de-France", "Hauts-de-Seine", "Malakoff"]},
    "contract_type": "permanent",
    "redirect_url": "https://www.adzuna.fr/details/4711",
}
b = pige.convertir_adzuna(offre_ad, 2, "paie")
assert b["commune"] == "Malakoff"          # la zone la plus fine est retenue
assert b["entreprise"] == "FIDUCIAL"
assert b["publiee_le"] == date(2026, 8, 1)
assert b["source"] == "adzuna"


# --- 5. Filtre paie -----------------------------------------------------
# Les codes ROME mélangent paie et comptabilité : l'intitulé tranche.
assert pige.concerne_la_paie({"intitule": "Gestionnaire de paie H/F"})
assert pige.concerne_la_paie({"intitule": "Chargé de PAYE et ADP"})
assert pige.concerne_la_paie({"intitule": "Assistant payroll"})
assert not pige.concerne_la_paie({"intitule": "Comptable fournisseurs"})
assert not pige.concerne_la_paie({"intitule": ""})


# --- 6. Filtre des missions courtes (partie 1) -------------------------
# Le cabinet ne pige que de l'intérim, du CDD et du management de
# transition. Un CDI de contrôleur de gestion n'est pas un prospect.
assert pige.est_mission_courte({"type_contrat": "Mission intérimaire",
                                "intitule": "Contrôleur de gestion"})
assert pige.est_mission_courte({"type_contrat": "Contrat à durée déterminée",
                                "intitule": "Contrôleur de gestion"})
assert not pige.est_mission_courte({"type_contrat": "Contrat à durée indéterminée",
                                    "intitule": "Contrôleur de gestion"})
assert not pige.est_mission_courte({"type_contrat": "permanent",
                                    "intitule": "Responsable contrôle de gestion"})

# Rattrapage : le management de transition se publie parfois en CDI.
assert pige.est_mission_courte({"type_contrat": "CDI",
                                "intitule": "Manager de transition - contrôle de gestion"})
assert pige.est_mission_courte({"type_contrat": "permanent",
                                "intitule": "Contrôleur de gestion - mission 6 mois"})

# Sans type de contrat annoncé, on garde : le tri se fera à la lecture.
assert pige.est_mission_courte({"type_contrat": None, "intitule": "Contrôleur de gestion"})


# --- 7. Les deux périmètres sont bien couverts -------------------------
parties = {r["partie"] for r in pige.RECHERCHES}
assert parties == {1, 2}
metiers = {r["metier"] for r in pige.RECHERCHES}
assert metiers == {"controle_gestion", "comptabilite", "paie"}

# Partie 1 : toute la France, missions courtes uniquement.
p1 = [r for r in pige.RECHERCHES if r["partie"] == 1]
assert len(p1) == 1
assert p1[0]["zone"] == "france"
assert p1[0]["contrats"] == pige.CONTRATS_COURTS
assert "CDI" not in pige.CONTRATS_COURTS

# Partie 2 : Malakoff et 10 km, tous types de contrat.
p2 = [r for r in pige.RECHERCHES if r["partie"] == 2]
assert all(r["zone"] == "malakoff" and r["contrats"] is None for r in p2)
assert pige.COMMUNE_PARTIE_2 == "92046"
assert pige.DISTANCE_PARTIE_2 == 10

# Les requêtes envoyées à France Travail traduisent bien tout cela.
cg = [p for _, m, p in pige._recherches_france_travail()
      if m == "controle_gestion"][0]
assert cg["typeContrat"] == pige.CONTRATS_COURTS
assert "commune" not in cg and "departement" not in cg   # toute la France

compta = [p for _, m, p in pige._recherches_france_travail() if m == "comptabilite"][0]
assert compta["commune"] == "92046" and compta["distance"] == 10
assert "typeContrat" not in compta

# La paie se cherche par mots-clés : la première collecte a montré que
# les codes ROME M1203 et M1501 ne rendaient que 9 annonces, alors que
# les gestionnaires de paie sont noyés dans les 511 offres de compta.
paie = [p for _, m, p in pige._recherches_france_travail() if m == "paie"][0]
assert "motsCles" in paie and "paie" in paie["motsCles"]
assert "codeROME" not in paie
assert paie["commune"] == "92046" and paie["distance"] == 10

# Une seule recherche paie désormais, au lieu de deux codes ROME.
assert len([r for r in pige.RECHERCHES if r["metier"] == "paie"]) == 1


# --- 7 bis. Le métier se lit dans l'intitulé -----------------------------
# Sans cela, un gestionnaire de paie trouvé d'abord par la recherche
# comptabilité garde l'étiquette « comptabilite » après dédoublonnage,
# et le filtre par métier de la page devient faux.
assert pige.metier_reel({"partie": 2, "intitule": "Gestionnaire de paie H/F"},
                        "comptabilite") == "paie"
assert pige.metier_reel({"partie": 2, "intitule": "Assistant paie et ADP"},
                        "comptabilite") == "paie"
assert pige.metier_reel({"partie": 2, "intitule": "Comptable général"},
                        "paie") == "comptabilite"
# La partie 1 ne contient qu'un métier, quel que soit l'intitulé.
assert pige.metier_reel({"partie": 1, "intitule": "Contrôleur de gestion paie"},
                        "controle_gestion") == "controle_gestion"


# --- 8. Écarter les intermédiaires -------------------------------------
# Ce sont des confrères : ils recrutent pour un client dont ils taisent
# le nom, il n'y a personne à démarcher derrière l'annonce.
for confrere in ("ADECCO", "Manpower France", "Randstad", "Hays France",
                 "MICHAEL PAGE", "Fed Finance", "SUPPLAY INTERIM",
                 "Cabinet de recrutement Durand", "ABC Intérim",
                 "Talents & Co", "AGENCE EMPLOI SERVICES"):
    assert pige.est_intermediaire({"entreprise": confrere}), confrere

# Détectés sur une racine, sans figurer dans aucune liste d'enseignes.
for confrere in ("Comptalents", "Interaction Interim", "Sourcing Pro",
                 "RH Solutions Paris", "Groupe Talents", "Recrutimmo"):
    assert pige.est_intermediaire({"entreprise": confrere}), confrere

# Reconnus à leur nom entier, parce que rien dedans ne trahit le métier.
for confrere in ("LTd", "Collective.work", "EXPERTNET TECHNOLOGIES SA"):
    assert pige.est_intermediaire({"entreprise": confrere}), confrere

for client in ("KPMG France", "Fiducial Expertise", "GROUPE ALPHA",
               "Cabinet Dupont Expertise Comptable", "Danone", "SNCF",
               "LECLERC", "Chanel Fr", "Fayat Energie Services",
               "Ministère des Armées", "Crédit Agricole de Bretagne"):
    assert not pige.est_intermediaire({"entreprise": client}), client

# « Ltd » en fin de nom est un suffixe juridique courant : il ne doit
# pas faire écarter une entreprise réelle.
assert not pige.est_intermediaire({"entreprise": "Smith Ltd France"})
# « Conseil » non plus : beaucoup de cabinets comptables s'appellent ainsi.
assert not pige.est_intermediaire({"entreprise": "Dupont Audit et Conseil"})


# --- 9. Écarter le secteur public --------------------------------------
# Une administration passe par marché public : elle ne choisit pas son
# prestataire librement, il n'y a personne à démarcher.
for public in ("Fonction publique Territoriale", "Fonction publique Hospitalière",
               "Ministère des Armées", "Ministère de la justice", "CNFPT", "CEA",
               "Assistance hôpitaux de Paris", "Mairie de Clamart", "Ville de Paris",
               "Centre Hospitalier de Meudon", "Conseil Départemental du 92"):
    assert pige.est_secteur_public({"entreprise": public}), public

for prive in ("KPMG France", "LECLERC", "Chanel Fr", "SNCF", "Danone",
              "Fayat Energie Services", "Crédit Agricole de Bretagne",
              "Ramsay Santé"):
    assert not pige.est_secteur_public({"entreprise": prive}), prive


# --- 10. Écarter les annonces trop anciennes ---------------------------
# Jusqu'à trois mois, une annonce qui dure est un bon signal. Au-delà de
# quatre mois, c'est un vivier permanent ou une date fausse.
AUJ = date(2026, 8, 31)
for jours in (10, 45, 90, 119):
    a = {"publiee_le": date.fromordinal(AUJ.toordinal() - jours)}
    assert not pige.trop_ancienne(a, AUJ), jours
for jours in (121, 400, 2555):
    a = {"publiee_le": date.fromordinal(AUJ.toordinal() - jours)}
    assert pige.trop_ancienne(a, AUJ), jours

# Sans date, on ne peut rien conclure : on garde.
assert not pige.trop_ancienne({"publiee_le": None}, AUJ)
# À défaut de date de publication, la première fois qu'on l'a vue.
assert pige.trop_ancienne({"publiee_le": None,
                           "vue_le_premier": date(2025, 1, 1)}, AUJ)


# --- 11. Le rayon de 10 km autour de Malakoff --------------------------
# Adzuna ignore le rayon quand il ne reconnaît pas la ville : on vérifie
# nous-mêmes, sinon des comptables de toute la France remontent.
for dedans in ("Malakoff", "MALAKOFF", "Vanves", "Issy-les-Moulineaux",
               "Montrouge", "Paris 14e Arrondissement", "Cachan", "Clamart"):
    assert not pige.hors_perimetre_2({"partie": 2, "commune": dedans}), dedans

for dehors in ("Lyon", "Nantes", "Bordeaux", "Marseille", "Lille", "Rennes"):
    assert pige.hors_perimetre_2({"partie": 2, "commune": dehors}), dehors

# Le département ne fait plus foi : le 92 s'étend de Malakoff à
# Colombes, bien au-delà du rayon. Seule la liste de communes compte.
assert pige.hors_perimetre_2({"partie": 2, "commune": "SAINT-MAUR",
                              "code_postal": "94100"})
assert pige.hors_perimetre_2({"partie": 2, "commune": "Nanterre",
                              "code_postal": "92000"})
assert pige.hors_perimetre_2({"partie": 2, "commune": "Colombes",
                              "code_postal": "92700"})

# Paris est traité par arrondissement : le 18e et le 20e sont hors des
# 10 km, le 14e et le 16e non.
for dedans in ("75005", "75014", "75015", "75016"):
    assert not pige.hors_perimetre_2({"partie": 2, "commune": "PARIS",
                                      "code_postal": dedans}), dedans
for dehors in ("75017", "75018", "75019", "75020"):
    assert pige.hors_perimetre_2({"partie": 2, "commune": "PARIS",
                                  "code_postal": dehors}), dehors

# France Travail écrit « 75 - PARIS 14 » : le 75 ne doit pas être pris
# pour un numéro d'arrondissement.
assert pige._arrondissement("75 - PARIS 14", "75014") == 14
assert pige._arrondissement("PARIS 14") == 14
# Sans arrondissement identifiable, on garde plutôt que d'écarter à tort.
assert not pige.hors_perimetre_2({"partie": 2, "commune": "PARIS",
                                  "code_postal": "75000"})


# --- 11 bis. Alternance, stage et organismes de formation --------------
# Le cabinet place des missions de cadres, pas des alternants.
for hors in (("Alternance - Assistant contrôle de gestion", "Arkema"),
             ("Comptable en apprentissage", "Société X"),
             ("Stagiaire paie", "Société Y"),
             ("Contrôleur de gestion", "Walter Learning"),
             ("Assistant comptable", "Les Sherpas")):
    assert pige.est_alternance({"intitule": hors[0], "entreprise": hors[1]}), hors

for garde in (("Contrôleur de gestion", "LECLERC"),
              ("Comptable général", "In Extenso"),
              ("Gestionnaire de paie", "KPMG France")):
    assert not pige.est_alternance({"intitule": garde[0], "entreprise": garde[1]}), garde


# --- 11 ter. Le secteur public, y compris les armées -------------------
# La première collecte a fait remonter « Armée de l'Air et de l'Espace »
# en tête du classement, avec 46 postes. L'apostrophe empêchait la
# reconnaissance.
for public in ("Armée de l'Air et de l'Espace", "Marine Nationale",
               "Gendarmerie Nationale", "SSA", "Anah", "Dgafp"):
    assert pige.est_secteur_public({"entreprise": public}), public

for prive in ("L'Oréal", "Pennylane SAS", "In Extenso", "SELECT T.I.",
              "Fayat Energie Services", "Groupe IGF", "Arkema"):
    assert not pige.est_secteur_public({"entreprise": prive}), prive

# « France Travail » échappait au filtre : cle_entreprise() retire
# « france », vu comme un suffixe géographique, et « france travail »
# devenait « travail ». La comparaison se fait donc aussi sur le nom
# aplati, avant tout retrait.
assert pige.est_secteur_public({"entreprise": "France Travail"})
assert pige.est_secteur_public({"entreprise": "Pole Emploi"})


# --- 11 quater. Candidatures spontanées et viviers ---------------------
# Une boîte aux lettres laissée en ligne toute l'année n'est pas un
# recrutement : elle explique une partie des anciennetés aberrantes.
for faux in ("Profil Comptable - Candidature Spontanée",
             "Vivier comptables et gestionnaires de paie",
             "CVthèque — déposez votre CV"):
    assert pige.sans_poste_reel({"intitule": faux}), faux

for vrai in ("Comptable général H/F", "Gestionnaire de paie",
             "Contrôleur de gestion - mission 6 mois"):
    assert not pige.sans_poste_reel({"intitule": vrai}), vrai
# La partie 1 couvre toute la France : ce contrôle ne la concerne pas.
assert not pige.hors_perimetre_2({"partie": 1, "commune": "Lyon"})


# --- 12. Motif d'écart ---------------------------------------------------
assert pige.motif_ecart({"partie": 2, "commune": "Lyon",
                         "entreprise": "KPMG"}).startswith("hors des 10 km")
assert "recrutement" in pige.motif_ecart({"partie": 2, "commune": "Vanves",
                                          "entreprise": "Adecco"})
assert pige.motif_ecart({"partie": 1, "commune": "Lyon",
                         "entreprise": None}) == "entreprise non nommee"
assert pige.motif_ecart({"partie": 2, "commune": "Malakoff",
                         "entreprise": "KPMG France"}) is None

assert "secteur public" in pige.motif_ecart(
    {"partie": 2, "commune": "Malakoff", "entreprise": "Ministère des Armées"})
assert "120 jours" in pige.motif_ecart(
    {"partie": 1, "commune": "Lyon", "entreprise": "Danone",
     "publiee_le": date(2019, 1, 1)}, AUJ)


# --- 13. Adresses de fonction et adresses de personne ------------------
# Une adresse générique ne désigne personne : c'est ce qui distingue
# une boîte d'entreprise d'une donnée personnelle.
for fonction in ("contact@cabinet.fr", "recrutement@societe.com",
                 "rh@groupe.fr", "candidatures@abc.fr", "info@x.fr",
                 "service-paie@y.fr", "Direction@Z.FR"):
    assert pige.courriel_generique(fonction), fonction

for personne in ("marie.dupont@cabinet.fr", "m.dupont@cabinet.fr",
                 "jdupont@societe.com", "pierre@abc.fr"):
    assert not pige.courriel_generique(personne), personne

# Ce qui n'est pas une adresse ne passe pas.
for faux in ("", None, "pas une adresse", "a@b", "contact@"):
    assert not pige.courriel_valide(faux), faux
    assert not pige.courriel_generique(faux), faux

# La mention d'information doit dire d'où vient l'adresse et comment
# s'y opposer : sans elle, le traitement ne tient pas.
assert "France Travail" in pige.MENTION_OBLIGATOIRE
assert "opposer" in pige.MENTION_OBLIGATOIRE


# --- 14. Sans clé, aucune source n'est appelée --------------------------
import os
sauve = {c: os.environ.pop(c, None)
         for c in ("FT_CLIENT_ID", "FT_CLIENT_SECRET",
                   "ADZUNA_APP_ID", "ADZUNA_APP_KEY")}
assert pige.configuree() is False
assert pige.collecter_si_besoin() is None   # ne touche même pas à la base
for c, v in sauve.items():
    if v is not None:
        os.environ[c] = v


print("Tests de pige : tout est vert.")
