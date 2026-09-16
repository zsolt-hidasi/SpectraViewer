<p align="center">
  <a href="https://doi.org/10.5281/zenodo.20715098">
    <img src="https://zenodo.org/badge/DOI/10.5281/zenodo.20715098.svg" alt="DOI">
  </a>
</p>

<p align="center">
  <img src="assets/SpectraViewer_banner.png" alt="SpectraViewer banner" width="500">
</p>

# SpectraViewer

SpectraViewer is a lightweight desktop application for opening, browsing, and visually inspecting spectrum files. It is designed as a fast spectrum browser rather than a full spectrum-processing or spectrum-manipulation environment.

The program can collect supported spectrum files from a folder, from a folder tree, from a manually selected set of files, or from drag-and-drop input, then display them as a navigable list. It can also browse individual spectra stored in supported OPUS DataSeries files.

SpectraViewer does **not** replace OPUS or other dedicated spectroscopy software. It does not perform spectral processing, manipulation, identification, database searching, or quantitative analysis. Its purpose is quick viewing and convenient browsing.

SpectraViewer displays a single spectrum at a time. It does not provide stacked or overlaid multi-spectrum views.

## Current version

**Version:** 1.1.9<br>
**Release:** v1.1.9<br>
**Concept DOI:** 10.5281/zenodo.20715098<br>
**Author:** Zsolt Hidasi<br>
**Year:** 2026<br>
**License:** MIT License

## Supported spectrum formats

SpectraViewer currently supports:

- **OPUS native spectrum files** with numeric extensions, such as `.0`, `.1`, `.2`, `.12`, etc.
- **OPUS exported data point table files:** `.dpt`
- **JCAMP-DX files:** `.dx`, `.jdx`

Numeric extensions are not accepted blindly: native OPUS files are also checked for the OPUS binary file signature, so unrelated files with numeric extensions are skipped.

For OPUS files, SpectraViewer supports processed **Absorbance**, **Transmittance**, **Reflectance**, and **Kubelka–Munk** spectra, including compatible multi-spectrum DataSeries.

Not all supported file formats contain the same amount or structure of metadata. Depending on the file type and file content, SpectraViewer may display only the spectrum itself, or it may also display metadata such as sample name, sample form, or INFO fields.

## Main features

- Open individual spectrum files.
- Open multiple selected spectrum files as a custom list.
- Open folders and browse all supported spectrum files in the selected folder.
- Optionally include subfolders in the scan.
- Drag and drop files or folders into the application window.
- Browse files with Previous/Next, Home/End, and Page Up/Page Down navigation.
- Browse spectra inside supported OPUS DataSeries files with dedicated controls or the Up/Down arrow keys.
- Use **Single file** mode to inspect only one selected spectrum without loading the surrounding folder context.
- Display filename, Sample Name, and Sample Form in copyable read-only header fields.
- Display the active OPUS INFO block in a separate **INFO** window when available.
- Select the character encoding used to display text metadata in OPUS and JCAMP-DX files when needed.
- Choose the X-axis display direction.
- Use an optional crosshair cursor to read approximate coordinates.
- Toggle the crosshair with the right mouse button in the plot area.
- Change the displayed spectrum color.
- Configure spectrum line width through `SpectraViewer.ini`.
- Export the current plot as PNG, JPEG, PDF, or SVG.
- Use Matplotlib's built-in toolbar for zooming, panning, and restoring the view.
- File-count and large-OPUS safeguards help avoid accidental loading of very large collections or unusually large files.

## Operating logic

SpectraViewer is not based purely on the traditional "open one file, show one file" model. In normal operation, opening a single supported spectrum file usually creates a browsable list from the file's surrounding context.

When a single file is opened and **Include subfolders** is not enabled, SpectraViewer scans the folder containing that file and builds a list from the supported spectrum files found there. The opened file becomes the current item in the list.

When **Include subfolders** is enabled, SpectraViewer scans the same folder recursively and includes supported files from its subfolders as well. The resulting files are handled as one navigable list.

When a supported OPUS DataSeries is opened, the file remains one item in the file list, while its individual spectra can be browsed sequentially inside the file.

When **Single file** mode is enabled, SpectraViewer opens and displays only one selected spectrum file. The surrounding folder context is not loaded, and subfolder traversal is temporarily disabled.

Single file mode applies consistently to:

- file dialog opening,
- manually typed paths,
- drag-and-drop opening.

If multiple files are dropped while Single file mode is active, SpectraViewer shows a warning and does not load them as a list.

When Single file mode is disabled again, SpectraViewer restores the previously stored **Include subfolders** setting and rebuilds the folder context from the current spectrum.

The Previous and Next navigation controls are automatically disabled when the active list contains fewer than two files.

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

