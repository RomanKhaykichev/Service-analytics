# -*- coding: utf-8 -*-
"""Read RU and UZ seller-storage files and print size group column + unique values."""
import io
import pandas as pd
from pathlib import Path

BASE = Path(r"c:\Personal\Projects\Power_BI_start_UP\Выгрузки Uzum")
RU_PATH = BASE / "Выгрузки_ RU" / "seller-storage-report_4_shops_28.02.2026 11_15_16.xlsx"
UZ_PATH = BASE / "Выгрузки_Uzb" / "seller-storage-report_4_shops_28.02.2026 11_21_47.xlsx"


def safe_repr(s):
    return repr(s).replace("\\u02bb", "'").replace("\\u2019", "'")


def norm(s):
    return " ".join(str(s).replace("\n", " ").replace("\r", " ").strip().split()) if s else ""


def read_storage(path, label):
    print("=== ", label, " ", path.name[:60], " ===")
    xl = pd.ExcelFile(path, engine="openpyxl")
    sheet = xl.sheet_names[0]
    df = pd.read_excel(xl, sheet_name=sheet, header=1, engine="openpyxl")
    df.columns = [norm(c) for c in df.columns]
    print("All headers:", list(df.columns))
    found = False
    for col in df.columns:
        c = str(col).lower()
        if "габарит" in c or "gabarit" in c and "guruhi" in c or "o'lchov guruhi" in c or "olchov guruhi" in c:
            vals = df[col].dropna().astype(str).str.strip()
            vals = vals[vals != ""]
            uniq = sorted(vals.unique().tolist())
            print("Size group column:", repr(col))
            print("Unique values:", list(uniq))
            counts = df[col].value_counts()
            print("Value counts:", counts.to_dict())
            found = True
            break
    if not found:
        print("No size group column found")
    print()


if __name__ == "__main__":
    buf = io.StringIO()
    import sys
    old_stdout, sys.stdout = sys.stdout, buf
    try:
        read_storage(RU_PATH, "RU")
        read_storage(UZ_PATH, "UZ")
    finally:
        sys.stdout = old_stdout
    out_path = Path(__file__).parent / "size_group_comparison.txt"
    out_path.write_text(buf.getvalue(), encoding="utf-8")
    print("Written", out_path)
