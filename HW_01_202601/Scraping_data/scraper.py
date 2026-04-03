from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://admision.unmsm.edu.pe/Website20262/A/A.html"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output" / "resultados_sanmarcos.xlsx"


def build_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def get_career_links(driver: webdriver.Chrome, wait: WebDriverWait) -> list[str]:
    driver.get(BASE_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    links: list[str] = []
    for a_tag in soup.select("a[href]"):
        href = (a_tag.get("href") or "").strip()
        if not href:
            continue

        full_url = urljoin(BASE_URL, href)
        if "/Website20262/A/" not in full_url:
            continue
        if not full_url.lower().endswith(".html"):
            continue

        links.append(full_url)

    unique_links = sorted(set(links))
    unique_links = [url for url in unique_links if url != BASE_URL]

    if not unique_links:
        raise RuntimeError("No se encontraron links de carreras en la pagina principal.")

    return unique_links


def extract_career_name(driver: webdriver.Chrome) -> str:
    for selector in ["h1", "h2", "h3", ".titulo", ".title"]:
        elems = driver.find_elements(By.CSS_SELECTOR, selector)
        for elem in elems:
            text = normalize_text(elem.text)
            if text:
                return text
    return "Carrera_sin_nombre"


def get_table_headers(table_element) -> list[str]:
    header_cells = table_element.find_elements(By.CSS_SELECTOR, "thead th")
    headers = [normalize_text(cell.text) for cell in header_cells]
    if any(headers):
        return headers

    first_row_cells = table_element.find_elements(By.CSS_SELECTOR, "tbody tr:first-child td")
    return [f"col_{idx + 1}" for idx, _ in enumerate(first_row_cells)]


def row_values_from_tr(row_element) -> list[str]:
    cells = row_element.find_elements(By.CSS_SELECTOR, "td")
    return [normalize_text(cell.text) for cell in cells]


def try_set_show_all_rows(driver: webdriver.Chrome) -> None:
    for selector in ["select[name$='_length']", "div.dataTables_length select", "select"]:
        selects = driver.find_elements(By.CSS_SELECTOR, selector)
        for sel in selects:
            try:
                options = Select(sel)
            except Exception:
                continue

            values = [o.get_attribute("value") for o in options.options]
            if "-1" in values:
                options.select_by_value("-1")
                time.sleep(1.0)
                return

            numeric_values = [int(v) for v in values if v and v.isdigit()]
            if numeric_values:
                options.select_by_value(str(max(numeric_values)))
                time.sleep(1.0)
                return


def click_next_page_if_possible(driver: webdriver.Chrome) -> bool:
    next_selectors = [
        "a.paginate_button.next",
        "#DataTables_Table_0_next",
        "li.paginate_button.next a",
    ]

    for selector in next_selectors:
        candidates = driver.find_elements(By.CSS_SELECTOR, selector)
        for btn in candidates:
            classes = (btn.get_attribute("class") or "").lower()
            if "disabled" in classes:
                return False

            parent_classes = ""
            try:
                parent = btn.find_element(By.XPATH, "..")
                parent_classes = (parent.get_attribute("class") or "").lower()
            except Exception:
                pass

            if "disabled" in parent_classes:
                return False

            if not btn.is_enabled():
                return False

            try:
                btn.click()
                time.sleep(0.8)
                return True
            except Exception:
                continue

    return False


def extract_all_rows_current_career(driver: webdriver.Chrome, wait: WebDriverWait) -> tuple[list[str], list[list[str]]]:
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
    table = driver.find_element(By.CSS_SELECTOR, "table")
    headers = get_table_headers(table)

    try_set_show_all_rows(driver)

    collected: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    while True:
        table = driver.find_element(By.CSS_SELECTOR, "table")
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

        for row in rows:
            values = row_values_from_tr(row)
            if not any(values):
                continue

            key = tuple(values)
            if key in seen:
                continue

            seen.add(key)
            collected.append(values)

        moved = click_next_page_if_possible(driver)
        if not moved:
            break

    return headers, collected


def rows_to_dataframe(career_name: str, source_url: str, headers: list[str], rows: Iterable[list[str]]) -> pd.DataFrame:
    clean_headers = [h if h else f"col_{i + 1}" for i, h in enumerate(headers)]
    matrix = [list(r) for r in rows]

    if not matrix:
        return pd.DataFrame(columns=["carrera", "source_url", *clean_headers])

    max_len = max(len(r) for r in matrix)
    if len(clean_headers) < max_len:
        clean_headers.extend([f"col_{i + 1}" for i in range(len(clean_headers), max_len)])

    normalized_rows = [r + [""] * (len(clean_headers) - len(r)) for r in matrix]
    df = pd.DataFrame(normalized_rows, columns=clean_headers)
    df.insert(0, "source_url", source_url)
    df.insert(0, "carrera", career_name)
    return df


def run_scraper(output_path: Path, headless: bool = True) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    driver = build_driver(headless=headless)
    wait = WebDriverWait(driver, 20)

    all_frames: list[pd.DataFrame] = []
    errors: list[dict[str, str]] = []

    try:
        career_links = get_career_links(driver, wait)
        print(f"[INFO] Carreras encontradas: {len(career_links)}")

        for idx, link in enumerate(career_links, start=1):
            print(f"[INFO] ({idx}/{len(career_links)}) Procesando: {link}")
            try:
                driver.get(link)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
                career_name = extract_career_name(driver)
                headers, rows = extract_all_rows_current_career(driver, wait)

                df = rows_to_dataframe(career_name, link, headers, rows)
                print(f"[OK] {career_name}: {len(df)} registros")
                all_frames.append(df)
            except (TimeoutException, NoSuchElementException) as exc:
                msg = f"No se pudo leer tabla en {link}: {exc}"
                print(f"[WARN] {msg}")
                errors.append({"url": link, "error": str(exc)})
            except Exception as exc:
                msg = f"Fallo inesperado en {link}: {exc}"
                print(f"[WARN] {msg}")
                errors.append({"url": link, "error": str(exc)})

    finally:
        driver.quit()

    if not all_frames:
        raise RuntimeError("No se pudo extraer informacion de ninguna carrera.")

    final_df = pd.concat(all_frames, ignore_index=True)
    final_df.to_excel(output_path, index=False)
    print(f"[DONE] Excel generado: {output_path}")
    print(f"[DONE] Total registros: {len(final_df)}")

    if errors:
        error_path = output_path.with_name("errores_scraping.csv")
        pd.DataFrame(errors).to_csv(error_path, index=False, encoding="utf-8")
        print(f"[DONE] Se guardo log de errores en: {error_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scraper resultados UNMSM 2026-II")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Ruta de salida del Excel (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Si se usa, abre Chrome en modo visible (no headless).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_scraper(output_path=args.output, headless=not args.show_browser)
