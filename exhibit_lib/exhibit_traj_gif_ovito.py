#!/usr/bin/env python3
"""
Clean OVITO trajectory-to-GIF renderer
=====================================

Purpose
-------
Render atomic trajectory files to publication-style PNG/GIF using OVITO for all
3D rendering. 2D titles and legends are composed with Pillow after rendering so
legends never cover atoms.

Examples
--------
python3 make_traj_gif_ovito_clean.py traj.xyz --frames 120 --quality draft
python3 make_traj_gif_ovito_clean.py *.xyz --output-dir gifs --stride 2
python3 make_traj_gif_ovito_clean.py traj.traj --reader ase --width 1200 --height 800

Notes
-----
- OVITO is used for rendering.
- ASE is optional and is only used as a reader/converter when --reader ase is set
  or when OVITO cannot import the input directly.
- Output is PNG + GIF only.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import ovito
    from ovito import scene
    from ovito.io import import_file
    from ovito.modifiers import CreateBondsModifier
    from ovito.pipeline import Pipeline
    from ovito.vis import BondsVis, ParticlesVis, TachyonRenderer, Viewport
except ImportError as exc:
    raise SystemExit(
        "OVITO Python module was not found. Run with ovitos or install ovito:\n"
        "  ovitos make_traj_gif_ovito_clean.py traj.xyz\n"
        "  python3 -m pip install -U ovito pillow numpy"
    ) from exc

OVITO_VERSION = tuple(getattr(ovito, "version", (0, 0, 0)))
OVITO_VERSION_STRING = getattr(ovito, "version_string", ".".join(map(str, OVITO_VERSION)))


def ovito_at_least(major: int, minor: int, patch: int = 0) -> bool:
    version = tuple(OVITO_VERSION) + (0, 0, 0)
    return version[:3] >= (major, minor, patch)


# ── Visual palette inherited from your latest differential-charge script ────

def hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.strip().lstrip("#")
    if len(value) in (3, 4):
        value = "".join(ch * 2 for ch in value[:3])
    elif len(value) in (6, 8):
        value = value[:6]
    else:
        raise ValueError(f"Invalid color '{hex_color}'. Use #RGB or #RRGGBB.")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def make_element_style(style_hex: dict[str, tuple[str, float]]):
    return {sym: (hex_to_rgb01(color), radius) for sym, (color, radius) in style_hex.items()}


BG = hex_to_rgb01("#F5F6F7")
TEXT = (34, 38, 44)
SUBTEXT = (88, 95, 104)
DIVIDER = (219, 223, 228)

ELEMENT_STYLE_HEX = {
    "H":  ("#D0E0F1", 0.235),
    "B":  ("#BD9C80", 0.395),
    "C":  ("#6F7873", 0.405),
    "N":  ("#5778A8", 0.410),
    "O":  ("#B55B62", 0.405),
    "F":  ("#7CA89C", 0.390),
    "P":  ("#B88F4F", 0.490),
    "S":  ("#C2A869", 0.505),
    "Cl": ("#17827D", 0.500),
    "Br": ("#8A5E4A", 0.545),
    "I":  ("#785C99", 0.600),
    "Na": ("#808CC2", 0.545),
    "Mg": ("#9DA888", 0.545),
    "K":  ("#8F6EB3", 0.615),
    "Ca": ("#8A8DD2", 0.615),
    "Fe": ("#A37352", 0.560),
    "Cu": ("#B07852", 0.560),
    "Zn": ("#8F94A8", 0.560),
    "U":  ("#2A407B", 0.700),
}
ELEMENT_STYLE = make_element_style(ELEMENT_STYLE_HEX)

ATOMIC_SYMBOLS = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F",
    11: "Na", 12: "Mg", 15: "P", 16: "S", 17: "Cl",
    19: "K", 20: "Ca", 26: "Fe", 29: "Cu", 30: "Zn",
    35: "Br", 53: "I", 92: "U",
}
CPK_ORDER = {"H": 0, "C": 1, "N": 2, "O": 3, "F": 4, "P": 5, "S": 6,
             "Cl": 7, "Br": 8, "I": 9, "Na": 10, "Mg": 11, "K": 12,
             "Ca": 13, "Fe": 14, "Cu": 15, "Zn": 16, "U": 17}

DEFAULTS = dict(
    width=1200,
    height=760,
    fps=12,
    gif_duration_ms=None,
    quality="draft",
    perspective_fov=18.0,
    camera_padding=1.18,
    atom_scale=1.0,
    bond_width=0.118,
    azim=35.0,
    elev=18.0,
    fit_samples=24,
)


# ── Small utilities ──────────────────────────────────────────────────────────

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def normalize(v: Sequence[float]) -> np.ndarray:
    arr = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(arr))
    if n < 1e-12:
        raise ValueError("Cannot normalize a near-zero vector.")
    return arr / n


def rgb01_to_u8(rgb: Sequence[float]) -> tuple[int, int, int]:
    return tuple(int(round(clamp(float(c), 0.0, 1.0) * 255)) for c in rgb)


def remove_all_scene_pipelines() -> None:
    while len(scene.pipelines):
        del scene.pipelines[0]


def parse_rgb(text: str) -> tuple[float, float, float]:
    return hex_to_rgb01(text)


def parse_type_map(text: str) -> dict[int, str]:
    """Parse type map like '1=C,2=H,3=O'. Useful for numeric LAMMPS types."""
    if not text.strip():
        return {}
    out: dict[int, str] = {}
    for item in text.split(","):
        key, val = item.split("=", 1)
        out[int(key.strip())] = val.strip().capitalize()
    return out


def parse_atom_colors(text: str) -> dict[str, tuple[float, float, float]]:
    if not text.strip():
        return {}
    out = {}
    for item in text.split(","):
        sym, color = item.split("=", 1)
        out[sym.strip().capitalize()] = hex_to_rgb01(color.strip())
    return out


def find_font(size: int, bold: bool = False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            if Path(name).exists():
                return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill=TEXT):
    x0, y0, x1, y1 = box
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x0 + (x1 - x0 - w) / 2, y0 + (y1 - y0 - h) / 2 - bbox[1]), text, font=font, fill=fill)


# ── Import and styling ───────────────────────────────────────────────────────

def import_with_ovito(path: Path) -> Pipeline:
    try:
        return import_file(str(path), generate_bonds=False)
    except TypeError:
        return import_file(str(path))


def import_with_ase_then_ovito(path: Path, tmpdir: Path) -> Pipeline:
    try:
        from ase.io import read, write
    except ImportError as exc:
        raise RuntimeError("ASE is not installed. Use --reader ovito or install ase.") from exc
    images = read(str(path), index=":")
    if not isinstance(images, list):
        images = [images]
    extxyz_path = tmpdir / (path.stem + "__ase_converted.extxyz")
    write(str(extxyz_path), images, format="extxyz")
    return import_with_ovito(extxyz_path)


def load_pipeline(path: Path, reader: str, tmpdir: Path) -> Pipeline:
    if reader == "ovito":
        return import_with_ovito(path)
    if reader == "ase":
        return import_with_ase_then_ovito(path, tmpdir)
    try:
        return import_with_ovito(path)
    except Exception:
        return import_with_ase_then_ovito(path, tmpdir)


def source_num_frames(pipeline: Pipeline) -> int:
    return int(getattr(pipeline.source, "num_frames", 1) or 1)


def symbol_for_type(ptype, type_map: dict[int, str] | None = None) -> str:
    type_id = int(getattr(ptype, "id", 0))
    if type_map and type_id in type_map:
        return type_map[type_id]

    raw = (getattr(ptype, "name", "") or "").strip()
    normalized = raw.capitalize()
    aliases = {
        "Hydrogen": "H", "Boron": "B", "Carbon": "C", "Nitrogen": "N", "Oxygen": "O",
        "Fluorine": "F", "Phosphorus": "P", "Sulfur": "S", "Chlorine": "Cl",
        "Bromine": "Br", "Iodine": "I", "Sodium": "Na", "Magnesium": "Mg",
        "Potassium": "K", "Calcium": "Ca", "Iron": "Fe", "Copper": "Cu",
        "Zinc": "Zn", "Uranium": "U",
    }
    if raw in aliases:
        return aliases[raw]
    if normalized in ELEMENT_STYLE:
        return normalized
    return ATOMIC_SYMBOLS.get(type_id, raw or f"T{type_id}")


def make_style_modifier(atom_scale: float, type_map: dict[int, str], atom_colors: dict[str, tuple[float, float, float]], show_cell: bool):
    def style_modifier(frame, data):
        del frame
        if data.cell is not None:
            data.cell.vis.enabled = bool(show_cell)
        if data.particles is None:
            return
        data.particles.vis.shape = ParticlesVis.Shape.Sphere
        data.particles.vis.scaling = 1.0
        types = data.particles_.particle_types_
        for ptype in types.types_:
            symbol = symbol_for_type(ptype, type_map)
            color, radius = ELEMENT_STYLE.get(symbol, ((0.54, 0.56, 0.60), 0.46))
            if symbol in atom_colors:
                color = atom_colors[symbol]
            ptype.color = color
            ptype.radius = radius * atom_scale
    return style_modifier


def create_bonds(width: float, color: tuple[float, float, float], enabled: bool):
    if not enabled:
        return None
    mod = CreateBondsModifier(mode=CreateBondsModifier.Mode.CovalentRadius)
    mod.vis.width = width
    mod.vis.flat_shading = False
    try:
        mod.vis.coloring_mode = BondsVis.ColoringMode.Uniform
    except Exception:
        pass
    mod.vis.color = color
    try:
        mod.vis.visualize_bond_order = False
    except Exception:
        pass
    return mod


def apply_style(pipeline: Pipeline, args) -> None:
    pipeline.modifiers.append(make_style_modifier(args.atom_scale, args.type_map, args.atom_colors, args.show_cell))
    bond_mod = create_bonds(args.bond_width, hex_to_rgb01(args.bond_color), not args.no_bonds)
    if bond_mod is not None:
        pipeline.modifiers.append(bond_mod)


# ── Camera and renderer ──────────────────────────────────────────────────────

def choose_frame_indices(total: int, start: int, stop: int | None, stride: int, max_frames: int | None) -> list[int]:
    last = total if stop is None else min(stop, total)
    frames = list(range(max(0, start), max(0, last), max(1, stride)))
    if max_frames and len(frames) > max_frames:
        pick = np.linspace(0, len(frames) - 1, max_frames).round().astype(int)
        frames = [frames[i] for i in pick]
    return frames or [0]


def sampled_fit_frames(render_frames: list[int], max_samples: int) -> list[int]:
    if len(render_frames) <= max_samples:
        return render_frames
    idx = np.linspace(0, len(render_frames) - 1, max_samples).round().astype(int)
    return [render_frames[i] for i in idx]


def calculate_bounds(pipeline: Pipeline, frames: list[int], fit_mode: str) -> tuple[np.ndarray, float]:
    if fit_mode == "first":
        frames = [frames[0]]
    point_sets = []
    for frame in frames:
        data = pipeline.compute(frame=frame)
        if data.particles is None:
            continue
        pos = np.asarray(data.particles.positions, dtype=float)
        if pos.size:
            point_sets.append(pos)
    if not point_sets:
        return np.zeros(3), 5.0
    points = np.vstack(point_sets)
    lo, hi = points.min(axis=0), points.max(axis=0)
    center = (lo + hi) / 2.0
    radius = float(np.linalg.norm(points - center, axis=1).max())
    return center, max(radius, 1.0)


def camera_vectors(azim_deg: float, elev_deg: float) -> tuple[np.ndarray, np.ndarray]:
    az = math.radians(azim_deg)
    el = math.radians(elev_deg)
    view_dir = normalize([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    world_up = np.array([0.0, 0.0, 1.0])
    camera_up = world_up - float(np.dot(world_up, view_dir)) * view_dir
    if np.linalg.norm(camera_up) < 1e-8:
        camera_up = np.array([0.0, 1.0, 0.0])
    return view_dir, normalize(camera_up)


def configure_viewport(viewport: Viewport, center: np.ndarray, radius: float, panel_size: tuple[int, int], args) -> None:
    view_dir, camera_up = camera_vectors(args.azim, args.elev)
    if args.projection == "ortho":
        viewport.type = Viewport.Type.Ortho
        viewport.fov = radius * args.camera_padding * max(1.0, panel_size[1] / max(1, panel_size[0]))
        distance = max(10.0, radius * 4.0)
    else:
        viewport.type = Viewport.Type.Perspective
        fov = math.radians(args.perspective_fov)
        viewport.fov = fov
        aspect = panel_size[0] / panel_size[1]
        fit = radius * args.camera_padding
        distance = max(fit / max(math.tan(fov / 2), 1e-8), fit / max(math.tan(fov / 2) * aspect, 1e-8))
    viewport.camera_dir = tuple(float(x) for x in view_dir)
    viewport.camera_up = tuple(float(x) for x in camera_up)
    viewport.camera_pos = tuple(float(x) for x in (center - view_dir * distance))


def make_renderer(quality: str) -> TachyonRenderer:
    presets = {
        "draft":  dict(ambient_occlusion_samples=6,  antialiasing_samples=6,  max_ray_recursion=40),
        "normal": dict(ambient_occlusion_samples=14, antialiasing_samples=12, max_ray_recursion=70),
        "high":   dict(ambient_occlusion_samples=24, antialiasing_samples=20, max_ray_recursion=100),
    }
    return TachyonRenderer(
        ambient_occlusion=True,
        ambient_occlusion_brightness=0.91,
        antialiasing=True,
        direct_light=True,
        direct_light_intensity=0.74,
        shadows=True,
        **presets[quality],
    )


def render_ovito_frame(viewport: Viewport, frame: int, filename: Path, size: tuple[int, int], renderer: TachyonRenderer) -> None:
    kwargs = dict(filename=str(filename), size=size, background=BG, alpha=False, renderer=renderer, crop=False, frame=int(frame))
    if ovito_at_least(3, 9, 2):
        kwargs["stop_on_error"] = True
    try:
        viewport.render_image(**kwargs)
    except TypeError:
        kwargs.pop("frame", None)
        scene.anim.current_frame = int(frame)
        viewport.render_image(**kwargs)


# ── 2D composition and GIF encoding ─────────────────────────────────────────

def atom_legend(pipeline: Pipeline, frame: int, type_map: dict[int, str], atom_colors: dict[str, tuple[float, float, float]]):
    data = pipeline.compute(frame=frame)
    if data.particles is None:
        return []
    seen = {}
    for ptype in data.particles.particle_types.types:
        symbol = symbol_for_type(ptype, type_map)
        color, _ = ELEMENT_STYLE.get(symbol, ((0.54, 0.56, 0.60), 0.46))
        if symbol in atom_colors:
            color = atom_colors[symbol]
        seen.setdefault(symbol, color)
    return sorted(seen.items(), key=lambda item: CPK_ORDER.get(item[0], 999))


def legend_height(n_items: int, height: int, no_legend: bool) -> int:
    if no_legend or n_items == 0:
        return 0
    rows = math.ceil(n_items / 8)
    return max(58, rows * max(28, int(height * 0.035)) + 22)


def compose_frame(rendered: Image.Image, width: int, height: int, title: str, legend_items, args) -> Image.Image:
    title_h = 0 if args.no_title else max(54, int(height * 0.075))
    foot_h = legend_height(len(legend_items), height, args.no_legend)
    panel_h = height - title_h - foot_h
    bg = rgb01_to_u8(BG)
    canvas = Image.new("RGB", (width, height), bg)
    panel = rendered.convert("RGB").resize((width, panel_h), Image.Resampling.LANCZOS)
    canvas.paste(panel, (0, title_h))

    draw = ImageDraw.Draw(canvas)
    if title_h:
        centered_text(draw, (0, 0, width, title_h), title, find_font(max(22, int(height * 0.033))), TEXT)
        draw.line((int(width * 0.08), title_h - 1, int(width * 0.92), title_h - 1), fill=DIVIDER, width=1)

    if foot_h:
        y0 = height - foot_h
        draw.line((int(width * 0.08), y0, int(width * 0.92), y0), fill=DIVIDER, width=1)
        font = find_font(max(15, int(height * 0.020)), bold=True)
        sw = max(16, int(height * 0.022))
        row_h = max(28, int(height * 0.035))
        col_w = max(82, int(width * 0.090))
        ncols = max(1, min(8, width // col_w))
        total_w = min(ncols, len(legend_items)) * col_w
        x_start = max(20, (width - total_w) // 2)
        y_start = y0 + (foot_h - math.ceil(len(legend_items) / ncols) * row_h) // 2
        for i, (symbol, color) in enumerate(legend_items):
            col, row = i % ncols, i // ncols
            x = x_start + col * col_w
            y = y_start + row * row_h
            draw.rounded_rectangle((x, y, x + sw, y + sw), radius=3, fill=rgb01_to_u8(color))
            draw.text((x + sw + 8, y - 1), symbol, font=font, fill=TEXT)
    return canvas


def build_global_palette(frame_paths: Sequence[Path]) -> Image.Image:
    sample_count = min(12, len(frame_paths))
    indices = np.linspace(0, len(frame_paths) - 1, sample_count).round().astype(int)
    thumb = (300, 190)
    cols = 4
    rows = math.ceil(sample_count / cols)
    sheet = Image.new("RGB", (thumb[0] * cols, thumb[1] * rows), rgb01_to_u8(BG))
    for slot, idx in enumerate(indices):
        with Image.open(frame_paths[int(idx)]) as im:
            sheet.paste(im.convert("RGB").resize(thumb, Image.Resampling.LANCZOS), ((slot % cols) * thumb[0], (slot // cols) * thumb[1]))
    return sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def save_gif(frame_paths: Sequence[Path], output: Path, fps: int, duration_ms: int | None) -> None:
    palette = build_global_palette(frame_paths)
    frames = []
    for path in frame_paths:
        with Image.open(path) as im:
            frames.append(im.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE).copy())
    duration = int(duration_ms) if duration_ms else max(1, int(round(1000 / fps)))
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=1, optimize=False)


# ── Main render routine ──────────────────────────────────────────────────────

def output_prefix_for(path: Path, args) -> Path:
    if args.output_prefix and len(args.inputs) == 1:
        return Path(args.output_prefix).expanduser().resolve()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else path.parent
    return out_dir / f"{path.stem}{args.suffix}"


def render_one(input_path: Path, args) -> None:
    with tempfile.TemporaryDirectory(prefix="ovito_traj_") as tmpname:
        tmp = Path(tmpname)
        remove_all_scene_pipelines()
        pipeline = load_pipeline(input_path, args.reader, tmp)
        apply_style(pipeline, args)

        n_total = source_num_frames(pipeline)
        render_frames = choose_frame_indices(n_total, args.start, args.stop, args.stride, args.max_frames)
        fit_frames = sampled_fit_frames(render_frames, args.fit_samples)
        center, radius = calculate_bounds(pipeline, fit_frames, args.fit_mode)

        legend_items = atom_legend(pipeline, render_frames[0], args.type_map, args.atom_colors)
        title_h = 0 if args.no_title else max(54, int(args.height * 0.075))
        foot_h = legend_height(len(legend_items), args.height, args.no_legend)
        panel_size = (args.width, args.height - title_h - foot_h)

        out_prefix = output_prefix_for(input_path, args)
        out_prefix.parent.mkdir(parents=True, exist_ok=True)
        png_path = out_prefix.with_suffix(".png")
        gif_path = out_prefix.with_suffix(".gif")

        print(f"\nInput: {input_path}")
        print(f"   OVITO version: {OVITO_VERSION_STRING}")
        print(f"   Source frames: {n_total}; rendered frames: {len(render_frames)}")
        print(f"   Atom legend: {', '.join(sym for sym, _ in legend_items) if legend_items else 'none'}")
        print(f"   Camera center: {np.array2string(center, precision=3)}")
        print(f"   Fit radius: {radius:.3f}")
        print(f"   Output: {gif_path}")

        renderer = make_renderer(args.quality)
        viewport = Viewport(type=Viewport.Type.Perspective)
        configure_viewport(viewport, center, radius, panel_size, args)

        pipeline.add_to_scene()
        frame_paths: list[Path] = []
        try:
            for i, src_frame in enumerate(render_frames):
                print(f"   Rendering {i + 1:>4}/{len(render_frames)}  source frame {src_frame}")
                raw_path = tmp / f"raw_{i:04d}.png"
                final_path = tmp / f"frame_{i:04d}.png"
                render_ovito_frame(viewport, src_frame, raw_path, panel_size, renderer)
                with Image.open(raw_path) as raw:
                    final = compose_frame(raw, args.width, args.height, input_path.stem if args.title == "auto" else args.title, legend_items, args)
                    final.save(final_path, format="PNG", optimize=True)
                    if i == 0 and not args.no_png:
                        final.save(png_path, format="PNG", optimize=True)
                frame_paths.append(final_path)
        finally:
            pipeline.remove_from_scene()
            remove_all_scene_pipelines()

        if not args.no_gif:
            print("   Encoding GIF with shared global palette...")
            save_gif(frame_paths, gif_path, args.fps, args.gif_duration_ms)
        if not args.no_png:
            print(f"   PNG: {png_path}")
        if not args.no_gif:
            print(f"   GIF: {gif_path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Render trajectory files to publication-style GIF/PNG using OVITO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("inputs", nargs="+", help="Trajectory files, e.g. xyz/extxyz/dump/lammpstrj/traj")
    p.add_argument("--reader", choices=("auto", "ovito", "ase"), default="auto")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stop", type=int, default=None)
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--max-frames", type=int, default=None, help="Uniformly sample at most this many frames after start/stop/stride")

    p.add_argument("--width", type=int, default=DEFAULTS["width"])
    p.add_argument("--height", type=int, default=DEFAULTS["height"])
    p.add_argument("--fps", type=int, default=DEFAULTS["fps"])
    p.add_argument("--gif-duration-ms", type=int, default=DEFAULTS["gif_duration_ms"])
    p.add_argument("--quality", choices=("draft", "normal", "high"), default=DEFAULTS["quality"])
    p.add_argument("--projection", choices=("perspective", "ortho"), default="perspective")
    p.add_argument("--perspective-fov", type=float, default=DEFAULTS["perspective_fov"])
    p.add_argument("--camera-padding", type=float, default=DEFAULTS["camera_padding"])
    p.add_argument("--azim", type=float, default=DEFAULTS["azim"])
    p.add_argument("--elev", type=float, default=DEFAULTS["elev"])
    p.add_argument("--fit-mode", choices=("sampled", "first"), default="sampled")
    p.add_argument("--fit-samples", type=int, default=DEFAULTS["fit_samples"])

    p.add_argument("--atom-scale", type=float, default=DEFAULTS["atom_scale"])
    p.add_argument("--bond-width", type=float, default=DEFAULTS["bond_width"])
    p.add_argument("--bond-color", default="#495057")
    p.add_argument("--no-bonds", action="store_true")
    p.add_argument("--show-cell", action="store_true")
    p.add_argument("--type-map", type=parse_type_map, default={}, metavar="1=C,2=H")
    p.add_argument("--atom-colors", type=parse_atom_colors, default={}, metavar="C=#6F7873,O=#B55B62")

    p.add_argument("--title", default="auto", help="Use 'auto' for file stem")
    p.add_argument("--no-title", action="store_true")
    p.add_argument("--no-legend", action="store_true")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--output-prefix", default=None, help="Only valid for one input")
    p.add_argument("--suffix", default="_ovito_traj")
    p.add_argument("--no-png", action="store_true")
    p.add_argument("--no-gif", action="store_true")
    return p.parse_args()


def validate(args) -> None:
    if args.width < 500 or args.height < 420:
        raise ValueError("Use at least --width 500 and --height 420.")
    if args.stride < 1 or args.fps < 1 or args.fit_samples < 1:
        raise ValueError("--stride, --fps and --fit-samples must be positive.")
    if args.output_prefix and len(args.inputs) > 1:
        raise ValueError("--output-prefix can only be used with one input file. Use --output-dir for batch rendering.")
    if args.no_png and args.no_gif:
        raise ValueError("Both PNG and GIF outputs are disabled.")


def main() -> int:
    args = parse_args()
    validate(args)
    for raw in args.inputs:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            print(f"Skipping missing file: {path}", file=sys.stderr)
            continue
        render_one(path, args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
