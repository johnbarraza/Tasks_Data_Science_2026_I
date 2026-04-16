from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

IPRESS_PATH = RAW_DIR / "IPRESS_Health_Facilities" / "IPRESS.csv"
C1_PATH = RAW_DIR / "Consulta_C1_IPRESS" / "ConsultaC1_2026_v4.csv"


def load_ipress_raw(path: Path | None = None) -> pd.DataFrame:
    source = path or IPRESS_PATH
    return pd.read_csv(source, encoding="latin1", dtype=str)


def load_c1_raw(path: Path | None = None) -> pd.DataFrame:
    source = path or C1_PATH
    return pd.read_csv(source, sep=";", encoding="latin1", dtype=str)

