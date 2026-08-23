"""
Conservation et effacement des donnees candidats.

La regle appliquee est simple : les donnees nominatives sont conservees
JOURS_CONSERVATION jours apres la creation de l'invitation (180 par
defaut), puis effacees. Ce qui subsiste ensuite (reponses, temps passe,
score) ne permet plus d'identifier personne et sert uniquement a mesurer
la qualite des questions.

On anonymise plutot que de tout supprimer : detruire les reponses
appauvrirait l'analyse des tests sans rien apporter au candidat, dont
l'identite a deja disparu. C'est la minimisation, pas l'effacement total,
qui est demandee ici. La suppression complete reste possible a la demande,
depuis le back-office.

L'hebergement ne fournit pas de planificateur. La purge est donc
declenchee de trois facons, qui aboutissent au meme resultat :
  - au demarrage du serveur ;
  - au plus une fois par jour, a l'ouverture du back-office ;
  - a la demande, depuis la page « Donnees personnelles ».
"""
from datetime import date

import db

_dernier_passage = None


def purger():
    """Anonymise les invitations echues. Renvoie le nombre traite."""
    echues = db.invitations_a_purger()
    for ligne in echues:
        db.anonymiser(ligne["id"])
    return len(echues)


def purger_si_besoin(aujourdhui=None):
    """
    Purge au plus une fois par jour, quel que soit le nombre de visites.

    Le marqueur vit en memoire : un redemarrage du serveur relance un
    passage, ce qui est sans consequence puisque la purge ne fait rien
    quand plus rien n'est echu.
    """
    global _dernier_passage
    jour = aujourdhui or date.today()
    if _dernier_passage == jour:
        return None
    _dernier_passage = jour
    return purger()
