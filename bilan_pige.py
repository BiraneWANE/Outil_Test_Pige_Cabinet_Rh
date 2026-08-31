"""
Bilan de la pige : les chiffres a citer dans le rapport.

    python bilan_pige.py

Lit ce qui est en base et rend un etat des lieux : volumes par
perimetre, apport reel de chaque source, entreprises les plus actives,
distribution des anciennetes. Aucune ecriture, on peut le relancer
autant qu'on veut.
"""
import db


def ligne(titre):
    print(f"\n{titre}")
    print("-" * len(titre))


def lire(requete, valeurs=None):
    """Sans valeurs, on n'en passe aucune : sinon psycopg interprete les
    « % » des LIKE comme des emplacements de parametres."""
    with db.curseur() as cur:
        if valeurs is None:
            cur.execute(requete)
        else:
            cur.execute(requete, valeurs)
        return cur.fetchall()


# ------------------------------------------------------------------
print("=" * 62)
print("BILAN DE LA PIGE")
print("=" * 62)

total = lire("""
    SELECT count(*) AS brut,
           count(*) FILTER (WHERE NOT ecartee) AS n,
           count(*) FILTER (WHERE NOT ecartee AND en_ligne) AS en_ligne,
           count(*) FILTER (WHERE ecartee) AS ecartees
      FROM annonce
""")[0]
print(f"\n{total['brut']} annonces collectees.")
print(f"{total['ecartees']} ecartees, {total['n']} prospects retenus, "
      f"dont {total['en_ligne']} en ligne.")

ligne("Pourquoi des annonces sont ecartees")
for r in lire("""
    SELECT motif_ecart, count(*) AS n FROM annonce
     WHERE ecartee GROUP BY 1 ORDER BY n DESC
"""):
    part = 100.0 * r["n"] / max(total["brut"], 1)
    print(f"  {(r['motif_ecart'] or 'non precise')[:45]:<46} {r['n']:>5}  ({part:.1f} %)")

# ------------------------------------------------------------------
ligne("Par perimetre et metier")
for r in lire("""
    SELECT partie, metier, count(*) AS n,
           count(DISTINCT entreprise_cle) AS entreprises
      FROM annonce WHERE NOT ecartee GROUP BY partie, metier ORDER BY partie, n DESC
"""):
    print(f"  partie {r['partie']} | {r['metier']:<17} "
          f"{r['n']:>5} annonces | {r['entreprises']:>4} entreprises")

# ------------------------------------------------------------------
ligne("Apport reel de chaque source")
# La question qui justifie de garder deux sources : combien Adzuna
# apporte-t-il d'annonces que France Travail n'a pas ?
for r in lire("""
    SELECT CASE
             WHEN sources LIKE '%adzuna%' AND sources LIKE '%france_travail%'
                  THEN 'les deux'
             WHEN sources LIKE '%adzuna%' THEN 'Adzuna seul'
             ELSE 'France Travail seul'
           END AS origine,
           count(*) AS n
      FROM annonce WHERE NOT ecartee GROUP BY 1 ORDER BY n DESC
"""):
    part = 100.0 * r["n"] / max(total["n"], 1)
    print(f"  {r['origine']:<22} {r['n']:>5} annonces  ({part:.1f} %)")

# ------------------------------------------------------------------
ligne("Types de contrat, partie 1 (missions courtes attendues)")
for r in lire("""
    SELECT COALESCE(type_contrat, 'non precise') AS contrat, count(*) AS n
      FROM annonce WHERE partie = 1 AND NOT ecartee GROUP BY 1 ORDER BY n DESC LIMIT 10
"""):
    print(f"  {r['contrat'][:44]:<45} {r['n']:>5}")

# ------------------------------------------------------------------
ligne("Ou sont les annonces de la partie 2")
for r in lire("""
    SELECT COALESCE(commune, 'non precisee') AS commune, count(*) AS n
      FROM annonce WHERE partie = 2 AND NOT ecartee GROUP BY 1 ORDER BY n DESC LIMIT 12
"""):
    print(f"  {r['commune'][:30]:<31} {r['n']:>5}")

# ------------------------------------------------------------------
ligne("Anciennete des annonces en ligne")
for r in lire("""
    SELECT CASE
             WHEN j < 7  THEN 'moins d une semaine'
             WHEN j < 15 THEN '1 a 2 semaines'
             WHEN j < 31 THEN '2 a 4 semaines'
             WHEN j < 61 THEN '1 a 2 mois'
             ELSE 'plus de 2 mois'
           END AS tranche,
           min(j) AS ordre, count(*) AS n
      FROM (SELECT (CURRENT_DATE - COALESCE(publiee_le, vue_le_premier)) AS j
              FROM annonce WHERE en_ligne AND NOT ecartee) t
     GROUP BY 1 ORDER BY ordre
"""):
    print(f"  {r['tranche']:<22} {r['n']:>5}")

# ------------------------------------------------------------------
ligne("Les 15 entreprises les plus actives")
for r in lire("""
    SELECT max(entreprise) AS entreprise,
           count(*) FILTER (WHERE en_ligne) AS ouverts,
           count(*) AS total,
           string_agg(DISTINCT commune, ', ') AS communes
      FROM annonce WHERE entreprise_cle <> '' AND NOT ecartee
     GROUP BY entreprise_cle
     ORDER BY ouverts DESC, total DESC LIMIT 15
"""):
    lieux = (r["communes"] or "")[:38]
    print(f"  {r['entreprise'][:34]:<35} {r['ouverts']:>3} postes | {lieux}")

# ------------------------------------------------------------------
ligne("Les 10 annonces qui trainent le plus (meilleurs prospects)")
for r in lire("""
    SELECT entreprise, intitule, commune,
           (CURRENT_DATE - COALESCE(publiee_le, vue_le_premier)) AS jours
      FROM annonce WHERE en_ligne AND NOT ecartee
     ORDER BY jours DESC NULLS LAST LIMIT 10
"""):
    print(f"  {r['jours']:>4} j | {(r['entreprise'] or 'non precisee')[:26]:<27} "
          f"| {r['intitule'][:38]:<39} | {r['commune'] or ''}")

# ------------------------------------------------------------------
print("\n" + "=" * 62)
