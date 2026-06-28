# SpectraViewer
# Copyright (c) 2026 Zsolt Hidasi
# All rights reserved.
# Use of this program is governed by the accompanying terms of use.

import os, sys
import re
import configparser
import numpy as np
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
# --- OPTIONAL Drag&Drop support (Windows/macOS/Linux depending on Tcl/Tk build) ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    DND_AVAILABLE = False
try:
    from brukeropus import read_opus as opus_read
except ImportError:
    opus_read = None
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, colorchooser
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

APP_NAME = "SpectraViewer"
VERSION_NUMBER = "1.1.6"
AUTHOR = "Hidasi Zsolt"
YEAR = "2026"

WARN_FILE_COUNT = 5000
MAX_FILE_COUNT = 20000

ENCODING_OPTIONS = [
    ("Auto / OPUS alapértelmezett", "auto"),
    ("Windows-1252 / nyugat-európai", "cp1252"),
    ("Windows-1250 / közép-európai", "cp1250"),
    ("UTF-8", "utf-8"),
    ("Latin-1 / ISO-8859-1", "iso-8859-1"),
    ("Latin-2 / ISO-8859-2", "iso-8859-2"),
]
ENCODING_LABEL_TO_VALUE = dict(ENCODING_OPTIONS)
ENCODING_VALUE_TO_LABEL = {value: label for label, value in ENCODING_OPTIONS}
DEFAULT_METADATA_ENCODING = "auto"
DEFAULT_LINE_COLOR = "#1f77b4"

UI_TEXT = UI_TEXT = {
    'initial_status': 'Válassz egy fájlt vagy mappát…',
    'last_path_not_found_status': 'Az utolsó elérési út nem található. Válassz egy fájlt vagy mappát…',
    'last_path_unsupported_status': 'Az utolsó elérési út nem támogatott formátumra mutat. Válassz egy fájlt vagy mappát…',
    'last_path_single_folder_status': 'Az utolsó elérési út mappa, de a Single file mód be van kapcsolva. Válassz egy spektrumfájlt…',
    'last_path_no_spectrum_status': 'Az utolsó útvonal visszaállítva, de nem találtam támogatott spektrumfájlt.',
    'last_path_too_many_status': 'Az utolsó mappa {count} támogatott fájlt tartalmaz. Automatikusan nem töltöttem be; szükség esetén nyisd meg kézzel.',
    'last_path_restored_status': 'Utolsó munkamenet visszaállítva: {path}',
    'path_label': 'Elérési út:',
    'folder_button': 'Mappa…',
    'file_button': 'Fájl…',
    'recursive_checkbox': 'almappák bejárása',
    'single_file_checkbox': 'csak egy fájl',
    'about_button': 'Névjegy',
    'prev_button': '◀ Előző',
    'next_button': 'Következő ▶',
    'save_image_button': 'Mentés képként',
    'color_button': 'Szín',
    'invert_x_checkbox': 'X fordítás',
    'crosshair_checkbox': 'Szálkereszt',
    'metadata_encoding_label': 'Metaadat-kódolás:',
    'axis_wavenumber': 'Wavenumber (cm⁻¹)',
    'axis_intensity': 'Intensity',
    'single_file_title': 'Single file mód',
    'single_file_drop_multiple': 'Single file módban egyszerre csak egy spektrumfájl húzható be.',
    'single_file_folder_not_allowed': 'Single file módban mappa helyett egy konkrét spektrumfájlt kell megnyitni.',
    'single_file_select_one': 'Single file módban egyszerre pontosan egy támogatott spektrumfájl nyitható meg.',
    'single_file_path_must_be_file': 'Single file módban az elérési útnak egy konkrét spektrumfájlra kell mutatnia, nem mappára.',
    'single_file_invalid_path': 'Single file módban a megadott útvonalnak egy létező spektrumfájlra kell mutatnia.',
    'single_file_subfolders_disabled': 'Single file módban az almappák bejárása nem használható.',
    'single_file_enabled_status': 'Single file mód bekapcsolva.',
    'single_file_disabled_rebuilt_status': 'Single file mód kikapcsolva. Mappakörnyezet visszatöltve ({mode}).',
    'single_file_disabled_restored_status': 'Single file mód kikapcsolva. A rekurzív beállítás visszaállítva.',
    'too_many_files_title': 'Túl sok fájl',
    'too_many_files_error': 'A {origin} {count} támogatott fájlt tartalmaz.\n\nEz meghaladja a megengedett maximumot ({max_count}).\nSzűkítsd a kijelölést vagy válassz kisebb mappát.',
    'too_many_files_confirm_title': 'Túl sok betöltendő fájl',
    'too_many_files_confirm': 'A {origin} {count} támogatott fájlt tartalmaz.\n\nEnnyi spektrum betöltése memóriaigényes művelet,\nami lassú működést eredményezhet.\nSzeretnéd folytatni?',
    'all_supported_files': 'Minden támogatott',
    'opus_numeric_extension': 'OPUS / numerikus kiterjesztés',
    'all_files': 'Minden fájl',
    'open_files_title': 'Fájlok megnyitása',
    'open_folder_title': 'Mappa kiválasztása',
    'unsupported_format_title': 'Nem támogatott formátum',
    'unsupported_selected_message': 'A kiválasztott fájl(ok) formátuma nem támogatott.',
    'unsupported_path_message': 'A megadott fájl formátuma nem támogatott.',
    'some_files_skipped_title': 'Néhány fájl kihagyva',
    'selected_files_skipped': 'A kiválasztott {total} fájlból {valid} támogatott, {invalid} kihagyva.\n\nKihagyott fájlok:\n- {shown}',
    'dropped_items_skipped': 'A kiválasztott elemekből {valid} támogatott fájl került betöltésre és {invalid} kihagyva.\n\nKihagyott fájlok:\n- {shown}',
    'and_more': '\n- ... és még {more} db',
    'selected_list_origin': 'kiválasztott lista',
    'opened_folder_origin': 'megnyitott mappa',
    'folder_context_origin': 'mappa-kontextus',
    'folder_context_origin_alt': 'mappa-kontextus',
    'warning_title': 'Figyelem',
    'no_loadable_file': 'Nincs betölthető fájl.',
    'invalid_path_title': 'Érvénytelen útvonal',
    'invalid_path_message': 'A megadott elérési út (fájl vagy mappa) érvénytelen.',
    'no_match_title': 'Nincs találat',
    'no_spectrum_at_path': 'A megadott útvonalon nem találtam támogatott formátumú spektrumot.',
    'context_reload_cancelled': 'A mappakörnyezet visszatöltése megszakítva. Az aktuális fájl maradt betöltve.',
    'invalid_file_title': 'Érvénytelen fájl',
    'no_supported_among_items': 'A kiválasztott elemek között nincs támogatott formátum.',
    'no_supported_among_items_with_skips': 'A kiválasztott {total} tétel között nem volt támogatott formátum.\n\nKihagyott fájlok:\n- {shown}',
    'custom_list_loaded': 'Egyedi lista betöltve: {count} fájl',
    'invalid_folder_status': 'Érvénytelen mappa.',
    'loading_cancelled_previous_kept': 'Betöltés megszakítva: túl sok fájl. Az előző lista maradt aktív.',
    'no_match_in_folder_status': 'Nincs találat ebben a mappában (OPUS/DX/JDX/DPT).',
    'error_prefix': 'Hiba',
    'file_label': 'Fájl',
    'unknown_error': 'Ismeretlen hiba',
    'spectrum_color_title': 'Spektrum színe',
    'about_window_title': 'Névjegy',
    'about_dnd_line': '\t• Drag&Drop – fájl vagy mappa behúzása az ablakba\n',
    'about_text': 'Verzió: {version} © {author}, {year}\nFejlesztés: {author}, OpenAI\n\nTámogatott spektrum formátumok:\n\t• OPUS (*.0–*.5)\n\t• JCAMP-DX (*.dx, *.jdx)\n\t• DPT (*.dpt)\n\nGyorsbillentyűk:\n\t• Ctrl+O – Fájl megnyitása\n\t• Ctrl+Shift+O – Mappa megnyitása\n\t• Bal nyíl / Jobb nyíl – Előző / Következő spektrum\n\t• Ctrl+S – spektrum mentése képként\n\t• Ctrl+Shift+C – spektrum szín választása / módosítása\n{dnd_line}\t• F1 – Névjegy\n\nHasználati útmutató: SpectraViewerMan_HU.pdf\n\nA beállítások a SpectraViewer.ini fájlba mentődnek. Az alapállapot visszaállításához töröld ezt a fájlt.',
    'save_message_title': 'Mentés',
    'no_loaded_spectrum': 'Nincs betöltött spektrum.',
    'save_plot_title': 'Ábra mentése',
    'saved_status': 'Mentve: {path}',
    'runtime_opus_not_available': "A 'brukeropus' nem importálható (OPUS olvasás nem megy).",
    'runtime_no_xy': 'Nincs x/y érték a spektrumfájlban. data_keys=',
    'runtime_unknown_file_type': 'Ismeretlen fájltípus.',
    'runtime_jcamp_no_data': 'JCAMP: nincs adat (XYDATA).',
    'runtime_jcamp_unknown_compression': 'JCAMP: nem sikerült Y adatot kiolvasni (ismeretlen tömörítés?).',
    'runtime_dpt_too_few_points': 'A DPT-ből nem sikerült elég pontot kiolvasni.',
}


