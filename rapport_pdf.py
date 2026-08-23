"""Genere le rapport PDF d'une passation, destine a etre transmis au client."""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

import affichage

ACCENT = colors.HexColor("#2F5D50")
ALERTE = colors.HexColor("#9E2A2A")
JUSTE = colors.HexColor("#1F7A3D")
DOUX = colors.HexColor("#6B6B64")
TRAIT = colors.HexColor("#DDDDD6")
FOND = colors.HexColor("#F3F3EE")

_base = getSampleStyleSheet()

S = {
    "titre": ParagraphStyle("titre", parent=_base["Normal"], fontName="Helvetica-Bold",
                            fontSize=16, leading=20, spaceAfter=2),
    "soustitre": ParagraphStyle("soustitre", parent=_base["Normal"],
                                fontName="Helvetica", fontSize=10.5, leading=14,
                                textColor=DOUX, spaceAfter=10),
    "h2": ParagraphStyle("h2", parent=_base["Normal"], fontName="Helvetica-Bold",
                         fontSize=11.5, leading=15, spaceBefore=14, spaceAfter=6),
    "corps": ParagraphStyle("corps", parent=_base["Normal"], fontName="Helvetica",
                            fontSize=9.5, leading=13, spaceAfter=4),
    "petit": ParagraphStyle("petit", parent=_base["Normal"], fontName="Helvetica",
                            fontSize=8, leading=11, textColor=DOUX, spaceAfter=3),
    "cellule": ParagraphStyle("cellule", parent=_base["Normal"], fontName="Helvetica",
                              fontSize=8.5, leading=11),
    "score": ParagraphStyle("score", parent=_base["Normal"], fontName="Helvetica-Bold",
                            fontSize=22, leading=26, textColor=ACCENT, spaceAfter=2),
    "note": ParagraphStyle("note", parent=_base["Normal"], fontName="Helvetica-Oblique",
                           fontSize=8, leading=11, textColor=DOUX),
}

GRILLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), FOND),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
    ("LINEBELOW", (0, 0), (-1, -1), 0.4, TRAIT),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
])


def _duree(secondes):
    if not secondes:
        return "non renseignée"
    return f"{secondes // 60} min {secondes % 60} s"


def _entete(inv, res, elements):
    elements.append(Paragraph(inv.get("candidat_nom") or "Candidat", S["titre"]))
    ligne = inv["intitule"]
    if inv.get("poste_vise"):
        ligne += f" &nbsp;|&nbsp; poste visé : {inv['poste_vise']}"
    elements.append(Paragraph(ligne, S["soustitre"]))

    infos = [
        ["Date de passation", affichage.date_heure(inv.get("termine_le"))],
        ["Durée", _duree(res.get("duree_secondes"))],
    ]
    t = Table(infos, colWidths=[45 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 0), (1, -1), DOUX),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, TRAIT),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)


def _technique(d, res, elements):
    elements.append(Paragraph("Résultat", S["h2"]))
    elements.append(Paragraph(f"{res['score']} / {res['total_points']}", S["score"]))
    elements.append(Paragraph(f"{res['pourcentage']} % &mdash; {d['lecture']}", S["corps"]))

    if d.get("synthese"):
        elements.append(Paragraph("Synthèse", S["h2"]))
        elements.append(Paragraph(d["synthese"], S["corps"]))

    if d.get("themes"):
        elements.append(Paragraph("Résultat par thème", S["h2"]))
        lignes = [["Thème", "Réussite", "Lecture", "Questions manquées"]]
        styles = []
        for i, t in enumerate(d["themes"], start=1):
            lignes.append([
                Paragraph(t["theme"], S["cellule"]),
                f"{t['reussies']}/{t['total']}",
                affichage.joli(t["niveau"]),
                ", ".join(str(n) for n in t["ratees"]) or "-",
            ])
            if t["niveau"] == "acquis":
                styles.append(("TEXTCOLOR", (2, i), (2, i), JUSTE))
            elif t["niveau"] == "a consolider":
                styles.append(("TEXTCOLOR", (2, i), (2, i), ALERTE))
        t_themes = Table(lignes, colWidths=[70 * mm, 22 * mm, 33 * mm, 40 * mm],
                         repeatRows=1)
        t_themes.setStyle(GRILLE)
        for st in styles:
            t_themes.setStyle(TableStyle([st]))
        elements.append(t_themes)

    elements.append(Paragraph("Détail des réponses", S["h2"]))
    lignes = [["N°", "Question", "Attendu", "Donné", ""]]
    styles = []
    for i, q in enumerate(d["questions"], start=1):
        texte = q["enonce"]
        if not q["juste"] and q.get("justification"):
            texte += f"<br/><font size=7 color='#6B6B64'>{q['justification']}</font>"
        lignes.append([
            str(q["numero"]),
            Paragraph(texte, S["cellule"]),
            ", ".join(q["attendu"]),
            ", ".join(q["donne"]) or "-",
            "OK" if q["juste"] else "X",
        ])
        couleur = JUSTE if q["juste"] else ALERTE
        styles.append(("TEXTCOLOR", (4, i), (4, i), couleur))
        styles.append(("FONTNAME", (4, i), (4, i), "Helvetica-Bold"))

    t = Table(lignes, colWidths=[10 * mm, 105 * mm, 20 * mm, 20 * mm, 10 * mm],
              repeatRows=1)
    t.setStyle(GRILLE)
    for s in styles:
        t.setStyle(TableStyle([s]))
    elements.append(t)

    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Une question est validée uniquement si toutes les bonnes réponses sont "
        "cochées et qu'aucune réponse erronée ne l'est. Aucun point partiel, "
        "aucun point négatif.", S["note"]))


