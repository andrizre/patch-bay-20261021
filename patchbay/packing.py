from dataclasses import asdict

from patchbay.model import Spec


def build_plan(spec: Spec) -> dict:
    stock = spec.stock
    items = [
        (piece, instance, piece.width + 2 * spec.seam, piece.height + 2 * spec.seam)
        for piece in spec.pieces for instance in range(1, piece.quantity + 1)
    ]
    items.sort(key=lambda item: (-max(item[2:]), -item[2] * item[3], item[0].id, item[1]))
    sheets = []
    placements = []
    initial = (stock.margin, stock.margin, stock.width - 2 * stock.margin + stock.gap, stock.height - 2 * stock.margin + stock.gap)
    for piece, instance, width, height in items:
        orientations = [(width, height, False)]
        if piece.rotate and width != height:
            orientations.append((height, width, True))
        best = None
        for sheet_id, free in enumerate(sheets):
            for region_id, (_, _, region_w, region_h) in enumerate(free):
                for cut_w, cut_h, rotated in orientations:
                    footprint_w, footprint_h = cut_w + stock.gap, cut_h + stock.gap
                    if footprint_w <= region_w and footprint_h <= region_h:
                        score = (region_w * region_h - footprint_w * footprint_h, min(region_w - footprint_w, region_h - footprint_h), sheet_id, region_id, rotated)
                        candidate = (score, sheet_id, region_id, cut_w, cut_h, rotated)
                        if best is None or score < best[0]:
                            best = candidate
        if best is None:
            sheets.append([initial])
            sheet_id, region_id = len(sheets) - 1, 0
            fitting = [(w, h, rotated) for w, h, rotated in orientations if w + stock.gap <= initial[2] and h + stock.gap <= initial[3]]
            if not fitting:
                raise ValueError(f"Potongan {piece.id} tidak muat pada stok.")
            cut_w, cut_h, rotated = min(fitting, key=lambda value: (min(initial[2] - value[0] - stock.gap, initial[3] - value[1] - stock.gap), value[2]))
        else:
            _, sheet_id, region_id, cut_w, cut_h, rotated = best
        x, y, region_w, region_h = sheets[sheet_id].pop(region_id)
        footprint_w, footprint_h = cut_w + stock.gap, cut_h + stock.gap
        if region_w > footprint_w:
            sheets[sheet_id].append((x + footprint_w, y, region_w - footprint_w, footprint_h))
        if region_h > footprint_h:
            sheets[sheet_id].append((x, y + footprint_h, region_w, region_h - footprint_h))
        placements.append({"sheet": sheet_id + 1, "piece_id": piece.id, "instance": instance, "x": x, "y": y, "width": cut_w, "height": cut_h, "rotated": rotated})
    cut_area = sum(item["width"] * item["height"] for item in placements)
    stock_area = len(sheets) * stock.width * stock.height
    result = {
        "title": spec.title, "unit": "mm", "stock": asdict(stock), "seam": spec.seam,
        "placements": placements,
        "summary": {"sheets": len(sheets), "placements": len(placements), "cut_area_mm2": cut_area, "stock_area_mm2": stock_area, "utilisation_ratio": cut_area / stock_area},
    }
    validate_plan(spec, result)
    return result


def validate_plan(spec: Spec, plan: dict) -> None:
    expected = {(piece.id, instance): piece for piece in spec.pieces for instance in range(1, piece.quantity + 1)}
    seen = set()
    stock = spec.stock
    placements = plan.get("placements")
    if not isinstance(placements, list) or len(placements) != len(expected):
        raise ValueError("Jumlah potongan pada rencana tidak cocok.")
    sheet_ids = set()
    for item in placements:
        if not isinstance(item, dict) or any(type(item.get(key)) is not int for key in ("sheet", "instance", "x", "y", "width", "height")):
            raise ValueError("Koordinat dan indeks potongan harus integer.")
        key = (item.get("piece_id"), item["instance"])
        if key not in expected or key in seen or item["sheet"] < 1 or type(item.get("rotated")) is not bool:
            raise ValueError("Identitas, rotasi, atau sheet potongan tidak valid.")
        seen.add(key)
        sheet_ids.add(item["sheet"])
        piece = expected[key]
        width, height = piece.width + 2 * spec.seam, piece.height + 2 * spec.seam
        if item["rotated"]:
            if not piece.rotate:
                raise ValueError("Rotasi tidak diizinkan untuk potongan ini.")
            width, height = height, width
        if (item["width"], item["height"]) != (width, height):
            raise ValueError("Ukuran potongan tidak sesuai spesifikasi dan kampuh.")
        if item["x"] < stock.margin or item["y"] < stock.margin or item["x"] + width > stock.width - stock.margin or item["y"] + height > stock.height - stock.margin:
            raise ValueError("Potongan melampaui batas stok atau margin.")
    if sheet_ids != set(range(1, len(sheet_ids) + 1)):
        raise ValueError("Nomor sheet harus berurutan mulai satu.")
    for index, left in enumerate(placements):
        for right in placements[index + 1:]:
            if left["sheet"] != right["sheet"]:
                continue
            separate = (
                left["x"] + left["width"] + stock.gap <= right["x"] or
                right["x"] + right["width"] + stock.gap <= left["x"] or
                left["y"] + left["height"] + stock.gap <= right["y"] or
                right["y"] + right["height"] + stock.gap <= left["y"]
            )
            if not separate:
                raise ValueError("Potongan bertumpang tindih atau jaraknya kurang dari gap.")
