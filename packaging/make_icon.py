"""Generate the SkyAdmin Pro application icons (.ico, .icns, .png)."""

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO_PNG = ROOT / "logo.png"
SOURCE_LOGO_JPG = ROOT / "logo.jpg"
OUT_ICO = ROOT / "icon.ico"
OUT_ICNS = ROOT / "icon.icns"
OUT_PNG = ROOT / "icon.png"

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def load_source() -> Image.Image:
    if SOURCE_LOGO_PNG.is_file():
        return Image.open(SOURCE_LOGO_PNG).convert("RGBA")
    if SOURCE_LOGO_JPG.is_file():
        return Image.open(SOURCE_LOGO_JPG).convert("RGBA")
    raise FileNotFoundError(f"Source logo not found: {SOURCE_LOGO_PNG} or {SOURCE_LOGO_JPG}")


def resize_image(img: Image.Image, size: int) -> Image.Image:
    # Use LANCZOS for high-quality downsampling
    return img.resize((size, size), Image.Resampling.LANCZOS)


def write_ico(path: Path, images: list[Image.Image]) -> None:
    """Write a multi-size .ico using PNG-compressed entries (Vista+ compatible)."""
    # Windows typically supports up to 256x256 in ICO
    ico_sizes = [s for s in ICON_SIZES if s <= 256]
    ico_images = [resize_image(images[0], s) for s in ico_sizes]

    pngs = []
    for image in ico_images:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pngs.append(buffer.getvalue())

    header = b"\x00\x00" + struct.pack("<HH", 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = bytearray()
    payload = bytearray()
    for size, data in zip(ico_sizes, pngs, strict=True):
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


def write_icns(path: Path, source_img: Image.Image) -> None:
    """Write an macOS .icns file."""
    # Pillow's ICNS saver requires a single image, it handles sizes automatically
    try:
        source_img.save(path, format="ICNS")
    except Exception as e:
        print(f"Failed to save .icns: {e}")


def main() -> None:
    try:
        source_img = load_source()

        # Make it square if it's not (pad with transparent)
        width, height = source_img.size
        if width != height:
            size = max(width, height)
            square = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            square.paste(source_img, ((size - width) // 2, (size - height) // 2))
            source_img = square

        write_ico(OUT_ICO, [source_img])
        print(f"Wrote {OUT_ICO} ({OUT_ICO.stat().st_size} bytes)")

        write_icns(OUT_ICNS, source_img)
        if OUT_ICNS.exists():
            print(f"Wrote {OUT_ICNS} ({OUT_ICNS.stat().st_size} bytes)")

        # Save a high-res PNG
        png_img = resize_image(source_img, 512)
        png_img.save(OUT_PNG, format="PNG")
        print(f"Wrote {OUT_PNG}")

    except Exception as e:
        print(f"Error generating icons: {e}")


if __name__ == "__main__":
    main()
