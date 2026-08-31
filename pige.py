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
  Partie 1 : controle de gestion, missions courtes uniquement
             (interim, CDD, management de transition), toute la France.
  Partie 2 : comptabilite et paie, cabinet comme entreprise,
             Malakoff et 10 km autour, tous types de contrat.

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

COMMUNE_PARTIE_2 = os.environ.get("PIGE_COMMUNE", "92046")   # Malakoff
DISTANCE_PARTIE_2 = int(os.environ.get("PIGE_DISTANCE", "10"))

# Partie 1 : uniquement des missions courtes, dans toute la France.
# Codes de contrat France Travail : CDD, mission d'interim, CDD
# d'insertion, travail temporaire d'insertion. Le CDI est ecarte.
CONTRATS_COURTS = "CDD,MIS,DDI,TTI"

# Le management de transition n'a pas de code de contrat a lui : il se
# publie tantot en CDD cadre, tantot en mission. Ces mots servent de
# rattrapage quand le contrat annonce ne dit rien d'utile.
MOTS_MISSION = ("transition", "interim", "mission", "temporaire",
                "remplacement", "vacation")

CONTRATS_PERMANENTS = ("cdi", "permanent", "indeterminee", "duree indeterminee")

# Le code ROME du gestionnaire de paie n'est pas etabli : selon les
# annonces il apparait en comptabilite ou en assistanat RH. On
# interroge les deux et on filtre sur les mots du metier. A trancher
# sur les resultats reels, pas sur la documentation.
MOTS_PAIE = ("paie", "paye", "payroll", "bulletin")

# ------------------------------------------------------------------
# Ce que le cabinet ne veut PAS voir
# ------------------------------------------------------------------
# Les cabinets de recrutement et les agences d'interim publient
# beaucoup, mais ce ne sont pas des prospects : ce sont des confreres.
# Ils recrutent pour un client dont ils taisent le nom, il n'y a donc
# personne a demarcher derriere l'annonce.
# Racines cherchees N'IMPORTE OU dans la raison sociale. C'est ce qui
# attrape « Comptalents » ou « Interaction Interim » sans avoir a les
# lister un par un : une liste finie sera toujours en retard.
RACINES_INTERMEDIAIRE = (
    "interim", "intérim", "recrut", "talent", "staffing", "sourcing",
    "headhunt", "chasseur de tete", "travail temporaire",
    "agence d emploi", "portage salarial", "rh solutions",
    "conseil en rh", "consulting rh", "cabinet rh", "solutions rh",
)

# Mots cherches comme mots entiers : trop courants pour etre cherches
# au milieu d'un nom. « job » attraperait « Jobin », « emploi »
# attraperait « Emploi Store ».
# « conseil » et « consulting » ne figurent pas ici volontairement :
# beaucoup de cabinets d'expertise comptable s'appellent « X Conseil ».
# Ce sont justement des prospects.
MOTS_INTERMEDIAIRE = (
    "job", "jobs", "emploi", "emplois", "placement", "interimaire",
    "esn", "rh",
)

# Enseignes reconnues a leur nom complet, quand rien dans le nom ne
# trahit le metier. Comparaison sur le nom normalise, pas en sous-chaine :
# « LTd » ne doit pas attraper toutes les societes finissant par Ltd.
ENSEIGNES_EXACTES = (
    "ltd", "collective work", "expertnet technologies", "expertnet",
    "comptalents", "choisir le service public",
)

# Les enseignes connues ne contiennent pas toujours un mot revelateur.
ENSEIGNES_INTERMEDIAIRE = (
    "adecco", "manpower", "randstad", "expectra", "proman", "synergie",
    "crit", "start people", "actual", "adequat", "temporis", "supplay",
    "leader", "abalone", "partnaire", "menway", "triangle", "interaction",
    "sofitex", "ergalis", "domino", "gi group", "kelly", "gitec",
    "hays", "michael page", "page personnel", "robert half", "fed finance",
    "fed group", "walters people", "robert walters", "lhh", "morgan philips",
    "approach people", "vidal associates", "winsearch", "adsearch",
    "lynx rh", "aquila rh", "nextep", "tertialis", "sirh", "silkhom",
    "fab group", "vitalis", "kolibri", "opensourcing", "talentskill",
    "sbc interim", "up skills", "harry hope", "aec partners", "spring",
    "cerba", "groupement demploi", "gerpa",
)

