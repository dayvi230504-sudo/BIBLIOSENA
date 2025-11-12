from __future__ import annotations

import csv
from pathlib import Path
from typing import Tuple

import pandas as pd


SOURCE_FILENAME = "Material_bibliografico_final pr 2.csv"
OUTPUT_FILENAME = "libros_unificados.csv"


def detect_encoding_and_delimiter(path: Path) -> Tuple[str, str]:
    """Detectar codificación (UTF-8 o Latin-1) y delimitador (',' o ';')."""
    raw_bytes = path.read_bytes()
    detected_encoding = None
    decoded_text = ""

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded_text = raw_bytes.decode(encoding)
            detected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if detected_encoding is None:
        raise UnicodeDecodeError("utf-8", raw_bytes, 0, 1, "No se pudo decodificar el archivo en UTF-8 ni Latin-1")

    sample = "\n".join(decoded_text.splitlines()[:5]) or decoded_text
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        delimiter = dialect.delimiter
    except Exception:
        comma_count = sample.count(",")
        semicolon_count = sample.count(";")
        if semicolon_count > comma_count:
            delimiter = ";"

    return detected_encoding, delimiter


def load_dataframe(path: Path) -> pd.DataFrame:
    encoding, delimiter = detect_encoding_and_delimiter(path)
    df = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,
        keep_default_na=False,
        na_values=["", "NA", "NaN", None],
        engine="python",
    )
    return df


def ensure_required_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"Columnas requeridas faltantes en el CSV: {missing}")


def normalize_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )


def main() -> None:
    source_path = Path(SOURCE_FILENAME)
    if not source_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo '{SOURCE_FILENAME}' en el directorio actual.")

    df = load_dataframe(source_path)

    required = [
        "titulo",
        "autor",
        "cantidad_disponible",
        "stock",
    ]
    ensure_required_columns(df, required)

    numeric_cols = ["cantidad_disponible", "stock"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["unidades"] = df["cantidad_disponible"]
    unidades_vacias = df["unidades"].isna()
    if "stock" in df.columns:
        df.loc[unidades_vacias, "unidades"] = df.loc[unidades_vacias, "stock"]
    df["unidades"] = df["unidades"].fillna(0).astype(int)

    df["_titulo_norm"] = normalize_series(df["titulo"])
    df["_autor_norm"] = normalize_series(df["autor"])
    df["_orden_original"] = range(len(df))

    df_sorted = df.sort_values("_orden_original")

    agg_map: dict[str, str] = {
        col: "first" for col in df.columns if col not in {"unidades", "_titulo_norm", "_autor_norm", "_orden_original"}
    }
    agg_map["unidades"] = "sum"

    grouped = (
        df_sorted
        .groupby(["_titulo_norm", "_autor_norm"], as_index=False)
        .agg(agg_map)
    )

    grouped = grouped.drop(columns=["_titulo_norm", "_autor_norm", "_orden_original"], errors="ignore")
    grouped.to_csv(OUTPUT_FILENAME, index=False, encoding="utf-8-sig")

    print(f"Se generaron {len(grouped)} registros únicos en '{OUTPUT_FILENAME}'.")


if __name__ == "__main__":
    main()

