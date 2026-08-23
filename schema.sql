-- ============================================================
-- Plateforme de tests candidats - schema PostgreSQL
-- ============================================================

-- ------------------------------------------------------------
-- 1. Catalogue des tests
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS test (
    id              SERIAL PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,          -- ex : QCM_COMPTA_JUNIOR
    intitule        TEXT NOT NULL,
    domaine         TEXT NOT NULL CHECK (domaine IN ('comptabilite', 'paie')),
    niveau          TEXT NOT NULL CHECK (niveau IN ('junior', 'confirme')),
    type_test       TEXT NOT NULL CHECK (type_test IN ('technique', 'positionnement')),
    duree_minutes   INT  NOT NULL DEFAULT 20,
    consignes       TEXT,
    actif           BOOLEAN NOT NULL DEFAULT TRUE,
    cree_le         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 2. Questions
--    format : 'unique'    = une seule bonne reponse (technique)
--             'multiple'  = plusieurs bonnes reponses (technique)
--             'paire'     = choix force entre deux propositions (positionnement)
--             'situation' = mise en situation (positionnement)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question (
    id              SERIAL PRIMARY KEY,
    test_id         INT  NOT NULL REFERENCES test(id) ON DELETE CASCADE,
    numero          INT  NOT NULL,
    partie          INT  NOT NULL DEFAULT 1,
    format          TEXT NOT NULL CHECK (format IN ('unique', 'multiple', 'paire', 'situation')),
    enonce          TEXT NOT NULL,
    justification   TEXT,                          -- affichee au recruteur uniquement
    UNIQUE (test_id, numero)
);

-- ------------------------------------------------------------
-- 3. Options de reponse
--    est_correcte  : tests techniques uniquement
--    dimension     : positionnement, partie 1 (R, O, A, C, S, E, N)
--    est_vigilance : positionnement, partie 2
--    lecture       : commentaire destine au recruteur
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS option_reponse (
    id              SERIAL PRIMARY KEY,
    question_id     INT  NOT NULL REFERENCES question(id) ON DELETE CASCADE,
    lettre          TEXT NOT NULL,
    texte           TEXT NOT NULL,
    ordre           INT  NOT NULL,
    est_correcte    BOOLEAN NOT NULL DEFAULT FALSE,
    dimension       CHAR(1),
    est_vigilance   BOOLEAN NOT NULL DEFAULT FALSE,
    lecture         TEXT,
    UNIQUE (question_id, lettre)
);

-- ------------------------------------------------------------
-- 4. Invitations : un lien unique par candidat et par test
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invitation (
    id              SERIAL PRIMARY KEY,
    token           TEXT NOT NULL UNIQUE,          -- 22 caracteres, genere par secrets.token_urlsafe
    test_id         INT  NOT NULL REFERENCES test(id),
    candidat_nom    TEXT,
    candidat_email  TEXT,
    poste_vise      TEXT,
    cree_par        TEXT NOT NULL,                 -- identifiant du recruteur
    cree_le         TIMESTAMPTZ NOT NULL DEFAULT now(),
    expire_le       TIMESTAMPTZ NOT NULL,          -- validite du lien, ex : 7 jours
    statut          TEXT NOT NULL DEFAULT 'envoyee'
                    CHECK (statut IN ('envoyee', 'en_cours', 'terminee', 'expiree', 'annulee')),
    demarre_le      TIMESTAMPTZ,                   -- depart du chrono, fait foi cote serveur
    termine_le      TIMESTAMPTZ,
    consentement_le TIMESTAMPTZ,                   -- horodatage de l'information RGPD
    purge_apres     DATE NOT NULL                  -- suppression automatique des donnees
);

CREATE INDEX IF NOT EXISTS idx_invitation_token  ON invitation(token);
CREATE INDEX IF NOT EXISTS idx_invitation_statut ON invitation(statut);
CREATE INDEX IF NOT EXISTS idx_invitation_purge  ON invitation(purge_apres);

-- ------------------------------------------------------------
-- 5. Reponses : une ligne par option cochee
--    Sauvegarde au fil de l'eau : si le navigateur ferme, rien n'est perdu.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reponse (
    id              SERIAL PRIMARY KEY,
    invitation_id   INT  NOT NULL REFERENCES invitation(id) ON DELETE CASCADE,
    question_id     INT  NOT NULL REFERENCES question(id),
    option_id       INT  NOT NULL REFERENCES option_reponse(id),
    repondu_le      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (invitation_id, option_id)
);

CREATE INDEX IF NOT EXISTS idx_reponse_invitation ON reponse(invitation_id);

-- ------------------------------------------------------------
-- 6. Resultats calcules
--    detail : pour un test technique, le detail question par question
--             pour un positionnement, les totaux par dimension
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resultat (
    id                  SERIAL PRIMARY KEY,
    invitation_id       INT  NOT NULL UNIQUE REFERENCES invitation(id) ON DELETE CASCADE,
    score               INT,                       -- technique uniquement
    total_points        INT,
    pourcentage         NUMERIC(5,2),
    duree_secondes      INT,
    nb_vigilances       INT,                       -- positionnement, partie 2
    detail              JSONB NOT NULL,
    calcule_le          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 7. Journal d'acces (tracabilite RGPD)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal (
    id              SERIAL PRIMARY KEY,
    invitation_id   INT REFERENCES invitation(id) ON DELETE CASCADE,
    evenement       TEXT NOT NULL,                 -- ouverture, demarrage, soumission, expiration, purge
    detail          TEXT,
    horodatage      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Purge RGPD
-- Implementee dans rgpd.py et db.anonymiser() : declenchee au demarrage du
-- serveur, une fois par jour a l'ouverture du back-office, ou a la demande
-- depuis /admin/rgpd. Requete equivalente, pour memoire :
-- ============================================================
-- UPDATE invitation
--    SET candidat_nom = NULL, candidat_email = NULL, poste_vise = NULL,
--        token = 'purge_' || id
--  WHERE purge_apres < CURRENT_DATE;
