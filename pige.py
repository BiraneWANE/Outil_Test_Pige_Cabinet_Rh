"""
Pige des offres d'emploi : collecte, historisation, signaux.

Ce que fait ce module
---------------------
Une fois par jour, il interroge deux sources d'annonces sur deux
perimetres, range ce qu'il trouve dans la base, et note que chaque
annonce etait encore en ligne ce jour-la.

Cette derniere phrase est tout l'interet du dispositif. Une collecte
isolee donne une photographie du marche, ce qui n'a aucune valeur
commerciale. C'est la repetition quotidienne qui permet de dire qu'une
annonce traine depuis six semaines, ou qu'elle a disparu puis est
revenue : deux signaux qui designent une entreprise en difficulte de
recrutement, donc un prospect a appeler.

Les deux perimetres
-------------------
  Partie 1 : controle de gestion, toute l'Ile-de-France.
  Partie 2 : comptabilite et paie, Malakoff et 10 km autour.

Les deux sources
----------------
  France Travail, API Offres d'emploi v2, source principale.
  Adzuna, agregateur, pour rattraper les offres publiees uniquement
  sur des jobboards prives.

Aucune bibliotheque supplementaire n'est necessaire : les appels
passent par urllib, fourni avec Python. Une dependance de moins a
installer sur l'hebergeur, et une de moins a maintenir.
"""
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from hashlib import sha1

import db

ICI = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# Perimetres
# ------------------------------------------------------------------

DEPARTEMENTS_IDF = "75,77,78,91,92,93,94,95"
COMMUNE_PARTIE_2 = os.environ.get("PIGE_COMMUNE", "92046")   # Malakoff
DISTANCE_PARTIE_2 = int(os.environ.get("PIGE_DISTANCE", "10"))

# Le code ROME du gestionnaire de paie n'est pas etabli : selon les
# annonces il apparait en comptabilite ou en assistanat RH. On
# interroge les deux et on filtre sur les mots du metier. A trancher
# sur les resultats reels, pas sur la documentation.
MOTS_PAIE = ("paie", "paye", "payroll", "bulletin")

RECHERCHES = [
    # partie, metier, code ROME, perimetre
    (1, "controle_gestion", "M1204", "idf"),
    (2, "comptabilite",     "M1203", "malakoff"),
    (2, "paie",             "M1203", "malakoff"),
    (2, "paie",             "M1501", "malakoff"),
]

MOTS_CLES_ADZUNA = {
    "controle_gestion": "contrôle de gestion",
    "comptabilite":     "comptable",
    "paie":             "gestionnaire de paie",
}

PAGE_FRANCE_TRAVAIL = 150     # maximum accepte par l'API
PAUSE = 0.4                   # entre deux appels, par courtoisie

_tables_pretes = False
_dernier_passage = None
_jeton = {"valeur": None, "expire": 0}


# ==================================================================
# Preparation
# ==================================================================

def _assurer_tables():
    """Cree les tables au premier usage plutot que par une migration
    a lancer a la main : une etape manuelle oubliee, c'est une
    collecte qui ne tourne pas."""
    global _tables_pretes
    if _tables_pretes:
        return
    with open(os.path.join(ICI, "schema_pige.sql"), encoding="utf-8") as f:
        script = f.read()
    with db.curseur() as cur:
        cur.execute(script)
    _tables_pretes = True


def configuree():
    """Vrai si au moins une source est utilisable."""
    return bool(os.environ.get("FT_CLIENT_ID")) or bool(os.environ.get("ADZUNA_APP_ID"))


# ==================================================================
# Normalisation
# ==================================================================

def _sans_accent(texte):
    if not texte:
        return ""
    forme = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in forme if not unicodedata.combining(c))


FORMES_JURIDIQUES = (
    "sas", "sasu", "sarl", "eurl", "sa", "sci", "scp", "selarl", "selas",
    "snc", "gie", "association", "cabinet", "groupe", "france", "holding",
)


def cle_entreprise(nom):
    """
    Ramene une raison sociale a une cle stable.

    « KPMG France », « Cabinet KPMG » et « KPMG S.A.S. » doivent se
    regrouper, sinon le classement des entreprises les plus actives
    ne veut rien dire.
    """
    if not nom:
        return ""
    t = _sans_accent(nom).lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    # Les lettres isolees viennent des sigles pointes : « KPMG S.A.S. »
    # devient « kpmg s a s », qui ne doit pas differer de « kpmg ».
    mots = [m for m in t.split() if len(m) > 1 and m not in FORMES_JURIDIQUES]
    return " ".join(mots) or _sans_accent(nom).lower().strip()


