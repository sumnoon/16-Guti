"""Make generated textures tile and panoramas wrap. Reads production/source/, writes textures/ and panoramas/.

Textures: overlap search (aligns repeating weaves/corrugation), min-cut seams on both axes, low-frequency
lighting flattened out of the base colour, resampled to 1024 px, plus a derived tangent-space normal map.
Panoramas: min-cut horizontal wrap, pole rows blended to a constant colour, resampled to 2048 x 1024.
Requires numpy and Pillow.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'production' / 'source'
TEX_SIZE = 1024
PANO_SIZE = (2048, 1024)
# Mean surface tilt (|xy| of the unit normal) each normal map is scaled to. Calibrated against the
# shipped game's maps: smooth swept mud stays subtle, rough soil, straw and bark read more strongly.
NORMAL_TILT = {'uthan_tex_ground_mud': .09, 'uthan_tex_ground_rough': .22, 'uthan_tex_wall_mud': .11, 'support_stone': .08,
               'uthan_tex_roof_tin': .16, 'uthan_tex_fence_bamboo': .14, 'uthan_tex_mat_jute': .13, 'uthan_tex_straw': .2, 'uthan_tex_bark_banyan': .2}


def load(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float64) / 255.


def save(a, path):
    Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255 + .5)).save(path, optimize=True)


def best_overlap(img, lo, hi, band):
    """Overlap width whose wrap shift best matches existing content (finds pattern periods)."""
    w = img.shape[1]
    errs = {ov: float(((img[:, w - ov:w - ov + band] - img[:, :band]) ** 2).mean()) for ov in range(lo, hi + 1)}
    return min(errs, key=errs.get)


def min_cut(cost, start=None):
    """Vertical path (one column per row) of minimum cost; with start, the path must end within 1 px of it."""
    h, w = cost.shape
    acc = np.full((h, w), np.inf)
    back = np.zeros((h, w), dtype=np.int64)
    acc[0] = cost[0] if start is None else np.where(np.arange(w) == start, cost[0], np.inf)
    for y in range(1, h):
        prev = acc[y - 1]
        cand = np.stack([np.r_[np.inf, prev[:-1]], prev, np.r_[prev[1:], np.inf]])
        k = cand.argmin(0)
        acc[y] = cost[y] + cand[k, np.arange(w)]
        back[y] = np.arange(w) + k - 1
    last = acc[-1].copy()
    if start is not None:
        last[np.abs(np.arange(w) - start) > 1] = np.inf
    path = np.zeros(h, dtype=np.int64)
    path[-1] = int(last.argmin())
    for y in range(h - 1, 0, -1):
        path[y - 1] = back[y, path[y]]
    return path, float(last.min())


def wrap_horizontal(img, ov, circular=False, feather=3):
    """Drop ov columns so the right edge continues into the left edge, joined along a min-cost seam."""
    h, w = img.shape[:2]
    a, b = img[:, w - ov:], img[:, :ov]      # a continues the right edge, b is the original left edge
    cost = ((a - b) ** 2).sum(2)
    cost[:, :feather + 1] = cost[:, -feather - 1:] = 1e6   # keep the feathered seam inside the overlap
    if circular:   # the cut must meet itself across the other axis' wrap
        options = [min_cut(cost, s) for s in range(feather + 1, ov - feather - 1, max(1, ov // 24))]
        path = min(options, key=lambda r: r[1])[0]
    else:
        path = min_cut(cost)[0]
    x = np.arange(ov)[None, :]
    t = np.clip((x - path[:, None] + feather) / (2 * feather), 0, 1)[..., None]
    out = img[:, :w - ov].copy()
    out[:, :ov] = a * (1 - t) + b * t
    return out


def equalize_wrap(img, k=32, sigma=12):
    """Spread the right/left edge colour difference across the full width as a ramp, so broad
    brightness and hue match at the wrap before the min-cut handles detail."""
    w = img.shape[1]
    diff = img[:, -k:].mean(1) - img[:, :k].mean(1)
    rows = np.arange(img.shape[0])
    kernel = np.exp(-.5 * ((rows[:, None] - rows[None, :]) / sigma) ** 2)
    diff = (kernel @ diff) / kernel.sum(1)[:, None]
    ramp = np.linspace(-.5, .5, w)[None, :, None]
    return np.clip(img - diff[:, None, :] * ramp, 0, 1)


def blur_wrap(a, sigma):
    """Gaussian blur with periodic boundaries (FFT), so tiled images stay seamless."""
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=a.shape)


def luminance(a):
    return a @ np.array([.2126, .7152, .0722])


def flatten_lighting(img, strength=.85):
    """Divide out broad brightness gradients (baked sun / vignetting) while keeping material colour."""
    lum = luminance(img)
    low = blur_wrap(lum, img.shape[0] / 10)
    gain = (low.mean() / np.maximum(low, 1e-3)) ** strength
    return np.clip(img * gain[..., None], 0, 1)


def normal_map(albedo, tilt):
    h = luminance(albedo)
    h = h - blur_wrap(h, 24)                  # keep relief detail, drop the colour-driven slope
    h = blur_wrap(h, 1.2)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
    g = np.hypot(dx, dy)
    lo, hi = 0., 1e4                          # bisect the gain that gives the target mean tilt
    for _ in range(60):
        k = (lo + hi) / 2
        lo, hi = (k, hi) if np.mean(k * g / np.sqrt(1 + (k * g) ** 2)) < tilt else (lo, k)
    n = np.dstack([-dx * k, dy * k, np.ones_like(h)])   # glTF / OpenGL: +Y up
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5


def edge_errors(a):
    a = a * 255
    return dict(horizontal_wrap_error=round(float(np.abs(a[:, 0] - a[:, -1]).mean()), 2),
                vertical_wrap_error=round(float(np.abs(a[0] - a[-1]).mean()), 2),
                interior_neighbor_error=round(float(np.abs(a[:, 1:] - a[:, :-1]).mean()), 2))


def resize(a, size):
    return np.asarray(Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255 + .5)).resize(size, Image.LANCZOS), dtype=np.float64) / 255.


def process_texture(path):
    img = equalize_wrap(load(path))
    w = img.shape[1]
    band = w // 20
    ovx = best_overlap(img, w // 16, w // 5, band)
    img = wrap_horizontal(img, ovx)
    imgT = equalize_wrap(img.transpose(1, 0, 2))
    ovy = best_overlap(imgT, w // 16, w // 5, band)
    img = wrap_horizontal(imgT, ovy, circular=True).transpose(1, 0, 2)
    img = flatten_lighting(img)
    img = resize(img, (TEX_SIZE, TEX_SIZE))
    save(img, ROOT / 'textures' / f'{path.stem}.png')
    nm = normal_map(img, NORMAL_TILT.get(path.stem, .14))
    save(nm, ROOT / 'textures' / f'{path.stem}_normal.png')
    return dict(name=path.stem, size=[TEX_SIZE, TEX_SIZE], source_size=list(Image.open(path).size), overlap_px=[ovx, ovy],
                source=edge_errors(load(path)), result=edge_errors(img), normal_map=f'textures/{path.stem}_normal.png')


def process_panorama(path):
    img = equalize_wrap(load(path))
    w = img.shape[1]
    ov = best_overlap(img, w // 40, w // 12, w // 100)
    img = wrap_horizontal(img, ov, feather=10)
    h = img.shape[0]
    band = int(h * .07)
    for rows, edge in [(np.arange(band), 0), (np.arange(h - band, h), h - 1)]:
        t = (1 - np.abs(rows - edge) / band) ** 2          # 1 at the pole row, 0 at the band edge
        mean = img[rows].mean(1, keepdims=True)
        pole = img[edge].mean(0)
        target = mean * (1 - t[:, None, None]) + pole * t[:, None, None]
        img[rows] = img[rows] * (1 - t[:, None, None]) + target * t[:, None, None]
    img = resize(img, PANO_SIZE)
    save(img, ROOT / 'panoramas' / f'{path.stem}.png')
    a = img * 255
    return dict(name=path.stem, size=list(PANO_SIZE), source_size=list(Image.open(path).size), overlap_px=ov,
                horizontal_wrap_error=round(float(np.abs(a[:, 0] - a[:, -1]).mean()), 2),
                source_horizontal_wrap_error=round(float(np.abs(load(path)[:, 0] - load(path)[:, -1]).mean() * 255), 2),
                top_row_std=round(float(a[0].std(0).mean()), 2), bottom_row_std=round(float(a[-1].std(0).mean()), 2),
                interior_neighbor_error=round(float(np.abs(a[:, 1:] - a[:, :-1]).mean()), 2))


if __name__ == '__main__':
    (ROOT / 'textures').mkdir(exist_ok=True)
    (ROOT / 'panoramas').mkdir(exist_ok=True)
    report = dict(textures=[], panoramas=[])
    for p in sorted((SRC / 'textures').glob('*.png')):
        report['textures'].append(process_texture(p))
        print(json.dumps(report['textures'][-1]))
    for p in sorted((SRC / 'panoramas').glob('*.png')):
        report['panoramas'].append(process_panorama(p))
        print(json.dumps(report['panoramas'][-1]))
    (ROOT / 'production' / 'image_processing.json').write_text(json.dumps(report, indent=2))