# ------------------------------------------------------------------
# Le secteur public
# ------------------------------------------------------------------
# Une administration ne choisit pas librement son prestataire : au-dela
# d'un certain montant elle doit passer par un marche public, et elle
# reference souvent deux ou trois cabinets pour plusieurs annees. Un
# courriel de prospection n'y sert a rien, personne ne peut decider.
# Ces annonces sont donc du bruit, et elles ecrasent les entreprises
# reelles dans le classement.
SECTEUR_PUBLIC_RACINES = (
    "fonction publique", "ministere", "prefecture", "rectorat",
    "academie de", "mairie", "ville de", "commune de",
    "conseil departemental", "conseil regional", "conseil general",
    "communaute de communes", "communaute d agglomeration",
    "centre hospitalier", "hopitaux de", "assistance publique",
    "etablissement public", "syndicat mixte", "office public",
    "centre communal", "service departemental d incendie",
    "collectivite", "agence regionale de sante",
)

SECTEUR_PUBLIC_EXACTES = (
    "cnfpt", "cea", "aphp", "assistance hopitaux de paris", "cnrs",
    "inserm", "inrae", "inria", "onf", "ademe", "ars", "cpam", "caf",
    "urssaf", "msa", "ccas", "sdis", "france travail", "pole emploi",
    "education nationale", "armee de terre", "gendarmerie nationale",
)

# ------------------------------------------------------------------
# Anciennete au-dela de laquelle une annonce ne dit plus rien
# ------------------------------------------------------------------
# Jusqu'a trois mois, une annonce qui dure signale un recrutement qui
# peine : c'est le bon signal. Au-dela de quatre mois, c'est un vivier
# permanent laisse en ligne toute l'annee, ou une date de publication
# fausse. Dans les deux cas il n'y a plus de besoin a appeler.
ANCIENNETE_MAX = int(os.environ.get("PIGE_ANCIENNETE_MAX", "120"))

# ------------------------------------------------------------------
# Perimetre reel de la partie 2
# ------------------------------------------------------------------
# France Travail sait chercher « a 10 km de la commune 92046 ».
# Adzuna, non : il ignore le rayon des qu'il ne reconnait pas la ville
# et renvoie la France entiere. On verifie donc nous-memes, sur une
# liste de communes etablie une fois pour toutes.
COMMUNES_PARTIE_2 = {
    # Hauts-de-Seine
    "malakoff", "vanves", "montrouge", "chatillon", "clamart", "bagneux",
    "issy les moulineaux", "boulogne billancourt", "fontenay aux roses",
    "le plessis robinson", "sceaux", "bourg la reine", "antony",
    "chatenay malabry", "meudon", "sevres", "chaville", "ville d avray",
    "saint cloud", "suresnes", "levallois perret", "neuilly sur seine",
    "puteaux", "la garenne colombes", "clichy",
    # Val-de-Marne
    "cachan", "arcueil", "gentilly", "le kremlin bicetre", "villejuif",
    "l hay les roses", "fresnes", "chevilly larue", "ivry sur seine",
    "vitry sur seine", "rungis", "thiais", "charenton le pont",
    "saint maurice", "alfortville",
    # Essonne
    "verrieres le buisson", "massy", "wissous",
    # Paris intra-muros
    "paris",
}


def _commune_normalisee(nom):
    """
    Ramene « 92 - MALAKOFF », « Paris 14e Arrondissement » et
    « Issy-les-Moulineaux » a une forme comparable.
    """
    if not nom:
        return ""
    t = _sans_accent(nom).lower()
    t = re.sub(r"\b(\d+\s*(er|e|eme|ème)?\s*arrondissement|cedex|arrondissement)\b",
               " ", t)
    t = re.sub(r"[^a-z ]+", " ", t)
    return " ".join(t.split())

