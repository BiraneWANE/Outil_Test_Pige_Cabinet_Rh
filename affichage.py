"""
Mise en forme des donnees au moment de l'affichage.

Deux besoins :

1. Les dates. Le serveur d'hebergement tourne en UTC et les dates sont
   stockees ainsi en base : c'est le bon choix, il ne depend d'aucun pays.
   La conversion vers le fuseau du cabinet se fait donc ici, au dernier
   moment, et jamais a l'enregistrement.

2. Les libelles. Certaines valeurs sont enregistrees dans le detail JSON
   des resultats ("a consolider", "presente"). Les accentuer a la source
   rendrait illisibles les enregistrements deja produits : on les accentue
   donc a l'affichage, en laissant la valeur stockee telle quelle.
"""
import os
from datetime import timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:          # Python anterieur a 3.9
    ZoneInfo = None

FUSEAU = os.environ.get("FUSEAU", "Europe/Paris")

try:
    _ZONE = ZoneInfo(FUSEAU) if ZoneInfo else timezone.utc
except Exception:            # base de fuseaux absente du systeme
    _ZONE = timezone.utc


def local(dt):
    """Convertit une date UTC vers le fuseau d'affichage."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_ZONE)


def date_heure(dt, defaut="-"):
    """23/08/2026 à 21:31"""
    d = local(dt)
    return d.strftime("%d/%m/%Y à %H:%M") if d else defaut


def jour(dt, defaut=""):
    """20260823, pour les noms de fichiers."""
    d = local(dt)
    return d.strftime("%Y%m%d") if d else defaut


LIBELLES = {
    "a consolider": "à consolider",
    "presente": "présente",
    "Sans reponse": "Sans réponse",
}


def joli(valeur):
    """Accentue un libelle enregistre sans accent."""
    return LIBELLES.get(valeur, valeur)
