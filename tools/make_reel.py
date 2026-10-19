# Click Mali reel generator.
# Usage: python3 make_reel.py reel.json out.mp4 [stills: 1.4,4.5,...]
# reel.json: {"image": "product.jpg", "headline": "...", "feature": "...", "chip": "...",
#             "hook_sub": "...", "price": 8.09, "was": 16.15, "rating": 4.9, "orders": 11046}
# Needs: Pillow with raqm (Hebrew RTL), ffmpeg, DejaVu fonts.
import math, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features

W, H, FPS = 1080, 1920, 30
DUR = 16.5
BG = (18, 21, 34)
BG2 = (26, 30, 46)
ORANGE = (242, 68, 27)
WHITE = (237, 240, 246)
MUTED = (154, 162, 182)
GREEN = (63, 208, 143)

BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
_fc = {}
def F(size, path=BOLD):
    k = (size, path)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]

import json
CFG = json.load(open(sys.argv[1], encoding='utf-8'))
HERE = CFG.get('workdir', '.')
OUT = sys.argv[2]
prod = Image.open(CFG['image']).convert('RGB')
w0, h0 = prod.size; side = min(w0, h0)
prod = prod.crop(((w0 - side) // 2, (h0 - side) // 2, (w0 + side) // 2, (h0 + side) // 2))
def money(v):
    v = float(v); return str(int(v)) if abs(v - round(v)) < 0.05 else f'{v:.1f}'
PRICE, WAS = money(CFG['price']), money(CFG['was'])
OFF = round((1 - float(CFG['price']) / float(CFG['was'])) * 100)
ORDERS = int(CFG['orders'])

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def prog(t, a, b): return clamp((t - a) / (b - a))

def text_size(txt, font, rtl=True):
    bb = font.getbbox(txt, direction='rtl' if rtl else 'ltr')
    return bb[2] - bb[0], bb[3] - bb[1], bb

def fit(txt, size, max_w=960, path=BOLD, rtl=True):
    while size > 24 and text_size(txt, F(size, path), rtl)[0] > max_w: size -= 4
    return F(size, path)

def draw_text(img, txt, font, cy, fill, cx=W / 2, rtl=True, scale=1.0, alpha=1.0):
    """Draw text centered at (cx, cy), with optional scale and alpha."""
    if alpha <= 0 or scale <= 0: return
    w, h, bb = text_size(txt, font, rtl)
    pad = 20
    layer = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((pad - bb[0], pad - bb[1]), txt, font=font, fill=fill + (255,), direction='rtl' if rtl else 'ltr')
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.LANCZOS)
    if alpha < 1:
        a = layer.getchannel('A').point(lambda v: int(v * alpha)); layer.putalpha(a)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

def rounded(img, box, r, fill, alpha=1.0):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, r, fill=fill + (int(255 * alpha),))
    img.alpha_composite(layer)

def shadow(img, box, r, strength=110, blur=40, dy=30):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    ImageDraw.Draw(layer).rounded_rectangle((x0, y0 + dy, x1, y1 + dy), r, fill=(0, 0, 0, strength))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))

def product_card(img, cx, cy, size, angle=0.0, alpha=1.0):
    pad = int(size * 0.06)
    card = Image.new('RGBA', (size + pad * 2, size + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, card.width - 1, card.height - 1), int(size * 0.07), fill=(255, 255, 255, 255))
    p = prod.resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size, size), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), int(size * 0.05), fill=255)
    card.paste(p, (pad, pad), m)
    if angle: card = card.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = card.getchannel('A').point(lambda v: int(v * alpha)); card.putalpha(a)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((cx - card.width / 2 + 20, cy - card.height / 2 + 40, cx + card.width / 2 - 20, cy + card.height / 2 + 40), 40, fill=(0, 0, 0, int(120 * alpha)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(40)))
    img.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))

def star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=fill)

def cursor_mark(img, cx, cy, s, color=WHITE):
    """The brand mark: click rays + arrow cursor, on a 24-unit grid."""
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    k = s / 24.0; ox, oy = cx - 12 * k, cy - 12 * k
    P = lambda x, y: (ox + x * k, oy + y * k)
    lw = max(3, int(2.4 * k))
    for a, b in [((9, 2.5), (9, 7)), ((3.8, 4.8), (7, 8)), ((2.5, 10), (7, 10))]:
        d.line([P(*a), P(*b)], fill=color + (255,), width=lw)
    d.polygon([P(11, 11), P(21, 14.8), P(16.6, 16.6), P(14.8, 21)], fill=color + (255,))
    img.alpha_composite(layer)