ABOUT_PNG_B64 = """
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
dfz4oTHqLYB2aaQ9F79pzh+FMYzdT7JD99T4vCZR1ST1jdnuXLaMeR+Thmp/OPJfnx9Bq4q0uv8B
gZMXETHAztEAAAGFaUNDUElDQyBwcm9maWxlAAB4nH2RvUvDQBjGn6aVilQczCDikKE6WRAVcZQq
FsFCaSu06mBy6Rc0aUhSXBwF14KDH4tVBxdnXR1cBUHwA8Q/QJwUXaTE95JCixjvOO7Hc+/zcPce
IDSrTLNCE4Cm22Y6EZdy+VUp/IogRJohhGRmGcnMYha+4+seAb7fxXiWf92fo18tWAwISMRzzDBt
4g3imU3b4LxPLLKyrBKfE4+bdEHiR64rHr9xLrks8EzRzKbniUViqdTFShezsqkRTxNHVU2nfCHn
scp5i7NWrbP2PfkLIwV9JcN1WiNIYAlJpCBBQR0VVGEjRrtOioU0ncd9/MOuP0UuhVwVMHIsoAYN
susH/4PfvbWKU5NeUiQO9Lw4zscoEN4FWg3H+T52nNYJEHwGrvSOv9YEZj9Jb3S06BEwsA1cXHc0
ZQ+43AGGngzZlF0pSEsoFoH3M/qmPDB4C/SteX1rn+P0AchSr5ZvgINDYKxE2es+7+7t7tu/Ne3+
/QAZKXKDuWW7JQAADRhpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i
77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+Cjx4OnhtcG1ldGEgeG1sbnM6eD0i
YWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDQuNC4wLUV4aXYyIj4KIDxyZGY6UkRG
IHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+
CiAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgIHhtbG5zOnhtcE1NPSJodHRwOi8v
bnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9i
ZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIKICAgIHhtbG5zOmRjPSJodHRwOi8v
cHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIKICAgIHhtbG5zOkdJTVA9Imh0dHA6Ly93d3cuZ2lt
cC5vcmcveG1wLyIKICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAv
IgogICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICB4bXBNTTpE
b2N1bWVudElEPSJnaW1wOmRvY2lkOmdpbXA6YzQyMmU2ZGUtMjU3Yi00MjcwLWI1ZGYtZDczMWIx
NWZmNzRiIgogICB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjUxODYyNTFmLTk3NTAtNDc1Ny1h
NmQxLWNlZTJmMjE4YmZlOSIKICAgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOmUz
MzI5MGMxLWQ4NWItNDdkOC04MGFhLWFkNzA0NDAyMzU2ZiIKICAgZGM6Rm9ybWF0PSJpbWFnZS9w
bmciCiAgIEdJTVA6QVBJPSIyLjAiCiAgIEdJTVA6UGxhdGZvcm09IldpbmRvd3MiCiAgIEdJTVA6
VGltZVN0YW1wPSIxNzc0MDM3NTI1MDA0NTM5IgogICBHSU1QOlZlcnNpb249IjIuMTAuMjQiCiAg
IHRpZmY6T3JpZW50YXRpb249IjEiCiAgIHhtcDpDcmVhdG9yVG9vbD0iR0lNUCAyLjEwIj4KICAg
PHhtcE1NOkhpc3Rvcnk+CiAgICA8cmRmOlNlcT4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFj
dGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNl
SUQ9InhtcC5paWQ6NGE5ZmVjNzctNTJiMC00ZTY1LWJjZjktYzdkNTA3MTUyOWM4IgogICAgICBz
dEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKFdpbmRvd3MpIgogICAgICBzdEV2dDp3aGVu
PSIyMDI2LTAzLTIwVDIxOjEyOjA1Ii8+CiAgICA8L3JkZjpTZXE+CiAgIDwveG1wTU06SGlzdG9y
eT4KICA8L3JkZjpEZXNjcmlwdGlvbj4KIDwvcmRmOlJERj4KPC94OnhtcG1ldGE+CiAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
IAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAog
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg
ICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAKPD94cGFja2V0IGVu
ZD0idyI/PnCrQ18AAAAGYktHRAD/AP8A/6C9p5MAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElN
RQfqAxQUDARTJ6jlAAAAGXRFWHRDb21tZW50AENyZWF0ZWQgd2l0aCBHSU1QV4EOFwAADUJJREFU
eNrtnXmQHFUdxz+vWUJuhCVIOJIA8ptkEwJJSIGBgFwJhyCIIEJUJJDIWUUhoggqKlhY4sElN+JK
gRQIGBM5hAQCxCAhZHPszi+CIVwhB1dOdifz/KM7Mhmmu2d6Zna7Z+dbtbW7/V73637f/r3f8X7v
taGO2EBELgYmA01AO9Dq/dyuqrNLvZ6pd2lsiH0cmBhQpQWYoqpz6+QmCKlUapK1trkowoy5xVp7
mapuCKvr1Lu262GtPbaEuucDM0Skd53chAhvifUPAx4PI7hObjzwboRzxgN/rZMbf7wS8byJInJN
ndwYwxjzcBmnXyEi4+vWsr8bso2n93oBA72ffLQBG4D3gTdUNVvhe3gU+ErE01tUdb9uSW5KpI+F
4cB+wJ7Azt7fjcCQiP3QBsxzHOfZbDb7vKq2lklub+Bh4JhPJZpZ1tIC7AYc5718fjhXVe+seXJF
ZIBncBxmjBlnrT2gE5p9EbgVeEhVN5Zx70M9azirqnfkHB8FPAEM8Dn1PWBvVV1fc+SKyGjgFNwo
z5guvJXVwHXALcUEGkp8xkOBWQG8/UBVr6sZcr0H/jlwaMxubRlwpareV+Hn/SFwrU/xClUdmHhy
RWQCcDVwUMxv9Ulgsqq+VaHndoCFuJMLhfANVX0gka7QyJH79heRezz9c1ACbnkCsFhEvlqJi3lW
+oUBVc5PpOSKyNHAHcDghA44N6vqhRXqi2cDVNEAVV3tJIjYKd4Ql1RiAS4QkWYR2bYC13ogoOzY
xAzLqZRMBW6rEcN+EvBEMbM6IQiKap2aiGFZRC4CbqhBd3w2cEw57pKIPAMcXqBoPbCDE3Nip9Qo
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
""".strip()

class ToolbarNoSave(NavigationToolbar2Tk):
    toolitems = tuple(t for t in NavigationToolbar2Tk.toolitems if t[0] != "Save")

    # Do not pack automatically, because the UI uses grid layout.
    def __init__(self, canvas, window, **kwargs):
        super().__init__(canvas, window, pack_toolbar=False, **kwargs)

def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)

