"""
Plateforme de passation des tests candidats.

Lancement en local :
    export DATABASE_URL="postgresql://..."
    export MOT_DE_PASSE_RECRUTEUR="..."
    export URL_PUBLIQUE="http://127.0.0.1:8000"
    uvicorn main:app --reload
"""
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import quote

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Form, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import db
import correction
import analyse
import rapport_pdf
import ia
import affichage
import rgpd


@asynccontextmanager
async def cycle_de_vie(app):
    """
    Purge des donnees echues au demarrage du serveur.

    L'hebergement ne propose pas de planificateur : ce passage, complete
    par celui du back-office, suffit largement pour une conservation
    exprimee en mois. Une base injoignable ne doit pas empecher le
    serveur de demarrer, d'ou le filet.
    """
    try:
        n = rgpd.purger_si_besoin()
        if n:
            print(f"[rgpd] {n} invitation(s) anonymisee(s) au demarrage")
    except Exception as e:
        print(f"[rgpd] purge impossible au demarrage : {e}")
    yield


app = FastAPI(title="Tests candidats", lifespan=cycle_de_vie)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Le serveur tourne en UTC : les dates sont converties dans le fuseau du
# cabinet au moment de l'affichage, et les libelles enregistres sans
# accent sont accentues de la meme facon.
templates.env.filters["heure"] = affichage.date_heure
templates.env.filters["joli"] = affichage.joli

URL_PUBLIQUE = os.environ.get("URL_PUBLIQUE", "http://127.0.0.1:8000")
MOT_DE_PASSE = os.environ.get("MOT_DE_PASSE_RECRUTEUR")
JOURS_VALIDITE = int(os.environ.get("JOURS_VALIDITE", "7"))
JOURS_CONSERVATION = int(os.environ.get("JOURS_CONSERVATION", "180"))

securite = HTTPBasic()


def recruteur(creds: HTTPBasicCredentials = Depends(securite)):
    """Authentification simple du back-office. A remplacer par un vrai
    annuaire si plusieurs consultants doivent avoir des acces distincts."""
    if not MOT_DE_PASSE:
        raise HTTPException(500, "MOT_DE_PASSE_RECRUTEUR n'est pas défini.")
    if not secrets.compare_digest(creds.password, MOT_DE_PASSE):
        raise HTTPException(401, "Identifiants invalides",
                            headers={"WWW-Authenticate": "Basic"})
    return creds.username


# ==================================================================
# Chrono : calcule cote serveur, jamais cote navigateur
# ==================================================================

def secondes_restantes(inv):
    if not inv["demarre_le"]:
        return inv["duree_minutes"] * 60
    ecoule = (datetime.now(timezone.utc) - inv["demarre_le"]).total_seconds()
    return max(0, int(inv["duree_minutes"] * 60 - ecoule))


def charger_invitation(token, attendus=("envoyee", "en_cours")):
    inv = db.invitation_par_token(token)
    if not inv:
        raise HTTPException(404, "Ce lien n'existe pas.")
    if inv["statut"] == "terminee":
        return inv, "terminee"
    if inv["statut"] in ("annulee", "expiree"):
        return inv, "indisponible"
    if inv["expire_le"] < datetime.now(timezone.utc):
        return inv, "expiree"
    return inv, "ok"


def finaliser(inv):
    """Corrige, enregistre le resultat et cloture l'invitation."""
    questions = db.questions_du_test(inv["test_id"])
    reponses = db.reponses_de(inv["id"])
    duree = None
    if inv["demarre_le"]:
        fin = inv["termine_le"] or datetime.now(timezone.utc)
        duree = int((fin - inv["demarre_le"]).total_seconds())

    if inv["type_test"] == "technique":
        res = correction.corriger_technique(questions, reponses, duree)
    else:
        dims = correction.dimensions_du_test(questions)
        res = correction.calculer_positionnement(questions, reponses, dims, duree)

    db.cloturer_vues(inv["id"])
    db.enregistrer_resultat(inv["id"], res)

    anomalies = analyse.detecter_anomalies(
        inv, res, db.vues_de(inv["id"]), db.lettres_choisies(inv["id"]),
        comportement={
            "sorties_page": db.compter_evenements(inv["id"], "sortie_page"),
            "copies_tentees": db.compter_evenements(inv["id"], "copie_tentee"),
        },
    )
    db.enregistrer_anomalies(inv["id"], anomalies)

    db.cloturer(inv["id"])
    return res


