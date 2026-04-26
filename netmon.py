#!/usr/bin/env python3
"""netmon — Network Monitor for Termux / narrow terminals"""

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

# ─── ANSI ───────────────────────────────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
RD = "\033[91m"
GR = "\033[92m"
YL = "\033[93m"
CY = "\033[96m"
MG = "\033[95m"
WH = "\033[97m"

def clear():
    os.system('clear')

def hide_cursor():  sys.stdout.write("\033[?25l"); sys.stdout.flush()
def show_cursor():  sys.stdout.write("\033[?25h"); sys.stdout.flush()
def goto(r, c):     sys.stdout.write(f"\033[{r};{c}H")

def term_width():
    try:    return os.get_terminal_size().columns
    except: return 40

# ─── Ping ────────────────────────────────────────────────────────────────────
def do_ping(host, timeout=2):
    is_win = platform.system() == "Windows"
    cmd = (["ping", "-n", "1", "-w", str(timeout*1000), host] if is_win
           else ["ping", "-c", "1", "-W", str(timeout), host])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+2)
        out = r.stdout + r.stderr
        for pat in [r"time[=<]([\d.]+)\s*ms", r"avg.*?=([\d.]+)/", r"Average = ([\d.]+)ms"]:
            m = re.search(pat, out, re.IGNORECASE)
            if m:
                return True, float(m.group(1))
        return (r.returncode == 0), 0.0
    except:
        return False, None

# ─── Endpoint ────────────────────────────────────────────────────────────────
class Endpoint:
    def __init__(self, name, host, color):
        self.name      = name
        self.host      = host
        self.color     = color
        self.alive     = None
        self.latency   = None
        self.sent      = 0
        self.recv      = 0
        self.history   = deque(maxlen=14)
        self.latencies = deque(maxlen=10)
        self.ts        = None

    @property
    def loss_pct(self):
        return 0.0 if self.sent == 0 else 100*(self.sent-self.recv)/self.sent

    @property
    def avg_ms(self):
        v = [x for x in self.latencies if x]
        return sum(v)/len(v) if v else None

    @property
    def sc(self):
        if self.alive is None: return D+WH
        if self.alive: return YL if (self.latency and self.latency > 150) else GR
        return RD

def monitor_worker(ep, interval, stop):
    while not stop.is_set():
        t0 = time.time()
        ok, ms = do_ping(ep.host)
        ep.sent += 1
        ep.alive = ok
        ep.ts = datetime.now()
        if ok:
            ep.recv += 1
            ep.latency = ms
            ep.latencies.append(ms)
        else:
            ep.latency = None
            ep.latencies.append(None)
        ep.history.append(ok)
        stop.wait(max(0, interval - (time.time()-t0)))

# ─── Packet Animation ────────────────────────────────────────────────────────
class Anim:
    def __init__(self):
        self.pkts = []
        self.lock = threading.Lock()

    def spawn(self, color):
        with self.lock:
            self.pkts.append({"pos": 0.0, "color": color})

    def update(self, dt, speed=0.35):
        with self.lock:
            for p in self.pkts:
                p["pos"] = min(1.0, p["pos"] + dt * speed)
            self.pkts = [p for p in self.pkts if p["pos"] < 1.0]

    def get(self):
        with self.lock: return list(self.pkts)

# ─── Render helpers ──────────────────────────────────────────────────────────
def sparkline(history, w):
    buf = list(history)
    while len(buf) < w: buf.insert(0, None)
    buf = buf[-w:]
    out = ""
    for h in buf:
        if h is True:    out += GR + "█" + R
        elif h is False: out += RD + "░" + R
        else:            out += D  + "─" + R
    return out

def latbar(val, w=10):
    if val is None: return D + "─"*w + R
    ratio = min(val/200, 1.0)
    f = int(ratio * w)
    c = GR if ratio < 0.3 else (YL if ratio < 0.7 else RD)
    return c + "▓"*f + D + "░"*(w-f) + R

