"""In-app guide content: Blender setup + the drawing -> rigged 3D -> sheet workflow.

Plain data so the UI can render it (and so it's easy to translate/extend).
Each step: (title, body, optional action label, optional url).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Step:
    title: str
    body: str
    action: str | None = None
    url: str | None = None


SETUP_STEPS: list[Step] = [
    Step(
        "Install Blender",
        "framemill renders through Blender running in the background — you never "
        "have to open Blender yourself. Install any recent version (4.2 or newer "
        "recommended), then return here.",
        action="Download Blender",
        url="https://www.blender.org/download/",
    ),
    Step(
        "Point framemill at Blender",
        "framemill looks for Blender on your PATH and in the usual install "
        "locations automatically. If it can't find it, use the 'Locate Blender' "
        "button on the Render tab to pick the executable once — the choice is "
        "remembered.",
    ),
    Step(
        "You're ready",
        "Drop in a rigged, animated model on the Render tab, pick a preset, and "
        "click Render. That's the whole loop.",
    ),
]

WORKFLOW_STEPS: list[Step] = [
    Step(
        "1 · Start from a 2D character drawing",
        "Begin with a clean front-facing (T-pose or A-pose) drawing of your "
        "character on a plain background. This is the single reference the rest "
        "of the pipeline builds on.",
    ),
    Step(
        "2 · Turn the drawing into a 3D model (Tripo)",
        "Upload the drawing to an image-to-3D service to generate a textured 3D "
        "mesh. Export it as FBX or glTF/GLB.",
        action="Open Tripo",
        url="https://www.tripo3d.ai/",
    ),
    Step(
        "3 · Rig and animate it (Mixamo)",
        "Upload the mesh to Mixamo (free, Adobe account). Its auto-rigger adds a "
        "skeleton; then pick an animation such as a walk cycle. Download as FBX "
        "with skin. For a clean idle frame, also download a standing/idle clip.",
        action="Open Mixamo",
        url="https://www.mixamo.com/",
    ),
    Step(
        "4 · Render the sprite sheet (framemill)",
        "Back on the Render tab, load the walk-cycle FBX (and optionally the idle "
        "FBX for frame 0). Choose the number of directions and frames, pick a "
        "preset, and render. Export PNG for modern engines or TGA for legacy 2D "
        "engines.",
    ),
    Step(
        "Not using Tripo?",
        "Any rigged, animated FBX/GLB works — Mixamo library characters, your own "
        "Blender rigs, asset-store models. If a model renders too dark or washed "
        "out, switch presets or nudge Ambient strength and Colour management on "
        "the Render tab.",
    ),
]
