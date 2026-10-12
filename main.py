# bibliothèques standard
import os.path
import glob
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.filedialog import askdirectory
import tkinter.font as tkfont
from idlelib.tooltip import Hovertip
from datetime import datetime
from threading import Thread
import shutil

# bibliothèques tierces
from unidecode import unidecode
# from PyMuPDF import open as fitz_open, Rect as fitz_Rect  # pip install  (pas fitz qui est une autre bibliothèque !)

# bibliothèque perso
from fonctions import *


# saisie du dossier à scanner
def select_folder_to_process():
    global label_folder_to_process, folder_to_process
    folder_to_process = askdirectory(title=translate['choose_scan_folder'][language], initialdir=folder_to_process)
    # # TKinter renvoie des '/' et pas des '\' sous Windows
    folder_to_process = folder_to_process.replace('/', '\\')
    if folder_to_process:
        label_folder_to_process.destroy()
        label_folder_to_process = tk.Label(lframe_scan, text=folder_to_process, anchor='w')
        label_folder_to_process.grid(row=1, column=0, sticky='NW')
        message_scan.config(text='')
        adjust_window()

# saisie du dossier de destination
def select_dest_folder():
    global label_dest_folder, dest_folder
    clear_all_messages()
    dest_folder = askdirectory(title=translate['choose_dest_folder'][language], initialdir=dest_folder)
    # # TKinter renvoie des '/' et pas des '\' sous Windows
    dest_folder = dest_folder.replace('/', '\\')

    if dest_folder:  # Ne mettre à jour que si un dossier a été sélectionné
        label_dest_folder.destroy()
        label_dest_folder = tk.Label(lframe_newrule, text=dest_folder, anchor='w')
        label_dest_folder.grid(row=3, column=1, sticky='NW') # attention conflit avec le positionnement initial (à factoriser)
        adjust_window()

# recherche de chaînes intéressantes
# def search_patterns(content):
#     results = {
#         'address': set(REGEX_PATTERNS['address'].findall(content)),
#         'iban':     set(REGEX_PATTERNS['iban'].findall(content)),
#         'mail':     set(REGEX_PATTERNS['mail'].findall(content)),
#         'name':     set(REGEX_PATTERNS['name'].findall(content)),
#         'tel':      set(REGEX_PATTERNS['tel'].findall(content)),
#         'web':      set(REGEX_PATTERNS['web'].findall(content)),
#         'suspect':  set(REGEX_PATTERNS['suspect'].findall(content))
#     }
#     return results

#
# # ajout d'une règle
# # tous les mots-clés seront testés en minuscules pour simplifier le test de présence
# # attention problèmes d'accents qq fois exemple IFU_09_04_2024.pdf (Imprimé Fiscal Unique 2023)
# # bug aussi sur PV.AGO.27.03.2024.pdf (PV d'AG Box V)
#
# def add_keyword():
#     global dest_folder, entry_new_keyword
#     keyword = entry_new_keyword.get()
#     if keyword == '':
#         display_message_new(translate['please_enter_keyword'][language])
#         root.update_idletasks()
#         return
#     if dest_folder == '':
#         display_message_new(translate['please_enter_dest'][language])
#         root.update_idletasks()
#         return
#     if keyword.lower() in {k.lower() for k in keywords}:  # insensible à la casse, comme scan()
#         display_message_new(translate['keywords_already_used'][language])
#         root.update_idletasks()
#         return
#     conflicts = find_keyword_conflicts(keyword)
#     if conflicts and not confirm_keyword_conflict(keyword, conflicts):
#         display_message_new(translate['keyword_add_cancelled'][language])
#         root.update_idletasks()
#         return
#     display_message_new(translate['keywords_added'][language] % (keyword, dest_folder))
#     keywords[keyword] = dest_folder + '/'  # il paraît que c'est pas propre
#     root.update_idletasks()
#     return


# trie les mots-clés d'une règle dans l'ordre alphabétique
def format_rule(rule):
    rule['keywords'].sort(key=str.casefold)
    return rule


