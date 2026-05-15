from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]


def md(text: str):
    return nbf.v4.new_markdown_cell(dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(dedent(text).strip())


def write_notebook(path: Path, cells):
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    nb["cells"] = cells
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)


def raster_notebook():
    cells = [
        md(
            """
            # Territorial Digital Divide in Cusco

            This notebook measures territorial digital divide patterns in Cusco, Peru, by combining NASA nighttime lights with OSIPTEL mobile coverage density.

            Required local inputs:

            - `data/VNL_cusco_2025.tif`
            - `data/kernel_cobmovil2019_50m.tif`
            """
        ),
        md(
            """
            ## Step 0 - Environment setup

            Import required packages and print versions for reproducibility.
            """
        ),
        code(
            '''
            from pathlib import Path
            import math
            import warnings

            import numpy as np
            import pandas as pd
            import rasterio
            from rasterio.enums import Resampling
            from rasterio.warp import reproject
            import matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.colors import ListedColormap, BoundaryNorm
            from matplotlib.patches import Patch
            import scipy
            from scipy import ndimage, stats
            import seaborn as sns

            warnings.filterwarnings("ignore", category=RuntimeWarning)
            sns.set_theme(style="whitegrid")

            cwd = Path.cwd()
            if (cwd / "data").exists():
                PROJECT_ROOT = cwd
            elif (cwd.parent / "data").exists():
                PROJECT_ROOT = cwd.parent
            else:
                PROJECT_ROOT = cwd
            DATA_DIR = PROJECT_ROOT / "data"
            OUTPUT_DIR = PROJECT_ROOT / "output"
            OUTPUT_DIR.mkdir(exist_ok=True)

            VNL_PATH = DATA_DIR / "VNL_cusco_2025.tif"
            CONN_PATH = DATA_DIR / "kernel_cobmovil2019_50m.tif"

            versions = {
                "rasterio": rasterio.__version__,
                "numpy": np.__version__,
                "matplotlib": matplotlib.__version__,
                "scipy": scipy.__version__,
                "seaborn": sns.__version__,
                "pandas": pd.__version__,
            }
            versions
            '''
        ),
        md(
            """
            ## Step 1 - Raster loading and inspection

            For each raster, print CRS, dimensions, band count, NoData value, data type, bounds, pixel resolution, valid pixels, and value range.
            """
        ),
        code(
            '''
            def pixel_resolution_report(src):
                xres, yres = abs(src.transform.a), abs(src.transform.e)
                bounds = src.bounds
                center_lat = (bounds.bottom + bounds.top) / 2

                if src.crs and src.crs.is_geographic:
                    x_deg, y_deg = xres, yres
                    x_km = x_deg * 111.32 * math.cos(math.radians(center_lat))
                    y_km = y_deg * 110.57
                    return {
                        "resolution_degrees": (x_deg, y_deg),
                        "approx_resolution_km": (abs(x_km), abs(y_km)),
                    }

                x_km = xres / 1000
                y_km = yres / 1000
                x_deg = xres / (111_320 * max(math.cos(math.radians(center_lat)), 0.01))
                y_deg = yres / 110_570
                return {
                    "resolution_degrees_approx": (abs(x_deg), abs(y_deg)),
                    "resolution_km": (abs(x_km), abs(y_km)),
                }


            def read_clean_array(path):
                with rasterio.open(path) as src:
                    arr = src.read(1).astype("float32")
                    nodata = src.nodata
                    mask = np.zeros(arr.shape, dtype=bool)
                    if nodata is not None:
                        mask |= arr == nodata
                    mask |= ~np.isfinite(arr)
                    clean = arr.copy()
                    clean[mask] = np.nan
                    return clean, src.profile.copy()


            def inspect_raster(path, label):
                with rasterio.open(path) as src:
                    arr = src.read(1).astype("float32")
                    nodata = src.nodata
                    valid = np.isfinite(arr)
                    if nodata is not None:
                        valid &= arr != nodata
                    values = arr[valid]
                    report = {
                        "label": label,
                        "path": str(path),
                        "crs": str(src.crs),
                        "shape_height_width": (src.height, src.width),
                        "band_count": src.count,
                        "nodata": nodata,
                        "dtype": src.dtypes[0],
                        "bounds": src.bounds,
                        "pixel_resolution": pixel_resolution_report(src),
                        "valid_pixels": int(values.size),
                        "value_min": float(np.nanmin(values)),
                        "value_max": float(np.nanmax(values)),
                    }
                print(f"\\n--- {label} ---")
                for key, value in report.items():
                    print(f"{key}: {value}")
                return report


            vnl_report = inspect_raster(VNL_PATH, "VNL nighttime lights")
            conn_report = inspect_raster(CONN_PATH, "OSIPTEL mobile coverage")
            '''
        ),
        md(
            """
            ## Step 2 - Reprojection and grid alignment

            The connectivity raster is reprojected from EPSG:32719 to the exact VNL grid in EPSG:4326 using bilinear resampling.
            """
        ),
        code(
            '''
            vnl_raw, vnl_profile = read_clean_array(VNL_PATH)

            with rasterio.open(VNL_PATH) as vnl_src, rasterio.open(CONN_PATH) as conn_src:
                conn_aligned = np.zeros((vnl_src.height, vnl_src.width), dtype="float32")
                source = conn_src.read(1).astype("float32")
                if conn_src.nodata is not None:
                    source[source == conn_src.nodata] = np.nan
                source[~np.isfinite(source)] = np.nan

                reproject(
                    source=source,
                    destination=conn_aligned,
                    src_transform=conn_src.transform,
                    src_crs=conn_src.crs,
                    src_nodata=np.nan,
                    dst_transform=vnl_src.transform,
                    dst_crs=vnl_src.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )

            print("VNL shape:", vnl_raw.shape)
            print("Aligned connectivity shape:", conn_aligned.shape)
            assert vnl_raw.shape == conn_aligned.shape
            print("Grid alignment verified: both rasters share identical dimensions.")
            '''
        ),
        md(
            """
            ## Step 3 - Robust normalization

            Normalize both rasters with a 2nd-98th percentile scaling. Negative values, NoData, and non-finite values are replaced with zero before clipping.
            """
        ),
        code(
            '''
            def robust_normalize(arr, label):
                clean = arr.astype("float32").copy()
                clean[~np.isfinite(clean)] = 0
                clean[clean < 0] = 0
                p2, p98 = np.percentile(clean[clean > 0], [2, 98]) if np.any(clean > 0) else (0, 1)
                norm = (clean - p2) / (p98 - p2) if p98 > p2 else clean * 0
                norm = np.clip(norm, 0, 1).astype("float32")
                print(
                    f"{label}: min={norm.min():.4f}, max={norm.max():.4f}, "
                    f"mean={norm.mean():.4f}, std={norm.std():.4f}, p2={p2:.4f}, p98={p98:.4f}"
                )
                return norm


            vnl_norm = robust_normalize(vnl_raw, "VNL normalized")
            conn_norm = robust_normalize(conn_aligned, "Connectivity normalized")
            '''
        ),
        md(
            """
            ## Step 4 - Map 1: VNL nighttime lights

            Raw and normalized nighttime lights. Bright zones indicate urbanization and economic activity concentration.
            """
        ),
        code(
            '''
            def raster_extent(profile):
                transform = profile["transform"]
                height, width = profile["height"], profile["width"]
                left, top = transform * (0, 0)
                right, bottom = transform * (width, height)
                return [left, right, bottom, top]


            extent = raster_extent(vnl_profile)

            fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
            im0 = axes[0].imshow(np.nan_to_num(vnl_raw, nan=0), cmap="inferno", extent=extent)
            axes[0].set_title("Raw VNL nighttime lights")
            axes[0].set_xlabel("Longitude")
            axes[0].set_ylabel("Latitude")
            fig.colorbar(im0, ax=axes[0], shrink=0.85)

            im1 = axes[1].imshow(vnl_norm, cmap="inferno", extent=extent, vmin=0, vmax=1)
            axes[1].set_title("Normalized VNL nighttime lights")
            axes[1].set_xlabel("Longitude")
            axes[1].set_ylabel("Latitude")
            fig.colorbar(im1, ax=axes[1], shrink=0.85)

            plt.show()
            print("Observation: the brightest zones identify urban and economically active areas, used here as a proxy for population concentration.")
            '''
        ),
        md(
            """
            ## Step 5 - Map 2: Digital Divide Index and Total Digital Exclusion

            IBD captures areas with more light than connectivity. EDT captures areas with neither light nor connectivity.
            """
        ),
        code(
            '''
            ibd = (vnl_norm - conn_norm).astype("float32")
            edt = ((1 - vnl_norm) * (1 - conn_norm)).astype("float32")

            fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
            im0 = axes[0].imshow(ibd, cmap="RdYlGn_r", extent=extent, vmin=-1, vmax=1)
            axes[0].set_title("IBD: Digital Divide Index")
            axes[0].set_xlabel("Longitude")
            axes[0].set_ylabel("Latitude")
            fig.colorbar(im0, ax=axes[0], shrink=0.85)

            im1 = axes[1].imshow(edt, cmap="Purples", extent=extent, vmin=0, vmax=1)
            axes[1].set_title("EDT: Total Digital Exclusion")
            axes[1].set_xlabel("Longitude")
            axes[1].set_ylabel("Latitude")
            fig.colorbar(im1, ax=axes[1], shrink=0.85)
            plt.show()

            print("IBD interpretation: red areas have higher nighttime light than connectivity and indicate active digital divide.")
            print("EDT interpretation: darker purple areas have both low nighttime light and low connectivity, indicating total exclusion.")
            '''
        ),
        md(
            """
            ## Step 6 - Map 3: Intervention priority

            Priority levels combine population proxy intensity and low connectivity.
            """
        ),
        code(
            '''
            priority = np.zeros(vnl_norm.shape, dtype="uint8")
            priority[(vnl_norm >= 0.10) & (conn_norm < 0.25)] = 1
            priority[(vnl_norm >= 0.15) & (conn_norm < 0.15)] = 2
            priority[(vnl_norm >= 0.30) & (conn_norm < 0.10)] = 3

            priority_cmap = ListedColormap(["#f7f7f7", "#ffd166", "#f77f00", "#d62828"])
            priority_norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], priority_cmap.N)

            fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
            ax.imshow(priority, cmap=priority_cmap, norm=priority_norm, extent=extent)
            ax.set_title("Intervention priority")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(
                handles=[
                    Patch(color="#ffd166", label="P1 Medium"),
                    Patch(color="#f77f00", label="P2 High"),
                    Patch(color="#d62828", label="P3 Critical"),
                ],
                loc="lower left",
            )
            plt.show()

            total_pixels = priority.size
            for level, name in [(1, "P1 Medium"), (2, "P2 High"), (3, "P3 Critical")]:
                count = int((priority == level).sum())
                print(f"{name}: {count:,} pixels ({count / total_pixels * 100:.2f}% of total area)")
            '''
        ),
        md(
            """
            ## Step 7 - Map 4: Social Exclusion Risk

            Risk is based on total exclusion and low light, then smoothed with a Gaussian filter to show regional patterns.
            """
        ),
        code(
            '''
            risk_raw = edt * (1 - vnl_norm)
            risk_raw = robust_normalize(risk_raw, "Social exclusion risk")
            risk_smooth = ndimage.gaussian_filter(risk_raw, sigma=5)

            p75, p90 = np.percentile(risk_raw, [75, 90])

            fig, axes = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
            im0 = axes[0].imshow(risk_raw, cmap="hot_r", extent=extent, vmin=0, vmax=1)
            axes[0].set_title("Raw social exclusion risk")
            axes[0].set_xlabel("Longitude")
            axes[0].set_ylabel("Latitude")
            fig.colorbar(im0, ax=axes[0], shrink=0.85)

            im1 = axes[1].imshow(risk_smooth, cmap="hot_r", extent=extent, vmin=0, vmax=1)
            axes[1].set_title("Smoothed social exclusion risk")
            axes[1].set_xlabel("Longitude")
            axes[1].set_ylabel("Latitude")
            fig.colorbar(im1, ax=axes[1], shrink=0.85)
            plt.show()

            print(f"Risk threshold p75: {p75:.4f}")
            print(f"Risk threshold p90: {p90:.4f}")
            '''
        ),
        md(
            """
            ## Step 8 - Territorial classification

            Apply a 2 by 2 classification using thresholds VNL >= 0.15 and Connectivity >= 0.15.
            """
        ),
        code(
            '''
            classification = np.zeros(vnl_norm.shape, dtype="uint8")
            urban = vnl_norm >= 0.15
            connected = conn_norm >= 0.15
            classification[urban & connected] = 1
            classification[urban & ~connected] = 2
            classification[~urban & connected] = 3
            classification[~urban & ~connected] = 4

            class_info = {
                1: {"name": "Urban Connected", "color": "#2ca25f"},
                2: {"name": "Urban Divide", "color": "#de2d26"},
                3: {"name": "Rural Connected", "color": "#3182bd"},
                4: {"name": "Critical Divide", "color": "#756bb1"},
            }
            class_cmap = ListedColormap([class_info[i]["color"] for i in [1, 2, 3, 4]])
            class_norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], class_cmap.N)

            fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
            ax.imshow(classification, cmap=class_cmap, norm=class_norm, extent=extent)
            ax.set_title("Territorial digital divide classification")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(
                handles=[Patch(color=class_info[i]["color"], label=class_info[i]["name"]) for i in [1, 2, 3, 4]],
                loc="lower left",
            )
            plt.show()

            pixel_width_deg = abs(vnl_profile["transform"].a)
            pixel_height_deg = abs(vnl_profile["transform"].e)
            mean_lat = (vnl_profile["transform"].f + (vnl_profile["transform"].f + vnl_profile["height"] * vnl_profile["transform"].e)) / 2
            pixel_area_km2 = (pixel_width_deg * 111.32 * math.cos(math.radians(mean_lat))) * (pixel_height_deg * 110.57)

            class_rows = []
            for class_id in [1, 2, 3, 4]:
                count = int((classification == class_id).sum())
                class_rows.append(
                    {
                        "class": class_id,
                        "name": class_info[class_id]["name"],
                        "pixel_count": count,
                        "percentage_total_area": count / classification.size * 100,
                        "approx_area_km2": count * pixel_area_km2,
                    }
                )

            class_df = pd.DataFrame(class_rows)
            display(class_df)
            '''
        ),
        md(
            """
            ## Step 9 - Statistical summary

            Compute grouped descriptive statistics, Pearson correlation, KDE distributions, Welch t-test, and Cohen's d.
            """
        ),
        code(
            '''
            sample_step = 40
            flat_df = pd.DataFrame(
                {
                    "vnl": vnl_norm.ravel(),
                    "connectivity": conn_norm.ravel(),
                    "ibd": ibd.ravel(),
                    "class": classification.ravel(),
                }
            )
            flat_df["class_name"] = flat_df["class"].map({k: v["name"] for k, v in class_info.items()})

            summary = flat_df.groupby("class_name")[["vnl", "connectivity", "ibd"]].agg(["mean", "std", "min", "max"])
            display(summary)

            sample_vnl = vnl_norm[::sample_step, ::sample_step].ravel()
            sample_conn = conn_norm[::sample_step, ::sample_step].ravel()
            pearson_r, pearson_p = stats.pearsonr(sample_vnl, sample_conn)
            print(f"Pearson correlation, every {sample_step}th pixel: r={pearson_r:.4f}, p={pearson_p:.4g}")

            plt.figure(figsize=(10, 6))
            palette = dict(zip(flat_df["class_name"].dropna().unique(), sns.color_palette("tab10")))
            for class_name, class_data in flat_df.iloc[::sample_step].groupby("class_name"):
                if len(class_data) < 5:
                    continue
                sns.kdeplot(
                    class_data["vnl"],
                    label=f"{class_name} - VNL",
                    color=palette[class_name],
                    linestyle="-",
                    common_norm=False,
                )
                sns.kdeplot(
                    class_data["connectivity"],
                    label=f"{class_name} - Connectivity",
                    color=palette[class_name],
                    linestyle="--",
                    common_norm=False,
                )
            plt.title("KDE distributions by class")
            plt.xlabel("Normalized value")
            plt.ylabel("Density")
            plt.legend(fontsize=8)
            plt.show()

            class1_vnl = flat_df.loc[flat_df["class"] == 1, "vnl"].iloc[::sample_step]
            class4_vnl = flat_df.loc[flat_df["class"] == 4, "vnl"].iloc[::sample_step]
            t_stat, p_value = stats.ttest_ind(class1_vnl, class4_vnl, equal_var=False)
            pooled_sd = math.sqrt(((class1_vnl.std(ddof=1) ** 2) + (class4_vnl.std(ddof=1) ** 2)) / 2)
            cohen_d = (class1_vnl.mean() - class4_vnl.mean()) / pooled_sd if pooled_sd else np.nan

            print(f"Welch t-test Class 1 vs Class 4 VNL: t={t_stat:.4f}, p={p_value:.4g}, Cohen d={cohen_d:.4f}")
            '''
        ),
        md(
            """
            ## Step 10 - Export deliverables

            Export processed rasters aligned to the VNL grid and save the final dashboard figure.
            """
        ),
        code(
            '''
            def export_raster(path, array, dtype="float32", nodata=None):
                profile = vnl_profile.copy()
                profile.update(
                    driver="GTiff",
                    count=1,
                    dtype=dtype,
                    compress="lzw",
                    nodata=nodata,
                )
                with rasterio.open(path, "w", **profile) as dst:
                    dst.write(array.astype(dtype), 1)
                print(f"Saved {path}")


            export_raster(OUTPUT_DIR / "vnl_norm.tif", vnl_norm, "float32")
            export_raster(OUTPUT_DIR / "conn_norm.tif", conn_norm, "float32")
            export_raster(OUTPUT_DIR / "ibd_brecha_digital.tif", ibd, "float32")
            export_raster(OUTPUT_DIR / "clasificacion_brecha.tif", classification, "uint8", nodata=0)

            fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
            panels = [
                (vnl_norm, "VNL normalized", "inferno", 0, 1),
                (conn_norm, "Connectivity normalized", "viridis", 0, 1),
                (ibd, "IBD digital divide", "RdYlGn_r", -1, 1),
                (edt, "EDT total exclusion", "Purples", 0, 1),
                (priority, "Intervention priority", priority_cmap, None, None),
                (risk_smooth, "Smoothed exclusion risk", "hot_r", 0, 1),
            ]
            for ax, (arr, title, cmap, vmin, vmax) in zip(axes.ravel(), panels):
                im = ax.imshow(arr, cmap=cmap, extent=extent, vmin=vmin, vmax=vmax)
                ax.set_title(title)
                ax.set_xlabel("Longitude")
                ax.set_ylabel("Latitude")
                fig.colorbar(im, ax=ax, shrink=0.75)
            dashboard_path = OUTPUT_DIR / "dashboard_brecha_digital.png"
            fig.savefig(dashboard_path, dpi=150)
            plt.show()
            print(f"Saved {dashboard_path}")
            '''
        ),
    ]
    return cells