The Path field shows the current file or folder context. A file or folder path can also be typed or pasted into the field and opened with Enter.

### Drag and drop

Files or folders can be dragged onto the SpectraViewer window.

- Dropping a single supported spectrum file follows the same logic as opening a file normally.
- Dropping a folder scans that folder.
- Dropping multiple files creates an ad-hoc playlist from the dropped supported files.
- Unsupported files are skipped.
- In Single file mode, dropping multiple files produces a warning instead of creating a playlist.

Drag-and-drop support depends on the availability of `tkinterdnd2` and the underlying Tcl/Tk environment.

## User interface overview

The main window contains:

- a Path field,
- **Folder...** and **File...** buttons,
- **Include subfolders** and **Single file** checkboxes,
- file navigation buttons,
- image export and color controls,
- a file counter,
- X-axis display direction and crosshair options,
- a metadata character-encoding selector,
- the spectrum display area,
- copyable filename / Sample Name / Sample Form header fields,
- the Matplotlib navigation toolbar,
- DataSeries navigation controls,
- an **INFO** button,
- a status bar.

The **INFO** button is enabled when the current OPUS spectrum contains a readable INFO block. The INFO window follows the current spectrum and the selected metadata encoding.

## Configuration file

SpectraViewer stores selected settings in `SpectraViewer.ini`, located next to the program script or executable. The file is created automatically when needed.

Stored settings include:

- spectrum color and line width,
- crosshair state,
- X-axis direction,
- Single file and subfolder settings,
- window geometry,
- last used path,
- metadata encoding,
- advanced warning thresholds.

Advanced settings currently include:

```ini
[advanced]
warn_file_count = 5000
large_opus_warn_mb = 20
```

`warn_file_count` may be set from 1 to 19999. The hard maximum of 20000 files is internal and cannot be overridden. `large_opus_warn_mb` may be set above 0 and up to 100 MB. Invalid values fall back to their defaults.

The spectrum line width is also configurable in the INI file. The default is `1.5`; valid values are `0.1` to `5.0`.

Deleting `SpectraViewer.ini` restores the default settings.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open file |
| `Ctrl+Shift+O` | Open folder |
| `Left` / `Right` | Previous / Next file |
| `Page Up` / `Page Down` | Jump backward / forward by 25 files |
| `Home` / `End` | First / Last file |
| `Up` / `Down` | Previous / Next spectrum in DataSeries |
| `Ctrl+S` | Save current plot as image |
| `Ctrl+Shift+C` | Change spectrum color |
| `Ctrl+I` | Open INFO window when INFO data are available |
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

Development and testing are performed primarily on Windows. Core functionality may also work on other systems where the required Python packages and Tcl/Tk support are available, although some platform-dependent behavior may differ.

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

When available, the portable ZIP package is provided in the repository's release section.

The bundled distribution is intended to run without modifying system-level Python installations, Windows Registry settings, or other existing Python environments.

## Important notes and limitations

SpectraViewer is intended for quick viewing and browsing rather than full spectral processing.

For compatible OPUS files, processed Absorbance, Transmittance, Reflectance, and Kubelka–Munk spectra can be displayed as individual spectra or browsed sequentially from DataSeries files. OPUS containers may also contain images, auxiliary data, or other blocks that SpectraViewer does not attempt to display.

Large composite OPUS files may require substantial memory and loading time. SpectraViewer therefore warns before opening unusually large OPUS files; the default warning threshold is 20 MB and can be adjusted in `SpectraViewer.ini` up to 100 MB. This is a warning threshold, not a file-size limit.

SpectraViewer does not perform spectral correction, preprocessing, baseline correction, normalization, library searching, peak picking, or quantitative analysis.

## Localization

The English user interface is the primary public GitHub version.

A matching Hungarian UI variant is preserved for version 1.1.9. The English and Hungarian variants share the same program logic and differ only in the language of the user-facing text.

## Repository structure

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
    SpectraViewer_banner.png
    SpectraViewer_logo.png
  localized/
    hu/
      SpectraViewer_1.1.9_HU.py
      SpectraViewerMan_HU.pdf
  docs/
    SpectraViewer_User_Manual_1.1.8.docx
    SpectraViewerMan_EN.pdf
```

## Citation and DOI

SpectraViewer is archived on Zenodo and has a citable Concept DOI: `10.5281/zenodo.20715098`.

If you use SpectraViewer in research, teaching, or documentation, please cite the released version using the citation information provided in the repository or on Zenodo.

A `CITATION.cff` file is included so that GitHub can display citation information for the repository.

## License

SpectraViewer is released under the MIT License.

## Acknowledgements

SpectraViewer was developed by Zsolt Hidasi with assistance from OpenAI ChatGPT during design, refactoring, documentation, and release preparation.
