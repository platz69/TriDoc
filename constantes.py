import re

# from pdfminer.utils import isnumber

"""______________________________________________________________________________________________
            CONSTANTES BACK
 _____________________________________________________________________________________________"""
EXTENSIONS_TRAITEES = ['doc', 'docx', 'pdf', 'txt', 'odt', 'rtf']
# MOTS_CLES_FILE    = "keywords.json"
RULES_FILE        = "rules.csv"
CONFIG_FILE      = "configuration.json"
DIC_FRANCAIS_FILE  = 'French.sans.accents.dic'
TRADUCTIONS_FILE = 'traductions.csv'
REGEX_CHERCHEES   = {
    "address":  re.compile(r"\d{1,5}(?: (?:bis|ter))?,? (?:av|avenue|bd|boulevard|chemin|cours|impasse|rue) [.A-Za-zÀ-ÖØ-öø-ÿ- ]+", re.IGNORECASE),
    "cp":       re.compile(r"\d{5} +[A-ZÉÈÊËÎÏÔÖÛÜ]+(?: +CEDEX(?: +\d{1,5})?)?", re.IGNORECASE),
    "iban":     re.compile(r"\bFR\d{2}\s?(?:\d{4}\s?){2}\d{2}\s?[A-Z0-9]{2}\s?(?:[A-Z0-9]{4}\s?){2}[A-Z0-9]\d{2}", re.IGNORECASE),
    "mail":     re.compile(r"\b[\w.-]+@[\w.-]+\.[a-zA-Z]{2,6}", re.IGNORECASE),
    "name":     re.compile(r"\b[A-Z]\w{2,}", re.IGNORECASE), # une majuscule suivie d'au moins 2 lettres
    "tel":      re.compile(r"(?:0|\+33 |\+33 \(0\) ?)\d(?:[-. ]?\d{2}){4}", re.IGNORECASE),
    "web":      re.compile(r"(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-z]{2,6}", re.IGNORECASE),
    "suspect":  re.compile(r"\b\w{3,}\b", re.IGNORECASE)
}
REGEX_CHERCHEES_v2026 = {
    "address": re.compile(r"(?:\d{1,5}(?: (?:bis|ter))?,? )?(?:av|avenue|bd|boulevard|chemin|cours|impasse|rue) ['.0-9A-Za-zÀ-ÖØ-öø-ÿ- ]+", re.IGNORECASE),
    "mail":    re.compile(r"[\w.-]+@[\w.-]+\.[a-zA-Z]{2,6}", re.IGNORECASE),
    "tel":     re.compile(r"(?:0|\+\d{2,3} |\+\d{2,3} \(0\) ?)\d(?:[-_. ]?\d{2}){4}", re.IGNORECASE),
    "web":     re.compile(r"(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-z]{2,6}", re.IGNORECASE)
}
# pas moins de 5 chiffres
# plus de 2 lettres
# pas plus de 4 caractères identiques uniquement
# pas de point aux extrémités

REGEX_IA = {
    "address": re.compile(r"(?:(?:(?:(?:n[°ºo]|num(?:[eé]ro)?\.?)\s*)?\d{1,5}(?:(?:\s*,\s*|\s*[-/]\s*|\s*)(?:bis|ter)|(?:\s*[-/]\s*|\s?)[a-z]\d?)?(?:(?:\s*[-/]\s*|\s+(?:à|au|et)\s+)\d{1,5}(?:(?:\s*,\s*|\s*[-/]\s*|\s*)(?:bis|ter|quater|quinquies)|(?:\s*[-/]\s*|\s?)[a-z]\d?)?)*(?:\s*,\s*|\s+))(?:(?:(?:grande?|grand|gde|petite?|pte|anc(?:ien(?:ne)?)?\.?|vieux|vieille|nouvelle|haut|bas)\s+|grand['’])(?:rue|r(?:ou)?te|av(?:enue)?|ch(?:emin)?|imp(?:asse)?|b(?:oul(?:evard)?|d)|all[ée]e)\.?(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9](?:[A-Za-zÀ-ÖØ-öø-ÿ0-9'’.°\- ]*[A-Za-zÀ-ÖØ-öø-ÿ0-9.])?)?|(?:rue|ruel(?:le)?|r|av(?:e|enue)?|b(?:oul(?:evard)?|vd|lvd|ld|d)|ch(?:e|em|m|emin)?|cours?|crs|imp(?:asse)?|al(?:l(?:[ée]e)?)?|pl(?:ace)?|quai|q|r(?:ou)?te?|pas(?:s(?:age)?)?|sq(?:uare)?|f(?:aub(?:ourg)?|b?g)|chauss[ée]e|chau|chs|sen(?:t(?:ier|e)?)?|villa|vill|vla|cit[ée]|clos|rond[- ]?point|rpt|terre[- ]?plein|esp(?:l(?:anade)?)?|prom(?:enade)?|trav(?:erse)?|mont(?:[ée]e)?|mte|parv(?:is)?|r[ée]s(?:i(?:dence)?)?|lot(?:i(?:ssement)?)?|ham(?:e(?:au)?)?|voie|mail|pont|parc|bouc(?:le)?|vene(?:lle)?|ramp(?:e)?|desc(?:ente)?|esca(?:lier)?|corn(?:iche)?|roca(?:de)?|c[ôo]te|vall(?:on)?|dom(?:a(?:ine)?)?|p[ée]ri(?:ph[ée]rique)?|lieu[- ]?dit|ld|z\.?a\.?c?|z\.?i|zone|centre commercial|ccal|village|vlge)\.?\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9](?:[A-Za-zÀ-ÖØ-öø-ÿ0-9'’.°\- ]*[A-Za-zÀ-ÖØ-öø-ÿ0-9.])?)|(?:r[nd]|[dn])\s?\d{1,4})", re.IGNORECASE),
    "name":    re.compile(r"(?:Madame|Mademoiselle|Monsieur|Messieurs|MLLE|Mlle|MME|Mme|MM|Mr|M)(?: et Mme)? [A-ZÀ-ÖØ-Þ]{2,}(?: [A-ZÀ-ÖØ-Þ]{2,})?"),
    "tel":     re.compile(r"(\d{2}([-. ])\d{2}(?:\2\d{2}){3})", re.IGNORECASE)  # attention on garde la 1ère composante d'un tuple capturé, sinon faire \d{2}(?:[-. ]\d{2}){4}", re.IGNORECASE)
}

MOTS_CLES_IGNORES = {"sarl", "ttc", "tva", "TVA INTRACOMMUNAU"} \
                    | {f"{h}h" for h in range(0, 25)} \
                    | {f"{h}h{m}" for h in range(24) for m in range(60) if m % 15 == 0}  # mots et heures trop fréquents

"""______________________________________________________________________________________________
        CONSTANTES GUI
 _____________________________________________________________________________________________"""

ICONES_DIR = './icons'

LANGUAGES = ["de", "en", "fr"]

LARGEUR_CADRES_MIN = 500
LARGEUR_CADRES_MAX = 1000
HAUTEUR_CADRES     = 120

LARGEUR_POPUP         = 300
HAUTEUR_POPUP         = 150
OFFSET_POPUP          = 100
DELAI_AVANT_FERMETURE = 2000

DELAI_ASTUCES         = 500
COULEUR_ASTUCES       = 'plum1'
COULEUR_MESSAGES      = 'red'