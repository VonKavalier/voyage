#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Voyage : un petit voyage contemplatif, à relancer de temps en temps.

Chaque lancement : un faux chargement de durée variable, une étape racontée,
et la progression avance de quelques pourcents. Pas de défi, pas d'échec.
Les univers (textes, régions, ambiances) sont de simples fichiers JSON
dans le dossier data/.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------
# Réglages
# ----------------------------------------------------------------------------
PROFILS = [
    {"nom": "Trajet quotidien", "lancements": 8, "nb_regions": 3},
    {"nom": "Randonnée", "lancements": 20, "nb_regions": 4},
    {"nom": "Voyage par étapes", "lancements": 45, "nb_regions": 6},
]

CARTE_L = 60
CARTE_H = 9

CHARGEMENT_DISCRET = [
    "Analyse des fichiers en cours...",
    "Synchronisation du cache local...",
    "Vérification de l'intégrité des données...",
    "Indexation en cours...",
    "Nettoyage des fichiers temporaires...",
]

COULEURS = {
    "gris": "90",
    "gris_clair": "37",
    "blanc": "97",
    "vert": "32",
    "cyan": "36",
    "cyan_clair": "96",
    "jaune": "33",
    "magenta": "35",
    "bleu": "34",
    "rouge": "31",
}

# Caractères réservés à la carte (chemin, départ, position, arrivée)
GLYPHES_RESERVES = ".o@X "


# ----------------------------------------------------------------------------
# Affichage
# ----------------------------------------------------------------------------
def couleur_active() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def c(texte: str, couleur: str) -> str:
    if not couleur_active():
        return texte
    return f"\033[{COULEURS[couleur]}m{texte}\033[0m"


def ecrire_paragraphe(texte: str, couleur: str = "gris_clair", largeur: int = 78, retrait: int = 2) -> None:
    marge = " " * retrait
    for ligne in textwrap.wrap(texte, width=largeur, initial_indent=marge, subsequent_indent=marge):
        print(c(ligne, couleur))


def preparer_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    if sys.platform == "win32":
        os.system("")  # active les séquences ANSI dans la console Windows


# ----------------------------------------------------------------------------
# Emplacements des fichiers
# ----------------------------------------------------------------------------
def dossier_utilisateur() -> Path:
    env = os.environ.get("VOYAGE_HOME")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / "voyage"


def fichier_etat() -> Path:
    return dossier_utilisateur() / "etat.json"


def dossier_donnees() -> Path:
    return Path(__file__).resolve().parent / "data"


# ----------------------------------------------------------------------------
# Chargement et validation des univers
# ----------------------------------------------------------------------------
def _liste_textes(valeur, nom: str) -> None:
    ok = isinstance(valeur, list) and valeur and all(isinstance(v, str) and v.strip() for v in valeur)
    if not ok:
        raise ValueError(f"'{nom}' doit être une liste non vide de textes")


def valider_univers(u) -> None:
    """Lève ValueError avec un message clair si l'univers est mal formé."""
    if not isinstance(u, dict):
        raise ValueError("le fichier doit contenir un objet JSON")
    for cle in ("nom", "arrivee"):
        if not isinstance(u.get(cle), str) or not u[cle].strip():
            raise ValueError(f"'{cle}' manquant ou vide")
    for cle in ("departs", "destinations", "chargement", "meteo"):
        _liste_textes(u.get(cle), cle)

    mini = max(p["nb_regions"] for p in PROFILS)
    regions = u.get("regions")
    if not isinstance(regions, list) or len(regions) < mini:
        raise ValueError(f"'regions' doit contenir au moins {mini} régions")
    for i, r in enumerate(regions, 1):
        if not isinstance(r, dict):
            raise ValueError(f"région n°{i} : objet attendu")
        for cle in ("nom", "entree"):
            if not isinstance(r.get(cle), str) or not r[cle].strip():
                raise ValueError(f"région n°{i} : '{cle}' manquant ou vide")
        g = r.get("glyphe")
        if not isinstance(g, str) or len(g) != 1 or g in GLYPHES_RESERVES:
            raise ValueError(
                f"région n°{i} : 'glyphe' doit être un seul caractère, "
                f"différent de {' '.join(GLYPHES_RESERVES.strip())}"
            )
        if r.get("couleur") not in COULEURS:
            raise ValueError(f"région n°{i} : 'couleur' doit être parmi {', '.join(COULEURS)}")
        for cle in ("lieux", "ambiance", "rencontres", "trouvailles"):
            try:
                _liste_textes(r.get(cle), cle)
            except ValueError as err:
                raise ValueError(f"région n°{i} : {err}") from None


