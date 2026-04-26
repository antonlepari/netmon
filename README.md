# 🌐 netmon

**Network Monitor** — visualisasi konektivitas dua endpoint secara real-time di terminal.

```
  ◈  NETMON — Network Monitor  ◈                                14:32:01
──────────────────────────────────────────────────────────────────────────

  ◉  Google DNS                 A→B                    B→A  ◉  Cloudflare
  HOST: 8.8.8.8                 ──────────────────────────  HOST: 1.1.1.1
  STATUS: ● ONLINE  12.3ms      ·····●····················  STATUS: ● ONLINE  9.8ms
  AVG:  ████░░░░░░ 14.1ms       ──────────────────────────  AVG:  ███░░░░░░░ 10.2ms
  PKTS: ↑12  ↓12  loss:0%                                  PKTS: ↑12  ↓12  loss:0%
  HIST: ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄                                HIST: ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄

──────────────────────────────────────────────────────────────────────────
 [14:32:01]  Google DNS    ──→  ✓ 12.3ms      pkt:12/12
 [14:32:01]  Cloudflare    ←──  ✓ 9.8ms       pkt:12/12

 Ctrl+C to stop  |  interval: 2s
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/USERNAME/netmon.git
cd netmon
python3 netmon.py
```

Tidak perlu `pip install` — hanya Python 3 standar.

---

## ⚙️ Penggunaan

```bash
# Syntax
python3 netmon.py [HOST_A] [HOST_B] [--name-a LABEL] [--name-b LABEL] [--interval DETIK]

# Default: Google DNS vs Cloudflare
python3 netmon.py

# Monitor 2 server di jaringan lokal
python3 netmon.py 192.168.1.1 192.168.1.254

# Dengan label custom
python3 netmon.py 8.8.8.8 1.1.1.1 --name-a "Google" --name-b "Cloudflare"

# Interval 5 detik
python3 netmon.py --interval 5

# Localhost vs internet
python3 netmon.py 127.0.0.1 8.8.8.8 --name-a "Localhost" --name-b "Internet"
```

### Parameter

| Parameter     | Default   | Keterangan                        |
|---------------|-----------|-----------------------------------|
| `HOST_A`      | `8.8.8.8` | IP/hostname endpoint A            |
| `HOST_B`      | `1.1.1.1` | IP/hostname endpoint B            |
| `--name-a`    | HOST_A    | Label tampilan endpoint A         |
| `--name-b`    | HOST_B    | Label tampilan endpoint B         |
| `--interval`  | `2.0`     | Interval probe dalam detik        |

---

## 🖥️ Kompatibilitas

| Platform | Status |
|----------|--------|
| Linux    | ✅ Full support |
| macOS    | ✅ Full support |
| Windows  | ✅ Support (Windows Terminal / ANSI enabled) |

**Requirements:** Python 3.6+ · stdlib only · command `ping` tersedia di sistem

---

## ✨ Fitur

- 📦 **Animasi paket** — titik `●` bergerak di tunnel antar endpoint
- 📊 **Latency bar** — hijau / kuning / merah sesuai delay
- 📈 **History sparkline** — 20 probe terakhir tiap endpoint
- 📉 **Statistik live** — sent / recv / packet loss real-time
- 🔄 **Dual thread** — kedua endpoint diprobe secara paralel
- 🛑 **Graceful exit** — `Ctrl+C` menampilkan ringkasan akhir

---

## 📂 Struktur

```
netmon/
├── netmon.py    # Single-file, zero dependency
├── README.md
└── LICENSE
```

---

## 📝 Lisensi

MIT