RECHERCHES = [
    {"partie": 1, "metier": "controle_gestion", "rome": "M1204",
     "zone": "france",   "contrats": CONTRATS_COURTS},
    {"partie": 2, "metier": "comptabilite",     "rome": "M1203",
     "zone": "malakoff", "contrats": None},
    {"partie": 2, "metier": "paie",             "rome": "M1203",
     "zone": "malakoff", "contrats": None},
    {"partie": 2, "metier": "paie",             "rome": "M1501",
     "zone": "malakoff", "contrats": None},
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

def _lire(url, entetes=None, donnees=None, delai=40):
    requete = urllib.request.Request(url, data=donnees, headers=entetes or {})
    with urllib.request.urlopen(requete, timeout=delai) as reponse:
        return reponse.status, reponse.read().decode("utf-8")


URL_JETON = ("https://entreprise.francetravail.fr/connexion/oauth2/access_token"
             "?realm=%2Fpartenaire")


def _perimetres_possibles(identifiant):
    """
    France Travail a change la forme du perimetre demande au fil des
    versions : certaines applications exigent encore le prefixe
    application_<identifiant>, d'autres non. Plutot que de parier, on
    essaie les formes connues et on garde celle qui repond.
    """
    return [
        "api_offresdemploiv2 o2dsoffre",
        f"application_{identifiant} api_offresdemploiv2 o2dsoffre",
        f"application_{identifiant} o2dsoffre api_offresdemploiv2",
        "o2dsoffre api_offresdemploiv2",
    ]


def _jeton_france_travail():
    """
    Jeton OAuth2, garde en memoire jusqu'a son expiration.

    Le redemander a chaque appel fonctionnerait, mais multiplierait
    par deux le nombre de requetes et finirait par declencher une
    limite de debit.
    """
    if _jeton["valeur"] and time.time() < _jeton["expire"]:
        return _jeton["valeur"]

    # Les espaces en trop sont la premiere cause d'echec : une valeur
    # collee depuis un fichier tient souvent un retour a la ligne.
    identifiant = (os.environ.get("FT_CLIENT_ID") or "").strip()
    secret = (os.environ.get("FT_CLIENT_SECRET") or "").strip()
    if not identifiant or not secret:
        raise RuntimeError("FT_CLIENT_ID ou FT_CLIENT_SECRET n'est pas defini.")

    echecs = []
    for perimetre in _perimetres_possibles(identifiant):
        corps = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": identifiant,
            "client_secret": secret,
            "scope": perimetre,
        }).encode("utf-8")
        try:
            _, texte = _lire(
                URL_JETON,
                {"Content-Type": "application/x-www-form-urlencoded"},
                corps,
            )
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            echecs.append(f"[{perimetre}] {e.code} {detail}")
            continue
        except urllib.error.URLError as e:
            # Panne reseau ou serveur injoignable : inutile d'essayer
            # les autres perimetres, le probleme n'est pas la.
            raise RuntimeError(
                f"France Travail injoignable : {e.reason}") from None
        reponse = json.loads(texte)
        _jeton["valeur"] = reponse["access_token"]
        _jeton["expire"] = time.time() + int(reponse.get("expires_in", 1200)) - 60
        return _jeton["valeur"]

    raise RuntimeError(
        "France Travail refuse la demande de jeton. Reponses du serveur :\n  "
        + "\n  ".join(echecs)
    )


def _appeler_france_travail(parametres, debut, fin):
    jeton = _jeton_france_travail()
    url = ("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?"
           + urllib.parse.urlencode(dict(parametres, range=f"{debut}-{fin}")))
    statut, texte = _lire(url, {"Authorization": f"Bearer {jeton}",
                                "Accept": "application/json"})
    if statut == 204 or not texte.strip():
        return []
    return json.loads(texte).get("resultats", [])


def _appeler_adzuna(mots, ou, distance, page, missions_seules=False):
    identifiant = os.environ.get("ADZUNA_APP_ID")
    cle = os.environ.get("ADZUNA_APP_KEY")
    if not identifiant or not cle:
        raise RuntimeError("ADZUNA_APP_ID ou ADZUNA_APP_KEY n'est pas defini.")

    parametres = {
        "app_id": identifiant,
        "app_key": cle,
        "results_per_page": 50,
        "what": mots,
        "content-type": "application/json",
    }
    if ou:
        parametres["where"] = ou
    if distance:
        parametres["distance"] = distance
    if missions_seules:
        # Adzuna ne distingue que « permanent » et « contract » :
        # on demande le second, le tri fin se fait ensuite.
        parametres["contract"] = 1
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
        "contact_courriel": (contact.get("courriel") or "").strip().lower() or None,
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
        "contact_courriel": None,     # Adzuna n'en publie pas
        "publiee_le": _date(offre.get("created")),
    }