def app_dir() -> str:
    """Return the folder where user-editable app files should be stored."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def settings_file_path() -> str:
    return os.path.join(app_dir(), "SpectraViewer.ini")

def normalize_metadata_encoding(value: str) -> str:
    value = (value or DEFAULT_METADATA_ENCODING).strip()
    return value if value in ENCODING_VALUE_TO_LABEL else DEFAULT_METADATA_ENCODING

def decode_meta_text(value, metadata_encoding: str = DEFAULT_METADATA_ENCODING):
    """
    Decode OPUS metadata text using a user-selected code page.

    In auto mode the brukeropus result is returned unchanged. For manual modes,
    the already-returned string is first mapped back to Latin-1 bytes, then
    decoded using the selected encoding. If that round-trip is unsafe, keep the
    original value rather than replacing valid Unicode characters with '?'.
    """
    metadata_encoding = normalize_metadata_encoding(metadata_encoding)
    if value is None or metadata_encoding == DEFAULT_METADATA_ENCODING:
        return value

    if isinstance(value, bytes):
        try:
            return value.decode(metadata_encoding, errors="replace")
        except Exception:
            return value.decode("latin-1", errors="replace")

    if isinstance(value, str):
        try:
            raw = value.encode("latin-1", errors="strict")
        except UnicodeEncodeError:
            return value
        try:
            return raw.decode(metadata_encoding, errors="replace")
        except Exception:
            return value

    return value

def extract_opus_parameter_editor_metadata(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Dict[str, str]:
    """
    Extract the latest Sample Name / Sample Form values written by OPUS
    ParameterEditor from the OPUS history area, if present.

    Some OPUS files contain multiple SNM/SFM occurrences. In files modified
    through OPUS Edit Parameter or by macros using ParameterEditor, brukeropus
    may return an older parameter occurrence while OPUS displays the newer
    edited value. This helper is read-only and affects metadata display only.
    """
    try:
        data = Path(path).read_bytes()
    except Exception:
        return {}

    result: Dict[str, str] = {}

    # Prefer the explicit OPUS command history, because it records the edited
    # parameter values that OPUS itself subsequently displays.
    pattern = re.compile(
        rb"COMMAND_LINE\s+ParameterEditor\s*\(.*?\{(?P<params>.*?)\}\);",
        re.DOTALL,
    )

    matches = list(pattern.finditer(data))
    if matches:
        params = matches[-1].group("params")
        for key in (b"SNM", b"SFM"):
            m = re.search(key + rb"='(?P<value>[^']*)'", params, re.DOTALL)
            if m is not None:
                raw_value = m.group("value")
                # Decode as Latin-1 first to preserve byte values, then apply
                # the same user-selected metadata decoding path used elsewhere.
                text_value = raw_value.decode("latin-1", errors="replace")
                result[key.decode("ascii")] = decode_meta_text(text_value, metadata_encoding) or ""

    return result

def is_opus_like(path: str) -> bool:
    ext = Path(path).suffix
    return bool(ext) and ext[1:].isdigit()

def is_jcamp_like(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in (".dx", ".jdx")

def is_dpt_like(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == ".dpt"

def is_supported_spectrum(path: str) -> bool:
    return is_opus_like(path) or is_jcamp_like(path) or is_dpt_like(path)

@dataclass
class Spectrum:
    x: np.ndarray
    y: np.ndarray
    title: str
    xunit: str = "cm⁻¹"
    yunit: str = ""
    meta: Dict[str, Any] = None
    path: str = ""

def read_opus_file(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Spectrum:
    if opus_read is None:
        raise RuntimeError(UI_TEXT["runtime_opus_not_available"])

    opus = opus_read(path)  # OPUSFile
    keys = list(getattr(opus, "data_keys", []) or [])

    # Preferred spectrum data types.
    candidates = [("a", "Absorbance"), ("ab", "Absorbance"), ("tr", "Transmittance"),
                  ("sm", "Single-channel sample"), ("rf", "Single-channel reference")]

    spec_obj = None
    spec_label = None

    for k, label in candidates:
        if k in keys and hasattr(opus, k):
            o = getattr(opus, k)
            if hasattr(o, "x") and hasattr(o, "y"):
                spec_obj, spec_label = o, label
                break

    if spec_obj is None:
        for k in keys:
            if hasattr(opus, k):
                o = getattr(opus, k)
                if hasattr(o, "x") and hasattr(o, "y"):
                    spec_obj, spec_label = o, str(k)
                    break

    if spec_obj is None:
        raise RuntimeError(UI_TEXT["runtime_no_xy"] + str(keys))

    x = np.asarray(spec_obj.x, dtype=float)
    y = np.asarray(spec_obj.y, dtype=float)

    snm = decode_meta_text(getattr(opus, "snm", "") or "", metadata_encoding) or ""
    sfm = decode_meta_text(getattr(opus, "sfm", "") or "", metadata_encoding) or ""

    # OPUS files may contain multiple SNM/SFM occurrences after metadata editing.
    # If a ParameterEditor history entry is present, use its latest values for
    # display, because these match the metadata shown by OPUS itself.
    edited_meta = extract_opus_parameter_editor_metadata(path, metadata_encoding)
    if "SNM" in edited_meta:
        snm = edited_meta["SNM"]
    if "SFM" in edited_meta:
        sfm = edited_meta["SFM"]

    title = os.path.basename(path)
    if sfm or snm:
        title = (sfm + " - " + snm).strip(" -")

    meta = {
        "sample_name": snm,
        "sample_form": sfm,
        "data_keys": keys,
        "y_label_hint": spec_label or ""
    }

    return Spectrum(x=x, y=y, title=title, xunit="cm⁻¹", yunit=spec_label or "", meta=meta, path=path)

def read_jcamp(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Spectrum:
    import re
    meta: Dict[str, str] = {}
    data_lines: List[str] = []
    in_xy = False

    # In Auto mode, keep the previous JCAMP/DX behavior: UTF-8 with replacement.
    # In manual modes, decode the text file directly with the selected encoding.
    # This affects JCAMP metadata display (e.g. TITLE, SAMPLING PROCEDURE) while
    # the numeric x/y data remain ASCII-compatible and are parsed as before.
    metadata_encoding = normalize_metadata_encoding(metadata_encoding)
    text_encoding = "utf-8" if metadata_encoding == DEFAULT_METADATA_ENCODING else metadata_encoding

    def keyval(line: str):
        s = line[2:].strip()
        if "=" in s:
            k, v = s.split("=", 1)
            return k.strip().upper(), v.strip()
        return s.strip().upper(), ""

    with open(path, "r", encoding=text_encoding, errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.upper().startswith("##END"):
                break
            if line.startswith("##"):
                k, v = keyval(line)
                meta[k] = v
                if k == "XYDATA":
                    in_xy = True
                continue
            if in_xy:
                data_lines.append(line)

    if not data_lines:
        raise RuntimeError(UI_TEXT["runtime_jcamp_no_data"])

    firstx = float(meta.get("FIRSTX", "0"))
    deltax = float(meta.get("DELTAX", "1"))
    npoints = int(meta.get("NPOINTS", "0") or "0")
    yfactor = float(meta.get("YFACTOR", "1"))
    if npoints <= 0:
        npoints = 10**9

    packed = any(re.search(r"\d[+-]\d", ln) and (" " not in ln) for ln in data_lines[:25])

    ys: List[float] = []

    if packed:
        for ln in data_lines:
            nums = re.findall(r"[+-]?\d+", ln)
            if len(nums) >= 2:
                for s in nums[1:]:
                    ys.append(float(int(s)))
    else:
        for ln in data_lines:
            parts = ln.replace(",", " ").replace(";", " ").split()
            if len(parts) >= 2:
                for tok in parts[1:]:
                    try:
                        tok2 = tok.replace("D", "E").replace("d", "e")
                        ys.append(float(tok2))
                    except ValueError:
                        pass

    if len(ys) < 10:
        raise RuntimeError(UI_TEXT["runtime_jcamp_unknown_compression"])

    ys = ys[:npoints]
    x = firstx + np.arange(len(ys)) * deltax
    y = np.asarray(ys, dtype=float) * yfactor

    title = meta.get("TITLE", os.path.basename(path))
    xunit = meta.get("XUNITS", "1/CM")
    yunit = meta.get("YUNITS", "")

    sampling = meta.get("SAMPLING PROCEDURE", "")

    return Spectrum(
        x=x, y=y,
        title=title,
        xunit=xunit,
        yunit=yunit,
        meta={"sample_name": title, "sample_form": sampling},
        path=path
    )

def read_dpt_simple(path: str) -> Spectrum:
    xs = []
    ys = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            # OPUS DPT: "x,y" (comma separator, decimal point).
            parts = line.split(",")
            if len(parts) < 2:
                # Fallback for whitespace-separated data.
                parts = line.split()
                if len(parts) < 2:
                    continue
            try:
                x = float(parts[0])
                y = float(parts[1])
            except ValueError:
                continue
            xs.append(x)
            ys.append(y)

    if len(xs) < 10:
        raise RuntimeError(UI_TEXT["runtime_dpt_too_few_points"])

    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)

    meta = {
        "sample_name": "",
        "sample_form": "",
        "y_label_hint": ""  # vagy "Absorbance", ha fixen azt akarod
    }

    title = os.path.basename(path)
    return Spectrum(x=x, y=y, title=title, xunit="cm⁻¹", yunit="", meta=meta, path=path)

def read_any(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Spectrum:
    if is_opus_like(path):
        return read_opus_file(path, metadata_encoding=metadata_encoding)
    if is_jcamp_like(path):
        return read_jcamp(path, metadata_encoding=metadata_encoding)
    if is_dpt_like(path):
        return read_dpt_simple(path)
    raise RuntimeError(UI_TEXT["runtime_unknown_file_type"])

def scan_folder(folder: str, recursive: bool) -> List[str]:
    folder = os.path.abspath(folder)
    out: List[str] = []
    if recursive:
        for dirpath, _, filenames in os.walk(folder):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if is_supported_spectrum(p):
                    out.append(p)
    else:
        for fn in os.listdir(folder):
            p = os.path.join(folder, fn)
            if os.path.isfile(p) and is_supported_spectrum(p):
                out.append(p)
    out.sort(key=lambda s: s.lower())
    return out

# Single file mode implementation: context rebuild + navigation button state (2026-06-14)
# -------- UI --------

# dynamic base class: with DnD support if available
_BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk

class App(_BaseTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} {VERSION_NUMBER}")
        #self.geometry("900x650")
        # Set the main window icon.
        try:
            self.iconbitmap(resource_path(r"assets\SpectraViewer.ico"))
        except Exception as e:
            print("Icon not set:", e)

        self.settings_path = settings_file_path()
        self.settings = self.load_settings()

        self.folder_var = tk.StringVar(value=self.get_setting("open", "last_path", ""))
        self.recursive_var = tk.BooleanVar(value=self.get_setting_bool("open", "recursive", True))
        self.single_file_var = tk.BooleanVar(value=self.get_setting_bool("open", "single_file", False))
        self._recursive_before_single = bool(self.recursive_var.get())
        self.invert_x_var = tk.BooleanVar(value=self.get_setting_bool("view", "invert_x", False))
        self.crosshair_var = tk.BooleanVar(value=self.get_setting_bool("view", "crosshair", True))
        self.status_var = tk.StringVar(value=UI_TEXT["initial_status"])
        self.line_color = self.get_setting("view", "line_color", DEFAULT_LINE_COLOR) or DEFAULT_LINE_COLOR
        self.metadata_encoding = normalize_metadata_encoding(
            self.get_setting("metadata", "encoding", DEFAULT_METADATA_ENCODING)
        )
        self.encoding_var = tk.StringVar(value=ENCODING_VALUE_TO_LABEL[self.metadata_encoding])
        self.files: List[str] = []
        self.idx: int = -1
        self.current: Optional[Spectrum] = None
        self._build_ui()
        self._bind_keys()
        self._setup_dnd()  # Drag & Drop init (if available)
        if bool(self.single_file_var.get()):
            self.recursive_chk.state(["disabled"])
        self.update_idletasks()  # segít a pontosabb méretekhez

        # Initial window size, restored from INI if available; otherwise scaled to the screen.
        saved_geometry = self.get_setting("window", "geometry", "").strip()
        if saved_geometry:
            try:
                self.geometry(saved_geometry)
            except Exception:
                self.set_default_geometry()
        else:
            self.set_default_geometry()

        # Minimum window size.
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Restore the last opened file/folder after the UI and saved settings are ready.
        self.after(100, self.restore_last_path_on_startup)

    # --- Settings / INI memory ---
    def load_settings(self) -> configparser.ConfigParser:
        cfg = configparser.ConfigParser()
        if os.path.isfile(settings_file_path()):
            try:
                cfg.read(settings_file_path(), encoding="utf-8")
            except Exception as e:
                print("Settings not loaded:", e)
        return cfg

    def get_setting(self, section: str, key: str, default: str = "") -> str:
        try:
            return self.settings.get(section, key, fallback=default)
        except Exception:
            return default

    def get_setting_bool(self, section: str, key: str, default: bool = False) -> bool:
        try:
            return self.settings.getboolean(section, key, fallback=default)
        except Exception:
            return default

    def set_default_geometry(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = int(sw * 0.65)
        h = int(sh * 0.65)
        x = int((sw - w) / 2)
        y = int((sh - h) / 3)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def save_settings(self):
        cfg = configparser.ConfigParser()

        cfg["view"] = {
            "line_color": str(self.line_color or DEFAULT_LINE_COLOR),
            "crosshair": str(bool(self.crosshair_var.get())).lower(),
            "invert_x": str(bool(self.invert_x_var.get())).lower(),
        }

        last_path = self.folder_var.get().strip()
        active_file = self.get_active_file_path() if hasattr(self, "current") else ""
        if bool(self.single_file_var.get()) and active_file:
            last_path = active_file

        cfg["open"] = {
            "single_file": str(bool(self.single_file_var.get())).lower(),
            "recursive": str(bool(self.recursive_var.get())).lower(),
            "last_path": last_path,
        }

        cfg["window"] = {
            "geometry": self.geometry(),
        }

        cfg["metadata"] = {
            "encoding": normalize_metadata_encoding(self.metadata_encoding),
        }

        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            print("Settings not saved:", e)

    def on_close(self):
        self.save_settings()
        self.destroy()

    def restore_last_path_on_startup(self):
        """Restore the last file or folder from SpectraViewer.ini without disruptive startup warnings."""
        last_path = (self.folder_var.get() or "").strip()
        if not last_path:
            self.status_var.set(UI_TEXT["initial_status"])
            return

        p = os.path.abspath(os.path.expanduser(last_path))

        if not os.path.exists(p):
            self.status_var.set(UI_TEXT["last_path_not_found_status"])
            return

        # Folder restore. Do not show startup message boxes; use the status line instead.
        if os.path.isdir(p):
            self.folder_var.set(p)
            if bool(self.single_file_var.get()):
                self.status_var.set(UI_TEXT["last_path_single_folder_status"])
                return

            files = scan_folder(p, recursive=bool(self.recursive_var.get()))
            if not files:
                self.status_var.set(UI_TEXT["last_path_no_spectrum_status"])
                return

            if len(files) > WARN_FILE_COUNT:
                self.status_var.set(UI_TEXT["last_path_too_many_status"].format(count=len(files)))
                return

            self.files = files
            self.idx = 0
            self.update_counter()
            self.load_current()
            self.status_var.set(UI_TEXT["last_path_restored_status"].format(path=p))
            return

        # File restore.
        if os.path.isfile(p):
            if not is_supported_spectrum(p):
                self.status_var.set(UI_TEXT["last_path_unsupported_status"])
                return

            if bool(self.single_file_var.get()):
                self.open_single_file(p)
                self.status_var.set(UI_TEXT["last_path_restored_status"].format(path=p))
                return

            folder = os.path.dirname(p)
            self.folder_var.set(folder)
            files = scan_folder(folder, recursive=bool(self.recursive_var.get()))

            if not files:
                self.status_var.set(UI_TEXT["last_path_no_spectrum_status"])
                return

            if len(files) > WARN_FILE_COUNT:
                self.status_var.set(UI_TEXT["last_path_too_many_status"].format(count=len(files)))
                return

            self.files = files
            target = os.path.normcase(os.path.abspath(p))
            self.idx = 0
            for i, item in enumerate(self.files):
                if os.path.normcase(os.path.abspath(str(item))) == target:
                    self.idx = i
                    break
            self.update_counter()
            self.load_current()
            self.status_var.set(UI_TEXT["last_path_restored_status"].format(path=p))
            return

        self.status_var.set(UI_TEXT["last_path_not_found_status"])

    # --- Drag & Drop support ---
    def _setup_dnd(self):
        if not DND_AVAILABLE:
            return

        def reg(widget):
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # whole window + the main interactive widgets
        reg(self)

        # after UI is built, these exist
        if getattr(self, "header", None) is not None:
            reg(self.header)
        if getattr(self, "canvas", None) is not None:
            reg(self.canvas.get_tk_widget())

    def _on_drop(self, event):
        """
        event.data is usually a Tcl list:
          - one item: C:/path/file.dx
          - or multiple items
          - paths containing spaces may be grouped as: {C:/path with space/file.dx}
        """
        data = getattr(event, "data", "") or ""
        if not data:
            return "break"

        # Split Tcl list data; this also handles {...} grouping.
        try:
            items = list(self.tk.splitlist(data))
        except Exception:
            items = [data]

        paths: List[str] = []
        for it in items:
            p = (it or "").strip()
            if p.startswith("{") and p.endswith("}"):
                p = p[1:-1]
            p = p.strip().strip('"')
            if p:
                paths.append(p)

        if not paths:
            return "break"

        first = paths[0]

        if bool(self.single_file_var.get()):
            if len(paths) > 1:
                messagebox.showwarning(
                    UI_TEXT["single_file_title"],
                    UI_TEXT["single_file_drop_multiple"]
                )
                return "break"
            self.open_path(first)
        elif len(paths) > 1:
            # Load a mixed ad-hoc spectrum list, regardless of where the files came from.
            self.open_dropped_items_as_playlist(paths)
        else:
            # Same behavior as typing a path and pressing Enter (open_path).
            self.open_path(first)

        # Update the path field: folder path for folders, parent folder for files.
        try:
            ap = os.path.abspath(os.path.expanduser(first))
            if os.path.isdir(ap):
                self.folder_var.set(ap)
            elif os.path.isfile(ap):
                self.folder_var.set(os.path.dirname(ap))
        except Exception:
            pass

        return "break"

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, sticky="ew")

        ttk.Label(top, text=UI_TEXT["path_label"]).pack(side=tk.LEFT)
        e = ttk.Entry(top, textvariable=self.folder_var, width=65)
        e.pack(side=tk.LEFT, padx=(6, 6), fill=tk.X, expand=True)
        e.bind("<Return>", self.on_path_enter)

        self.fldr_btn = ttk.Button(top, text=UI_TEXT["folder_button"], command=self.choose_folder)
        self.fldr_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.file_btn = ttk.Button(top, text=UI_TEXT["file_button"], command=self.choose_file)
        self.file_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.recursive_chk = ttk.Checkbutton(top, text=UI_TEXT["recursive_checkbox"], variable=self.recursive_var, command=self.rescan)
        self.recursive_chk.pack(side=tk.LEFT, padx=(0, 10))

        self.single_file_chk = ttk.Checkbutton(top, text=UI_TEXT["single_file_checkbox"], variable=self.single_file_var, command=self.on_single_file_toggle)
        self.single_file_chk.pack(side=tk.LEFT, padx=(0, 10))

        self.about_btn = ttk.Button(top, text=UI_TEXT["about_button"], command=self.show_about)
        self.about_btn.pack(side=tk.RIGHT)

        nav = ttk.Frame(self, padding=(8, 0, 8, 8))
        nav.grid(row=1, column=0, sticky="ew")

        self.prev_btn = ttk.Button(nav, text=UI_TEXT["prev_button"], command=self.prev)
        self.prev_btn.pack(side=tk.LEFT)
        self.next_btn = ttk.Button(nav, text=UI_TEXT["next_button"], command=self.next)
        self.next_btn.pack(side=tk.LEFT, padx=(6, 12))
        self.save_btn = ttk.Button(nav, text=UI_TEXT["save_image_button"], command=self.save_current_plot)
        self.save_btn.pack(side=tk.LEFT, padx=(6, 12))
        #self.clr_btn = ttk.Button(nav, text=UI_TEXT["color_button"], command=self.choose_color).pack(side=tk.LEFT, padx=(6, 12))
        self.clr_btn = ttk.Button(nav, text=UI_TEXT["color_button"], command=self.choose_color)
        self.clr_btn.pack(side=tk.LEFT, padx=(6, 12))

        self.counter_lbl = ttk.Label(nav, text="0/0")
        self.counter_lbl.pack(side=tk.LEFT)

        ttk.Checkbutton(nav, text=UI_TEXT["invert_x_checkbox"], variable=self.invert_x_var, command=self.redraw).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(nav, text=UI_TEXT["crosshair_checkbox"], variable=self.crosshair_var, command=self.update_crosshair_visibility).pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(nav, text=UI_TEXT["metadata_encoding_label"]).pack(side=tk.LEFT, padx=(40, 4))
        self.encoding_combo = ttk.Combobox(
            nav,
            textvariable=self.encoding_var,
            values=[label for label, _value in ENCODING_OPTIONS],
            state="readonly",
            width=30,
        )
        self.encoding_combo.pack(side=tk.LEFT, padx=(0, 0))
        self.encoding_combo.bind("<<ComboboxSelected>>", self.on_encoding_change)

        mid = ttk.Frame(self, padding=2)
        mid.grid(row=2, column=0, sticky="nsew")

        fig = Figure(figsize=(7, 5), dpi=100)
        self.ax = fig.add_subplot(111)
        #fig.subplots_adjust(left=0.07, right=0.99, top=0.97, bottom=0.09)
        fig.subplots_adjust(left=0.07, right=0.99, top=0.97, bottom=0.14)
        self.ax.set_xlabel(UI_TEXT["axis_wavenumber"])
        self.ax.set_ylabel(UI_TEXT["axis_intensity"])

        # Copyable header (filename / sample name / sample form)
        # mid grid: 3 rows (header, canvas, toolbar); the canvas expands.
        mid.grid_rowconfigure(1, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        self.header = tk.Text(mid, height=3, wrap="none", borderwidth=0)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.header.configure(font=("Segoe UI", 12), state="disabled", padx=8, pady=0, highlightthickness=0)

        self.canvas = FigureCanvasTkAgg(fig, master=mid)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        toolbar = ToolbarNoSave(self.canvas, mid)
        toolbar.update()
        toolbar.grid(row=2, column=0, sticky="ew", pady=(2, 0))

        # crosshair
        self.vline = self.ax.axvline(np.nan, color="black", linewidth=0.5)
        self.hline = self.ax.axhline(np.nan, color="black", linewidth=0.5)
        self.coord_text = self.ax.text(0.01, 0.99, "", transform=self.ax.transAxes, va="top")

        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_press_event", self.on_plot_button_press)

        status = ttk.Label(self, textvariable=self.status_var, padding=(8, 4))
        status.grid(row=3, column=0, sticky="ew")

        self.update_navigation_state()

    def _bind_keys(self):
        self.bind_all("<Left>", self._on_left)
        self.bind_all("<Right>", self._on_right)
        self.bind("<Prior>", lambda e: self.jump(-25))              # PageUp
        self.bind("<Next>", lambda e: self.jump(+25))               # PageDown
        self.bind("<Home>", lambda e: self.first())
        self.bind("<End>", lambda e: self.last())
        self.bind_all("<Control-s>", self._on_ctrl_s)
        self.bind_all("<Control-S>", self._on_ctrl_s)
        self.bind_all("<Control-Shift-o>", self._on_ctrl_shift_o)   # mappa
        self.bind_all("<Control-Shift-O>", self._on_ctrl_shift_o)
        self.bind_all("<Control-o>", self._on_ctrl_o)               # file
        self.bind_all("<Control-O>", self._on_ctrl_o)
        self.bind_all("<Control-Shift-c>", self._on_ctrl_shift_c)   # colour
        self.bind_all("<Control-Shift-C>", self._on_ctrl_shift_c)
        self.bind_all("<F1>", self._on_F1)                          # about

    def _on_left(self, event=None):
        if not getattr(self, "prev_btn", None):
            return
        if "disabled" in self.prev_btn.state():
            return "break"
        self.prev_btn.state(['pressed'])
        self.prev_btn.after(150, lambda: self.prev_btn.state(['!pressed']))
        self.prev_btn.invoke()
        return "break"

    def _on_right(self, event=None):
        if not getattr(self, "next_btn", None):
            return
        if "disabled" in self.next_btn.state():
            return "break"
        self.next_btn.state(['pressed'])
        self.next_btn.after(150, lambda: self.next_btn.state(['!pressed']))
        self.next_btn.invoke()
        return "break"

    def _on_ctrl_s(self, event=None):
        if not getattr(self, "save_btn", None):
            return
        self.save_btn.state(['pressed'])
        self.save_btn.after(150, lambda: self.save_btn.state(['!pressed']))
        self.save_btn.invoke()
        #return "break"

    def _on_ctrl_shift_o(self, event=None):
        if not getattr(self, "fldr_btn", None):
            return
        self.fldr_btn.state(['pressed'])
        self.fldr_btn.after(150, lambda: self.fldr_btn.state(['!pressed']))
        self.fldr_btn.invoke()
        #return "break"

    def _on_ctrl_o(self, event=None):
        if not getattr(self, "file_btn", None):
            return
        self.file_btn.state(['pressed'])
        self.file_btn.after(150, lambda: self.file_btn.state(['!pressed']))
        self.file_btn.invoke()
        #return "break"

    def _on_ctrl_shift_c(self, event=None):
        if not getattr(self, "clr_btn", None):
            return
        self.clr_btn.state(['pressed'])
        self.clr_btn.after(150, lambda: self.clr_btn.state(['!pressed']))
        self.clr_btn.invoke()
        #return "break"

    def _on_F1(self, event=None):
        if not getattr(self, "about_btn", None):
            return
        self.about_btn.state(['pressed'])
        self.about_btn.after(150, lambda: self.about_btn.state(['!pressed']))
        self.about_btn.invoke()
        #return "break"

    def choose_folder(self):
        folder = filedialog.askdirectory(title=UI_TEXT["open_folder_title"])
        if not folder:
            return

        if bool(self.single_file_var.get()):
            messagebox.showwarning(
                UI_TEXT["single_file_title"],
                UI_TEXT["single_file_folder_not_allowed"]
            )
            return

        self.open_folder(folder, recursive=self.recursive_var.get())
        self.folder_var.set(folder)

    def confirm_file_count(self, count: int, origin: str = "lista") -> bool:
        if count > MAX_FILE_COUNT:
            messagebox.showerror(
                UI_TEXT["too_many_files_title"],
                UI_TEXT["too_many_files_error"].format(origin=origin, count=count, max_count=MAX_FILE_COUNT)
            )
            return False

        if count > WARN_FILE_COUNT:
            return messagebox.askyesno(
                UI_TEXT["too_many_files_confirm_title"],
                UI_TEXT["too_many_files_confirm"].format(origin=origin, count=count)
            )

        return True

    def choose_file(self):
        # Windows/Tk file dialog wildcards cannot precisely express the
        # "numeric extension only" pattern, so the dialog is intentionally broad,
        # and the actual validation is done in Python.
        filetypes = [
            (UI_TEXT["all_supported_files"], "*.dx;*.jdx;*.dpt;*.0*;*.1*;*.2*;*.3*;*.4*;*.5*;*.6*;*.7*;*.8*;*.9*"),
            ("JCAMP-DX (ASCII)", "*.dx;*.jdx"),
            ("DPT (ASCII)", "*.dpt"),
            (UI_TEXT["opus_numeric_extension"], "*.0*;*.1*;*.2*;*.3*;*.4*;*.5*;*.6*;*.7*;*.8*;*.9*"),
            (UI_TEXT["all_files"], "*.*"),
        ]

        paths = filedialog.askopenfilenames(
            title=UI_TEXT["open_files_title"],
            filetypes=filetypes,
        )

        if not paths:
            return

        valid_paths = [
            p for p in paths
            if is_supported_spectrum(p)
        ]
        invalid_paths = [p for p in paths if p not in valid_paths]

        if not valid_paths:
            messagebox.showwarning(
                UI_TEXT["unsupported_format_title"],
                UI_TEXT["unsupported_selected_message"]
            )
            return

        if bool(self.single_file_var.get()):
            if len(valid_paths) != 1 or len(paths) != 1:
                messagebox.showwarning(
                    UI_TEXT["single_file_title"],
                    UI_TEXT["single_file_select_one"]
                )
                return
            path = valid_paths[0]
            self.open_single_file(path)
            return

        if not self.confirm_file_count(len(valid_paths), UI_TEXT["selected_list_origin"]):
            return

        if invalid_paths:
            max_show = 8
            shown = [os.path.basename(p) for p in invalid_paths[:max_show]]
            more = len(invalid_paths) - len(shown)

            msg = UI_TEXT["selected_files_skipped"].format(
                total=len(paths),
                valid=len(valid_paths),
                invalid=len(invalid_paths),
                shown="\n- ".join(shown),
            )
            if more > 0:
                msg += UI_TEXT["and_more"].format(more=more)

            messagebox.showwarning(UI_TEXT["some_files_skipped_title"], msg)

        if len(valid_paths) == 1:
            path = valid_paths[0]
            self.folder_var.set(os.path.dirname(path))
            self.open_file_with_context(path, recursive=self.recursive_var.get())
        else:
            self.folder_var.set(os.path.dirname(valid_paths[0]))
            self.files = [Path(p) for p in valid_paths]
            self.files.sort()
            self.idx = 0
            self.load_current()

    def load_custom_list(self, file_list):
        self.files = []
        
        for p in file_list:
            # Important: p is a string returned by the file dialog.
            # The rest of the program expects Path objects in the list.
            path_obj = Path(p)
            
            # Check that the path exists and is a file.
            if path_obj.is_file():
                # Add it to the list as a Path object.
                self.files.append(path_obj)
        
        # Sort the Path objects.
        self.files.sort()
        
        if self.files:
            self.idx = 0
            self.load_current()
        else:
            messagebox.showwarning(UI_TEXT["warning_title"], UI_TEXT["no_loadable_file"])

    def on_path_enter(self, _evt=None):
        self.open_path(self.folder_var.get().strip())

    def open_path(self, path: str):
        if not path:
            return

        p = os.path.abspath(os.path.expanduser(path))

        # Invalid path.
        if not os.path.exists(p):
            messagebox.showwarning(UI_TEXT["invalid_path_title"], UI_TEXT["invalid_path_message"])
            return

        # Folder.
        if os.path.isdir(p):
            if bool(self.single_file_var.get()):
                messagebox.showwarning(
                    UI_TEXT["single_file_title"],
                    UI_TEXT["single_file_path_must_be_file"]
                )
                return
            self.open_folder(p, recursive=self.recursive_var.get())
            return

        # File with a valid format.
        if os.path.isfile(p):
            if not is_supported_spectrum(p):
                messagebox.showwarning(UI_TEXT["unsupported_format_title"], UI_TEXT["unsupported_path_message"])
                return

            if bool(self.single_file_var.get()):
                self.open_single_file(p)
            else:
                self.open_file_with_context(p, recursive=self.recursive_var.get())
            return

    def get_active_file_path(self) -> str:
        """Return the currently displayed/selected spectrum path, if available."""
        if self.current is not None and getattr(self.current, "path", ""):
            return os.path.abspath(os.path.expanduser(str(self.current.path)))
        if self.files and 0 <= self.idx < len(self.files):
            return os.path.abspath(os.path.expanduser(str(self.files[self.idx])))
        return ""

    def rebuild_context_from_current_file(self, recursive: bool) -> bool:
        """Rebuild the surrounding folder context from the active spectrum file."""
        current_path = self.get_active_file_path()
        if not current_path or not os.path.isfile(current_path) or not is_supported_spectrum(current_path):
            self.update_counter()
            return False

        folder = os.path.dirname(current_path)
        files = scan_folder(folder, recursive=recursive)

        if not files:
            messagebox.showwarning(
                UI_TEXT["no_match_title"],
                UI_TEXT["no_spectrum_at_path"]
            )
            self.update_counter()
            return False

        if not self.confirm_file_count(len(files), UI_TEXT["folder_context_origin"]):
            self.update_counter()
            self.status_var.set(
                UI_TEXT["context_reload_cancelled"]
            )
            return False

        self.folder_var.set(folder)
        self.files = files

        # Normalized, case-insensitive lookup: more robust for Windows paths,
        # and it also works if list items are Path objects or strings.
        target = os.path.normcase(os.path.abspath(current_path))
        self.idx = 0
        for i, item in enumerate(self.files):
            if os.path.normcase(os.path.abspath(str(item))) == target:
                self.idx = i
                break

        self.update_counter()
        self.load_current()
        return True

    def on_single_file_toggle(self):
        if bool(self.single_file_var.get()):
            self._recursive_before_single = bool(self.recursive_var.get())
            self.recursive_chk.state(["disabled"])

            # Single file mode must not leave a multi-file list active.
            # If a spectrum is currently active, immediately reduce the list to that one file.
            if self.current is not None and self.current.path:
                self.open_single_file(self.current.path)
            else:
                self.update_counter()
                self.status_var.set(UI_TEXT["single_file_enabled_status"])
        else:
            self.recursive_chk.state(["!disabled"])
            restored_recursive = bool(self._recursive_before_single)
            self.recursive_var.set(restored_recursive)

            # When leaving single file mode, return to the original program philosophy:
            # rebuild the context around the current file
            # using the previously preserved recursive setting.
            if self.rebuild_context_from_current_file(recursive=restored_recursive):
                mode = "rekurzív" if restored_recursive else "nem rekurzív"
                self.status_var.set(UI_TEXT["single_file_disabled_rebuilt_status"].format(mode=mode))
            else:
                self.status_var.set(UI_TEXT["single_file_disabled_restored_status"])

    def open_single_file(self, filepath: str):
        filepath = os.path.abspath(os.path.expanduser(str(filepath)))

        if not os.path.isfile(filepath):
            messagebox.showwarning(
                UI_TEXT["invalid_file_title"],
                UI_TEXT["single_file_invalid_path"]
            )
            return

        if not is_supported_spectrum(filepath):
            messagebox.showwarning(UI_TEXT["unsupported_format_title"], UI_TEXT["unsupported_path_message"])
            return

        folder = os.path.dirname(filepath)
        self.folder_var.set(folder)
        self.files = [filepath]
        self.idx = 0
        self.update_counter()
        self.load_current()
        self.status_var.set(UI_TEXT["single_file_title"] + f": {filepath}")

    def open_folder(self, folder: str, recursive: bool):
        folder = os.path.abspath(folder)
        files = scan_folder(folder, recursive=recursive)

        # No spectra found.
        if not files:
            messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_spectrum_at_path"])
            return

        if not self.confirm_file_count(len(files), UI_TEXT["opened_folder_origin"]):
            return

        self.folder_var.set(folder)
        self.files = files
        self.idx = 0
        self.update_counter()
        self.load_current()

    def open_dropped_items_as_playlist(self, paths, recursive=None):
        if bool(self.single_file_var.get()):
            messagebox.showwarning(
                UI_TEXT["single_file_title"],
                UI_TEXT["single_file_select_one"]
            )
            return

        if recursive is None:
            recursive = bool(self.recursive_var.get())

        items = []
        invalid_paths = []
        for p in paths:
            ap = os.path.abspath(os.path.expanduser(p))
            if os.path.isdir(ap):
                items.extend(scan_folder(ap, recursive=recursive))
            elif os.path.isfile(ap):
                if is_supported_spectrum(ap):
                    items.append(ap)
                else:
                    invalid_paths.append(ap)

        # Remove duplicates while preserving order.
        seen = set()
        uniq = []
        for x in items:
            xl = x.lower()
            if xl not in seen:
                seen.add(xl)
                uniq.append(x)

        if not uniq:
            if invalid_paths:
                max_show = 8
                shown = [os.path.basename(p) for p in invalid_paths[:max_show]]
                more = len(invalid_paths) - len(shown)
                msg = UI_TEXT["no_supported_among_items_with_skips"].format(
                    total=len(paths),
                    shown="\n- ".join(shown),
                )
                if more > 0:
                    msg += UI_TEXT["and_more"].format(more=more)
                messagebox.showwarning(UI_TEXT["no_match_title"], msg)
            else:
                messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_supported_among_items"])
            return

        if not self.confirm_file_count(len(uniq), UI_TEXT["selected_list_origin"]):
            return

        if invalid_paths:
            max_show = 8
            shown = [os.path.basename(p) for p in invalid_paths[:max_show]]
            more = len(invalid_paths) - len(shown)
            msg = UI_TEXT["dropped_items_skipped"].format(
                valid=len(uniq),
                invalid=len(invalid_paths),
                shown="\n- ".join(shown),
            )
            if more > 0:
                msg += UI_TEXT["and_more"].format(more=more)
            messagebox.showwarning(UI_TEXT["some_files_skipped_title"], msg)

        self.files = uniq
        self.idx = 0
        self.update_counter()
        self.load_current()
        self.status_var.set(UI_TEXT["custom_list_loaded"].format(count=len(self.files)))

    def open_file_with_context(self, filepath: str, recursive: bool):
        if bool(self.single_file_var.get()):
            self.open_single_file(filepath)
            return

        filepath = os.path.abspath(filepath)
        folder = os.path.dirname(filepath)

        files = scan_folder(folder, recursive=recursive)

        # Rare fallback case, but keep it handled.
        if not files:
            messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_spectrum_at_path"])
            return

        if not self.confirm_file_count(len(files), UI_TEXT["folder_context_origin"]):
            return

        self.folder_var.set(folder)
        self.files = files

        try:
            self.idx = self.files.index(filepath)
        except ValueError:
            # If it was not included for any reason, insert it at the front.
            self.files.insert(0, filepath)
            self.idx = 0

        self.update_counter()
        self.load_current()

    def rescan(self):
        if bool(self.single_file_var.get()):
            self.recursive_var.set(bool(self._recursive_before_single))
            self.status_var.set(UI_TEXT["single_file_subfolders_disabled"])
            return

        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self.files = []
            self.idx = -1
            self.update_counter()
            self.status_var.set(UI_TEXT["invalid_folder_status"])
            return

        requested_recursive = bool(self.recursive_var.get())

        # Do not overwrite the current list before the file count check
        # has completed. This keeps the previous safe state intact
        # if MAX_FILE_COUNT is exceeded or a WARN_FILE_COUNT prompt is rejected.
        new_files = scan_folder(folder, requested_recursive)

        if not self.confirm_file_count(len(new_files), UI_TEXT["folder_context_origin_alt"]):
            # At this point the checkbox state has already changed, because
            # rescan was triggered by the Checkbutton itself. Restore it so
            # the UI reflects what is actually still loaded.
            self.recursive_var.set(not requested_recursive)
            self.update_counter()
            self.status_var.set(
                UI_TEXT["loading_cancelled_previous_kept"]
            )
            return

        self.files = new_files
        self.idx = 0 if self.files else -1
        self.update_counter()
        if self.idx >= 0:
            self.load_current()
        else:
            self.status_var.set(UI_TEXT["no_match_in_folder_status"])
            self.clear_plot()

    def update_counter(self):
        total = len(self.files)
        cur = self.idx + 1 if self.idx >= 0 else 0
        self.counter_lbl.config(text=f"{cur}/{total}")
        self.update_navigation_state()

    def update_navigation_state(self):
        enabled = len(self.files) > 1
        state = ["!disabled"] if enabled else ["disabled"]
        for btn_name in ("prev_btn", "next_btn"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.state(state)

    def update_crosshair_visibility(self):
        on = bool(self.crosshair_var.get())
        for a in (getattr(self, "vline", None), getattr(self, "hline", None), getattr(self, "coord_text", None)):
            if a is not None:
                a.set_visible(on)
        self.canvas.draw_idle()

    def on_encoding_change(self, event=None):
        label = self.encoding_var.get()
        self.metadata_encoding = normalize_metadata_encoding(
            ENCODING_LABEL_TO_VALUE.get(label, DEFAULT_METADATA_ENCODING)
        )
        if self.current is not None or (self.files and 0 <= self.idx < len(self.files)):
            self.load_current()

    def clear_plot(self):
        self.ax.clear()
        self.ax.set_title("")
        self.ax.set_xlabel(UI_TEXT["axis_wavenumber"])
        self.ax.set_ylabel(UI_TEXT["axis_intensity"])
        self.canvas.draw_idle()

    def clear_header(self):
        self.header.configure(state="normal")
        self.header.delete("1.0", tk.END)
        self.header.configure(state="disabled")

    def show_header_lines(self, lines):
        clean = [str(x) for x in (lines or []) if str(x).strip()]
        self.header.configure(state="normal")
        self.header.delete("1.0", tk.END)
        self.header.insert("1.0", "\n".join(clean))
        self.header.configure(state="disabled")

    def show_error_state(self, path: str, error_msg: str):
        self.current = None
        self.clear_plot()

        fname = os.path.basename(path) if path else ""
        fullpath = str(path or "")
        msg = str(error_msg or UI_TEXT["unknown_error"])

        wpx = self.canvas.get_tk_widget().winfo_width() or 900
        max_chars = int(wpx / 10)

        header_lines = []
        if fname:
            header_lines.append(self.ellipsize(fname, max_chars))
        if fullpath and fullpath != fname:
            header_lines.append(self.ellipsize(fullpath, max_chars))
        header_lines.append(self.ellipsize(f"{UI_TEXT['error_prefix']}: {msg}", max_chars))
        self.show_header_lines(header_lines)

        if fullpath:
            self.status_var.set(f"{UI_TEXT['error_prefix']}: {msg} | {UI_TEXT['file_label']}: {fullpath}")
        else:
            self.status_var.set(f"{UI_TEXT['error_prefix']}: {msg}")

    def load_current(self):
        if self.idx < 0 or self.idx >= len(self.files):
            return
        
        path = self.files[self.idx]
        try:
            spec = read_any(str(path), metadata_encoding=self.metadata_encoding) 
            self.current = spec
            self.status_var.set(str(path))
            self.redraw()
        except Exception as ex:
            self.show_error_state(str(path), str(ex))
        finally:
            self.update_counter()

    def choose_color(self):
        # Returns: ((r, g, b), "#rrggbb") or (None, None).
        _, hexcol = colorchooser.askcolor(color=self.line_color, title=UI_TEXT["spectrum_color_title"])
        if hexcol:
            self.line_color = hexcol
            self.redraw()

    def show_about(self, _evt=None):
        # If the About window is already open, just bring it to the front.
        existing = getattr(self, "about_win", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        about = tk.Toplevel(self)
        self.about_win = about

        # Set the About window icon.
        try:
            about.iconbitmap(resource_path(r"assets\SpectraViewer.ico"))
        except Exception:
            pass

        # Closing via Esc, OK, or the window close button uses the same handler.
        def on_close(event=None):
            if about.winfo_exists():
                about.destroy()
            self.about_win = None

        about.title(UI_TEXT["about_window_title"])
        about.transient(self)
        about.resizable(False, False)
        about.protocol("WM_DELETE_WINDOW", on_close)
        about.bind("<Escape>", on_close)

        # Icon.
        try:
            about.iconbitmap(resource_path(r"assets\SpectraViewer.ico"))
        except Exception:
            pass

        # --- UI ---
        top_frame = ttk.Frame(about)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        b64 = "".join(ABOUT_PNG_B64.split())
        img = tk.PhotoImage(data=b64)
        about._about_img = img  # ne garbage-collectolja

        tk.Label(top_frame, image=img).pack(side="left")

        tk.Label(
            top_frame,
            text=f"{APP_NAME}",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(side="left", padx=(10, 0), pady=(8, 0))

        dnd_line = UI_TEXT["about_dnd_line"] if DND_AVAILABLE else ""

        text = UI_TEXT["about_text"].format(
            version=VERSION_NUMBER,
            author=AUTHOR,
            year=YEAR,
            dnd_line=dnd_line,
        )

        tk.Label(about, text=text, justify="left", anchor="w").pack(
            padx=15, pady=(0, 10), fill="both"
        )

        ok_btn = ttk.Button(about, text="OK", command=on_close)
        ok_btn.pack(pady=(0, 10))
        ok_btn.focus_set()
        ok_btn.bind("<Return>", on_close)

        # UX refinement: keep the window focused and in front.
        about.lift()
        about.focus_force()

    def redraw(self):
        if self.current is None:
            return
        spec = self.current
        self.ax.clear()
        self.ax.plot(spec.x, spec.y, color=self.line_color)

        # Header lines: 1) filename, 2) sample name, 3) sample form.
        fname = os.path.basename(spec.path) if spec.path else spec.title
        sname = (spec.meta or {}).get("sample_name", "") or ""
        sform = (spec.meta or {}).get("sample_form", "") or ""

        wpx = self.canvas.get_tk_widget().winfo_width() or 900
        max_chars = int(wpx / 10)

        t1 = self.ellipsize(fname, max_chars)
        t2 = self.ellipsize(sname, max_chars)
        t3 = self.ellipsize(sform, max_chars)

        lines = [t1]
        if t2: lines.append(t2)
        if t3: lines.append(t3)

        self.header.configure(state="normal")
        self.header.delete("1.0", tk.END)
        self.header.insert("1.0", "\n".join(lines))
        self.header.configure(state="disabled")
        self.ax.set_xlabel(spec.xunit)
        self.ax.set_ylabel(spec.yunit or "Intensity")

        if not self.invert_x_var.get():
            try:
                self.ax.invert_xaxis()
            except Exception:
                pass

        # crosshair reinit after clear
        self.vline = self.ax.axvline(np.nan, color="black", linewidth=0.5)
        self.hline = self.ax.axhline(np.nan, color="black", linewidth=0.5)
        self.coord_text = self.ax.text(0.01, 0.99, "", transform=self.ax.transAxes, va="top")
        self.update_crosshair_visibility()

        self.canvas.draw_idle()

    def ellipsize(self, s: str, max_chars: int) -> str:
        s = s or ""
        if max_chars < 10:
            max_chars = 10
        if len(s) <= max_chars:
            return s
        return s[: max_chars - 3].rstrip() + "..."

    def current_default_png_name(self) -> str:
        if not self.current or not self.current.path:
            return "spectrum.png"
        base = os.path.basename(self.current.path)
        return base + ".png"

    def save_current_plot(self):
        if self.current is None:
            messagebox.showinfo(UI_TEXT["save_message_title"], UI_TEXT["no_loaded_spectrum"])
            return

        default = self.current_default_png_name()
        initialdir = os.path.dirname(self.current.path) if self.current.path else os.getcwd()

        out = filedialog.asksaveasfilename(
            title=UI_TEXT["save_plot_title"],
            initialdir=initialdir,
            initialfile=default,
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
                ("All files", "*.*"),
            ],
        )
        if not out:
            return

        # Save exactly what is currently visible.
        # If the crosshair is OFF it is not visible; if it is ON it will be included in the export.
        self.canvas.figure.savefig(out, dpi=300, bbox_inches="tight")
        self.status_var.set(UI_TEXT["saved_status"].format(path=out))

    def on_plot_button_press(self, event):
        # Right mouse button in the spectrum display area:
        # toggle the crosshair checkbox state.
        # Under Matplotlib/Tk, the right mouse button is usually event.button == 3.
        if event.inaxes != self.ax or event.button != 3:
            return

        self.crosshair_var.set(not bool(self.crosshair_var.get()))
        self.update_crosshair_visibility()
        return "break"

    def on_motion(self, event):
        if not self.crosshair_var.get():
            return
        if self.current is None or event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        x = float(event.xdata)
        y = float(event.ydata)
        self.vline.set_xdata([x, x])
        self.hline.set_ydata([y, y])
        self.coord_text.set_text(f"x={x:.2f}  y={y:.6g}")
        self.canvas.draw_idle()

    # Navigation with wrap-around behavior.
    def prev(self):
        if not self.files:
            return
        self.idx = (self.idx - 1) % len(self.files)
        self.load_current()

    def next(self):
        if not self.files:
            return
        self.idx = (self.idx + 1) % len(self.files)
        self.load_current()

    # Alternative navigation behavior: stop at the first/last item instead of wrapping.
    #def prev(self):
    #    if not self.files:
    #        return
    #    self.idx = max(0, self.idx - 1)
    #    self.load_current()

    #def next(self):
    #    if not self.files:
    #        return
    #    self.idx = min(len(self.files) - 1, self.idx + 1)
    #    self.load_current()

    def jump(self, delta: int):
        if not self.files:
            return
        self.idx = max(0, min(len(self.files) - 1, self.idx + delta))
        self.load_current()

    def first(self):
        if not self.files:
            return
        self.idx = 0
        self.load_current()

    def last(self):
        if not self.files:
            return
        self.idx = len(self.files) - 1
        self.load_current()

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
