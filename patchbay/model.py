from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Stock:
    width: int
    height: int
    margin: int = 0
    gap: int = 0


@dataclass(frozen=True)
class Piece:
    id: str
    width: int
    height: int
    quantity: int = 1
    rotate: bool = True


@dataclass(frozen=True)
class Spec:
    title: str
    stock: Stock
    seam: int
    pieces: tuple[Piece, ...]


def _integer(value, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} harus integer {minimum}–{maximum}.")
    return value


def parse_spec(data: dict) -> Spec:
    if not isinstance(data, dict):
        raise ValueError("Spesifikasi harus berupa objek JSON.")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValueError("Judul harus berisi 1–200 karakter.")
    raw_stock = data.get("stock")
    if not isinstance(raw_stock, dict):
        raise ValueError("stock harus berupa objek.")
    stock = Stock(
        _integer(raw_stock.get("width"), "stock.width", 1, 10000),
        _integer(raw_stock.get("height"), "stock.height", 1, 10000),
        _integer(raw_stock.get("margin", 0), "stock.margin", 0, 1000),
        _integer(raw_stock.get("gap", 0), "stock.gap", 0, 100),
    )
    usable_w, usable_h = stock.width - 2 * stock.margin, stock.height - 2 * stock.margin
    if usable_w <= 0 or usable_h <= 0:
        raise ValueError("Margin menyisakan area stok kosong.")
    seam = _integer(data.get("seam", 0), "seam", 0, 100)
    raw_pieces = data.get("pieces")
    if not isinstance(raw_pieces, list) or not 1 <= len(raw_pieces) <= 500:
        raise ValueError("pieces harus berisi 1–500 jenis potongan.")
    pieces = []
    ids = set()
    total = 0
    for raw in raw_pieces:
        if not isinstance(raw, dict):
            raise ValueError("Setiap potongan harus berupa objek.")
        identity = raw.get("id")
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", identity):
            raise ValueError("ID potongan harus 1–40 karakter huruf kecil, angka, _ atau -.")
        if identity in ids:
            raise ValueError(f"ID potongan duplikat: {identity}")
        ids.add(identity)
        rotate = raw.get("rotate", True)
        if type(rotate) is not bool:
            raise ValueError(f"rotate untuk {identity} harus boolean.")
        piece = Piece(
            identity,
            _integer(raw.get("width"), f"{identity}.width", 1, 10000),
            _integer(raw.get("height"), f"{identity}.height", 1, 10000),
            _integer(raw.get("quantity", 1), f"{identity}.quantity", 1, 500),
            rotate,
        )
        width, height = piece.width + 2 * seam, piece.height + 2 * seam
        fits = width <= usable_w and height <= usable_h
        if not fits and not (rotate and height <= usable_w and width <= usable_h):
            raise ValueError(f"Potongan {identity} beserta kampuh tidak muat pada stok.")
        total += piece.quantity
        pieces.append(piece)
    if total > 500:
        raise ValueError("Total potongan maksimal 500.")
    return Spec(title.strip(), stock, seam, tuple(pieces))
