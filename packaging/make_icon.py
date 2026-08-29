"""Generate the SkyAdmin Pro application icon (.ico)."""

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icon.ico"
OUT_PNG = ROOT / "icon.png"

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw(size: int) -> Image.Image:
    scale = size / 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = int(56 * scale)
    # rounded-square background with a sky-blue gradient
    for y in range(size):
        t = y / size
        r = int(37 + 40 * t)
        g = int(99 + 40 * t)
        b = int(235 - 30 * t)
        draw.rectangle(
            [(radius, y), (size - radius, y + 1)],
            fill=(r, g, b, 255),
        )
    # fill top/bottom rounded corners by re-drawing rounded rectangle mask
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / size
        r = int(37 + 40 * t)
        g = int(99 + 40 * t)
        b = int(235 - 30 * t)
        bg.paste((r, g, b, 255), (0, y, size, y + 1))
    img = Image.composite(bg, img, mask)

    draw = ImageDraw.Draw(img)
    # white document sheet
    pad = int(62 * scale)
    doc = [pad, int(52 * scale), size - pad, size - int(52 * scale)]
    draw.rounded_rectangle(doc, radius=int(18 * scale), fill=(255, 255, 255, 255))

    # folded corner
    fold = int(88 * scale)
    corner = [
        (size - fold, int(52 * scale)),
        (size - pad, int(52 * scale)),
        (size - pad, fold),
    ]
    draw.polygon(corner, fill=(214, 224, 240, 255))

    # text lines (sky blue)
    line_color = (66, 122, 235, 255)
    for i, width in enumerate((0.52, 0.62, 0.44)):
        y0 = int((110 + i * 30) * scale)
        x0 = pad + int(16 * scale)
        x1 = x0 + int(size * width)
        draw.rounded_rectangle([x0, y0, x1, y0 + int(14 * scale)], radius=int(7 * scale), fill=line_color)

    # check mark accent
    cx = int(size * 0.62)
    cy = int(size * 0.80)
    r = int(30 * scale)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(46, 204, 113, 255))
    draw.line(
        [(cx - r * 0.55, cy), (cx - r * 0.12, cy + r * 0.45), (cx + r * 0.6, cy - r * 0.4)],
        fill=(255, 255, 255, 255),
        width=max(3, int(7 * scale)),
        joint="curve",
    )
    return img


def write_ico(path: Path, images: list[Image.Image]) -> None:
    """Write a multi-size .ico using PNG-compressed entries (Vista+ compatible)."""
    pngs = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pngs.append(buffer.getvalue())

    header = b"\x00\x00" + struct.pack("<HH", 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = bytearray()
    payload = bytearray()
    for size, data in zip(ICON_SIZES, pngs, strict=True):
        width = size if size < 256 else 0
        entries += struct.pack(
            "<BBBBHHII",
            width,
            width,
            0,
            0,
            1,
            32,
            len(data),
            offset,
        )
        payload += data
        offset += len(data)
    path.write_bytes(header + bytes(entries) + bytes(payload))


def main() -> None:
    images = [draw(size) for size in ICON_SIZES]
    write_ico(OUT, images)
    images[-1].save(OUT_PNG, format="PNG")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes, {len(images)} sizes)")
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