# Insère une règle au bon endroit dans une liste pour respecter les priorités de tri (traiter a;b;c avant a;b par exemple)
# Est également appelé par la fonction de tri en début de programme pour vérifier l'intégrité et l'ordre après d'éventuelles
# saisies manuelles par l'utilisateur
def insert_rule(rules_old, rule):
    global entry_new_keyword

    # encore une normalisation :(
    rule          = format_rule(rule)
    rule_keywords = {keyword.casefold() for keyword in rule['keywords']}

    # 5 cas de figure entre 2 règles : A=B, A<B (sous-ensemble), A>B (sur-ensemble), A disjoint B, A partiel B.
    # Seuls les 2 cas d'inclusion (sous-ensemble / sur-ensemble) contraignent la position de la nouvelle règle :
    # - elle doit passer APRÈS la dernière règle existante dont elle est un sous-ensemble strict (règle existante plus stricte)
    # - elle doit passer AVANT la première règle existante dont elle est un sur-ensemble strict (règle existante moins stricte)
    # Les cas disjoint / intersection partielle ne contraignent rien l'un par rapport à l'autre : dans les deux cas,
    # seul l'ordre alphabétique des dossiers tranche, à l'intérieur de la fenêtre déterminée par les contraintes ci-dessus.
    insert_after_index  = -1                # -1 : rien n'empêche de placer la règle tout au début
    insert_before_index = len(rules_old)     # len(...) : rien n'empêche de la placer tout à la fin

    for i, r in enumerate(rules_old):
        r_keywords = {keyword.casefold() for keyword in r['keywords']}

        # identité : conflit, on n'insère pas la règle
        if rule_keywords == r_keywords:
            popup_message(translate['keywords_used'][language] % rule_keywords)
            return False

        # sous-ensemble strict : r est plus stricte, elle doit rester avant -> la nouvelle règle passe après r
        elif rule_keywords < r_keywords:
            insert_after_index = max(insert_after_index, i)

        # sur-ensemble strict : la nouvelle règle est plus stricte que r -> elle doit passer avant r
        elif rule_keywords > r_keywords:
            insert_before_index = min(insert_before_index, i)

        # disjonction (intersection vide) ou intersection partielle : aucune contrainte d'inclusion avec r,
        # seul l'ordre alphabétique des dossiers (ci-dessous) décidera de la position exacte

    # cas impossible à satisfaire : une règle plus stricte que la nouvelle est déjà placée, dans rules_old,
    # après une règle moins stricte qu'elle -> rules_old est dans un état incohérent (ex. édition manuelle du csv)
    if insert_after_index + 1 > insert_before_index:
        popup_message(translate['keywords_order_conflict'][language] % rule['folder'])
        return False

    # à l'intérieur de la fenêtre autorisée [insert_after_index+1, insert_before_index[, on insère
    # au bon endroit par ordre alphabétique des dossiers
    idx = insert_after_index + 1
    while idx < insert_before_index and rules_old[idx]['folder'].casefold() < rule['folder'].casefold():
        idx += 1

    rules_old.insert(idx, rule)

    return True


# renvoie des règles triées de manière cohérente pour respecter les priorités
def sort_rules(rules_list):
    rules_new = []
    for rule in rules_list:
        insert_rule(rules_new, rule)
    return rules_new


# ajoute une règle dans le CSV
def add_keywords_csv():
    global dest_folder, entry_new_keyword
    clear_all_messages()
    keywords_string = entry_new_keyword.get().strip()
    if keywords_string == '':
        display_message(message_new, translate['please_enter_keyword'][language])
        root.update_idletasks()
        return
    keywords_list = [k.strip() for k in keywords_string.split(';') if k.strip()]
    if not keywords_list:
        display_message(message_new, translate['please_enter_keyword'][language])
        root.update_idletasks()
        return
    if dest_folder == '':
        display_message(message_new, translate['please_enter_dest'][language])
        root.update_idletasks()
        return
    if len(keywords_list) != len(set(keywords_list)):
        display_message(message_new, translate['duplicate_keywords'][language])
        return

    new_rule = format_rule({'folder': dest_folder, 'keywords': keywords_list})

    if insert_rule(rules, new_rule):
        entry_new_keyword.delete(0, tk.END)
        display_message(message_new, translate['keywords_added'][language] % (new_rule['keywords'], dest_folder))

    root.update_idletasks()


# Popup listant les conflits ; renvoie True si l'utilisateur confirme l'ajout, False s'il annule (ou ferme la fenêtre)
def confirm_keyword_conflict(keyword, conflicts):
    result = {'ok': False}

    def on_ok():
        result['ok'] = True
        dialog.destroy()

    lines = []
    for existing, folder in conflicts:
        if keyword.lower() in existing.lower():
            lines.append(translate['keyword_conflict_inside'][language] % (keyword, existing, folder))
        else:
            lines.append(translate['keyword_conflict_contains'][language] % (keyword, existing, folder))

    dialog = tk.Toplevel(root)
    dialog.title(translate['keyword_conflict_title'][language])
    dialog.geometry(f'+{window_x+OFFSET_POPUP}+{window_y+OFFSET_POPUP}')
    tk.Label(dialog, text=translate['keyword_conflict_message'][language] % (keyword, '\n'.join(lines)),
             justify='left', anchor='w', wraplength=450).pack(padx=10, pady=10)
    tk.Button(dialog, text=translate['ok'][language], command=on_ok).pack(side='left', expand=True, pady=10)
    tk.Button(dialog, text=translate['cancel'][language], command=dialog.destroy).pack(side='left', expand=True, pady=10)
    dialog.grab_set()
    root.wait_window(dialog)
    return result['ok']