def concerne_la_paie(annonce):
    """Filtre de rattrapage : les codes ROME melangent paie et
    comptabilite, l'intitule tranche mieux qu'eux."""
    texte = _sans_accent(annonce.get("intitule") or "").lower()
    return any(mot in texte for mot in MOTS_PAIE)


def est_mission_courte(annonce):
    """
    Partie 1 : le cabinet ne pige que des missions courtes, interim,
    CDD et management de transition. Le CDI ne l'interesse pas.

    France Travail sait filtrer par type de contrat, mais Adzuna ne
    connait que « permanent » ou « contract », et le management de
    transition se publie parfois sans contrat clair. Ce controle
    s'applique donc aux deux sources, apres coup.
    """
    contrat = _sans_accent(annonce.get("type_contrat") or "").lower()
    intitule = _sans_accent(annonce.get("intitule") or "").lower()
    if any(p in contrat for p in CONTRATS_PERMANENTS):
        # Un poste annonce en CDI ne passe que s'il se decrit lui-meme
        # comme une mission : c'est le cas du management de transition.
        return any(m in intitule for m in MOTS_MISSION)
    return True


def est_intermediaire(annonce):
    """
    Cabinet de recrutement ou agence d'interim : un confrere, pas un
    prospect. L'annonce est conservee mais mise de cote, pour que le
    cabinet puisse verifier et rattraper une erreur de tri.
    """
    nom = _sans_accent(annonce.get("entreprise") or "").lower()
    if not nom:
        return False

    # 1. une enseigne connue, reconnue en sous-chaine
    if any(e in nom for e in ENSEIGNES_INTERMEDIAIRE):
        return True

    # 2. une racine du metier, n'importe ou dans le nom
    if any(r in nom for r in RACINES_INTERMEDIAIRE):
        return True

    # 3. un mot entier trop courant pour etre cherche en sous-chaine
    mots = set(re.sub(r"[^a-z0-9 ]+", " ", nom).split())
    if mots & set(MOTS_INTERMEDIAIRE):
        return True

    # 4. un nom entier de la liste, compare a l'identique
    return cle_entreprise(nom) in ENSEIGNES_EXACTES


def est_secteur_public(annonce):
    """Administration, collectivite, hopital public : passe par marche
    public, donc hors demarchage."""
    nom = _sans_accent(annonce.get("entreprise") or "").lower()
    if not nom:
        return False
    if any(r in nom for r in SECTEUR_PUBLIC_RACINES):
        return True
    return cle_entreprise(nom) in SECTEUR_PUBLIC_EXACTES


def trop_ancienne(annonce, aujourdhui=None):
    """Vrai au-dela de ANCIENNETE_MAX jours depuis la publication."""
    publiee = annonce.get("publiee_le") or annonce.get("vue_le_premier")
    if not publiee:
        return False
    if isinstance(publiee, datetime):
        publiee = publiee.date()
    jour = aujourdhui or date.today()
    return (jour - publiee).days > ANCIENNETE_MAX


def hors_perimetre_2(annonce):
    """Vrai si une annonce de la partie 2 n'est pas dans les 10 km."""
    if annonce.get("partie") != 2:
        return False
    code = (annonce.get("code_postal") or "").strip()
    if code[:2] in ("92", "94", "75"):
        return False
    commune = _commune_normalisee(annonce.get("commune"))
    if not commune:
        return True          # sans lieu, on ne peut pas garantir le rayon
    return not any(commune == c or commune.startswith(c + " ") or c in commune
                   for c in COMMUNES_PARTIE_2)