def brand_strip(img, t):
    # dashed orange strip along the bottom, scrolling slowly (brand detail from the site/banner)
    layer = Image.new('RGBA', (W, 22), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    off = int(t * 60) % 44
    for x in range(-44, W + 44, 44):
        d.rectangle((x + off, 0, x + off + 28, 21), fill=ORANGE + (255,))
    img.alpha_composite(layer, (0, H - 22))

def header(img, alpha=1.0):
    if alpha <= 0: return
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((W / 2 - 230, 96, W / 2 + 230, 176), 40, fill=(255, 255, 255, int(22 * alpha)))
    img.alpha_composite(layer)
    draw_text(img, 'קליק מאלי', F(46), 136, WHITE, cx=W / 2 - 30, alpha=alpha)
    m = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(m).rounded_rectangle((W / 2 + 120, 112, W / 2 + 168, 160), 12, fill=ORANGE + (int(255 * alpha),))
    img.alpha_composite(m)
    cursor_mark(img, W / 2 + 144, 136, 36)

def background(t):
    img = Image.new('RGBA', (W, H), BG + (255,))
    # soft orange glow that drifts, plus dashed postmark ring (brand motif)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(glow)
    gx = W * 0.5 + 160 * math.sin(t * 0.6); gy = H * 0.42 + 120 * math.cos(t * 0.45)
    d.ellipse((gx - 520, gy - 520, gx + 520, gy + 520), fill=ORANGE + (46,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
    ring = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ring)
    cx, cy, R = W - 60, 300, 330
    rot = t * 0.15
    for i in range(48):
        a0 = rot + i * 2 * math.pi / 48; a1 = a0 + math.pi / 48 * 0.9
        d.arc((cx - R, cy - R, cx + R, cy + R), math.degrees(a0), math.degrees(a1), fill=(237, 240, 246, 30), width=5)
    img.alpha_composite(ring)
    return img

# ---------- scenes ----------
def s1(t):  # hook 0 - 2.8
    img = background(t)
    draw_text(img, 'TRACKING · ALIEXPRESS → ISRAEL', F(30, MONO), 250, MUTED, rtl=False, alpha=ease_out(prog(t, 0, .4)))
    draw_text(img, CFG['headline'], fit(CFG['headline'], 112), 420, WHITE, scale=0.6 + 0.4 * ease_back(prog(t, 0.05, .45)), alpha=ease_out(prog(t, 0.05, .3)))
    sc = ease_back(prog(t, .35, .85))
    draw_text(img, f'ב-{PRICE}₪', fit(f'ב-{PRICE}₪', 290), 650, ORANGE, scale=sc * (1 + 0.03 * math.sin(t * 9)) if sc > 0 else 0, alpha=ease_out(prog(t, .35, .5)))
    draw_text(img, CFG.get('hook_sub', 'כן, באמת.'), fit(CFG.get('hook_sub', 'כן, באמת.'), 56), 850, WHITE, alpha=ease_out(prog(t, .8, 1.05)))
    y = 1330 + 700 * (1 - ease_out(prog(t, .5, 1.2)))
    product_card(img, W / 2, y, 640, angle=-4 + 2 * math.sin(t * 2))
    return img

def s2(t):  # what it is 2.8 - 6.2
    lt = t - 2.8
    img = background(t); header(img)
    z = 1.0 + 0.05 * prog(lt, 0, 3.4)
    product_card(img, W / 2, 860, int(700 * z), angle=0)
    draw_text(img, CFG['feature'], fit(CFG['feature'], 70), 1420, WHITE, alpha=ease_out(prog(lt, .2, .5)), scale=0.8 + 0.2 * ease_out(prog(lt, .2, .5)))
    a = ease_out(prog(lt, .7, 1.0))
    if a > 0:
        cf = fit(CFG['chip'], 54, 860); w, h, _ = text_size(CFG['chip'], cf)
        y = 1560 + 40 * (1 - a)
        rounded(img, (W / 2 - w / 2 - 44, y - 56, W / 2 + w / 2 + 44, y + 56), 56, ORANGE, alpha=a)
        draw_text(img, CFG['chip'], cf, y, (255, 255, 255), alpha=a)
    return img

def s3(t):  # social proof 6.2 - 9.8
    lt = t - 6.2
    img = background(t); header(img)
    product_card(img, W / 2, 470, 380, angle=-5)
    a = ease_out(prog(lt, .1, .4))
    draw_text(img, str(CFG['rating']), F(260), 930, WHITE, alpha=a, scale=0.7 + 0.3 * ease_back(prog(lt, .1, .5)))
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for i in range(5):
        p = ease_back(prog(lt, .35 + i * .1, .6 + i * .1))
        if p > 0:
            star(d, W / 2 + (i - 2) * 132, 1140, 54 * p, ORANGE + (255,))
    img.alpha_composite(layer)
    n = int(ORDERS * ease_out(prog(lt, .6, 2.0)))
    draw_text(img, f'{n:,}', F(150), 1380, ORANGE, rtl=False, alpha=ease_out(prog(lt, .6, .8)))
    draw_text(img, 'הזמנות באלי אקספרס', F(64), 1530, WHITE, alpha=ease_out(prog(lt, .8, 1.1)))
    return img

def s4(t):  # price 9.8 - 13.4
    lt = t - 9.8
    img = background(t); header(img)
    draw_text(img, 'המחיר הרגיל', F(60, REG), 430, MUTED, alpha=ease_out(prog(lt, 0, .3)))
    draw_text(img, f'{WAS}₪', fit(f'{WAS}₪', 190, 700), 600, MUTED, alpha=ease_out(prog(lt, 0, .3)))
    s = ease_out(prog(lt, .5, .9))
    if s > 0:
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        x0 = W / 2 - 230; d.line([(x0, 640), (x0 + 460 * s, 560)], fill=ORANGE + (255,), width=18)
        img.alpha_composite(layer)
    draw_text(img, 'עכשיו רק', F(70), 860, WHITE, alpha=ease_out(prog(lt, .9, 1.2)))
    sc = ease_back(prog(lt, 1.1, 1.6))
    draw_text(img, f'{PRICE}₪', fit(f'{PRICE}₪', 420, 900), 1150, ORANGE, scale=sc * (1 + 0.025 * math.sin(lt * 8)) if sc > 0 else 0, alpha=ease_out(prog(lt, 1.1, 1.25)))
    b = ease_back(prog(lt, 1.6, 2.0))
    if b > 0:
        layer = Image.new('RGBA', (360, 140), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((0, 0, 359, 139), 30, fill=(255, 255, 255, 255))
        dl = ImageDraw.Draw(layer)
        f = F(84); bb = f.getbbox(f'-{OFF}%', direction='ltr')
        dl.text((180 - (bb[2] - bb[0]) / 2 - bb[0], 70 - (bb[3] - bb[1]) / 2 - bb[1]), f'-{OFF}%', font=f, fill=BG + (255,))
        layer = layer.rotate(8, resample=Image.BICUBIC, expand=True)
        layer = layer.resize((max(1, int(layer.width * b)), max(1, int(layer.height * b))), Image.LANCZOS) if b != 1 else layer
        img.alpha_composite(layer, (int(W / 2 + 230 - layer.width / 2), int(1450 - layer.height / 2)))
    draw_text(img, 'מחיר בשקלים, משלוח לישראל', F(52, REG), 1640, MUTED, alpha=ease_out(prog(lt, 1.8, 2.1)))
    return img

def s5(t):  # CTA 13.4 - 16.5
    lt = t - 13.4
    img = background(t)
    p = ease_back(prog(lt, 0, .5))
    if p > 0:
        sz = int(220 * p)
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((W / 2 - sz / 2, 470 - sz / 2, W / 2 + sz / 2, 470 + sz / 2), int(sz * .24), fill=ORANGE + (255,))
        img.alpha_composite(layer)
        cursor_mark(img, W / 2, 470, int(sz * .62))
    draw_text(img, 'קליק מאלי', F(150), 760, WHITE, alpha=ease_out(prog(lt, .25, .5)), scale=0.85 + 0.15 * ease_out(prog(lt, .25, .5)))
    draw_text(img, 'הדילים הכי שווים מאלי, בקליק', F(52, REG), 890, MUTED, alpha=ease_out(prog(lt, .45, .7)))
    a = ease_out(prog(lt, .7, 1.0))
    if a > 0:
        w, h, _ = text_size('הקישור בתגובה הראשונה', F(68))
        rounded(img, (W / 2 - w / 2 - 60, 1130, W / 2 + w / 2 + 60, 1270), 70, ORANGE, alpha=a)
        draw_text(img, 'הקישור בתגובה הראשונה', F(68), 1200, (255, 255, 255), alpha=a)
        by = 1360 + 26 * math.sin(lt * 7)
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon([(W / 2 - 60, by), (W / 2 + 60, by), (W / 2, by + 70)], fill=WHITE + (int(255 * a),))
        img.alpha_composite(layer)
    draw_text(img, 'clickmali.netlify.app', F(58, MONO), 1600, WHITE, rtl=False, alpha=ease_out(prog(lt, 1.0, 1.3)))
    draw_text(img, 'דילים חדשים כל יום · עקבו אחרינו', F(48, REG), 1700, MUTED, alpha=ease_out(prog(lt, 1.2, 1.5)))
    draw_text(img, '* קישור שותפים, בלי עלות נוספת לכם', F(34, REG), 1810, MUTED, alpha=0.8 * ease_out(prog(lt, 1.4, 1.7)))
    return img

SCENES = [(0, 2.8, s1), (2.8, 6.2, s2), (6.2, 9.8, s3), (9.8, 13.4, s4), (13.4, DUR, s5)]
XF = 0.22

def frame(t):
    for i, (a, b, fn) in enumerate(SCENES):
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            img = fn(t)
            # crossfade into next scene near the boundary, with a slight push
            if i + 1 < len(SCENES) and t > b - XF:
                k = (t - (b - XF)) / XF
                nxt = SCENES[i + 1][2](b + 0.0001)
                img = Image.blend(img, nxt, ease_out(k))
            brand_strip(img, t)
            return img.convert('RGB')

if __name__ == '__main__':
    if len(sys.argv) > 3:  # preview stills
        for ts in sys.argv[3].split(','):
            frame(float(ts)).save(f'{OUT}_still_{ts}.jpg', quality=85)
        sys.exit()
    n = int(DUR * FPS)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                          '-shortest', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                          '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    print('done', OUT)
