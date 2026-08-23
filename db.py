"""Acces a la base PostgreSQL."""
import os
from contextlib import contextmanager

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable d'environnement DATABASE_URL n'est pas definie.")

pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True)


@contextmanager
def curseur():
    """Ouvre un curseur, valide la transaction si tout se passe bien."""
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur


# ------------------------------------------------------------------
# Invitations
# ------------------------------------------------------------------

def invitation_par_token(token):
    with curseur() as cur:
        cur.execute(
            """
            SELECT i.*, t.code, t.intitule, t.type_test, t.duree_minutes,
                   t.consignes, t.domaine, t.niveau
              FROM invitation i
              JOIN test t ON t.id = i.test_id
             WHERE i.token = %s
            """,
            (token,),
        )
        return cur.fetchone()


def creer_invitation(token, test_id, nom, email, poste, cree_par,
                     jours_validite, jours_conservation):
    with curseur() as cur:
        cur.execute(
            """
            INSERT INTO invitation (token, test_id, candidat_nom, candidat_email,
                                    poste_vise, cree_par, expire_le, purge_apres)
            VALUES (%s, %s, %s, %s, %s, %s,
                    now() + make_interval(days => %s),
                    (CURRENT_DATE + make_interval(days => %s))::date)
            RETURNING id
            """,
            (token, test_id, nom, email, poste, cree_par,
             jours_validite, jours_conservation),
        )
        return cur.fetchone()["id"]


def demarrer(invitation_id):
    with curseur() as cur:
        cur.execute(
            """
            UPDATE invitation
               SET demarre_le = now(), statut = 'en_cours', consentement_le = now()
             WHERE id = %s AND demarre_le IS NULL
            """,
            (invitation_id,),
        )


def cloturer(invitation_id, motif="soumission"):
    with curseur() as cur:
        cur.execute(
            """
            UPDATE invitation
               SET termine_le = COALESCE(termine_le, now()), statut = 'terminee'
             WHERE id = %s
            """,
            (invitation_id,),
        )
        cur.execute(
            "INSERT INTO journal (invitation_id, evenement) VALUES (%s, %s)",
            (invitation_id, motif),
        )


def journaliser(invitation_id, evenement, detail=None):
    with curseur() as cur:
        cur.execute(
            "INSERT INTO journal (invitation_id, evenement, detail) VALUES (%s, %s, %s)",
            (invitation_id, evenement, detail),
        )


# ------------------------------------------------------------------
# Questions et reponses
# ------------------------------------------------------------------

def questions_du_test(test_id):
    with curseur() as cur:
        cur.execute(
            "SELECT * FROM question WHERE test_id = %s ORDER BY numero",
            (test_id,),
        )
        questions = cur.fetchall()
        for q in questions:
            cur.execute(
                """
                SELECT id, lettre, texte, est_correcte, dimension,
                       est_vigilance, lecture
                  FROM option_reponse
                 WHERE question_id = %s
                 ORDER BY ordre
                """,
                (q["id"],),
            )
            q["options"] = cur.fetchall()
        return questions


def question_par_numero(test_id, numero):
    with curseur() as cur:
        cur.execute(
            "SELECT * FROM question WHERE test_id = %s AND numero = %s",
            (test_id, numero),
        )
        q = cur.fetchone()
        if not q:
            return None
        cur.execute(
            """
            SELECT id, lettre, texte
              FROM option_reponse
             WHERE question_id = %s
             ORDER BY ordre
            """,
            (q["id"],),
        )
        q["options"] = cur.fetchall()
        return q


def nombre_questions(test_id):
    with curseur() as cur:
        cur.execute("SELECT count(*) AS n FROM question WHERE test_id = %s", (test_id,))
        return cur.fetchone()["n"]