# ==================================================================
# Parcours candidat
# ==================================================================

@app.get("/t/{token}", response_class=HTMLResponse)
def accueil(request: Request, token: str):
    inv, etat = charger_invitation(token)
    if etat == "terminee":
        return templates.TemplateResponse(request, "fin.html", {"request": request, "inv": inv})
    if etat != "ok":
        return templates.TemplateResponse(
            request, "indisponible.html", {"request": request, "etat": etat},
            status_code=410
        )
    if inv["demarre_le"]:
        return RedirectResponse(f"/t/{token}/q/1", status_code=303)

    db.journaliser(inv["id"], "ouverture")
    return templates.TemplateResponse(request, "accueil.html", {"request": request, "inv": inv})


@app.post("/t/{token}/demarrer")
def demarrer(token: str, nom: str = Form(...), consentement: str = Form(None)):
    inv, etat = charger_invitation(token)
    if etat != "ok":
        raise HTTPException(410, "Ce lien n'est plus utilisable.")
    if not consentement:
        raise HTTPException(400, "L'information sur les données doit être acceptée.")
    db.demarrer(inv["id"])
    db.journaliser(inv["id"], "demarrage", nom)
    return RedirectResponse(f"/t/{token}/q/1", status_code=303)


@app.get("/t/{token}/q/{numero}", response_class=HTMLResponse)
def afficher_question(request: Request, token: str, numero: int):
    inv, etat = charger_invitation(token)
    if etat == "terminee":
        return RedirectResponse(f"/t/{token}/fin", status_code=303)
    if etat != "ok":
        return templates.TemplateResponse(
            request, "indisponible.html", {"request": request, "etat": etat},
            status_code=410
        )
    if not inv["demarre_le"]:
        return RedirectResponse(f"/t/{token}", status_code=303)

    restant = secondes_restantes(inv)
    if restant <= 0:
        finaliser(inv)
        db.journaliser(inv["id"], "expiration_chrono")
        return RedirectResponse(f"/t/{token}/fin", status_code=303)

    total = db.nombre_questions(inv["test_id"])
    if numero < 1 or numero > total:
        raise HTTPException(404, "Question inconnue.")

    q = db.question_par_numero(inv["test_id"], numero)
    db.marquer_vue(inv["id"], q["id"])
    deja = {r["option_id"] for r in db.reponses_de(inv["id"], q["id"])}

    return templates.TemplateResponse(request, "question.html", {
        "request": request, "inv": inv, "q": q, "numero": numero,
        "total": total, "restant": restant, "deja": deja,
        "multiple": q["format"] == "multiple",
    })


@app.post("/t/{token}/q/{numero}")
async def enregistrer(request: Request, token: str, numero: int):
    inv, etat = charger_invitation(token)
    if etat != "ok" or not inv["demarre_le"]:
        return RedirectResponse(f"/t/{token}", status_code=303)

    if secondes_restantes(inv) <= 0:
        finaliser(inv)
        return RedirectResponse(f"/t/{token}/fin", status_code=303)

    formulaire = await request.form()
    q = db.question_par_numero(inv["test_id"], numero)
    valides = {o["id"] for o in q["options"]}
    choisies = []
    for valeur in formulaire.getlist("option"):
        try:
            oid = int(valeur)
        except ValueError:
            continue
        if oid in valides:
            choisies.append(oid)

    # une seule reponse autorisee sauf pour les questions a reponses multiples
    if q["format"] != "multiple":
        choisies = choisies[:1]

    db.enregistrer_reponses(inv["id"], q["id"], choisies)

    total = db.nombre_questions(inv["test_id"])
    if numero >= total:
        return RedirectResponse(f"/t/{token}/terminer", status_code=303)
    return RedirectResponse(f"/t/{token}/q/{numero + 1}", status_code=303)


