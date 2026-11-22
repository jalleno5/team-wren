"""Write review reports with artifact paths relative to outputs/, on any machine."""
import json
from pathlib import Path
import re

OUTPUTS = Path(__file__).resolve().parent


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(item) for item in value]
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        normalized = re.sub(r"[/\\]+", "/", value)
        base = OUTPUTS.as_posix().rstrip("/") + "/"
        if normalized.casefold().startswith(base.casefold()):
            return normalized[len(base):]
        if normalized.startswith("outputs/"):
            return normalized[len("outputs/"):]
    return value


def write_report(path, value):
    Path(path).write_text(json.dumps(portable(value), indent=2) + "\n", encoding="utf-8")
