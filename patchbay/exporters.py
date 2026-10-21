import csv
import io
from pathlib import Path


def to_csv(plan: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["sheet", "piece_id", "instance", "x_mm", "y_mm", "width_mm", "height_mm", "rotated"])
    for item in sorted(plan["placements"], key=lambda row: (row["sheet"], row["y"], row["x"], row["piece_id"])):
        writer.writerow([item["sheet"], item["piece_id"], item["instance"], item["x"], item["y"], item["width"], item["height"], str(item["rotated"]).lower()])
    return output.getvalue()


def write_outputs(outputs: list[tuple[Path, str]]) -> None:
    paths = [path.expanduser().resolve() for path, _ in outputs]
    if len(set(paths)) != len(paths):
        raise ValueError("Path output JSON dan CSV harus berbeda.")
    if any(path.exists() for path in paths):
        raise ValueError("Output sudah ada; gunakan nama baru agar tidak tertimpa.")
    created = []
    try:
        for path, (_, content) in zip(paths, outputs):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="") as stream:
                created.append(path)
                stream.write(content)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