def rag_notebook():
    cells = [
        md(
            """
            # Beca 18 RAG Chatbot

            This notebook builds an end-to-end RAG pipeline over the official Beca 18 regulation PDF. The chatbot answers only from retrieved source fragments and refuses to answer when the document does not contain enough evidence.
            """
        ),
        md(
            """
            ## Step 0 - Setup

            Install dependencies, load the Gemini API key from `.env`, and print package versions.
            """
        ),
        code(
            '''
            from pathlib import Path
            import os
            import re
            import time
            import textwrap
            import importlib.metadata as metadata
            from typing import List, Dict, Any

            import chromadb
            from dotenv import load_dotenv
            from google import genai
            from google.genai import types
            import ipywidgets as widgets
            from IPython.display import display, Markdown, clear_output
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from pypdf import PdfReader
            import tiktoken
            from tqdm.auto import tqdm

            cwd = Path.cwd()
            if (cwd / "data").exists():
                PROJECT_ROOT = cwd
            elif (cwd.parent / "data").exists():
                PROJECT_ROOT = cwd.parent
            else:
                PROJECT_ROOT = cwd
            DATA_DIR = PROJECT_ROOT / "data"
            PDF_PATH = DATA_DIR / "beca18_reglamento.pdf"
            CHROMA_PATH = PROJECT_ROOT / "chroma_db_beca18"

            load_dotenv(PROJECT_ROOT / ".env")
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
            if GEMINI_API_KEY:
                print("GEMINI_API_KEY loaded from .env.")
            else:
                print("GEMINI_API_KEY not found. Offline extraction/chunking cells can run, but embeddings and generation will be skipped.")

            packages = [
                "pypdf",
                "tiktoken",
                "langchain-text-splitters",
                "google-genai",
                "chromadb",
                "ipywidgets",
                "tqdm",
                "python-dotenv",
            ]
            versions = {pkg: metadata.version(pkg) for pkg in packages}
            versions
            '''
        ),
        md(
            """
            ## Step 1 - PDF text extraction

            Extract text page by page, add `[PAGE N]` markers, lightly clean whitespace, and print total character and word counts.
            """
        ),
        code(
            '''
            def clean_page_text(text: str) -> str:
                text = text or ""
                text = re.sub(r"\\r", "\\n", text)
                text = re.sub(r"(?<!\\n)\\n(?!\\n)", " ", text)
                text = re.sub(r"[ \\t]+", " ", text)
                text = re.sub(r"\\n{3,}", "\\n\\n", text)
                return text.strip()


            reader = PdfReader(str(PDF_PATH))
            page_texts = []
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = clean_page_text(page.extract_text())
                page_texts.append(f"[PAGE {page_number}]\\n{page_text}")

            document_text = "\\n\\n".join(page_texts)
            char_count = len(document_text)
            word_count = len(re.findall(r"\\b\\w+\\b", document_text))
            print(f"Pages: {len(page_texts)}")
            print(f"Total characters: {char_count:,}")
            print(f"Total words: {word_count:,}")
            print(document_text[:1000])
            '''
        ),
        md(
            """
            ## Step 2 - Tokenization and chunking justification

            Gemini embedding requests support an 8,192-token input limit. A 400-token chunk with 60-token overlap is small enough to preserve retrieval precision, large enough to carry legal context, and safely below the embedding limit. The overlap reduces boundary loss when requirements, obligations, or sanctions are split across pages or paragraphs.
            """
        ),
        code(
            '''
            encoding = tiktoken.get_encoding("cl100k_base")

            def count_tokens(text: str) -> int:
                return len(encoding.encode(text))


            total_tokens = count_tokens(document_text)
            print(f"Total tokens with cl100k_base: {total_tokens:,}")

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,
                chunk_overlap=60,
                separators=["\\n\\n", "\\n", ". ", " "],
                length_function=count_tokens,
            )

            raw_chunks = splitter.split_text(document_text)

            def page_from_chunk(text: str):
                match = re.search(r"\\[PAGE (\\d+)\\]", text)
                return int(match.group(1)) if match else None


            chunks = []
            for idx, text in enumerate(raw_chunks):
                chunks.append(
                    {
                        "id": f"beca18-{idx:04d}",
                        "text": text,
                        "metadata": {
                            "document": "Resolucion Directoral Ejecutiva N. 033-2026-MINEDU/VMGI-PRONABEC",
                            "topic": "Beca 18 regulations",
                            "language": "Spanish",
                            "page": page_from_chunk(text) or -1,
                        },
                    }
                )

            avg_chars = sum(len(chunk["text"]) for chunk in chunks) / len(chunks)
            print(f"Total chunks: {len(chunks):,}")
            print(f"Average chunk length: {avg_chars:.1f} characters")
            print(chunks[0])
            '''
        ),
        md(
            """
            ## Step 3 - Embeddings

            Use `gemini-embedding-001` with task-specific embedding modes and exponential backoff for free-tier rate limits.
            """
        ),
        code(
            '''
            EMBEDDING_MODEL = "gemini-embedding-001"
            GENERATION_MODEL = "gemini-2.5-flash"


            def _embed_with_retry(texts: List[str], task_type: str, batch_size: int = 16, max_retries: int = 6) -> List[List[float]]:
                if genai_client is None:
                    raise ValueError("GEMINI_API_KEY is required for embeddings. Create .env from .env.example.")
                embeddings = []
                for start in tqdm(range(0, len(texts), batch_size), desc=f"Embedding {task_type}"):
                    batch = texts[start : start + batch_size]
                    for attempt in range(max_retries):
                        try:
                            response = genai_client.models.embed_content(
                                model=EMBEDDING_MODEL,
                                contents=batch,
                                config=types.EmbedContentConfig(
                                    task_type=task_type,
                                    output_dimensionality=768,
                                ),
                            )
                            embeddings.extend([item.values for item in response.embeddings])
                            break
                        except Exception as exc:
                            if attempt == max_retries - 1:
                                raise
                            sleep_seconds = min(60, 2 ** attempt)
                            print(f"Embedding retry after error: {exc}. Sleeping {sleep_seconds}s.")
                            time.sleep(sleep_seconds)
                    time.sleep(1.1)
                return embeddings


            def embed_documents(texts: List[str]) -> List[List[float]]:
                return _embed_with_retry(texts, task_type="RETRIEVAL_DOCUMENT")


            def embed_query(text: str) -> List[float]:
                return _embed_with_retry([text], task_type="RETRIEVAL_QUERY", batch_size=1)[0]
            '''
        ),
        md(
            """
            ## Step 4 - Vector database

            Create a persistent ChromaDB collection with cosine distance and idempotent indexing.
            """
        ),
        code(
            '''
            chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            collection = chroma_client.get_or_create_collection(
                name="beca18_reglamento",
                metadata={"hnsw:space": "cosine"},
            )

            existing_count = collection.count()
            if existing_count > 0:
                print(f"Collection already has {existing_count:,} documents. Skipping embedding.")
            elif genai_client is None:
                print("Collection is empty, but GEMINI_API_KEY is missing. Skipping embedding/indexing.")
            else:
                texts = [chunk["text"] for chunk in chunks]
                ids = [chunk["id"] for chunk in chunks]
                metadatas = [chunk["metadata"] for chunk in chunks]
                embeddings = embed_documents(texts)
                collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
                print("Indexing completed.")

            print(f"Stored documents: {collection.count():,}")
            '''
        ),
        md(
            """
            ## Step 5 - Semantic search

            Query ChromaDB with a Gemini query embedding and return text, metadata, and distance.
            """
        ),
        code(
            '''
            def semantic_search(question: str, k: int = 5) -> List[Dict[str, Any]]:
                question_embedding = embed_query(question)
                result = collection.query(
                    query_embeddings=[question_embedding],
                    n_results=k,
                    include=["documents", "metadatas", "distances"],
                )
                hits = []
                for text, metadata_item, distance in zip(
                    result["documents"][0],
                    result["metadatas"][0],
                    result["distances"][0],
                ):
                    hits.append({"text": text, "metadata": metadata_item, "distance": distance})
                return hits


            sample_question = "Cuales son los requisitos para postular a Beca 18?"
            if genai_client is None or collection.count() == 0:
                print("Skipping semantic search test until GEMINI_API_KEY is available and the collection is indexed.")
            else:
                sample_hits = semantic_search(sample_question, k=3)
                for idx, hit in enumerate(sample_hits, start=1):
                    print(f"\\nResult {idx} | distance={hit['distance']:.4f} | page={hit['metadata'].get('page')}")
                    print(textwrap.shorten(hit["text"].replace("\\n", " "), width=500))
            '''
        ),
        md(
            """
            ## Step 6 - Grounded generation

            Generate answers using only retrieved context. If the context is insufficient, the answer must decline.
            """
        ),
        code(
            '''
            SYSTEM_PROMPT = """
            You are a grounded assistant for the official Beca 18 regulation.
            Answer exclusively from the retrieved context.
            Cite page numbers when they are available.
            If the retrieved context is insufficient, respond exactly:
            "The document does not contain information about this topic."
            Do not use outside knowledge.
            """


            def format_context(hits: List[Dict[str, Any]]) -> str:
                blocks = []
                for idx, hit in enumerate(hits, start=1):
                    page = hit["metadata"].get("page", "unknown")
                    blocks.append(
                        f"[SOURCE {idx} | PAGE {page} | DISTANCE {hit['distance']:.4f}]\\n{hit['text']}"
                    )
                return "\\n\\n".join(blocks)


            def answer_with_context(question: str, k: int = 5) -> Dict[str, Any]:
                if genai_client is None:
                    raise ValueError("GEMINI_API_KEY is required for grounded generation. Create .env from .env.example.")
                hits = semantic_search(question, k=k)
                context = format_context(hits)
                prompt = f"Question: {question}\\n\\nRetrieved context:\\n{context}\\n\\nAnswer:"
                response = genai_client.models.generate_content(
                    model=GENERATION_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0,
                    ),
                )
                return {"answer": response.text, "sources": hits}


            test_questions = [
                "Cuales son los requisitos de elegibilidad para Beca 18?",
                "Que modalidades de beca se mencionan?",
                "Cual es el monto de la subvencion mensual?",
                "Cuales son las obligaciones de los estudiantes becarios?",
                "En que condiciones se puede perder la beca?",
                "Cual es la mejor receta para preparar ceviche?",
            ]

            if genai_client is None or collection.count() == 0:
                print("Skipping grounded generation tests until GEMINI_API_KEY is available and the collection is indexed.")
            else:
                for question in test_questions:
                    result = answer_with_context(question, k=5)
                    print("\\n" + "=" * 100)
                    print("QUESTION:", question)
                    print("ANSWER:", result["answer"])
            '''
        ),
        md(
            """
            ## Step 7 - Interactive chat interface

            Ask questions, control top-k retrieval, and inspect expandable source fragments.
            """
        ),
        code(
            '''
            question_box = widgets.Text(
                value="",
                placeholder="Escribe una pregunta sobre Beca 18",
                description="Pregunta:",
                layout=widgets.Layout(width="80%"),
            )
            ask_button = widgets.Button(description="Ask", button_style="primary")
            clear_button = widgets.Button(description="Clear")
            k_slider = widgets.IntSlider(value=5, min=1, max=10, step=1, description="k")
            output_area = widgets.Output()


            def render_sources(hits):
                children = []
                titles = []
                for idx, hit in enumerate(hits, start=1):
                    page = hit["metadata"].get("page", "unknown")
                    distance = hit["distance"]
                    source_output = widgets.Output()
                    with source_output:
                        print(hit["text"])
                    children.append(source_output)
                    titles.append(f"Source {idx} | page {page} | distance {distance:.4f}")
                accordion = widgets.Accordion(children=children)
                for idx, title in enumerate(titles):
                    accordion.set_title(idx, title)
                return accordion


            def on_ask(_):
                question = question_box.value.strip()
                if not question:
                    return
                with output_area:
                    clear_output()
                    print("Searching and generating answer...")
                    result = answer_with_context(question, k=k_slider.value)
                    clear_output()
                    display(Markdown(result["answer"]))
                    display(render_sources(result["sources"]))


            def on_clear(_):
                question_box.value = ""
                with output_area:
                    clear_output()


            ask_button.on_click(on_ask)
            clear_button.on_click(on_clear)

            if genai_client is None or collection.count() == 0:
                display(Markdown("Create `.env` with `GEMINI_API_KEY`, rerun the notebook, and the chat interface will answer from indexed sources."))

            display(widgets.VBox([
                widgets.HBox([question_box, ask_button, clear_button]),
                k_slider,
                output_area,
            ]))
            '''
        ),
    ]
    return cells


if __name__ == "__main__":
    write_notebook(
        ROOT / "raster-digital-divide" / "notebooks" / "digital_divide_cusco.ipynb",
        raster_notebook(),
    )
    write_notebook(
        ROOT / "beca18-rag-chatbot" / "notebooks" / "beca18_rag_chatbot.ipynb",
        rag_notebook(),
    )
    print("HW3 notebooks generated.")