# ------------------------------------------------------------------
# Adresses de contact
# ------------------------------------------------------------------
# Une adresse generique ne designe personne : « contact@societe.fr »
# est une boite de l'entreprise, pas une donnee personnelle. Une
# adresse nominative, si. La distinction change tout, elle est donc
# faite a la collecte et affichee dans les exports.
PREFIXES_GENERIQUES = (
    "contact", "info", "infos", "accueil", "recrutement", "recrute",
    "rh", "drh", "job", "jobs", "emploi", "emplois", "candidature",
    "candidatures", "cv", "secretariat", "administration", "admin",
    "direction", "compta", "comptabilite", "paie", "social", "agence",
    "cabinet", "bonjour", "hello", "commercial", "service",
)

MOTIF_COURRIEL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)


def courriel_valide(adresse):
    return bool(adresse) and bool(MOTIF_COURRIEL.match(adresse.strip()))


def courriel_generique(adresse):
    """
    Vrai si l'adresse designe une fonction plutot qu'une personne.

    « recrutement@cabinet.fr » : oui. « marie.dupont@cabinet.fr » : non.
    Le doute profite a la prudence : tout ce qui ressemble a un
    prenom.nom est classe comme nominatif.
    """
    if not courriel_valide(adresse):
        return False
    local = _sans_accent(adresse.split("@")[0]).lower()
    propre = re.sub(r"[._-]+", " ", local).strip()
    mots = propre.split()
    if any(m in PREFIXES_GENERIQUES for m in mots):
        return True
    # prenom.nom, p.nom, prenomnom : on considere que c'est une personne
    return False


def motif_ecart(annonce, aujourdhui=None):
    """Rend la raison de mettre une annonce de cote, ou None."""
    if hors_perimetre_2(annonce):
        return "hors des 10 km autour de Malakoff"
    if est_intermediaire(annonce):
        return "cabinet de recrutement ou agence d'interim"
    if est_secteur_public(annonce):
        return "secteur public, passe par marche public"
    if trop_ancienne(annonce, aujourdhui):
        return f"en ligne depuis plus de {ANCIENNETE_MAX} jours"
    if not (annonce.get("entreprise") or "").strip():
        return "entreprise non nommee"
    return None


# ==================================================================
# Collecte
# ==================================================================

def _recherches_france_travail():
    for r in RECHERCHES:
        parametres = {"codeROME": r["rome"], "sort": 1}
        if r["zone"] == "malakoff":
            parametres["commune"] = COMMUNE_PARTIE_2
            parametres["distance"] = DISTANCE_PARTIE_2
        # zone « france » : aucun filtre geographique, l'API rend
        # l'ensemble du territoire.
        if r["contrats"]:
            parametres["typeContrat"] = r["contrats"]
        yield r["partie"], r["metier"], parametres


def collecter_france_travail(journal=None):
    annonces = []
    for partie, metier, parametres in _recherches_france_travail():
        zone = "toute la France" if "commune" not in parametres else "Malakoff 10 km"
        print(f"  France Travail | partie {partie} | {metier} | {zone} ...",
              flush=True)
        avant = len(annonces)
        debut = 0
        while debut < 3000:
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
                if partie == 1 and not est_mission_courte(a):
                    continue
                if a["intitule"]:
                    annonces.append(a)
            if len(offres) < PAGE_FRANCE_TRAVAIL:
                break
            debut += PAGE_FRANCE_TRAVAIL
            time.sleep(PAUSE)
        print(f"      {len(annonces) - avant} annonce(s)", flush=True)
    return annonces


