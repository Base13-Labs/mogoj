#!/usr/bin/env python3
"""Render the deterministic README terminal demo GIF (development only)."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "assets" / "terminal-demo.gif"
SCENES = [
    ["$ curl …/install.sh | sh", "✓ Mogoj 0.1.0-beta.1 installed", "$ mogoj onboard", "✓ Private store ready at ~/.mogoj"],
    ["$ mogoj save \"We chose SQLite for local search.\"", "✓ Saved: docs/decisions/2026-10-10-local-search.md"],
    ["$ mogoj rebuild", "✓ Backup created", "✓ Rebuild complete; Markdown was not deleted"],
    ["$ mogoj search \"Why SQLite?\"", "[docs/decisions/2026-10-10-local-search.md:L1-L3]", "We chose SQLite for local search.", "[72 estimated tokens; within budget]"],
]


def font(size):
    for path in ("/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    history = []
    for scene in SCENES:
        history.extend(scene + [""])
        image = Image.new("RGB", (1000, 520), "#0b1020")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((18, 18, 982, 502), radius=18, fill="#111827", outline="#334155", width=2)
        draw.ellipse((42, 40, 58, 56), fill="#fb7185")
        draw.ellipse((68, 40, 84, 56), fill="#fbbf24")
        draw.ellipse((94, 40, 110, 56), fill="#34d399")
        draw.text((132, 36), "Mogoj — local AI memory", font=font(22), fill="#cbd5e1")
        y = 86
        for line in history[-13:]:
            color = "#67e8f9" if line.startswith("$") else "#e5e7eb"
            if line.startswith("✓") or line.startswith("["):
                color = "#86efac"
            draw.text((46, y), line, font=font(21), fill=color)
            y += 31
        frames.append(image)
    frames[0].save(OUTPUT, save_all=True, append_images=frames[1:], duration=[1300] * len(frames), loop=0, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
