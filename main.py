#!/usr/bin/env python3
"""Entry for make.fun news-image-20261126: sum up 26 November 2026 world news.

Pure standard library (struct, zlib, os). Draws a 1024x1024 front-page
image — the day's four biggest stories, each with a headline, a short
summary and a small picture, plus the date — and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (or /output/entry.png). Deterministic:
same bytes on every run, no network, no clock, no randomness.
"""
import os

import struct, zlib

W, H = 1024, 1024

# --- 5x7 bitmap font: glyph -> 7 rows of 5 bits ---------------------------
def g(*rows):
    return [int(r.replace('#', '1').replace('.', '0'), 2) for r in rows]

FONT = {
 'A': g('01110','10001','10001','11111','10001','10001','10001'),
 'B': g('11110','10001','10001','11110','10001','10001','11110'),
 'C': g('01110','10001','10000','10000','10000','10001','01110'),
 'D': g('11110','10001','10001','10001','10001','10001','11110'),
 'E': g('11111','10000','10000','11110','10000','10000','11111'),
 'F': g('11111','10000','10000','11110','10000','10000','10000'),
 'G': g('01110','10001','10000','10111','10001','10001','01111'),
 'H': g('10001','10001','10001','11111','10001','10001','10001'),
 'I': g('01110','00100','00100','00100','00100','00100','01110'),
 'J': g('00111','00010','00010','00010','00010','10010','01100'),
 'K': g('10001','10010','10100','11000','10100','10010','10001'),
 'L': g('10000','10000','10000','10000','10000','10000','11111'),
 'M': g('10001','11011','10101','10101','10001','10001','10001'),
 'N': g('10001','11001','10101','10011','10001','10001','10001'),
 'O': g('01110','10001','10001','10001','10001','10001','01110'),
 'P': g('11110','10001','10001','11110','10000','10000','10000'),
 'Q': g('01110','10001','10001','10001','10101','10010','01101'),
 'R': g('11110','10001','10001','11110','10100','10010','10001'),
 'S': g('01111','10000','10000','01110','00001','00001','11110'),
 'T': g('11111','00100','00100','00100','00100','00100','00100'),
 'U': g('10001','10001','10001','10001','10001','10001','01110'),
 'V': g('10001','10001','10001','10001','10001','01010','00100'),
 'W': g('10001','10001','10001','10101','10101','11011','10001'),
 'X': g('10001','10001','01010','00100','01010','10001','10001'),
 'Y': g('10001','10001','01010','00100','00100','00100','00100'),
 'Z': g('11111','00001','00010','00100','01000','10000','11111'),
 '0': g('01110','10001','10011','10101','11001','10001','01110'),
 '1': g('00100','01100','00100','00100','00100','00100','01110'),
 '2': g('01110','10001','00001','00110','01000','10000','11111'),
 '3': g('11111','00010','00100','00010','00001','10001','01110'),
 '4': g('00010','00110','01010','10010','11111','00010','00010'),
 '5': g('11111','10000','11110','00001','00001','10001','01110'),
 '6': g('00110','01000','10000','11110','10001','10001','01110'),
 '7': g('11111','00001','00010','00100','01000','01000','01000'),
 '8': g('01110','10001','10001','01110','10001','10001','01110'),
 '9': g('01110','10001','10001','01111','00001','00010','01100'),
 ' ': g('00000','00000','00000','00000','00000','00000','00000'),
 '.': g('00000','00000','00000','00000','00000','01100','01100'),
 ',': g('00000','00000','00000','00000','01100','00100','01000'),
 ':': g('00000','01100','01100','00000','01100','01100','00000'),
 ';': g('00000','01100','01100','00000','01100','00100','01000'),
 '!': g('00100','00100','00100','00100','00100','00000','00100'),
 '?': g('01110','10001','00001','00110','00100','00000','00100'),
 "'": g('00100','00100','01000','00000','00000','00000','00000'),
 '-': g('00000','00000','00000','01110','00000','00000','00000'),
 '/': g('00001','00010','00010','00100','01000','01000','10000'),
 '(': g('00010','00100','01000','01000','01000','00100','00010'),
 ')': g('01000','00100','00010','00010','00010','00100','01000'),
 '&': g('01100','10010','10100','01000','10101','10010','01101'),
 '%': g('11001','11010','00010','00100','01000','01011','10011'),
 '+': g('00000','00100','00100','01110','00100','00100','00000'),
 '=': g('00000','00000','11111','00000','11111','00000','00000'),
 '*': g('00000','00100','10101','01110','10101','00100','00000'),
 '>': g('10000','01000','00100','00010','00100','01000','10000'),
 '<': g('00001','00010','00100','01000','00100','00010','00001'),
}

