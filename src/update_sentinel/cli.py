"""Entrada da CLI; Qt só é importado quando solicitado."""

import argparse
import json
import sys

from update_sentinel.core.reports import load_report, render_report, save_report
from update_sentinel.core.service import ScanService, demo_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UpdateSentinel — diagnóstico sem privilégios")
    parser.add_argument("command", choices=["gui", "scan", "doctor", "report", "demo"])
    parser.add_argument("--json", action="store_true", help="Saída estruturada")
    parser.add_argument("--no-save", action="store_true", help="Não gravar último relatório")
    args = parser.parse_args(argv)
    if args.command == "gui":
        try:
            from update_sentinel.ui.app import launch
        except ImportError:
            print('Interface indisponível. Instale com: pip install -e ".[gui]"', file=sys.stderr)
            return 1
        return launch()
    try:
        if args.command == "report":
            data = load_report()
        else:
            report = (
                demo_report()
                if args.command == "demo"
                else ScanService().scan(updates=args.command == "scan")
            )
            data = report.to_dict()
            if not args.no_save and not report.demo:
                try:
                    save_report(report)
                except OSError:
                    print(
                        "Não foi possível salvar o relatório; análise preservada na saída.",
                        file=sys.stderr,
                    )
        print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else render_report(data))
        return (
            2
            if args.command == "scan"
            and (data["update_status"].startswith(("Falha", "Distribuição não suportada")))
            else 0
        )
    except FileNotFoundError:
        print("Nenhum relatório salvo. Execute updatesentinel scan ou doctor.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Não foi possível ler os dados ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
