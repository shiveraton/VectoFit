from PIL import Image
from pathlib import Path

source = Path("vectofit_logo.png")

sizes = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

image = Image.open(source).convert("RGBA")

for density, size in sizes.items():
    resized = image.resize(
        (size, size),
        Image.Resampling.LANCZOS
    )

    output = Path(f"ic_launcher_{density}.png")
    resized.save(output)

    print(f"Created {output}: {size}x{size}")