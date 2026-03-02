#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare RU vs UZ export files and print header mappings.
Use to build/update app/utils/column_mappings.py UZ_TO_RU_* dicts.

Usage:
  # From repo root, with Python path including apps/api:
  python tools/compare_ru_uz_import.py --ru-dir "C:\path\to\Выгрузки_ RU" --uz-dir "C:\path\to\Выгрузки_Uzb"

  # Or set env and run:
  set RU_DIR=C:\path\to\Выгрузки_ RU
  set UZ_DIR=C:\path\to\Выгрузки_Uzb
  python tools/compare_ru_uz_import.py

File naming: in each folder expect 4 files (or pass --suffix .xlsx):
  - seller / storage / Отчет по хранению
  - sells / sales / Отчет по продажам
  - expenses / Отчет по услугам
  - left_out_old / inventory_old / Остатки (старый)

Sheet: RU uses sheet names from SHEETS in imports.py; UZ may use first sheet if names differ.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


# File type -> (possible file names, sheet name for RU)
FILE_CONFIG = {
    "sales": (["sells.xlsx", "sales.xlsx", "Отчет по продажам.xlsx"], "Отчет по продажам"),
    "expenses": (["expenses.xlsx", "Отчет по услугам.xlsx"], "Отчет по услугам"),
    "storage": (["seller.xlsx", "storage.xlsx", "Отчет по хранению.xlsx"], "Отчет по хранению"),
    "leftout_old": (["left_out_old.xlsx", "inventory_old.xlsx", "Остатки (старый).xlsx"], None),  # first sheet
}


def norm(s: str) -> str:
    return " ".join(str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ").strip().split())


def get_headers_from_excel(path: Path, sheet_name: str | None, header_row: int = 1) -> list[str]:
    """Read first row (header) from Excel. If sheet_name is None, use first sheet."""
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheets = xl.sheet_names
    if not sheets:
        return []
    use_sheet = sheet_name if sheet_name and sheet_name in sheets else sheets[0]
    df = pd.read_excel(xl, sheet_name=use_sheet, header=header_row, nrows=0, engine="openpyxl")
    return [norm(c) for c in df.columns if c and not str(c).startswith("Unnamed")]


def find_file(folder: Path, names: list[str]) -> Path | None:
    for n in names:
        p = folder / n
        if p.exists():
            return p
    return None


# Заголовки колонки «Габаритная группа» в выгрузках RU и UZ (для сравнения значений)
SIZE_GROUP_HEADERS_RU = ("Габаритная группа",)
SIZE_GROUP_HEADERS_UZ = ("Gabarit guruhi", "O'lchov guruhi", "Olchov guruhi", "O'lchamlar guruhi")


def get_unique_values_for_column(path: Path, sheet_name: str | None, header_row: int, possible_headers: tuple[str, ...]) -> list[str]:
    """Прочитать Excel и вернуть уникальные непустые значения из колонки с одним из заголовков."""
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheets = xl.sheet_names
    if not sheets:
        return []
    use_sheet = sheet_name if sheet_name and sheet_name in sheets else sheets[0]
    df = pd.read_excel(xl, sheet_name=use_sheet, header=header_row, engine="openpyxl")
    df.columns = [norm(str(c)) if c else "" for c in df.columns]
    for h in possible_headers:
        if h in df.columns:
            vals = df[h].dropna().astype(str).str.strip()
            vals = vals[vals != ""]
            return sorted(vals.unique().tolist())
    return []


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare RU vs UZ export headers")
    ap.add_argument("--ru-dir", type=Path, default=Path(__file__).resolve().parent.parent / "samples" / "ru", help="Folder with RU Excel files")
    ap.add_argument("--uz-dir", type=Path, default=Path(__file__).resolve().parent.parent / "samples" / "uz", help="Folder with UZ Excel files")
    ap.add_argument("--print-mapping", action="store_true", help="Print Python dict snippet for UZ_TO_RU_*")
    ap.add_argument("--size-group-values", action="store_true", help="Compare unique values of Габаритная группа in RU vs UZ storage file")
    args = ap.parse_args()

    ru_dir: Path = args.ru_dir
    uz_dir: Path = args.uz_dir
    if not ru_dir.is_dir():
        print(f"RU folder not found: {ru_dir}", file=sys.stderr)
        sys.exit(1)
    if not uz_dir.is_dir():
        print(f"UZ folder not found: {uz_dir}", file=sys.stderr)
        sys.exit(1)

    print("File type | RU headers (normalized) | UZ headers (normalized) | Suggested UZ->RU")
    print("-" * 100)
    for file_type, (possible_names, sheet_name) in FILE_CONFIG.items():
        ru_path = find_file(ru_dir, possible_names)
        uz_path = find_file(uz_dir, possible_names)
        if not ru_path:
            print(f"{file_type}: no RU file (tried {possible_names})")
            continue
        if not uz_path:
            print(f"{file_type}: no UZ file (tried {possible_names})")
            continue
        ru_headers = get_headers_from_excel(ru_path, sheet_name)
        uz_headers = get_headers_from_excel(uz_path, sheet_name)
        print(f"\n--- {file_type} ---")
        print(f"  RU: {ru_headers}")
        print(f"  UZ: {uz_headers}")
        if len(ru_headers) == len(uz_headers) and ru_headers and uz_headers:
            print("  Suggested mapping (UZ -> RU):")
            for uz, ru in zip(uz_headers, ru_headers):
                print(f"    {uz!r} -> {ru!r}")
        elif ru_headers and uz_headers:
            # Build minimal mapping by position (assume same order)
            print("  (Column count differs; check order manually)")
            for i, uz in enumerate(uz_headers):
                ru = ru_headers[i] if i < len(ru_headers) else "???"
                print(f"    {uz!r} -> {ru!r}")

    if args.size_group_values:
        _, (storage_names, storage_sheet) = FILE_CONFIG["storage"]
        ru_path = find_file(ru_dir, storage_names)
        uz_path = find_file(uz_dir, storage_names)
        if ru_path and uz_path:
            ru_vals = get_unique_values_for_column(ru_path, storage_sheet, 1, SIZE_GROUP_HEADERS_RU)
            uz_vals = get_unique_values_for_column(uz_path, storage_sheet, 1, SIZE_GROUP_HEADERS_UZ)
            print("\n--- Габаритная группа: уникальные значения RU vs UZ ---")
            print(f"  RU (storage): {ru_vals}")
            print(f"  UZ (storage): {uz_vals}")
            print("  Цвета: СГТ/Кichik = зелёный, МГТ/O'rta = оранжевый, БГТ/Katta = красный.")
        else:
            print("\n  (storage file not found in one or both folders, skip size-group values)")

    print("\nDone. Update app/utils/column_mappings.py UZ_TO_RU_* with the UZ header strings (normalized lower).")


if __name__ == "__main__":
    main()
