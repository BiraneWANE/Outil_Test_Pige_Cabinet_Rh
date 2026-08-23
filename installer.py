"""
Installation complete de la base, en une seule commande.

    python installer.py

Cree les tables, la couche analytique, puis charge les 8 tests.
Le script est sans danger : relancez-le autant de fois que necessaire.
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import psycopg
except ImportError:
    sys.exit("psycopg n'est pas installe. Lancez d'abord :\n"
             "    pip install -r requirements.txt")

ICI = os.path.dirname(os.path.abspath(__file__))


def executer_fichier(conn, nom):
    chemin = os.path.join(ICI, nom)
    if not os.path.exists(chemin):
        sys.exit(f"Fichier introuvable : {nom}")
    with open(chemin, encoding="utf-8") as f:
        sql = f.read()
    conn.execute(sql)
    print(f"  {nom} : execute")


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "La variable DATABASE_URL n'est pas definie.\n\n"
            "Sous Windows (PowerShell) :\n"
            '    $env:DATABASE_URL="postgresql://..."\n\n'
            "Sous macOS ou Linux :\n"
            '    export DATABASE_URL="postgresql://..."'
        )

    print("Connexion a la base...")
    try:
        conn = psycopg.connect(url, autocommit=True)
    except Exception as e:
        sys.exit(f"Connexion impossible : {e}\n\n"
                 "Verifiez que la chaine est complete, entre guillemets, "
                 "et qu'elle ne contient pas '-pooler'.")

    with conn:
        version = conn.execute("SELECT version()").fetchone()[0]
        print(f"  {version.split(',')[0]}\n")

        print("Creation des tables...")
        executer_fichier(conn, "schema.sql")
        executer_fichier(conn, "schema_analyse.sql")

        print("\nControle...")
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ).fetchall()
        print("  tables creees : " + ", ".join(t[0] for t in tables))

    print("\nChargement des questions...")
    import charger_banque
    charger_banque.main()

    with psycopg.connect(url) as conn:
        n_tests = conn.execute("SELECT count(*) FROM test").fetchone()[0]
        n_q = conn.execute("SELECT count(*) FROM question").fetchone()[0]
        n_o = conn.execute("SELECT count(*) FROM option_reponse").fetchone()[0]

    print(f"\nTermine : {n_tests} tests, {n_q} questions, {n_o} options.")
    print("\nEtape suivante :")
    print('    uvicorn main:app --reload')
    print("    puis ouvrez http://127.0.0.1:8000/admin")


if __name__ == "__main__":
    main()