def enregistrer_reponses(invitation_id, question_id, options_ids):
    """Remplace les reponses de cette question : le candidat peut revenir dessus."""
    with curseur() as cur:
        cur.execute(
            "DELETE FROM reponse WHERE invitation_id = %s AND question_id = %s",
            (invitation_id, question_id),
        )
        for oid in options_ids:
            cur.execute(
                """
                INSERT INTO reponse (invitation_id, question_id, option_id)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (invitation_id, question_id, oid),
            )


def reponses_de(invitation_id, question_id=None):
    with curseur() as cur:
        if question_id:
            cur.execute(
                "SELECT option_id FROM reponse WHERE invitation_id = %s AND question_id = %s",
                (invitation_id, question_id),
            )
        else:
            cur.execute(
                "SELECT question_id, option_id FROM reponse WHERE invitation_id = %s",
                (invitation_id,),
            )
        return cur.fetchall()


# ------------------------------------------------------------------
# Resultats
# ------------------------------------------------------------------

def enregistrer_resultat(invitation_id, res):
    import json
    with curseur() as cur:
        cur.execute(
            """
            INSERT INTO resultat (invitation_id, score, total_points, pourcentage,
                                  duree_secondes, nb_vigilances, detail)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invitation_id) DO UPDATE
               SET score = EXCLUDED.score,
                   total_points = EXCLUDED.total_points,
                   pourcentage = EXCLUDED.pourcentage,
                   duree_secondes = EXCLUDED.duree_secondes,
                   nb_vigilances = EXCLUDED.nb_vigilances,
                   detail = EXCLUDED.detail,
                   calcule_le = now()
            """,
            (invitation_id, res.get("score"), res.get("total_points"),
             res.get("pourcentage"), res.get("duree_secondes"),
             res.get("nb_vigilances"), json.dumps(res["detail"])),
        )


def resultat_de(invitation_id):
    with curseur() as cur:
        cur.execute("SELECT * FROM resultat WHERE invitation_id = %s", (invitation_id,))
        return cur.fetchone()


def liste_tests():
    with curseur() as cur:
        cur.execute(
            "SELECT id, code, intitule, type_test, domaine, niveau "
            "FROM test WHERE actif ORDER BY domaine, niveau, type_test"
        )
        return cur.fetchall()


def liste_invitations(limite=200):
    with curseur() as cur:
        cur.execute(
            """
            SELECT i.id, i.token, i.candidat_nom, i.candidat_email, i.poste_vise,
                   i.statut, i.cree_le, i.expire_le, i.termine_le,
                   t.intitule, t.type_test,
                   r.score, r.total_points, r.pourcentage, r.nb_vigilances
              FROM invitation i
              JOIN test t ON t.id = i.test_id
              LEFT JOIN resultat r ON r.invitation_id = i.id
             ORDER BY i.cree_le DESC
             LIMIT %s
            """,
            (limite,),
        )
        return cur.fetchall()


# ------------------------------------------------------------------
# Couche analytique
# ------------------------------------------------------------------

def marquer_vue(invitation_id, question_id):
    """Enregistre l'affichage d'une question et cloture la duree de la
    precedente. C'est cette donnee qui alimente l'analyse d'items."""
    with curseur() as cur:
        cur.execute(
            """
            UPDATE vue_question
               SET quittee_le = now(),
                   duree_secondes = COALESCE(duree_secondes, 0)
                                  + EXTRACT(EPOCH FROM now() - affichee_le)::int
             WHERE invitation_id = %s AND quittee_le IS NULL AND question_id <> %s
            """,
            (invitation_id, question_id),
        )
        cur.execute(
            """
            INSERT INTO vue_question (invitation_id, question_id)
            VALUES (%s, %s)
            ON CONFLICT (invitation_id, question_id) DO UPDATE
               SET affichee_le = now(),
                   quittee_le = NULL,
                   nb_affichages = vue_question.nb_affichages + 1
            """,
            (invitation_id, question_id),
        )


def cloturer_vues(invitation_id):
    with curseur() as cur:
        cur.execute(
            """
            UPDATE vue_question
               SET quittee_le = now(),
                   duree_secondes = COALESCE(duree_secondes, 0)
                                  + EXTRACT(EPOCH FROM now() - affichee_le)::int
             WHERE invitation_id = %s AND quittee_le IS NULL
            """,
            (invitation_id,),
        )


def vues_de(invitation_id):
    with curseur() as cur:
        cur.execute(
            "SELECT question_id, duree_secondes, nb_affichages "
            "FROM vue_question WHERE invitation_id = %s",
            (invitation_id,),
        )
        return cur.fetchall()