def charger_univers() -> dict:
    """Charge data/*.json puis <dossier utilisateur>/univers/*.json."""
    univers = {}
    for dossier in (dossier_donnees(), dossier_utilisateur() / "univers"):
        if not dossier.is_dir():
            continue
        for f in sorted(dossier.glob("*.json")):
            try:
                u = json.loads(f.read_text(encoding="utf-8"))
                valider_univers(u)
            except (OSError, ValueError) as err:
                print(f"  Univers ignoré ({f.name}) : {err}", file=sys.stderr)
                continue
            univers[f.stem] = u
    return univers


# ----------------------------------------------------------------------------
# Sauvegarde
# ----------------------------------------------------------------------------
def charger_etat():
    f = fichier_etat()
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def sauver_etat(etat: dict) -> None:
    f = fichier_etat()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)


def archiver_etat(etat: dict) -> None:
    arch = dossier_utilisateur() / "archive"
    arch.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fichier_etat(), arch / f"voyage-{etat['graine']}.json")


# ----------------------------------------------------------------------------
# Carte (déterministe à partir de la graine)
# ----------------------------------------------------------------------------
def nouvelle_carte(graine: int) -> dict:
    r = random.Random(graine)
    pts = []
    y = 4
    for x in range(CARTE_L):
        ny = y
        if r.randrange(100) < 45:
            ny = max(1, min(CARTE_H - 2, y + r.randint(-2, 2)))
        if ny == y:
            pts.append((x, y))
        else:
            d = 1 if ny > y else -1
            yy = y
            while yy != ny:
                yy += d
                pts.append((x, yy))
        y = ny
    r2 = random.Random(graine + 1)
    decor = [[r2.random() for _ in range(CARTE_L)] for _ in range(CARTE_H)]
    return {"pts": pts, "decor": decor}


def position(etat: dict, carte: dict) -> dict:
    pts = carte["pts"]
    i = int(etat["progression"] / 100.0 * (len(pts) - 1))
    x, y = pts[i]
    nr = len(etat["sequence"])
    k = min(nr - 1, int(x / CARTE_L * nr))
    return {"index": i, "x": x, "y": y, "k": k, "region": etat["sequence"][k]}


def afficher_carte(etat: dict, u: dict, carte: dict) -> None:
    pos = position(etat, carte)
    fini = etat["progression"] >= 100
    max_x = CARTE_L - 1 if fini else min(CARTE_L - 1, pos["x"] + 4)
    seq = etat["sequence"]
    nr = len(seq)

    grille = [[(" ", "gris") for _ in range(CARTE_L)] for _ in range(CARTE_H)]
    for ligne in range(CARTE_H):
        for col in range(max_x + 1):
            if carte["decor"][ligne][col] < 0.16:
                k = min(nr - 1, int(col / CARTE_L * nr))
                reg = u["regions"][seq[k]]
                grille[ligne][col] = (reg["glyphe"], reg["couleur"])

    for x, y in carte["pts"][: pos["index"] + 1]:
        grille[y][x] = (".", "gris_clair")
    x0, y0 = carte["pts"][0]
    grille[y0][x0] = ("o", "blanc")
    grille[pos["y"]][pos["x"]] = ("X" if fini else "@", "blanc")

    print()
    for ligne in grille:
        print("  " + "".join(c(ch, col) for ch, col in ligne))