def text_width(s, scale):
    return sum(6 for _ in s) * scale - scale  # 5px glyph + 1px gap, no trailing gap

def wrap(text, scale, max_w):
    words = text.split(' ')
    lines, cur = [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if text_width(t, scale) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

class Canvas:
    def __init__(self, w=W, h=H, bg=(247, 243, 234)):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))
    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i+3] = bytes(c)
    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self._set(xx, yy, c)
    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)
    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)
    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for a in range(t):
                for b in range(t):
                    self._set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy
    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill and d <= r * r:
                    self._set(xx, yy, c)
                elif not fill and abs(d - r * r) <= r:
                    self._set(xx, yy, c)
    def text(self, x, y, s, color, scale, align='left'):
        s = s.upper()
        w = text_width(s, scale)
        if align == 'center':
            x -= w // 2
        elif align == 'right':
            x -= w
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale, scale, scale, color)
            cx += 6 * scale
        return y + 7 * scale
    def para(self, x, y, s, color, scale, max_w, leading=None):
        lines = wrap(s, scale, max_w)
        lh = leading if leading else 9 * scale
        for ln in lines:
            self.text(x, y, ln, color, scale)
            y += lh
        return y
    def png(self):
        raw = bytearray()
        stride = self.w * 3
        for yy in range(self.h):
            raw.append(0)
            raw += self.px[yy * stride:(yy + 1) * stride]
        def chunk(tag, data):
            c = struct.pack('>I', len(data)) + tag + data
            return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        ihdr = struct.pack('>IIBBBBB', self.w, self.h, 8, 2, 0, 0, 0)
        return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
                + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
                + chunk(b'IEND', b''))

# --- palette ---------------------------------------------------------------
INK    = (24, 24, 24)
PAPER  = (247, 243, 234)
NAVY   = (20, 33, 61)
NAVY2  = (28, 48, 88)
RED    = (178, 34, 34)
GOLD   = (201, 162, 39)
GREY   = (110, 110, 105)
LGREY  = (210, 205, 192)
STEEL  = (70, 90, 120)
WHITE  = (255, 255, 255)
CREAM  = (255, 248, 220)

DATE = 'THURSDAY, 26 NOVEMBER 2026'

def missile_burst(c, x, y, w, h):
    """A missile streaking down-right with a starburst blast at its nose."""
    c.line(x + 20, y + 8, x + w - 70, y + h - 18, (40, 40, 40), 4)
    c.line(x + w - 70, y + h - 18, x + w - 34, y + h - 6, (40, 40, 40), 3)
    c.line(x + 28, y + 16, x + 44, y + 2, (40, 40, 40), 3)
    bx, by = x + w - 40, y + h - 12
    for dx, dy in ((0, -16), (11, -11), (16, 0), (11, 11),
                   (0, 16), (-11, 11), (-16, 0), (-11, -11)):
        c.line(bx, by, bx + dx, by + dy, RED, 3)
    c.circle(bx, by, 6, RED)
    c.circle(bx - 22, by - 8, 5, (150, 150, 145))
    c.circle(bx - 30, by + 4, 6, (170, 170, 165))