def popup_message(message: str):
    dialog = tk.Toplevel(root)
    dialog.title('Information')
    dialog.transient(root)
    dialog.geometry(f'+{window_x+OFFSET_POPUP}+{window_y+OFFSET_POPUP}')

    tk.Label(dialog, text=message, justify='left', wraplength=450).pack(padx=10, pady=10)
    tk.Button(dialog, text='Fermer', command=dialog.destroy).pack(pady=10)

    dialog.grab_set()
    root.wait_window(dialog)

def display_message(tk_label, message):
    tk_label.config(text=message)
    root.update_idletasks()

# def display_message_analyze(message):
#     message_analyze.config(text=message)
#     root.update_idletasks()

# def display_message_scan(message):
#     message_scan.config(text=message)
#     root.update_idletasks()

# def display_message_new(message):
#     message_new.config(text=message)
#     root.update_idletasks()

def clear_all_messages():
    display_message(message_new, '')
    display_message(message_analyze, '')
    display_message(message_scan, '')

def create_progress_bar():

    def cancel_folder_process():
        global cancelled
        cancelled = True
        cancel_button.config(state='disabled')
        display_message(message_scan, translate['scan_cancelled'][language])

    progress_window = tk.Toplevel()
    progress_window.title(translate['progress_title'][language])
    progress_window.geometry(f'{LARGEUR_POPUP}x{HAUTEUR_POPUP}+{window_x + OFFSET_POPUP}+{window_y + OFFSET_POPUP}')

    progress_label = tk.Label(progress_window, text=translate['processing_folder'][language], anchor='w')
    progress_label.pack(pady=10)

    progress_bar = ttk.Progressbar(progress_window, length=200, mode='determinate')
    progress_bar.pack(pady=10)

    cancel_button = tk.Button(progress_window, text=translate['cancel'][language], command=cancel_folder_process)
    cancel_button.pack(pady=10)

    return progress_window, progress_bar, progress_label


# lance le scan dans un thread séparé pour que tkinter puisse détecter l'annulation par l'utilisateur pendant le traitement
def start_folder_process_thread():
    clear_all_messages()
    root.attributes('-disabled', True)
    folder_process_thread = Thread(target=process_folder)
    folder_process_thread.start()


def close_progress_window(progress_window):
    if progress_window.winfo_exists():
        progress_window.destroy()
    root.attributes('-disabled', False)


def confirm_files_to_move(files_to_move):
    """Popup dont la taille s'adapte au texte : nom du fichier, puis '-> destination' sur la ligne suivante."""
    result = {'ok': False}

    def on_ok():
        result['ok'] = True
        dialog.destroy()

    dialog = tk.Toplevel(root)
    dialog.title(translate['files_to_be_moved_title'][language])
    dialog.geometry(f'+{window_x+OFFSET_POPUP}+{window_y+OFFSET_POPUP}')
    files_by_destination = {}

    for src, dst in files_to_move:
        files_by_destination.setdefault(os.path.dirname(dst), []).append(os.path.basename(src))

    move_list = '\n\n'.join('\n'.join(filenames) + f'\n-> {destination}'
                for destination, filenames in files_by_destination.items())

    tk.Label(dialog, text=translate['files_to_be_moved_message'][language] % move_list,
             justify='left', anchor='w').pack(padx=10, pady=10)
    tk.Button(dialog, text=translate['ok'][language], command=on_ok).pack(side='left', expand=True, pady=10)
    tk.Button(dialog, text=translate['cancel'][language], command=dialog.destroy).pack(side='left', expand=True, pady=10)
    dialog.grab_set()
    root.wait_window(dialog)
    return result['ok']


