"""Petit serveur local pour tester la page web (index.html) avant publication.

Tout le calcul se fait désormais dans le navigateur (alchemy.js) : ce serveur
ne fait que servir les fichiers du dossier parent.

Lancement : python3 python/server.py  puis ouvrir http://localhost:8000
"""

from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

from data import DATA_DIR

PORT = 8000


if __name__ == "__main__":
    handler = partial(SimpleHTTPRequestHandler, directory=DATA_DIR)
    print(f"Calculateur d'alchimie : http://localhost:{PORT}")
    HTTPServer(("localhost", PORT), handler).serve_forever()