@app.post("/t/{token}/evenement")
async def evenement(request: Request, token: str):
    """
    Enregistre un evenement de comportement pendant la passation :
    sortie de page, tentative de copie.

    On ne bloque rien et on n'interrompt jamais le test : ces donnees
    servent uniquement a nuancer la lecture du resultat.
    """
    inv = db.invitation_par_token(token)
    if not inv or inv["statut"] != "en_cours":
        return Response(status_code=204)
    try:
        donnees = await request.json()
        type_evenement = str(donnees.get("type", ""))[:40]
    except Exception:
        return Response(status_code=204)
    if type_evenement in ("sortie_page", "copie_tentee"):
        db.journaliser(inv["id"], type_evenement)
    return Response(status_code=204)


@app.get("/t/{token}/terminer", response_class=HTMLResponse)
def confirmer_fin(request: Request, token: str):
    inv, etat = charger_invitation(token)
    if etat == "terminee":
        return RedirectResponse(f"/t/{token}/fin", status_code=303)
    total = db.nombre_questions(inv["test_id"])
    repondues = {r["question_id"] for r in db.reponses_de(inv["id"])}
    return templates.TemplateResponse(request, "terminer.html", {
        "request": request, "inv": inv, "total": total,
        "repondues": len(repondues), "restant": secondes_restantes(inv),
    })


@app.post("/t/{token}/terminer")
def valider_fin(token: str):
    inv, etat = charger_invitation(token)
    if etat == "ok":
        finaliser(inv)
    return RedirectResponse(f"/t/{token}/fin", status_code=303)


@app.get("/t/{token}/fin", response_class=HTMLResponse)
def fin(request: Request, token: str):
    inv = db.invitation_par_token(token)
    if not inv:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "fin.html", {"request": request, "inv": inv})


# ==================================================================
# Back-office recruteur
# ==================================================================

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, supprime: str = None,
          utilisateur: str = Depends(recruteur)):
    # Deuxieme declencheur de la purge, au plus une fois par jour. Une
    # erreur ici ne doit pas empecher le recruteur de travailler.
    try:
        rgpd.purger_si_besoin()
    except Exception as e:
        print(f"[rgpd] purge impossible : {e}")

    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "tests": db.liste_tests(),
        "invitations": db.liste_invitations(),
        "url_publique": URL_PUBLIQUE,
        "utilisateur": utilisateur,
        "supprime": supprime,
    })


@app.post("/admin/inviter")
def inviter(test_id: int = Form(...), nom: str = Form(""), email: str = Form(""),
            poste: str = Form(""), utilisateur: str = Depends(recruteur)):
    token = secrets.token_urlsafe(16)   # 22 caracteres, imprevisible
    db.creer_invitation(token, test_id, nom or None, email or None, poste or None,
                        utilisateur, JOURS_VALIDITE, JOURS_CONSERVATION)
    return RedirectResponse("/admin", status_code=303)


# ==================================================================
# Donnees personnelles : conservation, purge, suppression
# ==================================================================

@app.get("/admin/rgpd", response_class=HTMLResponse)
def page_rgpd(request: Request, purgees: int = None,
              utilisateur: str = Depends(recruteur)):
    return templates.TemplateResponse(request, "rgpd.html", {
        "request": request,
        "etat": db.etat_conservation(),
        "purges": db.journal_des_purges(),
        "jours_conservation": JOURS_CONSERVATION,
        "jours_validite": JOURS_VALIDITE,
        "purgees": purgees,
    })


@app.post("/admin/rgpd/purger")
def lancer_purge(utilisateur: str = Depends(recruteur)):
    """Meme traitement que la purge automatique, declenche a la main."""
    n = rgpd.purger()
    return RedirectResponse(f"/admin/rgpd?purgees={n}", status_code=303)


@app.post("/admin/invitation/{invitation_id}/supprimer")
def supprimer_invitation(invitation_id: int, utilisateur: str = Depends(recruteur)):
    """
    Suppression definitive d'une passation, sur demande du candidat ou
    pour retirer un essai. Tout ce qui s'y rattache disparait.
    """
    ligne = db.supprimer_invitation(invitation_id)
    if ligne is None:
        raise HTTPException(404, "Cette invitation n'existe pas ou plus.")
    return RedirectResponse(
        f"/admin?supprime={quote(ligne['nom'] or 'sans nom')}", status_code=303
    )


