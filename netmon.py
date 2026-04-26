#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║           NETMON  v1.0               ║
║  Network Monitor — dual endpoint     ║
╚══════════════════════════════════════╝
"""

import subprocess
import threading
import time
import sys
import os
import re
import platform
import argparse
from datetime import datetime
from collections import deque

# ─── ANSI Colors & Styles ───────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
ORANGE  = "\033[38;5;208m"

BG_DARK = "\033[48;5;235m"
BG_BLUE = "\033[48;5;17m"

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def move_cursor(row, col):
    sys.stdout.write(f"\033[{row};{col}H")

def get_terminal_size():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except:
        return 80, 24

# ─── Ping Logic ─────────────────────────────────────────────────────────────
def do_ping(host, count=1, timeout=2):
    """Execute a single ping and return (success, latency_ms)."""
    system = platform.system()

    if system == "Windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        output = result.stdout + result.stderr

        patterns = [
            r"time[=<]([\d.]+)\s*ms",
            r"avg.*?=([\d.]+)/",
            r"Average = ([\d.]+)ms",
        ]
        for pat in patterns:
            match = re.search(pat, output, re.IGNORECASE)
            if match:
                return True, float(match.group(1))

        if result.returncode == 0:
            return True, 0.0
        return False, None

    except subprocess.TimeoutExpired:
        return False, None
    except Exception:
        return False, None

# ─── Endpoint State ──────────────────────────────────────────────────────────
class Endpoint:
    def __init__(self, name, host, color, symbol):
        self.name    = name
        self.host    = host
        self.color   = color
        self.symbol  = symbol
        self.alive   = None
        self.latency = None
        self.sent    = 0
        self.recv    = 0
        self.history   = deque(maxlen=20)
        self.latencies = deque(maxlen=20)
        self.last_ping_time = None

    @property
    def loss_pct(self):
        if self.sent == 0:
            return 0.0
        return 100.0 * (self.sent - self.recv) / self.sent

    @property
    def avg_latency(self):
        vals = [v for v in self.latencies if v is not None]
        return sum(vals) / len(vals) if vals else None

    @property
    def status_color(self):
        if self.alive is None:
            return DIM + WHITE
        if self.alive:
            return YELLOW if (self.latency and self.latency > 150) else GREEN
        return RED

    @property
    def status_text(self):
        if self.alive is None:
            return "CHECKING..."
        if self.alive:
            return f"ONLINE  {self.latency:.1f}ms" if self.latency else "ONLINE"
        return "OFFLINE"

# ─── Monitor Thread ──────────────────────────────────────────────────────────
def monitor_worker(endpoint: Endpoint, interval: float, stop_event: threading.Event):
    while not stop_event.is_set():
        start = time.time()
        success, latency = do_ping(endpoint.host)

        endpoint.sent += 1
        endpoint.alive = success
        endpoint.last_ping_time = datetime.now()

        if success:
            endpoint.recv += 1
            endpoint.latency = latency
            endpoint.latencies.append(latency)
        else:
            endpoint.latency = None
            endpoint.latencies.append(None)

        endpoint.history.append(success)

        elapsed = time.time() - start
        stop_event.wait(max(0, interval - elapsed))

# ─── Packet Animation ────────────────────────────────────────────────────────
class PacketAnimation:
    """Animates packets traveling between two endpoints."""
    def __init__(self):
        self.packets = []
        self.lock = threading.Lock()

    def spawn(self, direction, color):
        with self.lock:
            self.packets.append({
                "pos": 0.0,
                "direction": direction,  # 1 = A→B, -1 = B→A
                "color": color,
                "age": 0,
            })

    def update(self, dt, speed=1.0):
        with self.lock:
            for p in self.packets:
                p["pos"] += dt * speed * p["direction"]
                p["age"] += dt
            self.packets = [p for p in self.packets if 0.0 <= p["pos"] <= 1.0]

    def get_packets(self):
        with self.lock:
            return list(self.packets)

# ─── Renderer ────────────────────────────────────────────────────────────────
def latency_bar(value, max_val=200, width=10):
    if value is None:
        return DIM + "─" * width + RESET
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    color = GREEN if ratio < 0.3 else (YELLOW if ratio < 0.7 else RED)
    return color + "█" * filled + DIM + "░" * (width - filled) + RESET

def history_sparkline(history, width=20):
    chars = {True: GREEN + "▄" + RESET, False: RED + "▄" + RESET, None: DIM + "─" + RESET}
    hist = list(history)
    while len(hist) < width:
        hist.insert(0, None)
    return "".join(chars[h] for h in hist[-width:])

def render(ep_a: Endpoint, ep_b: Endpoint, anim: PacketAnimation, frame: int, width: int, height: int):
    lines = []

    # ── Header ──────────────────────────────────────────────────────────────
    title = "  ◈  NETMON — Network Monitor  ◈  "
    ts    = datetime.now().strftime("%H:%M:%S")
    pad   = max(0, width - len(title) - len(ts) - 2)
    lines.append(BOLD + CYAN + title + RESET + DIM + " " * pad + ts + RESET)
    lines.append(DIM + "─" * width + RESET)
    lines.append("")

    # ── Endpoint Boxes ──────────────────────────────────────────────────────
    box_w = 28

    def endpoint_box(ep: Endpoint):
        sc = ep.status_color
        avg = ep.avg_latency
        return [
            BOLD + ep.color + f"  {ep.symbol}  {ep.name:<18}" + RESET,
            DIM + "  HOST: " + RESET + f"{ep.host}",
            f"  STATUS: {sc}{BOLD}{ep.status_text:<20}{RESET}",
            f"  AVG:    {latency_bar(avg, width=10)} " + (f"{avg:.1f}ms" if avg else " N/A  "),
            f"  PKTS:   " + GREEN + f"↑{ep.sent}" + RESET + "  " + CYAN + f"↓{ep.recv}" + RESET +
            "  " + (RED if ep.loss_pct > 5 else DIM) + f"loss:{ep.loss_pct:.0f}%" + RESET,
            f"  HIST:   {history_sparkline(ep.history, 18)}",
        ]

    rows_a = endpoint_box(ep_a)
    rows_b = endpoint_box(ep_b)

    # ── Tunnel visualization ─────────────────────────────────────────────────
    tunnel_w = max(width - (box_w * 2) - 4, 10)

    packets = anim.get_packets()
    tunnel_chars  = [" "] * tunnel_w
    tunnel_colors = [""] * tunnel_w

    for p in packets:
        idx = max(0, min(tunnel_w - 1, int(p["pos"] * (tunnel_w - 1))))
        tunnel_chars[idx]  = "●"
        tunnel_colors[idx] = p["color"]

    def build_tunnel_line():
        parts = []
        for i in range(tunnel_w):
            if tunnel_colors[i]:
                parts.append(BOLD + tunnel_colors[i] + tunnel_chars[i] + RESET)
            else:
                parts.append(DIM + "·" + RESET)
        return "".join(parts)

    tunnel_rows = [
        DIM + "  " + "─" * tunnel_w + "  " + RESET,
        "  " + build_tunnel_line() + "  ",
        DIM + "  " + "─" * tunnel_w + "  " + RESET,
    ]
    dir_line = GREEN + "  A→B" + " " * (tunnel_w - 8) + "B→A  " + RESET

    def vis_len(s):
        return len(re.sub(r'\033\[[0-9;]*m', '', s))

    for i in range(max(len(rows_a), len(rows_b))):
        left  = rows_a[i] if i < len(rows_a) else ""
        right = rows_b[i] if i < len(rows_b) else ""
        left_pad = left + " " * (box_w - vis_len(left))

        if   i == 0: mid = dir_line
        elif i == 1: mid = tunnel_rows[0]
        elif i == 2: mid = tunnel_rows[1]
        elif i == 3: mid = tunnel_rows[2]
        else:        mid = " " * (tunnel_w + 4)

        lines.append(left_pad + mid + right)

    lines.append("")

    # ── Status Log ──────────────────────────────────────────────────────────
    lines.append(DIM + "─" * width + RESET)

    def status_line(ep: Endpoint, arrow: str):
        t   = ep.last_ping_time.strftime("%H:%M:%S") if ep.last_ping_time else "--:--:--"
        sc  = ep.status_color
        lat = f"{ep.latency:.1f}ms" if ep.latency else "timeout"
        icon = "✓" if ep.alive else "✗"
        return (DIM + f" [{t}]  " + RESET +
                ep.color + BOLD + f"{ep.name:<12}" + RESET +
                f"  {arrow}  " +
                sc + BOLD + f"{icon} {lat:<12}" + RESET +
                DIM + f"  pkt:{ep.sent}/{ep.recv}" + RESET)

    lines.append(status_line(ep_a, "──→"))
    lines.append(status_line(ep_b, "←──"))
    lines.append("")
    lines.append(DIM + f" Ctrl+C to stop  |  interval: {INTERVAL}s  |  frame: {frame}" + RESET)

    return lines

# ─── Main ────────────────────────────────────────────────────────────────────
INTERVAL = 2.0

def main():
    global INTERVAL

    parser = argparse.ArgumentParser(
        prog="netmon",
        description="NETMON — Monitor konektivitas dua endpoint secara real-time"
    )
    parser.add_argument("host_a", nargs="?", default="8.8.8.8",
                        help="Host/IP endpoint A (default: 8.8.8.8)")
    parser.add_argument("host_b", nargs="?", default="1.1.1.1",
                        help="Host/IP endpoint B (default: 1.1.1.1)")
    parser.add_argument("--name-a",   default=None,  help="Label endpoint A")
    parser.add_argument("--name-b",   default=None,  help="Label endpoint B")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Interval probe dalam detik (default: 2)")
    args = parser.parse_args()

    INTERVAL = args.interval
    ep_a = Endpoint(args.name_a or args.host_a, args.host_a, CYAN,    "◉")
    ep_b = Endpoint(args.name_b or args.host_b, args.host_b, MAGENTA, "◉")
    anim = PacketAnimation()

    stop_event = threading.Event()
    for ep in (ep_a, ep_b):
        threading.Thread(target=monitor_worker, args=(ep, INTERVAL, stop_event),
                         daemon=True).start()

    hide_cursor()
    clear_screen()

    frame      = 0
    last_spawn = time.time()
    last_anim  = time.time()

    try:
        while True:
            now = time.time()
            dt  = now - last_anim
            last_anim = now

            if now - last_spawn > INTERVAL * 0.5:
                if ep_a.alive: anim.spawn(1,  CYAN)
                if ep_b.alive: anim.spawn(-1, MAGENTA)
                last_spawn = now

            anim.update(dt, speed=0.4)

            width, height = get_terminal_size()
            lines = render(ep_a, ep_b, anim, frame, width, height)

            move_cursor(1, 1)
            sys.stdout.write("\n".join(lines))
            sys.stdout.flush()

            frame += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        show_cursor()
        clear_screen()
        print(f"\n{CYAN}netmon dihentikan.{RESET}")
        for ep in (ep_a, ep_b):
            print(f"  {ep.color}{ep.name}{RESET}: "
                  f"sent={ep.sent}  recv={ep.recv}  loss={ep.loss_pct:.1f}%")
        print()

if __name__ == "__main__":
    main()
