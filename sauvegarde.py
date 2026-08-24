"""
Sauvegarde complete de la base, sous forme d'archive telechargeable.

Pourquoi ce module existe
-------------------------
Les donnees du cabinet vivent chez un seul hebergeur de base. S'il
disparaissait, le code serait toujours sur GitHub et l'application
redeployable ailleurs en quelques heures, mais les invitations, les
reponses et les resultats seraient perdus. Une copie qui ne sort pas
de chez l'hebergeur ne protege de rien.

Ce module produit donc une archive autonome : les donnees, le schema
qui permet de recreer les tables, et un script qui reinjecte le tout
dans une base neuve. Elle s'ouvre avec n'importe quel outil de
decompression et se lit sans PostgreSQL, puisque chaque table est
aussi ecrite en CSV.

Deux usages, qui ne protegent pas de la meme chose
--------------------------------------------------
  - une copie automatique par jour, conservee un mois dans la base :
    elle rattrape une fausse manoeuvre ou une suppression accidentelle ;
  - un telechargement depuis le back-office : c'est celui-la, et lui
    seul, qui protege de la disparition de l'hebergeur.

Le back-office rappelle la date du dernier telechargement pour que le
second ne soit pas oublie.
"""
import csv
import io
import json
import os
import zipfile
from datetime import date, datetime
from decimal import Decimal

from psycopg import sql

import db

ICI = os.path.dirname(os.path.abspath(__file__))

# Ordre d'insertion : une table n'est ecrite qu'apres celles auxquelles
# elle renvoie. C'est ce qui permet a la restauration de fonctionner
# sans desactiver les contraintes.
ORDRE_TABLES = [
    "test",
    "question",
    "option_reponse",
    "invitation",
    "reponse",
    "resultat",
    "journal",
    "vue_question",
    "anomalie",
    "guide_entretien",
]

# Tables de service : elles decrivent la sauvegarde elle-meme et n'ont
# aucune raison d'y figurer. Les inclure ferait grossir chaque copie de
# toutes les precedentes.
TABLES_EXCLUES = {"sauvegarde", "sauvegarde_telechargement"}

JOURS_HISTORIQUE = 30       # duree de conservation des copies automatiques
JOURS_AVANT_RAPPEL = 7      # au-dela, le back-office reclame un telechargement

_tables_pretes = False
_dernier_passage = None


# ==================================================================
# Tables de service
# ==================================================================

def _assurer_tables():
    """
    Cree les deux tables de service si elles manquent.

    Fait a l'usage plutot que par une migration a lancer a la main :
    la base de production est chez un hebergeur distant, et une etape
    manuelle oubliee, c'est une sauvegarde qui ne tourne pas.
    """
    global _tables_pretes
    if _tables_pretes:
        return
    chemin = os.path.join(ICI, "schema_sauvegarde.sql")
    with open(chemin, encoding="utf-8") as f:
        script = f.read()
    with db.curseur() as cur:
        cur.execute(script)
    _tables_pretes = True


# ==================================================================
# Lecture de la base
# ==================================================================

def _tables_a_sauvegarder():
    """Toutes les tables reelles du schema public, dans l'ordre des
    dependances. Une table ajoutee plus tard est reprise d'office, a la
    fin : la sauvegarde ne se perime pas quand le schema evolue."""
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT table_name AS nom
              FROM information_schema.tables
             WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        presentes = {l["nom"] for l in cur.fetchall()} - TABLES_EXCLUES
    connues = [t for t in ORDRE_TABLES if t in presentes]
    autres = sorted(presentes - set(connues))
    return connues + autres


def _lire(table):
    with db.curseur() as cur:
        cur.execute(sql.SQL("SELECT * FROM {} ORDER BY 1").format(sql.Identifier(table)))
        return cur.fetchall()


