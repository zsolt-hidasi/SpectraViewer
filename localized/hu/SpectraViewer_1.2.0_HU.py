# SpectraViewer
# Copyright (c) 2026 Zsolt Hidasi
# All rights reserved.
# Use of this program is governed by the accompanying terms of use.

import os, sys
import re
import configparser
import base64
import json
import zlib
import tempfile
import unicodedata
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
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
from matplotlib.ticker import AutoMinorLocator, NullLocator

APP_NAME = "SpectraViewer"
VERSION_NUMBER = "1.2.0"
AUTHOR = "Hidasi Zsolt"
YEAR = "2026"

DEFAULT_WARN_FILE_COUNT = 5000
MAX_FILE_COUNT = 20000

# OPUS native files use a numeric extension and this 4-byte magic signature.
OPUS_MAGIC = b"\x0A\x0A\xFE\xFE"

# The OPUS warning threshold is user-configurable (SpectraViewer.ini).
# The separate hard file-size limit is fixed and applies before OPUS decoding.
DEFAULT_LARGE_OPUS_WARN_MB = 20
MAX_LARGE_OPUS_WARN_MB = 100
MAX_OPUS_FILE_MB = 100
MAX_OPUS_FILE_BYTES = MAX_OPUS_FILE_MB * 1024 * 1024

DEFAULT_METADATA_ENCODING = "auto"
DEFAULT_LINE_COLOR = "#1f77b4"
DEFAULT_LINE_WIDTH = 1.5
MIN_LINE_WIDTH = 0.1
MAX_LINE_WIDTH = 5.0

# Supported processed OPUS spectrum types.
# The same keys are used by brukeropus for single spectra (data_keys)
# and multi-spectrum DataSeries (series_keys).
SUPPORTED_OPUS_SPECTRAL_TYPES = {
    "a": "Absorbance",
    "t": "Transmittance",
    "r": "Reflectance",
    "km": "Kubelka–Munk",
}
OPUS_SPECTRAL_TYPE_PRIORITY = ("a", "t", "r", "km")

UI_TEXT = {
    "initial_status": "Válassz egy fájlt vagy mappát…",
    "busy_status": "Feldolgozás folyamatban… Kérem, várjon.",
    "loading_spectrum_status": "Betöltés: {filename}… Kérem, várjon.",
    "last_path_not_found_status": "Az utoljára használt elérési út nem található. Válassz egy fájlt vagy mappát…",
    "last_path_unsupported_status": "Az utoljára használt elérési út nem támogatott fájlformátumra mutat. Válassz egy fájlt vagy mappát…",
    "last_path_single_folder_status": "Az utoljára használt elérési út egy mappára mutat, de a \"Single file\" mód be van kapcsolva. Válassz egy spektrumfájlt…",
    "last_path_no_spectrum_status": "Az utoljára használt elérési útvonalon nem található támogatott spektrumfájl.",
    "last_path_too_many_status": "Az utoljára használt mappa {count} támogatott fájlt tartalmaz, ezért nem töltődött be automatikusan. Szükség esetén nyisd meg kézzel.",
    "last_path_restored_status": "Az előző munkamenet visszaállítva: {path}",
    "path_label": "Elérési út:",
    "folder_button": "Mappa…",
    "file_button": "Fájl…",
    "recursive_checkbox": "almappák bejárása",
    "single_file_checkbox": "\"Single file\" mód",
    "about_button": "Névjegy",
    "prev_button": "◀ Előző",
    "next_button": "Következő ▶",
    "export_image_button": "Képexport",
    "save_jcamp_button": "JCAMP-DX export",
    "save_jcamp_title": "Spektrum exportálása JCAMP-DX formátumban",
    "save_jcamp_error_title": "JCAMP-DX exportálási hiba",
    "save_jcamp_same_source": "A forrásfájl nem írható felül. Válassz másik célhelyet.",
    "save_jcamp_filter": "JCAMP-DX (*.dx)",
    "jcamp_export_xy_required": "A JCAMP-DX-exporthoz legalább két X/Y-adatpár szükséges (azonos számú X- és Y-értékkel).",
    "jcamp_export_nonfinite": "A JCAMP-DX-export nem tudja biztonságosan tárolni a NaN vagy végtelen értékeket.",
    "file_access_title": "Fájlhozzáférési hiba",
    "file_locked_message": "A fájlhoz nem lehet hozzáférni. Lehetséges, hogy egy másik alkalmazás (például az OPUS) zárolta.\n\n{path}\n\n{reason}",
    "color_button": "Szín",
    "invert_x_checkbox": "X fordítás",
    "crosshair_checkbox": "Szálkereszt",
    "metadata_encoding_label": "Metaadat-kódolás:",
    "encoding_auto": "Automatikus / OPUS alapértelmezés",
    "encoding_cp1252": "Windows-1252 / nyugat-európai",
    "encoding_cp1250": "Windows-1250 / közép-európai",
    "encoding_utf8": "UTF-8",
    "encoding_latin1": "Latin-1 / ISO-8859-1",
    "encoding_latin2": "Latin-2 / ISO-8859-2",
    "info_button": "INFO",
    "info_window_title": "INFO",
    "info_no_block": "Ehhez a spektrumhoz nem érhető el INFO-blokk.",
    "info_no_filled_fields": "Az INFO-blokk nem tartalmaz kitöltött mezőket.",
    "axis_wavenumber": "Wavenumber (cm⁻¹)",
    "axis_intensity": "Intensity",

    "single_file_title": "\"Single file\" mód",
    "single_file_drop_multiple": "\"Single file\" módban egyszerre csak egy spektrumfájlt húzhatsz az ablakba.",
    "single_file_folder_not_allowed": "\"Single file\" módban mappa helyett egy konkrét spektrumfájlt nyiss meg.",
    "single_file_select_one": "\"Single file\" módban egyszerre pontosan egy támogatott spektrumfájl nyitható meg.",
    "single_file_path_must_be_file": "\"Single file\" módban az elérési útnak egy konkrét spektrumfájlra kell mutatnia, nem mappára.",
    "single_file_invalid_path": "\"Single file\" módban a megadott elérési útnak egy létező spektrumfájlra kell mutatnia.",
    "single_file_subfolders_disabled": "\"Single file\" módban az almappák bejárása nem használható.",
    "single_file_enabled_status": "\"Single file\" mód bekapcsolva.",
    "single_file_disabled_rebuilt_status": "\"Single file\" mód kikapcsolva. A mappakörnyezet újraépítve ({mode}).",
    "single_file_disabled_restored_status": "\"Single file\" mód kikapcsolva. Az almappák bejárásának korábbi beállítása visszaállítva.",
    "mode_recursive": "almappákkal együtt",
    "mode_nonrecursive": "almappák nélkül",
    "series_default_label": "Sorozat",
    "series_stored_status": "{path} | {label} {index}/{count} (tárolt sorszám: {stored_index})",

    "too_many_files_title": "Túl sok fájl",
    "too_many_files_error": "Forrás: {origin}\nTámogatott fájlok száma: {count}\n\nEz meghaladja a megengedett felső határt ({max_count}).\nSzűkítsd a kijelölést, vagy válassz kisebb mappát.",
    "too_many_files_confirm_title": "Nagy fájllista",
    "too_many_files_confirm": "Forrás: {origin}\nTámogatott fájlok száma: {count}\n\nEnnyi spektrum betöltése sok memóriát igényelhet, és lelassíthatja a programot.\nSzeretnéd folytatni?",

    "large_opus_title": "Nagy méretű OPUS-fájl",
    "large_opus_list_title": "Nagy méretű OPUS-fájlok",
    "large_opus_choice_intro": "Forrás: {origin}\nA {threshold_mb} MB-os figyelmeztetési küszöböt meghaladó OPUS-fájlok száma: {count}.\n\nBetöltheted a teljes fájllistát, kihagyhatod ezeket a fájlokat, vagy megszakíthatod a műveletet.",
    "large_opus_choice_single": "Kiválasztott OPUS-fájl: {filename} ({size_mb:.1f} MB).",
    "large_opus_choice_hard": "A fájlok közül {count} meghaladja a {max_mb} MB-os maximális méretkorlátot. Ezek szerepelhetnek a fájllistában, de nem nyithatók meg.",
    "large_opus_choice_small_count": "Szűrt lista választásakor {kept} fájl marad a {total} támogatott fájlból.",
    "large_opus_choice_no_small": "A kiválasztott fájlok között nincs a figyelmeztetési küszöb alatti fájl.",
    "large_opus_choice_all_button": "A teljes fájllista megnyitása",
    "large_opus_choice_small_button": "Csak a figyelmeztetési küszöb alatti fájlok megnyitása",
    "large_opus_choice_cancel_button": "Művelet megszakítása",
    "filtered_large_opus_status": "Szűrt lista: {count} fájl betöltve; {excluded} OPUS-fájl kihagyva ({threshold_mb} MB felett).",
    "startup_large_opus_cancelled": "Az utoljára használt elérési út nem töltődött be, mert megszakítottad a nagyméretű OPUS-fájlok kiválasztását.",
    "excluded_large_opus_counter": " (-{count} nagy OPUS-fájl kihagyva)",
    "opus_file_too_large": "Ez az OPUS-fájl {size_mb:.1f} MB méretű, amely meghaladja a SpectraViewerben megnyitható {max_mb} MB-os maximális fájlméretet.\nA korlát haladó felhasználók számára a forráskódban található MAX_OPUS_FILE_MB konstans értékének SAJÁT FELELŐSSÉGRE TÖRTÉNŐ módosításával megemelhető.\nA módosítás a nagyméretű állományok betöltése esetében jelentős memóriahasználattal és hosszabb feldolgozási idővel járhat!",

    "all_supported_files": "Minden támogatott fájl",
    "jcamp_ascii_filter": "JCAMP-DX (ASCII)",
    "dpt_ascii_filter": "DPT (ASCII)",
    "opus_numeric_extension": "OPUS / numerikus kiterjesztés",
    "all_files": "Minden fájl",
    "open_files_title": "Fájlok megnyitása",
    "open_folder_title": "Mappa megnyitása",
    "unsupported_format_title": "Nem támogatott formátum",
    "unsupported_selected_message": "A kijelölt fájl(ok) formátuma nem támogatott.",
    "unsupported_path_message": "A megadott fájl formátuma nem támogatott.",
    "some_files_skipped_title": "Néhány fájl kimaradt",
    "selected_files_skipped": "A kijelölt {total} fájlból {valid} támogatott; {invalid} fájl kimaradt.\n\nKihagyott fájlok:\n- {shown}",
    "dropped_items_skipped": "A kijelölt elemek közül {valid} támogatott fájl betöltődött, {invalid} fájl kimaradt.\n\nKihagyott fájlok:\n- {shown}",
    "and_more": "\n- … és még {more} fájl",
    "selected_list_origin": "kijelölt fájlok",
    "opened_folder_origin": "megnyitott mappa",
    "folder_context_origin": "aktuális mappakörnyezet",
    "folder_context_origin_alt": "aktuális mappakörnyezet",
    "warning_title": "Figyelem",
    "no_loadable_file": "Nincs betölthető fájl.",
    "invalid_path_title": "Érvénytelen elérési út",
    "invalid_path_message": "A megadott elérési út (fájl vagy mappa) érvénytelen.",
    "no_match_title": "Nincs találat",
    "no_spectrum_at_path": "A megadott elérési úton nem található támogatott spektrumfájl.",
    "context_reload_cancelled": "A mappakörnyezet újratöltése megszakadt. A jelenlegi fájl maradt betöltve.",
    "invalid_file_title": "Érvénytelen fájl",
    "no_supported_among_items": "A kijelölt elemek között nem található támogatott fájlformátum.",
    "no_supported_among_items_with_skips": "A kijelölt {total} elem között egyetlen támogatott fájlformátum sem található.\n\nKihagyott fájlok:\n- {shown}",
    "custom_list_loaded": "Egyedi fájllista betöltve: {count} fájl",
    "invalid_folder_status": "Érvénytelen mappa.",
    "loading_cancelled_previous_kept": "A betöltés megszakadt: túl sok fájl. Az előző lista maradt érvényben.",
    "loading_cancelled_large_opus": "A betöltés megszakadt: a nagy méretű OPUS-fájlok megnyitását nem hagytad jóvá. Az előző lista maradt érvényben.",
    "no_match_in_folder_status": "Ebben a mappában nem található támogatott spektrumfájl (OPUS/DX/JDX/DPT).",
    "error_prefix": "Hiba",
    "file_label": "Fájl",
    "unknown_error": "Ismeretlen hiba",
    "spectrum_color_title": "Spektrum színe",
    "invalid_line_width_title": "Érvénytelen vonalvastagság",
    "invalid_line_width_message": "Érvénytelen line_width érték a SpectraViewer.ini fájlban.\n\nMegengedett tartomány: 0,1–5,0.\nAz alapértelmezett 1,5 értéket használja a program.",
    "about_window_title": "Névjegy",
    "ok_button": "OK",
    "about_dnd_line": "\t• Drag&Drop – Fájl vagy mappa behúzása az ablakba\n",
    "about_text": "Verzió: {version} © {author}, {year}\nFejlesztés: {author}, OpenAI\n\nTámogatott spektrumformátumok:\n\t• OPUS (*.0, *.1, …)\n\t• JCAMP-DX (*.dx, *.jdx)\n\t• DPT (*.dpt)\n\nBillentyű- és egérparancsok:\n\t• Ctrl+O – Fájl megnyitása\n\t• Ctrl+Shift+O – Mappa megnyitása\n\t• Bal / jobb nyíl – Előző / következő fájl\n\t• Page Up / Page Down – Ugrás 25 fájllal vissza / előre\n\t• Home / End – Első / utolsó fájl\n\t• Fel / le nyíl – Előző / következő spektrum a DataSeries-ben\n\t• Jobb kattintás a grafikonon – Szálkereszt be-/kikapcsolása\n\t• Ctrl+E – Az aktuális spektrum exportálása JCAMP-DX formátumban\n\t• Ctrl+Shift+E – A spektrum exportálása képként\n\t• Ctrl+Shift+C – A spektrum színének kiválasztása / módosítása\n{dnd_line}\t• F1 – Névjegy\n\nHasználati útmutató: SpectraViewerMan_HU.pdf\n\nA beállításokat a SpectraViewer.ini fájl tárolja. Az alapértelmezett beállítások visszaállításához töröld ezt a fájlt.",
    "save_message_title": "Exportálás",
    "no_loaded_spectrum": "Nincs betöltött spektrum.",
    "save_plot_title": "Kép exportálása",
    "saved_status": "Mentve: {path}",

    "runtime_opus_not_available": "A „brukeropus” Python-csomag nem importálható, ezért az OPUS-fájlok nem olvashatók be.",
    "runtime_no_xy": "A spektrumfájlban nem találhatók X/Y-adatok. data_keys=",
    "runtime_no_xy_series_keys": "; series_keys=",
    "runtime_series_2d_shape": "Kétdimenziós (2D) OPUS DataSeries-adatokat várt a program, de az Y-adattömb alakja: {shape}.",
    "runtime_series_x_shape": "Az OPUS DataSeries Y-adattömbjének alakja ({y_shape}) nem egyeztethető össze az X-adatsor hosszával ({x_length}).",
    "runtime_unknown_file_type": "Ismeretlen fájltípus.",
    "runtime_jcamp_no_data": "JCAMP: nem találhatók spektrális adatok (XYDATA/XYPOINTS).",
    "runtime_jcamp_unknown_compression": "JCAMP: az Y-adatok nem olvashatók be (ismeretlen tömörítés?).",
    "jcamp_nonfinite_factor": "Érvénytelen JCAMP-skálázási szorzó: az érték nem véges szám.",
    "jcamp_invalid_numeric_header": "Érvénytelen numerikus JCAMP-fejlécadat: {reason}",
    "jcamp_truncated_xydata": "Hiányos JCAMP XYDATA-adatsor: {actual} Y-érték található a várt {expected} helyett.",
    "jcamp_invalid_x_header": "Érvénytelen JCAMP X-tengelyadat a fejlécben: {reason}",
    "jcamp_invalid_xypoints_row": "Érvénytelen JCAMP XYPOINTS-sor: az X/Y-értékek nem alkotnak párokat.",
    "jcamp_invalid_xypoints_number": "Érvénytelen numerikus érték a JCAMP XYPOINTS-adatok között.",
    "jcamp_xypoints_count_mismatch": "A JCAMP XYPOINTS-adatsor {actual} pontot tartalmaz a várt {expected} helyett.",
    "jcamp_invalid_compressed_metadata": "Érvénytelen vagy túl nagy méretű tömörített JCAMP-metaadat.",
    "runtime_dpt_too_few_points": "A DPT-fájlból nem sikerült elegendő adatpontot beolvasni.",
    # Console messages are kept here too, so no English status/diagnostic text
    # is scattered throughout the shared English/Hungarian application code.
    "console_icon_not_set": "Az alkalmazásikon beállítása sikertelen: {error}",
    "console_invalid_warn_file_count": "Érvénytelen [advanced] warn_file_count beállítás a SpectraViewer.ini fájlban; az alapértelmezett {default} értéket használja a program.",
    "console_invalid_large_opus_warn_mb": "Érvénytelen [advanced] large_opus_warn_mb beállítás a SpectraViewer.ini fájlban; az alapértelmezett {default} MB-os értéket használja a program.",
    "console_settings_not_loaded": "Nem sikerült betölteni a beállításokat: {error}",
    "console_settings_not_saved": "Nem sikerült menteni a beállításokat: {error}",
}