def collecter_adzuna(journal=None):
    """Adzuna cherche par mots-cles, pas par code ROME : les deux
    recherches paie de France Travail n'en font donc qu'une ici."""
    annonces = []
    deja = set()
    for r in RECHERCHES:
        partie, metier, zone = r["partie"], r["metier"], r["zone"]
        if (metier, zone) in deja:
            continue
        deja.add((metier, zone))
        national = zone == "france"
        ou = None if national else "Malakoff"
        distance = None if national else DISTANCE_PARTIE_2
        print(f"  Adzuna | partie {partie} | {metier} | "
              f"{'toute la France' if national else 'Malakoff 10 km'} ...",
              flush=True)
        avant = len(annonces)
        for page in range(1, 5):
            try:
                offres = _appeler_adzuna(MOTS_CLES_ADZUNA[metier], ou, distance,
                                         page, missions_seules=national)
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
                if partie == 1 and not est_mission_courte(a):
                    continue
                if a["intitule"]:
                    annonces.append(a)
            if len(offres) < 50:
                break
            time.sleep(PAUSE)
        print(f"      {len(annonces) - avant} annonce(s)", flush=True)
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
    resume = {"recues": len(annonces), "nouvelles": 0, "revues": 0,
              "reparues": 0, "ecartees": 0}

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

            motif = motif_ecart(a)
            if motif:
                resume["ecartees"] += 1

            if ligne is None:
                cur.execute(
                    """
                    INSERT INTO annonce
                        (empreinte, partie, metier, intitule, entreprise,
                         entreprise_cle, commune, code_postal, departement,
                         type_contrat, url, contact_nom, publiee_le,
                         vue_le_premier, vue_le_dernier, sources,
                         ecartee, motif_ecart,
                         contact_courriel, courriel_generique)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s)
                    RETURNING id
                    """,
                    (cle, a["partie"], a["metier"], a["intitule"], a["entreprise"],
                     cle_entreprise(a["entreprise"]), a["commune"], a["code_postal"],
                     a["departement"], a["type_contrat"], a["url"], a["contact_nom"],
                     a["publiee_le"], jour, jour, sources,
                     motif is not None, motif,
                     a.get("contact_courriel"),
                     courriel_generique(a.get("contact_courriel"))),
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
                           url            = COALESCE(%s, url),
                           ecartee        = %s,
                           motif_ecart    = %s
                     WHERE id = %s
                    """,
                    (jour, jour, 1 if revenue else 0, toutes, a["url"],
                     motif is not None, motif, annonce_id),
                )
                resume["revues"] += 1
                if revenue:
                    resume["reparues"] += 1

            # L'adresse va au repertoire, pas seulement sur l'annonce :
            # une desinscription doit valoir pour toutes les offres de
            # la meme entreprise, aujourd'hui et plus tard.
            if not motif and a.get("contact_courriel"):
                enregistrer_contact(a)

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
        print("Collecte en cours. Comptez trois a cinq minutes.", flush=True)
        if os.environ.get("FT_CLIENT_ID"):
            annonces += collecter_france_travail(journal)
        else:
            journal.append("france_travail : pas de cle, source ignoree")
        if os.environ.get("ADZUNA_APP_ID"):
            annonces += collecter_adzuna(journal)
        else:
            journal.append("adzuna : pas de cle, source ignoree")

        print(f"  rangement de {len(annonces)} annonce(s) ...", flush=True)
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
              tri="anciennete", limite=300, ecartees=False):
    _assurer_tables()
    conditions, valeurs = [], []
    # Par defaut on ne montre que les vrais prospects : ni confreres,
    # ni annonces hors zone, ni entreprises anonymes.
    conditions.append("ecartee" if ecartees else "NOT ecartee")
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
             WHERE entreprise_cle <> '' AND NOT ecartee
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
                   count(*) FILTER (WHERE en_ligne AND NOT ecartee) AS en_ligne,
                   count(*) FILTER (WHERE ecartee)            AS ecartees,
                   count(*) FILTER (WHERE partie = 1 AND NOT ecartee) AS partie_1,
                   count(*) FILTER (WHERE partie = 2 AND NOT ecartee) AS partie_2,
                   count(*) FILTER (WHERE nb_reparutions > 0 AND NOT ecartee)
                                                              AS reparues,
                   count(*) FILTER (WHERE en_ligne AND NOT ecartee AND
                        (CURRENT_DATE - COALESCE(publiee_le, vue_le_premier)) >= 30)
                                                              AS anciennes
              FROM annonce
            """
        )
        base = cur.fetchone()
        cur.execute("SELECT count(DISTINCT entreprise_cle) AS n FROM annonce "
                    " WHERE entreprise_cle <> '' AND NOT ecartee")
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


# ==================================================================
# Repertoire des contacts
# ==================================================================
# Separe des annonces : une adresse revient sur plusieurs offres, et
# une desinscription doit valoir pour toujours, meme si l'entreprise
# republie. C'est ce registre qui rend l'opposition effective.

