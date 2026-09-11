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
        "connection control at the bottom of the workspace to pick the executable once — the choice is "
        "remembered.",
    ),
    Step(
        "You're ready",
        "Choose a source model in the workspace, check its automatic preview, "
        "then Render sheet. Export sprite sheet saves the finished result.",
    ),
]

WORKFLOW_STEPS: list[Step] = [
    Step(
        "1 · Create the character",
        "Create a textured 3D character in Tripo or another modelling tool. "
        "Framemill needs the 3D model, not the original drawing.",
        action="Open Tripo", url="https://www.tripo3d.ai/",
    ),
    Step(
        "2 · Apply the animation",
        "Rig the character and apply a motion in Mixamo, Blender or another "
        "animation tool. For Mixamo, download the animated FBX with skin so "
        "the mesh is included. Walking, idle breathing, running and talking "
        "all use the same rendering pipeline; Framemill does not generate motion.",
        action="Mixamo rigging and animation guide",
        url="https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html",
    ),
    Step(
        "3 · Render one animation per source",
        "Load the animated file as the main source. Set directions and frame "
        "count, check Preview, then Render sheet. For an idle animation, load "
        "the idle FBX as the main source too. Export walk and idle separately; "
        "the second-model option is not needed. For a static model, choose "
        "one frame per direction; extra frames repeat the same pose.",
    ),
    Step(
        "4 · Export and configure your game",
        "Export sprite sheet opens a processed output preview. Use matching "
        "dimensions, orientation and framing for related sheets, and check "
        "their anchors. Use fixed world scale, the same feet/centre anchor and "
        "output offsets so related clips match. Your game still chooses which "
        "sheet to play. Optionally export a JSON sidecar with layout, sample "
        "times, playback FPS, loop mode and pivot; the image itself does not "
        "encode those rules.",
    ),
]

ANIMATION_STEPS: list[Step] = [
    Step(
        "Inspect without changing your export",
        "New sources preview facing South (front), regardless of the sheet's "
        "start direction. Drag to pan, scroll or pinch to zoom, and use the "
        "recenter control to reset the view transform. Facing buttons request "
        "another Blender preview, or switch instantly within a rendered sheet. "
        "These are viewing controls; export framing and order stay unchanged. "
        "Use Camera settings and render again to change the output framing.",
    ),
    Step(
        "How frames are sampled",
        "Framemill uses the range of the first active action found on an "
        "imported object, or the scene range if none is found. The detected "
        "action, start, end and source FPS appear after you load a model. "
        "Start/end fields trim that range. It samples evenly, including "
        "fractional times. Eleven frames is valid. It does not detect a stride "
        "or pick among NLA/multiple clips. Prepare one intended animation per "
        "source file.",
    ),
    Step(
        "Loop vs one-shot",
        "Loop keeps the walk-cycle behaviour: the final source endpoint is "
        "excluded and phase wraps inside that range. Reverse wraps too. "
        "One-shot includes both endpoints when there are two or more frames, "
        "ignores phase, reverses without wrapping, and stops preview playback "
        "on the last frame. A single one-shot frame is the start pose, or the "
        "end pose if reverse is on. A single loop frame is start + phase × span.",
    ),
    Step(
        "Preview speed is not export timing",
        "The FPS control changes viewer playback only. Frame count changes "
        "how densely the source is sampled. Set the intended animation speed "
        "separately in your game engine, or write it into the optional metadata "
        "sidecar as playback_fps (distinct from source_fps).",
    ),
    Step(
        "First-frame replacement is a compatibility option",
        "The optional second model replaces frame 01 in each direction; "
        "it does not add a slot. Eleven requested frames become one replacement "
        "and ten original samples. The remaining samples are not redistributed. "
        "The replacement uses the second model's end pose by default and the "
        "main model's framing; scale, origin and orientation must match.",
    ),
    Step(
        "Replacement does not create a smooth transition",
        "There is no pose blending. Preview playback includes the replacement; "
        "skipping it in-game still leaves an uneven loop-boundary gap. Use it "
        "only for an engine that explicitly requires this layout and accepts "
        "that tradeoff. For ordinary idle/walk states, render separate sheets.",
    ),
]


TROUBLESHOOTING_STEPS: list[Step] = [
    Step(
        "Model faces the wrong way",
        "South is the front camera. Sheet order and preview facing do not "
        "rotate the mesh. Use Source facing → Left/Right 90° or the yaw field "
        "to correct the imported source (animation included) without changing "
        "sheet order. Up-axis correction and free 3D orbit are not provided.",
    ),
    Step(
        "Drifting, small or clipped sprites",
        "Framemill does not remove root motion. Prepare an in-place animation "
        "when the game moves the actor. For matching walk/idle/attack sheets, "
        "switch Camera to Fixed world scale and set the same world-unit origin "
        "(do not rely on each clip's bounds). Output X/Y offsets are finished "
        "cell pixels: +X right, +Y down. Fit mode still sizes each clip from "
        "its own bounds. Increase the fit multiplier or fixed scale to make "
        "the sprite smaller. Viewer pan/zoom does not change the crop.",
    ),
    Step(
        "Recipes, validation and size limits",
        "Save recipe writes a versioned JSON file with relative source paths, "
        "render settings and export config. Load it from the desktop picker or "
        "an absolute path in the browser preview. Invalid frames, inverted "
        "ranges and oversized sheets (too many pixels of RGBA) are rejected "
        "before render. The CLI also rejects zero/negative --frames and "
        "unknown --format values.",
    ),
    Step(
        "Camera and output size",
        "90° is level; smaller angles look down from above. Framing changes "
        "orthographic scale. Orbit distance is not zoom and also changes light "
        "placement. Use Framing to change the character's size in the sprite.",
    ),
    Step(
        "Missing mesh or textures",
        "Include the character mesh with the animation. Keep glTF buffers and "
        "textures, or OBJ material files, alongside their source. Open the file "
        "in Blender to check the source if it renders blank or without textures.",
    ),
    Step(
        "Transparency, dithering and palettes",
        "32-bit PNG/TGA supports alpha. Soft edges are anti-aliasing; dithering "
        "is for reduced-colour output. Edge bleed extends hidden RGB, not the "
        "silhouette or cell padding. Adaptive palettes can vary across sheets. "
        "Use a shared palette for related animations; adding a missing key "
        "colour can shift palette indices, so check your engine's requirements.",
    ),
    Step(
        "Reporting a problem",
        "Include your OS, Blender and Framemill versions, source format, settings, "
        "steps and error text. A minimal model you are permitted to share helps. "
        "The CLI currently has fewer controls and export formats than this app.",
    ),
]