@app.get("/admin/resultat/{invitation_id}", response_class=HTMLResponse)
def voir_resultat(request: Request, invitation_id: int, erreur: str = None,
                  utilisateur: str = Depends(recruteur)):
    res = db.resultat_de(invitation_id)
    if not res:
        raise HTTPException(404, "Aucun résultat pour cette invitation.")
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT i.*, t.intitule, t.type_test
              FROM invitation i JOIN test t ON t.id = i.test_id
             WHERE i.id = %s
            """,
            (invitation_id,),
        )
        inv = cur.fetchone()
    return templates.TemplateResponse(request, "resultat.html", {
        "request": request, "inv": inv, "res": res, "d": res["detail"],
        "anomalies": db.anomalies_de(invitation_id),
        "guide": db.guide_de(invitation_id),
        "ia_disponible": ia.disponible(),
        "erreur_ia": erreur,
    })


# ==================================================================
# Tableau de bord analytique
# ==================================================================

@app.get("/admin/analyse", response_class=HTMLResponse)
def choisir_analyse(request: Request, utilisateur: str = Depends(recruteur)):
    return templates.TemplateResponse(request, "analyse_index.html", {
        "request": request, "tests": db.liste_tests(),
    })


@app.get("/admin/analyse/{test_id}", response_class=HTMLResponse)
def analyser(request: Request, test_id: int, utilisateur: str = Depends(recruteur)):
    test = db.test_par_id(test_id)
    if not test:
        raise HTTPException(404, "Test inconnu.")

    resultats = db.resultats_du_test(test_id)
    invitations = db.invitations_du_test(test_id)
    stats = analyse.statistiques_test(resultats, invitations)

    contexte = {
        "request": request, "test": test, "stats": stats,
        "distribution": analyse.distribution_scores(resultats),
        "items": None, "profils": None, "situations": None,
    }

    if test["type_test"] == "technique":
        # Les mesures sont passees a plat plutot que sous forme de
        # dictionnaire : dans un gabarit, "mesure.items" designe la methode
        # items() du dictionnaire, pas la cle du meme nom.
        mesure = analyse.analyser_items(db.lignes_analyse(test_id))
        contexte["items"] = mesure["items"]
        contexte["items_effectif"] = mesure["effectif"]
        contexte["items_fiable"] = mesure["fiable"]
        contexte["items_a_revoir"] = mesure.get("a_revoir", [])
    else:
        contexte["profils"] = analyse.profils_agreges(resultats)
        contexte["situations"] = analyse.frequence_situations(resultats)
        contexte["effectif"] = len(resultats)

    return templates.TemplateResponse(request, "analyse.html", contexte)


@app.post("/admin/resultat/{invitation_id}/guide")
def generer_guide(invitation_id: int, utilisateur: str = Depends(recruteur)):
    """
    Genere un guide d'entretien a partir du profil de positionnement.

    Le modele ne recoit aucune donnee nominative et ne produit aucune
    appreciation sur le candidat : la sortie est controlee avant enregistrement.
    La decision reste entierement au recruteur.
    """
    res = db.resultat_de(invitation_id)
    if not res:
        raise HTTPException(404, "Aucun résultat pour cette invitation.")

    with db.curseur() as cur:
        cur.execute(
            """
            SELECT i.poste_vise, t.niveau, t.domaine
              FROM invitation i JOIN test t ON t.id = i.test_id
             WHERE i.id = %s
            """,
            (invitation_id,),
        )
        contexte = cur.fetchone()

    texte, erreur = ia.generer(res["detail"], {
        "poste": contexte["poste_vise"],
        "niveau": contexte["niveau"],
        "domaine": contexte["domaine"],
    })

    if erreur:
        db.journaliser(invitation_id, "guide_echec", erreur)
        return RedirectResponse(
            f"/admin/resultat/{invitation_id}?erreur={quote(erreur)}", status_code=303
        )

    db.enregistrer_guide(invitation_id, texte, ia.FOURNISSEUR, ia.MODELE, utilisateur)
    db.journaliser(invitation_id, "guide_genere", ia.MODELE)
    return RedirectResponse(f"/admin/resultat/{invitation_id}", status_code=303)


@app.get("/admin/resultat/{invitation_id}/pdf")
def resultat_pdf(invitation_id: int, utilisateur: str = Depends(recruteur)):
    """Rapport PDF d'un candidat, destine a etre transmis au client."""
    res = db.resultat_de(invitation_id)
    if not res:
        raise HTTPException(404, "Aucun résultat pour cette invitation.")
    with db.curseur() as cur:
        cur.execute(
            """
            SELECT i.*, t.intitule, t.type_test
              FROM invitation i JOIN test t ON t.id = i.test_id
             WHERE i.id = %s
            """,
            (invitation_id,),
        )
        inv = cur.fetchone()

    contenu = rapport_pdf.construire(inv, res, db.anomalies_de(invitation_id))
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{rapport_pdf.nom_fichier(inv)}"'},
    )


