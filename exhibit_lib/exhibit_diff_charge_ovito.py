#!/usr/bin/env python3
"""
Premium publication-style differential charge density renderer using OVITO - v5 chunked
=========================================================================
Outputs:
  1) <cube_stem>_ovito_premium.png
  2) <cube_stem>_ovito_premium.gif

Design goals
------------
- Perspective projection with strict panel isomorphism:
  both panels share the same camera position, direction, up vector, field of view,
  and framing parameters.
- Premium ray-traced rendering using Tachyon with ambient occlusion, shadows,
  anti-aliasing, and high recursion depth for semi-transparent isosurfaces.
- Cool light-gray background instead of pure white.
- Low-saturation editorial palette:
    positive density = amber gold
    negative density = mist blue
- Refined ball-and-stick geometry on both panels.
- Right panel skeleton is smaller and more desaturated so the charge-density
  surfaces remain the protagonist.
- OVITO latest behavior fix:
  use particle_types_.types_ (writable copy) instead of .types to avoid
  shared-reference conflicts when multiple pipelines share the same data source.

Recommended run:
    ovitos make_diff_charge_ovito_premium.py diff.cube --level 0.005

Also works with a normal Python interpreter if the OVITO module is installed:
    python3 make_diff_charge_ovito_premium.py diff.cube --level 0.005
"""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
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
    from ovito.data import VoxelGrid
    from ovito.io import import_file
    from ovito.modifiers import CreateBondsModifier, CreateIsosurfaceModifier
    from ovito.pipeline import Pipeline
    from ovito.vis import BondsVis, ParticlesVis, TachyonRenderer, Viewport
except ImportError as exc:
    raise SystemExit(
        "OVITO Python module was not found.\n"
        "Please run with OVITO's interpreter:\n"
        "  ovitos make_diff_charge_ovito_premium.py your_file.cube ...\n"
        "or install the package:\n"
        "  python3 -m pip install -U ovito pillow numpy\n"
    ) from exc


OVITO_VERSION = tuple(getattr(ovito, "version", (0, 0, 0)))
OVITO_VERSION_STRING = getattr(
    ovito, "version_string", ".".join(str(x) for x in OVITO_VERSION)
)


def ovito_at_least(major: int, minor: int, patch: int = 0) -> bool:
    version = tuple(OVITO_VERSION) + (0, 0, 0)
    return version[:3] >= (major, minor, patch)


if not ovito_at_least(3, 10, 4):
    raise SystemExit(
        "This script requires OVITO 3.10.4 or newer.\n"
        f"Detected OVITO version: {OVITO_VERSION_STRING}"
    )


def hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    """Convert #RGB/#RGBA/#RRGGBB/#RRGGBBAA to OVITO RGB floats in [0, 1].

    Alpha, if present, is ignored here because atom opacity is controlled elsewhere.
    """
    value = hex_color.strip().lstrip("#")

    if len(value) in (3, 4):
        value = "".join(ch * 2 for ch in value[:3])
    elif len(value) in (6, 8):
        value = value[:6]
    else:
        raise ValueError(
            f"Invalid color '{hex_color}'. Use #RGB, #RGBA, #RRGGBB, or #RRGGBBAA."
        )

    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

BG = (0.962, 0.965, 0.970)
TEXT = (34, 38, 44)
SUBTEXT = (88, 95, 104)
DIVIDER = (219, 223, 228)

POSITIVE_RGB = hex_to_rgb01("#57A86D")
NEGATIVE_RGB = hex_to_rgb01("#5D77BD")


def make_element_style(style_hex: dict[str, tuple[str, float]]) -> dict[str, tuple[tuple[float, float, float], float]]:
    return {symbol: (hex_to_rgb01(color), radius) for symbol, (color, radius) in style_hex.items()}


# 现在你只需要在这里写正常可视化的 HEX 色号；脚本会自动转换成 OVITO 需要的 0-1 RGB。
ELEMENT_STYLE_HEX = {
    "H":  ("#D0E0F1", 0.235),
    "B":  ("#BD9C80", 0.395),
    "C":  ("#6F7873", 0.405),
    "N":  ("#5778A8", 0.410),
    "O":  ("#B55B62", 0.405),
    "F":  ("#7CA89C", 0.390),
    "P":  ("#B88F4F", 0.490),
    "S":  ("#C2A869", 0.505),
    "Cl": ("#17827D", 0.500),  # muted teal, avoids all-green look
    "Br": ("#8A5E4A", 0.545),
    "I":  ("#785C99", 0.600),
    "Na": ("#808CC2", 0.545),
    "Mg": ("#9DA888", 0.545),
    "K":  ("#8F6EB3", 0.615),
    "Ca": ("#8A8DD2", 0.615),  # soft lavender
    "Fe": ("#A37352", 0.560),
    "Cu": ("#B07852", 0.560),
    "Zn": ("#8F94A8", 0.560),
    "U":  ("#2A407B", 0.700),  # aged bronze
}

ELEMENT_STYLE = make_element_style(ELEMENT_STYLE_HEX)

ATOMIC_SYMBOLS = {
    1: "H", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F",
    11: "Na", 12: "Mg", 15: "P", 16: "S", 17: "Cl",
    19: "K", 20: "Ca", 26: "Fe", 29: "Cu", 30: "Zn",
    35: "Br", 53: "I", 92: "U",
}

DEFAULTS = dict(
    width=1800,
    height=980,
    frames=72,
    fps=12,
    elev=17.0,
    perspective_fov_deg=17.5,
    camera_padding=1.14,
    atom_scale=1.00,
    right_atom_shrink=0.82,
    bond_width=0.118,
    alpha_pos=0.46,
    alpha_neg=0.36,
    percentile=99.4,
    smooth_sigma=0.7,
)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def normalize(vector: Sequence[float]) -> np.ndarray:
    v = np.asarray(vector, dtype=float)
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        raise ValueError("Cannot normalize a near-zero vector.")
    return v / n


def remove_all_scene_pipelines() -> None:
    while len(scene.pipelines):
        del scene.pipelines[0]


