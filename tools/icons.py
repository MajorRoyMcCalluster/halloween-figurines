"""Shop icons (256x256, transparent) and hero images (512x360) for the figurines, rendered from the built meshes."""
import numpy as np, os, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as RD, model as M, common as C

GREEN = (90, 255, 130)
FOCUS = {"ghost": 0.072, "lanternjack": 0.088}

def fig_rgba(key, W, H, ppu):
    img, cov = RD.render(key, W=W, H=H, yaw=20, pitch=-9, ppu=ppu, focus_y=FOCUS[key], bg=(0, 0, 0))
    rgb = np.asarray(img).astype(np.float32)
    a = Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    glow = np.clip(rgb.max(-1) / 255 - 0.03, 0, 1)
    alpha = np.maximum(np.asarray(a).astype(np.float32) / 255, glow * 0.85)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")

def pedestal(W, H, cx, cy, rx, ry, thick):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([cx - rx, cy - ry + thick, cx + rx, cy + ry + thick], fill=(18, 20, 24, 255))
    d.rectangle([cx - rx, cy, cx + rx, cy + thick], fill=(26, 28, 33, 255))
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(40, 44, 50, 255))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dg = ImageDraw.Draw(g)
    dg.ellipse([cx - rx * 0.86, cy - ry * 0.86, cx + rx * 0.86, cy + ry * 0.86], outline=GREEN + (255,), width=max(2, int(rx * 0.09)))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(rx * 0.06))); im.alpha_composite(g)
    return im

def compose(key, W, H, ppu, bg=None):
    im = bg if bg is not None else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r = fig_rgba(key, W, H, ppu)
    rows = np.where(np.asarray(r)[..., 3].max(1) > 200)[0]
    foot = rows.max()
    im.alpha_composite(pedestal(W, H, W // 2, foot - int(H * 0.02), int(W * 0.25), int(W * 0.066), int(W * 0.045)))
    im.alpha_composite(r)
    return im

def hero_bg(W, H):
    y, x = np.mgrid[0:H, 0:W]; d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    g = np.clip(1 - d * 1.5, 0, 1) ** 1.5
    bg = np.stack([20 + 200 * g, 8 + 70 * g, 26 + 10 * g], -1)                  # pumpkin glow on dusky purple
    bg += np.random.default_rng(3).normal(0, 2.5, bg.shape)
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

def write(out_dir):
    os.makedirs(out_dir, exist_ok=True); prev = os.path.join(C.WORK, "out")
    for f in C.FIGS:
        a = compose(f["key"], 256, 256, 1500); a.save(os.path.join(prev, f"icon_{f['key']}.png"))
        b = compose(f["key"], 512, 360, 1900, hero_bg(512, 360)); b.save(os.path.join(prev, f"hero_{f['key']}.png"))
        M.mip_dds(a, "DXT5", os.path.join(out_dir, f"SPECIAL.{f['icon']}.DDS"))
        M.mip_dds(b, "DXT5", os.path.join(out_dir, f"HERO.{f['icon']}.DDS"))
