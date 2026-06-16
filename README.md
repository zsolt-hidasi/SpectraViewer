[![DOI](https://zenodo.org/badge/1270508432.svg)](https://doi.org/10.5281/zenodo.20715098)

<p align="center">
  <img src="assets/SpectraViewer_banner.png" alt="SpectraViewer banner" width="800">
</p>

# SpectraViewer

SpectraViewer is a lightweight desktop application for opening, browsing, and visually inspecting spectrum files. It is designed as a fast spectrum browser rather than a full spectrum-processing or spectrum-manipulation environment.

The program can collect supported spectrum files from a folder, from a folder tree, from a manually selected set of files, or from drag-and-drop input, then display them as a navigable list. This makes it useful for quick inspection, checking, and visual comparison of larger spectrum collections.

SpectraViewer does **not** replace OPUS or other dedicated spectroscopy software. It does not perform spectral processing, manipulation, identification, or database searching. Its purpose is quick viewing and convenient browsing.

SpectraViewer displays a single spectrum at a time. It does not provide stacked or overlaid multi-spectrum views, as commonly used in dedicated spectral evaluation or processing software.

## Current version

**Version:** 1.1.5  
**Release:** v1.1.5  
**Version DOI:** 10.5281/zenodo.20715099  
**Author:** Zsolt Hidasi  
**Year:** 2026  
**License:** MIT License

Version 1.1.5 is preserved as a functional milestone with matching English and Hungarian user-interface variants. Both variants share the same program logic and differ only in the language of the user-facing text.

## Supported spectrum formats

SpectraViewer currently supports:

- **OPUS native spectrum files** with numeric extensions, such as `.0`, `.1`, `.2`, etc.
- **OPUS exported data point table files:** `.dpt`
- **JCAMP-DX files:** `.dx`, `.jdx`

During file opening, folder scanning, or drag-and-drop operations, SpectraViewer only uses files with supported extensions. Unsupported files are skipped, and the program may display a warning when appropriate.

Not all supported file formats contain the same amount or structure of metadata. Depending on the file type and file content, SpectraViewer may display only the spectrum itself, or it may also display basic metadata such as sample name and sample form.

## Main features

- Open individual spectrum files.
- Open multiple selected spectrum files as a custom list.
- Open folders and browse all supported spectrum files in the selected folder.
- Optionally include subfolders in the scan.
- Drag and drop files or folders into the application window.
- Browse spectra with Previous/Next, Home/End, and PageUp/PageDown navigation.
- Use **Single file** mode to inspect only one selected spectrum without loading the surrounding folder context.
- Display basic file and spectrum metadata above the plot when available.
- Invert the X axis for the conventional FTIR wavenumber display direction.
- Use an optional crosshair cursor to read approximate coordinates.
- Toggle the crosshair with the right mouse button in the plot area.
- Change the displayed spectrum color.
- Export the current plot as PNG, JPEG, PDF, or SVG.
- Use Matplotlib's built-in toolbar for zooming, panning, and restoring the view.
- File-count safeguards are used to avoid accidental loading of extremely large collections.
- User-interface text is centralized in a `UI_TEXT` dictionary to support maintainable localization.

## Operating logic

SpectraViewer is not based purely on the traditional "open one file, show one file" model. In normal operation, opening a single supported spectrum file usually creates a browsable list from the file's surrounding context.

When a single file is opened and **Include subfolders** is not enabled, SpectraViewer scans the folder containing that file and builds a list from the supported spectrum files found there. The opened file becomes the current item in the list.

When **Include subfolders** is enabled, SpectraViewer scans the same folder recursively and includes supported files from its subfolders as well. The resulting files are handled as one navigable list.

This behavior is useful when a user wants to move quickly through a spectrum collection without repeatedly opening files one by one.

## Single file mode

Version 1.1.5 adds **Single file** mode.

When **Single file** mode is enabled, SpectraViewer opens and displays only one selected spectrum file. The surrounding folder context is not loaded, and subfolder traversal is temporarily disabled.

Single file mode applies consistently to:

- file dialog opening,
- manually typed paths,
- drag-and-drop opening.

If multiple files are dropped while Single file mode is active, SpectraViewer shows a warning and does not load them as a list.

When Single file mode is disabled again, SpectraViewer restores the previously stored **Include subfolders** setting and rebuilds the folder context from the current spectrum. This returns the program to its normal browsing behavior.

The Previous and Next navigation controls are automatically disabled when the active list contains fewer than two spectra.

## File loading and drag and drop

SpectraViewer can load spectra in several ways:

### File dialog

Use **File...** to select one or more supported spectrum files.

- Selecting one file normally loads its surrounding folder context.
- Selecting multiple files creates a custom navigable list from the selected supported files.
- In Single file mode, only one supported file can be opened.

### Folder dialog

Use **Folder...** to select a folder. SpectraViewer scans the selected folder and builds a list from the supported spectrum files found there.

If **Include subfolders** is active, the selected folder is scanned recursively.

### Path field

The path field shows the current file or folder context. A file or folder path can also be typed or pasted into the field and opened with Enter.

### Drag and drop

Files or folders can be dragged onto the SpectraViewer window.

- Dropping a single supported spectrum file follows the same logic as opening a file normally.
- Dropping a folder scans that folder.
- Dropping multiple files creates an ad-hoc playlist from the dropped supported files.
- Unsupported files are skipped.
- In Single file mode, dropping multiple files produces a warning instead of creating a playlist.

Drag and drop support depends on the availability of `tkinterdnd2` and the underlying Tcl/Tk environment.

## User interface overview

The main window contains:

- a path field,
- **Folder...** and **File...** buttons,
- **Include subfolders** and **Single file** checkboxes,
- navigation buttons,
- image export and color controls,
- a file counter,
- X-axis inversion and crosshair options,
- the spectrum display area,
- the Matplotlib navigation toolbar,
- a status bar.

The spectrum display area shows the current spectrum plot. When available, the header above the plot displays the filename and selected metadata, such as sample name and sample form. The status bar provides short feedback about the current state, opened file, saved output, or errors.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open file |
| `Ctrl+Shift+O` | Open folder |
| `Left` / `Right` | Previous / Next spectrum |
| `Home` / `End` | First / Last spectrum |
| `PageUp` / `PageDown` | Jump backward / forward by 25 spectra |
| `Ctrl+S` | Save current plot as image |
| `Ctrl+Shift+C` | Change spectrum color |
| `F1` | About window |

## Plot export

The currently displayed spectrum plot can be exported as:

- PNG,
- JPEG,
- PDF,
- SVG.

The exported image reflects the visible plot state. If the crosshair is enabled and visible, it is included in the saved figure.

## Requirements

SpectraViewer is a Python/Tkinter application. The source version requires:

- Python 3,
- NumPy,
- Matplotlib,
- Tkinter / Tcl-Tk,
- `tkinterdnd2` for drag-and-drop support,
- `brukeropus` for reading OPUS files.

Tkinter is normally bundled with standard Python installations on Windows. On some Linux distributions it may need to be installed through the system package manager.

## Installation from source

Clone or download the repository, then install the required Python packages in a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On Linux or macOS, use the appropriate activation command for your shell, for example:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Running SpectraViewer

From the project folder:

```bash
python SpectraViewer.py
```

## Portable/bundled distribution

A bundled Windows distribution may include an isolated Python environment and launcher scripts. In that case, the program can be started by running the provided launcher, such as `SpectraViewer.bat`.

The bundled distribution is intended to run without modifying system-level Python installations, Windows Registry settings, or other existing Python environments.

## Important notes and limitations

SpectraViewer is intended for quick viewing of relatively simple spectrum files.

Some OPUS files can contain multiple data blocks, such as absorbance or transmittance spectra, single-channel data, mapping data, image-related information, or other accompanying blocks. In such cases, SpectraViewer may not always display the spectrum that the user expects as the primary result.

If a complex OPUS file does not display as expected, extract the desired spectrum as a simpler file in OPUS first, then open the extracted file in SpectraViewer.

SpectraViewer does not perform spectral correction, preprocessing, baseline correction, normalization, library searching, peak picking, or quantitative analysis.

## Localization

The English user interface is intended as the primary public GitHub version.

A matching Hungarian UI variant is preserved for version 1.1.5. The English and Hungarian variants share the same program logic and differ only in the language of the user-facing text.

## Proposed repository structure

```text
SpectraViewer/
  SpectraViewer.py
  history.txt
  README.md
  LICENSE
  requirements.txt
  CITATION.cff
  .gitignore
  assets/
    SpectraViewer.ico
  localized/
    hu/
      SpectraViewer_1.1.5_HU.py
  docs/
    SpectraViewerMan.pdf
```

## Citation and DOI

SpectraViewer is intended to be published as citable research software. The planned workflow is:

1. publish the source code on GitHub,
2. create a tagged GitHub release,
3. archive the release through Zenodo,
4. obtain a DOI for the released version,
5. update the README and citation metadata with the DOI.

A `CITATION.cff` file should be added before the first public release so that GitHub can display citation information for the repository.

Until a DOI is minted, cite the repository and version manually.

## License

SpectraViewer is planned to be released under the MIT License.

## Acknowledgements

SpectraViewer was developed by Zsolt Hidasi with assistance from OpenAI ChatGPT during design, refactoring, documentation, and release preparation.
