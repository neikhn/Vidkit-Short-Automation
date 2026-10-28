from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .storage import Workspace


def _font(workspace: Workspace, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(workspace.project_root / "renderer/library/fonts/NotoSans-Bold.ttf"), size)


def _wrap(draw: ImageDraw.ImageDraw, value: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def render_brief_frames(workspace: Workspace, job_id: str, language: str,
                        frames: dict[str, Any], theme: str, revision: int) -> dict[str, str]:
    from .library import show
    style = show(workspace, theme)["style"]
    background, foreground, accent = style["background"], style["text"], style["accent"]
    output: dict[str, str] = {}
    root = workspace.area(job_id, language, "briefs") / f"frames.r{revision}"
    root.mkdir(parents=True, exist_ok=True)
    for name in ("hook", "evidence", "takeaway"):
        frame = frames[name]
        image = Image.new("RGB", (1080, 1920), background)
        draw = ImageDraw.Draw(image)
        if theme == "dark-grid":
            for x in range(0, 1080, 76):
                draw.line((x, 0, x, 1920), fill="#11283f", width=2)
            for y in range(0, 1920, 76):
                draw.line((0, y, 1080, y), fill="#11283f", width=2)
        title_size = 80
        title_font = _font(workspace, title_size)
        body_font = _font(workspace, 40)
        draw.rounded_rectangle((70, 240, 1010, 260), radius=9, fill=accent)
        top = 350
        title_lines = _wrap(draw, frame["headline"], title_font, 920)
        while len(title_lines) > 2 and title_size > 50:
            title_size -= 6
            title_font = _font(workspace, title_size)
            title_lines = _wrap(draw, frame["headline"], title_font, 920)
        if len(title_lines) > 2:
            raise ValueError(f"Brief {name} frame headline exceeds two lines")
        for line in title_lines:
            draw.text((76, top), line, font=title_font, fill=foreground)
            top += 112
        if frame.get("imagePath"):
            source = Path(frame["imagePath"]).expanduser().resolve()
            if not source.is_file():
                raise ValueError(f"Brief frame image missing: {source}")
            with Image.open(source) as imported:
                visual = imported.convert("RGB")
                visual.thumbnail((900, 850))
                image.paste(visual, ((1080 - visual.width) // 2, 790 + (850 - visual.height) // 2))
        else:
            draw.rounded_rectangle((70, 790, 1010, 1640), radius=44, outline=accent, width=5)
            top = 1010
            visual_lines = _wrap(draw, frame["visualNote"], body_font, 780)
            if len(visual_lines) > 8:
                raise ValueError(f"Brief {name} frame visualNote is too long")
            for line in visual_lines:
                draw.text((145, top), line, font=body_font, fill=foreground)
                top += 62
        target = root / f"{name}.png"
        image.save(target)
        output[name] = target.relative_to(workspace.workspace_root).as_posix()
    return output