def process_folder():
    global cancelled
    cancelled = False

    if not os.path.exists(folder_to_process):
        display_message(message_scan, translate['unknown_folder'][language])
        root.after(0, lambda: root.attributes('-disabled', False))
        return

    # Créer la fenêtre de progression
    progress_window, progress_bar, progress_label = create_progress_bar()

    # Obtenir la liste des fichiers à traiter
    files = [file for extension in EXTENSIONS_TRAITEES
                  for file in glob.glob(f'{folder_to_process}/*.{extension}', recursive=False)]
    total_files = len(files)

    if total_files == 0:
        progress_window.destroy()
        display_message(message_scan, translate['no_files_found'][language])
        root.after(0, lambda: root.attributes('-disabled', False))
        return

    progress_bar['maximum'] = total_files
    processed_files = 0

    start_time = datetime.now()
    files_to_move = []

    for file_path in files:
        if cancelled:
            break
        try:
            base_name = os.path.basename(file_path)
            progress_label.config(text=translate['processing_file'][language] % base_name)
            root.update_idletasks()

            extension_pos = base_name.rfind('.')
            extension     = base_name[extension_pos + 1:].lower()

            if extension not in EXTENSIONS_TRAITEES:
                continue

            print('\033[32m')
            print('**********', file_path)
            content = extract_text_from_file(file_path)
            print('\033[0m(')
            # print('Content :', content[:200].replace(r')\r\n', ' '))
            if content is None or content == '':
                continue

            # # recherche de correspondance dans keywords.json (le filtrage est inutile, contrairement à analyse_file())
            # for keyword in keywords:
            #     # insensible à la casse
            #     if keyword.lower() in content.lower():  # insensibilité à la casse
            #         print('  keyword ' + keyword)
            #         new_file_path = os.path.join(keywords[keyword], os.path.basename(file_path))
            #         if os.path.exists(new_file_path):
            #             print('  \033[31malready exists in destination folder\033[0m')
            #         else:
            #             files_to_move.append((file_path, new_file_path))
            #         break

            # # dessin de rectangles si pas de mot trouvé
            # if extension == 'pdf' and not keyword_found and False: # debug : ne passe jamais
            #     # Ouvrir le document PDF
            #     doc = fitz_open(file_path)
            #
            #     # Parcourir les pages du PDF
            #     for page_num in range(doc.page_count):
            #         page = doc.load_page(page_num)  # Charger une page
            #
            #         # Extraire les mots
            #         words = page.get_text('words')
            #
            #         # Parcourir chaque mot et dessiner un rectangle autour
            #         for word in words:
            #             clean_word = word[4].lower().strip('.').strip(',').strip(':').strip('(').strip(')') # à refaire ça peut être multiple et dans le désordre
            #             if len(clean_word) > 1 and clean_word[1] in """':                # enlever le début en apostrophe
            #                 clean_word = clean_word[2:]
            #             if len(clean_word) > 2 and clean_word not in dico:
            #                 rect = fitz_Rect(word[:4])  # Les 4 premières valeurs sont les coordonnées du rectangle
            #                 # Dessiner un rectangle autour du mot
            #                 shape = page.new_shape()
            #                 shape.draw_rect(rect)
            #                 shape.finish(width=1, color=(0, 1, 0))  # Vert avec une épaisseur de 2 points
            #                 shape.commit()  # Appliquer les changements à la page

                # # Sauvegarder le PDF avec les rectangles dessinés
                # doc.save(file_path + 'annoted.pdf')  # **************************************************************************************************
                # print(file_path + ' annoté avec les mots entourés enregistré !')


            # recherches de correspondances dans rules.csv
            content_lower = content.casefold()  # plus agressif que lower()
            for rule in rules:
                if all(keyword.casefold() in content_lower for keyword in rule['keywords']):
                    print(f'Règle remplie : {rule['folder']}')
                    new_file_path = os.path.join(rule['folder'], os.path.basename(file_path))
                    if os.path.exists(new_file_path):
                        print('  \033[31malready exists in destination folder\033[0m')
                    else:
                        files_to_move.append((file_path, new_file_path))
                    break

            processed_files += 1
            progress_bar['value'] = processed_files
            root.update_idletasks()

        except Exception as e:
            print('  ' + str(e) + 'exception on ' + file_path)
            continue

    if cancelled:
        progress_label.config(text=translate['scan_cancelled'][language])
        root.update_idletasks()
        root.after(DELAI_AVANT_FERMETURE, close_progress_window, progress_window)
        return

    if files_to_move and confirm_files_to_move(files_to_move):
        for src, dst in files_to_move:
            shutil.move(src, dst)
            print(f'Moved {os.path.basename(src)} to {os.path.dirname(dst)}')
        display_message(message_scan, translate['files_moved_message'][language])

    duration = datetime.now() - start_time
    progress_label.config(text=translate['completed'][language] % duration)
    root.update_idletasks()

    # Fermer la fenêtre de progression après 2 secondes
    root.after(DELAI_AVANT_FERMETURE, close_progress_window, progress_window)


# def copy_to_keyword(value):
#     """Colle la valeur dans le champ keyword de Create rule"""
#     entry_new_keyword.delete(0, tk.END)
#     entry_new_keyword.insert(0, value)

def analyse_file():
    global anal_folder, combobox_results
    clear_all_messages()
    file_path = filedialog.askopenfilename(title=translate['select_file'][language],
                                           filetypes=[('Documents', '*.pdf;*.docx;*.txt')],
                                           initialdir=anal_folder)
    if not file_path:
        return

    anal_folder = os.path.dirname(file_path)
    root.attributes('-disabled', True)
    try:
        keywords = get_keyword_list_from_file(file_path)
        combobox_results["values"] = sorted(keywords) # remplit la liste déroulante
        btn_copy_keyword.grid() # faire réapparaître
    finally:
        root.attributes('-disabled', False)


