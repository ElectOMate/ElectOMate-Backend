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
}

# Directory where local copies are stored
# This file lives at: src/em_backend/config/manifesto_urls.py
# .parent      → src/em_backend/config/
# .parent.parent   → src/em_backend/
# .parent.parent.parent  → src/
# .parent.parent.parent.parent → backend root (ElectOMate-Backend/)
LOCAL_MANIFESTO_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "manifestos"