def _mots_clefs_intitule(intitule):
    """L'intitule reduit a ses mots significatifs, pour comparer
    « Comptable general H/F » et « comptable général (h/f) »."""
    t = _sans_accent(intitule or "").lower()
    t = re.sub(r"\b(h\s*/?\s*f|f\s*/?\s*h|m\s*/?\s*f|cdi|cdd)\b", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return " ".join(sorted(set(m for m in t.split() if len(m) > 2)))


def empreinte(annonce):
    """
    Cle de dedoublonnage.

    Deux annonces se valent si elles portent sur la meme entreprise,
    le meme poste et la meme commune. On ne compare pas les
    identifiants des sources : ils different par construction, c'est
    justement le probleme a resoudre.
    """
    morceaux = (
        cle_entreprise(annonce.get("entreprise")),
        _mots_clefs_intitule(annonce.get("intitule")),
        _sans_accent(annonce.get("commune") or "").lower().strip(),
    )
    return sha1("|".join(morceaux).encode("utf-8")).hexdigest()[:20]


def _date(valeur):
    """Accepte les formats renvoyes par les deux sources."""
    if not valeur:
        return None
    texte = str(valeur)[:10]
    try:
        return datetime.strptime(texte, "%Y-%m-%d").date()
    except ValueError:
        return None


# ==================================================================
# Appels reseau
# ==================================================================

def _lire(url, entetes=None, donnees=None, delai=25):
    requete = urllib.request.Request(url, data=donnees, headers=entetes or {})
    with urllib.request.urlopen(requete, timeout=delai) as reponse:
        return reponse.status, reponse.read().decode("utf-8")


def _jeton_france_travail():
    """
    Jeton OAuth2, garde en memoire jusqu'a son expiration.

    Le redemander a chaque appel fonctionnerait, mais multiplierait
    par deux le nombre de requetes et finirait par declencher une
    limite de debit.
    """
    if _jeton["valeur"] and time.time() < _jeton["expire"]:
        return _jeton["valeur"]

    identifiant = os.environ.get("FT_CLIENT_ID")
    secret = os.environ.get("FT_CLIENT_SECRET")
    if not identifiant or not secret:
        raise RuntimeError("FT_CLIENT_ID ou FT_CLIENT_SECRET n'est pas defini.")

    url = ("https://entreprise.francetravail.fr/connexion/oauth2/access_token"
           "?realm=%2Fpartenaire")
    corps = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": identifiant,
        "client_secret": secret,
        "scope": "api_offresdemploiv2 o2dsoffre",
    }).encode("utf-8")

    _, texte = _lire(url, {"Content-Type": "application/x-www-form-urlencoded"}, corps)
    reponse = json.loads(texte)
    _jeton["valeur"] = reponse["access_token"]
    _jeton["expire"] = time.time() + int(reponse.get("expires_in", 1200)) - 60
    return _jeton["valeur"]


def _appeler_france_travail(parametres, debut, fin):
    jeton = _jeton_france_travail()
    url = ("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?"
           + urllib.parse.urlencode(dict(parametres, range=f"{debut}-{fin}")))
    statut, texte = _lire(url, {"Authorization": f"Bearer {jeton}",
                                "Accept": "application/json"})
    if statut == 204 or not texte.strip():
        return []
    return json.loads(texte).get("resultats", [])


def _appeler_adzuna(mots, ou, distance, page):
    identifiant = os.environ.get("ADZUNA_APP_ID")
    cle = os.environ.get("ADZUNA_APP_KEY")
    if not identifiant or not cle:
        raise RuntimeError("ADZUNA_APP_ID ou ADZUNA_APP_KEY n'est pas defini.")

    parametres = {
        "app_id": identifiant,
        "app_key": cle,
        "results_per_page": 50,
        "what": mots,
        "where": ou,
        "content-type": "application/json",
    }
    if distance:
        parametres["distance"] = distance
    url = (f"https://api.adzuna.com/v1/api/jobs/fr/search/{page}?"
           + urllib.parse.urlencode(parametres))
    _, texte = _lire(url)
    return json.loads(texte).get("results", [])


# ==================================================================
# Traduction des reponses dans un format commun
# ==================================================================