def parse_rgb(text: str) -> tuple[float, float, float]:
    value = text.strip().lstrip("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("Color must be a 6-digit hex value, e.g. C79B4F.")
    try:
        return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Invalid hexadecimal color.") from exc


def parse_atom_colors(text: str) -> dict[str, tuple[float, float, float]]:
    """Parse --atom-colors like 'H=#FFFFFF,C=#404040,O=#FF6633'"""
    result: dict[str, tuple[float, float, float]] = {}
    if not text.strip():
        return result
    for part in text.split(","):
        part = part.strip()
        if "=" not in part:
            raise argparse.ArgumentTypeError(
                f"Invalid atom-color spec '{part}'. Use format: H=#FFFFFF,C=#404040"
            )
        symbol_str, hex_color = part.split("=", 1)
        symbol_str = symbol_str.strip().capitalize()
        hex_color = hex_color.strip()
        result[symbol_str] = parse_rgb(hex_color)
    return result


def find_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    else:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ])

    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass

    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def draw_centered_text(draw, box, text, font, fill=TEXT):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + (right - left - width) / 2
    y = top + (bottom - top - height) / 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def to_u8_rgb(rgb_triplet: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(int(round(clamp(c, 0.0, 1.0) * 255)) for c in rgb_triplet)


def symbol_for_type(ptype) -> str:
    raw_name = (getattr(ptype, "name", "") or "").strip()
    normalized = raw_name.capitalize()

    if normalized in ELEMENT_STYLE:
        return normalized

    name_aliases = {
        "Hydrogen": "H", "Boron": "B", "Carbon": "C", "Nitrogen": "N",
        "Oxygen": "O", "Fluorine": "F", "Phosphorus": "P", "Sulfur": "S",
        "Chlorine": "Cl", "Bromine": "Br", "Iodine": "I",
        "Sodium": "Na", "Magnesium": "Mg", "Potassium": "K",
        "Calcium": "Ca", "Iron": "Fe", "Copper": "Cu", "Zinc": "Zn",
        "Uranium": "U",
    }
    if raw_name in name_aliases:
        return name_aliases[raw_name]

    type_id = int(getattr(ptype, "id", 0))
    return ATOMIC_SYMBOLS.get(type_id, raw_name or f"Z{type_id}")


def choose_iso_level(values: np.ndarray, user_level: float | None, percentile: float) -> float:
    if user_level is not None:
        level = abs(float(user_level))
        if level <= 0:
            raise ValueError("--level must be greater than zero.")
        return level

    finite = np.abs(np.asarray(values, dtype=float).ravel())
    finite = finite[np.isfinite(finite)]
    finite = finite[finite > 0]
    if finite.size == 0:
        raise ValueError("The selected voxel field contains no finite non-zero values.")
    if not (0 < percentile < 100):
        raise ValueError("--percentile must lie between 0 and 100.")
    return float(np.percentile(finite, percentile))


def print_density_stats(values: np.ndarray) -> None:
    finite = np.abs(np.asarray(values, dtype=float).ravel())
    finite = finite[np.isfinite(finite)]
    finite = finite[finite > 0]
    if finite.size == 0:
        return
    print("   |Δρ| percentile reference:")
    for q in (95, 97, 98, 98.5, 99, 99.2, 99.4, 99.5, 99.8):
        print(f"     p{q:>4}: {np.percentile(finite, q):.7g}")


def detect_grid_and_field(
    pipeline: Pipeline,
    requested_grid: str | None,
    requested_field: str | None,
) -> tuple[str, str, np.ndarray]:
    data = pipeline.compute()
    if not data.grids:
        raise RuntimeError("OVITO did not find a voxel grid in the cube file.")

    grid_names = list(data.grids.keys())
    if requested_grid:
        if requested_grid not in data.grids:
            raise KeyError(f"Grid '{requested_grid}' was not found. Available grids: {grid_names}")
        grid_name = requested_grid
    else:
        grid_name = grid_names[0]

    grid = data.grids[grid_name]
    property_names = list(grid.keys())
    if not property_names:
        raise RuntimeError(f"Voxel grid '{grid_name}' contains no properties.")

    if requested_field:
        if requested_field not in grid:
            raise KeyError(
                f"Field '{requested_field}' was not found in grid '{grid_name}'. "
                f"Available fields: {property_names}"
            )
        field_name = requested_field
    else:
        candidates = []
        for name in property_names:
            if name in {"Color", "Selection", "Transparency"}:
                continue
            arr = np.asarray(grid[name])
            if arr.ndim == 1 or (arr.ndim == 2 and arr.shape[1] == 1):
                candidates.append(name)
        field_name = candidates[0] if candidates else property_names[0]

    values = np.asarray(grid[field_name], dtype=float).reshape(-1)
    return grid_name, field_name, values


def make_style_modifier(
    *,
    panel_role: str,
    atom_scale: float,
    nonperiodic: bool,
    atom_color_overrides: dict[str, tuple[float, float, float]] | None = None,
):
    def style_modifier(frame, data):
        del frame

        if data.cell is not None:
            data.cell.vis.enabled = False
            if nonperiodic:
                try:
                    data.cell_.pbc = (False, False, False)
                except Exception:
                    pass

        for grid in data.grids.values():
            grid.vis.enabled = False
            if nonperiodic:
                try:
                    grid.domain_.pbc = (False, False, False)
                except Exception:
                    try:
                        grid.domain.pbc = (False, False, False)
                    except Exception:
                        pass

        if data.particles is None:
            return

        data.particles.vis.shape = ParticlesVis.Shape.Sphere
        data.particles.vis.scaling = 1.0

        types = data.particles_.particle_types_
        for ptype in types.types_:
            symbol = symbol_for_type(ptype)
            base_color, base_radius = ELEMENT_STYLE.get(symbol, ((0.54, 0.56, 0.60), 0.46))

            # Apply custom color override if set
            if atom_color_overrides and symbol in atom_color_overrides:
                base_color = atom_color_overrides[symbol]

            if panel_role == "left":
                ptype.color = base_color
                ptype.radius = base_radius * atom_scale
            else:
                if symbol == "H":
                    ptype.color = (0.865, 0.875, 0.885)
                else:
                    ptype.color = (0.695, 0.715, 0.740)
                ptype.radius = base_radius * atom_scale

    return style_modifier


def create_bond_modifier(width: float, color: tuple[float, float, float]) -> CreateBondsModifier:
    modifier = CreateBondsModifier(mode=CreateBondsModifier.Mode.CovalentRadius)
    modifier.vis.width = width
    modifier.vis.flat_shading = False
    try:
        modifier.vis.coloring_mode = BondsVis.ColoringMode.Uniform
    except Exception:
        pass
    modifier.vis.color = color
    try:
        modifier.vis.visualize_bond_order = False
    except Exception:
        pass
    return modifier


def configure_surface(
    modifier: CreateIsosurfaceModifier,
    color: tuple[float, float, float],
    alpha: float,
) -> None:
    modifier.vis.surface_color = color
    modifier.vis.surface_transparency = 1.0 - clamp(alpha, 0.0, 1.0)
    for attr, value in (
        ("smooth_shading", True),
        ("show_cap", False),
        ("highlight_edges", False),
        ("clip_at_domain_boundaries", True),
    ):
        try:
            setattr(modifier.vis, attr, value)
        except Exception:
            pass


def make_isosurface_modifier(
    *,
    grid_name: str,
    field_name: str,
    iso_level: float,
    smoothing_level: int,
) -> CreateIsosurfaceModifier:
    modifier = CreateIsosurfaceModifier(
        operate_on=f"voxels:{grid_name}",
        property=field_name,
        isolevel=iso_level,
    )
    try:
        modifier.smoothing_level = int(smoothing_level)
    except Exception:
        pass
    return modifier


def build_pipelines(
    base_pipeline: Pipeline,
    *,
    grid_name: str,
    field_name: str,
    iso_level: float,
    smoothing_level: int,
    alpha_pos: float,
    alpha_neg: float,
    positive_color: tuple[float, float, float],
    negative_color: tuple[float, float, float],
    atom_scale: float,
    right_atom_shrink: float,
    bond_width: float,
    periodic: bool,
    atom_color_overrides: dict[str, tuple[float, float, float]] | None = None,
) -> tuple[Pipeline, Pipeline]:
    left = Pipeline(source=base_pipeline.source)
    right = Pipeline(source=base_pipeline.source)

    left.modifiers.append(make_style_modifier(
        panel_role="left",
        atom_scale=atom_scale,
        nonperiodic=not periodic,
        atom_color_overrides=atom_color_overrides,
    ))
    left.modifiers.append(create_bond_modifier(
        width=bond_width,
        color=(0.285, 0.305, 0.335),
    ))

    right.modifiers.append(make_style_modifier(
        panel_role="right",
        atom_scale=atom_scale * right_atom_shrink,
        nonperiodic=not periodic,
        atom_color_overrides=atom_color_overrides,
    ))
    right.modifiers.append(create_bond_modifier(
        width=bond_width * 0.92,
        color=(0.565, 0.590, 0.620),
    ))

    positive = make_isosurface_modifier(
        grid_name=grid_name,
        field_name=field_name,
        iso_level=iso_level,
        smoothing_level=smoothing_level,
    )
    configure_surface(positive, positive_color, alpha_pos)
    right.modifiers.append(positive)

    negative = make_isosurface_modifier(
        grid_name=grid_name,
        field_name=field_name,
        iso_level=-iso_level,
        smoothing_level=smoothing_level,
    )
    configure_surface(negative, negative_color, alpha_neg)
    right.modifiers.append(negative)

    return left, right


def compute_principal_axis(positions: np.ndarray) -> np.ndarray:
    points = np.asarray(positions, dtype=float)
    if len(points) < 2:
        return np.array([0.0, 0.0, 1.0])

    centered = points - points.mean(axis=0)
    covariance = centered.T @ centered
    _, eigenvectors = np.linalg.eigh(covariance)
    axis = normalize(eigenvectors[:, -1])

    preferred = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(axis, preferred))) < 0.2:
        preferred = np.array([0.0, 1.0, 0.0])
    if float(np.dot(axis, preferred)) < 0:
        axis = -axis
    return axis


