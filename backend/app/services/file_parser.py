import json

import pandas as pd


def parse_text(raw_text: str) -> str:
    return raw_text.strip()


def parse_file(file_path: str, file_type: str) -> str:
    file_type = file_type.lower().lstrip(".")

    if file_type == "txt":
        return _parse_txt(file_path)
    elif file_type == "csv":
        return _parse_csv(file_path)
    elif file_type == "json":
        return _parse_json(file_path)
    elif file_type == "pdf":
        return _parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def _parse_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _parse_csv(file_path: str) -> str:
    df = pd.read_csv(file_path)
    lines = []
    for _, row in df.iterrows():
        parts = [str(v) for v in row.values if pd.notna(v)]
        lines.append(" ".join(parts))
    return "\n".join(lines)


def _parse_json(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                parts = [str(v) for v in item.values()]
                lines.append(" ".join(parts))
            else:
                lines.append(str(item))
        return "\n".join(lines)
    return json.dumps(data)


def _parse_pdf(file_path: str) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text.strip())
    return "\n".join(text_parts)