def convertir_france_travail(offre, partie, metier):
    lieu = offre.get("lieuTravail") or {}
    entreprise = offre.get("entreprise") or {}
    origine = offre.get("origineOffre") or {}
    contact = offre.get("contact") or {}
    code_postal = (lieu.get("codePostal") or "").strip()
    return {
        "partie": partie,
        "metier": metier,
        "source": "france_travail",
        "intitule": (offre.get("intitule") or "").strip(),
        "entreprise": (entreprise.get("nom") or "").strip() or None,
        "commune": (lieu.get("libelle") or "").split(" - ")[-1].strip() or None,
        "code_postal": code_postal or None,
        "departement": code_postal[:2] or None,
        "type_contrat": offre.get("typeContratLibelle") or offre.get("typeContrat"),
        "url": origine.get("urlOrigine"),
        "contact_nom": (contact.get("nom") or "").strip() or None,
        "publiee_le": _date(offre.get("dateCreation")),
    }


def convertir_adzuna(offre, partie, metier):
    lieu = offre.get("location") or {}
    zones = lieu.get("area") or []
    societe = offre.get("company") or {}
    return {
        "partie": partie,
        "metier": metier,
        "source": "adzuna",
        "intitule": (offre.get("title") or "").strip(),
        "entreprise": (societe.get("display_name") or "").strip() or None,
        "commune": (zones[-1] if zones else lieu.get("display_name") or "").strip() or None,
        "code_postal": None,
        "departement": None,
        "type_contrat": offre.get("contract_type"),
        "url": offre.get("redirect_url"),
        "contact_nom": None,
        "publiee_le": _date(offre.get("created")),
    }


def concerne_la_paie(annonce):
    """Filtre de rattrapage : les codes ROME melangent paie et
    comptabilite, l'intitule tranche mieux qu'eux."""
    texte = _sans_accent(annonce.get("intitule") or "").lower()
    return any(mot in texte for mot in MOTS_PAIE)


# ==================================================================
# Collecte
# ==================================================================

def _recherches_france_travail():
    for partie, metier, rome, perimetre in RECHERCHES:
        parametres = {"codeROME": rome, "sort": 1}
        if perimetre == "idf":
            parametres["departement"] = DEPARTEMENTS_IDF
        else:
            parametres["commune"] = COMMUNE_PARTIE_2
            parametres["distance"] = DISTANCE_PARTIE_2
        yield partie, metier, parametres


def collecter_france_travail(journal=None):
    annonces = []
    for partie, metier, parametres in _recherches_france_travail():
        debut = 0
        while debut < 1000:
            fin = debut + PAGE_FRANCE_TRAVAIL - 1
            try:
                offres = _appeler_france_travail(parametres, debut, fin)
            except urllib.error.HTTPError as e:
                if e.code == 429:      # limite de debit : on souffle
                    time.sleep(2)
                    continue
                if journal is not None:
                    journal.append(f"france_travail {metier} : erreur {e.code}")
                break
            if not offres:
                break
            for offre in offres:
                a = convertir_france_travail(offre, partie, metier)
                if metier == "paie" and not concerne_la_paie(a):
                    continue
                if a["intitule"]:
                    annonces.append(a)
            if len(offres) < PAGE_FRANCE_TRAVAIL:
                break
            debut += PAGE_FRANCE_TRAVAIL
            time.sleep(PAUSE)
    return annonces


def collecter_adzuna(journal=None):
    """Adzuna cherche par mots-cles, pas par code ROME : les deux
    recherches paie de France Travail n'en font donc qu'une ici."""
    annonces = []
    deja = set()
    for partie, metier, _, perimetre in RECHERCHES:
        if (metier, perimetre) in deja:
            continue
        deja.add((metier, perimetre))
        ou = "Île-de-France" if perimetre == "idf" else "Malakoff"
        distance = None if perimetre == "idf" else DISTANCE_PARTIE_2
        for page in range(1, 5):
            try:
                offres = _appeler_adzuna(MOTS_CLES_ADZUNA[metier], ou, distance, page)
            except urllib.error.HTTPError as e:
                if journal is not None:
                    journal.append(f"adzuna {metier} : erreur {e.code}")
                break
            if not offres:
                break
            for offre in offres:
                a = convertir_adzuna(offre, partie, metier)
                if metier == "paie" and not concerne_la_paie(a):
                    continue
                if a["intitule"]:
                    annonces.append(a)
            if len(offres) < 50:
                break
            time.sleep(PAUSE)
    return annonces


# ==================================================================
# Rangement en base
# ==================================================================

