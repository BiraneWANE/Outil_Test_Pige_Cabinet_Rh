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


# --- 6. Les deux périmètres sont bien couverts -------------------------
parties = {p for p, _, _, _ in pige.RECHERCHES}
assert parties == {1, 2}
metiers = {m for _, m, _, _ in pige.RECHERCHES}
assert metiers == {"controle_gestion", "comptabilite", "paie"}

# Partie 1 : toute l'Île-de-France, huit départements.
assert len(pige.DEPARTEMENTS_IDF.split(",")) == 8
# Partie 2 : Malakoff et 10 km.
assert pige.COMMUNE_PARTIE_2 == "92046"
assert pige.DISTANCE_PARTIE_2 == 10


# --- 7. Sans clé, aucune source n'est appelée ---------------------------
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
