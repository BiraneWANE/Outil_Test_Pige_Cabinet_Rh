"""
Remise en service de la base a partir d'une sauvegarde.

    pip install "psycopg[binary]"
    export DATABASE_URL="postgresql://..."     # la NOUVELLE base, vide
    python restaurer.py

Ce script est fait pour tourner depuis le dossier d'une archive
decompressee, sans le reste de l'application : il n'a besoin que de
`MANIFESTE.json`, `donnees.json` et du dossier `schema/`.

Il refuse d'ecrire dans une base qui contient deja des donnees. Pour
forcer malgre tout, par exemple lors d'un essai de restauration :

    python restaurer.py --ecraser
"""
import base64
import json
import os
import sys

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    sys.exit('psycopg n\'est pas installe. Lancez :\n'
             '    pip install "psycopg[binary]"')

ICI = os.path.dirname(os.path.abspath(__file__))
ECRASER = "--ecraser" in sys.argv


def lire_json(nom):
    chemin = os.path.join(ICI, nom)
    if not os.path.exists(chemin):
        sys.exit(f"Fichier introuvable : {nom}. Lancez le script depuis le "
                 f"dossier de l'archive decompressee.")
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def valeur(v):
    """Remet une valeur du JSON dans une forme que PostgreSQL accepte."""
    if isinstance(v, dict) and set(v) == {"__octets__"}:
        return base64.b64decode(v["__octets__"])
    if isinstance(v, (dict, list)):
        return Jsonb(v)
    return v            # les dates et nombres sont convertis par PostgreSQL


def base_deja_peuplee(conn):
    existe = conn.execute(
        "SELECT to_regclass('public.invitation') IS NOT NULL AS oui"
    ).fetchone()[0]
    if not existe:
        return False
    n = conn.execute("SELECT count(*) FROM invitation").fetchone()[0]
    return n > 0


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("La variable DATABASE_URL n'est pas definie.\n\n"
                 "Sous Windows (PowerShell) :\n"
                 '    $env:DATABASE_URL="postgresql://..."\n\n'
                 "Sous macOS ou Linux :\n"
                 '    export DATABASE_URL="postgresql://..."')

    manifeste = lire_json("MANIFESTE.json")
    donnees = lire_json("donnees.json")

    print(f"Archive du {manifeste['cree_le']}, "
          f"{manifeste['total_lignes']} lignes.\n")

    conn = psycopg.connect(url, autocommit=True)
    with conn:
        if base_deja_peuplee(conn) and not ECRASER:
            sys.exit("Cette base contient deja des passations. Le script "
                     "s'arrete pour ne rien ecraser.\n"
                     "Utilisez une base vide, ou relancez avec --ecraser "
                     "si vous savez ce que vous faites.")

        print("Creation des tables...")
        for nom in ("schema.sql", "schema_analyse.sql", "schema_sauvegarde.sql"):
            chemin = os.path.join(ICI, "schema", nom)
            if os.path.exists(chemin):
                with open(chemin, encoding="utf-8") as f:
                    conn.execute(f.read())
                print(f"  {nom}")

        print("\nReinjection des donnees...")
        for table in manifeste["ordre_insertion"]:
            lignes = donnees.get(table) or []
            if not lignes:
                print(f"  {table} : vide")
                continue
            if ECRASER:
                conn.execute(f'TRUNCATE "{table}" CASCADE')
            colonnes = list(lignes[0].keys())
            noms = ", ".join(f'"{c}"' for c in colonnes)
            trous = ", ".join(["%s"] * len(colonnes))
            requete = f'INSERT INTO "{table}" ({noms}) VALUES ({trous})'
            with conn.cursor() as cur:
                cur.executemany(
                    requete,
                    [[valeur(l[c]) for c in colonnes] for l in lignes],
                )
            print(f"  {table} : {len(lignes)} lignes")

        print("\nRecalage des compteurs d'identifiants...")
        for table in manifeste["ordre_insertion"]:
            conn.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT max(id) FROM "{table}"), 1)
                )
                WHERE pg_get_serial_sequence('{table}', 'id') IS NOT NULL
                """
            )

        total = conn.execute("SELECT count(*) FROM invitation").fetchone()[0]

    print(f"\nTermine. {total} invitation(s) en base.")
    print("\nEtape suivante : pointez l'application vers cette base en "
          "changeant DATABASE_URL, puis ouvrez /sante/base pour verifier.")


if __name__ == "__main__":
    main()