def enregistrer(annonces, aujourdhui=None):
    """
    Range une collecte et rend son resume.

    Trois cas par annonce : inconnue, deja vue hier, ou revenue apres
    une absence. Le troisieme est le signal le plus interessant de
    toute la pige, il est donc compte a part.
    """
    _assurer_tables()
    jour = aujourdhui or date.today()
    resume = {"recues": len(annonces), "nouvelles": 0, "revues": 0, "reparues": 0}

    # Une meme offre peut arriver deux fois dans la meme collecte,
    # par deux sources ou deux codes ROME : on fusionne d'abord.
    groupees = {}
    for a in annonces:
        cle = empreinte(a)
        if cle in groupees:
            groupees[cle]["sources"].add(a["source"])
        else:
            a = dict(a)
            a["sources"] = {a.pop("source")}
            groupees[cle] = a

    with db.curseur() as cur:
        for cle, a in groupees.items():
            sources = ",".join(sorted(a["sources"]))
            cur.execute("SELECT id, en_ligne, vue_le_dernier, sources "
                        "FROM annonce WHERE empreinte = %s", (cle,))
            ligne = cur.fetchone()

            if ligne is None:
                cur.execute(
                    """
                    INSERT INTO annonce
                        (empreinte, partie, metier, intitule, entreprise,
                         entreprise_cle, commune, code_postal, departement,
                         type_contrat, url, contact_nom, publiee_le,
                         vue_le_premier, vue_le_dernier, sources)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (cle, a["partie"], a["metier"], a["intitule"], a["entreprise"],
                     cle_entreprise(a["entreprise"]), a["commune"], a["code_postal"],
                     a["departement"], a["type_contrat"], a["url"], a["contact_nom"],
                     a["publiee_le"], jour, jour, sources),
                )
                annonce_id = cur.fetchone()["id"]
                resume["nouvelles"] += 1
            else:
                annonce_id = ligne["id"]
                revenue = not ligne["en_ligne"]
                connues = {s for s in (ligne["sources"] or "").split(",") if s}
                toutes = ",".join(sorted(connues | a["sources"]))
                cur.execute(
                    """
                    UPDATE annonce
                       SET vue_le_dernier = %s,
                           en_ligne       = TRUE,
                           nb_jours_vue   = nb_jours_vue + CASE WHEN vue_le_dernier < %s THEN 1 ELSE 0 END,
                           nb_reparutions = nb_reparutions + %s,
                           sources        = %s,
                           url            = COALESCE(%s, url)
                     WHERE id = %s
                    """,
                    (jour, jour, 1 if revenue else 0, toutes, a["url"], annonce_id),
                )
                resume["revues"] += 1
                if revenue:
                    resume["reparues"] += 1

            for source in sorted(a["sources"]):
                cur.execute(
                    "INSERT INTO observation (annonce_id, jour, source) "
                    "VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (annonce_id, jour, source),
                )

    return resume


def marquer_retirees(aujourdhui=None):
    """Une annonce que la collecte du jour n'a pas revue est retiree.
    On ne la supprime pas : son historique reste, et si elle revient
    on saura que c'est une reparution."""
    _assurer_tables()
    jour = aujourdhui or date.today()
    with db.curseur() as cur:
        cur.execute("UPDATE annonce SET en_ligne = FALSE "
                    " WHERE en_ligne AND vue_le_dernier < %s", (jour,))
        return cur.rowcount


# ==================================================================
# Orchestration
# ==================================================================

def collecter(aujourdhui=None):
    """Une collecte complete : les deux sources, les deux parties."""
    _assurer_tables()
    journal = []
    with db.curseur() as cur:
        cur.execute("INSERT INTO collecte DEFAULT VALUES RETURNING id")
        collecte_id = cur.fetchone()["id"]

    try:
        annonces = []
        if os.environ.get("FT_CLIENT_ID"):
            annonces += collecter_france_travail(journal)
        else:
            journal.append("france_travail : pas de cle, source ignoree")
        if os.environ.get("ADZUNA_APP_ID"):
            annonces += collecter_adzuna(journal)
        else:
            journal.append("adzuna : pas de cle, source ignoree")

        resume = enregistrer(annonces, aujourdhui)
        resume["retirees"] = marquer_retirees(aujourdhui)
        statut = "terminee"
    except Exception as e:                       # la collecte ne doit jamais
        resume = {"recues": 0, "nouvelles": 0,   # faire tomber le serveur
                  "revues": 0, "reparues": 0, "retirees": 0}
        journal.append(f"echec : {e}")
        statut = "echouee"

    with db.curseur() as cur:
        cur.execute(
            """
            UPDATE collecte
               SET terminee_le = now(), statut = %s, nb_recues = %s,
                   nb_nouvelles = %s, nb_revues = %s, nb_reparues = %s,
                   nb_retirees = %s, detail = %s
             WHERE id = %s
            """,
            (statut, resume["recues"], resume["nouvelles"], resume["revues"],
             resume["reparues"], resume["retirees"],
             " | ".join(journal) or None, collecte_id),
        )
    resume["statut"] = statut
    resume["journal"] = journal
    return resume


def _collecte_faite_aujourdhui():
    with db.curseur() as cur:
        cur.execute("SELECT 1 FROM collecte "
                    " WHERE lancee_le::date = CURRENT_DATE AND statut = 'terminee' "
                    " LIMIT 1")
        return cur.fetchone() is not None


def collecter_si_besoin(aujourdhui=None):
    """
    Une collecte par jour, pas davantage.

    Meme dispositif que la purge RGPD et la sauvegarde : un marqueur
    en memoire evite d'interroger la base a chaque visite, un controle
    en base evite de recollecter a chaque redemarrage du serveur.
    """
    global _dernier_passage
    if not configuree():
        return None
    _assurer_tables()
    jour = aujourdhui or date.today()
    if _dernier_passage == jour:
        return None
    _dernier_passage = jour
    if _collecte_faite_aujourdhui():
        return None
    return collecter(aujourdhui)


# ==================================================================
# Lecture pour le back-office
# ==================================================================

TRIS = {
    "anciennete": "anciennete_jours DESC NULLS LAST, nb_reparutions DESC",
    "reparutions": "nb_reparutions DESC, anciennete_jours DESC NULLS LAST",
    "entreprise": "postes_ouverts_entreprise DESC, entreprise_cle, anciennete_jours DESC",
    "recentes": "vue_le_premier DESC, id DESC",
}


def prospects(partie=None, metier=None, en_ligne=True, anciennete_min=0,
              tri="anciennete", limite=300):
    _assurer_tables()
    conditions, valeurs = [], []
    if partie:
        conditions.append("partie = %s");            valeurs.append(partie)
    if metier:
        conditions.append("metier = %s");            valeurs.append(metier)
    if en_ligne:
        conditions.append("en_ligne")
    if anciennete_min:
        conditions.append("(CURRENT_DATE - COALESCE(publiee_le, vue_le_premier)) >= %s")
        valeurs.append(anciennete_min)
    ou = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    ordre = TRIS.get(tri, TRIS["anciennete"])
    with db.curseur() as cur:
        cur.execute(f"SELECT * FROM v_prospects{ou} ORDER BY {ordre} LIMIT %s",
                    valeurs + [limite])
        return cur.fetchall()


def entreprises_actives(limite=20):
    """Les entreprises qui publient le plus, tous postes confondus."""
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT entreprise_cle,
                   max(entreprise)                     AS entreprise,
                   count(*)                            AS postes,
                   count(*) FILTER (WHERE en_ligne)    AS postes_en_ligne,
                   max(CURRENT_DATE - vue_le_premier)  AS plus_ancienne,
                   sum(nb_reparutions)                 AS reparutions,
                   string_agg(DISTINCT commune, ', ')  AS communes
              FROM annonce
             WHERE entreprise_cle <> ''
             GROUP BY entreprise_cle
             ORDER BY postes_en_ligne DESC, postes DESC
             LIMIT %s
            """,
            (limite,),
        )
        return cur.fetchall()


def etat():
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT count(*)                                   AS total,
                   count(*) FILTER (WHERE en_ligne)           AS en_ligne,
                   count(*) FILTER (WHERE partie = 1)         AS partie_1,
                   count(*) FILTER (WHERE partie = 2)         AS partie_2,
                   count(*) FILTER (WHERE nb_reparutions > 0) AS reparues,
                   count(*) FILTER (WHERE en_ligne AND
                        (CURRENT_DATE - COALESCE(publiee_le, vue_le_premier)) >= 30)
                                                              AS anciennes
              FROM annonce
            """
        )
        base = cur.fetchone()
        cur.execute("SELECT count(DISTINCT entreprise_cle) AS n FROM annonce "
                    " WHERE entreprise_cle <> ''")
        base["entreprises"] = cur.fetchone()["n"]
        cur.execute("SELECT * FROM collecte ORDER BY lancee_le DESC LIMIT 1")
        base["derniere_collecte"] = cur.fetchone()
        cur.execute("SELECT count(DISTINCT jour) AS n FROM observation")
        base["jours_historises"] = cur.fetchone()["n"]
    base["configuree"] = configuree()
    return base


def journal_collectes(limite=10):
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute("SELECT * FROM collecte ORDER BY lancee_le DESC LIMIT %s",
                    (limite,))
        return cur.fetchall()


def oublier_contact(annonce_id):
    """Efface le nom de contact d'une annonce, sur demande."""
    with db.curseur() as cur:
        cur.execute("UPDATE annonce SET contact_nom = NULL WHERE id = %s",
                    (annonce_id,))
        return cur.rowcount