def _convertir(valeur):
    """Rend une valeur ecrivable en JSON sans perdre d'information."""
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    if isinstance(valeur, Decimal):
        return str(valeur)          # str et non float : pas d'arrondi
    if isinstance(valeur, (bytes, memoryview)):
        import base64
        return {"__octets__": base64.b64encode(bytes(valeur)).decode("ascii")}
    raise TypeError(f"Type non pris en charge dans la sauvegarde : {type(valeur)}")


# ==================================================================
# Construction de l'archive
# ==================================================================

def _csv_de(lignes):
    """
    Une table en CSV, pour pouvoir la lire dans un tableur sans rien
    installer. L'encodage utf-8-sig est celui qu'Excel reconnait tout
    seul : sans lui, les accents arrivent en caracteres bizarres.
    """
    if not lignes:
        return b""
    tampon = io.StringIO()
    graveur = csv.DictWriter(tampon, fieldnames=list(lignes[0].keys()),
                             delimiter=";", extrasaction="ignore")
    graveur.writeheader()
    for ligne in lignes:
        graveur.writerow({
            cle: ("" if v is None else
                  json.dumps(v, ensure_ascii=False, default=_convertir)
                  if isinstance(v, (dict, list)) else v)
            for cle, v in ligne.items()
        })
    return tampon.getvalue().encode("utf-8-sig")


def construire(horodatage=None):
    """
    Lit toute la base et rend (octets_de_l_archive, resume).

    Le resume sert a l'affichage et au journal : nombre de lignes par
    table, total, taille.
    """
    _assurer_tables()
    quand = horodatage or datetime.now()
    tables = _tables_a_sauvegarder()

    donnees = {}
    comptes = {}
    for table in tables:
        lignes = _lire(table)
        donnees[table] = lignes
        comptes[table] = len(lignes)

    manifeste = {
        "application": "Plateforme de tests candidats",
        "cree_le": quand.isoformat(timespec="seconds"),
        "ordre_insertion": tables,
        "lignes_par_table": comptes,
        "total_lignes": sum(comptes.values()),
        "format": 1,
    }

    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("MANIFESTE.json",
                    json.dumps(manifeste, ensure_ascii=False, indent=2))
        zf.writestr("donnees.json",
                    json.dumps(donnees, ensure_ascii=False, indent=1,
                               default=_convertir))
        for table in tables:
            zf.writestr(f"csv/{table}.csv", _csv_de(donnees[table]))
        for fichier in ("schema.sql", "schema_analyse.sql",
                        "schema_sauvegarde.sql", "restaurer.py"):
            chemin = os.path.join(ICI, fichier)
            if os.path.exists(chemin):
                zf.write(chemin, f"schema/{fichier}" if fichier.endswith(".sql")
                         else fichier)
        zf.writestr("RESTAURATION.md", _mode_d_emploi(manifeste))

    return tampon.getvalue(), manifeste


def nom_fichier(quand=None):
    quand = quand or datetime.now()
    return f"sauvegarde-tests-candidats-{quand:%Y-%m-%d}.zip"


def _mode_d_emploi(manifeste):
    lignes = "\n".join(
        f"| {t} | {n} |" for t, n in manifeste["lignes_par_table"].items()
    )
    return f"""# Restaurer cette sauvegarde

Archive produite le {manifeste['cree_le']}.
{manifeste['total_lignes']} lignes au total.

| Table | Lignes |
|---|---|
{lignes}

## Ce que contient l'archive

- `donnees.json` : toutes les donnees, dans l'ordre d'insertion.
- `csv/` : les memes donnees, une table par fichier, lisibles dans un
  tableur sans rien installer.
- `schema/` : les scripts qui recreent les tables vides.
- `restaurer.py` : le script de remise en service.

## Remettre la base en service

Sur une base PostgreSQL **vide** (n'importe quel hebergeur, ou une base
locale), depuis le dossier de l'archive :

    pip install psycopg[binary]
    export DATABASE_URL="postgresql://..."    # la nouvelle base
    python restaurer.py

Le script cree les tables, reinjecte les lignes dans l'ordre, puis
recale les compteurs d'identifiants. Il refuse de s'executer sur une
base qui contient deja des donnees, pour ne rien ecraser par
inadvertance.

Il ne reste alors qu'a pointer l'application vers la nouvelle base en
changeant la variable `DATABASE_URL`.

## A verifier une fois par an

Une sauvegarde jamais restauree n'est pas une sauvegarde. Le test tient
en dix minutes : creer une base d'essai vide, lancer `restaurer.py`
dessus, ouvrir l'application avec cette base, verifier qu'un ancien
resultat s'affiche, puis supprimer la base d'essai.
"""