def choose_spin_axis(mode: str, positions: np.ndarray) -> np.ndarray:
    if mode == "auto":
        return compute_principal_axis(positions)
    axes = {
        "x": np.array([1.0, 0.0, 0.0]),
        "y": np.array([0.0, 1.0, 0.0]),
        "z": np.array([0.0, 0.0, 1.0]),
    }
    return axes[mode]


def make_camera_basis(spin_axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    axis = normalize(spin_axis)
    references = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    ]
    reference = min(references, key=lambda ref: abs(float(np.dot(ref, axis))))
    radial_x = normalize(np.cross(axis, reference))
    radial_y = normalize(np.cross(axis, radial_x))
    return radial_x, radial_y


def camera_orientation(
    angle_deg: float,
    elevation_deg: float,
    spin_axis: np.ndarray,
    radial_x: np.ndarray,
    radial_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    angle = math.radians(angle_deg)
    elevation = math.radians(elevation_deg)

    radial = math.cos(angle) * radial_x + math.sin(angle) * radial_y
    view_dir = normalize(math.cos(elevation) * radial - math.sin(elevation) * spin_axis)

    camera_up = spin_axis - float(np.dot(spin_axis, view_dir)) * view_dir
    if np.linalg.norm(camera_up) < 1e-8:
        camera_up = radial_y
    camera_up = normalize(camera_up)

    return view_dir, camera_up


def calculate_scene_bounds(
    right_pipeline: Pipeline,
    *,
    fit_mode: str,
) -> tuple[np.ndarray, float, np.ndarray]:
    data = right_pipeline.compute()
    if data.particles is None:
        raise RuntimeError("No atoms were imported from the cube file.")

    atom_positions = np.asarray(data.particles.positions, dtype=float)
    center = atom_positions.mean(axis=0)

    point_sets: list[np.ndarray] = [atom_positions]
    if fit_mode == "all":
        for surface in data.surfaces.values():
            try:
                vertices = np.asarray(surface.vertices["Position"], dtype=float)
            except Exception:
                continue
            if vertices.size:
                point_sets.append(vertices)

    radius = 0.0
    for points in point_sets:
        if points.size:
            radius = max(radius, float(np.linalg.norm(points - center, axis=1).max()))

    return center, max(radius, 1.0), atom_positions


def configure_viewport(
    viewport: Viewport,
    *,
    center: np.ndarray,
    radius: float,
    view_dir: np.ndarray,
    camera_up: np.ndarray,
    panel_size: tuple[int, int],
    camera_padding: float,
    perspective_fov_deg: float,
) -> None:
    viewport.type = Viewport.Type.Perspective
    viewport.camera_dir = tuple(float(x) for x in view_dir)
    viewport.camera_up = tuple(float(x) for x in camera_up) # type: ignore

    fov_rad = math.radians(perspective_fov_deg)
    viewport.fov = fov_rad

    aspect = panel_size[0] / panel_size[1]
    tan_half = math.tan(fov_rad / 2.0)
    fit_radius = radius * camera_padding

    dist_vertical = fit_radius / max(tan_half, 1e-8)
    dist_horizontal = fit_radius / max(tan_half * aspect, 1e-8)
    distance = max(dist_vertical, dist_horizontal)

    viewport.camera_pos = tuple(float(x) for x in (center - view_dir * distance)) # pyright: ignore[reportAttributeAccessIssue]


def make_renderer(quality: str) -> TachyonRenderer:
    if quality == "draft":
        return TachyonRenderer(
            ambient_occlusion=True,
            ambient_occlusion_samples=8,
            ambient_occlusion_brightness=0.92,
            antialiasing=True,
            antialiasing_samples=8,
            direct_light=True,
            direct_light_intensity=0.74,
            shadows=True,
            max_ray_recursion=60,
        )
    if quality == "high":
        return TachyonRenderer(
            ambient_occlusion=True,
            ambient_occlusion_samples=28,
            ambient_occlusion_brightness=0.87,
            antialiasing=True,
            antialiasing_samples=24,
            direct_light=True,
            direct_light_intensity=0.76,
            shadows=True,
            max_ray_recursion=120,
        )
    return TachyonRenderer(
        ambient_occlusion=True,
        ambient_occlusion_samples=18,
        ambient_occlusion_brightness=0.89,
        antialiasing=True,
        antialiasing_samples=16,
        direct_light=True,
        direct_light_intensity=0.75,
        shadows=True,
        max_ray_recursion=90,
    )


def render_pipeline_to_file(
    pipeline: Pipeline,
    viewport: Viewport,
    renderer: TachyonRenderer,
    output_path: Path,
    panel_size: tuple[int, int],
) -> None:
    pipeline.add_to_scene()
    try:
        kwargs = dict(
            filename=str(output_path),
            size=panel_size,
            background=BG,
            alpha=False,
            renderer=renderer,
            crop=False,
        )
        if ovito_at_least(3, 9, 2):
            kwargs["stop_on_error"] = True
        viewport.render_image(**kwargs)
    finally:
        pipeline.remove_from_scene()


def compose_figure(
    left_image: Image.Image,
    right_image: Image.Image,
    *,
    width: int,
    height: int,
    title_left: str,
    title_right: str,
    iso_level: float,
    unit_label: str,
    positive_color: tuple[float, float, float],
    negative_color: tuple[float, float, float],
    atom_legend_data: list[tuple[str, tuple[float, float, float]]] | None = None,
) -> Image.Image:
    panel_width = width // 2
    title_height = max(78, int(height * 0.096))
    footer_height = max(132, int(height * 0.148))
    panel_height = height - title_height - footer_height

    bg_u8 = to_u8_rgb(BG)
    canvas = Image.new("RGB", (width, height), bg_u8)

    left = left_image.convert("RGB").resize((panel_width, panel_height), Image.Resampling.LANCZOS)
    right = right_image.convert("RGB").resize((width - panel_width, panel_height), Image.Resampling.LANCZOS)

    canvas.paste(left, (0, title_height))
    canvas.paste(right, (panel_width, title_height))

    draw = ImageDraw.Draw(canvas)
    title_font = find_font(max(28, int(height * 0.036)), bold=False)
    legend_font = find_font(max(18, int(height * 0.021)), bold=False)
    note_font = find_font(max(17, int(height * 0.019)), bold=False)

    draw_centered_text(draw, (0, 0, panel_width, title_height), title_left, title_font, fill=TEXT)
    draw_centered_text(draw, (panel_width, 0, width, title_height), title_right, title_font, fill=TEXT)

    draw.line((panel_width, 18, panel_width, title_height - 14), fill=DIVIDER, width=1)

    footer_top = height - footer_height
    legend_x = panel_width + int((width - panel_width) * 0.56)
    legend_y = footer_top + 18
    swatch_w = max(42, int(width * 0.028))
    swatch_h = max(24, int(height * 0.027))
    text_gap = 16
    row_gap = max(14, int(height * 0.016))

    draw.rounded_rectangle(
        (legend_x, legend_y, legend_x + swatch_w, legend_y + swatch_h),
        radius=4,
        fill=to_u8_rgb(positive_color),
    )
    draw.text(
        (legend_x + swatch_w + text_gap, legend_y - 2),
        "Δρ > 0  accumulation",
        font=legend_font,
        fill=TEXT,
    )

    second_y = legend_y + swatch_h + row_gap
    draw.rounded_rectangle(
        (legend_x, second_y, legend_x + swatch_w, second_y + swatch_h),
        radius=4,
        fill=to_u8_rgb(negative_color),
    )
    draw.text(
        (legend_x + swatch_w + text_gap, second_y - 2),
        "Δρ < 0  depletion",
        font=legend_font,
        fill=TEXT,
    )

    note_y = second_y + swatch_h + row_gap + 2
    draw.text(
        (legend_x, note_y),
        f"iso = ±{iso_level:.4g} {unit_label}",
        font=note_font,
        fill=SUBTEXT,
    )

    # ── Atom type legend ──────────────────────────────────────────
    if atom_legend_data:
        atom_font = find_font(max(16, int(height * 0.019)), bold=True)
        swatch_s = max(16, int(height * 0.020))
        text_gap = max(8, int(width * 0.006))
        row_h = max(26, int(height * 0.028))
        ncols = min(max(1, len(atom_legend_data) // 5 + 1), 4)
        col_w = max(80, int(width * 0.058))

        base_x = max(22, int(width * 0.018))
        total_rows = (len(atom_legend_data) + ncols - 1) // ncols
        base_y = footer_top + (footer_height - total_rows * row_h) // 2

        for i, (symbol, color) in enumerate(atom_legend_data):
            col = i % ncols
            row = i // ncols
            sx = base_x + col * col_w
            sy = base_y + row * row_h

            draw.rounded_rectangle(
                (sx, sy, sx + swatch_s, sy + swatch_s),
                radius=3,
                fill=to_u8_rgb(color),
            )
            draw.text(
                (sx + swatch_s + text_gap, sy - 1),
                symbol,
                font=atom_font,
                fill=TEXT,
            )

    return canvas


def build_global_palette(frame_paths: Sequence[Path]) -> Image.Image:
    count = min(12, len(frame_paths))
    indices = np.linspace(0, len(frame_paths) - 1, count).astype(int)

    thumb_size = (340, 190)
    columns = 4
    rows = math.ceil(count / columns)
    sheet = Image.new("RGB", (thumb_size[0] * columns, thumb_size[1] * rows), to_u8_rgb(BG))

    for slot, index in enumerate(indices):
        with Image.open(frame_paths[index]) as image:
            thumb = image.convert("RGB").resize(thumb_size, Image.Resampling.LANCZOS)
        x = (slot % columns) * thumb_size[0]
        y = (slot // columns) * thumb_size[1]
        sheet.paste(thumb, (x, y))

    return sheet.quantize(
        colors=255,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )


def save_gif_with_global_palette(frame_paths: Sequence[Path], output_path: Path, fps: int, duration_ms_override: int | None = None) -> None:
    if not frame_paths:
        raise ValueError("No frames were generated.")

    palette_source = build_global_palette(frame_paths)
    quantized_frames = []

    for path in frame_paths:
        with Image.open(path) as image:
            frame = image.convert("RGB").quantize(
                palette=palette_source,
                dither=Image.Dither.NONE,
            )
            quantized_frames.append(frame.copy())

    duration_ms = max(1, int(duration_ms_override)) if duration_ms_override else max(1, int(round(1000 / fps)))
    quantized_frames[0].save(
        output_path,
        save_all=True,
        append_images=quantized_frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=1,
        optimize=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render premium publication-style differential charge density PNG and GIF using OVITO.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("cube_file", help="Gaussian Cube differential-density file")

    iso = parser.add_argument_group("Isosurface")
    iso.add_argument("--level", type=float, default=None,
                     help="Absolute positive/negative isovalue; overrides --percentile")
    iso.add_argument("--percentile", type=float, default=DEFAULTS["percentile"],
                     help="Percentile of |field| used when --level is omitted")
    iso.add_argument("--smooth-sigma", type=float, default=DEFAULTS["smooth_sigma"],
                     help="Compatibility option mapped to OVITO mesh smoothing")
    iso.add_argument("--surface-smoothing", type=int, default=None,
                     help="Explicit OVITO mesh smoothing iteration count")
    iso.add_argument("--alpha-pos", type=float, default=DEFAULTS["alpha_pos"],
                     help="Opacity of positive/amber isosurface")
    iso.add_argument("--alpha-neg", type=float, default=DEFAULTS["alpha_neg"],
                     help="Opacity of negative/blue isosurface")
    iso.add_argument("--positive-color", type=parse_rgb, default=POSITIVE_RGB,
                     metavar="RRGGBB", help="Positive isosurface color")
    iso.add_argument("--negative-color", type=parse_rgb, default=NEGATIVE_RGB,
                     metavar="RRGGBB", help="Negative isosurface color")
    iso.add_argument("--grid", default=None,
                     help="Voxel-grid identifier; auto-detected when omitted")
    iso.add_argument("--field", default=None,
                     help="Scalar grid property; auto-detected when omitted")
    iso.add_argument("--convert-density-bohr", action="store_true",
                     help="Convert cube density from bohr^-3 to angstrom^-3 when supported by OVITO")
    iso.add_argument("--periodic", action="store_true",
                     help="Keep periodic boundary conditions from the cube reader")

    view = parser.add_argument_group("View and rendering")
    view.add_argument("--frames", type=int, default=DEFAULTS["frames"])
    view.add_argument("--fps", type=int, default=DEFAULTS["fps"])
    view.add_argument("--elev", type=float, default=DEFAULTS["elev"],
                      help="Camera elevation relative to the molecular long axis")
    view.add_argument("--start-azim", type=float, default=0.0)
    view.add_argument("--spin-degrees", type=float, default=360.0)
    view.add_argument("--spin-axis", choices=("auto", "x", "y", "z"), default="auto",
                      help="Rotation axis; auto uses the longest PCA axis")
    view.add_argument("--fit", choices=("all", "atoms"), default="all",
                      help="Fit camera to atoms+isosurfaces or atoms only")
    view.add_argument("--camera-padding", type=float, default=DEFAULTS["camera_padding"])
    view.add_argument("--perspective-fov", type=float, default=DEFAULTS["perspective_fov_deg"],
                      help="Vertical perspective field of view in degrees")
    view.add_argument("--atom-scale", type=float, default=DEFAULTS["atom_scale"])
    view.add_argument("--right-atom-shrink", type=float, default=DEFAULTS["right_atom_shrink"],
                      help="Relative atom-size factor for the right panel")
    view.add_argument("--bond-width", type=float, default=DEFAULTS["bond_width"])
    view.add_argument("--quality", choices=("draft", "normal", "high"), default="normal")
    view.add_argument("--parallel-mode", choices=("auto", "serial", "process"), default="auto",
                      help="Rendering scheduler. auto avoids multiprocessing for small draft jobs; process uses chunked multiprocessing.")
    view.add_argument("--workers", type=int, default=0,
                      help="Requested worker processes for --parallel-mode process. 0 = auto.")
    view.add_argument("--worker-ovito-threads", type=int, default=0,
                      help="OVITO/Tachyon CPU threads per worker. 0 = auto, using roughly cpu_count/workers.")
    view.add_argument("--min-frames-per-worker", type=int, default=8,
                      help="Cap workers so initialization is amortized over at least this many frames. Use 1 to force one worker per frame.")
    view.set_defaults(no_surface_prepass=True)
    view.add_argument("--surface-prepass", dest="no_surface_prepass", action="store_false",
                      help="Do a parent-process isosurface prepass for exact atom+surface camera fitting. Slower startup.")
    view.add_argument("--no-surface-prepass", dest="no_surface_prepass", action="store_true",
                      help="Skip parent-process isosurface prepass. This is now the default for speed; increase --camera-padding if needed.")
    view.add_argument("--gif-duration-ms", type=int, default=None,
                      help="Override GIF frame duration in ms. Larger means slower GIF, e.g. 140-180.")

    layout = parser.add_argument_group("Layout")
    layout.add_argument("--width", type=int, default=DEFAULTS["width"])
    layout.add_argument("--height", type=int, default=DEFAULTS["height"])
    layout.add_argument("--title-left", default="Atomic structure")
    layout.add_argument("--title-right", default="Differential charge density")
    layout.add_argument("--unit-label", default="e/Å³")
    layout.add_argument("--output-prefix", default=None,
                        help="Output path prefix without extension")
    layout.add_argument("--atom-colors", type=parse_atom_colors, default={},
                        metavar="H=#FFFFFF,C=#404040",
                        help="Custom atom colors in Element=#RRGGBB format, comma-separated")
    layout.add_argument("--no-png", action="store_true")
    layout.add_argument("--no-gif", action="store_true")

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.frames < 1:
        raise ValueError("--frames must be at least 1.")
    if args.fps < 1:
        raise ValueError("--fps must be at least 1.")
    if args.width < 700 or args.height < 450:
        raise ValueError("Use at least --width 700 and --height 450.")
    if args.camera_padding <= 0:
        raise ValueError("--camera-padding must be positive.")
    if args.atom_scale <= 0 or args.right_atom_shrink <= 0 or args.bond_width <= 0:
        raise ValueError("--atom-scale, --right-atom-shrink, and --bond-width must be positive.")
    if not (0 <= args.alpha_pos <= 1 and 0 <= args.alpha_neg <= 1):
        raise ValueError("Alpha values must lie between 0 and 1.")
    if args.no_png and args.no_gif:
        raise ValueError("Both outputs are disabled.")
    if args.perspective_fov <= 1 or args.perspective_fov >= 120:
        raise ValueError("--perspective-fov should be in a practical range, e.g. 10-40 degrees.")
    if args.workers < 0:
        raise ValueError("--workers must be >= 0. Use 0 for auto.")
    if args.worker_ovito_threads < 0:
        raise ValueError("--worker-ovito-threads must be >= 0. Use 0 for auto.")
    if args.min_frames_per_worker < 1:
        raise ValueError("--min-frames-per-worker must be at least 1.")
    if args.gif_duration_ms is not None and args.gif_duration_ms < 1:
        raise ValueError("--gif-duration-ms must be positive.")


def _render_frame_chunk(args_tuple):
    """Render a chunk of frames in one subprocess.

    This is intentionally chunk-based instead of one-task-per-frame: importing the
    cube, building OVITO pipelines, extracting isosurfaces, and initializing the
    renderer are the expensive parts.  A worker should pay that cost once and then
    render several camera angles.
    """
    chunk_id, frame_items, shared = args_tuple

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["OVITO_THREAD_COUNT"] = str(shared.get("worker_ovito_threads", 1))

    import_kwargs: dict = {"generate_bonds": False}
    try:
        import_kwargs["grid_type"] = VoxelGrid.GridType.PointData
    except AttributeError:
        pass
    if shared.get("convert_density_bohr"):
        import_kwargs["convert_field_bohr_to_angstrom"] = True

    remove_all_scene_pipelines()
    base = import_file(shared["cube_path"], **import_kwargs)

    bk = shared["build_kwargs"]
    left_p, right_p = build_pipelines(base, **bk)

    renderer = make_renderer(shared["quality"])
    viewport = Viewport(type=Viewport.Type.Perspective)

    spin_axis = np.asarray(shared["spin_axis"])
    radial_x = np.asarray(shared["radial_x"])
    radial_y = np.asarray(shared["radial_y"])
    center = np.asarray(shared["center"])
    tmp_dir = Path(shared["tmp_dir"])

    results: list[tuple[int, str]] = []
    first_in_chunk = True
    for frame_idx, angle_deg in frame_items:
        view_dir, camera_up = camera_orientation(
            angle_deg,
            shared["elev"],
            spin_axis,
            radial_x,
            radial_y,
        )
        configure_viewport(
            viewport,
            center=center,
            radius=shared["radius"],
            view_dir=view_dir,
            camera_up=camera_up,
            panel_size=shared["panel_size"],
            camera_padding=shared["camera_padding"],
            perspective_fov_deg=shared["perspective_fov"],
        )

        left_path = tmp_dir / f"left_{frame_idx:04d}.png"
        right_path = tmp_dir / f"right_{frame_idx:04d}.png"
        frame_path = tmp_dir / f"frame_{frame_idx:04d}.png"

        render_pipeline_to_file(left_p, viewport, renderer, left_path, shared["panel_size"])
        render_pipeline_to_file(right_p, viewport, renderer, right_path, shared["panel_size"])

        with Image.open(left_path) as left_img, Image.open(right_path) as right_img:
            composed = compose_figure(
                left_img,
                right_img,
                width=shared["width"],
                height=shared["height"],
                title_left=shared["title_left"],
                title_right=shared["title_right"],
                iso_level=shared["iso_level"],
                unit_label=shared["unit_label"],
                positive_color=shared["positive_color"],
                negative_color=shared["negative_color"],
                atom_legend_data=shared["atom_legend_data"],
            )
            composed.save(frame_path, format="PNG", optimize=True)
            # Use the very first global frame as the static PNG.
            if frame_idx == 0 and not shared["no_png"]:
                composed.save(shared["png_path"], format="PNG", optimize=True)

        results.append((frame_idx, str(frame_path)))
        first_in_chunk = False

    remove_all_scene_pipelines()
    return chunk_id, results

def main() -> int:
    args = parse_args()
    validate_args(args)

    cube_path = Path(args.cube_file).expanduser().resolve()
    if not cube_path.is_file():
        raise FileNotFoundError(f"Cube file does not exist: {cube_path}")

    remove_all_scene_pipelines()

    print(f"OVITO version: {OVITO_VERSION_STRING}")
    print(f"Reading: {cube_path}")

    import_kwargs = {"generate_bonds": False}
    try:
        import_kwargs["grid_type"] = VoxelGrid.GridType.PointData
    except AttributeError:
        pass

    if ovito_at_least(3, 15, 0):
        import_kwargs["convert_field_bohr_to_angstrom"] = args.convert_density_bohr
    elif args.convert_density_bohr:
        raise RuntimeError("--convert-density-bohr requires OVITO 3.15 or newer.")

    base = import_file(str(cube_path), **import_kwargs)

    grid_name, field_name, values = detect_grid_and_field(
        base,
        requested_grid=args.grid,
        requested_field=args.field,
    )

    print(f"   Detected grid:  {grid_name}")
    print(f"   Detected field: {field_name}")
    print(f"   Field range:    [{np.nanmin(values):.7g}, {np.nanmax(values):.7g}]")
    print_density_stats(values)

    iso_level = choose_iso_level(values, args.level, args.percentile)
    if args.surface_smoothing is not None:
        smoothing_level = max(0, args.surface_smoothing)
    else:
        smoothing_level = max(0, int(round(args.smooth_sigma * 6.0)))

    print(f"   Isovalue:       ±{iso_level:.7g}")
    print(f"   Mesh smoothing: {smoothing_level} iteration(s)")

    left_pipeline, right_pipeline = build_pipelines(
        base,
        grid_name=grid_name,
        field_name=field_name,
        iso_level=iso_level,
        smoothing_level=smoothing_level,
        alpha_pos=args.alpha_pos,
        alpha_neg=args.alpha_neg,
        positive_color=args.positive_color,
        negative_color=args.negative_color,
        atom_scale=args.atom_scale,
        right_atom_shrink=args.right_atom_shrink,
        bond_width=args.bond_width,
        periodic=args.periodic,
        atom_color_overrides=args.atom_colors,
    )

    if args.no_surface_prepass:
        print("Skipping parent-process isosurface prepass; using atom-only startup metadata.")
    else:
        print("Computing scene bounds and isosurfaces once in parent process...")
        right_data = right_pipeline.compute()
        surface_count = 0
        for identifier, surface in right_data.surfaces.items():
            try:
                count = len(surface.vertices["Position"])
            except Exception:
                count = 0
            print(f"   Surface {identifier}: {count:,} vertices")
            surface_count += count
        if surface_count == 0:
            print("   Warning: no isosurfaces were generated. Check --level and field units.")

    # Detect atom types present in the structure for the legend
    atom_legend_data: list[tuple[str, tuple[float, float, float]]] = []
    base_data = base.compute()
    if base_data.particles is not None:
        seen_symbols: set[str] = set()
        ptypes = base_data.particles_.particle_types_
        for ptype in ptypes.types:
            symbol = symbol_for_type(ptype)
            if symbol not in seen_symbols:
                seen_symbols.add(symbol)
                if args.atom_colors and symbol in args.atom_colors:
                    color = args.atom_colors[symbol]
                else:
                    color, _ = ELEMENT_STYLE.get(symbol, ((0.54, 0.56, 0.60), 0.46))
                atom_legend_data.append((symbol, color))
    # Sort by a CPK-ish order
    cpk_order = {"H": 0, "C": 1, "N": 2, "O": 3, "F": 4, "P": 5, "S": 6, "Cl": 7, "Br": 8, "I": 9, "U": 10}
    atom_legend_data.sort(key=lambda x: cpk_order.get(x[0], 99))
    print(f"   Atom types detected: {', '.join(s for s, _ in atom_legend_data)}")

    if args.no_surface_prepass:
        if base_data.particles is None:
            raise RuntimeError("No atoms were imported from the cube file.")
        atom_positions = np.asarray(base_data.particles.positions, dtype=float)
        center = atom_positions.mean(axis=0)
        radius = max(float(np.linalg.norm(atom_positions - center, axis=1).max()), 1.0)
        if args.fit == "all":
            print("   Note: --no-surface-prepass uses atom-only camera fitting. Increase --camera-padding if needed.")
    else:
        center, radius, atom_positions = calculate_scene_bounds(right_pipeline, fit_mode=args.fit)
    spin_axis = choose_spin_axis(args.spin_axis, atom_positions)
    radial_x, radial_y = make_camera_basis(spin_axis)

    print(f"   Camera center:  {np.array2string(center, precision=3)}")
    print(f"   Spin axis:      {np.array2string(spin_axis, precision=3)}")
    print(f"   Fit radius:     {radius:.3f}")
    print(f"   Projection:     perspective")
    print(f"   FOV:            {args.perspective_fov:.2f}°")

    output_prefix = (
        Path(args.output_prefix).expanduser().resolve()
        if args.output_prefix
        else cube_path.with_name(cube_path.stem + "_ovito_premium")
    )
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_prefix.with_suffix(".png")
    gif_path = output_prefix.with_suffix(".gif")

    panel_width = args.width // 2
    title_height = max(78, int(args.height * 0.096))
    footer_height = max(132, int(args.height * 0.148))
    panel_height = args.height - title_height - footer_height
    panel_size = (panel_width, panel_height)

    angles = args.start_azim + np.linspace(0.0, args.spin_degrees, args.frames, endpoint=False)

    # ── Scheduler: serial or chunked multiprocessing ───────────────
    # Important speed reality:
    #   Tachyon is already multi-threaded. Many single-thread workers can be
    #   slower than one process using all CPU cores because each spawned process
    #   must import OVITO, re-read the cube, build pipelines, and initialize the
    #   renderer. For small draft jobs, serial usually wins.
    n_cores = mp.cpu_count()

    if args.parallel_mode == "serial":
        use_process_pool = False
    elif args.parallel_mode == "process":
        use_process_pool = True
    else:
        use_process_pool = bool(args.workers > 0 or (args.frames >= 72 and args.quality != "draft"))

    build_kwargs = dict(
        grid_name=grid_name,
        field_name=field_name,
        iso_level=iso_level,
        smoothing_level=smoothing_level,
        alpha_pos=args.alpha_pos,
        alpha_neg=args.alpha_neg,
        positive_color=args.positive_color,
        negative_color=args.negative_color,
        atom_scale=args.atom_scale,
        right_atom_shrink=args.right_atom_shrink,
        bond_width=args.bond_width,
        periodic=args.periodic,
        atom_color_overrides=args.atom_colors,
    )

    def render_serial_frames() -> None:
        renderer = make_renderer(args.quality)
        viewport = Viewport(type=Viewport.Type.Perspective)

        with tempfile.TemporaryDirectory(prefix="ovito_premium_frames_") as tmpdir:
            tmp = Path(tmpdir)
            frame_paths: list[Path] = []

            for index, angle in enumerate(angles):
                print(f"Rendering frame {index + 1:>3}/{args.frames}  azimuth={float(angle):7.2f}°")

                view_dir, camera_up = camera_orientation(
                    angle_deg=float(angle),
                    elevation_deg=args.elev,
                    spin_axis=spin_axis,
                    radial_x=radial_x,
                    radial_y=radial_y,
                )
                configure_viewport(
                    viewport,
                    center=center,
                    radius=radius,
                    view_dir=view_dir,
                    camera_up=camera_up,
                    panel_size=panel_size,
                    camera_padding=args.camera_padding,
                    perspective_fov_deg=args.perspective_fov,
                )

                left_path = tmp / f"left_{index:04d}.png"
                right_path = tmp / f"right_{index:04d}.png"
                frame_path = tmp / f"frame_{index:04d}.png"

                render_pipeline_to_file(left_pipeline, viewport, renderer, left_path, panel_size)
                render_pipeline_to_file(right_pipeline, viewport, renderer, right_path, panel_size)

                with Image.open(left_path) as left_img, Image.open(right_path) as right_img:
                    composed = compose_figure(
                        left_img,
                        right_img,
                        width=args.width,
                        height=args.height,
                        title_left=args.title_left,
                        title_right=args.title_right,
                        iso_level=iso_level,
                        unit_label=args.unit_label,
                        positive_color=args.positive_color,
                        negative_color=args.negative_color,
                        atom_legend_data=atom_legend_data,
                    )
                    composed.save(frame_path, format="PNG", optimize=True)
                    if index == 0 and not args.no_png:
                        composed.save(png_path, format="PNG", optimize=True)

                frame_paths.append(frame_path)

            if not args.no_gif:
                print("Encoding GIF with a shared global palette...")
                save_gif_with_global_palette(frame_paths, gif_path, args.fps, args.gif_duration_ms)

    if not use_process_pool:
        print("   Render scheduler: serial single-process")
        print("   Reason: avoids spawn/import/cube-reload overhead; OVITO/Tachyon can use its internal CPU threading.")
        if args.worker_ovito_threads:
            print("   Note: --worker-ovito-threads only affects process workers. For serial, set OVITO_THREAD_COUNT before launching if needed.")
        render_serial_frames()
        n_workers = 1
        effective_worker_threads = 0

    else:
        if args.workers > 0:
            requested_workers = min(args.workers, n_cores, args.frames)
        else:
            target_threads = 8 if args.quality == "draft" else 12
            requested_workers = max(1, min(args.frames, max(1, n_cores // target_threads)))

        max_workers_by_frames = max(1, math.ceil(args.frames / args.min_frames_per_worker))
        n_workers = min(requested_workers, n_cores, args.frames, max_workers_by_frames)

        if n_workers <= 1 and args.parallel_mode == "auto":
            print("   Auto scheduler switched to serial because effective workers would be 1.")
            render_serial_frames()
            effective_worker_threads = 0
        else:
            effective_worker_threads = (
                max(1, n_cores // max(1, n_workers))
                if args.worker_ovito_threads == 0
                else int(args.worker_ovito_threads)
            )
            if args.workers > n_workers:
                print(
                    f"   Requested workers: {args.workers}; effective workers: {n_workers} "
                    f"(capped by --min-frames-per-worker={args.min_frames_per_worker})."
                )
            print("   Render scheduler: process chunk pool")
            print(f"   Worker processes: {n_workers}")
            print(f"   OVITO threads per worker: {effective_worker_threads}")
            print(f"   Approx. active CPU threads: {n_workers * effective_worker_threads}")
            print(f"   Frames per worker: about {math.ceil(args.frames / n_workers)}")
            print("   Parallel strategy: fewer fat workers; each worker loads the cube once and renders a chunk.")

            # Must be set before spawned children import this module/OVITO.
            os.environ["OVITO_THREAD_COUNT"] = str(effective_worker_threads)

            shared = dict(
                cube_path=str(cube_path),
                convert_density_bohr=args.convert_density_bohr,
                build_kwargs=build_kwargs,
                quality=args.quality,
                elev=args.elev,
                spin_axis=tuple(float(x) for x in spin_axis),
                radial_x=tuple(float(x) for x in radial_x),
                radial_y=tuple(float(x) for x in radial_y),
                center=tuple(float(x) for x in center),
                radius=float(radius),
                panel_size=(int(panel_width), int(panel_height)),
                camera_padding=args.camera_padding,
                perspective_fov=args.perspective_fov,
                width=args.width,
                height=args.height,
                title_left=args.title_left,
                title_right=args.title_right,
                iso_level=float(iso_level),
                unit_label=args.unit_label,
                positive_color=tuple(float(x) for x in args.positive_color),
                negative_color=tuple(float(x) for x in args.negative_color),
                atom_legend_data=list((s, tuple(float(c) for c in col)) for s, col in atom_legend_data),
                no_png=args.no_png,
                worker_ovito_threads=int(effective_worker_threads),
                tmp_dir="",
                png_path=str(png_path),
            )

            with tempfile.TemporaryDirectory(prefix="ovito_premium_frames_") as tmpdir:
                tmp = Path(tmpdir)
                shared["tmp_dir"] = str(tmp)
                frame_paths: list[Path] = []

                frame_items = [(i, float(angles[i])) for i in range(args.frames)]
                chunks_raw = np.array_split(np.array(frame_items, dtype=object), n_workers)
                tasks = []
                for chunk_id, chunk in enumerate(chunks_raw):
                    items = [(int(item[0]), float(item[1])) for item in chunk.tolist()]
                    if items:
                        tasks.append((chunk_id, items, shared))

                completed = 0
                with mp.get_context("spawn").Pool(processes=n_workers) as pool:
                    results: dict[int, Path] = {}
                    for chunk_id, chunk_results in pool.imap_unordered(_render_frame_chunk, tasks):
                        for frame_idx, frame_path_str in chunk_results:
                            results[frame_idx] = Path(frame_path_str)
                            completed += 1
                            print(f"   [{completed:>3}/{args.frames}] Frame {frame_idx + 1} done  (chunk {chunk_id + 1})")
                    frame_paths = [results[i] for i in range(args.frames)]

                if not args.no_gif:
                    print("Encoding GIF with a shared global palette...")
                    save_gif_with_global_palette(frame_paths, gif_path, args.fps, args.gif_duration_ms)

    print("Done.")
    if not args.no_png:
        print(f"   PNG: {png_path}")
    if not args.no_gif:
        print(f"   GIF: {gif_path}")

    print("\nSpeed note:")
    if effective_worker_threads:
        print(f"   Process mode used {n_workers} worker(s) × {effective_worker_threads} OVITO thread(s).")
        print("   Each worker still re-imports the cube; use fewer workers with more threads to reduce startup overhead.")
    else:
        print("   Serial mode avoided multiprocessing startup and cube re-import overhead.")
        print("   For this 36-frame draft workload, this is often faster than process parallelism.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise

# python3 make_diff_charge_ovito-v6_speed.py   dicarbonate_001_on_QAS_diff_density_small.cube   --level 0.001   --smooth-sigma 0.7   --alpha-pos 0.56   --alpha-neg 0.44   --quality draft   --frames 72   --width 1200   --height 700   --gif-duration-ms 140