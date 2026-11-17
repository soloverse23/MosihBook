"""What a proofreader checks in each language the studio writes in. Shared by Text control (the manuscript,
before the art) and Control & correction (the built pages), so both read the words to the same standard."""
from __future__ import annotations

from . import words

COMMON = """\
Read every sentence word by word, as a proofreader, not as a reader: do not skim, do not guess from meaning.
Every error of spelling, conjugation, agreement, grammar or punctuation is a real mistake, however small, and
is reported. ("Never nitpick" means: no opinions on style or taste. It never means letting a language error pass.)
Check in every language:
- spelling of every word, accents and special letters included; a real word used in place of the right one;
- conjugation: the right tense, person and ending; tenses that stay consistent through the story;
- agreement: subject and verb, noun with its articles, adjectives and pronouns (gender and number);
- grammar: a missing or doubled word, a wrong preposition, a sentence with no verb or cut off, a wrong pronoun;
- punctuation: a sentence without its final mark, a missing comma that changes the meaning, quotes or brackets
  that are opened and never closed, a dialogue whose quotes are mixed up;
- capitals at the start of each sentence and on names, and nowhere else by mistake;
- an ellipsis has exactly 3 dots (... or …), never 4 or 2."""

LANGUAGE = {
    "French": """\
French, check all of these:
- accents: é è ê ë à â ù û ô î ï ç and on capitals too (À, É, Ç: « À demain », « Ça »); œ in cœur, sœur, œuf,
  œil, nœud; no accent where none belongs (« téte » -> « tête », « déja » -> « déjà », « voila » -> « voilà »);
- conjugation: the right ending for the person (je mange / tu manges / il mange; je finis / il finit; ils
  mangent); -é / -er / -ez / -ait / -ais / -ai (« il a mangé », « pour manger », « vous mangez »); imperative
  without -s (« mange ! », « va ! ») except before en / y (« manges-en », « vas-y »); subjunctive after
  « il faut que », « pour que », « avant que », « bien que »; passé simple / imparfait / passé composé used
  consistently in the narration; « si » never followed by the conditional (« si j'avais », not « si j'aurais »);
- agreement: past participle with être agrees with the subject (« elles sont parties »), with avoir only with a
  direct object placed before (« les pommes qu'il a mangées »), reflexive verbs; adjectives and determiners agree
  in gender and number; « leur » (before a verb, invariable) / « leurs » (plural noun); « tout / tous / toute /
  toutes »; « quel / quelle / quels / quelles »; numbers « vingt / cent » with -s only when multiplied and last;
- homophones: a / à, ou / où, et / est, son / sont, on / ont, ces / ses / c'est / s'est, ce / se, la / là / l'a,
  peu / peut / peux, quand / quant / qu'en, sans / s'en / c'en, ni / n'y, dans / d'en, mes / mais / met;
- elision: le / la / de / que / ne / je / me / te / se / ce before a vowel or silent h (« l'arbre », « qu'il »,
  « s'il », « jusqu'à », « lorsqu'il »), never before a consonant or aspirated h (« le héros »); the negation keeps
  its « ne » in written text (« je ne sais pas », not « je sais pas ») unless it is a character's spoken voice on
  purpose;
- typography: a space before ; : ! ? and » and after « (the layout makes those spaces non-breaking itself: report
  only a MISSING space, as in « Bonjour! », never ask for a non-breaking one); French quotes « » rather than " ";
  the apostrophe is always the curly French one ’ (the printed book turns a straight ' into ’ by itself, so do
  not report a straight ' alone); an ellipsis has exactly 3 dots, never 4;
  a dash — to open each line of dialogue when the book does that; no space before a comma or a full stop;
  ordinals 1er / 1re / 2e / 3e (never 2ème, 2nd for deuxième is fine only as « second »); capitals only on the
  first word of a title, as French titles do, unless it is a name;
- words: an anglicism or a calque where a French word exists, a word that does not exist, a word a 4 to 8 year old
  French child could not know when a simple one exists (report only when it clearly stops the child).""",
    "English": """\
English, check: its / it's, your / you're, their / there / they're, then / than, to / too, lose / loose,
affect / effect; a / an before a vowel sound; irregular past tenses (caught, not catched); one spelling system
throughout (US or UK, never mixed: color / colour); apostrophes in plurals (apple's -> apples); curly quotes
and apostrophes used the same way throughout.""",
    "German": """\
German, check: capital letters on every noun; ß / ss (dass, muss, groß, Straße); umlauts (ä ö ü), never ae / oe /
ue in place of them; case after prepositions and articles (dem / den / der); verb in second place in main clauses
and last in subordinate clauses; comma before dass, weil, wenn, als, ob, und before a full clause where needed;
German quotes „…“ used the same way throughout; das / dass.""",
    "Spanish": """\
Spanish, check: accents (tildes) on stressed syllables and on question words (qué, cómo, dónde, cuándo, por qué
vs porque); ñ; opening ¿ and ¡ for every question and exclamation; gender and number agreement; ser / estar;
subjunctive after que in wishes and purposes; dialogue dash — used the same way throughout.""",
    "Romanian": """\
Romanian, check: diacritics ă â î ș ț (comma below, not cedilla ş ţ); â inside words and î at the start or end
(cuvânt, înger, a urî); the definite article attached to the noun (băiatul, fata); agreement of adjectives;
hyphens in forms like s-a, l-am, într-o, dintr-un; Romanian quotes „…” used the same way throughout.""",
}


def rules(language: str | None) -> str:
    """The checklist for the book's language: the common checks, then that language's own."""
    lang = words.canonical(language) or str(language or "")
    own = LANGUAGE.get(lang)
    return COMMON + ("\n\n" + own if own else "")
