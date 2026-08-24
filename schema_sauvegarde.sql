-- ============================================================
-- Sauvegarde de la base
-- A executer apres schema.sql et schema_analyse.sql.
-- Ces tables sont creees automatiquement au premier usage par
-- sauvegarde.py : ce fichier sert de reference et permet de les
-- recreer a la main si besoin.
-- ============================================================

-- ------------------------------------------------------------
-- Copies automatiques.
-- Une archive complete par jour, conservee un mois glissant.
-- Elle protege d'une fausse manoeuvre ou d'une suppression
-- accidentelle. Elle ne protege PAS de la disparition de
-- l'hebergeur de la base, puisqu'elle vit dans cette meme base :
-- c'est le telechargement depuis le back-office qui joue ce role.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sauvegarde (
    id          SERIAL PRIMARY KEY,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now(),
    octets      BIGINT NOT NULL,
    nb_lignes   INT NOT NULL,
    contenu     BYTEA NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sauvegarde_cree ON sauvegarde(cree_le);

-- ------------------------------------------------------------
-- Journal des telechargements.
-- Sert a rappeler au recruteur quand la derniere copie est
-- reellement sortie des serveurs. C'est la seule qui protege
-- vraiment.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sauvegarde_telechargement (
    id            SERIAL PRIMARY KEY,
    telecharge_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    utilisateur   TEXT,
    octets        BIGINT NOT NULL
);
