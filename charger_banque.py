"""
Charge la banque de questions dans PostgreSQL.

Usage :
    python charger_banque.py

Le script met a jour sans rien detruire : les tests, questions et options
existants sont mis a jour en place, ce qui preserve les invitations deja
creees et les reponses deja enregistrees.
"""
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row

BANQUE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "banque_questions.json")


def charger(conn, test):
    with conn.cursor() as cur:
        # --- le test : cree ou mis a jour, l'identifiant est conserve ---
        cur.execute(
            """
            INSERT INTO test (code, intitule, domaine, niveau,
                              type_test, duree_minutes, consignes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE
               SET intitule = EXCLUDED.intitule,
                   domaine = EXCLUDED.domaine,
                   niveau = EXCLUDED.niveau,
                   type_test = EXCLUDED.type_test,
                   duree_minutes = EXCLUDED.duree_minutes,
                   consignes = EXCLUDED.consignes
            RETURNING id
            """,
            (test["code"], test["intitule"], test["domaine"], test["niveau"],
             test["type_test"], test["duree_minutes"], test["consignes"]),
        )
        test_id = cur.fetchone()["id"]

        numeros = []
        for q in test["questions"]:
            numeros.append(q["numero"])
            cur.execute(
                """
                INSERT INTO question (test_id, numero, partie, format,
                                      enonce, justification, theme)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (test_id, numero) DO UPDATE
                   SET partie = EXCLUDED.partie,
                       format = EXCLUDED.format,
                       enonce = EXCLUDED.enonce,
                       justification = EXCLUDED.justification,
                       theme = EXCLUDED.theme
                RETURNING id
                """,
                (test_id, q["numero"], q["partie"], q["format"],
                 q["enonce"], q["justification"], q.get("theme")),
            )
            question_id = cur.fetchone()["id"]

            lettres = []
            for o in q["options"]:
                lettres.append(o["lettre"])
                cur.execute(
                    """
                    INSERT INTO option_reponse (question_id, lettre, texte, ordre,
                                                est_correcte, dimension,
                                                est_vigilance, lecture)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (question_id, lettre) DO UPDATE
                       SET texte = EXCLUDED.texte,
                           ordre = EXCLUDED.ordre,
                           est_correcte = EXCLUDED.est_correcte,
                           dimension = EXCLUDED.dimension,
                           est_vigilance = EXCLUDED.est_vigilance,
                           lecture = EXCLUDED.lecture
                    """,
                    (question_id, o["lettre"], o["texte"], o["ordre"],
                     o["est_correcte"], o["dimension"],
                     o["est_vigilance"], o["lecture"]),
                )

            # options retirees de la banque, sauf si un candidat les a cochees
            cur.execute(
                """
                DELETE FROM option_reponse o
                 WHERE o.question_id = %s
                   AND o.lettre <> ALL(%s)
                   AND NOT EXISTS (SELECT 1 FROM reponse r WHERE r.option_id = o.id)
                """,
                (question_id, lettres),
            )

        # questions retirees de la banque, sauf si un candidat y a repondu
        cur.execute(
            """
            DELETE FROM question q
             WHERE q.test_id = %s
               AND q.numero <> ALL(%s)
               AND NOT EXISTS (SELECT 1 FROM reponse r WHERE r.question_id = q.id)
            """,
            (test_id, numeros),
        )
    return test_id


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL n'est pas defini.")

    with open(BANQUE, encoding="utf-8") as f:
        banque = json.load(f)

    with psycopg.connect(url, row_factory=dict_row) as conn:
        for test in banque["tests"]:
            charger(conn, test)
            print(f"  {test['code']:<22} {len(test['questions']):>3} questions")
        conn.commit()

    print(f"\n{len(banque['tests'])} tests charges.")


if __name__ == "__main__":
    main()
