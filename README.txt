Lu Xun German Translations Stylometry
Public preparation 3.3-public.4 — 17 November 2026
Associated manuscript: v3.3; quantitative analysis: 3.2.1; syntax: 3.1.2.

This package documents the quantitative comparison of nine German textual witnesses of Lu Xun's Diary of a Madman. It includes analysis scripts, numerical results, six figures, sentence-level counts without sentence text, and corrections identified by hashes and token positions.

CONTENTS
analysis/syntax-v3.1.2/: syntax method, aggregate results and 2,404 text-free sentence metric records.
analysis/all-analyses-v3.2.1/: readability, lexical, PCA and Delta analyses, numerical comparisons, frequency tables and figures.
REPRODUCTION.txt: verification without corpus access and local recalculation with separately obtained inputs.
PUBLICATION_SCOPE.txt: included and omitted material and precise reproducibility limits.
CITATION.cff: structured citation metadata with the repository URL and the author-reserved Zenodo DOI.
LICENSE.txt and RIGHTS.txt: MIT for scripts; CC BY 4.0 for original standalone documentation, figures and result materials.
LICENSES/: complete licence texts.
CITING.txt: requested scholarly citation of the version used and, where relevant, the associated article.
PUBLIC_FILES.json and SHA256SUMS: exact file inventory and integrity checks.

The public preparation retains the final corrected numerical values. It contains no translation full texts, scans, manuscript versions, concordance passages, ordered lexical token streams or complete reference sentences. Word types and short linguistic forms remain where required to document features and correction patterns.

QUICK VERIFICATION
python verify_public_results.py
This uses the Python standard library to check the numerical consistency of the distributed results without accessing the translation texts.

ARCHIVE
python make_public_archive.py --output ../lu-xun-german-translations-stylometry-v3.3-public.4.zip
The exporter includes only the inventoried files, checks their hashes and refuses changed files. It never recursively adds a local corpus or new analysis outputs.

REPOSITORY AND ARCHIVAL RECORD
GitHub: https://github.com/ch-auf-der-horst/lu-xun-german-translations-stylometry
Zenodo DOI: https://doi.org/10.5281/zenodo.24307802

The author reserved this DOI for the code and numerical-results package. It identifies the accompanying research materials, not the manuscript itself. At preparation on 17 November 2026, archival publication was pending; the DOI is registered when the Zenodo record is published. No completed package upload or release date is claimed in this preparation.

LICENSING AND CITATION
The MIT and CC BY 4.0 licences apply to different components, as specified in LICENSE.txt. They do not grant rights in the translation texts. Please cite the version used with its Zenodo DOI once published, and cite the associated article when drawing on its interpretation or findings. This scholarly request does not add a condition to either licence.