def get_keyword_list_from_file(file_path):
    global tip_add_keyword, keywords_global
    clear_all_messages()
    try:
        with open(DIC_FRANCAIS_FILE, 'r', encoding='utf-8') as f:
            dico = f.read().splitlines()
    except FileNotFoundError:
        display_message(message_analyze, translate['dictionary_not_found'][language] % DIC_FRANCAIS_FILE)
        return {}

    content = extract_text_from_file(file_path)

    content_lower = content.casefold()  # plus agressif que lower()
    for rule in rules:
        rule_keywords = rule['keywords']
        if rule_keywords and all(keyword.casefold() in content_lower for keyword in rule_keywords):
            print(f'Règle remplie : {rule['folder']}')

    # if not content:
    #     label_result.config(text='Unable to extract text from file.')
    #     return

    # keywords_known   = {key for key in keywords if key.lower() in content.lower()} # ceux déjà connus
    # if keywords_known :
    #     print('Contient déjà des mots-clé connus : ', sorted(list(keywords_known)))

    # recherche de mots-clés valables

    keywords_address = keywords_cp = keywords_iban = keywords_mail = keywords_name \
         = keywords_suspect = keywords_tel = keywords_web = set()

    # keywords_address = set(REGEX_CHERCHEES['address'].findall(content))  # bof
    keywords_address = set(REGEX_CHERCHEES_v2026['address'].findall(content))
    # keywords_address = set(REGEX_IA['address'].findall(content))

    keywords_cp      = set(REGEX_CHERCHEES['cp'].findall(content))
    keywords_iban    = set(REGEX_CHERCHEES['iban'].findall(content))
    keywords_mail    = set(REGEX_CHERCHEES['mail'].findall(content))
    # keywords_mail    = set(REGEX_CHERCHEES_v2026['mail'].findall(content)) # idem
    # keywords_name  = set(REGEX_CHERCHEES['name'].findall(content)) # beaucoup
    # keywords_name  = {k for k in keywords_name if k.isalpha()  # is alphabétique, pas alphanumérique !
    #                     if len(k) > 2
    #                     and unidecode(k.lower()) not in MOTS_CLES_IGNORES
    #                     and unidecode(k.lower()) not in dico} # insensibiliser aux accents pour comparer du [a-z]
    keywords_name    = set(REGEX_IA['name'].findall(content))
    # keywords_suspect = {k for k in set(REGEX_CHERCHEES['suspect'].findall(content)) if len(k) > 3 } # if k.isalpha()
    # keywords_tel   = set(REGEX_CHERCHEES['tel'].findall(content))
    # keywords_tel   = set(REGEX_CHERCHEES_v2026['tel'].findall(content)) # idem
    keywords_tel     = set(k[0] for k in REGEX_IA['tel'].findall(content)) # regex spéciale qui renvoie des tuples
    keywords_web     = set(REGEX_CHERCHEES['web'].findall(content))
    # keywords_web   = set(REGEX_CHERCHEES_v2026['web'].findall(content)) # idem

    # synthèse
    keywords_global = keywords_address | keywords_cp | keywords_iban | keywords_mail | keywords_name | keywords_suspect \
                      | keywords_tel | keywords_web

    # suppression des mots du dictionnaire
    keywords_global = {k for k in keywords_global if unidecode(k.lower()) not in dico}

    # suppression des mots ignorés par défaut
    keywords_global = {k for k in keywords_global if unidecode(k.lower()) not in MOTS_CLES_IGNORES}

    # purge des mots qui sont inclus dans d'autres pour ne garder que la version longue
    keywords_global = {k for k in keywords_global if not any (k!= mot and k in mot for mot in keywords_global)}

    # # en cas de sélection d'un élément de la liste par l'utilisateur
    # def on_combobox_select(_event):
    #     selected_value = combobox_results.get()
    #     entry_new_keyword.delete(0, tk.END)           # Efface le contenu actuel
    #     entry_new_keyword.insert(0, selected_value)  # Insère la valeur sélectionnée
    #     display_message_new('')  # Efface le message de confirmation précédent
    #
    # label_choose_keyword = tk.Label(lframe_analyze, text=translate['choose_keyword'][language], anchor='w')
    # label_choose_keyword.translate_key = 'choose_keyword'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
    # label_choose_keyword.grid(row=0, column=1, sticky='NW')
    # # combobox_results = ttk.Combobox(lframe_analyze, values=sorted(list(keywords_address | keywords_cp \
    # #                                                                    | keywords_iban| keywords_mail | keywords_name \
    # #                                                                    | keywords_suspect | keywords_tel | keywords_web)), width=47)
    #
    # combobox_results = ttk.Combobox(lframe_analyze, values=sorted(keywords_global), width=47)  # values=sorted(keywords_global)
    # # pour voir ligne par ligne (test) :
    # # combobox_results = ttk.Combobox(lframe_analyze, values=content.split('\n'), width=47)
    # combobox_results.bind('<<ComboboxSelected>>', on_combobox_select)
    # combobox_results.grid(row=1, column=1,  sticky='NW', padx=5)

    # # en cas de sélection d'un élément de la liste par l'utilisateur : effacer l'ancien
    # # le champ de mot-clé n'est plus rempli automatiquement (voir copy_selected_keyword, sur le bouton '+')
    # def on_combobox_select(_event):
    #     display_message_new('')  # Efface le message de confirmation précédent

    # return keywords_global    # renvoie les mots-clés
    return content.split('\n')  # renvoie les lignes

