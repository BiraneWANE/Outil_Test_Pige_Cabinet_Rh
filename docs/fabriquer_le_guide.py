"""
Fabrique le PDF du guide a partir de GUIDE_CONSULTANTE.md.

    cd docs
    python fabriquer_le_guide.py

A relancer chaque fois que GUIDE_CONSULTANTE.md change, sinon la version
imprimee prend du retard sur la version texte -- ce qui est deja arrive une
fois, le PDF ne parlant ni de la pige ni des sauvegardes.

Deux bibliotheques sont necessaires, et elles ne sont PAS dans
requirements.txt : elles ne servent qu'ici, sur le poste de travail, et
n'ont rien a faire sur le serveur.

    pip install markdown playwright
    playwright install chromium

Le style reprend celui de la premiere version : A4, titres vert sombre,
tableaux a en-tete grise, filets entre les sections. S'y ajoutent un
sommaire et une numerotation des pages, le guide ayant double de taille.
"""
import io
import os
import re
import sys
import unicodedata

import markdown

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCE = sys.argv[1] if len(sys.argv) > 1 else "GUIDE_CONSULTANTE.md"
SORTIE = sys.argv[2] if len(sys.argv) > 2 else "Guide_utilisation_plateforme_tests.pdf"


def ancre(titre):
    """Un identifiant de lien stable, sans accent ni ponctuation."""
    plat = unicodedata.normalize("NFD", titre)
    plat = "".join(c for c in plat if unicodedata.category(c) != "Mn")
    plat = re.sub(r"[^a-z0-9]+", "-", plat.lower()).strip("-")
    return plat


texte = io.open(os.path.join(ICI, SOURCE), encoding="utf-8").read()

# Le titre de niveau 1 et le chapeau sont repris a la main, pour construire
# une page de garde plutot que de les laisser en tete de flux.
lignes = texte.split("\n")
titre = lignes[0].lstrip("# ").strip()
corps = "\n".join(lignes[1:])

sections = re.findall(r"^## (.+)$", corps, re.M)

# Chaque titre de section recoit son ancre, pour que le sommaire soit
# cliquable dans le PDF.
def poser_ancre(m):
    t = m.group(1)
    return f'<h2 id="{ancre(t)}">{t}</h2>'


html = markdown.markdown(corps, extensions=["tables", "sane_lists"])
html = re.sub(r"<h2>(.+?)</h2>", poser_ancre, html)

sommaire = "\n".join(
    f'<li><a href="#{ancre(s)}">{s}</a></li>' for s in sections
)

