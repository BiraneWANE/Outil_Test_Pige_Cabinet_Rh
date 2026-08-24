"""
Tests du module de sauvegarde, sans base de donnees.

La base est remplacee par un faux jeu de donnees : ce qu'on verifie ici,
c'est que l'archive produite est complete, lisible et surtout
restaurable, pas que PostgreSQL sait faire un SELECT.
"""
import base64
import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal

import sauvegarde


# --- 1. Conversion des valeurs -----------------------------------------
d = sauvegarde._convertir(datetime(2026, 8, 24, 14, 30, tzinfo=timezone.utc))
assert d.startswith("2026-08-24T14:30"), d

# Un nombre decimal doit rester exact : converti en flottant, un
# pourcentage comme 66.67 deviendrait 66.66999999999999.
assert sauvegarde._convertir(Decimal("66.67")) == "66.67"

octets = sauvegarde._convertir(b"pdf binaire")
assert base64.b64decode(octets["__octets__"]) == b"pdf binaire"

try:
    sauvegarde._convertir(object())
except TypeError:
    pass
else:                                    # pragma: no cover
    raise AssertionError("un type inconnu doit lever une erreur, pas passer "
                         "silencieusement dans l'archive")


# --- 2. Ecriture CSV ----------------------------------------------------
lignes = [
    {"id": 1, "nom": "Dupont", "detail": {"score": 12}, "vide": None},
    {"id": 2, "nom": "Été",    "detail": [1, 2],        "vide": None},
]
texte = sauvegarde._csv_de(lignes).decode("utf-8-sig")
assert "Été" in texte                     # les accents survivent au tableur

relu = list(csv.DictReader(io.StringIO(texte), delimiter=";"))
assert list(relu[0]) == ["id", "nom", "detail", "vide"]
assert relu[0]["detail"] == '{"score": 12}'   # le JSONB reste lisible
assert relu[0]["vide"] == ""                  # un vide reste un vide
assert sauvegarde._csv_de([]) == b""          # une table vide ne casse rien


# --- 3. Archive complete ------------------------------------------------
# On simule la base : deux tables, dont une avec des types qui ne
# s'ecrivent pas tels quels en JSON.
FAUSSE_BASE = {
    "test": [{"id": 1, "code": "QCM_COMPTA_JUNIOR", "cree_le": datetime(2026, 8, 1)}],
    "invitation": [{"id": 7, "candidat_nom": "Dupont",
                    "pourcentage": Decimal("66.67"), "termine_le": None}],
}

sauvegarde._tables_pretes = True                       # pas de base a preparer
sauvegarde._assurer_tables = lambda: None
sauvegarde._tables_a_sauvegarder = lambda: list(FAUSSE_BASE)
sauvegarde._lire = lambda table: FAUSSE_BASE[table]

contenu, manifeste = sauvegarde.construire(datetime(2026, 8, 24, 9, 0))

assert manifeste["total_lignes"] == 2
assert manifeste["ordre_insertion"] == ["test", "invitation"]

with zipfile.ZipFile(io.BytesIO(contenu)) as zf:
    noms = set(zf.namelist())
    # Les donnees, sous les deux formes, plus de quoi recreer les tables.
    for attendu in ("MANIFESTE.json", "donnees.json", "RESTAURATION.md",
                    "csv/test.csv", "csv/invitation.csv",
                    "schema/schema.sql", "restaurer.py"):
        assert attendu in noms, f"{attendu} manque dans l'archive : {sorted(noms)}"

    donnees = json.loads(zf.read("donnees.json"))
    assert donnees["invitation"][0]["pourcentage"] == "66.67"
    assert donnees["test"][0]["cree_le"].startswith("2026-08-01")

    # Le mode d'emploi doit reprendre le compte reel, pas un texte fige.
    mode = zf.read("RESTAURATION.md").decode("utf-8")
    assert "| test | 1 |" in mode and "| invitation | 1 |" in mode


# --- 4. Nom du fichier --------------------------------------------------
assert sauvegarde.nom_fichier(datetime(2026, 8, 24)) == \
    "sauvegarde-tests-candidats-2026-08-24.zip"


# --- 5. Les tables de service ne se sauvegardent pas elles-memes --------
# Sans cette exclusion, chaque copie contiendrait toutes les precedentes
# et la taille doublerait chaque jour.
assert "sauvegarde" in sauvegarde.TABLES_EXCLUES
assert "sauvegarde_telechargement" in sauvegarde.TABLES_EXCLUES


print("Tests de sauvegarde : tout est vert.")