# copie le mot actuellement sélectionné dans le champ de saisie de mot-clé de la nouvelle règle ;
# appelé par un clic sur le bouton '+
def copy_selected_keyword():
    clear_all_messages()
    selected_value = combobox_results.get()
    if not selected_value:
        return
    current_value = entry_new_keyword.get().strip()
    if selected_value in current_value:
        return
    if current_value:
        entry_new_keyword.insert(tk.END, ';' + selected_value)  # ajouté après le contenu existant, séparé par ';'
    else:
        entry_new_keyword.insert(0, selected_value)  # champ vide : rien à séparer
    combobox_results.set('')
    display_message(message_new, '')  # Efface le message de confirmation précédent


def translate_widgets(widget, new_lang):
    # Si le widget porte une clé de traduction explicite, l'utiliser directement
    key = getattr(widget, 'translate_key', None)
    if key is not None:
        widget.config(text=translate[key][new_lang])
    # Parcourir récursivement les enfants du widget
    for child in widget.winfo_children():
        translate_widgets(child, new_lang)


def translate_tooltips(new_lang):
    tip_add_rule.text    = translate['click_to_add_rule'][new_lang]
    tip_analyze.text     = translate['click_to_analyze_file'][new_lang]
    tip_add_keyword.text = translate['click_to_add_keyword'][new_lang]
    tip_destination.text = translate['click_to_select_destination'][new_lang]
    tip_entry.text       = translate['enter_keyword_here'][new_lang]
    tip_folder.text      = translate['click_to_choose_folder'][new_lang]
    tip_scan.text        = translate['click_to_start_scan'][new_lang]


def translate_menu(new_lang):
    assert file_menu_index is not None  # évite un warning (même si techniquement file_menu_index ne peut pas être None)
    menu_bar.entryconfig(file_menu_index, label=translate['menu_file'][new_lang])
    assert lang_menu_index is not None  # évite un warning0 (même si techniquement lang_menu_index ne peut pas être None)
    menu_bar.entryconfig(lang_menu_index, label=translate['menu_language'][new_lang])
    file_menu.entryconfig(0, label=translate['quit'][new_lang])


def translate_app():
    translate_widgets(root, language)
    translate_tooltips(language)
    translate_menu(language)


def change_language():
    global language
    language = lang_var.get()
    translate_app()


def show_welcome_popup():
    def on_ok():
        global hide_welcome
        hide_welcome = show_welc.get()
        welcome_popup.destroy()

    welcome_popup = tk.Toplevel(root)
    welcome_popup.title(translate['welcome_title'][language])
    welcome_popup.geometry(f'{LARGEUR_POPUP}x{HAUTEUR_POPUP}+{window_x + OFFSET_POPUP}+{window_y + OFFSET_POPUP}')

    tk.Label(welcome_popup, text=translate['welcome_greeting'][language], anchor='w').pack(pady=10)

    show_welc = tk.BooleanVar(value=hide_welcome)
    tk.Checkbutton(welcome_popup, text=translate['dont_show_again'][language], variable=show_welc).pack(pady=5)

    tk.Button(welcome_popup, text=translate['ok'][language], command=on_ok).pack(pady=10)

    welcome_popup.transient(root)
    welcome_popup.grab_set()
    root.wait_window(welcome_popup)


# sauvegarde de la configuration
def on_exit():
    config['hide_welcome'] = hide_welcome
    config['language'] = language
    config['window_width'] = root.winfo_width()
    # config['window_height'] = root.winfo_height()
    config['window_x'] = max(0, root.winfo_x())  # devient négatif/invisible lorsqu'on supprime 1 moniteur depuis Windows
    config['window_y'] = max(0, root.winfo_y())  # devient négatif/invisible lorsqu'on supprime 1 moniteur depuis Windows
    config['last_anal_folder'] = anal_folder
    config['last_scan_folder'] = folder_to_process
    config['last_dest_folder'] = dest_folder
    save_config(config)
    root.destroy()
    # with open(MOTS_CLES_FILE, 'w', encoding='utf8') as new_file:
    #     json.dump(keywords, new_file, indent=1, ensure_ascii=False)
    save_rules_csv(rules)