def chart_down(c, x, y, w, h, col=(178, 34, 34)):
    """Falling market chart: axes and a descending line with arrowhead."""
    c.vline(x + 8, y + 4, h - 8, INK, 2)
    c.hline(x + 8, y + h - 4, w - 8, INK, 2)
    pts = [(x + 16, y + 6), (x + w // 3, y + 10), (x + w // 2, y + 12),
           (x + 2 * w // 3, y + 24), (x + w - 30, y + h - 12)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        c.line(x0, y0, x1, y1, col, 3)
    ex, ey = pts[-1]
    c.line(ex, ey, ex - 12, ey - 2, col, 3)
    c.line(ex, ey, ex - 2, ey - 12, col, 3)
    for px, py in pts[:-1]:
        c.circle(px, py, 3, col)

def cyclone(c, x, y, w, h, col=(28, 48, 88)):
    """Cyclone: concentric spiral arcs over a coastline, with rain slashes."""
    cx, cy = x + w // 2 - 20, y + h // 2 - 8
    for r in (22, 16, 10):
        c.circle(cx, cy, r, col, fill=False)
    c.circle(cx, cy, 4, RED)
    c.line(cx - 22, cy - 8, cx - 30, cy - 18, col, 2)
    c.line(cx + 22, cy + 8, cx + 30, cy + 16, col, 2)
    c.hline(x, y + h - 6, w, col, 3)
    for k in range(0, w, 26):
        c.line(x + k + 18, y + h - 14, x + k + 12, y + h - 4, STEEL, 2)

def deal_flags(c, x, y, w, h):
    """Two flags side by side — UK and EU — with a joining check mark."""
    fw, fh = (w - 60) // 2, h - 16
    c.rect(x + 10, y + 8, fw, fh, (28, 48, 88))
    c.text(x + 10 + fw // 2, y + 8 + fh // 2 - 7, 'UK', WHITE, 2, 'center')
    c.rect(x + 30 + fw, y + 8, fw, fh, (201, 162, 39))
    c.text(x + 30 + fw + fw // 2, y + 8 + fh // 2 - 7, 'EU', NAVY, 2, 'center')
    c.line(x + 10 + fw + 4, y + h - 6, x + 30 + fw - 4, y + h - 6, RED, 3)


def quake(c, x, y, w, h):
    """Earthquake: a seismograph zigzag over a cracked ground line."""
    c.hline(x, y + h - 8, w, INK, 3)
    pts = [(x + 6, y + h // 2), (x + w // 5, y + h // 2),
           (x + w // 5 + 14, y + 8), (x + w // 5 + 30, y + h - 14),
           (x + w // 5 + 44, y + 12), (x + w // 5 + 58, y + h // 2 + 8),
           (x + 3 * w // 5, y + h // 2), (x + 3 * w // 5 + 16, y + 6),
           (x + 3 * w // 5 + 30, y + h - 16), (x + w - 8, y + h // 2)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        c.line(x0, y0, x1, y1, RED, 3)
    c.line(x + w // 2, y + h - 8, x + w // 2 + 12, y + h - 2, INK, 2)
    c.line(x + w // 2 + 12, y + h - 2, x + w // 2 + 22, y + h - 8, INK, 2)

def cop_globe(c, x, y, w, h):
    """Climate talks: a globe crossed by a red deadlock slash."""
    cx, cy = x + w // 2, y + h // 2
    r = min(w, h) // 2 - 4
    c.circle(cx, cy, r, NAVY2, fill=False)
    c.vline(cx, cy - r, 2 * r, NAVY2, 2)
    c.hline(cx - r, cy, 2 * r, NAVY2, 2)
    c.circle(cx, cy, r // 2, NAVY2, fill=False)
    c.line(cx - r + 4, cy + r - 4, cx + r - 4, cy - r + 4, RED, 4)
    c.circle(cx - r // 2, cy - r // 2, 3, RED)

def border_fence(c, x, y, w, h):
    """A closed border: fence bars with a red barrier stripe."""
    c.hline(x, y + 8, w, INK, 3)
    c.hline(x, y + h - 10, w, INK, 3)
    for k in range(0, w, 18):
        c.vline(x + k, y + 8, h - 18, INK, 2)
    c.line(x + 6, y + h - 14, x + w - 6, y + 12, RED, 4)
    c.line(x + 6, y + 12, x + w - 6, y + h - 14, RED, 4)

def flame(c, x, y, w, h):
    """Factory fire: a flame over a roofline."""
    cx = x + w // 2
    c.hline(x, y + h - 8, w, INK, 3)
    c.line(x + 8, y + h - 8, cx - 26, y + h - 26, INK, 2)
    c.line(cx - 26, y + h - 26, cx - 26, y + h - 8, INK, 2)
    c.line(cx + 26, y + h - 26, cx + 26, y + h - 8, INK, 2)
    c.line(cx + 26, y + h - 26, x + w - 8, y + h - 8, INK, 2)
    for dx, dy, r in ((0, -6, 12), (-10, 2, 8), (10, 2, 8), (0, 8, 6)):
        c.circle(cx + dx, y + h // 2 + dy, r, RED)
    c.circle(cx, y + h // 2 + 4, 5, GOLD)

def arrest(c, x, y, w, h):
    """Arrest: prison bars with a gold star badge."""
    for k in range(0, w, 20):
        c.vline(x + k, y + 4, h - 8, INK, 3)
    c.hline(x, y + 4, w, INK, 3)
    c.hline(x, y + h - 8, w, INK, 3)
    cx, cy = x + w // 2, y + h // 2
    for dx, dy in ((0, -12), (11, -4), (7, 10), (-7, 10), (-11, -4)):
        c.line(cx, cy, cx + dx, cy + dy, GOLD, 3)
    c.circle(cx, cy, 5, GOLD)

def gavel(c, x, y, w, h):
    """Court verdict: a gavel over its sound block."""
    cx = x + w // 2
    base = y + h - 8
    c.hline(cx - 14, y + 10, 34, GOLD, 9)
    c.hline(cx - 14, y + 10, 34, RED, 2)
    c.line(cx + 4, y + 14, cx - 16, base - 12, INK, 4)
    c.hline(x + 12, base, w - 24, INK, 4)
    c.hline(x + 20, base - 8, w - 40, INK, 3)

def tanker(c, x, y, w, h):
    """A tanker in a strait, burst at the bow."""
    base = y + h - 12
    c.hline(x + 18, base - 10, w - 36, INK, 3)
    c.line(x + 6, base, x + 18, base - 10, INK, 3)
    c.line(x + w - 6, base, x + w - 18, base - 10, INK, 3)
    c.hline(x + 6, base, w - 12, INK, 4)
    c.hline(x + w - 54, base - 24, 28, INK, 3)
    c.vline(x + w - 40, base - 24, 14, INK, 3)
    for dx in (-32, 0, 32):
        c.hline(x + w // 2 + dx - 8, base + 5, 16, GOLD, 2)
    bx, by = x + 14, base - 6
    for dx, dy in ((0, -12), (9, -8), (-9, -8), (12, 2), (-12, 2)):
        c.line(bx, by, bx + dx, by + dy, RED, 2)
    c.circle(bx, by, 4, RED)

def droneship(c, x, y, w, h):
    """A drone over a warship."""
    base = y + h - 12
    c.hline(x + 22, base - 9, w - 44, INK, 3)
    c.line(x + 10, base, x + 22, base - 9, INK, 3)
    c.line(x + w - 10, base, x + w - 22, base - 9, INK, 3)
    c.hline(x + 10, base, w - 20, INK, 4)
    c.hline(x + 30, base - 20, 34, INK, 3)
    c.vline(x + 47, base - 32, 12, INK, 3)
    dx, dy = x + w - 42, y + 14
    c.line(dx - 10, dy - 6, dx + 10, dy + 6, RED, 3)
    c.line(dx - 10, dy + 6, dx + 10, dy - 6, RED, 3)
    c.circle(dx, dy, 4, RED)
    c.circle(dx - 12, dy - 8, 3, GOLD)
    c.circle(dx + 12, dy - 8, 3, GOLD)
    c.circle(dx - 12, dy + 8, 3, GOLD)
    c.circle(dx + 12, dy + 8, 3, GOLD)

def scales(c, x, y, w, h):
    """Scales of justice for the World Court ruling."""
    cx = x + w // 2
    top = y + 6
    c.vline(cx, top, h - 18, INK, 3)
    c.hline(cx - 30, top + 6, 60, INK, 3)
    c.circle(cx, top + 2, 4, GOLD)
    for sx in (cx - 30, cx + 30):
        c.line(sx, top + 6, sx - 9, top + 22, INK, 2)
        c.line(sx, top + 6, sx + 9, top + 22, INK, 2)
        c.hline(sx - 13, top + 22, 26, GOLD, 3)
    c.hline(cx - 16, y + h - 8, 32, INK, 4)

def shipstrike(c, x, y, w, h):
    """A cargo ship struck from above: hull, drone cross, burst."""
    base = y + h - 12
    c.hline(x + 22, base - 9, w - 44, INK, 3)
    c.line(x + 10, base, x + 22, base - 9, INK, 3)
    c.line(x + w - 10, base, x + w - 22, base - 9, INK, 3)
    c.hline(x + 10, base, w - 20, INK, 4)
    c.hline(x + 30, base - 20, 34, INK, 3)
    c.vline(x + 47, base - 32, 12, INK, 3)
    dx, dy = x + w - 42, y + 14
    c.line(dx - 10, dy - 6, dx + 10, dy + 6, RED, 3)
    c.line(dx - 10, dy + 6, dx + 10, dy - 6, RED, 3)
    c.circle(dx, dy, 4, RED)
    bx, by = x + w // 2, base - 14
    for ddx, ddy in ((0, -10), (8, -7), (-8, -7), (10, 2), (-10, 2)):
        c.line(bx, by, bx + ddx, by + ddy, RED, 2)
    c.circle(bx, by, 4, RED)

def pact(c, x, y, w, h):
    """Two flags side by side - Australia and the Solomons - with a check."""
    fw, fh = (w - 60) // 2, h - 16
    c.rect(x + 10, y + 8, fw, fh, (28, 48, 88))
    c.text(x + 10 + fw // 2, y + 8 + fh // 2 - 7, 'AU', WHITE, 2, 'center')
    c.rect(x + 30 + fw, y + 8, fw, fh, (201, 162, 39))
    c.text(x + 30 + fw + fw // 2, y + 8 + fh // 2 - 7, 'SB', NAVY, 2, 'center')
    c.line(x + 10 + fw + 4, y + h - 6, x + 30 + fw - 4, y + h - 6, RED, 3)

def rocket(c, x, y, w, h):
    """A rocket lifting off: body, fins, flame, stars."""
    cx = x + w // 2
    top = y + 6
    c.rect(cx - 7, top + 10, 14, h - 34, INK)
    c.line(cx, top, cx - 7, top + 10, INK, 3)
    c.line(cx, top, cx + 7, top + 10, INK, 3)
    c.line(cx - 7, top + 22, cx - 15, top + 34, INK, 3)
    c.line(cx + 7, top + 22, cx + 15, top + 34, INK, 3)
    c.circle(cx, top + 16, 3, GOLD)
    c.hline(x + 12, y + h - 8, w - 24, INK, 3)
    for dx, dy, r in ((0, -4, 7), (-7, 2, 5), (7, 2, 5), (0, 6, 4)):
        c.circle(cx + dx, y + h - 16 + dy, r, RED)
    c.circle(x + 14, y + 10, 3, GOLD)
    c.circle(x + w - 16, y + 18, 3, GOLD)

def nuke(c, x, y, w, h):
    """A missile streaking down toward a radiation trefoil."""
    cx, cy = x + w // 2, y + h // 2
    c.line(x + 10, y + 6, cx, cy - 6, INK, 4)
    c.line(cx, cy - 6, cx + 14, cy + 8, INK, 3)
    c.line(x + 18, y + 14, x + 32, y + 4, INK, 3)
    c.circle(cx + 15, cy - 13, 7, RED)
    c.circle(cx + 3, cy + 8, 6, RED)
    c.circle(cx + 27, cy + 8, 6, RED)
    c.circle(cx + 15, cy + 1, 4, GOLD)
    c.circle(x + w - 14, y + 10, 3, GOLD)
    c.circle(x + 12, y + h - 10, 3, GOLD)

def summit(c, x, y, w, h):
    """Two flags - EU and Ukraine - over a gold table bar."""
    fw, fh = (w - 60) // 2, h - 16
    c.rect(x + 10, y + 8, fw, fh, (28, 48, 88))
    c.text(x + 10 + fw // 2, y + 8 + fh // 2 - 7, 'EU', WHITE, 2, 'center')
    c.rect(x + 30 + fw, y + 8, fw, fh // 2, (0, 91, 172))
    c.rect(x + 30 + fw, y + 8 + fh // 2, fw, fh - fh // 2, (255, 213, 0))
    c.hline(x + 10, y + h - 6, w - 20, GOLD, 3)

def storm(c, x, y, w, h):
    """A storm cloud with driving rain and wind lines."""
    cx, cy = x + w // 2, y + h // 3
    r = max(8, h // 4)
    c.circle(cx - r, cy, r - 2, STEEL)
    c.circle(cx, cy - 4, r, STEEL)
    c.circle(cx + r, cy, r - 2, STEEL)
    c.rect(cx - r - 6, cy, 2 * r + 12, r // 2 + 2, STEEL)
    for k in range(0, w, 24):
        c.line(x + k + 16, y + h - 16, x + k + 10, y + h - 4, STEEL, 3)
    c.line(x + 6, y + 4, x + 34, y + 4, GOLD, 2)
    c.line(x + w - 34, y + 8, x + w - 6, y + 8, GOLD, 2)

# --- Variant B: four-panel grid --------------------------------------------
def draw_image():
    c = Canvas()
    c.rect(0, 0, W, 104, NAVY)
    c.text(36, 22, DATE, GOLD, 5)
    c.text(36, 66, 'THE WORLD IN ONE IMAGE', WHITE, 3)
    c.hline(0, 104, W, GOLD, 4)
    panels = [
        ('1', 'KOREA', 'KIM ORDERS NUCLEAR BUILD-UP',
         "Kim Jong Un orders tactical nuclear weapons deployed across more domains, KCNA says."),
        ('2', 'EUROPE', 'EU SUMMIT OPENS ON UKRAINE CASH',
         "EU leaders open a two-day Brussels summit on a 45-billion-euro Ukraine loan for 2027."),
        ('3', 'AMERICA', 'THANKSGIVING STORM SLAMS US EAST',
         "A nor'easter hits the US Northeast on Thanksgiving Day, threatening the Macy's parade."),
        ('4', 'INDONESIA', 'EX-POLICE CHIEF FACES TRIAL',
         "Former police chief Listyo Sigit faces an ethics hearing over wiretapping and treason."),
    ]
    pw, ph = 468, 380
    for i, (num, kick, head, body) in enumerate(panels):
        x = 36 + (i % 2) * (pw + 20)
        y = 128 + (i // 2) * (ph + 20)
        c.rect(x, y, pw, ph, WHITE)
        c.rect(x, y, pw, 6, RED)
        c.text(x + 18, y + 22, num, GOLD, 8)
        c.text(x + 96, y + 30, kick, RED, 2)
        yy = c.para(x + 18, y + 118, head, INK, 4, pw - 36, leading=38)
        yy = c.para(x + 18, yy + 10, body, INK, 2, pw - 36, leading=18)
        iy = y + ph - 78
        if i == 0:
            nuke(c, x + 18, iy + 4, pw - 36, 48)
        elif i == 1:
            summit(c, x + 18, iy + 4, pw - 36, 48)
        elif i == 2:
            storm(c, x + 18, iy + 4, pw - 36, 48)
        else:
            arrest(c, x + 18, iy + 4, pw - 36, 48)
    c.hline(36, 928, 952, INK, 3)
    c.para(36, 944, "ALSO: North Korea expels Swiss diplomat in sanctions row  -  Rohingya refugees in Malaysia seek more time after ICJ genocide ruling  -  Thai tourist house collapse injures 32 students  -  Karachi building collapse kills three  -  Australia passes law forcing platforms to remove harmful content",
           GREY, 2, 952, leading=17)
    return c.png()



def main():
    data = draw_image()
    out = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'entry.png'), 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    main()
