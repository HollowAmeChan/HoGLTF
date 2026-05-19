import json
from array import array
from pathlib import Path

import bpy

OUT_PATH = Path(r"D:\Unity_Fork\mmd_probe\texture_alpha_scan.json")


def scan_image(image):
    # Force-load the image before reading pixels.
    pixel_count = len(image.pixels)
    pixels = array("f", [0.0]) * pixel_count
    image.pixels.foreach_get(pixels)
    alphas = pixels[3::4]
    total = len(alphas)
    min_alpha = min(alphas) if total else 1.0
    max_alpha = max(alphas) if total else 1.0
    zero_count = sum(1 for alpha in alphas if alpha <= 0.001)
    mid_count = sum(1 for alpha in alphas if 0.001 < alpha < 0.999)
    opaque_count = sum(1 for alpha in alphas if alpha >= 0.999)
    return {
        "name": image.name,
        "filepath": bpy.path.abspath(image.filepath),
        "size": list(image.size),
        "colorspace": image.colorspace_settings.name,
        "alpha_mode": image.alpha_mode,
        "min_alpha": float(min_alpha),
        "max_alpha": float(max_alpha),
        "zero_alpha_pixels": zero_count,
        "mid_alpha_pixels": mid_count,
        "opaque_alpha_pixels": opaque_count,
        "total_pixels": total,
        "has_cutout_alpha": zero_count > 0,
        "has_blend_alpha": mid_count > 0,
    }


def main():
    names = ["TEXB10.png", "TEXA2.png", "T.png"]
    records = []
    for name in names:
        image = bpy.data.images.get(name)
        if image is None:
            records.append({"name": name, "missing": True})
            continue
        records.append(scan_image(image))

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT_PATH}")


if __name__ == "__main__":
    main()