def adjust_window():
    root.update_idletasks()

    def largeur_texte(label):
        font = tkfont.nametofont(label.cget('font'))
        return font.measure(label.cget('text'))

    largeur_bloc_scan = max(
        largeur_texte(label_folder_to_process),
        btn_folder.winfo_reqwidth()
    ) + btn_scan.winfo_reqwidth() + 40
    largeur_bloc_regle = max(
        largeur_texte(label_dest_folder),
        entry_new_keyword.winfo_reqwidth(),
        btn_add.winfo_reqwidth()
    ) + btn_new.winfo_reqwidth() + 40
    frame_width = min(LARGEUR_CADRES_MAX, max(LARGEUR_CADRES_MIN, largeur_bloc_scan, largeur_bloc_regle))

    for frame in (lframe_scan, lframe_analyze, lframe_newrule):
        frame.config(width=frame_width)

    root.geometry(f'{frame_width}x{HAUTEUR_CADRES * 3}')

"""______________________________________________________________________________________________
            DEMARRAGE DU SCRIPT
 _____________________________________________________________________________________________"""

# chargement de la config
config    = load_config()
# keywords  = load_keywords()
translate = load_translations()

hide_welcome  = config.get('hide_welcome', True)  # on met de valeurs par défaut, au cas où le fichier de conf disparaissait
language      = config.get('language', 'en')
window_width  = config.get('window_width', 600)
window_height = config.get('window_height', 500)
window_x      = config.get('window_x', 600)
window_y      = config.get('window_y', 300)
anal_folder   = config.get('last_anal_folder', './')
folder_to_process: str = config.get('last_scan_folder', './')  # str() pour éviter un faux positif
dest_folder   = config.get('last_dest_folder', './')

# initialisation des variables globales
cancelled = False

"""______________________________________________________________________________________________
        FENETRE PRINCIPALE
 _____________________________________________________________________________________________"""
root = tk.Tk()
root.title('TriDoc')
root.geometry(f'{window_width}x{window_height}+{window_x}+{window_y}')
root.columnconfigure(0, weight=1)
root.protocol('WM_DELETE_WINDOW', on_exit) # si on ferme la fenêtre au lieu d'appuyer sur 'Quitter'

if not hide_welcome:
    show_welcome_popup()

# BARRE DES MENUS
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

# MENU FICHIER
file_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label=translate['menu_file'][language], menu=file_menu)
file_menu.add_command(label=translate['quit'][language], command=on_exit)
file_menu_index = menu_bar.index('end')

# MENU LANGUE
lang_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label=translate['menu_language'][language], menu=lang_menu)
lang_menu_index = menu_bar.index('end')
lang_var = tk.StringVar(value=language)
for l in LANGUAGES:
    lang_menu.add_radiobutton(
        label=l.upper(),
        value=l,
        variable=lang_var,
        command=change_language
    )

ICON_LANGUAGE = tk.PhotoImage(file=f'{ICONES_DIR}/language.png')
ICON_EXIT     = tk.PhotoImage(file=f'{ICONES_DIR}/exit.png')
ICON_DISPATCH = tk.PhotoImage(file=f'{ICONES_DIR}/dispatch.11.png')
ICON_NEW      = tk.PhotoImage(file=f'{ICONES_DIR}/new.11.png')
ICON_ANALYZE  = tk.PhotoImage(file=f'{ICONES_DIR}/analyze.11.png')

# -----------------frame analyze file-----------------
# le cadre
lframe_analyze = tk.LabelFrame(root, text=translate['analyze_file'][language], width=LARGEUR_CADRES_MIN, height=HAUTEUR_CADRES)
lframe_analyze.translate_key = 'analyze_file'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
lframe_analyze.grid_propagate(False) # Empêche l'ajustement automatique
lframe_analyze.grid(sticky='ew')
lframe_analyze.columnconfigure(1, weight=1)