# ==================================================================
# Copies automatiques conservees en base
# ==================================================================

def enregistrer():
    """Construit une archive et la range dans la base. Rend le resume."""
    contenu, manifeste = construire()
    with db.curseur() as cur:
        cur.execute(
            "INSERT INTO sauvegarde (octets, nb_lignes, contenu) "
            "VALUES (%s, %s, %s) RETURNING id, cree_le",
            (len(contenu), manifeste["total_lignes"], contenu),
        )
        ligne = cur.fetchone()
        cur.execute(
            "DELETE FROM sauvegarde "
            " WHERE cree_le < now() - make_interval(days => %s)",
            (JOURS_HISTORIQUE,),
        )
    manifeste["id"] = ligne["id"]
    return manifeste


def _existe_aujourdhui():
    with db.curseur() as cur:
        cur.execute(
            "SELECT 1 FROM sauvegarde WHERE cree_le::date = CURRENT_DATE LIMIT 1"
        )
        return cur.fetchone() is not None


def sauvegarder_si_besoin(aujourdhui=None):
    """
    Une copie par jour, pas davantage.

    Deux garde-fous : un marqueur en memoire, qui evite d'interroger la
    base a chaque visite du back-office, et un controle en base, qui
    evite de refaire une copie a chaque redemarrage du serveur.
    """
    global _dernier_passage
    _assurer_tables()
    jour = aujourdhui or date.today()
    if _dernier_passage == jour:
        return None
    _dernier_passage = jour
    if _existe_aujourdhui():
        return None
    return enregistrer()


# ==================================================================
# Lecture pour le back-office
# ==================================================================

def liste(limite=40):
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute(
            "SELECT id, cree_le, octets, nb_lignes FROM sauvegarde "
            " ORDER BY cree_le DESC LIMIT %s",
            (limite,),
        )
        return cur.fetchall()


def copie(sauvegarde_id):
    with db.curseur() as cur:
        cur.execute(
            "SELECT cree_le, contenu FROM sauvegarde WHERE id = %s",
            (sauvegarde_id,),
        )
        return cur.fetchone()


def journaliser_telechargement(utilisateur, octets):
    with db.curseur() as cur:
        cur.execute(
            "INSERT INTO sauvegarde_telechargement (utilisateur, octets) "
            "VALUES (%s, %s)",
            (utilisateur, octets),
        )


def etat():
    """
    De quoi afficher un rappel utile : quand a eu lieu la derniere copie
    automatique, et surtout quand une copie est reellement sortie d'ici.
    """
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT count(*)      AS copies,
                   max(cree_le)  AS derniere_copie,
                   sum(octets)   AS place_occupee
              FROM sauvegarde
            """
        )
        base = cur.fetchone()
        cur.execute(
            """
            SELECT max(telecharge_le) AS dernier,
                   (CURRENT_DATE - max(telecharge_le)::date) AS jours
              FROM sauvegarde_telechargement
            """
        )
        tel = cur.fetchone()

    jours = tel["jours"]
    return {
        "copies": base["copies"] or 0,
        "derniere_copie": base["derniere_copie"],
        "place_occupee": base["place_occupee"] or 0,
        "dernier_telechargement": tel["dernier"],
        "jours_depuis_telechargement": jours,
        # Jamais telecharge, ou trop ancien : dans les deux cas, il n'y a
        # aucune copie hors des serveurs, et c'est ce qu'il faut dire.
        "rappel": jours is None or jours > JOURS_AVANT_RAPPEL,
    }