# Reusable metadata encoding labels; only the UI_TEXT values need translation.
ENCODING_OPTIONS = [
    (UI_TEXT["encoding_auto"], "auto"),
    (UI_TEXT["encoding_cp1252"], "cp1252"),
    (UI_TEXT["encoding_cp1250"], "cp1250"),
    (UI_TEXT["encoding_utf8"], "utf-8"),
    (UI_TEXT["encoding_latin1"], "iso-8859-1"),
    (UI_TEXT["encoding_latin2"], "iso-8859-2"),
]
ENCODING_LABEL_TO_VALUE = dict(ENCODING_OPTIONS)
ENCODING_VALUE_TO_LABEL = {value: label for label, value in ENCODING_OPTIONS}


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

def parse_line_width(value):
    """Return (line_width, is_valid) for a manually editable INI value."""
    try:
        # Accept both decimal point and decimal comma in manually edited INI files.
        width = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return DEFAULT_LINE_WIDTH, False

    if not np.isfinite(width) or width < MIN_LINE_WIDTH or width > MAX_LINE_WIDTH:
        return DEFAULT_LINE_WIDTH, False

    return width, True

def parse_warn_file_count(value):
    """Return (warning_count, is_valid) for the advanced INI setting."""
    try:
        count = int(str(value).strip())
    except (TypeError, ValueError):
        return DEFAULT_WARN_FILE_COUNT, False

    # Keep the warning threshold meaningful below the hard safety limit.
    if count < 1 or count >= MAX_FILE_COUNT:
        return DEFAULT_WARN_FILE_COUNT, False

    return count, True


def parse_large_opus_warn_mb(value):
    """Return (warning_mb, is_valid) for the advanced INI setting."""
    try:
        mb = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return DEFAULT_LARGE_OPUS_WARN_MB, False

    if not np.isfinite(mb) or mb <= 0 or mb > MAX_LARGE_OPUS_WARN_MB:
        return DEFAULT_LARGE_OPUS_WARN_MB, False

    # Keep whole-number values tidy in the INI and warning text.
    if mb.is_integer():
        mb = int(mb)

    return mb, True


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



def extract_opus_active_parameter_metadata(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING, file_bytes: Optional[bytes] = None) -> Dict[str, str]:
    """
    Extract the active Sample Name / Sample Form values from the OPUS Sample
    Parameter block referenced by the file directory.

    Important: edited OPUS files may contain more than one genuine binary
    SNM/SFM parameter block. The active edited Sample Parameter block can occur
    *before* the original measurement block in the file, while later SNM/SFM
    strings may also occur in the textual history / COMMAND_LINE area.
    Therefore file-position order is not a reliable way to determine the
    currently active values.

    The OPUS directory identifies Sample Parameter blocks by type code 0xA0.
    In edited files tested here, the current/editable Sample Parameter block
    uses the unflagged directory type (0x000000A0), while the original
    measurement block remains as 0x400000A0. If an unflagged block is present,
    prefer it. If not, fall back to the last directory-referenced Sample
    Parameter block so original, never-edited files continue to work.

    Only structured binary parameter records inside the selected directory
    block are parsed. Text fragments in OPUS history are therefore excluded by
    construction.

    If *file_bytes* is supplied, reuse that already-read OPUS binary buffer.
    This keeps the current SpectraViewer optimization for large OPUS/DataSeries
    files and avoids reading the same file again for metadata extraction.
    """
    if file_bytes is None:
        try:
            data = Path(path).read_bytes()
        except Exception:
            return {}
    else:
        data = file_bytes

    # Basic OPUS header validation.
    if len(data) < 24 or data[:4] != OPUS_MAGIC:
        return {}

    try:
        directory_start = int.from_bytes(data[12:16], "little", signed=True)
        num_blocks = int.from_bytes(data[20:24], "little", signed=True)
    except Exception:
        return {}

    if directory_start < 0 or num_blocks <= 0 or num_blocks > 10000:
        return {}

    directory_end = directory_start + num_blocks * 12
    if directory_end > len(data):
        return {}

    # brukeropus decodes the meaningful OPUS block type from the low 22 bits.
    # For Sample Parameters that low-bit type code is 0xA0.
    block_type_mask = 0x003FFFFF
    sample_parameter_type = 0x000000A0
    original_variant_flag = 0x40000000

    sample_blocks = []

    for index in range(num_blocks):
        entry_pos = directory_start + index * 12

        type_raw = int.from_bytes(
            data[entry_pos:entry_pos + 4], "little", signed=False
        )
        size_words = int.from_bytes(
            data[entry_pos + 4:entry_pos + 8], "little", signed=True
        )
        block_start = int.from_bytes(
            data[entry_pos + 8:entry_pos + 12], "little", signed=True
        )

        if (type_raw & block_type_mask) != sample_parameter_type:
            continue

        if size_words <= 0 or block_start < 0:
            continue

        block_size = size_words * 4
        block_end = block_start + block_size
        if block_end > len(data):
            continue

        sample_blocks.append(
            (index, type_raw, block_start, block_size)
        )

    if not sample_blocks:
        return {}

    # Edited files can retain the original 0x400000A0 block in addition to a
    # current 0x000000A0 block. Prefer the unflagged/current variant. If there
    # are several such blocks, use the last directory entry among them.
    current_blocks = [
        block for block in sample_blocks
        if not (block[1] & original_variant_flag)
    ]

    _index, _type_raw, block_start, block_size = (
        current_blocks[-1] if current_blocks else sample_blocks[-1]
    )

    block = data[block_start:block_start + block_size]

    result: Dict[str, str] = {}
    loc = 0

    while loc + 8 <= len(block):
        key_bytes = block[loc:loc + 3]

        # Structured OPUS parameter records use a three-byte key followed by NUL.
        if block[loc + 3:loc + 4] != b"\x00":
            break

        try:
            key = key_bytes.decode("ascii")
        except UnicodeDecodeError:
            break

        param_type = int.from_bytes(
            block[loc + 4:loc + 6], "little", signed=False
        )
        size_words = int.from_bytes(
            block[loc + 6:loc + 8], "little", signed=False
        )
        payload_size = size_words * 2

        value_start = loc + 8
        value_end = value_start + payload_size

        if value_end > len(block):
            break

        if key == "END":
            break

        if key in ("SNM", "SFM") and param_type == 2:
            raw_value = block[value_start:value_end].split(b"\x00", 1)[0]

            if raw_value:
                text_value = raw_value.decode("latin-1", errors="replace")
                text_value = (
                    decode_meta_text(text_value, metadata_encoding) or ""
                )
                if text_value:
                    # If a malformed block contains a duplicate key, keep its
                    # last structured value.
                    result[key] = text_value

        loc = value_end

    return result


