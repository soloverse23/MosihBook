"""The languages a book can be written in, and the few words the software itself prints in a book.

Everything else a reader sees is written by the author (or Claude) in the book's language. These are
the fixed labels: the closing "The End", the about-the-author heading, the certificate and the default
copyright notice. A book can override any of them with `words:` in book.yaml.
"""
from __future__ import annotations

import re
import unicodedata

LANGUAGES = ("English", "French", "German", "Romanian", "Spanish")

_ALIASES = {
    "english": "English", "en": "English", "anglais": "English", "englisch": "English", "engleza": "English",
    "ingles": "English",
    "french": "French", "fr": "French", "francais": "French", "franzosisch": "French", "franceza": "French",
    "frances": "French",
    "german": "German", "de": "German", "deutsch": "German", "germany": "German", "allemand": "German",
    "germana": "German", "aleman": "German",
    "romanian": "Romanian", "ro": "Romanian", "romana": "Romanian", "roumain": "Romanian", "rumanisch": "Romanian",
    "rumano": "Romanian",
    "spanish": "Spanish", "es": "Spanish", "espanol": "Spanish", "castellano": "Spanish", "espagnol": "Spanish",
    "spanisch": "Spanish", "spaniola": "Spanish",
}


def canonical(language: str | None) -> str | None:
    """'fr', 'Français', 'germany' -> 'French', 'German'; None when it is not a supported language."""
    if not language or not str(language).strip():
        return "English"
    plain = unicodedata.normalize("NFKD", str(language).strip().lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    plain = re.split(r"[\s_(-]", plain)[0]
    return _ALIASES.get(plain)


KEYS = ("the_end", "about_author", "well_done", "name", "date", "copyright")

# {year} and {author} are filled in when the page is laid out
TABLE = {
    "English": {
        "the_end": "The End", "about_author": "About the Author", "well_done": "Well done!",
        "name": "Name", "date": "Date",
        "copyright": "Text copyright © {year} {author}\nAll rights reserved.\n\nNo part of this book may be "
                     "reproduced in any form without written permission from the author, except for brief "
                     "quotations in reviews.",
    },
    "French": {
        "the_end": "Fin", "about_author": "Qui a écrit ce livre ?", "well_done": "Bravo !",
        "name": "Prénom", "date": "Date",
        "copyright": "Texte © {year} {author}\nTous droits réservés.\n\nAucune partie de ce livre ne peut être "
                     "reproduite sous quelque forme que ce soit sans l’autorisation écrite de l’auteur, sauf de "
                     "courtes citations dans le cadre d’une critique.",
    },
    "German": {
        "the_end": "Ende", "about_author": "Wer hat dieses Buch geschrieben?", "well_done": "Super gemacht!",
        "name": "Name", "date": "Datum",
        "copyright": "Text © {year} {author}\nAlle Rechte vorbehalten.\n\nKein Teil dieses Buches darf ohne "
                     "schriftliche Genehmigung des Autors in irgendeiner Form vervielfältigt werden, ausgenommen "
                     "kurze Zitate in Rezensionen.",
    },
    "Romanian": {
        "the_end": "Sfârșit", "about_author": "Cine a scris această carte?", "well_done": "Bravo!",
        "name": "Nume", "date": "Data",
        "copyright": "Text © {year} {author}\nToate drepturile rezervate.\n\nNicio parte a acestei cărți nu "
                     "poate fi reprodusă sub nicio formă fără permisiunea scrisă a autorului, cu excepția unor "
                     "scurte citate în recenzii.",
    },
    "Spanish": {
        "the_end": "Fin", "about_author": "¿Quién escribió este libro?", "well_done": "¡Muy bien!",
        "name": "Nombre", "date": "Fecha",
        "copyright": "Texto © {year} {author}\nTodos los derechos reservados.\n\nNinguna parte de este libro "
                     "puede reproducirse de ninguna forma sin el permiso por escrito del autor, salvo breves "
                     "citas en reseñas.",
    },
}


def word(book, key: str, **fill) -> str:
    """The book's own word for `key` (book.yaml `words:`), else the built-in one for its language."""
    own = getattr(getattr(book, "words", None), key, None)
    text = own or TABLE.get(canonical(book.language) or "English", TABLE["English"])[key]
    return text.format(**fill) if fill else text


# French puts a thin no-break space before ! ? ; : » and after «, so the mark never starts a line
_FR_BEFORE = re.compile(r"[   ]+([!?;:»])")
_FR_AFTER = re.compile(r"«[   ]+")


def typeset(text: str, language: str | None) -> str:
    """Language typography for set text (not for prompts): French spaces that never break."""
    if canonical(language) != "French":
        return text
    return _FR_AFTER.sub("« ", _FR_BEFORE.sub(" \\1", text))