def afficher_barre(etat: dict, u: dict, carte: dict) -> None:
    pos = position(etat, carte)
    p = int(etat["progression"])
    plein = int(p / 100.0 * 40)
    print()
    print(c("  [" + "=" * plein + "-" * (40 - plein) + f"]  {p} %", "gris_clair"))
    print(c(f"  {u['regions'][pos['region']]['nom']}", "gris"))
    print()


# ----------------------------------------------------------------------------
# Bilan, journal, export
# ----------------------------------------------------------------------------
def _date(iso: str, fmt: str) -> str:
    return datetime.fromisoformat(iso).strftime(fmt)


def lignes_bilan(etat: dict, u: dict) -> list:
    profil = PROFILS[etat["profil"]]
    noms = [u["regions"][i]["nom"] for i in etat["sequence"]]
    souvenirs = etat["souvenirs"]
    lignes = [
        f"Voyage       : {profil['nom']} ({u['nom']})",
        f"Départ       : {etat['depart']}",
        f"Destination  : {etat['destination']}",
        f"Début        : {_date(etat['debut'], '%d/%m/%Y %H:%M')}",
    ]
    if etat.get("fin"):
        lignes.append(f"Arrivée      : {_date(etat['fin'], '%d/%m/%Y %H:%M')}")
    lignes += [
        f"Étapes       : {etat['etape']}",
        f"Progression  : {int(etat['progression'])} %",
        f"Régions      : {'  >  '.join(noms)}",
        "Souvenirs    : " + (" ; ".join(souvenirs) if souvenirs else "aucun"),
    ]
    return lignes


def afficher_bilan(etat: dict, u: dict) -> None:
    print()
    for ligne in lignes_bilan(etat, u):
        ecrire_paragraphe(ligne)
    print()


def afficher_journal(etat: dict) -> None:
    print()
    for e in etat["journal"]:
        entete = f"  [{_date(e['date'], '%d/%m %H:%M')}] Étape {e['etape']} - {e['region']} - {int(e['progression'])} %"
        print(c(entete, "gris"))
        ecrire_paragraphe(e["texte"], retrait=4)
        print()


def exporter_journal(etat: dict, u: dict) -> Path:
    dossier = dossier_utilisateur()
    dossier.mkdir(parents=True, exist_ok=True)
    nom = f"journal-{etat['graine']}-{datetime.now().strftime('%Y%m%d-%H%M')}.txt"
    f = dossier / nom
    out = ["JOURNAL DE VOYAGE", "=================", *lignes_bilan(etat, u), ""]
    for e in etat["journal"]:
        out.append(
            f"[{_date(e['date'], '%d/%m/%Y %H:%M')}] Étape {e['etape']} - {e['region']} - {int(e['progression'])} %"
        )
        out.append(e["texte"])
        out.append("")
    f.write_text("\n".join(out), encoding="utf-8")
    return f


# ----------------------------------------------------------------------------
# Interactions
# ----------------------------------------------------------------------------
def demander(invite: str) -> str:
    try:
        return input(invite).strip()
    except EOFError:
        return ""


def choisir(titre: str, options: list) -> int:
    print()
    print(c(f"  {titre}", "gris_clair"))
    for i, o in enumerate(options, 1):
        print(c(f"    {i}) {o}", "gris"))
    while True:
        rep = demander("  > ")
        if rep.isdigit() and 1 <= int(rep) <= len(options):
            return int(rep) - 1
        if not sys.stdin.isatty() and rep == "":
            raise SystemExit("Entrée interrompue.")


def attendre_touche() -> None:
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.getch()
        else:
            import termios
            import tty

            fd = sys.stdin.fileno()
            ancien = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, ancien)
    except Exception:
        try:
            input()
        except (EOFError, OSError):
            pass


def effacer_ecran() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


