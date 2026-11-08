"""Exportação local mínima do último relatório; histórico SQLite previsto na Fase 2."""

import json
import os
import tempfile
from pathlib import Path

from update_sentinel.core.models import Report


def state_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    if not base.is_absolute():
        base = Path.home() / ".local/state"
    return base / "updatesentinel" / "last-report.json"


def save_report(report: Report, path: Path | None = None) -> None:
    target = path or state_path()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Escrita atômica e permissões restritas, inclusive se houver falha durante gravação.
    descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".report-")
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(report.to_dict(), stream, ensure_ascii=False, indent=2)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def load_report(path: Path | None = None) -> dict:
    return json.loads((path or state_path()).read_text())


def render_report(data: dict) -> str:
    lines = ["UpdateSentinel — diagnóstico somente leitura", data["created_at"]]
    if data["demo"]:
        lines.append("DEMONSTRAÇÃO — DADOS SIMULADOS")
    diagnostic = data["diagnostic"]
    lines.extend(
        [diagnostic["distribution"], f"Kernel: {diagnostic['kernel']}", data["update_status"], ""]
    )
    for package in data["packages"]:
        lines.extend(
            [
                f"{package['name']}: {package['installed']} → {package['available']}",
                f"  {package['description']}",
                f"  {package['category']}: {package['components']}",
                f"  Dependências locais: {package['dependencies']}",
                f"  {package['changes']}",
            ]
        )
    lines.extend(["", "Diagnóstico:", json.dumps(diagnostic, ensure_ascii=False, indent=2)])
    for finding in data["findings"]:
        lines.extend(
            [
                "",
                f"[{finding['severity']}] {finding['component']}: {finding['evidence']}",
                f"Origem: {finding['origin']} · Confiança: {finding['confidence']}",
                f"Recomendação: {finding['recommendation']}",
                f"Limitações: {finding['limitations']}",
            ]
        )
    lines.extend(["", *data["limitations"]])
    return "\n".join(lines)
