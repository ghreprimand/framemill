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
        "their anchors: each source is framed independently. Your game chooses "
        "which sheet/frames to play, their speed, and whether to loop. "
        "Framemill exports images, not animation-state or timing metadata.",
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
        "imported object, or the scene range if none is found. It samples "
        "evenly, including fractional times. Eleven frames is valid. It does "
        "not detect a stride, select among clips, or repair loop boundaries. "
        "Prepare one intended animation per source file.",
    ),
    Step(
        "Looping assumption / one-shot actions",
        "The final source endpoint is excluded, assuming it repeats the "
        "starting pose. Phase wraps within that range; reverse changes its "
        "traversal. Attacks, jumps and deaths can render, but may lose their "
        "exact final pose, and preview playback loops them. There is no "
        "one-shot/include-end mode or source-range editor in the UI yet. "
        "Trim the source in your animation tool before export.",
    ),
    Step(
        "Preview speed is not export timing",
        "The FPS control changes viewer playback only. Frame count changes "
        "how densely the source is sampled. Set the intended animation speed "
        "separately in your game engine.",
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
        "South assumes the source already faces the front camera. Sheet order "
        "does not realign the mesh, and preview facing buttons only change the "
        "view. Correct source orientation in your modelling tool before export.",
    ),
    Step(
        "Drifting, small or clipped sprites",
        "Framemill does not remove root motion. Prepare an in-place animation "
        "when the game moves the actor. Increase Camera → Framing to make the "
        "sprite smaller, then render again and check all directions and extreme "
        "poses. Viewer pan/zoom does not change the exported crop. Separate "
        "animation files are framed independently.",
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
