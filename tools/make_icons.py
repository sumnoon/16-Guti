"""Draw the Sholo Guti app icon (two guti on carved board lines in packed mud) and write every size needed.

  game/assets/ui/icon-192.png, icon-512.png       web app manifest ("any")
  game/assets/ui/icon-maskable-512.png            web app manifest ("maskable", full bleed)
  game/assets/ui/apple-touch-icon.png             iOS home screen (180 px)
  android/app/src/main/res/mipmap-*/              launcher icons, if the Capacitor Android project exists
  android/app/src/main/res/drawable*/splash.png   splash screens for Android 11 and older

Content stays inside the central 66 % circle, so it survives Android adaptive-icon and maskable cropping.
Colours come from art/art_bible.txt. Needs Pillow and numpy. Run from this folder:  python make_icons.py
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MUD, MUD_EDGE, GROOVE, LIP = (201, 154, 106), (150, 104, 66), (92, 62, 40), (226, 196, 152)
CREAM, SLATE = (238, 228, 205), (78, 86, 96)
SS = 4  # supersampling


def background(s):
    y, x = np.mgrid[0:s, 0:s] / (s - 1) - .5
    t = np.clip(np.hypot(x, y) / .72, 0, 1)[..., None] ** 1.6
    a = np.array(MUD) * (1 - t) + np.array(MUD_EDGE) * t
    rng = np.random.default_rng(16)
    a += rng.normal(0, 3.5, (s, s, 1))  # faint packed-mud grain
    return Image.fromarray(np.uint8(np.clip(a, 0, 255)))


def board(s):
    """Carved grooves: a 2 x 2 patch of the board with its diagonals, dark groove plus a lit lower lip."""
    layer = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c, h, w = s / 2, s * .25, max(2, int(s * .022))
    pts = [(c + i * h, c + j * h) for j in (-1, 0, 1) for i in (-1, 0, 1)]
    lines = [((c - h, c + k * h), (c + h, c + k * h)) for k in (-1, 0, 1)] + [((c + k * h, c - h), (c + k * h, c + h)) for k in (-1, 0, 1)]
    lines += [((c - h, c - h), (c + h, c + h)), ((c + h, c - h), (c - h, c + h))]
    for (a, b) in lines:
        d.line([(a[0], a[1] + w * .55), (b[0], b[1] + w * .55)], fill=LIP + (200,), width=w)
        d.line([a, b], fill=GROOVE + (235,), width=w)
    for p in pts:
        r = w * .9
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=GROOVE + (235,))
    return layer


def pebble(s, centre, rx, ry, colour):
    """Shaded river pebble with a soft contact shadow, lit from the upper left like the game's sun."""
    layer = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    shadow = Image.new('L', (s, s), 0)
    ImageDraw.Draw(shadow).ellipse([centre[0] - rx * .95 + rx * .18, centre[1] - ry * .55 + ry * .55, centre[0] + rx * .95 + rx * .18, centre[1] + ry * .95 + ry * .55], fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(s * .02))
    layer.paste((40, 25, 15, 255), (0, 0), shadow)
    y, x = np.mgrid[0:s, 0:s].astype(float)
    nx, ny = (x - centre[0]) / rx, (y - centre[1]) / ry
    inside = nx ** 2 + ny ** 2 <= 1
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    light = np.array([-.45, -.55, .7]); light /= np.linalg.norm(light)
    lam = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
    spec = np.clip(lam, 0, 1) ** 18 * .35
    rgb = np.array(colour)[None, None, :] * (.38 + .7 * lam[..., None]) + 255 * spec[..., None]
    peb = np.dstack([np.clip(rgb, 0, 255), inside * 255]).astype(np.uint8)
    return Image.alpha_composite(layer, Image.fromarray(peb, 'RGBA'))


def master(size=1024):
    s = size * SS
    img = background(s).convert('RGBA')
    img = Image.alpha_composite(img, board(s))
    c, h = s / 2, s * .25
    img = Image.alpha_composite(img, pebble(s, (c - h * .02, c - h * .98), s * .118, s * .092, SLATE))
    img = Image.alpha_composite(img, pebble(s, (c + h * .02, c + h * .02), s * .128, s * .1, CREAM))
    return img.resize((size, size), Image.LANCZOS)


def rounded(img, radius_frac=.22):
    s = img.size[0]
    mask = Image.new('L', (s * SS, s * SS), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s * SS - 1, s * SS - 1], radius=int(s * SS * radius_frac), fill=255)
    out = img.copy(); out.putalpha(mask.resize((s, s), Image.LANCZOS)); return out


def circle(img):
    s = img.size[0]
    mask = Image.new('L', (s * SS, s * SS), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s * SS - 1, s * SS - 1], fill=255)
    out = img.copy(); out.putalpha(mask.resize((s, s), Image.LANCZOS)); return out


def main():
    full = master(1024)
    ui = ROOT / 'game' / 'assets' / 'ui'; ui.mkdir(parents=True, exist_ok=True)
    for n in (192, 512):
        rounded(full).resize((n, n), Image.LANCZOS).save(ui / f'icon-{n}.png', optimize=True)
    full.convert('RGB').resize((512, 512), Image.LANCZOS).save(ui / 'icon-maskable-512.png', optimize=True)
    full.convert('RGB').resize((180, 180), Image.LANCZOS).save(ui / 'apple-touch-icon.png', optimize=True)
    print('icons  web')
    res = ROOT / 'android' / 'app' / 'src' / 'main' / 'res'
    if not res.is_dir():
        return
    # Legacy icons are 48 dp; adaptive-icon layers are 108 dp with the content in the inner 72 dp.
    for name, scale in [('mdpi', 1), ('hdpi', 1.5), ('xhdpi', 2), ('xxhdpi', 3), ('xxxhdpi', 4)]:
        d = res / f'mipmap-{name}'; d.mkdir(exist_ok=True)
        legacy, layer = round(48 * scale), round(108 * scale)
        rounded(full, .18).resize((legacy, legacy), Image.LANCZOS).save(d / 'ic_launcher.png', optimize=True)
        circle(full).resize((legacy, legacy), Image.LANCZOS).save(d / 'ic_launcher_round.png', optimize=True)
        full.convert('RGB').resize((layer, layer), Image.LANCZOS).save(d / 'ic_launcher_foreground.png', optimize=True)
    # Pre-Android-12 splash: the page's soil colour with the icon in the middle, at each template size.
    for splash in res.glob('drawable*/splash.png'):
        w, h = Image.open(splash).size
        icon = rounded(full).resize((int(min(w, h) * .3),) * 2, Image.LANCZOS)
        img = Image.new('RGBA', (w, h), (38, 24, 15, 255))
        img.alpha_composite(icon, ((w - icon.width) // 2, (h - icon.height) // 2))
        img.convert('RGB').save(splash, optimize=True)
    print('icons  android (launcher + splash)')


if __name__ == '__main__':
    main()
