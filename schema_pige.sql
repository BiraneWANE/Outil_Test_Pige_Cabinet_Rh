-- ============================================================
-- Pige des offres d'emploi
-- A executer apres schema.sql. Cree automatiquement au premier
-- usage par pige.py : ce fichier sert de reference.
--
-- Aucune donnee personnelle de candidat ici : ce sont des
-- annonces publiees par des entreprises. Le seul cas limite est
-- le contact nomme parfois present dans une annonce, isole dans
-- sa propre colonne pour pouvoir etre efface a la demande.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Les annonces retenues
--    Une ligne par offre distincte, toutes sources confondues.
--    L'empreinte est la cle de dedoublonnage : deux annonces qui
--    la partagent sont considerees comme la meme offre, qu'elles
--    viennent de France Travail ou d'Adzuna.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS annonce (
    id                SERIAL PRIMARY KEY,
    empreinte         TEXT NOT NULL UNIQUE,
    partie            INT  NOT NULL CHECK (partie IN (1, 2)),
    metier            TEXT NOT NULL
                      CHECK (metier IN ('controle_gestion', 'comptabilite', 'paie')),
    intitule          TEXT NOT NULL,
    entreprise        TEXT,
    entreprise_cle    TEXT,          -- nom normalise, sert au regroupement
    commune           TEXT,
    code_postal       TEXT,
    departement       TEXT,
    type_contrat      TEXT,
    url               TEXT,
    contact_nom       TEXT,          -- rare ; efface a la demande
    publiee_le        DATE,          -- date annoncee par la source

    -- suivi dans le temps : c'est ce qui fait la pige
    vue_le_premier    DATE NOT NULL DEFAULT CURRENT_DATE,
    vue_le_dernier    DATE NOT NULL DEFAULT CURRENT_DATE,
    nb_jours_vue      INT  NOT NULL DEFAULT 1,
    nb_reparutions    INT  NOT NULL DEFAULT 0,
    en_ligne          BOOLEAN NOT NULL DEFAULT TRUE,
    sources           TEXT NOT NULL DEFAULT '',   -- 'france_travail', ou les deux
    cree_le           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_annonce_partie     ON annonce(partie);
CREATE INDEX IF NOT EXISTS idx_annonce_en_ligne   ON annonce(en_ligne);
CREATE INDEX IF NOT EXISTS idx_annonce_entreprise ON annonce(entreprise_cle);
CREATE INDEX IF NOT EXISTS idx_annonce_premier    ON annonce(vue_le_premier);

-- ------------------------------------------------------------
-- 2. Les observations quotidiennes
--    Une ligne par annonce et par jour ou elle a ete revue.
--    Sans cette table, on a une photographie ; avec elle, on sait
--    qu'une annonce traine depuis six semaines.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observation (
    id          SERIAL PRIMARY KEY,
    annonce_id  INT  NOT NULL REFERENCES annonce(id) ON DELETE CASCADE,
    jour        DATE NOT NULL DEFAULT CURRENT_DATE,
    source      TEXT NOT NULL,
    UNIQUE (annonce_id, jour, source)
);

CREATE INDEX IF NOT EXISTS idx_observation_jour ON observation(jour);

-- ------------------------------------------------------------
-- 3. Le journal des collectes
--    Pour savoir si la collecte du jour a bien tourne, et pourquoi
--    elle a echoue le cas echeant.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS collecte (
    id            SERIAL PRIMARY KEY,
    lancee_le     TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminee_le   TIMESTAMPTZ,
    statut        TEXT NOT NULL DEFAULT 'en_cours'
                  CHECK (statut IN ('en_cours', 'terminee', 'echouee')),
    nb_recues     INT NOT NULL DEFAULT 0,
    nb_nouvelles  INT NOT NULL DEFAULT 0,
    nb_revues     INT NOT NULL DEFAULT 0,
    nb_reparues   INT NOT NULL DEFAULT 0,
    nb_retirees   INT NOT NULL DEFAULT 0,
    detail        TEXT
);

CREATE INDEX IF NOT EXISTS idx_collecte_lancee ON collecte(lancee_le);

-- ------------------------------------------------------------
-- 4. Vue de travail : une ligne par annonce, avec son anciennete
--    L'anciennete est calculee a la lecture : elle change tous les
--    jours sans qu'on ait rien a recalculer.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_prospects AS
SELECT
    a.*,
    (CURRENT_DATE - COALESCE(a.publiee_le, a.vue_le_premier)) AS anciennete_jours,
    (CURRENT_DATE - a.vue_le_dernier)                          AS jours_sans_revoir,
    (SELECT count(*) FROM annonce b
      WHERE b.entreprise_cle = a.entreprise_cle AND b.en_ligne)  AS postes_ouverts_entreprise
FROM annonce a;