def duree_chargement(rapide: bool) -> int:
    if rapide:
        return 1
    t = random.randrange(100)
    if t < 60:
        return random.randint(4, 19)      # court
    if t < 90:
        return random.randint(25, 79)     # moyen
    return random.randint(100, 239)       # longue marche


def chargement(secondes: int, messages: list) -> None:
    spin = "|/-\\"
    fin = time.monotonic() + secondes
    msg = random.choice(messages)
    suivant = time.monotonic() + random.randint(3, 7)
    i = 0
    try:
        while time.monotonic() < fin:
            if time.monotonic() >= suivant:
                msg = random.choice(messages)
                suivant = time.monotonic() + random.randint(3, 7)
            ligne = f"  {spin[i % 4]} {msg}".ljust(70)
            sys.stdout.write("\r" + c(ligne, "gris"))
            sys.stdout.flush()
            i += 1
            time.sleep(0.15)
    finally:
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()


def moment_de_la_journee() -> str:
    h = datetime.now().hour
    if h < 6:
        return "Avant l'aube."
    if h < 10:
        return "Tôt le matin."
    if h < 12:
        return "Fin de matinée."
    if h < 14:
        return "Midi approche."
    if h < 18:
        return "L'après-midi s'étire."
    if h < 21:
        return "Le soir tombe."
    return "La nuit est calme."


# ----------------------------------------------------------------------------
# Voyage
# ----------------------------------------------------------------------------
def nouveau_voyage(univers: dict) -> dict:
    cles = sorted(univers)
    iu = choisir("Univers", [univers[k]["nom"] for k in cles])
    ip = choisir("Durée du voyage", [
        "Trajet quotidien (court)", "Randonnée (moyen)", "Voyage par étapes (long)",
    ])
    cle = cles[iu]
    u = univers[cle]
    profil = PROFILS[ip]

    graine = random.randint(1000, 900000)
    r = random.Random(graine)
    sequence = r.sample(range(len(u["regions"])), profil["nb_regions"])

    etat = {
        "graine": graine,
        "univers": cle,
        "profil": ip,
        "sequence": sequence,
        "depart": r.choice(u["departs"]),
        "destination": r.choice(u["destinations"]),
        "debut": datetime.now().isoformat(timespec="seconds"),
        "fin": None,
        "progression": 0.0,
        "etape": 0,
        "souvenirs": [],
        "journal": [],
    }
    sauver_etat(etat)
    print()
    print(c(f"  Départ : {etat['depart']}.", "gris_clair"))
    print(c(f"  Destination : {etat['destination']}.", "gris_clair"))
    return etat


def lancer_etape(etat: dict, u: dict, rapide: bool, discret: bool) -> None:
    profil = PROFILS[etat["profil"]]
    carte = nouvelle_carte(etat["graine"])
    avant = position(etat, carte)

    print()
    chargement(duree_chargement(rapide), CHARGEMENT_DISCRET if discret else u["chargement"])

    # Progression
    moyenne = 100.0 / profil["lancements"]
    gain = moyenne * (0.5 + random.randint(0, 100) / 100.0)
    nouvelle = min(100.0, etat["progression"] + gain)
    if nouvelle >= 97.0:
        nouvelle = 100.0
    etat["progression"] = round(nouvelle, 1)
    etat["etape"] += 1
    arrive = etat["progression"] >= 100

    pos = position(etat, carte)
    region = u["regions"][pos["region"]]
    changement = pos["k"] != avant["k"] or etat["etape"] == 1

    # Récit : déterministe pour une étape donnée
    rng = random.Random(etat["graine"] + 7919 * etat["etape"])
    parts = [moment_de_la_journee()]
    if changement:
        parts.append(region["entree"])
    parts.append(rng.choice(region["lieux"]))
    parts.append(rng.choice(u["meteo"]))
    parts.append(rng.choice(region["ambiance"]))
    if rng.randrange(100) < 45:
        parts.append(rng.choice(region["rencontres"]))
    if rng.randrange(100) < 30:
        trouvaille = rng.choice(region["trouvailles"])
        parts.append(f"On ramasse {trouvaille}.")
        etat["souvenirs"].append(trouvaille)
    if arrive:
        parts.append(f"Devant {etat['destination']}, le chemin s'achève.")
        parts.append(u["arrivee"])
        etat["fin"] = datetime.now().isoformat(timespec="seconds")
    texte = " ".join(parts)

    etat["journal"].append({
        "date": datetime.now().isoformat(timespec="seconds"),
        "etape": etat["etape"],
        "region": region["nom"],
        "progression": etat["progression"],
        "texte": texte,
    })
    sauver_etat(etat)

    # Affichage
    print(c(f"  Étape {etat['etape']}  -  {datetime.now().strftime('%H:%M')}", "gris"))
    print()

    if not discret:
        ecrire_paragraphe(texte)
        afficher_carte(etat, u, carte)
        afficher_barre(etat, u, carte)

    if arrive:
        print(c("  Voyage terminé.", "blanc"))
        afficher_bilan(etat, u)
        f = exporter_journal(etat, u)
        print(c(f"  Journal complet : {f}", "gris"))
        print()