def lettres_choisies(invitation_id):
    """Repartition des reponses par position, pour reperer un candidat
    qui coche systematiquement la meme lettre."""
    with curseur() as cur:
        cur.execute(
            """
            SELECT o.lettre, count(*) AS n
              FROM reponse r JOIN option_reponse o ON o.id = r.option_id
             WHERE r.invitation_id = %s
             GROUP BY o.lettre
            """,
            (invitation_id,),
        )
        return {l["lettre"]: l["n"] for l in cur.fetchall()}


def lignes_analyse(test_id):
    with curseur() as cur:
        cur.execute("SELECT * FROM v_reponses_analyse WHERE test_id = %s", (test_id,))
        return cur.fetchall()


def resultats_du_test(test_id):
    with curseur() as cur:
        cur.execute(
            """
            SELECT r.* FROM resultat r
              JOIN invitation i ON i.id = r.invitation_id
             WHERE i.test_id = %s
            """,
            (test_id,),
        )
        return cur.fetchall()


def invitations_du_test(test_id):
    with curseur() as cur:
        cur.execute("SELECT * FROM invitation WHERE test_id = %s", (test_id,))
        return cur.fetchall()


def test_par_id(test_id):
    with curseur() as cur:
        cur.execute("SELECT * FROM test WHERE id = %s", (test_id,))
        return cur.fetchone()


def enregistrer_anomalies(invitation_id, anomalies):
    with curseur() as cur:
        cur.execute("DELETE FROM anomalie WHERE invitation_id = %s", (invitation_id,))
        for a in anomalies:
            cur.execute(
                "INSERT INTO anomalie (invitation_id, code, libelle, gravite) "
                "VALUES (%s, %s, %s, %s)",
                (invitation_id, a["code"], a["libelle"], a["gravite"]),
            )


def anomalies_de(invitation_id):
    with curseur() as cur:
        cur.execute(
            "SELECT code, libelle, gravite FROM anomalie WHERE invitation_id = %s",
            (invitation_id,),
        )
        return cur.fetchall()


def export_lignes():
    """Export anonymise, destine a une analyse dans un notebook."""
    with curseur() as cur:
        cur.execute(
            """
            SELECT i.id AS passation, t.code AS test, t.domaine, t.niveau,
                   t.type_test, q.numero, q.partie, q.format,
                   v.duree_secondes AS temps_question, v.nb_affichages,
                   va.juste,
                   r.pourcentage AS score_global, r.duree_secondes AS duree_totale,
                   date_trunc('day', i.termine_le) AS jour
              FROM invitation i
              JOIN test t     ON t.id = i.test_id
              JOIN question q ON q.test_id = t.id
              LEFT JOIN vue_question v ON v.invitation_id = i.id AND v.question_id = q.id
              LEFT JOIN resultat r     ON r.invitation_id = i.id
              LEFT JOIN v_reponses_analyse va
                     ON va.invitation_id = i.id AND va.question_id = q.id
             WHERE i.statut = 'terminee'
             ORDER BY i.id, q.numero
            """
        )
        return cur.fetchall()


def enregistrer_guide(invitation_id, contenu, fournisseur, modele, utilisateur):
    with curseur() as cur:
        cur.execute(
            """
            INSERT INTO guide_entretien (invitation_id, contenu, fournisseur,
                                         modele, genere_par)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (invitation_id) DO UPDATE
               SET contenu = EXCLUDED.contenu,
                   fournisseur = EXCLUDED.fournisseur,
                   modele = EXCLUDED.modele,
                   genere_par = EXCLUDED.genere_par,
                   genere_le = now()
            """,
            (invitation_id, contenu, fournisseur, modele, utilisateur),
        )


def guide_de(invitation_id):
    with curseur() as cur:
        cur.execute(
            "SELECT contenu, fournisseur, modele, genere_le "
            "FROM guide_entretien WHERE invitation_id = %s",
            (invitation_id,),
        )
        return cur.fetchone()


def compter_evenements(invitation_id, evenement):
    with curseur() as cur:
        cur.execute(
            "SELECT count(*) AS n FROM journal "
            "WHERE invitation_id = %s AND evenement = %s",
            (invitation_id, evenement),
        )
        return cur.fetchone()["n"]