MENTION_OBLIGATOIRE = (
    "Vos coordonnees professionnelles proviennent d'une offre d'emploi que "
    "vous avez publiee sur France Travail. Elles sont utilisees une fois par "
    "an pour vous presenter nos services de recrutement. Vous pouvez vous y "
    "opposer a tout moment par le lien de desinscription ci-dessous, ou en "
    "repondant a ce message."
)


def enregistrer_contact(annonce):
    """Range une adresse dans le repertoire, sans jamais reveiller une
    desinscription passee."""
    adresse = (annonce.get("contact_courriel") or "").strip().lower()
    if not courriel_valide(adresse):
        return False
    import secrets
    with db.curseur() as cur:
        cur.execute(
            """
            INSERT INTO contact_pige
                (courriel, generique, entreprise, entreprise_cle, commune, jeton)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (courriel) DO UPDATE
               SET entreprise = COALESCE(contact_pige.entreprise, EXCLUDED.entreprise),
                   commune    = COALESCE(contact_pige.commune, EXCLUDED.commune)
            """,
            (adresse, courriel_generique(adresse), annonce.get("entreprise"),
             cle_entreprise(annonce.get("entreprise")), annonce.get("commune"),
             secrets.token_urlsafe(12)),
        )
    return True


def contacts(generiques_seulement=True, desinscrits=False, limite=2000):
    _assurer_tables()
    conditions = ["desinscrit" if desinscrits else "NOT desinscrit"]
    if generiques_seulement:
        conditions.append("generique")
    with db.curseur() as cur:
        cur.execute(
            "SELECT * FROM contact_pige WHERE " + " AND ".join(conditions)
            + " ORDER BY entreprise NULLS LAST, courriel LIMIT %s", (limite,))
        return cur.fetchall()


def desinscrire(jeton=None, courriel=None):
    """Une opposition est definitive : l'adresse reste en base,
    marquee, pour ne jamais etre recollectee par erreur."""
    _assurer_tables()
    with db.curseur() as cur:
        if jeton:
            cur.execute("UPDATE contact_pige SET desinscrit = TRUE, "
                        " desinscrit_le = now() WHERE jeton = %s "
                        " RETURNING courriel", (jeton,))
        else:
            cur.execute("UPDATE contact_pige SET desinscrit = TRUE, "
                        " desinscrit_le = now() WHERE courriel = %s "
                        " RETURNING courriel", ((courriel or "").lower(),))
        ligne = cur.fetchone()
    return ligne["courriel"] if ligne else None


def etat_contacts():
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT count(*)                                        AS total,
                   count(*) FILTER (WHERE generique)               AS generiques,
                   count(*) FILTER (WHERE NOT generique)           AS nominatives,
                   count(*) FILTER (WHERE desinscrit)              AS desinscrits,
                   count(*) FILTER (WHERE generique AND NOT desinscrit)
                                                                   AS envoyables
              FROM contact_pige
            """
        )
        return cur.fetchone()


def retrier_tout():
    """
    Repasse tout ce qui est deja en base dans le tri courant.

    A lancer apres avoir modifie les listes du haut de ce fichier :
    ajoute une enseigne d'interim, retire une commune, et les annonces
    deja collectees suivent sans attendre la prochaine collecte.

        python -c "import pige; print(pige.retrier_tout())"
    """
    _assurer_tables()
    with db.curseur() as cur:
        cur.execute("SELECT id, partie, entreprise, commune, code_postal, "
                    "       publiee_le, vue_le_premier "
                    "  FROM annonce")
        lignes = cur.fetchall()
    ecartees = 0
    with db.curseur() as cur:
        for l in lignes:
            motif = motif_ecart(l)
            ecartees += 1 if motif else 0
            cur.execute("UPDATE annonce SET ecartee = %s, motif_ecart = %s "
                        " WHERE id = %s", (motif is not None, motif, l["id"]))
    return {"examinees": len(lignes), "ecartees": ecartees,
            "retenues": len(lignes) - ecartees}


def oublier_contact(annonce_id):
    """Efface le nom de contact d'une annonce, sur demande."""
    with db.curseur() as cur:
        cur.execute("UPDATE annonce SET contact_nom = NULL WHERE id = %s",
                    (annonce_id,))
        return cur.rowcount
