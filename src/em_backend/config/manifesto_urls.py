"""
Manifesto PDF URL mapping for German federal election 2025.
"""
from pathlib import Path

# External URLs — used as fallback if local file not available
MANIFESTO_URLS: dict[str, str] = {
    "SPD": "https://www.spd.de/fileadmin/Dokumente/Beschluesse/Programm/SPD_Programm_bf.pdf",
    "CDU": "https://www.politikwechsel.cdu.de/sites/www.politikwechsel.cdu.de/files/downloads/km_btw_2025_wahlprogramm_langfassung_ansicht.pdf",
    "GRUNE": "https://cms.gruene.de/uploads/assets/99x210_DieGruenen_BTW_Give-Aways_Flyer-8-seiter_deutsch_2.pdf",
    "FDP": "https://www.fdp.de/sites/default/files/2024-12/fdp-wahlprogramm_2025.pdf",
    "AFD": "https://www.afd.de/wp-content/uploads/2025/02/AfD_Bundestagswahlprogramm2025_web.pdf",
    "LINKE": "https://www.die-linke.de/fileadmin/user_upload/Wahlprogramm_Langfassung_Linke-BTW25_01.pdf",
    "BSW": "https://bsw-vg.de/wp-content/themes/bsw/assets/downloads/BSW%20Wahlprogramm%202025.pdf",
    "BUENDNIS": "https://buendnis-deutschland.de/wp-content/uploads/2025/01/btw25-final.pdf",
    # FREIE and MLPD remote URLs are HTML pages, not PDFs — local files only
    # "FREIE": "https://www.freiewaehler.eu/unsere-politik/wahlprogramm/",
    # "MLPD": "https://www.mlpd.de/parteiprogramm",
    "VOLT": "https://voltdeutschland.org/storage/assets-btw25/volt-programm-bundestagswahl-2025.pdf",
}

# Local filename mapping — must match actual files in LOCAL_MANIFESTO_DIR
MANIFESTO_LOCAL_NAMES: dict[str, str] = {
    # Germany
    "SPD": "SPD.pdf",
    "CDU": "CDU.pdf",
    "GRUNE": "GRUNE.pdf",
    "FDP": "FDP.pdf",
    "AFD": "AFD.pdf",
    "LINKE": "LINKE.pdf",
    "BSW": "BSW.pdf",
    "BUENDNIS": "BUENDNIS.pdf",
    "FREIE": "FREIE.pdf",
    "MLPD": "MLPD.pdf",
    "VOLT": "VOLT.pdf",
    # Hungary
    "FIDESZ": "FIDESZ.pdf",
    "TISZA": "TISZA.pdf",
    "DK": "DK.pdf",
    "MI_HAZANK": "MI_HAZANK.pdf",
    "MKKP": "MKKP.pdf",
    "JOBBIK": "JOBBIK.pdf",
    "MSZP": "MSZP.pdf",
}

# Mapping from DB party shortname → manifesto key used in MANIFESTO_URLS / MANIFESTO_LOCAL_NAMES.
# Needed because DB shortnames use umlauts (Grüne, AfD, Linke) while manifesto keys are
# ASCII-normalised (GRUNE, AFD, LINKE). Without this, `"Grüne".upper()` → "GRÜNE" which
# doesn't match "GRUNE". See docs/party_shortname_mismatch.md for full explanation.
PARTY_SHORTNAME_TO_MANIFESTO_KEY: dict[str, str] = {
    # Germany
    "CDU": "CDU",
    "SPD": "SPD",
    "Grüne": "GRUNE",
    "FDP": "FDP",
    "AfD": "AFD",
    "Linke": "LINKE",
    "BSW": "BSW",
    "VOLT": "VOLT",
    "BUENDNIS": "BUENDNIS",
    "FREIE": "FREIE",
    "MLPD": "MLPD",
    # Hungary
    "Fidesz": "FIDESZ",
    "TISZA": "TISZA",
    "DK": "DK",
    "Mi Hazánk": "MI_HAZANK",
    "MKKP": "MKKP",
    "Jobbik": "JOBBIK",
    "MSZP": "MSZP",
}

# Directory where local copies are stored
# This file lives at: src/em_backend/config/manifesto_urls.py
# .parent      → src/em_backend/config/
# .parent.parent   → src/em_backend/
# .parent.parent.parent  → src/
# .parent.parent.parent.parent → backend root (ElectOMate-Backend/)
LOCAL_MANIFESTO_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "manifestos"