# ----------------------------------------------------------------------------
# Programme principal
# ----------------------------------------------------------------------------
def lire_arguments(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Un petit voyage contemplatif : un pas de plus à chaque lancement.",
    )
    p.add_argument("--journal", action="store_true", help="affiche le journal complet du voyage en cours")
    p.add_argument("--bilan", action="store_true", help="affiche un résumé (départ, régions, souvenirs)")
    p.add_argument("--carte", action="store_true", help="affiche la carte et la progression, sans avancer")
    p.add_argument("--export", action="store_true", help="écrit bilan + journal dans un fichier texte")
    p.add_argument("--nouveau", action="store_true", help="archive le voyage en cours et en commence un autre")
    p.add_argument("--discret", action="store_true", help="faux messages techniques pendant le chargement, efface l'écran ensuite")
    p.add_argument("--rapide", action="store_true", help="chargement d'une seconde (pour tester)")
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = lire_arguments(argv)
    preparer_console()

    univers = charger_univers()
    if not univers:
        print("Aucun univers valide trouvé dans le dossier data/.", file=sys.stderr)
        return 1

    etat = charger_etat()
    if etat and etat["univers"] not in univers:
        print(f"L'univers '{etat['univers']}' du voyage en cours est introuvable. "
              "Utilisez --nouveau pour repartir.", file=sys.stderr)
        if not args.nouveau:
            return 1

    # Consultation
    if args.journal or args.bilan or args.carte or args.export:
        if not etat:
            print(c("  Aucun voyage en cours.", "gris"))
            return 0
        u = univers[etat["univers"]]
        if args.bilan:
            afficher_bilan(etat, u)
        if args.journal:
            afficher_journal(etat)
        if args.carte:
            carte = nouvelle_carte(etat["graine"])
            afficher_carte(etat, u, carte)
            afficher_barre(etat, u, carte)
        if args.export:
            print(c(f"  Journal exporté : {exporter_journal(etat, u)}", "gris_clair"))
        return 0

    # Voyage terminé : proposer d'en commencer un autre
    nouveau = args.nouveau
    if etat and etat["progression"] >= 100 and not nouveau:
        print()
        print(c("  Le dernier voyage est terminé.", "gris_clair"))
        afficher_bilan(etat, univers[etat["univers"]])
        if not demander("  Repartir pour un nouveau voyage ? (o/N) ").lower().startswith(("o", "y")):
            return 0
        nouveau = True

    if nouveau and etat:
        archiver_etat(etat)
    if nouveau or not etat:
        etat = nouveau_voyage(univers)

    lancer_etape(etat, univers[etat["univers"]], args.rapide, args.discret)

    if args.discret:
        print(c("  Appuyez sur une touche...", "gris"))
        attendre_touche()
        effacer_ecran()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