@app.get("/admin/resultats.csv")
def resultats_csv(utilisateur: str = Depends(recruteur)):
    """Synthese de toutes les passations terminees, une ligne par candidat."""
    import csv
    import io
    lignes = db.liste_invitations(limite=2000)
    tampon = io.StringIO()
    graveur = csv.writer(tampon, delimiter=";")
    graveur.writerow(["Candidat", "Poste vise", "Test", "Type", "Statut",
                      "Date de creation", "Date de fin", "Score", "Total",
                      "Pourcentage", "Points de vigilance"])
    for i in lignes:
        graveur.writerow([
            i["candidat_nom"] or "", i["poste_vise"] or "", i["intitule"],
            i["type_test"], i["statut"],
            i["cree_le"].strftime("%d/%m/%Y") if i["cree_le"] else "",
            i["termine_le"].strftime("%d/%m/%Y") if i["termine_le"] else "",
            i["score"] if i["score"] is not None else "",
            i["total_points"] if i["total_points"] is not None else "",
            i["pourcentage"] if i["pourcentage"] is not None else "",
            i["nb_vigilances"] if i["nb_vigilances"] is not None else "",
        ])
    return Response(
        content=tampon.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="resultats.csv"'},
    )


@app.get("/admin/export.csv")
def exporter(utilisateur: str = Depends(recruteur)):
    """Export anonymise : aucune identite, exploitable dans un notebook."""
    import csv
    import io
    lignes = db.export_lignes()
    tampon = io.StringIO()
    if lignes:
        graveur = csv.DictWriter(tampon, fieldnames=list(lignes[0].keys()),
                                 delimiter=";")
        graveur.writeheader()
        graveur.writerows(lignes)
    return Response(
        content=tampon.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=passations.csv"},
    )


@app.get("/sante")
def sante():
    return {"statut": "ok"}


# ------------------------------------------------------------------
# Journalisation des erreurs
# En cas d'anomalie, la trace complete part dans les journaux du serveur :
# indispensable pour diagnostiquer une application deployee.
# ------------------------------------------------------------------
import logging
import traceback

logging.basicConfig(level=logging.INFO)
journal_app = logging.getLogger("tests-candidats")


@app.exception_handler(Exception)
async def toute_erreur(request: Request, exc: Exception):
    journal_app.error(
        "Erreur sur %s %s\n%s",
        request.method, request.url.path, traceback.format_exc(),
    )
    return Response(
        content="Une erreur est survenue. Le cabinet a ete informe.",
        status_code=500, media_type="text/plain; charset=utf-8",
    )


@app.get("/sante/base")
def sante_base():
    """Verifie que la base repond. Utile juste apres un deploiement."""
    try:
        with db.curseur() as cur:
            cur.execute("SELECT count(*) AS n FROM test")
            n = cur.fetchone()["n"]
        return {"base": "ok", "tests_en_base": n}
    except Exception as e:
        return {"base": "erreur", "detail": str(e)[:300]}