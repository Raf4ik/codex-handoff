from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "src" / "codex_handoff" / "assets" / "codex-handoff.svg"
RUNTIME_PNG = ROOT / "src" / "codex_handoff" / "assets" / "codex-handoff.png"
ICONS_DIR = ROOT / "build" / "icons"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
MACOS_ICONSET = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def render_svg(renderer: QSvgRenderer, output: Path, size: int) -> None:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output), "PNG"):
        raise RuntimeError(f"Failed to write {output}")


def main() -> None:
    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {SVG_PATH}")

    render_svg(renderer, RUNTIME_PNG, 1024)
    for size in ICON_SIZES:
        render_svg(renderer, ICONS_DIR / f"icon-{size}.png", size)

    iconset_dir = ICONS_DIR / "CodexHandoff.iconset"
    for filename, size in MACOS_ICONSET.items():
        render_svg(renderer, iconset_dir / filename, size)

    with Image.open(RUNTIME_PNG) as source:
        source.save(
            ICONS_DIR / "codex-handoff.ico",
            format="ICO",
            sizes=[(size, size) for size in ICON_SIZES],
        )


if __name__ == "__main__":
    main()