page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>{titre}</title>
<style>
  @page {{ size: A4; margin: 20mm 18mm 18mm; }}

  :root {{
    --vert:   #26584A;
    --encre:  #1F2426;
    --gris:   #5A6467;
    --filet:  #D8DEDC;
    --fond:   #F1F4F3;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    font-family: "DejaVu Sans", "Segoe UI", system-ui, sans-serif;
    font-size: 10.6pt;
    line-height: 1.55;
    color: var(--encre);
  }}

  /* ---- page de garde ---- */
  .garde {{
    height: 247mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    break-after: page;
  }}
  .garde h1 {{
    font-size: 30pt;
    line-height: 1.1;
    color: var(--vert);
    margin: 0 0 6mm;
    letter-spacing: -0.01em;
  }}
  .garde .barre {{ height: 3px; background: var(--vert); width: 62mm; margin-bottom: 8mm; }}
  .garde p {{ margin: 0 0 4mm; max-width: 120mm; color: var(--gris); font-size: 11pt; }}
  .garde .adresse {{
    margin-top: 10mm;
    padding: 5mm 6mm;
    background: var(--fond);
    border-left: 3px solid var(--vert);
    color: var(--encre);
    font-size: 11pt;
  }}
  .garde .adresse b {{ color: var(--vert); }}
  .garde .pied {{ margin-top: auto; color: var(--gris); font-size: 9pt; }}

  /* ---- sommaire ---- */
  .sommaire {{ break-after: page; }}
  .sommaire h2 {{
    font-size: 15pt; color: var(--vert); margin: 0 0 6mm;
    padding-bottom: 3mm; border-bottom: 2px solid var(--vert);
  }}
  .sommaire ol {{ margin: 0; padding-left: 11mm; }}
  .sommaire li {{ margin-bottom: 2.4mm; }}
  .sommaire a {{ color: var(--encre); text-decoration: none; }}

  /* ---- corps ---- */
  h2 {{
    font-size: 14pt;
    color: var(--vert);
    margin: 9mm 0 3mm;
    padding-top: 5mm;
    border-top: 1px solid var(--filet);
    break-after: avoid;
  }}
  h2:first-of-type {{ border-top: none; padding-top: 0; margin-top: 0; }}
  h3 {{ font-size: 11.5pt; color: var(--encre); margin: 5mm 0 2mm; break-after: avoid; }}

  p {{ margin: 0 0 3mm; }}
  strong {{ color: var(--encre); }}
  em {{ color: var(--gris); }}

  ul, ol {{ margin: 0 0 3mm; padding-left: 6mm; }}
  li {{ margin-bottom: 1.6mm; }}
  li > p {{ margin-bottom: 1.6mm; }}

  hr {{ display: none; }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 3mm 0 5mm;
    font-size: 9.8pt;
    break-inside: avoid;
  }}
  th {{
    background: var(--fond);
    text-align: left;
    padding: 2.2mm 3mm;
    font-weight: 600;
    border-bottom: 1px solid var(--filet);
  }}
  td {{ padding: 2.2mm 3mm; border-bottom: 1px solid var(--filet); vertical-align: top; }}

  code {{
    font-family: "DejaVu Sans Mono", ui-monospace, monospace;
    font-size: 9.4pt;
    background: var(--fond);
    padding: 0.3mm 1mm;
    border-radius: 2px;
  }}

  /* on evite les lignes orphelines en bas de page */
  p, li, table {{ orphans: 2; widows: 2; }}
</style>
</head><body>

<section class="garde">
  <h1>{titre}</h1>
  <div class="barre"></div>
  <p>Plateforme de tests candidats et pige des annonces.<br>
     Pour la personne qui fait passer les tests et qui suit les annonces.</p>
  <div class="adresse">
    <b>Adresse de l'application</b><br>
    https://tests-candidats.onrender.com/admin
  </div>
  <div class="pied">Document interne &middot; version du __DATE__</div>
</section>

<section class="sommaire">
  <h2>Sommaire</h2>
  <ol>
{sommaire}
  </ol>
</section>

{html}

</body></html>
"""

from datetime import date

MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
a = date.today()
page = page.replace("__DATE__", f"{a.day} {MOIS[a.month - 1]} {a.year}")

apercu = os.path.join(ICI, "_guide.html")
io.open(apercu, "w", encoding="utf-8").write(page)

from playwright.sync_api import sync_playwright
import pathlib

with sync_playwright() as pw:
    n = pw.chromium.launch()
    pg = n.new_page()
    pg.goto(pathlib.Path(apercu).as_uri())
    pg.wait_for_timeout(1200)
    pg.pdf(
        path=os.path.join(ICI, SORTIE),
        format="A4",
        print_background=True,
        margin={"top": "18mm", "bottom": "16mm", "left": "18mm", "right": "18mm"},
        display_header_footer=True,
        header_template="<div></div>",
        footer_template=(
            '<div style="width:100%;font-size:8pt;color:#5A6467;'
            'font-family:sans-serif;padding:0 18mm;display:flex;'
            'justify-content:space-between;">'
            "<span>Guide d'utilisation</span>"
            '<span class="pageNumber"></span></div>'
        ),
    )
    n.close()

print(f"{SORTIE} : {os.path.getsize(os.path.join(ICI, SORTIE)) // 1024} Ko, "
      f"{len(sections)} sections")