# le bouton qui sélectionne le fichier à analyser
btn_analyze = tk.Button(lframe_analyze, image=ICON_ANALYZE, command=analyse_file)
btn_analyze.grid(row=0, column=0, rowspan=4, ipadx=45)
tip_analyze = Hovertip(btn_analyze, translate['click_to_analyze_file'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)

message_analyze = tk.Label(lframe_analyze, fg=COULEUR_MESSAGES, text='')
message_analyze.grid(row=0, column=1, sticky='NW')

label_choose_keyword = tk.Label(lframe_analyze, text=translate['choose_keyword'][language], anchor='w')
label_choose_keyword.translate_key = 'choose_keyword'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
label_choose_keyword.grid(row=0, column=1, sticky='NW')
# combobox_results = ttk.Combobox(lframe_analyze, values=sorted(list(keywords_address | keywords_cp \
#                                                                    | keywords_iban| keywords_mail | keywords_name \
#                                                                    | keywords_suspect | keywords_tel | keywords_web)), width=47)

# contenu de la liste déroulante = mots-clés pertinents classés par ordre alphabétique
keywords_global = {}
combobox_results = ttk.Combobox(lframe_analyze, values=sorted(keywords_global), width=47)  # values sert à rien ici,si ?

# contenu de la liste déroulante = PDF ligne par ligne (test) :
# combobox_results = ttk.Combobox(lframe_analyze, values=content.split('\n'), width=47)
# combobox_results.bind('<<ComboboxSelected>>', on_combobox_select)

combobox_results.grid(row=1, column=1,  sticky='NW', padx=5)

# bouton d'ajout de mot-clé
btn_copy_keyword = tk.Button(lframe_analyze, text='+', command=copy_selected_keyword, padx=5)
btn_copy_keyword.grid(row=1, column=2, sticky='NW')
tip_add_keyword = Hovertip(btn_copy_keyword, translate['select_keyword'][language], hover_delay=DELAI_ASTUCES,
                           background=COULEUR_ASTUCES)
btn_copy_keyword.grid_remove() # cacher pour l'instant

# -----------------frame new keyword-----------------
# le cadre
lframe_newrule = tk.LabelFrame(root, text=translate['new_rule'][language], width=LARGEUR_CADRES_MIN, height=HAUTEUR_CADRES)
lframe_newrule.translate_key = 'new_rule'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
lframe_newrule.grid_propagate(False) # Empêche l'ajustement automatique
lframe_newrule.grid(sticky='ew')
lframe_newrule.columnconfigure(1, weight=1)

# le nom du champ de saisie
label_new_keyword = tk.Label(lframe_newrule, text=translate['new_keyword'][language])
label_new_keyword.translate_key = 'new_keyword'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
label_new_keyword.grid(row=0, column=1, sticky='NW')

# le  champ de saisie
entry_new_keyword = tk.Entry(lframe_newrule, width=50)
entry_new_keyword.grid(row=1, column=1, sticky='NW', padx=5)
tip_entry = Hovertip(entry_new_keyword, translate['enter_keyword_here'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)

# le bouton de sélection de dossier
btn_add = tk.Button(lframe_newrule, text=translate['select_dest_folder'][language], command=select_dest_folder, padx=5)
btn_add.translate_key = 'select_dest_folder'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
btn_add.grid(row=2, column=1, sticky='NW')
tip_destination = Hovertip(btn_add, translate['click_to_select_destination'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)

# l'afichage du nom de dossier
label_dest_folder = tk.Label(lframe_newrule, text=dest_folder)
label_dest_folder.grid(row=3, column=1, sticky='NW')

# le message de confirmation
message_new = tk.Label(lframe_newrule, fg=COULEUR_MESSAGES, text='', anchor='w')
message_new.grid(row=4, column=1, sticky='NW')

# le bouton d'ajout de règle
btn_new = tk.Button(lframe_newrule, image=ICON_NEW, command=add_keywords_csv)
btn_new.grid(row=0, column=2, rowspan=4, sticky='e')
tip_add_rule = Hovertip(btn_new, translate['click_to_add_rule'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)

# ---------------frame scan folder-----------------
# le cadre
lframe_scan = tk.LabelFrame(root, text=translate['scan_folder'][language], width=LARGEUR_CADRES_MIN, height=HAUTEUR_CADRES)
lframe_scan.translate_key = 'scan_folder'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
# lframe_scan.pack(anchor='nw', ipadx=20, padx=10, pady=10)
lframe_scan.grid_propagate(False) # Empêche l'ajustement automatique
lframe_scan.grid(sticky='ew')
lframe_scan.columnconfigure(2, weight=1)

# le bouton choix dossier
btn_folder = tk.Button(lframe_scan, text=translate['select_scan_folder'][language], command=select_folder_to_process)
btn_folder.translate_key = 'select_scan_folder'  # noqa (on précise sa clé de traduction pour qu'il puisse être traduit automatiquement)
tip_folder = Hovertip(btn_folder, translate['click_to_choose_folder'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)
btn_folder.grid(row=0, column=0, sticky='NW')

# le nom du dossier choisi
label_folder_to_process = tk.Label(lframe_scan, text=folder_to_process, anchor='w')
label_folder_to_process.grid(row=1, column=0, sticky='NW')

# le bouton de scan
btn_scan = tk.Button(lframe_scan, image=ICON_DISPATCH, command=start_folder_process_thread)
btn_scan.grid(row=0, column=2, sticky='e', rowspan=4)
tip_scan = Hovertip(btn_scan, translate['click_to_start_scan'][language], hover_delay=DELAI_ASTUCES, background=COULEUR_ASTUCES)

# le message d'erreur
message_scan = tk.Label(lframe_scan, fg=COULEUR_MESSAGES, text='', anchor='w')
message_scan.grid(row=2, column=0, columnspan=2, sticky='NW')  # autorisation de s'étendre sur 1 colonnes + aligné en haut à gauche

# root


rules = sort_rules(load_rules())
adjust_window()
root.mainloop()