def _decode_opus_binary_text(raw_value: bytes, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> str:
    """Decode a NUL-terminated OPUS binary text value using the metadata setting."""
    raw_value = (raw_value or b"").split(b"\x00", 1)[0]
    if not raw_value:
        return ""

    # Keep the same conversion path as the existing SNM/SFM binary fallback.
    # In Auto mode this preserves the OPUS/default byte interpretation; a manual
    # code page selection (e.g. cp1250) is applied by decode_meta_text().
    text_value = raw_value.decode("latin-1", errors="replace")
    return decode_meta_text(text_value, metadata_encoding) or ""


def _read_opus_string_record(data: bytes, pos: int, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Optional[str]:
    """Read one OPUS string parameter record starting at *pos*, or return None."""
    if pos < 0 or pos + 8 > len(data):
        return None

    # OPUS parameter record: 3-byte key + NUL + 2-byte type + 2-byte size.
    # Type 2 is a text parameter; size is stored in 16-bit words.
    if data[pos + 3:pos + 4] != b"\x00":
        return None
    param_type = int.from_bytes(data[pos + 4:pos + 6], "little", signed=False)
    if param_type != 2:
        return None

    size_words = int.from_bytes(data[pos + 6:pos + 8], "little", signed=False)
    payload_size = size_words * 2
    value_start = pos + 8
    value_end = value_start + payload_size
    if payload_size < 0 or value_end > len(data):
        return None

    return _decode_opus_binary_text(data[value_start:value_end], metadata_encoding)


def extract_opus_info_fields(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING, file_bytes: Optional[bytes] = None) -> List[Dict[str, str]]:
    """
    Extract the active OPUS INFO mask field definitions (T01..T99) together
    with their values (I01..I99) directly from the binary INFO parameter block.

    Important: after INFO editing OPUS may omit the MOP text record that was
    present in the original file and instead store a HIS change-history record
    before END. Therefore MOP must not be required to identify the active block.

    The active INFO block is located from a structured INP text parameter and
    bounded by the first structured END record that follows it. Only structured
    Tnn/Inn text parameter records inside that block are accepted. Plain-text
    copies inside HIS / COMMAND_LINE do not match the binary record signature.

    Returns every defined field in mask order, including empty values. Each item
    contains: code (Inn), label (Tnn without an optional 'TEXT:' prefix), value.
    """
    if file_bytes is None:
        try:
            data = Path(path).read_bytes()
        except Exception:
            return []
    else:
        data = file_bytes

    inp_marker = b"INP\x00\x02\x00"
    end_marker = b"END\x00\x00\x00\x00\x00"
    field_pattern = re.compile(rb"([TI])(\d{2})\x00\x02\x00")

    search_from = 0
    while True:
        inp_pos = data.find(inp_marker, search_from)
        if inp_pos < 0:
            break
        search_from = inp_pos + 1

        # INFO blocks normally also contain INM/IFN near INP. Requiring at least
        # one of them makes accidental INP-like byte sequences less plausible,
        # while still keeping the parser tolerant of older/nonstandard files.
        provisional_end = min(len(data), inp_pos + 65536)
        end_pos = data.find(end_marker, inp_pos + 8, provisional_end)
        if end_pos < 0:
            end_pos = provisional_end

        inm_pos = data.find(b"INM\x00\x02\x00", inp_pos, min(end_pos, inp_pos + 1024))
        ifn_pos = data.find(b"IFN\x00\x02\x00", inp_pos, min(end_pos, inp_pos + 1024))

        markers = []
        for match in field_pattern.finditer(data, inp_pos, end_pos):
            pos = match.start()
            kind = match.group(1).decode("ascii")
            number = match.group(2).decode("ascii")
            value = _read_opus_string_record(data, pos, metadata_encoding)
            if value is not None:
                markers.append((pos, kind, number, value))

        if not markers:
            continue

        # If neither companion INFO parameter is present, accept the block only
        # when it still contains a plausible Tnn/Inn pair.
        if inm_pos < 0 and ifn_pos < 0:
            nums_t = {number for _pos, kind, number, _value in markers if kind == "T"}
            nums_i = {number for _pos, kind, number, _value in markers if kind == "I"}
            if not (nums_t & nums_i):
                continue

        # Preserve mask order by the first appearance of each numeric field code.
        ordered_numbers: List[str] = []
        seen_numbers = set()
        records: Dict[tuple, str] = {}

        for _pos, kind, number, value in markers:
            records[(kind, number)] = value
            if number not in seen_numbers:
                seen_numbers.add(number)
                ordered_numbers.append(number)

        fields: List[Dict[str, str]] = []
        for number in ordered_numbers:
            label = records.get(("T", number), "") or ""
            value = records.get(("I", number), "") or ""

            if not label and not value:
                continue

            if label.upper().startswith("TEXT:"):
                label = label[5:]
            label = label.strip() or f"I{number}"

            fields.append({
                "code": f"I{number}",
                "label": label,
                "value": value,
            })

        if fields:
            return fields

    return []

def has_numeric_extension(path: str) -> bool:
    ext = Path(path).suffix
    return bool(ext) and ext[1:].isdigit()


def has_opus_magic(path: str) -> bool:
    """Cheap OPUS validation: read only the native 4-byte file signature."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == OPUS_MAGIC
    except OSError:
        return False


def is_opus_like(path: str) -> bool:
    # Numeric extension is necessary but not sufficient: files such as
    # "ttx.1" or "something.7" must not be mistaken for native OPUS data.
    return has_numeric_extension(path) and has_opus_magic(path)


def spectrum_file_access_error(path: str) -> Optional[OSError]:
    """Probe plausible spectrum files to distinguish inaccessible from unsupported.

    A Windows share lock may make even the OPUS signature unreadable.  Do not
    classify that situation as an invalid format merely because the signature
    check returned False.  No content is modified by this read-only probe.
    """
    if not (has_numeric_extension(path) or is_jcamp_like(path) or is_dpt_like(path)):
        return None
    try:
        with open(path, "rb") as stream:
            stream.read(4)
    except OSError as exc:
        return exc
    return None


def is_large_opus_file(path: str, threshold_bytes: int) -> bool:
    """Return True only for valid OPUS files above the supplied warning threshold."""
    if not is_opus_like(path):
        return False
    try:
        return os.path.getsize(path) > threshold_bytes
    except OSError:
        return False

def is_jcamp_like(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in (".dx", ".jdx")

def is_dpt_like(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == ".dpt"

def is_supported_spectrum(path: str) -> bool:
    return is_opus_like(path) or is_jcamp_like(path) or is_dpt_like(path)

def opus_series_as_2d(series):
    """Return OPUS DataSeries as (x, y2d), with rows = spectra."""
    x = np.asarray(series.x, dtype=float).ravel()
    y = np.asarray(series.y, dtype=float)

    if y.ndim != 2:
        raise ValueError(UI_TEXT["runtime_series_2d_shape"].format(shape=y.shape))

    if y.shape[1] == len(x):
        return x, y

    # Defensive fallback for an unexpectedly transposed series.
    if y.shape[0] == len(x):
        return x, y.T

    raise ValueError(
        UI_TEXT["runtime_series_x_shape"].format(y_shape=y.shape, x_length=len(x))
    )


def opus_expand_store_table(store_table, n_spectra: int) -> List[int]:
    """Expand brukeropus store_table ranges to original acquisition indices."""
    if store_table is None:
        return list(range(1, n_spectra + 1))

    try:
        raw = store_table.tolist() if hasattr(store_table, "tolist") else store_table

        if (
            isinstance(raw, (list, tuple))
            and len(raw) == 2
            and all(isinstance(v, (int, np.integer)) for v in raw)
        ):
            pairs = [raw]
        else:
            pairs = list(raw)

        indices: List[int] = []
        for pair in pairs:
            if len(pair) != 2:
                raise ValueError
            start, stop = int(pair[0]), int(pair[1])
            if stop < start:
                raise ValueError
            indices.extend(range(start, stop + 1))

        if len(indices) == n_spectra:
            return indices
    except Exception:
        pass

    return list(range(1, n_spectra + 1))


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
    # Hard safety limit: check the file size before the brukeropus parser or
    # any full-file metadata read can allocate memory for a large OPUS/FPA file.
    size_bytes = os.path.getsize(path)
    if size_bytes > MAX_OPUS_FILE_BYTES:
        raise ValueError(UI_TEXT["opus_file_too_large"].format(
            size_mb=size_bytes / (1024 * 1024), max_mb=MAX_OPUS_FILE_MB,
        ))

    if opus_read is None:
        raise RuntimeError(UI_TEXT["runtime_opus_not_available"])

    opus = opus_read(path)  # OPUSFile
    data_keys = list(getattr(opus, "data_keys", []) or [])
    series_keys = list(getattr(opus, "series_keys", []) or [])

    # Read the binary file only once for direct metadata helpers (SNM/SFM + INFO).
    # This avoids an extra full-file read when browsing large OPUS files.
    try:
        opus_binary = Path(path).read_bytes()
    except Exception:
        opus_binary = None

    spec_obj = None
    spec_label = None
    selected_key = None
    series_y = None
    series_store_indices = None

    # 1) Prefer a supported processed DataSeries when present.
    # This is the key change for line mappings: e.g. an Absorbance DataSeries
    # takes precedence over the single reference spectrum ('rf') that may also
    # be stored in the same OPUS file.
    for key in OPUS_SPECTRAL_TYPE_PRIORITY:
        if key in series_keys and hasattr(opus, key):
            candidate = getattr(opus, key)
            if not (hasattr(candidate, "x") and hasattr(candidate, "y")):
                continue
            try:
                x, y2d = opus_series_as_2d(candidate)
            except Exception:
                continue
            if y2d.shape[0] < 1:
                continue

            spec_obj = candidate
            selected_key = key
            spec_label = SUPPORTED_OPUS_SPECTRAL_TYPES[key]
            series_y = y2d
            series_store_indices = opus_expand_store_table(
                getattr(candidate, "store_table", None),
                y2d.shape[0],
            )
            break

    # 2) Otherwise prefer a supported single processed spectrum.
    if spec_obj is None:
        for key in OPUS_SPECTRAL_TYPE_PRIORITY:
            if key in data_keys and hasattr(opus, key):
                candidate = getattr(opus, key)
                if hasattr(candidate, "x") and hasattr(candidate, "y"):
                    spec_obj = candidate
                    selected_key = key
                    spec_label = SUPPORTED_OPUS_SPECTRAL_TYPES[key]
                    break

    # 3) Backward-compatible fallbacks for OPUS files that contain no supported
    # processed spectrum. Keep the old ability to display sample/reference
    # single-channel data or another 1D x/y block rather than rejecting the file.
    if spec_obj is None:
        fallback_candidates = [
            ("sm", "Single-channel sample"),
            ("rf", "Single-channel reference"),
        ]
        for key, label in fallback_candidates:
            if key in data_keys and hasattr(opus, key):
                candidate = getattr(opus, key)
                if hasattr(candidate, "x") and hasattr(candidate, "y"):
                    spec_obj, selected_key, spec_label = candidate, key, label
                    break

    if spec_obj is None:
        for key in data_keys:
            if hasattr(opus, key):
                candidate = getattr(opus, key)
                if hasattr(candidate, "x") and hasattr(candidate, "y"):
                    spec_obj, selected_key, spec_label = candidate, key, str(key)
                    break

    if spec_obj is None:
        raise RuntimeError(
            UI_TEXT["runtime_no_xy"]
            + str(data_keys)
            + UI_TEXT["runtime_no_xy_series_keys"]
            + str(series_keys)
        )

    if series_y is not None:
        x = np.asarray(spec_obj.x, dtype=float).ravel()
        y = np.asarray(series_y[0], dtype=float)
    else:
        x = np.asarray(spec_obj.x, dtype=float).ravel()
        y = np.asarray(spec_obj.y, dtype=float).ravel()

    snm = decode_meta_text(getattr(opus, "snm", "") or "", metadata_encoding) or ""
    sfm = decode_meta_text(getattr(opus, "sfm", "") or "", metadata_encoding) or ""

    # OPUS files may contain multiple SNM/SFM occurrences after metadata editing.
    # Read them from the active Sample Parameter block referenced by the OPUS
    # directory, not from file-position order or history / COMMAND_LINE text.
    active_meta = extract_opus_active_parameter_metadata(
        path, metadata_encoding, file_bytes=opus_binary
    )
    if "SNM" in active_meta:
        snm = active_meta["SNM"]
    if "SFM" in active_meta:
        sfm = active_meta["SFM"]

    title = os.path.basename(path)
    if sfm or snm:
        title = (sfm + " - " + snm).strip(" -")

    info_fields = extract_opus_info_fields(
        path, metadata_encoding, file_bytes=opus_binary
    )

    meta = {
        "sample_name": snm,
        "sample_form": sfm,
        "data_keys": data_keys,
        "series_keys": series_keys,
        "selected_opus_key": selected_key or "",
        "y_label_hint": spec_label or "",
        "info_fields": info_fields,
    }

    if series_y is not None:
        meta.update({
            "series_y": series_y,
            "series_index": 0,
            "series_count": int(series_y.shape[0]),
            "series_key": selected_key or "",
            "series_label": spec_label or "",
            "series_store_indices": series_store_indices or list(
                range(1, int(series_y.shape[0]) + 1)
            ),
        })

    return Spectrum(
        x=x,
        y=y,
        title=title,
        xunit="cm⁻¹",
        yunit=spec_label or "",
        meta=meta,
        path=path,
    )

def read_jcamp(path: str, metadata_encoding: str = DEFAULT_METADATA_ENCODING) -> Spectrum:
    """Read the legacy supported XYDATA and uncompressed XYPOINTS formats.

    This is not a general ASDF/DIF/SQZ decoder. Existing simple/packed XYDATA
    handling is retained; SpectraViewer exports use uncomplicated AFFN numbers.
    """
    headers: Dict[str, str] = {}
    data_lines: List[str] = []
    table_kind = None
    current_header = None

    metadata_encoding = normalize_metadata_encoding(metadata_encoding)
    text_encoding = "utf-8" if metadata_encoding == DEFAULT_METADATA_ENCODING else metadata_encoding

    with open(path, "r", encoding=text_encoding, errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("##"):
                body = line[2:]
                key, _, val = body.partition("=")
                key = key.strip().upper()
                val = val.strip()
                if key == "END":
                    break
                if key in ("XYDATA", "XYPOINTS"):
                    table_kind = key
                    headers[key] = val
                    current_header = None
                    continue
                if table_kind is not None:
                    # Additional records after the data table are not data.
                    table_kind = "FINISHED"
                headers[key] = val
                current_header = key
            elif table_kind in ("XYDATA", "XYPOINTS"):
                data_lines.append(line)
            elif current_header in ("$SV_METADATA_UTF8_BASE64", "$SV_METADATA_ZLIB_BASE64"):
                headers[current_header] += line

    if not data_lines:
        raise RuntimeError(UI_TEXT["runtime_jcamp_no_data"])

    table = "XYPOINTS" if "XYPOINTS" in headers and table_kind in ("XYPOINTS", "FINISHED") else "XYDATA"
    # Prefer whichever data table was encountered when collecting the rows.
    # The exporter writes exactly one data table per file.
    if "XYDATA" in headers and "XYPOINTS" not in headers:
        table = "XYDATA"

    try:
        npoints = int(headers.get("NPOINTS", "0") or "0")
        xfactor = float(headers.get("XFACTOR", "1") or "1")
        yfactor = float(headers.get("YFACTOR", "1") or "1")
        if not np.isfinite(xfactor) or not np.isfinite(yfactor):
            raise ValueError(UI_TEXT["jcamp_nonfinite_factor"])
    except (ValueError, TypeError) as exc:
        raise ValueError(UI_TEXT["jcamp_invalid_numeric_header"].format(reason=exc)) from exc

    if table == "XYDATA":
        packed = any(
            re.search(r"\d[+-]\d", ln) and not re.search(r"\s", ln) and not re.search(r"[eEdD][+-]\d", ln)
            for ln in data_lines[:25]
        )
        ys: List[float] = []
        if packed:
            # Backward compatibility with the legacy simple signed-integer PAC reader.
            for ln in data_lines:
                nums = re.findall(r"[+-]?\d+", ln)
                if len(nums) >= 2:
                    ys.extend(float(int(part)) for part in nums[1:])
        else:
            for ln in data_lines:
                parts = re.split(r"[,;\s]+", ln.strip())
                if len(parts) >= 2:
                    for part in parts[1:]:
                        try:
                            ys.append(float(part.replace("D", "E").replace("d", "e")))
                        except ValueError:
                            pass
        if len(ys) < 2:
            raise RuntimeError(UI_TEXT["runtime_jcamp_unknown_compression"])
        if npoints > 0 and len(ys) < npoints:
            raise ValueError(UI_TEXT["jcamp_truncated_xydata"].format(actual=len(ys), expected=npoints))
        if npoints > 0:
            ys = ys[:npoints]
        try:
            firstx = float(headers.get("FIRSTX", "0"))
            if "DELTAX" in headers:
                deltax = float(headers["DELTAX"])
            elif npoints > 1 and "LASTX" in headers:
                deltax = (float(headers["LASTX"]) - firstx) / (npoints - 1)
            else:
                deltax = 1.0
        except ValueError as exc:
            raise ValueError(UI_TEXT["jcamp_invalid_x_header"].format(reason=exc)) from exc
        # FIRSTX and DELTAX are already the actual X values. XFACTOR
        # only applies to X numbers explicitly stored in the data table.
        x = firstx + np.arange(len(ys), dtype=float) * deltax
        y = np.asarray(ys, dtype=float) * yfactor
    else:
        xs: List[float] = []
        ys: List[float] = []
        for ln in data_lines:
            parts = [p for p in re.split(r"[,;\s]+", ln) if p]
            if len(parts) % 2:
                raise ValueError(UI_TEXT["jcamp_invalid_xypoints_row"])
            for idx in range(0, len(parts), 2):
                try:
                    xs.append(float(parts[idx].replace("D", "E").replace("d", "e")))
                    ys.append(float(parts[idx + 1].replace("D", "E").replace("d", "e")))
                except ValueError as exc:
                    raise ValueError(UI_TEXT["jcamp_invalid_xypoints_number"]) from exc
        if len(xs) < 2:
            raise RuntimeError(UI_TEXT["runtime_jcamp_unknown_compression"])
        if npoints > 0 and len(xs) != npoints:
            raise ValueError(UI_TEXT["jcamp_xypoints_count_mismatch"].format(actual=len(xs), expected=npoints))
        x = np.asarray(xs, dtype=float) * xfactor
        y = np.asarray(ys, dtype=float) * yfactor

    title = headers.get("TITLE", os.path.basename(path))
    xunit = headers.get("XUNITS", "1/CM")
    yunit = headers.get("YUNITS", "")
    sample_name = headers.get("$SV_SAMPLE_NAME", title)
    sample_form = headers.get("$SV_SAMPLE_FORM", headers.get("SAMPLING PROCEDURE", ""))
    spec_meta: Dict[str, Any] = {
        "sample_name": sample_name,
        "sample_form": sample_form,
        "jcamp_headers": {k: v for k, v in headers.items()
                          if k not in ("$SV_METADATA_UTF8_BASE64", "$SV_METADATA_ZLIB_BASE64")},
    }

    # New SV files use losslessly compressed UTF-8 metadata. Continue reading
    # original, uncompressed private metadata from previous development builds.
    metadata_zlib_b64 = headers.get("$SV_METADATA_ZLIB_BASE64", "")
    metadata_utf8_b64 = headers.get("$SV_METADATA_UTF8_BASE64", "")
    if metadata_zlib_b64 or metadata_utf8_b64:
        try:
            if metadata_zlib_b64:
                compressed = base64.b64decode(metadata_zlib_b64, validate=True)
                decompressor = zlib.decompressobj()
                # Bound decompression when opening untrusted external DX files.
                decoded = decompressor.decompress(compressed, 32 * 1024 * 1024 + 1)
                if (len(decoded) > 32 * 1024 * 1024 or not decompressor.eof
                        or decompressor.unconsumed_tail or decompressor.unused_data):
                    raise ValueError(UI_TEXT["jcamp_invalid_compressed_metadata"])
            else:
                decoded = base64.b64decode(metadata_utf8_b64, validate=True)
            original = json.loads(decoded.decode("utf-8"))
            if isinstance(original, dict):
                spec_meta["sv_original_metadata"] = original
                # Recover accented sample names and the original descriptive title.
                base_meta = original.get("spectrum_metadata", {})
                if isinstance(base_meta, dict):
                    spec_meta["sample_name"] = str(base_meta.get("sample_name") or sample_name)
                    spec_meta["sample_form"] = str(base_meta.get("sample_form") or sample_form)
                title = str(original.get("original_title") or title)
                # Use the same internal INFO representation as native OPUS.
                # The GUI does not distinguish binary OPUS INFO from SV DX INFO.
                fields = base_meta.get("info_fields", []) if isinstance(base_meta, dict) else []
                if isinstance(fields, list):
                    spec_meta["info_fields"] = [
                        {"code": str(item.get("code", "")),
                         "label": str(item.get("label", "")),
                         "value": str(item.get("value", ""))}
                        for item in fields if isinstance(item, dict)
                        and (item.get("label") or item.get("value"))
                    ][:99]
        except (ValueError, UnicodeError, TypeError, KeyError, zlib.error):
            # Optional private metadata must never block the spectrum itself.
            pass

    # Compatibility fallback for SV files where only the readable INFO LDRs
    # survive. Their ASCII form is lossy; the compressed payload takes priority.
    if "info_fields" not in spec_meta:
        recovered = []
        for key, value in headers.items():
            match = re.fullmatch(r"\$SV_INFO_(I\d{2})", key)
            if not match:
                continue
            label, separator, field_value = value.partition(": ")
            recovered.append({"code": match.group(1),
                              "label": label if separator else match.group(1),
                              "value": field_value if separator else value})
        if recovered:
            spec_meta["info_fields"] = recovered

    return Spectrum(x=x, y=y, title=title, xunit=xunit,
                    yunit=yunit, meta=spec_meta, path=path)


# --- Portable JCAMP-DX writer (one active spectrum, not the displayed zoom) ---

def _jcamp_ascii(value: Any) -> str:
    """ASCII compatibility for conventional JCAMP header values.

    The lossless original Unicode metadata is also stored in a private
    UTF-8/Base64 record, so no information is discarded from the export.
    """
    value = str(value if value is not None else "")
    value = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.encode("ascii", "replace").decode("ascii")
    # JCAMP interprets '$$' as the start of a comment, even in text fields.
    return value.replace("$$", "$ $")


def _jcamp_number(value: Any) -> str:
    """17 significant digits round-trip binary64 without avoidable truncation.

    In scientific notation, we use a capital letter E in accordance with the
    official JCAMP-DX recommendation.
    """
    return format(float(value), ".17g").replace("e", "E")


def _jcamp_source_format(path: str) -> str:
    if is_opus_like(path):
        return "OPUS"
    if is_jcamp_like(path):
        return "JCAMP-DX"
    if is_dpt_like(path):
        return "DPT"
    return "UNKNOWN"


def _jcamp_public_units(spec: Spectrum) -> tuple:
    xunit = str(spec.xunit or "1/CM").strip()
    if ("cm" in xunit.lower() and ("-1" in xunit or "⁻¹" in xunit or "1/" in xunit.lower())) \
            or xunit.upper() in {"1/CM", "CM-1", "CM^-1"}:
        xunit = "1/CM"
    yunit = str(spec.yunit or "ARBITRARY UNITS").strip()
    canonical = {
        "absorbance": "ABSORBANCE",
        "transmittance": "TRANSMITTANCE",
        "reflectance": "REFLECTANCE",
        "kubelka–munk": "KUBELKA-MUNK",
        "kubelka-munk": "KUBELKA-MUNK",
    }
    yunit = canonical.get(yunit.casefold(), yunit)
    return _jcamp_ascii(xunit).upper(), _jcamp_ascii(yunit).upper()


def _jcamp_metadata_payload(spec: Spectrum) -> Dict[str, Any]:
    meta = spec.meta or {}
    if isinstance(meta.get("sv_original_metadata"), dict):
        # Existing SpectraViewer DX: reuse the upstream payload rather than
        # recursively nesting a copy of it after each re-export.
        return dict(meta["sv_original_metadata"])

    public_meta = {}
    for key, val in meta.items():
        if key in {"series_y", "series_store_indices", "sv_original_metadata"}:
            continue
        if isinstance(val, (str, int, float, bool, list, dict, type(None))):
            public_meta[key] = val
        elif isinstance(val, (np.integer, np.floating)):
            public_meta[key] = val.item()
        else:
            public_meta[key] = str(val)

    if "series_y" in meta:
        index = int(meta.get("series_index", 0))
        store = meta.get("series_store_indices", []) or []
        public_meta["series_stored_index"] = (
            int(store[index]) if index < len(store) else index + 1
        )

    return {
        "original_source_filename": os.path.basename(spec.path or ""),
        "original_source_format": _jcamp_source_format(spec.path),
        "original_title": spec.title,
        "original_xunits": spec.xunit,
        "original_yunits": spec.yunit,
        "spectrum_metadata": public_meta,
    }


def _jcamp_uniform_x(x: np.ndarray) -> bool:
    """Use XYDATA only if reconstructed X values match original to high precision."""
    if x.size < 2:
        return False
    step = (float(x[-1]) - float(x[0])) / (x.size - 1)
    if not np.isfinite(step) or step == 0:
        return False
    # Differences are judged against the sample spacing, not X's large offset.
    rebuilt = float(x[0]) + np.arange(x.size, dtype=float) * step
    tolerance = max(abs(step) * 1e-10, 1e-11)
    return bool(np.max(np.abs(x - rebuilt)) <= tolerance)


def _jcamp_append_ldr(lines: List[str], key: str, value: Any):
    """Write a plain-text LDR with short, ASCII continuation lines."""
    prefix = f"##{key}="
    words = _jcamp_ascii(value).split()
    line = prefix
    for word in words:
        proposed = (line + (" " if line != prefix else "") + word)
        if len(proposed) > 78 and line != prefix:
            lines.append(line)
            line = word
        else:
            line = proposed
    lines.append(line)


def create_jcamp_dx(spec: Spectrum) -> str:
    """Export a single 1D spectrum to ASCII JCAMP-DX with AFFN data tables.

    X and Y are the original numeric arrays of the active spectrum; view zoom,
    X-axis inversion and color are not involved. No interpolation is performed.
    """
    x = np.asarray(spec.x, dtype=float).ravel()
    y = np.asarray(spec.y, dtype=float).ravel()
    if len(x) != len(y) or len(x) < 2:
        raise ValueError(UI_TEXT["jcamp_export_xy_required"])
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError(UI_TEXT["jcamp_export_nonfinite"])

    uniform = _jcamp_uniform_x(x)
    table = "XYDATA" if uniform else "XYPOINTS"
    xunit, yunit = _jcamp_public_units(spec)
    source_headers = (spec.meta or {}).get("jcamp_headers", {})

    lines: List[str] = []
    # Some SpectraGryph versions misinterpret continuation lines in TITLE.
    # The complete Unicode original is preserved in the private metadata.
    lines.append("##TITLE=" + _jcamp_ascii(spec.title))
    lines.append("##JCAMP-DX=5.01")
    lines.append("##DATA TYPE=INFRARED SPECTRUM")
    # Deliberately omit DATA CLASS: control V1 showed that even adding this
    # optional header to a known-working OPUS DX breaks import in OPUS 8.2.
    # The actual table descriptor (XYDATA or XYPOINTS) remains unambiguous.
    # Re-emit common standardized metadata from source JCAMP without
    # inheriting obsolete data offsets, compression or spectral parameters.
    transferable = (
        "ORIGIN", "OWNER", "DATE", "TIME", "LONGDATE", "STATE",
        "SAMPLE DESCRIPTION", "SAMPLING PROCEDURE", "RESOLUTION",
        "SPECTROMETER DATA SYSTEM", "INSTRUMENTAL PARAMETERS",
        "CAS NAME", "IUPAC NAME", "MOLFORM",
    )
    if isinstance(source_headers, dict):
        for key in transferable:
            if source_headers.get(key):
                _jcamp_append_ldr(lines, key, source_headers[key])
    if (not (isinstance(source_headers, dict) and source_headers.get("SAMPLE DESCRIPTION"))
            and spec.meta and spec.meta.get("sample_name")):
        _jcamp_append_ldr(lines, "SAMPLE DESCRIPTION", spec.meta["sample_name"])

    lines.append(f"##XUNITS={xunit}")
    lines.append(f"##YUNITS={yunit}")
    lines.append("##XFACTOR=1")
    lines.append("##YFACTOR=1")
    lines.append(f"##FIRSTX={_jcamp_number(x[0])}")
    lines.append(f"##LASTX={_jcamp_number(x[-1])}")
    lines.append(f"##FIRSTY={_jcamp_number(y[0])}")
    lines.append(f"##MINX={_jcamp_number(np.min(x))}")
    lines.append(f"##MAXX={_jcamp_number(np.max(x))}")
    lines.append(f"##MINY={_jcamp_number(np.min(y))}")
    lines.append(f"##MAXY={_jcamp_number(np.max(y))}")
    lines.append(f"##NPOINTS={len(x)}")
    if uniform:
        step = (float(x[-1]) - float(x[0])) / (len(x) - 1)
        lines.append(f"##DELTAX={_jcamp_number(step)}")

    lines.append(f"##$SV_EXPORTER={APP_NAME} {VERSION_NUMBER}")
    lines.append("##$SV_EXPORT_TIME_UTC=" + datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _jcamp_append_ldr(lines, "$SV_SOURCE_FORMAT", _jcamp_source_format(spec.path))
    _jcamp_append_ldr(lines, "$SV_SOURCE_FILENAME", os.path.basename(spec.path or ""))
    if spec.meta:
        for key, label in (("sample_name", "$SV_SAMPLE_NAME"),
                           ("sample_form", "$SV_SAMPLE_FORM")):
            if spec.meta.get(key):
                _jcamp_append_ldr(lines, label, spec.meta[key])
        for entry in spec.meta.get("info_fields", []) or []:
            code = str(entry.get("code", ""))
            if re.fullmatch(r"I\d{2}", code) and (entry.get("label") or entry.get("value")):
                _jcamp_append_ldr(
                    lines, "$SV_INFO_" + code,
                    f"{entry.get('label', '')}: {entry.get('value', '')}",
                )

    payload = _jcamp_metadata_payload(spec)
    json_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                            allow_nan=False).encode("utf-8")
    # Lossless zlib compression keeps the full Unicode metadata but reduces
    # the length and number of continuation lines seen by older DX importers.
    # The key explicitly identifies the new encoding; the reader above also
    # understands the old uncompressed UTF8/Base64 format.
    encoded = base64.b64encode(zlib.compress(json_bytes, level=9)).decode("ascii")
    lines.append("##$SV_METADATA_ZLIB_BASE64=")
    lines.extend(encoded[i:i + 72] for i in range(0, len(encoded), 72))

    if uniform:
        lines.append("##XYDATA=(X++(Y..Y))")
        # Each row begins with its real X checkpoint and continues with
        # corresponding Y values. All values are plain AFFN with spaces.
        idx = 0
        while idx < x.size:
            words = [_jcamp_number(x[idx])]
            start = idx
            while idx < x.size:
                value = _jcamp_number(y[idx])
                if idx > start and sum(map(len, words)) + len(words) + len(value) > 78:
                    break
                words.append(value)
                idx += 1
            lines.append(" ".join(words))
    else:
        lines.append("##XYPOINTS=(XY..XY)")
        # Explicit pairs ensure nonuniform X arrays are not interpolated.
        line = ""
        for xx, yy in zip(x, y):
            pair = f"{_jcamp_number(xx)},{_jcamp_number(yy)}"
            if line and len(line) + 1 + len(pair) > 78:
                lines.append(line)
                line = pair
            else:
                line = (line + " " + pair) if line else pair
        if line:
            lines.append(line)
    lines.append("##END=")
    return "\n".join(lines) + "\n"


def save_jcamp_dx_file(spec: Spectrum, destination: str):
    """Save atomically, rejecting any attempt to overwrite the source file."""
    source = os.path.abspath(spec.path) if spec.path else ""
    destination = os.path.abspath(destination)
    if source and (os.path.normcase(source) == os.path.normcase(destination)
                   or (os.path.exists(destination) and os.path.samefile(source, destination))):
        raise ValueError(UI_TEXT["save_jcamp_same_source"])

    content = create_jcamp_dx(spec)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", newline="\r\n", delete=False,
            dir=os.path.dirname(destination), prefix=".spectraviewer_", suffix=".tmp",
        ) as f:
            temporary_path = f.name
            f.write(content)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path and os.path.isfile(temporary_path):
            os.unlink(temporary_path)


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

# A small decorator keeps slow GUI operations clearly marked while preserving
# their synchronous return values and error handling.
def busy_operation(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.busy_ui():
            return method(self, *args, **kwargs)
    return wrapper

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
            print(UI_TEXT["console_icon_not_set"].format(error=e))

        self.settings_path = settings_file_path()
        self.settings = self.load_settings()

        self.folder_var = tk.StringVar(value=self.get_setting("open", "last_path", ""))
        # The editable Path field is not necessarily the accepted file-list context.
        # Preserve the last accepted/recoverable path separately for INI persistence.
        self._committed_path = self.folder_var.get().strip()
        self._active_folder_path = ""
        self._excluded_large_opus_count = 0
        self._busy_depth = 0
        self.recursive_var = tk.BooleanVar(value=self.get_setting_bool("open", "recursive", True))
        self.single_file_var = tk.BooleanVar(value=self.get_setting_bool("open", "single_file", False))
        self._recursive_before_single = bool(self.recursive_var.get())
        self.invert_x_var = tk.BooleanVar(value=self.get_setting_bool("view", "invert_x", False))
        self.crosshair_var = tk.BooleanVar(value=self.get_setting_bool("view", "crosshair", True))
        # Optional, unlabeled axis subdivisions. No extra UI controls needed.
        self.x_minor_ticks = self.get_setting_bool("view", "x_minor_ticks", True)
        self.y_minor_ticks = self.get_setting_bool("view", "y_minor_ticks", True)
        self.status_var = tk.StringVar(value=UI_TEXT["initial_status"])
        self.series_counter_var = tk.StringVar(value="1/1")
        self.line_color = self.get_setting("view", "line_color", DEFAULT_LINE_COLOR) or DEFAULT_LINE_COLOR
        raw_line_width = self.get_setting("view", "line_width", str(DEFAULT_LINE_WIDTH))
        self.line_width, self._line_width_valid = parse_line_width(raw_line_width)

        raw_warn_file_count = self.get_setting(
            "advanced", "warn_file_count", str(DEFAULT_WARN_FILE_COUNT)
        )
        self.warn_file_count, self._warn_file_count_valid = parse_warn_file_count(
            raw_warn_file_count
        )

        raw_large_opus_warn_mb = self.get_setting(
            "advanced", "large_opus_warn_mb", str(DEFAULT_LARGE_OPUS_WARN_MB)
        )
        self.large_opus_warn_mb, self._large_opus_warn_mb_valid = parse_large_opus_warn_mb(
            raw_large_opus_warn_mb
        )
        self.large_opus_warn_bytes = int(float(self.large_opus_warn_mb) * 1024 * 1024)

        if not self._warn_file_count_valid:
            print(UI_TEXT["console_invalid_warn_file_count"].format(default=DEFAULT_WARN_FILE_COUNT))
        if not self._large_opus_warn_mb_valid:
            print(UI_TEXT["console_invalid_large_opus_warn_mb"].format(default=DEFAULT_LARGE_OPUS_WARN_MB))

        self.metadata_encoding = normalize_metadata_encoding(
            self.get_setting("metadata", "encoding", DEFAULT_METADATA_ENCODING)
        )
        self.encoding_var = tk.StringVar(value=ENCODING_VALUE_TO_LABEL[self.metadata_encoding])
        self.files: List[str] = []
        self.idx: int = -1
        self.current: Optional[Spectrum] = None
        self.info_win = None
        self.info_text = None

        self._build_ui()
        self._bind_keys()
        self._setup_dnd()  # Drag & Drop init (if available)
        if not self._line_width_valid:
            self.after(0, self.show_invalid_line_width_warning)
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


    def show_invalid_line_width_warning(self):
        messagebox.showwarning(
            UI_TEXT["invalid_line_width_title"],
            UI_TEXT["invalid_line_width_message"],
            parent=self,
        )

    @contextmanager
    def busy_ui(self):
        """Show a wait cursor and visible status before a synchronous operation.

        The explicit update() is essential: update_idletasks() alone does not
        activate Tk's busy overlay reliably on Windows. This does NOT make
        the application responsive during a long blocking file read.
        """
        first = self._busy_depth == 0
        self._busy_depth += 1
        busy_held = False
        fallback_cursor = None
        previous_status = None
        try:
            if first:
                previous_status = self.status_var.get()
                self.status_var.set(UI_TEXT["busy_status"])
                try:
                    self.tk.call("tk", "busy", "hold", self._w, "-cursor", "watch")
                    busy_held = True
                except tk.TclError:
                    # Fallback on Tcl/Tk builds lacking the busy subcommand.
                    fallback_cursor = str(self.cget("cursor"))
                    self.configure(cursor="watch")

                # Tk docs explicitly require update() after busy hold.
                # Do this once at the START, never inside the long-running work.
                self.update()
            yield
        finally:
            self._busy_depth -= 1
            if first:
                try:
                    if busy_held:
                        self.tk.call("tk", "busy", "forget", self._w)
                    if fallback_cursor is not None:
                        self.configure(cursor=fallback_cursor)
                finally:
                    # Keep any status written by the completed operation.
                    if self.status_var.get() == UI_TEXT["busy_status"]:
                        self.status_var.set(previous_status or "")
                    self.update_idletasks()

    @busy_operation
    def scan_folder_busy(self, folder: str, recursive: bool) -> List[str]:
        return scan_folder(folder, recursive)

    # --- Settings / INI memory ---
    def load_settings(self) -> configparser.ConfigParser:
        cfg = configparser.ConfigParser()
        if os.path.isfile(settings_file_path()):
            try:
                cfg.read(settings_file_path(), encoding="utf-8")
            except Exception as e:
                print(UI_TEXT["console_settings_not_loaded"].format(error=e))
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
            "line_width": str(self.line_width),
            "crosshair": str(bool(self.crosshair_var.get())).lower(),
            "invert_x": str(bool(self.invert_x_var.get())).lower(),
            "x_minor_ticks": str(bool(self.x_minor_ticks)).lower(),
            "y_minor_ticks": str(bool(self.y_minor_ticks)).lower(),
        }

        # Do not save an uncommitted Path-field edit or a cancelled folder choice.
        last_path = self._committed_path
        active_file = self.get_active_file_path() if hasattr(self, "current") else ""
        if bool(self.single_file_var.get()) and active_file and self.files:
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

        cfg["advanced"] = {
            "warn_file_count": str(self.warn_file_count),
            "large_opus_warn_mb": str(self.large_opus_warn_mb),
        }

        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception as e:
            print(UI_TEXT["console_settings_not_saved"].format(error=e))

    def on_close(self):
        self.save_settings()
        self.destroy()

    def restore_last_path_on_startup(self):
        """Restore the saved path, applying OPUS size choices to the restored list.

        Do not bypass the size warning simply because loading is automatic.
        If cancelled, keep the saved path visible for a later manual attempt.
        """
        last_path = (self._committed_path or "").strip()
        if not last_path:
            self.status_var.set(UI_TEXT["initial_status"])
            return

        p = os.path.abspath(os.path.expanduser(last_path))
        if not os.path.exists(p):
            self.status_var.set(UI_TEXT["last_path_not_found_status"])
            return

        if os.path.isdir(p):
            if bool(self.single_file_var.get()):
                self.status_var.set(UI_TEXT["last_path_single_folder_status"])
                return
            folder, preferred = p, ""
        elif os.path.isfile(p):
            if not is_supported_spectrum(p):
                self.status_var.set(UI_TEXT["last_path_unsupported_status"])
                return
            if bool(self.single_file_var.get()):
                if self.open_single_file(p):
                    self.status_var.set(UI_TEXT["last_path_restored_status"].format(path=p))
                elif self.current is None and not self.files:
                    self.status_var.set(UI_TEXT["startup_large_opus_cancelled"])
                return
            folder, preferred = os.path.dirname(p), p
        else:
            self.status_var.set(UI_TEXT["last_path_not_found_status"])
            return

        files = self.scan_folder_busy(folder, recursive=bool(self.recursive_var.get()))
        if not files:
            self.status_var.set(UI_TEXT["last_path_no_spectrum_status"])
            return

        # Preserve the previous non-intrusive startup file-count policy.
        # Large OPUS choices are different: they must be shown on startup.
        if len(files) > self.warn_file_count:
            self.status_var.set(UI_TEXT["last_path_too_many_status"].format(count=len(files)))
            return

        selection = self.select_large_opus_files(
            files, UI_TEXT["folder_context_origin"], preferred_single_path=preferred,
        )
        if selection is None:
            self.status_var.set(UI_TEXT["startup_large_opus_cancelled"])
            return

        selected, excluded = selection
        self._accept_file_list(selected, folder, preferred, excluded)
        if self.current is not None:
            if excluded:
                self._show_filtered_status()
            else:
                self.status_var.set(UI_TEXT["last_path_restored_status"].format(path=p))

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
        for header_field in getattr(self, "header_fields", []):
            reg(header_field)
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

        # Opening methods update Path only after an accepted change.
        # An unsuccessful drop must not replace the displayed active folder.

        return "break"

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, sticky="ew")

        ttk.Label(top, text=UI_TEXT["path_label"]).pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(top, textvariable=self.folder_var, width=65)
        self.path_entry.pack(side=tk.LEFT, padx=(6, 6), fill=tk.X, expand=True)
        self.path_entry.bind("<Return>", self.on_path_enter)
        self.path_entry.bind("<Control-c>", self._copy_widget_selection_to_clipboard)
        self.path_entry.bind("<Control-C>", self._copy_widget_selection_to_clipboard)

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
        self.save_btn = ttk.Button(nav, text=UI_TEXT["export_image_button"], command=self.save_current_plot)
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
        self.apply_minor_ticks()
        # An empty session is not a 0..1 spectrum: keep the axes hidden until
        # a file is successfully loaded. The canvas keeps its existing layout.
        self.ax.set_visible(False)

        # Copyable header (filename / sample name / sample form)
        # mid grid: 3 rows (header, canvas, toolbar); the canvas expands.
        mid.grid_rowconfigure(1, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        # Three independent, copyable read-only header fields.
        # Keeping them separate makes filename / SNM / SFM individually reachable
        # in the TAB order while preserving the previous flat, three-line appearance.
        self.header_frame = ttk.Frame(mid)
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.header_fields = []
        for row in range(3):
            field = tk.Text(
                self.header_frame,
                height=1,
                wrap="none",
                borderwidth=0,
                takefocus=1,
                font=("Segoe UI", 12),
                padx=8,
                pady=0,
                highlightthickness=0,
            )
            field.grid(row=row, column=0, sticky="ew")
            field.configure(state="disabled")
            field.bind("<FocusIn>", self._on_header_focus_in)
            field.bind("<FocusOut>", self._on_header_focus_out)
            field.bind("<Tab>", self._focus_next_widget)
            field.bind("<Shift-Tab>", self._focus_prev_widget)
            #field.bind("<ISO_Left_Tab>", self._focus_prev_widget) # It is not compatible with Portable 3.11.8, so we’ll have to replace it everywhere
            try:
                field.bind("<ISO_Left_Tab>", self._focus_prev_widget)
            except tk.TclError:
                pass
            field.bind("<Control-c>", self._copy_widget_selection_to_clipboard)
            field.bind("<Control-C>", self._copy_widget_selection_to_clipboard)

            # Header fields are read-only/copyable, not text editors.
            # Plain navigation keys therefore keep controlling SpectraViewer.
            # Widget-level bindings run before the Text class bindings, so
            # Home/End/arrows do not first move the invisible insertion cursor
            # or destroy the visible full-field selection.
            field.bind("<Left>", self._on_left)
            field.bind("<Right>", self._on_right)
            field.bind("<Up>", self._on_up)
            field.bind("<Down>", self._on_down)
            field.bind("<Prior>", self._on_page_up)       # Page Up
            field.bind("<Next>", self._on_page_down)      # Page Down
            field.bind("<Home>", self._on_home)
            field.bind("<End>", self._on_end)

            self.header_fields.append(field)

        self.canvas = FigureCanvasTkAgg(fig, master=mid)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        # Bottom row: Matplotlib toolbar on the left, INFO helper button on the right.
        toolbar_row = ttk.Frame(mid)
        toolbar_row.grid(row=2, column=0, sticky="ew", pady=(2, 0))

        toolbar = ToolbarNoSave(self.canvas, toolbar_row)
        toolbar.update()
        toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.info_btn = ttk.Button(
            toolbar_row,
            text=UI_TEXT["info_button"],
            command=self.show_info_window,
            width=6,
        )
        self.info_btn.pack(side=tk.RIGHT, padx=(6, 4), pady=(0, 1))
        self.info_btn.state(["disabled"])

        # JCAMP export lives in this lower row to preserve the minimum window
        # width (the navigation/metadata row above is already crowded).
        self.save_jcamp_btn = ttk.Button(
            toolbar_row, text=UI_TEXT["save_jcamp_button"],
            command=self.save_current_jcamp,
        )
        self.save_jcamp_btn.pack(side=tk.RIGHT, padx=(4, 4), pady=(0, 1))

        # Compact DataSeries navigation. It is always visible so the toolbar
        # geometry remains stable; for ordinary single spectra the arrows are
        # disabled and the counter reads 1/1.
        self.series_next_btn = ttk.Button(
            toolbar_row,
            text="▶",
            command=self.series_next,
            width=3,
        )
        self.series_next_btn.pack(side=tk.RIGHT, padx=(2, 0), pady=(0, 1))

        self.series_counter_lbl = ttk.Label(
            toolbar_row,
            textvariable=self.series_counter_var,
            width=7,
            anchor="center",
        )
        self.series_counter_lbl.pack(side=tk.RIGHT, padx=(2, 2))

        self.series_prev_btn = ttk.Button(
            toolbar_row,
            text="◀",
            command=self.series_prev,
            width=3,
        )
        self.series_prev_btn.pack(side=tk.RIGHT, padx=(6, 0), pady=(0, 1))

        self.series_prev_btn.state(["disabled"])
        self.series_next_btn.state(["disabled"])

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
        self.bind_all("<Up>", self._on_up)
        self.bind_all("<Down>", self._on_down)
        self.bind("<Prior>", self._on_page_up)                       # PageUp
        self.bind("<Next>", self._on_page_down)                      # PageDown
        self.bind("<Home>", self._on_home)
        self.bind("<End>", self._on_end)
        self.bind_all("<Control-e>", self._on_ctrl_e)
        self.bind_all("<Control-E>", self._on_ctrl_e)
        self.bind_all("<Control-Shift-e>", self._on_ctrl_shift_e)
        self.bind_all("<Control-Shift-E>", self._on_ctrl_shift_e)
        self.bind_all("<Control-Shift-o>", self._on_ctrl_shift_o)   # mappa
        self.bind_all("<Control-Shift-O>", self._on_ctrl_shift_o)
        self.bind_all("<Control-o>", self._on_ctrl_o)               # file
        self.bind_all("<Control-O>", self._on_ctrl_o)
        self.bind_all("<Control-Shift-c>", self._on_ctrl_shift_c)   # colour
        self.bind_all("<Control-Shift-C>", self._on_ctrl_shift_c)
        self.bind_all("<Control-i>", self._on_ctrl_i)     # info block viewer
        self.bind_all("<Control-I>", self._on_ctrl_i)
        self.bind_all("<F1>", self._on_F1)                          # about

    def _navigation_key_is_for_text_widget(self, event=None) -> bool:
        """
        Return True when a navigation key belongs to a focused text-entry widget.

        Global SpectraViewer navigation must not steal Left/Right/Up/Down,
        Page Up/Page Down or Home/End while the user is editing/navigating text
        (e.g. Path field, INFO text, metadata encoding combobox).
        """
        widget = getattr(event, "widget", None)
        if widget is None:
            return False

        # The three read-only/copyable header Text widgets are special:
        # when they have focus, navigation keys must still control SpectraViewer.
        if widget in getattr(self, "header_fields", []):
            return False

        try:
            widget_class = widget.winfo_class()
        except Exception:
            return False

        return widget_class in {
            "Entry",
            "TEntry",
            "Text",
            "TCombobox",
            "Spinbox",
            "TSpinbox",
        }

    def _on_page_up(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        self.jump(-25)
        return "break"

    def _on_page_down(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        self.jump(+25)
        return "break"

    def _on_home(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        self.first()
        return "break"

    def _on_end(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        self.last()
        return "break"

    def _on_left(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        if not getattr(self, "prev_btn", None):
            return
        if "disabled" in self.prev_btn.state():
            return "break"
        self.prev_btn.state(['pressed'])
        self.prev_btn.after(150, lambda: self.prev_btn.state(['!pressed']))
        self.prev_btn.invoke()
        return "break"

    def _on_right(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        if not getattr(self, "next_btn", None):
            return
        if "disabled" in self.next_btn.state():
            return "break"
        self.next_btn.state(['pressed'])
        self.next_btn.after(150, lambda: self.next_btn.state(['!pressed']))
        self.next_btn.invoke()
        return "break"

    def _on_up(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        if not getattr(self, "series_prev_btn", None):
            return
        if "disabled" in self.series_prev_btn.state():
            return "break"
        self.series_prev_btn.state(["pressed"])
        self.series_prev_btn.after(
            150, lambda: self.series_prev_btn.state(["!pressed"])
        )
        self.series_prev_btn.invoke()
        return "break"

    def _on_down(self, event=None):
        if self._navigation_key_is_for_text_widget(event):
            return
        if not getattr(self, "series_next_btn", None):
            return
        if "disabled" in self.series_next_btn.state():
            return "break"
        self.series_next_btn.state(["pressed"])
        self.series_next_btn.after(
            150, lambda: self.series_next_btn.state(["!pressed"])
        )
        self.series_next_btn.invoke()
        return "break"

    def _on_ctrl_e(self, event=None):
        if event is not None and (event.state & 0x0001):
            return
        btn = getattr(self, "save_jcamp_btn", None)
        if btn is None:
            return
        btn.state(["pressed"])
        btn.after(150, lambda: btn.state(["!pressed"]))
        btn.invoke()
        return "break"

    def _on_ctrl_shift_e(self, event=None):
        btn = getattr(self, "save_btn", None)
        if btn is None:
            return
        btn.state(["pressed"])
        btn.after(150, lambda: btn.state(["!pressed"]))
        btn.invoke()
        return "break"

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

    def _on_ctrl_i(self, event=None):
        if not getattr(self, "info_btn", None):
            return
        self.info_btn.state(['pressed'])
        self.info_btn.after(150, lambda: self.info_btn.state(['!pressed']))
        self.info_btn.invoke()
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

        # open_folder commits the new Path only after warnings are accepted.
        self.open_folder(folder, recursive=self.recursive_var.get())

    def confirm_file_count(self, count: int, origin: str = UI_TEXT["selected_list_origin"]) -> bool:
        if count > MAX_FILE_COUNT:
            messagebox.showerror(
                UI_TEXT["too_many_files_title"],
                UI_TEXT["too_many_files_error"].format(origin=origin, count=count, max_count=MAX_FILE_COUNT)
            )
            return False

        if count > self.warn_file_count:
            return messagebox.askyesno(
                UI_TEXT["too_many_files_confirm_title"],
                UI_TEXT["too_many_files_confirm"].format(origin=origin, count=count)
            )

        return True

    def _large_opus_path_key(self, path: str) -> str:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(path))))

    def get_large_opus_files(self, paths):
        """Find every OPUS file over the INI threshold, including >100 MB files."""
        large = []
        seen = set()
        for path in paths:
            p = os.path.abspath(os.path.expanduser(str(path)))
            key = self._large_opus_path_key(p)
            if key in seen:
                continue
            seen.add(key)
            if is_large_opus_file(p, self.large_opus_warn_bytes):
                large.append(p)
        return large

    def _ask_large_opus_action(self, origin, large_files, total_count, small_count,
                               preferred_single_path=""):
        """Three-way modal choice: complete list, filtered list, or cancellation.

        No choice is implied by closing the window or pressing Escape.
        """
        hard_count = 0
        for path in large_files:
            try:
                if os.path.getsize(path) > MAX_OPUS_FILE_BYTES:
                    hard_count += 1
            except OSError:
                pass

        dialog = tk.Toplevel(self)
        dialog.title(UI_TEXT["large_opus_title"] if total_count == 1
                     else UI_TEXT["large_opus_list_title"])
        dialog.transient(self)
        dialog.resizable(False, False)
        outer = ttk.Frame(dialog, padding=16)
        outer.pack(fill="both", expand=True)

        def paragraph(value):
            ttk.Label(outer, text=value, wraplength=520,
                      justify="left").pack(fill="x", pady=(0, 12))

        paragraph(UI_TEXT["large_opus_choice_intro"].format(
            origin=origin, count=len(large_files), threshold_mb=self.large_opus_warn_mb))
        if preferred_single_path and len(large_files) == 1 and (
            self._large_opus_path_key(large_files[0]) ==
            self._large_opus_path_key(preferred_single_path)
        ):
            try:
                size_mb = os.path.getsize(large_files[0]) / (1024 * 1024)
            except OSError:
                size_mb = float(self.large_opus_warn_mb)
            paragraph(UI_TEXT["large_opus_choice_single"].format(
                filename=os.path.basename(large_files[0]), size_mb=size_mb))
        if hard_count:
            paragraph(UI_TEXT["large_opus_choice_hard"].format(
                count=hard_count, max_mb=MAX_OPUS_FILE_MB))
        paragraph(UI_TEXT["large_opus_choice_small_count"].format(
            kept=small_count, total=total_count) if small_count else
            UI_TEXT["large_opus_choice_no_small"])

        result = {"choice": "cancel"}
        def choose(choice):
            result["choice"] = choice
            dialog.destroy()

        full_button = ttk.Button(
            outer, text=UI_TEXT["large_opus_choice_all_button"],
            command=lambda: choose("all"))
        full_button.pack(fill="x", pady=(0, 6))
        filtered_button = ttk.Button(
            outer, text=UI_TEXT["large_opus_choice_small_button"],
            command=lambda: choose("small"))
        filtered_button.pack(fill="x", pady=(0, 6))
        if small_count == 0:
            filtered_button.state(["disabled"])
        ttk.Button(outer, text=UI_TEXT["large_opus_choice_cancel_button"],
                   command=lambda: choose("cancel")).pack(fill="x")

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        dialog.bind("<Escape>", lambda event: choose("cancel"))

        # Enter activates the currently focused button, just like Space.
        def on_enter(event):
            if isinstance(event.widget, ttk.Button):
                event.widget.invoke()
                return "break"

        dialog.bind("<Return>", on_enter)
        dialog.bind("<KP_Enter>", on_enter)  # Numeric keypad Enter

        # Native Tk placement: center over the SpectraViewer main window,
        # keeping the dialog within the visible desktop when possible.
        dialog.tk.call("tk::PlaceWindow", dialog._w, "widget", self._w)
        dialog.grab_set()
        full_button.focus_set()
        self.wait_window(dialog)
        return result["choice"]

    def select_large_opus_files(self, paths, origin, preferred_single_path=""):
        """Return (chosen_paths, excluded_count), or None when cancelled.

        Filter on the configured INI warning threshold, not the hard 100 MB limit.
        Every NEW list selection asks again, but file-by-file navigation does not.
        """
        paths = list(paths)
        large = self.get_large_opus_files(paths)
        if not large:
            return paths, 0
        large_keys = {self._large_opus_path_key(p) for p in large}
        smaller = [p for p in paths if self._large_opus_path_key(p) not in large_keys]
        action = self._ask_large_opus_action(
            origin, large, len(paths), len(smaller), preferred_single_path)
        if action == "all":
            return paths, 0
        if action == "small" and smaller:
            return smaller, len(paths) - len(smaller)
        return None

    def _show_filtered_status(self):
        if self._excluded_large_opus_count:
            self.status_var.set(UI_TEXT["filtered_large_opus_status"].format(
                count=len(self.files), excluded=self._excluded_large_opus_count,
                threshold_mb=self.large_opus_warn_mb))

    def _accept_file_list(self, files, folder, preferred="", excluded=0,
                          persisted_path=None) -> bool:
        """Atomically commit a list, its Path display and its INI path.

        A failed read may show a file-specific error, but cannot roll back the
        already accepted list (e.g. an OPUS file above the hard 100 MB limit).
        """
        files = list(files)
        if not files:
            return False
        folder = os.path.abspath(os.path.expanduser(str(folder)))
        target = self._large_opus_path_key(preferred) if preferred else ""
        new_idx = next((i for i, item in enumerate(files)
                        if self._large_opus_path_key(item) == target), 0)
        self.files = files
        self.idx = new_idx
        self._excluded_large_opus_count = excluded
        self._active_folder_path = folder
        self._committed_path = persisted_path if persisted_path is not None else folder
        self.folder_var.set(folder)
        self.update_counter()
        loaded = self.load_current()
        if excluded and loaded:
            self._show_filtered_status()
        return True

    def choose_file(self):
        # Windows/Tk file dialog wildcards cannot precisely express the
        # "numeric extension only" pattern, so the dialog is intentionally broad,
        # and the actual validation is done in Python.
        filetypes = [
            (UI_TEXT["all_supported_files"], "*.dx;*.jdx;*.dpt;*.0*;*.1*;*.2*;*.3*;*.4*;*.5*;*.6*;*.7*;*.8*;*.9*"),
            (UI_TEXT["jcamp_ascii_filter"], "*.dx;*.jdx"),
            (UI_TEXT["dpt_ascii_filter"], "*.dpt"),
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
        inaccessible_paths = [p for p in invalid_paths if spectrum_file_access_error(p)]
        if inaccessible_paths:
            self._warn_inaccessible_spectrum(inaccessible_paths[0])
            return

        if not valid_paths:
            locked = next((p for p in paths if spectrum_file_access_error(p)), None)
            if locked and self._warn_inaccessible_spectrum(locked):
                return
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

        # A single file opens its folder context; that context has its own choice.
        if len(valid_paths) > 1:
            selection = self.select_large_opus_files(
                valid_paths, UI_TEXT["selected_list_origin"])
            if selection is None:
                return
            selected_paths, excluded = selection

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
            self.open_file_with_context(path, recursive=self.recursive_var.get())
        else:
            selected_paths = sorted([Path(p) for p in selected_paths])
            self._accept_file_list(
                selected_paths, os.path.dirname(str(selected_paths[0])), excluded=excluded)

    def load_custom_list(self, file_list):
        """Compatibility helper for externally prepared lists, using the same rules."""
        files = sorted(Path(p) for p in file_list if Path(p).is_file()
                       and is_supported_spectrum(str(p)))
        if not files:
            messagebox.showwarning(UI_TEXT["warning_title"], UI_TEXT["no_loadable_file"])
            return False
        if not self.confirm_file_count(len(files)):
            return False
        selection = self.select_large_opus_files(files, UI_TEXT["selected_list_origin"])
        if selection is None:
            return False
        selected, excluded = selection
        return self._accept_file_list(selected, os.path.dirname(str(selected[0])),
                                      excluded=excluded)

    def on_path_enter(self, _evt=None):
        """
        Open a manually entered path.

        On success, move focus out of the editable Path field so navigation
        shortcuts work immediately:
          folder -> Folder… button
          file   -> File… button

        On invalid/unsupported/cancelled input, keep focus in Path because the
        user will normally want to edit it.
        """
        result = self.open_path(self.folder_var.get().strip())

        if result == "folder":
            self.fldr_btn.focus_set()
        elif result == "file":
            self.file_btn.focus_set()
        else:
            path_entry = getattr(self, "path_entry", None)
            if path_entry is not None:
                path_entry.focus_set()

        return "break"

    def _warn_inaccessible_spectrum(self, path: str) -> bool:
        issue = spectrum_file_access_error(path)
        if issue is None:
            return False
        messagebox.showwarning(
            UI_TEXT["file_access_title"],
            UI_TEXT["file_locked_message"].format(path=path, reason=str(issue)),
            parent=self,
        )
        return True

    def open_path(self, path: str):
        if not path:
            return None

        p = os.path.abspath(os.path.expanduser(path))

        # Invalid path.
        if not os.path.exists(p):
            if self._warn_inaccessible_spectrum(p):
                return None
            messagebox.showwarning(UI_TEXT["invalid_path_title"], UI_TEXT["invalid_path_message"])
            return None

        # Folder.
        if os.path.isdir(p):
            if bool(self.single_file_var.get()):
                messagebox.showwarning(
                    UI_TEXT["single_file_title"],
                    UI_TEXT["single_file_path_must_be_file"]
                )
                return None

            if self.open_folder(p, recursive=self.recursive_var.get()):
                return "folder"
            return None

        # File with a valid format.
        if os.path.isfile(p):
            if not is_supported_spectrum(p):
                if self._warn_inaccessible_spectrum(p):
                    return None
                messagebox.showwarning(UI_TEXT["unsupported_format_title"], UI_TEXT["unsupported_path_message"])
                return None

            if bool(self.single_file_var.get()):
                ok = self.open_single_file(p)
            else:
                ok = self.open_file_with_context(p, recursive=self.recursive_var.get())

            return "file" if ok else None

        return None

    def get_active_file_path(self) -> str:
        """Return the currently displayed/selected spectrum path, if available."""
        if self.current is not None and getattr(self.current, "path", ""):
            return os.path.abspath(os.path.expanduser(str(self.current.path)))
        if self.files and 0 <= self.idx < len(self.files):
            return os.path.abspath(os.path.expanduser(str(self.files[self.idx])))
        return ""

    def rebuild_context_from_current_file(self, recursive: bool) -> bool:
        """Rebuild the folder around the selected file without premature commits."""
        current_path = self.get_active_file_path()
        if not current_path or not os.path.isfile(current_path) or not is_supported_spectrum(current_path):
            self.update_counter()
            return False

        folder = os.path.dirname(current_path)
        files = self.scan_folder_busy(folder, recursive=recursive)
        if not files:
            messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_spectrum_at_path"])
            return False
        if not self.confirm_file_count(len(files), UI_TEXT["folder_context_origin"]):
            self.status_var.set(UI_TEXT["context_reload_cancelled"])
            return False
        selection = self.select_large_opus_files(
            files, UI_TEXT["folder_context_origin"], preferred_single_path=current_path)
        if selection is None:
            self.status_var.set(UI_TEXT["context_reload_cancelled"])
            return False
        selected, excluded = selection
        return self._accept_file_list(selected, folder, preferred=current_path,
                                      excluded=excluded)

    def on_single_file_toggle(self):
        if bool(self.single_file_var.get()):
            self._recursive_before_single = bool(self.recursive_var.get())
            self.recursive_chk.state(["disabled"])

            # Single file mode must not leave a multi-file list active.
            # If a spectrum is currently active, immediately reduce the list to that one file.
            active_path = self.get_active_file_path()
            if active_path:
                if not self.open_single_file(active_path):
                    # The requested mode change was cancelled/rejected.
                    self.single_file_var.set(False)
                    self.recursive_chk.state(["!disabled"])
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
                mode = (UI_TEXT["mode_recursive"] if restored_recursive
                        else UI_TEXT["mode_nonrecursive"])
                self.status_var.set(UI_TEXT["single_file_disabled_rebuilt_status"].format(mode=mode))
            else:
                # Cancellation must not leave the checkbutton inconsistent
                # with the still-active single-file list.
                if self.files:
                    self.single_file_var.set(True)
                    self.recursive_chk.state(["disabled"])
                    self.recursive_var.set(bool(self._recursive_before_single))
                self.status_var.set(UI_TEXT["single_file_disabled_restored_status"])

    def open_single_file(self, filepath: str) -> bool:
        filepath = os.path.abspath(os.path.expanduser(str(filepath)))
        if not os.path.isfile(filepath):
            if self._warn_inaccessible_spectrum(filepath):
                return False
            messagebox.showwarning(UI_TEXT["invalid_file_title"], UI_TEXT["single_file_invalid_path"])
            return False
        if not is_supported_spectrum(filepath):
            if self._warn_inaccessible_spectrum(filepath):
                return False
            messagebox.showwarning(UI_TEXT["unsupported_format_title"], UI_TEXT["unsupported_path_message"])
            return False

        selection = self.select_large_opus_files(
            [filepath], UI_TEXT["selected_list_origin"], preferred_single_path=filepath)
        if selection is None:
            return False
        selected, excluded = selection  # Filtering is disabled when it would leave no files.
        self._accept_file_list(selected, os.path.dirname(filepath), preferred=filepath,
                               excluded=excluded, persisted_path=filepath)
        if self.current is not None:
            self.status_var.set(UI_TEXT["single_file_title"] + f": {filepath}")
            return True
        return False

    def open_folder(self, folder: str, recursive: bool) -> bool:
        folder = os.path.abspath(folder)
        files = self.scan_folder_busy(folder, recursive=recursive)
        if not files:
            messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_spectrum_at_path"])
            return False
        if not self.confirm_file_count(len(files), UI_TEXT["opened_folder_origin"]):
            return False
        selection = self.select_large_opus_files(files, UI_TEXT["opened_folder_origin"])
        if selection is None:
            return False
        selected, excluded = selection
        return self._accept_file_list(selected, folder, excluded=excluded)

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
                items.extend(self.scan_folder_busy(ap, recursive=recursive))
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

        selection = self.select_large_opus_files(uniq, UI_TEXT["selected_list_origin"])
        if selection is None:
            return False
        selected, excluded = selection

        if invalid_paths:
            max_show = 8
            shown = [os.path.basename(p) for p in invalid_paths[:max_show]]
            more = len(invalid_paths) - len(shown)
            msg = UI_TEXT["dropped_items_skipped"].format(
                valid=len(selected),
                invalid=len(invalid_paths),
                shown="\n- ".join(shown),
            )
            if more > 0:
                msg += UI_TEXT["and_more"].format(more=more)
            messagebox.showwarning(UI_TEXT["some_files_skipped_title"], msg)

        self._accept_file_list(selected, os.path.dirname(str(selected[0])), excluded=excluded)
        if not excluded and self.current is not None:
            self.status_var.set(UI_TEXT["custom_list_loaded"].format(count=len(self.files)))
        return True

    def open_file_with_context(self, filepath: str, recursive: bool) -> bool:
        if bool(self.single_file_var.get()):
            return bool(self.open_single_file(filepath))

        filepath = os.path.abspath(filepath)
        folder = os.path.dirname(filepath)
        files = self.scan_folder_busy(folder, recursive=recursive)
        if not files:
            messagebox.showwarning(UI_TEXT["no_match_title"], UI_TEXT["no_spectrum_at_path"])
            return False
        if not self.confirm_file_count(len(files), UI_TEXT["folder_context_origin"]):
            return False
        selection = self.select_large_opus_files(
            files, UI_TEXT["folder_context_origin"], preferred_single_path=filepath)
        if selection is None:
            return False
        selected, excluded = selection
        # If the requested file was excluded, show the first retained spectrum.
        # Never sneak the requested large file back into a filtered list.
        return self._accept_file_list(selected, folder, preferred=filepath,
                                      excluded=excluded)

    def rescan(self):
        if bool(self.single_file_var.get()):
            self.recursive_var.set(bool(self._recursive_before_single))
            self.status_var.set(UI_TEXT["single_file_subfolders_disabled"])
            return

        # Rescan the accepted folder, never an uncommitted Path-field edit.
        folder = self._active_folder_path or self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self.recursive_var.set(not bool(self.recursive_var.get()))
            self.status_var.set(UI_TEXT["invalid_folder_status"])
            return

        requested_recursive = bool(self.recursive_var.get())
        new_files = self.scan_folder_busy(folder, requested_recursive)
        if not self.confirm_file_count(len(new_files), UI_TEXT["folder_context_origin_alt"]):
            self.recursive_var.set(not requested_recursive)
            self.status_var.set(UI_TEXT["loading_cancelled_previous_kept"])
            return
        selection = self.select_large_opus_files(new_files, UI_TEXT["folder_context_origin_alt"])
        if selection is None:
            self.recursive_var.set(not requested_recursive)
            self.status_var.set(UI_TEXT["loading_cancelled_large_opus"])
            return
        selected, excluded = selection
        if not selected:
            # An actual empty folder is allowed during a rescan.
            self.files = []
            self.idx = -1
            self.current = None
            self._excluded_large_opus_count = 0
            self._active_folder_path = os.path.abspath(folder)
            self._committed_path = os.path.abspath(folder)
            self.folder_var.set(folder)
            self.update_counter()
            self.clear_header()
            self.clear_plot()
            self.status_var.set(UI_TEXT["no_match_in_folder_status"])
            return
        self._accept_file_list(selected, folder, excluded=excluded)

    def update_counter(self):
        total = len(self.files)
        cur = self.idx + 1 if self.idx >= 0 else 0

        # Indicate files excluded from the filtered list.
        suffix = (
            UI_TEXT["excluded_large_opus_counter"].format(
                count=self._excluded_large_opus_count
            )
            if self._excluded_large_opus_count else ""
        )

        self.counter_lbl.config(text=f"{cur}/{total}{suffix}")
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
        self.apply_minor_ticks()
        # Also hide the axes after a failed load or an empty folder rescan.
        self.ax.set_visible(False)
        self.canvas.draw_idle()
        self.update_info_button_state()
        self.refresh_info_window()
        self.update_series_navigation_state()

    def _select_header_field_contents(self, widget):
        """Keep a focused read-only header visibly selected for easy copying."""
        try:
            widget.tag_remove(tk.SEL, "1.0", tk.END)
            if widget.get("1.0", "end-1c"):
                widget.tag_add(tk.SEL, "1.0", "end-1c")
                widget.mark_set(tk.INSERT, "1.0")
        except Exception:
            pass

    def _set_header_field(self, widget, text: str):
        try:
            had_focus = (self.focus_get() == widget)
        except Exception:
            had_focus = False

        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", str(text or ""))
        widget.configure(state="disabled")

        if had_focus:
            self.after_idle(
                lambda w=widget: self._select_header_field_contents(w)
                if self.focus_get() == w else None
            )

    def clear_header(self):
        self.show_header_lines([])

    def show_header_lines(self, lines, error=False):
        values = [str(x or "") for x in (lines or [])][:3]
        values.extend([""] * (3 - len(values)))

        for index, (widget, text) in enumerate(zip(self.header_fields, values)):
            if index == 2:
                # Expand the third header field only when displaying an error.
                widget.configure(
                    height=7 if error else 1,
                    wrap="word" if error else "none"
                )
            self._set_header_field(widget, text)

    def _set_persistent_clipboard_text(self, text: str) -> bool:
        """
        Put Unicode text on the OS clipboard so it survives application exit.

        On Windows, use the native clipboard API. SetClipboardData transfers
        ownership of the allocated HGLOBAL to Windows, so the text remains
        available after SpectraViewer closes.

        On other platforms, fall back to Tk's clipboard implementation.
        """
        text = str(text)

        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 0x0002

                user32 = ctypes.WinDLL("user32", use_last_error=True)
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

                # Explicit prototypes are important on 64-bit Windows;
                # otherwise pointer-sized handles may be truncated.
                user32.OpenClipboard.argtypes = [wintypes.HWND]
                user32.OpenClipboard.restype = wintypes.BOOL
                user32.EmptyClipboard.argtypes = []
                user32.EmptyClipboard.restype = wintypes.BOOL
                user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
                user32.SetClipboardData.restype = wintypes.HANDLE
                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = wintypes.BOOL

                kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
                kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
                kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalUnlock.restype = wintypes.BOOL
                kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalFree.restype = wintypes.HGLOBAL

                payload = (text + "\x00").encode("utf-16-le")

                hmem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
                if not hmem:
                    return False

                transferred = False
                try:
                    ptr = kernel32.GlobalLock(hmem)
                    if not ptr:
                        return False

                    try:
                        ctypes.memmove(ptr, payload, len(payload))
                    finally:
                        kernel32.GlobalUnlock(hmem)

                    if not user32.OpenClipboard(None):
                        return False

                    try:
                        if not user32.EmptyClipboard():
                            return False

                        if not user32.SetClipboardData(CF_UNICODETEXT, hmem):
                            return False

                        # After successful SetClipboardData, Windows owns hmem.
                        transferred = True
                        return True
                    finally:
                        user32.CloseClipboard()
                finally:
                    if not transferred and hmem:
                        kernel32.GlobalFree(hmem)

            except Exception:
                # If the native API unexpectedly fails, fall through to Tk.
                pass

        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            return True
        except Exception:
            return False

    def _copy_widget_selection_to_clipboard(self, event=None):
        """
        Copy the current selection to a persistent system clipboard.

        Works with the Path Entry, read-only header Text widgets and INFO Text.
        """
        widget = getattr(event, "widget", None)
        if widget is None:
            return "break"

        selected = None

        # Text-like widgets (header fields, INFO window).
        try:
            selected = widget.get("sel.first", "sel.last")
        except Exception:
            pass

        # Entry-like widgets (Path field).
        if selected is None:
            try:
                if widget.selection_present():
                    start = widget.index("sel.first")
                    end = widget.index("sel.last")
                    selected = widget.get()[start:end]
            except Exception:
                pass

        # No selection: preserve the usual Ctrl+C behavior of doing nothing.
        if selected is None:
            return "break"

        self._set_persistent_clipboard_text(selected)
        return "break"

    def _on_header_focus_in(self, event):
        """Select the whole focused header field so TAB + Ctrl+C works naturally."""
        self._select_header_field_contents(event.widget)

    def _on_header_focus_out(self, event):
        try:
            event.widget.tag_remove(tk.SEL, "1.0", tk.END)
        except Exception:
            pass

    def _focus_next_widget(self, event):
        next_widget = event.widget.tk_focusNext()
        if next_widget is not None:
            next_widget.focus_set()
        return "break"

    def _focus_prev_widget(self, event):
        prev_widget = event.widget.tk_focusPrev()
        if prev_widget is not None:
            prev_widget.focus_set()
        return "break"

    def get_current_series_state(self):
        """Return (y2d, index, count, store_indices, label) or None."""
        if self.current is None:
            return None

        meta = self.current.meta or {}
        y2d = meta.get("series_y")
        if not isinstance(y2d, np.ndarray) or y2d.ndim != 2 or y2d.shape[0] < 1:
            return None

        count = int(y2d.shape[0])
        try:
            index = int(meta.get("series_index", 0))
        except Exception:
            index = 0
        index = max(0, min(count - 1, index))

        store_indices = list(meta.get("series_store_indices", []) or [])
        if len(store_indices) != count:
            store_indices = list(range(1, count + 1))

        label = str(meta.get("series_label", "") or self.current.yunit or UI_TEXT["series_default_label"])
        return y2d, index, count, store_indices, label

    def update_series_navigation_state(self):
        prev_btn = getattr(self, "series_prev_btn", None)
        next_btn = getattr(self, "series_next_btn", None)
        if prev_btn is None or next_btn is None:
            return

        state = self.get_current_series_state()
        if state is None:
            self.series_counter_var.set("1/1" if self.current is not None else "0/0")
            prev_btn.state(["disabled"])
            next_btn.state(["disabled"])
            return

        _y2d, index, count, _store_indices, _label = state
        self.series_counter_var.set(f"{index + 1}/{count}")

        if count <= 1 or index <= 0:
            prev_btn.state(["disabled"])
        else:
            prev_btn.state(["!disabled"])

        if count <= 1 or index >= count - 1:
            next_btn.state(["disabled"])
        else:
            next_btn.state(["!disabled"])

    @busy_operation
    def set_series_index(self, index: int):
        state = self.get_current_series_state()
        if state is None:
            self.update_series_navigation_state()
            return

        y2d, _old_index, count, store_indices, label = state
        index = max(0, min(count - 1, int(index)))

        meta = self.current.meta or {}
        meta["series_index"] = index
        self.current.meta = meta
        self.current.y = np.asarray(y2d[index], dtype=float)

        stored_index = store_indices[index] if index < len(store_indices) else index + 1
        path = getattr(self.current, "path", "") or ""
        self.status_var.set(UI_TEXT["series_stored_status"].format(
            path=path, label=label, index=index + 1,
            count=count, stored_index=stored_index,
        ))

        self.redraw()
        self.update_series_navigation_state()

    def series_prev(self):
        state = self.get_current_series_state()
        if state is None:
            return
        _y2d, index, _count, _store_indices, _label = state
        if index > 0:
            self.set_series_index(index - 1)

    def series_next(self):
        state = self.get_current_series_state()
        if state is None:
            return
        _y2d, index, count, _store_indices, _label = state
        if index < count - 1:
            self.set_series_index(index + 1)

    def get_current_info_fields(self) -> List[Dict[str, str]]:
        if self.current is None:
            return []
        return list((self.current.meta or {}).get("info_fields", []) or [])

    def update_info_button_state(self):
        btn = getattr(self, "info_btn", None)
        if btn is None:
            return

        # Both native OPUS and SpectraViewer DX expose the same INFO fields.
        # No source-format-specific UI behavior is needed.
        if self.get_current_info_fields():
            btn.state(["!disabled"])
        else:
            btn.state(["disabled"])

    def _format_info_text(self, fields: List[Dict[str, str]]) -> str:
        filled = [f for f in (fields or []) if str(f.get("value", "")).strip()]
        if not fields:
            return UI_TEXT["info_no_block"]
        if not filled:
            return UI_TEXT["info_no_filled_fields"]

        # Keep one logical INFO field per line. Long values remain intact and
        # can be reached with the horizontal scrollbar / copied to clipboard.
        return "\n".join(
            f"{f.get('label') or f.get('code') or 'INFO'}: {f.get('value', '')}"
            for f in filled
        )

    def refresh_info_window(self):
        win = getattr(self, "info_win", None)
        text_widget = getattr(self, "info_text", None)
        if win is None or text_widget is None:
            return
        try:
            if not win.winfo_exists():
                self.info_win = None
                self.info_text = None
                return
        except Exception:
            self.info_win = None
            self.info_text = None
            return

        path = getattr(self.current, "path", "") if self.current is not None else ""
        fname = os.path.basename(path) if path else ""
        title = UI_TEXT["info_window_title"]
        if fname:
            title += f" – {fname}"
        win.title(title)

        content = self._format_info_text(self.get_current_info_fields())
        text_widget.configure(state="normal")
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")
        text_widget.xview_moveto(0)
        text_widget.yview_moveto(0)

    def show_info_window(self):
        fields = self.get_current_info_fields()

        existing = getattr(self, "info_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    self.refresh_info_window()
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        win = tk.Toplevel(self)
        self.info_win = win
        win.geometry("760x430")
        win.minsize(420, 220)

        try:
            win.iconbitmap(resource_path(r"assets\SpectraViewer.ico"))
        except Exception:
            pass

        # Intentionally not transient / always-on-top: this is a normal helper
        # window that may sit beside or behind the main SpectraViewer window.
        frame = ttk.Frame(win, padding=6)
        frame.pack(fill="both", expand=True)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        text_widget = tk.Text(
            frame,
            wrap="none",
            font="TkFixedFont",
            undo=False,
            borderwidth=1,
            relief="sunken",
        )
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=text_widget.xview)
        text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        text_widget.bind("<Control-c>", self._copy_widget_selection_to_clipboard)
        text_widget.bind("<Control-C>", self._copy_widget_selection_to_clipboard)

        text_widget.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        self.info_text = text_widget

        def close_info(event=None):
            try:
                if win.winfo_exists():
                    win.destroy()
            finally:
                self.info_win = None
                self.info_text = None
            return "break"

        win.protocol("WM_DELETE_WINDOW", close_info)
        win.bind("<Escape>", close_info)
        self.refresh_info_window()
        win.lift()
        win.focus_force()

    def show_error_state(self, path: str, error_msg: str):
        self.current = None
        self.clear_plot()
        self.update_series_navigation_state()

        fname = os.path.basename(path) if path else ""
        fullpath = str(path or "")
        msg = str(error_msg or UI_TEXT["unknown_error"])

        header_lines = []
        if fname:
            header_lines.append(fname)
        if fullpath and fullpath != fname:
            header_lines.append(fullpath)
        header_lines.append(f"{UI_TEXT['error_prefix']}: {msg}")
        self.show_header_lines(header_lines, error=True)

        if fullpath:
            self.status_var.set(f"{UI_TEXT['error_prefix']}: {msg} | {UI_TEXT['file_label']}: {fullpath}")
        else:
            self.status_var.set(f"{UI_TEXT['error_prefix']}: {msg}")

    @busy_operation
    def load_current(self) -> bool:
        if self.idx < 0 or self.idx >= len(self.files):
            return False

        path = self.files[self.idx]
        self.status_var.set(
            UI_TEXT["loading_spectrum_status"].format(
                filename=os.path.basename(str(path))
            )
        )
        self.update_idletasks()
        loaded = False
        try:
            spec = read_any(str(path), metadata_encoding=self.metadata_encoding)
            self.current = spec
            self.status_var.set(str(path))
            self.redraw()
            self.update_info_button_state()
            self.refresh_info_window()
            self.update_series_navigation_state()
            loaded = True
        except Exception as ex:
            self.show_error_state(str(path), str(ex))
        finally:
            self.update_counter()

        return loaded

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

        ok_btn = ttk.Button(about, text=UI_TEXT["ok_button"], command=on_close)
        ok_btn.pack(pady=(0, 10))
        ok_btn.focus_set()
        ok_btn.bind("<Return>", on_close)

        # UX refinement: keep the window focused and in front.
        about.lift()
        ok_btn.focus_force()

    def apply_minor_ticks(self):
        """Show optional unlabeled divisions, without changing major ticks.

        AutoMinorLocator follows the existing automatic major spacing,
        including after Matplotlib toolbar zoom/pan operations.
        """
        self.ax.xaxis.set_minor_locator(
            AutoMinorLocator() if self.x_minor_ticks else NullLocator()
        )
        self.ax.yaxis.set_minor_locator(
            AutoMinorLocator() if self.y_minor_ticks else NullLocator()
        )
        self.ax.tick_params(
            axis="x", which="minor", direction="out",
            bottom=self.x_minor_ticks, top=False, length=3, width=0.6,
        )
        self.ax.tick_params(
            axis="y", which="minor", direction="out",
            left=self.y_minor_ticks, right=False, length=3, width=0.6,
        )

    def redraw(self):
        if self.current is None:
            return
        spec = self.current
        self.ax.clear()
        self.ax.plot(spec.x, spec.y, color=self.line_color, linewidth=self.line_width)
        # Restore the usual axes, ticks and labels whenever a valid spectrum
        # becomes active (including recovery after an unsuccessful file load).
        self.ax.set_visible(True)

        # Header fields: 1) filename, 2) sample name, 3) sample form.
        # Store the full strings; no width-dependent ellipsis is applied.
        fname = os.path.basename(spec.path) if spec.path else spec.title
        sname = (spec.meta or {}).get("sample_name", "") or ""
        sform = (spec.meta or {}).get("sample_form", "") or ""
        self.show_header_lines([fname, sname, sform])
        self.ax.set_xlabel(spec.xunit)
        self.ax.set_ylabel(spec.yunit or UI_TEXT["axis_intensity"])
        self.apply_minor_ticks()

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
        self.update_series_navigation_state()

    def current_default_jcamp_name(self) -> str:
        if not self.current or not self.current.path:
            return "spectrum.dx"
        base = os.path.basename(self.current.path)
        # Do not append an SV marker: source-overwrite protection is enforced
        # by save_jcamp_dx_file() even when a DX source name is unchanged.
        if is_jcamp_like(self.current.path):
            base = os.path.splitext(base)[0]
        state = self.get_current_series_state()
        if state is not None:
            _y2d, index, count, _store_indices, _label = state
            if count > 1:
                base += f"_series_{index + 1:04d}"
        return base + ".dx"

    def save_current_jcamp(self):
        if self.current is None:
            messagebox.showinfo(UI_TEXT["save_message_title"],
                                UI_TEXT["no_loaded_spectrum"])
            return
        default = self.current_default_jcamp_name()
        initialdir = (os.path.dirname(self.current.path)
                      if self.current.path else os.getcwd())
        out = filedialog.asksaveasfilename(
            title=UI_TEXT["save_jcamp_title"],
            initialdir=initialdir,
            initialfile=default,
            defaultextension=".dx",
            filetypes=[(UI_TEXT["save_jcamp_filter"], "*.dx")],
        )
        if not out:
            return
        try:
            save_jcamp_dx_file(self.current, out)
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            messagebox.showerror(UI_TEXT["save_jcamp_error_title"],
                                 str(exc), parent=self)
            return
        self.status_var.set(UI_TEXT["saved_status"].format(path=out))

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
                (UI_TEXT["all_files"], "*.*"),
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