def tunnel_line(pkts, w):
    cells = [D+"·"+R] * w
    for p in pkts:
        idx = max(0, min(w-1, int(p["pos"] * (w-1))))
        cells[idx] = B + p["color"] + "●" + R
    return "".join(cells)

def vis(s):
    return len(re.sub(r'\033\[[0-9;]*m', '', s))

def padto(s, w):
    return s + " " * max(0, w - vis(s))

# ─── Main render ─────────────────────────────────────────────────────────────
def render(ep_a, ep_b, anim, interval):
    W = term_width()
    now = datetime.now().strftime("%H:%M:%S")
    lines = []

    # Header
    title = B+CY+"◈ NETMON"+R
    lines.append(padto(title, W-8) + D+now+R)
    lines.append(D+"─"*W+R)

    def ep_block(ep):
        sc = ep.sc
        lines.append(f" {B}{ep.color}{ep.name}{R}  {D}{ep.host}{R}")

        if ep.alive is None:
            status = D+"…checking"+R
        elif ep.alive:
            lat = f"{ep.latency:.0f}ms" if ep.latency else "ok"
            status = sc+B+"▲ UP"+R+"  "+sc+lat+R
        else:
            status = sc+B+"▼ DOWN"+R

        avg = ep.avg_ms
        avg_str = (sc+f"{avg:.0f}ms"+R) if avg else D+"--"+R
        lines.append(f" {status}   avg:{avg_str}")
        lines.append(f" {latbar(ep.avg_ms, W-4)}")

        loss_c = RD if ep.loss_pct > 5 else D
        ts_str = ep.ts.strftime("%H:%M:%S") if ep.ts else "--:--:--"
        lines.append(f" {GR}↑{ep.sent}{R} {CY}↓{ep.recv}{R}  {loss_c}loss:{ep.loss_pct:.0f}%{R}  {D}{ts_str}{R}")
        lines.append(f" {sparkline(ep.history, W-4)}")

    ep_block(ep_a)
    lines.append("")

    # Tunnel
    tw = W - 2
    pkts = anim.get()
    lines.append(" " + tunnel_line(pkts, tw))
    mid = tw // 2 - 1
    lines.append(D + " A" + "─"*mid + "↕" + "─"*(tw - mid - 3) + "B" + R)
    lines.append("")

    ep_block(ep_b)
    lines.append("")
    lines.append(D + f" interval:{interval}s  ^C stop" + R)

    return lines

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(prog="netmon",
        description="Network Monitor — dual endpoint, Termux-friendly")
    parser.add_argument("host_a", nargs="?", default="192.168.1.1")
    parser.add_argument("host_b", nargs="?", default="192.168.1.2")
    parser.add_argument("--name-a",   default=None)
    parser.add_argument("--name-b",   default=None)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    ep_a = Endpoint(args.name_a or args.host_a, args.host_a, CY)
    ep_b = Endpoint(args.name_b or args.host_b, args.host_b, MG)
    anim = Anim()

    stop = threading.Event()
    for ep in (ep_a, ep_b):
        threading.Thread(target=monitor_worker,
                         args=(ep, args.interval, stop), daemon=True).start()

    hide_cursor()
    clear()

    last_spawn = time.time()
    last_t     = time.time()

    try:
        while True:
            now = time.time()
            dt  = now - last_t
            last_t = now

            if now - last_spawn > args.interval * 0.5:
                if ep_a.alive: anim.spawn(CY)
                if ep_b.alive: anim.spawn(MG)
                last_spawn = now

            anim.update(dt)
            lines = render(ep_a, ep_b, anim, args.interval)
            goto(1, 1)
            sys.stdout.write("\n".join(lines))
            sys.stdout.flush()
            time.sleep(0.12)

    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        show_cursor()
        clear()
        print(f"\n{CY}netmon stopped.{R}")
        for ep in (ep_a, ep_b):
            print(f"  {ep.color}{ep.name}{R}  sent={ep.sent} recv={ep.recv} loss={ep.loss_pct:.0f}%")
        print()

if __name__ == "__main__":
    main()
