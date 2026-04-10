from __future__ import annotations

import argparse
import base64
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://admision.unmsm.edu.pe/Website20262/A/A.html"
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent / "output_task_1" / "resultados_sanmarcos.xlsx"
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
})


def decode_b64(encoded: str) -> str:
    try:
        return base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return ""


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def fix_encoding(text: str) -> str:
    try:
        return text.encode("latin-1").decode("utf-8")
    except Exception:
        return text


def get_career_links() -> list[str]:
    resp = SESSION.get(BASE_URL, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(BASE_URL, href)
        if "/Website20262/A/" in full and full.lower().endswith(".html"):
            links.append(full)
    unique = sorted(set(links))
    unique = [u for u in unique if u != BASE_URL]
    if not unique:
        raise RuntimeError("No se encontraron links de carreras.")
    return unique


def scrape_career(url: str, retries: int = 3) -> pd.DataFrame:
    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, timeout=20)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.find("table", {"id": "tablaPostulantes"})
            if not table:
                table = soup.find("table")
            if not table:
                raise RuntimeError("No se encontrÃ³ tabla.")

            # Cabeceras con encoding corregido
            headers = [
                fix_encoding(normalize(th.get_text()))
                for th in table.select("thead th")
            ]

            # Filas
            rows = []
            for tr in table.select("tbody tr"):
                tds = tr.select("td")
                if not tds:
                    continue

                row = []
                for td in tds:
                    if td.get("data-score") is not None:
                        row.append(normalize(td["data-score"]))
                    elif td.get("data-merit") is not None:
                        row.append(normalize(td["data-merit"]))
                    elif (span := td.find("span", class_="obfuscated")) and span.get("data-auth"):
                        row.append(decode_b64(span["data-auth"]))
                    else:
                        row.append(fix_encoding(normalize(td.get_text())))

                if any(row):
                    rows.append(row)

            if not rows:
                raise RuntimeError("Tabla vacÃ­a.")

            max_len = max(len(r) for r in rows)
            if len(headers) < max_len:
                headers += [f"col_{i+1}" for i in range(len(headers), max_len)]
            norm_rows = [r + [""] * (len(headers) - len(r)) for r in rows]

            df = pd.DataFrame(norm_rows, columns=headers)
            df.insert(0, "source_url", url)
            return df

        except Exception as exc:
            if attempt < retries:
                print(f"    [RETRY {attempt}] {exc}")
                time.sleep(2 * attempt)
            else:
                raise


def run_scraper(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[INFO] Obteniendo links de carreras...")
    links = get_career_links()
    print(f"[INFO] Carreras encontradas: {len(links)}")

    all_frames: list[pd.DataFrame] = []
    errors: list[dict] = []

    for idx, link in enumerate(links, start=1):
        print(f"[INFO] ({idx}/{len(links)}) {link}")
        try:
            df = scrape_career(link)
            tiene_puntaje = (
                "Puntaje" in df.columns
                and df["Puntaje"].str.strip().ne("").any()
            )
            print(f"    [OK] {len(df)} registros | Puntaje={'xx' if tiene_puntaje else 'yy'}")
            all_frames.append(df)
            time.sleep(0.3)
        except Exception as exc:
            print(f"    [ERROR] {exc}")
            errors.append({"url": link, "error": str(exc)})

    if not all_frames:
        raise RuntimeError("No se extrajo informacion de ninguna carrera.")

    final_df = pd.concat(all_frames, ignore_index=True)
    final_df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"\n[DONE] {output_path} | {len(final_df)} registros totales")

    if errors:
        ep = output_path.with_name("errores_scraping.csv")
        pd.DataFrame(errors).to_csv(ep, index=False, encoding="utf-8")
        print(f"[DONE] Errores: {ep}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper UNMSM 2026-II")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_scraper(output_path=args.output)
