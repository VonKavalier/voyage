"""Vérifie les univers JSON et le déterminisme de la carte.

Lancer depuis la racine du dépôt :  python -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import voyage  # noqa: E402


class TestUnivers(unittest.TestCase):
    def test_tous_les_fichiers_sont_valides(self):
        fichiers = sorted((RACINE / "data").glob("*.json"))
        self.assertTrue(fichiers, "aucun fichier dans data/")
        for f in fichiers:
            with self.subTest(fichier=f.name):
                voyage.valider_univers(json.loads(f.read_text(encoding="utf-8")))

    def test_univers_incomplet_refuse(self):
        with self.assertRaises(ValueError):
            voyage.valider_univers({"nom": "Vide"})

    def test_glyphe_reserve_refuse(self):
        u = json.loads((RACINE / "data" / "fantasy.json").read_text(encoding="utf-8"))
        u["regions"][0]["glyphe"] = "@"
        with self.assertRaises(ValueError):
            voyage.valider_univers(u)


class TestCarte(unittest.TestCase):
    def test_meme_graine_meme_carte(self):
        a = voyage.nouvelle_carte(12345)
        b = voyage.nouvelle_carte(12345)
        self.assertEqual(a["pts"], b["pts"])
        self.assertEqual(a["decor"], b["decor"])

    def test_chemin_continu_de_gauche_a_droite(self):
        pts = voyage.nouvelle_carte(777)["pts"]
        self.assertEqual(pts[0][0], 0)
        self.assertEqual(pts[-1][0], voyage.CARTE_L - 1)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.assertLessEqual(abs(x2 - x1), 1)
            self.assertLessEqual(abs(y2 - y1), 1)


if __name__ == "__main__":
    unittest.main()