def _barre(valeur, maximum=6, largeur=24):
    plein = int(round(largeur * valeur / maximum))
    return "\u2588" * plein if plein else ""


def _positionnement(d, elements):
    elements.append(Paragraph("Profil", S["h2"]))
    lignes = [["Dimension", "Total", "", "Lecture"]]
    for p in d["profil"]:
        lignes.append([
            Paragraph(p["nom"], S["cellule"]),
            str(p["total"]),
            Paragraph(f"<font color='#2F5D50'>{_barre(p['total'])}</font>", S["cellule"]),
            affichage.joli(p["lecture"]),
        ])
    t = Table(lignes, colWidths=[62 * mm, 14 * mm, 55 * mm, 34 * mm], repeatRows=1)
    t.setStyle(GRILLE)
    elements.append(t)

    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "Le profil est relatif au candidat : les totaux s'additionnent toujours à 21. "
        "Une dimension ne peut monter que si une autre descend. Ces résultats ne "
        "permettent donc pas de comparer deux candidats entre eux.", S["note"]))

    elements.append(Paragraph("Mises en situation", S["h2"]))
    for s in d["situations"]:
        bloc = [
            Paragraph(f"<b>{s['numero']}.</b> {s['enonce']}", S["corps"]),
            Paragraph(
                f"<font color='{'#9E2A2A' if s['vigilance'] else '#1F7A3D'}'>"
                f"<b>{s['lettre'] or '-'}. {s['texte'] or 'Sans réponse'}</b></font>",
                S["corps"]),
            Paragraph(affichage.joli(s["lecture"]) or "", S["petit"]),
            Spacer(1, 6),
        ]
        elements.append(KeepTogether(bloc))


def _avertissement(elements):
    texte = (
        "<b>Précautions d'usage.</b> Ce questionnaire n'est pas un test psychométrique "
        "validé : aucune étude de fidélité ni de validité n'a été conduite sur une "
        "population de référence. Il ne mesure aucun trait de personnalité au sens "
        "clinique et ne produit ni note ni classement. Il constitue un support de "
        "préparation à l'entretien et ne doit jamais être utilisé seul pour écarter "
        "une candidature."
    )
    t = Table([[Paragraph(texte, S["petit"])]], colWidths=[165 * mm])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, TRAIT),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDF6F6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(Spacer(1, 8))
    elements.append(t)


def _anomalies(anomalies, elements):
    if not anomalies:
        return
    elements.append(Paragraph("Signalements automatiques", S["h2"]))
    for a in anomalies:
        prefixe = "Attention" if a["gravite"] == "attention" else "Information"
        elements.append(Paragraph(f"<b>{prefixe} :</b> {a['libelle']}", S["corps"]))
    elements.append(Paragraph(
        "Aucun de ces signalements n'est disqualifiant. Ce sont des sujets à évoquer "
        "en entretien.", S["note"]))


def _pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(DOUX)
    canvas.drawString(20 * mm, 12 * mm,
                      "Document confidentiel - usage strictement limité au processus "
                      "de recrutement")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def construire(inv, res, anomalies=None):
    """Renvoie les octets du PDF."""
    tampon = io.BytesIO()
    doc = SimpleDocTemplate(
        tampon, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Résultat - {inv.get('candidat_nom') or 'candidat'}",
        author="Plateforme de tests candidats",
    )
    d = res["detail"]
    elements = []
    _entete(inv, res, elements)
    _anomalies(anomalies or [], elements)

    if d["type"] == "technique":
        _technique(d, res, elements)
    else:
        _positionnement(d, elements)
        _avertissement(elements)

    doc.build(elements, onFirstPage=_pied, onLaterPages=_pied)
    return tampon.getvalue()


def nom_fichier(inv):
    nom = (inv.get("candidat_nom") or "candidat").replace(" ", "_")
    nom = "".join(c for c in nom if c.isalnum() or c in "_-")
    date = affichage.jour(inv.get("termine_le") or datetime.now(timezone.utc))
    return f"resultat_{nom}_{date}.pdf"
