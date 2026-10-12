import os.path
import csv
import json
from docx2txt import process
# from pdfminer.high_level import extract_text as pdfminer_get_text
# from pypdf import PdfReader
# import pdfplumber
import pymupdf

from constantes import *


# Chargement de la configuration
def load_config():
    with open(CONFIG_FILE, "r", encoding='utf-8') as f:
        return json.load(f)


# Sauvegarde de la configuration
def save_config(conf):
    with open(CONFIG_FILE, "w", encoding='utf-8') as f:
        json.dump(conf, f, ensure_ascii=False, indent=4)


def save_rules_csv(rules_list):
    with open(RULES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        for rule in rules_list:
            writer.writerow([os.path.normpath(rule["folder"]), *rule["keywords"]])


# # Chargement des mots-clés
# def load_keywords():
#     if os.path.exists(MOTS_CLES_FILE):
#         with open(MOTS_CLES_FILE, "r", encoding='utf-8') as f:
#             return json.load(f)
#     return {}


def load_rules():
    if not os.path.exists(RULES_FILE):
        return []

    rules = []
    with open(RULES_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        for line_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue
            if not row[0].strip():
                raise ValueError(f"Règle incomplète dans {RULES_FILE}, ligne {line_number}")

            folder = os.path.normpath(row[0].strip())
            rules.append({
                "folder": folder,
                "keywords": [keyword.strip() for keyword in row[1:] if keyword.strip()],
            })

    return rules

# Chargement des traductions v3
def load_translations():
    translations = {}
    if os.path.exists(TRADUCTIONS_FILE):
        with open(TRADUCTIONS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                for lang, text in row.items():
                    row[lang] = text.replace('\\n', '\n')  # Remplace les séquences \n par de vrais sauts de ligne
                translations[row['key']] = row
    return translations


def get_text_from_pdf(file_path, method):
    match method:
        case 'pymupdf':
            with pymupdf.open(file_path) as doc:
                return "".join(page.get_text() for page in doc)
        # case 'pypdf':
        #     reader = PdfReader(file_path)
        #     return "".join(page.extract_text() or "" for page in reader.pages)
        # case 'pdfminer':
        #     return pdfminer_get_text(file_path)
        # case 'pdfplumber':
        #     with pdfplumber.open(file_path) as pdf:
        #         return "".join(page.extract_text() or "" for page in pdf.pages)
        case _:
            raise ValueError(f"Méthode d'extraction PDF inconnue : {method}")


# extraction du texte d'un fichier selon son extension (utilisé par scan() et analyse_file())
def extract_text_from_file(file_path):
    extension = os.path.splitext(file_path)[1].lower().lstrip('.')
    match extension:
        case 'docx':
            return process(file_path)
        case 'pdf':
            return get_text_from_pdf(file_path, 'pymupdf')  # pymupdf > pypdf > pdfminer > pdfplumber
        case 'txt':
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        case _:
            # formats reconnus (doc, odp, ods, odt, ppt, pptx, rtf, xls, xlsx) mais extraction non implémentée
            return ''
