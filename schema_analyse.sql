-- ============================================================
-- Extension analytique
-- A executer apres schema.sql, sur une base existante.
-- ============================================================

-- ------------------------------------------------------------
-- Temps passe sur chaque question
-- C'est la donnee qui manque pour toute analyse serieuse :
-- sans elle, impossible de reperer une question mal formulee
-- ni un candidat qui a repondu au hasard.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vue_question (
    id              SERIAL PRIMARY KEY,
    invitation_id   INT NOT NULL REFERENCES invitation(id) ON DELETE CASCADE,
    question_id     INT NOT NULL REFERENCES question(id),
    affichee_le     TIMESTAMPTZ NOT NULL DEFAULT now(),
    quittee_le      TIMESTAMPTZ,
    duree_secondes  INT,
    nb_affichages   INT NOT NULL DEFAULT 1,
    UNIQUE (invitation_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_vue_invitation ON vue_question(invitation_id);
CREATE INDEX IF NOT EXISTS idx_vue_question   ON vue_question(question_id);

-- ------------------------------------------------------------
-- Signalements automatiques sur une passation
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomalie (
    id              SERIAL PRIMARY KEY,
    invitation_id   INT NOT NULL REFERENCES invitation(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    libelle         TEXT NOT NULL,
    gravite         TEXT NOT NULL CHECK (gravite IN ('info', 'attention')),
    detectee_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_anomalie_invitation ON anomalie(invitation_id);

-- ------------------------------------------------------------
-- Vue de travail : une ligne par candidat, question et resultat
-- Sert de base a l'analyse d'items et a l'export.
-- Aucune donnee nominative : exploitable pour des statistiques.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_reponses_analyse AS
SELECT
    i.id                AS invitation_id,
    t.id                AS test_id,
    t.code              AS test_code,
    t.type_test,
    t.domaine,
    t.niveau,
    q.id                AS question_id,
    q.numero,
    q.partie,
    q.format,
    v.duree_secondes    AS temps_question,
    v.nb_affichages,
    -- pour un test technique : la question est-elle validee ?
    CASE WHEN t.type_test = 'technique' THEN (
        (SELECT array_agg(o.id ORDER BY o.id) FROM option_reponse o
          WHERE o.question_id = q.id AND o.est_correcte)
        IS NOT DISTINCT FROM
        (SELECT array_agg(r.option_id ORDER BY r.option_id) FROM reponse r
          WHERE r.invitation_id = i.id AND r.question_id = q.id)
    ) END               AS juste,
    i.termine_le,
    i.cree_le
FROM invitation i
JOIN test t     ON t.id = i.test_id
JOIN question q ON q.test_id = t.id
LEFT JOIN vue_question v ON v.invitation_id = i.id AND v.question_id = q.id
WHERE i.statut = 'terminee';

-- ------------------------------------------------------------
-- Guide d'entretien genere automatiquement
-- Le contenu est une aide a la preparation, jamais une evaluation.
-- On conserve le modele utilise et la date, pour tracabilite.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guide_entretien (
    id              SERIAL PRIMARY KEY,
    invitation_id   INT NOT NULL UNIQUE REFERENCES invitation(id) ON DELETE CASCADE,
    contenu         TEXT NOT NULL,
    fournisseur     TEXT NOT NULL,
    modele          TEXT NOT NULL,
    genere_par      TEXT,
    genere_le       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Theme de rattachement d'une question (tests techniques)
-- Alimente la synthese par domaine sur la fiche de resultat.
ALTER TABLE question ADD COLUMN IF NOT EXISTS theme TEXT;
