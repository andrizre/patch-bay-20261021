# Patch Bay

Patch Bay adalah perencana potong kain quilt berbentuk persegi panjang. CLI membaca spesifikasi JSON, menempatkan potongan pada lembar stok, lalu memeriksa ukuran, margin, jarak, dan tumpang tindih sebelum mengekspor rencana.

## Fitur

- Kampuh (`seam`) pada setiap tepi, margin lembar, dan jarak antarpotongan (`gap`).
- Rotasi 90 derajat yang dapat diizinkan atau dilarang per jenis potongan.
- Heuristik guillotine deterministik untuk satu atau beberapa lembar stok.
- Verifikasi geometri dan jumlah seluruh potongan setelah penempatan.
- JSON lengkap, daftar koordinat CSV, serta ringkasan luas potong dan luas stok.
- Python standard library; tanpa dependensi runtime eksternal, network, atau layanan berbayar.

Rencana mengasumsikan **satu jenis kain dan ukuran stok yang seragam**. Buat rencana terpisah untuk warna atau bahan lain. Gunakan `rotate: false` jika arah serat atau motif tidak boleh diputar.

## Instalasi

Gunakan Python 3.11 atau lebih baru.

```bash
git clone https://github.com/andrizre/patch-bay-20261021.git
cd patch-bay-20261021
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Menjalankan

Validasi contoh bawaan dan cetak ringkasannya:

```bash
patch-bay validate examples/quilt.json
```

Buat rencana dan daftar potong:

```bash
patch-bay plan examples/quilt.json --output out/plan.json --csv out/cuts.csv
```

Modul juga dapat dijalankan dengan `python -m patchbay`. Direktori output dibuat jika belum ada. Output yang sudah ada atau path JSON/CSV yang sama akan ditolak, tidak ditimpa. Kesalahan input atau argumen menghasilkan exit code `2`. Jika salah satu penulisan gagal, file lain yang baru dibuat dalam operasi itu dibersihkan.

[Contoh input](examples/quilt.json) memiliki 16 potongan dalam tiga ukuran. [Rencana JSON](examples/plan.json) dan [daftar CSV](examples/cuts.csv) dihasilkan dengan CLI; hasil contoh memakai dua lembar, bukan klaim jumlah lembar minimum.

## Format spesifikasi

Semua ukuran adalah **integer milimeter**. Contoh minimal:

```json
{
  "title": "Panel Quilt",
  "stock": {"width": 300, "height": 250, "margin": 8, "gap": 3},
  "seam": 6,
  "pieces": [
    {"id": "panel", "width": 80, "height": 60, "quantity": 6, "rotate": true}
  ]
}
```

`width` dan `height` potongan adalah ukuran nominal sebelum kampuh. Ukuran kotak potong menjadi `(width + 2*seam) × (height + 2*seam)`. Margin membentuk bingkai di keempat sisi lembar. Gap dibutuhkan antarpotongan, bukan di luar tepi stok.

Default: `margin`, `gap`, dan `seam` adalah `0`; `quantity` adalah `1`; `rotate` adalah `true`. Dimensi stok/potongan berada pada 1–10000 mm; seam 0–100; margin 0–1000; gap 0–100. Boolean tidak diterima sebagai integer. ID unik memakai `[a-z][a-z0-9_-]{0,39}`. Total potongan maksimal 500, input CLI maksimal 1 MiB, dan setiap potongan dengan kampuh harus muat pada area stok yang tersisa.

## Membaca hasil

Koordinat `x,y` dimulai dari **sudut kiri atas lembar asli**. `sheet` dan `instance` dimulai dari 1. `width,height` keluaran sudah mencakup kampuh dan orientasi aktual; `rotated` menandai pertukaran lebar/tinggi.

CSV memakai header:

```text
sheet,piece_id,instance,x_mm,y_mm,width_mm,height_mm,rotated
```

`cut_area_mm2` menghitung kotak potong beserta kampuh. `stock_area_mm2` menghitung seluruh lembar termasuk margin. `utilisation_ratio` adalah luas potong dibagi luas stok; bukan persentase kain jadi setelah dijahit.

## Pengujian

```bash
python -m unittest discover -s tests -v
```

Tes mencakup validasi, rotasi, kampuh, margin, gap, banyak lembar, CSV/CLI, penolakan overwrite, rollback output, dan 50 spesifikasi acak ber-seed yang dapat diulang.

## Batasan

Hasil heuristik **tidak dijamin optimal secara global**. Tidak ada penanganan bentuk nonpersegi panjang, cacat kain, arah motif selain sakelar rotasi, urutan gerakan alat potong, atau visualisasi/SVG.

**Periksa ulang ukuran, arah kain, kampuh, dan template kertas sebelum memotong kain sungguhan.** Rencana koordinat ini bukan jaminan hasil produksi.

## Lisensi

MIT. Lihat [LICENSE](LICENSE).
