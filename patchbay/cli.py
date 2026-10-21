import argparse
from dataclasses import asdict
import json
from pathlib import Path

from patchbay.exporters import to_csv, write_outputs
from patchbay.model import parse_spec
from patchbay.packing import build_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="patch-bay", description="Rencanakan potongan quilt persegi panjang dalam milimeter.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "plan"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        if name == "plan":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--csv", type=Path)
    args = parser.parse_args(argv)
    try:
        path = args.input.expanduser()
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Spesifikasi melebihi batas 1 MiB.")
        spec = parse_spec(json.loads(path.read_text(encoding="utf-8")))
        if args.command == "validate":
            print(json.dumps({"title": spec.title, "stock": asdict(spec.stock), "piece_types": len(spec.pieces), "total_pieces": sum(piece.quantity for piece in spec.pieces)}, ensure_ascii=False, indent=2))
        else:
            plan = build_plan(spec)
            outputs = [(args.output, json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n")]
            if args.csv:
                outputs.append((args.csv, to_csv(plan)))
            write_outputs(outputs)
            print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f"patch-bay: error: {error}\n")
