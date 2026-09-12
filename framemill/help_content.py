"""In-app Help content: categories, articles, and search.

Pure data. No Flet imports. Existing guide.py wording is embedded verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import __version__, guide

REPO_URL = "https://github.com/ghreprimand/framemill"
BRAND_URL = "https://unfinished-works.com"

Block = tuple


def _t(*parts: str) -> str:
    return "".join(parts)


def _ctl(name: str, what: str, *, options: str, default: str, effect: str, gotcha: str) -> list[Block]:
    return [
        ("h", name),
        ("p", what),
        ("li", [
            f"Range or options: {options}",
            f"Default: {default}",
            f"Effect: {effect}",
            f"Gotcha: {gotcha}",
        ]),
    ]


@dataclass(frozen=True)
class Category:
    id: str
    title: str
    order: int
    blurb: str


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    category: str
    body: list[Block]
    keywords: tuple[str, ...] = field(default_factory=tuple)


def _step_blocks(step: guide.Step) -> list[Block]:
    blocks: list[Block] = [("h", step.title), ("p", step.body)]
    if step.action and step.url:
        blocks.append(("link", step.action, step.url))
    return blocks


CATEGORIES: list[Category] = [
    Category("getting-started", "Getting started", 1,
             "Install Blender, then the path from T-pose art through Tripo and Mixamo to a sheet."),
    Category("workspace", "The workspace tour", 2,
             "Sidebar, viewer, preview vs sheet, and playback."),
    Category("source", "Source & recipes", 3,
             "Models, detected animation, presets, and portable recipes."),
    Category("geometry", "Sprite geometry", 4,
             "Directions, frames, cell size, and the sheet-size readout."),
    Category("appearance", "Appearance (Look)", 5,
             "Camera, lighting, and colour: the 03 / Studio Appearance panel."),
    Category("layout", "Layout & timing", 6,
             "Sheet order, source facing, sampling, and first-frame replacement."),
    Category("preview", "Preview & automatic refresh", 7,
             "South-facing first look, debounce, and what Export still uses."),
    Category("export", "Exporting", 8,
             "Formats, palettes, metadata sidecar, and the export dialog."),
    Category("orientation", "Direction & orientation", 9,
             "South as front, sheet order vs mesh yaw, clockwise-from-N."),
    Category("cli", "Command line (CLI)", 10,
             "render, inspect, gui, and every flag."),
    Category("troubleshooting", "Troubleshooting", 11,
             "Facing, clipping, textures, palettes, config location."),
    Category("concepts", "How it works", 12,
             "Headless Blender pipeline, compositor, config vs recipe."),
    Category("about", "About", 13,
             "Version, license, and project links."),
    Category("reference", "Reference: every control", 14,
             "Element-level notes for every control you can touch."),
]


ARTICLES: list[Article] = [
    Article(
        "install-blender", "Install Blender", "getting-started",
        _step_blocks(guide.SETUP_STEPS[0]),
        ("blender 4.2", "not bundled"),
    ),
    Article(
        "connect-blender", "Connect Blender", "getting-started",
        _step_blocks(guide.SETUP_STEPS[1]) + [
            ("p", _t(
                "The footer connection control shows whether Blender was found. ",
                "On the desktop app you can pick the executable once; the path is ",
                "remembered in the user config. The browser preview uses PATH or ",
                "a path already saved by the desktop app.",
            )),
        ],
        ("locate blender", "PATH"),
    ),
    Article(
        "pipeline-at-a-glance", "The pipeline at a glance", "getting-started",
        _step_blocks(guide.WORKFLOW_STEPS[0])
        + _step_blocks(guide.WORKFLOW_STEPS[1])
        + [
            ("p", _t(
                "Framemill renders the motion already present in your model. ",
                "It does not create animations, identify footsteps, or generate transitions. ",
                "Walking is one use case; idle breathing, running, talking, and other ",
                "imported animations use the same pipeline.",
            )),
            ("p", "The whole path:"),
            ("kbd", "concept / T-pose art  ->  3D model (Tripo)  ->  rig + animate (Mixamo)  ->  framemill  ->  your engine"),
            ("p", _t(
                "You need a rigged, animated 3D model with its mesh. If you already have one, ",
                "skip to Your first sheet. If you start from a drawing or an idea, ",
                "the next two articles get you there.",
            )),
        ],
        ("tripo", "mixamo", "pipeline", "t-pose", "a-pose"),
    ),
    Article(
        "make-a-model", "Make a 3D model (Tripo)", "getting-started",
        [
            ("p", _t(
                "Tripo turns a text prompt or an image into a textured 3D model. ",
                "You can substitute Blender, a purchased model, or a scan. ",
                "The requirement is a humanoid mesh you can rig.",
            )),
            ("li", [
                "Aim for a character in a T-pose or A-pose (arms out, standing straight, facing forward). Auto-riggers need a clean neutral pose.",
                "Keep it a single connected humanoid mesh where possible.",
                "Export as FBX or GLB. Both carry the mesh and textures, which the next steps need.",
            ]),
            ("link", "Open Tripo", "https://www.tripo3d.ai/"),
        ],
        ("tripo", "t-pose", "a-pose", "glb"),
    ),
    Article(
        "rig-mixamo", "Rig and animate (Mixamo)", "getting-started",
        [
            ("p", _t(
                "Mixamo (free with an Adobe account) auto-rigs a humanoid and applies ",
                "ready-made animations.",
            )),
            ("h", "Upload your model"),
            ("li", [
                "Mixamo accepts FBX, OBJ, or a ZIP (use ZIP for OBJ plus its .mtl and textures). An FBX or GLB with embedded textures is easiest.",
                "Place the auto-rig markers (chin, wrists, elbows, knees, groin) on the T-pose or A-pose.",
            ]),
            ("h", "Pick an animation"),
            ("li", [
                "Choose a motion, for example Walking, Idle, or an attack.",
                "For anything the game moves across the ground, turn In Place on. If a clip still travels, turn on Remove root motion in Layout & timing so each frame is re-centered.",
            ]),
            ("h", "Download with the settings framemill needs"),
            ("li", [
                "Format: FBX Binary (.fbx).",
                "Skin: With Skin. This is the important one. Without Skin exports only the skeleton, and framemill has no mesh to render.",
                "Frames per Second: 30 or 60 is fine. framemill re-samples to the frame count you choose.",
                "Keyframe Reduction: None, so the motion stays faithful to what you previewed.",
            ]),
            ("p", _t(
                "For a static, non-animated sheet, download the character with the T-Pose animation, ",
                "still With Skin, then choose 1 frame per direction in framemill. ",
                "Download each animation you want as its own file (walk.fbx, idle.fbx, attack.fbx).",
            )),
            ("link", "Mixamo rigging and animation guide",
             "https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html"),
        ],
        ("mixamo", "with skin", "in place", "fbx binary", "keyframe reduction", "t-pose", "root motion"),
    ),
    Article(
        "first-sheet", "Your first sheet", "getting-started",
        _step_blocks(guide.SETUP_STEPS[2])
        + _step_blocks(guide.WORKFLOW_STEPS[2])
        + [
            ("p", _t(
                "Select a model to render a front-facing (South) preview automatically, ",
                "independently of the saved sheet start direction. Set appearance, sprite ",
                "dimensions, and layout, then choose Render sheet. Export sprite sheet ",
                "opens a separate output dialog and destination picker; rendering does not ",
                "write into your source folder.",
            )),
            ("li", [
                "Load the downloaded FBX (or GLB, glTF, OBJ) as the main source.",
                "framemill reads the first action's range and shows the detected action, start, end, span, and source FPS. Trim with Source start / Source end if needed.",
                "Set Directions (1 / 4 / 8 / 16) and Frames per direction.",
                "Choose Loop for cycles (walk, idle) or One-shot for attacks and deaths.",
                "If the character faces the wrong way, use Layout & timing, Source facing (South is the front camera).",
                "Preview, then Render sheet, then Export sprite sheet.",
            ]),
        ],
        ("first render", "south preview", "loop", "one-shot", "source facing"),
    ),
    Article(
        "aligned-sheets", "Keep related sheets aligned", "getting-started",
        [
            ("p", _t(
                "Export each animation separately (hero_walk.png, hero_idle.png, and so on). ",
                "So they line up in your engine, use the same framing for all of them.",
            )),
            ("li", [
                "Switch Camera, Framing mode to Fixed world scale.",
                "Set the same world-unit origin (usually the character root at 0, 0, 0) and the same output offsets for every sheet.",
            ]),
            ("p", _t(
                "Fit mode sizes each clip to its own bounds and will shift between clips whose poses differ. ",
                "If a walk still travels, turn on Remove root motion so Fit sizes the character, not the travel box.",
            )),
        ],
        ("fixed world scale", "origin", "related sheets"),
    ),
    Article(
        "formats-end-to-end", "File formats, end to end", "getting-started",
        [
            ("p", "What each stage takes in and writes out:"),
            ("li", [
                "Tripo: text or image in; FBX / GLB (textured) out.",
                "Mixamo: FBX / OBJ / ZIP (T-pose) in; FBX Binary, With Skin, In Place, no keyframe reduction out.",
                "framemill: FBX / glTF / GLB / OBJ in; PNG / TGA / BMP sprite sheet out, plus an optional JSON sidecar.",
            ]),
        ],
        ("with skin", "in place", "t-pose", "fbx binary"),
    ),
    Article(
        "sidebar-areas", "Sidebar areas", "workspace",
        [
            ("p", "The left sidebar is three numbered areas:"),
            ("li", [
                "01 / Source: model, detected clip, Load/Save recipe, appearance preset.",
                _t(
                    "02 / Sprite geometry: cell width and height, directions, frame count, ",
                    "and the sheet-size / sprite-count / MiB readout.",
                ),
                _t(
                    "03 / Studio: a two-way switch between Appearance (Look) and ",
                    "Layout & timing. Those are equally important panels, not one header.",
                ),
            ]),
            ("p", _t(
                "Appearance presets (Generic PBR, Tripo, Mixamo, or Custom) live under ",
                "Source so they stay visible while you switch Studio panels. Presets ",
                "preserve your geometry and timing.",
            )),
        ],
        ("03 / studio", "sidebar"),
    ),
    Article(
        "viewer-controls", "The viewer", "workspace",
        [
            ("p", "The centre workspace shows either the current sprite or the full sheet."),
            ("li", [
                _t(
                    "Sprite / Sheet tabs switch the view. Sheet shows the last completed ",
                    "exportable sheet when one exists.",
                ),
                "Drag to pan; scroll or pinch to zoom.",
                "Recenter resets pan and gesture zoom.",
                "Base size sets the underlying display size of a sprite cell.",
                "The checkerboard toggle shows or hides the transparency backdrop.",
            ]),
            ("p", "The viewer displays rendered sprites rather than a freely orbitable 3D model."),
            ("p", guide.ANIMATION_STEPS[0].body),
        ],
        ("pan", "pinch", "base size", "checkerboard", "recenter"),
    ),
    Article(
        "preview-vs-render", "Preview vs Render sheet", "workspace",
        [
            ("p", _t(
                "Preview (and automatic refresh) builds a single South-or-facing view so ",
                "you can judge look and framing. It is disposable.",
            )),
            ("p", _t(
                "Render sheet builds every direction and frame. That result becomes the ",
                "exportable sheet. A later preview never replaces it; the badge reads ",
                "CHANGES PENDING until you render the sheet again.",
            )),
            ("p", _t(
                "Export sprite sheet stays disabled until a sheet has been rendered. ",
                "It always writes the last completed sheet, not the 1-frame preview.",
            )),
        ],
        ("changes pending", "exportable"),
    ),
    Article(
        "playback-and-status", "Playback, directions and status", "workspace",
        [
            ("p", _t(
                "Facing buttons request another Blender preview before a sheet exists, ",
                "or switch instantly between rendered directions afterward.",
            )),
            ("p", _t(
                "The frame strip and play control review the last completed sheet's ",
                "animation when one exists. Preview playback stops at the last one-shot frame.",
            )),
            ("p", _t(
                "The footer shows status and a cancel control while a render is running. ",
                "Locate Blender is the connection chip on the left of the footer.",
            )),
            ("p", _t(
                "Progress appears as a thin bar during Blender work. Full-sheet renders ",
                "lock the sidebar; automatic previews leave it usable so you can keep editing.",
            )),
        ],
        ("frame strip", "cancel", "status"),
    ),
    Article(
        "loading-models", "Loading a model", "source",
        [
            ("p", "Import FBX, glTF/GLB, or OBJ. Include the character mesh with the animation."),
            ("p", _t(
                "Keep glTF buffers and textures, or OBJ material files, alongside their source. ",
                "Open the file in Blender to check the source if it renders blank or without textures.",
            )),
            ("p", _t(
                "The desktop app uses a native file picker. The browser preview loads models ",
                "using an absolute path on this computer.",
            )),
            ("note", _t(
                "A static model works: choose 1 frame per direction. Requesting more frames ",
                "from a static source repeats the same pose; it does not animate the model.",
            )),
        ],
        ("fbx", "glb", "gltf", "obj", "textures"),
    ),
    Article(
        "detected-animation", "Detected action and range", "source",
        [
            ("p", guide.ANIMATION_STEPS[1].body),
            ("p", _t(
                "The workspace shows the detected action, start, end, span and source FPS ",
                "after you load a model, plus mesh count and world-space W x D x H. ",
                "Start/end fields under Layout & timing trim that range.",
            )),
            ("kbd", "framemill inspect model.fbx"),
            ("p", _t(
                "inspect reports the range, action name, source FPS, mesh count and dimensions. ",
                "Many meshes or an unexpectedly large box usually means stray geometry is ",
                "enlarging the fit frame.",
            )),
        ],
        ("frame_start", "source fps", "inspect"),
    ),
    Article(
        "appearance-presets", "Appearance presets", "source",
        [
            ("p", _t(
                "Generic PBR, Tripo and Mixamo copy camera, light and colour settings onto ",
                "the current document. They leave output layout and animation choices intact.",
            )),
            ("p", "If you then move a slider, the preset menu shows Custom appearance."),
        ],
        ("generic pbr", "tripo", "mixamo", "custom appearance"),
    ),
    Article(
        "recipes", "Portable recipes", "source",
        [
            ("p", guide.TROUBLESHOOTING_STEPS[2].body),
            ("p", _t(
                "Save recipe writes a versioned JSON file with relative source paths, ",
                "render settings and export config. That is separate from the user config ",
                "that remembers Blender and last-used settings.",
            )),
            ("p", _t(
                "Load a recipe from the desktop picker or an absolute path in the browser ",
                "preview. A missing source is rejected and does not keep applying settings ",
                "onto the previously loaded model.",
            )),
        ],
        ("recipe.json", "relative path", "versioned"),
    ),
    Article(
        "sprite-geometry", "Directions, frames and cell size", "geometry",
        [
            ("p", _t(
                "Directions are 1, 4, 8 or 16. Frame count is 1-64. Cell width and height ",
                "are 1-1024 pixels. The readout shows finished sheet pixels, sprite count ",
                "(directions × frames), and an estimated RGBA size.",
            )),
            ("p", _t(
                "Oversized sheets (too many pixels of RGBA) are rejected before render. ",
                "Validation also rejects inverted source ranges and invalid numeric settings.",
            )),
            ("p", _t(
                "Odd counts such as 11 are valid; they change temporal sampling density, ",
                "not the duration or content of the source motion.",
            )),
            ("note", _t(
                "Direction count and sheet order do not trigger an automatic preview. ",
                "They change the exportable layout; Render sheet to apply them to the sheet.",
            )),
        ],
        ("96", "mib", "sheet size", "16 directions"),
    ),
    Article(
        "camera-framing", "Camera, framing and orbit distance", "appearance",
        [
            ("p", guide.TROUBLESHOOTING_STEPS[3].body),
            ("h", "Elevation"),
            ("p", "90° is level; smaller angles look down from above."),
            ("h", "Framing mode"),
            ("p", _t(
                "Fit this clip fills each clip to the cell from its own bounds, reserving only ",
                "a thin anti-alias margin (and a small ground band when Anchor is feet). ",
                "Fixed world scale uses an explicit world-unit scale and origin (X/Y/Z) that ",
                "stay identical across clips; required for matching walk/idle/attack sheets.",
            )),
            ("p", _t(
                "Fit multiplier is extra margin beyond that automatic fill. 1.0 fills the cell; ",
                "raise it for more breathing room (the model looks smaller). Fixed world scale ",
                "is a world-unit size; larger values also make the model smaller.",
            )),
            ("h", "Fit basis"),
            ("p", _t(
                "Visible only in Fit mode. Fit whole character (contain, default) uses the ",
                "larger of height and width so nothing crops. Height scales to character height ",
                "and may crop very wide poses. Width scales to the wider of X and Y.",
            )),
            ("h", "Anchor and offsets"),
            ("p", _t(
                "Fit mode can anchor to bounds centre or feet / lowest point. Fixed mode ",
                "uses the world origin you set. Output offsets are finished-cell pixels: ",
                "+X right, +Y down. Viewer pan/zoom is display-only and does not change the crop.",
            )),
            ("h", "Orbit distance"),
            ("p", _t(
                "Orbit distance is not zoom: it places the camera and the light. ",
                "Use Framing or Fixed world scale to change how large the character is.",
            )),
        ],
        ("orbit distance", "fit multiplier", "fixed world scale", "output offset", "fit basis"),
    ),
    Article(
        "light-environment", "Light and environment", "appearance",
        [
            ("p", "Light energy, softness (shadow soft size), and light colour control the key light."),
            ("p", _t(
                "Ambient strength and ambient colour fill the shadows. These travel with ",
                "appearance presets.",
            )),
        ],
        ("light energy", "softness", "ambient"),
    ),
    Article(
        "colour-material", "Colour and material", "appearance",
        [
            ("p", "View transform: Standard, AgX, or Filmic (Blender colour management)."),
            ("p", _t(
                "Exposure, gamma, and specular IOR are applied in the render. They update ",
                "the automatic preview after a short pause.",
            )),
        ],
        ("agx", "filmic", "exposure", "specular ior"),
    ),
    Article(
        "direction-order", "Direction order", "layout",
        [
            ("p", _t(
                "First direction, rotation (clockwise or counter-clockwise), and sheet layout ",
                "(directions as rows or as columns) change cell sequence only. They do not ",
                "rotate the mesh.",
            )),
            ("p", _t(
                "Clockwise from North is N → NE → E → SE → S → SW → W → NW. ",
                "The layout panel lists the actual output order. Match that order in your game; ",
                "do not assume its importer uses the same convention.",
            )),
            ("p", "Sheet order only changes cell sequence. It does not rotate the mesh."),
        ],
        ("clockwise", "rows", "columns", "start direction"),
    ),
    Article(
        "source-facing", "Source facing", "layout",
        [
            ("p", _t(
                "Left 90° / Right 90° and the yaw field rotate the imported source ",
                "(and its animation) around world Z. Independent of preview facing and sheet order.",
            )),
            ("p", guide.TROUBLESHOOTING_STEPS[0].body),
        ],
        ("yaw", "left 90", "source facing"),
    ),
    Article(
        "animation-sampling", "Animation sampling", "layout",
        [
            ("h", guide.ANIMATION_STEPS[1].title),
            ("p", guide.ANIMATION_STEPS[1].body),
            ("h", guide.ANIMATION_STEPS[2].title),
            ("p", guide.ANIMATION_STEPS[2].body),
            ("p", _t(
                "Loop keeps the walk-cycle formula: with phase zero and forward playback, ",
                "sample i is start + (i / frame_count) × (end − start). Fractional frames are ",
                "evaluated. The final endpoint is excluded to avoid repeating a loop's first pose. ",
                "Phase wraps; reverse wraps.",
            )),
            ("h", guide.ANIMATION_STEPS[3].title),
            ("p", guide.ANIMATION_STEPS[3].body),
            ("h", "Remove root motion"),
            ("p", _t(
                "Turn on Remove root motion (re-center each frame) when the source travels ",
                "across the ground. Fit mode then sizes the character from the largest single ",
                "frame, not the whole-clip travel box, and the camera recenters on each frame. ",
                "Leave it off if the source is already in-place (for example Mixamo In Place).",
            )),
        ],
        ("loop", "oneshot", "one-shot", "phase", "reverse", "playback_fps", "root motion"),
    ),
    Article(
        "first-frame-replacement", "First-frame replacement (advanced)", "layout",
        _step_blocks(guide.ANIMATION_STEPS[4])
        + _step_blocks(guide.ANIMATION_STEPS[5])
        + [
            ("p", _t(
                "For a normal idle animation, load the idle FBX as the main source and export ",
                "its own sheet. The second-model control is not an idle-sheet generator.",
            )),
            ("p", _t(
                "CLI equivalent: --idle. Keep this option unset unless your target engine ",
                "explicitly requires that layout and you accept the timing tradeoff.",
            )),
        ],
        ("idle", "replacement", "frame 01"),
    ),
    Article(
        "auto-preview", "Automatic preview refresh", "preview",
        [
            ("h", guide.ANIMATION_STEPS[0].title),
            ("p", guide.ANIMATION_STEPS[0].body),
            ("p", "New sources preview facing South (front), regardless of the sheet's start direction."),
            ("p", _t(
                "Camera, lighting, orientation, source-range and frame-size edits refresh the ",
                "preview after a short pause (about 450 ms after the last change). Slider ticks ",
                "do not each start Blender.",
            )),
            ("p", _t(
                "Directions, start direction, rotation and sheet layout do not auto-preview; ",
                "they are sheet-layout fields. Render sheet to bake them.",
            )),
            ("p", _t(
                "If you keep editing during a preview, the newest valid settings win. A finished ",
                "job does not skip the debounce window just because the sequence number advanced.",
            )),
            ("p", _t(
                "Cancel invalidates queued preview work so a leftover timer cannot restart. ",
                "The last completed sheet is preserved for the Sheet tab, playback and Export.",
            )),
        ],
        ("450", "debounce", "stale", "south"),
    ),
    Article(
        "exporting", "Exporting sprite sheets", "export",
        _step_blocks(guide.WORKFLOW_STEPS[3])
        + [
            ("p", _t(
                "Export sprite sheet opens a processed output preview. Rendering never writes ",
                "into your source folder. Export changes update the dialog preview without ",
                "starting Blender again.",
            )),
            ("h", "Formats and colour"),
            ("p", _t(
                "PNG, TGA, or BMP; 32-, 24- or 8-bit. 32-bit PNG/TGA supports alpha. ",
                "Use 24-bit or indexed output with a solid or key colour when the engine requires it.",
            )),
            ("p", _t(
                "Backgrounds: transparent (alpha), solid colour, or magic pink colour-key. ",
                "32-bit PNG offers transparent or solid only. 32-bit TGA also offers magic pink. ",
                "24-bit, 8-bit, and BMP offer magic pink or solid. Switching format or depth ",
                "resets an invalid leftover background. Soft edges are anti-aliasing; dithering ",
                "is for reduced-colour output.",
            )),
            ("h", "Edge bleed and palettes"),
            ("p", _t(
                "Edge bleed extends hidden RGB into transparent pixels without enlarging the ",
                "silhouette. It is not cell padding and not dithering.",
            )),
            ("p", _t(
                "Adaptive palettes can vary across sheets. Use Master palette to share a scene ",
                "palette (an indexed BMP is fine). Custom fixed colours is a typed index list ",
                "you build in the export dialog. Adaptive still puts a missing magic-pink key ",
                "at index 0. A supplied master palette or fixed list keeps its exact index ",
                "order and errors if the key colour is absent. See What a master palette file ",
                "is and how to create one.",
            )),
            ("h", "Metadata sidecar"),
            ("p", _t(
                "Optionally write a JSON sidecar with layout, sample times, playback_fps ",
                "(distinct from source_fps), loop mode and pivot. The image itself does not ",
                "encode those rules.",
            )),
            ("note", _t(
                "The CLI supports PNG/TGA, --recipe, --metadata, and the same settings ",
                "validation as the app. It does not offer the GUI export presets, palette ",
                "controls, or BMP output.",
            )),
        ],
        ("magic pink", "dithering", "palette", "sidecar", "tga", "bmp", "master palette"),
    ),
    Article(
        "dos-master-palette", "DOS master palette", "export",
        [
            ("p", _t(
                "DOS and Allegro 8-bit games use one shared 256-colour palette per scene. ",
                "The character sheet must be quantized to that same master palette as the ",
                "background. Index 0 is the transparent key (magic pink 255, 0, 255 in the ",
                "real assets).",
            )),
            ("p", "How to export a sheet that matches a scene:"),
            ("li", [
                "Export as BMP, 8-bit, Background = Magic pink.",
                "Set Palette to Master palette (share a scene palette).",
                "Load the scene BMP (for example BG_00.BMP). The embedded palette is used in exact index order.",
                "Sheet Direction order should match the engine (often First direction S, Rotation counter-clockwise).",
            ]),
            ("p", _t(
                "A supplied master palette is never reordered. If magic pink is missing, export ",
                "stops with an error instead of inserting it at index 0 (that would shift every ",
                "other colour). Adaptive palettes still place a missing key at index 0.",
            )),
            ("note", _t(
                "How to make or extract that file: see What a master palette file is and how ",
                "to create one. For a typed index list instead of a file, see Custom fixed colours.",
            )),
        ],
        ("master palette", "dos palette", "index 0", "allegro", "bg_00"),
    ),
    Article(
        "custom-fixed-colours", "Custom fixed colours", "export",
        [
            ("p", _t(
                "Custom fixed colours is a typed palette: you enter MULTIPLE colours, and the ",
                "order you put them in is the palette index. The first colour is index 0, the ",
                "second is index 1, and so on.",
            )),
            ("p", "How to build the list:"),
            ("li", [
                "Type one or more #RRGGBB codes and press Enter or Add. Spaces or commas separate several codes in one paste.",
                "Each row is a swatch, the hex value, and an index badge. Remove a row with the close icon.",
                "Drag rows to reorder. Index badges update so the new first colour is still index 0.",
                "Add magic pink inserts #ff00ff. Clear all empties the list.",
                "Pick a colour opens RGB sliders (0 to 255) bound to the hex field. It starts collapsed.",
            ]),
            ("p", _t(
                "For 8-bit DOS transparency, put magic pink (#ff00ff) first so transparent ",
                "pixels map to index 0. This is a typed list, not a file. Master palette loads ",
                "an indexed image or .pal/.gpl/.hex instead. Both reject a missing magic-pink ",
                "key; neither reorders a supplied list to insert it.",
            )),
            ("note", _t(
                "See also: DOS master palette, and What a master palette file is and how to create one.",
            )),
        ],
        ("custom colours", "fixed colours", "index 0", "#ff00ff"),
    ),
    Article(
        "create-master-palette", "What a master palette file is and how to create one", "export",
        [
            ("p", _t(
                "A master palette file is an indexed image (BMP, PNG, or GIF) or a .pal / .gpl / .hex ",
                "file whose colour ORDER is preserved exactly. The sprite sheet is quantized to ",
                "that same table so it shares a scene's global 256-colour palette, for example ",
                "the game's BG_00.BMP.",
            )),
            ("p", "How to create or extract one:"),
            ("li", [
                "Open the scene image in GIMP or Aseprite.",
                "Convert it to indexed colour using the exact scene palette (do not let the editor generate a new one).",
                "Export the indexed image, or export the palette as .pal or .gpl.",
                "Or point framemill straight at the shared indexed BMP. The embedded palette is read in index order.",
            ]),
            ("p", _t(
                "The transparent key (magic pink #ff00ff) must exist in the palette, usually at ",
                "index 0. framemill will not reorder or prepend a supplied master palette, so ",
                "indices stay in sync with the scene. A truecolour photo has no fixed palette ",
                "and is rejected. If you would rather type the colours, use Custom fixed colours.",
            )),
            ("note", _t(
                "See also: DOS master palette (export steps) and Custom fixed colours (typed list).",
            )),
        ],
        ("master palette file", "create palette", "index 0", "bg_00", "gimp", "aseprite"),
    ),
    Article(
        "direction-orientation", "South, sheet order and yaw", "orientation",
        [
            ("p", _t(
                "South is the front camera convention. Sheet start direction changes cell order. ",
                "Preview facing buttons change only the view.",
            )),
            ("p", _t(
                "Use Source facing (quarter turns or yaw) to rotate the imported source and ",
                "its animation. That does not change sheet order. Up-axis correction and free ",
                "3D orbit are not provided.",
            )),
            ("p", _t(
                "Clockwise from North is N → NE → E → SE → S → SW → W → NW. ",
                "The layout panel lists the actual output order. Match that order in your game.",
            )),
        ],
        ("south", "front camera", "orientation"),
    ),
    Article(
        "command-line", "Command line", "cli",
        [
            ("p", "The GUI is the primary interface. The CLI exists for scripting and CI."),
            ("h", "Subcommands"),
            ("li", [
                "framemill (no subcommand) or framemill gui: launch the desktop app.",
                "framemill render: render a sheet.",
                "framemill inspect: print animation frame range, action and fps as JSON.",
            ]),
            ("h", "render flags"),
            ("li", [
                "model: optional path when --recipe already names the source.",
                "-o / --output: required output path (extension set per --format).",
                "--preset: Generic PBR / Tripo / Mixamo key.",
                "--angles: 1, 4, 8 or 16.",
                "--frames: positive integer 1-64; zero or negative is an error.",
                "--recipe: versioned project recipe (JSON).",
                "--idle: advanced; replace frame 0 with a second model pose; keeps total count, no blending.",
                "--format: comma list: png, tga (not bmp).",
                "--magic-pink: TGA; transparent becomes magenta for legacy engines.",
                "--metadata: write a JSON sidecar next to each image.",
                "--blender: path to the Blender executable (or set PATH).",
            ]),
            ("kbd", "framemill render walk.fbx -o hero --preset mixamo --angles 8 --frames 8 --format png,tga"),
            ("kbd", "framemill render --recipe hero.recipe.json -o hero --metadata"),
            ("kbd", "framemill inspect walk.fbx"),
            ("p", _t(
                "CLI recipes currently restore source and render settings; their export ",
                "settings are used by the GUI only. Oversized sheets and inverted source ranges ",
                "are rejected before Blender starts.",
            )),
        ],
        ("--frames", "--recipe", "--magic-pink", "--metadata", "inspect"),
    ),
    Article(
        "troubleshooting", "Common problems", "troubleshooting",
        [
            *[block for step in guide.TROUBLESHOOTING_STEPS for block in _step_blocks(step)],
            ("h", "Where settings are stored"),
            ("p", _t(
                "Settings are stored in framemill/config.json under the user configuration ",
                "directory: $XDG_CONFIG_HOME (or ~/.config) on Linux, ",
                "~/Library/Application Support on macOS, and %APPDATA% on Windows. ",
                "These are application preferences. Use Save recipe for a portable, versioned ",
                "project file with relative source paths; that is separate from the user config.",
            )),
        ],
        ("xdg", "appdata", "clipped", "root motion"),
    ),
    Article(
        "how-it-works", "Headless Blender pipeline", "concepts",
        [
            ("p", _t(
                "framemill is a standalone GUI that runs Blender headless. You never have ",
                "to open Blender yourself.",
            )),
            ("kbd", "model  →  Blender (render_sprites.py)  →  per-angle PNG frames"),
            ("kbd", "compositor.py: crop → Lanczos → tile  →  sheet"),
            ("p", _t(
                "Consistent camera framing across an animation, Lanczos downscaling, ",
                "sprite-sheet layout, and legacy-engine TGA output are handled automatically.",
            )),
            ("h", "Config vs recipe"),
            ("p", _t(
                "User config remembers the Blender path and last render/export settings. ",
                "A recipe is a versioned project file you save next to your sources, with ",
                "relative paths. Load recipe restores that project; it does not replace the ",
                "need to have Blender installed.",
            )),
        ],
        ("render_sprites", "lanczos", "compositor", "headless"),
    ),
    Article(
        "about", "About Framemill", "about",
        [
            ("p", _t(
                f"Framemill {__version__}. Turn a rigged, animated 3D model into a ",
                "directional 2D sprite sheet. GPL-3.0-only.",
            )),
            ("p", "No Blender knowledge required. Blender is not bundled."),
            ("link", "Repository", REPO_URL),
            ("link", "Part of Unfinished Works", BRAND_URL),
        ],
        ("license", "gpl", "version", "unfinished works"),
    ),
    Article(
        "ref-workspace", "Top bar and viewer controls", "reference",
        [
            ("p", "Main workspace chrome: loading, render, view, playback, and status."),
        ]
        + _ctl(
            "Choose a model",
            "Opens a source file. Desktop uses the native picker. The browser preview asks for an absolute path.",
            options="fbx, glb, gltf, obj",
            default="No source loaded",
            effect="Loads the model, inspects its action range, and starts a South-facing preview.",
            gotcha="Keep glTF buffers/textures or OBJ materials next to the file. A missing mesh renders blank.",
        )
        + _ctl(
            "Preview",
            "Renders a single facing so you can judge look and framing.",
            options="Uses current settings and the selected facing (South on first load)",
            default="Automatic after load and after camera/light/timing edits",
            effect="Shows a disposable 1-frame view. Does not become the export.",
            gotcha="A later preview never replaces a completed sheet. Export still uses the last Render sheet.",
        )
        + _ctl(
            "Render sheet",
            "Renders every direction and frame into the exportable sheet.",
            options="Full directions × frames job",
            default="Off until you click it",
            effect="Replaces the last completed sheet and enables Export.",
            gotcha="Locks the sidebar while running. Cancel stops it. Layout-only fields (angles, order) need this to update the sheet.",
        )
        + _ctl(
            "Export sprite sheet",
            "Opens the export dialog on the last completed sheet.",
            options="Enabled only after a successful Render sheet",
            default="Disabled",
            effect="Lets you choose format, colour, palette, and destination without rendering again.",
            gotcha="Stays available after auto-previews. The dialog preview is processed output, not a new Blender job.",
        )
        + _ctl(
            "Cancel render",
            "Stops the in-progress Blender job.",
            options="Visible only while busy",
            default="Hidden",
            effect="Invalidates queued preview work so a leftover timer cannot restart.",
            gotcha="A queued Render sheet still starts after an interrupted preview. User cancel does not keep a stale preview timer.",
        )
        + _ctl(
            "Sprite / Sheet tabs",
            "Switch between one cell and the tiled sheet.",
            options="Sprite or Sheet",
            default="Sprite",
            effect="Sheet shows the last completed exportable sheet when one exists.",
            gotcha="Sheet view is empty until you have rendered a sheet. Sprite can show a 1-frame preview.",
        )
        + _ctl(
            "Recenter",
            "Resets pan and gesture zoom on the viewer.",
            options="Icon button (center-focus)",
            default="Centered, 1× gesture zoom",
            effect="Puts the sprite or sheet back in the middle of the viewport.",
            gotcha="Does not change Base size, export crop, or camera framing.",
        )
        + _ctl(
            "Base size",
            "Display scale of a sprite cell in the viewer.",
            options="100%, 200%, 300%, 400%, 600%",
            default="300%",
            effect="Changes how large the cell is drawn. Export pixels stay the same.",
            gotcha="This is not framing. Use Fit multiplier or Fixed world scale to change the crop.",
        )
        + _ctl(
            "Checkerboard",
            "Shows or hides the transparency backdrop.",
            options="On or off",
            default="On",
            effect="Helps you see alpha vs opaque pixels.",
            gotcha="Display only. It is not written into the export.",
        )
        + _ctl(
            "Facing buttons",
            "Change the viewed direction: S, SW, W, NW, N, NE, E, SE (or Front when angles is 1).",
            options="Eight compass names on a preview; sheet layout names after Render sheet",
            default="South (front) on a new source",
            effect="Before a sheet exists, requests another Blender preview. Afterward, switches instantly inside the sheet.",
            gotcha="View only. Never changes sheet order or source yaw.",
        )
        + _ctl(
            "Frame strip",
            "Thumbnails for each sampled frame of the current direction.",
            options="One tile per frame (1 on a preview)",
            default="Frame 1 selected",
            effect="Click a tile to inspect that frame.",
            gotcha="Preview has a single tile. Playback uses the last completed sheet when one exists.",
        )
        + _ctl(
            "Play / pause",
            "Animates the current direction at the viewer FPS.",
            options="Play or pause",
            default="Paused",
            effect="Steps through sheet frames. One-shot stops on the last frame.",
            gotcha="Viewer FPS is display speed only. It is not written into the image. Use the metadata sidecar for playback_fps.",
        )
        + _ctl(
            "Viewer FPS",
            "Playback speed for the Play control.",
            options="4, 6, 8, 12, 16, 24 fps",
            default="8 fps",
            effect="How fast the strip advances while playing.",
            gotcha="Does not change how densely the source is sampled. Frame count does that.",
        )
        + _ctl(
            "Viewer gestures",
            "Drag to pan. Scroll or pinch to zoom.",
            options="Pan any amount; gesture zoom about 0.25× to 8×",
            default="Centered, 1×",
            effect="Lets you inspect pixels. Recenter resets it.",
            gotcha="Display only. Does not change export crop, offsets, or camera.",
        )
        + _ctl(
            "Locate Blender",
            "Footer chip: connected version, or pick the executable once.",
            options="Auto-detect, PATH, or a remembered path",
            default="Whatever find_blender locates",
            effect="Stores the path in user config. Required before any render.",
            gotcha="The browser preview cannot pick a new executable; set it in the desktop app or on PATH.",
        )
        + _ctl(
            "Reset to defaults",
            "Restores render and export settings to factory defaults after a confirm dialog.",
            options="Confirm: Cancel or Reset",
            default="Off; current saved settings stay until you confirm",
            effect="Applies RenderSettings() defaults and the PNG RGBA export preset, then saves them.",
            gotcha="Keeps the loaded model and the remembered Blender path. Does not clear a completed sheet.",
        )
        + _ctl(
            "Help",
            "Opens this browser.",
            options="Search, category nav, Back to workspace",
            default="Hidden below 1000 px window width",
            effect="Starts on Getting started.",
            gotcha="Search replaces the category tree with ranked results until you clear the field.",
        )
        + _ctl(
            "Status line and progress bar",
            "Current activity, errors, and render progress.",
            options="Text plus a thin bar while busy",
            default="Choose a model to begin",
            effect="Shows inspect, preview, sheet, and export messages.",
            gotcha="A failed job prints the error here. Correct highlighted fields before rendering.",
        ),
        ("choose a model", "recenter", "base size", "locate blender", "reset to defaults",
         "frame strip", "checkerboard", "viewer fps"),
    ),
    Article(
        "ref-source", "Source panel controls", "reference",
        [
            ("p", "01 / Source: the loaded model, detected clip, recipes, and appearance preset."),
        ]
        + _ctl(
            "Model card",
            "Shows the loaded file name, format, and size. The folder icon reopens the picker.",
            options="fbx, glb, gltf, obj",
            default="No source loaded",
            effect="Same as Choose a model.",
            gotcha="Loading a new source clears the last completed sheet.",
        )
        + _ctl(
            "Detected clip line",
            "Action name, start, end, span, source FPS, mesh count, and W x D x H after inspect.",
            options="Read-only; updated after load",
            default="Load a model to read its animation range.",
            effect="Tells you what range Source start/end will trim, and whether extra meshes inflate the fit box.",
            gotcha="Uses the first active action on an imported object, or the scene range. No NLA picker. Unexpected dimensions usually mean stray geometry.",
        )
        + _ctl(
            "Load recipe",
            "Restores a versioned project file: source, idle, render settings, and export config.",
            options="*.recipe.json (desktop picker or absolute path on the web)",
            default="None",
            effect="Loads the recipe source and applies its settings.",
            gotcha="A missing source is rejected and does not keep applying settings onto the old model.",
        )
        + _ctl(
            "Save recipe",
            "Writes a versioned JSON file with relative source paths.",
            options="Desktop save picker or absolute path on the web",
            default="None",
            effect="Portable project next to your sources, separate from user config.",
            gotcha="User config still remembers Blender and last-used settings on this machine.",
        )
        + _ctl(
            "Appearance preset",
            "Copies camera, light, and colour settings from Generic PBR, Tripo, or Mixamo.",
            options="Generic PBR, Tripo, Mixamo, Custom appearance",
            default="Whatever matches the current sliders (often Tripo after first use)",
            effect="Leaves directions, frames, layout, and animation choices intact.",
            gotcha="Moving a slider after a preset shows Custom appearance.",
        ),
        ("load recipe", "save recipe", "appearance preset", "detected clip"),
    ),
    Article(
        "ref-geometry", "Sprite geometry controls", "reference",
        [
            ("p", "02 / Sprite geometry: cell size, direction count, frame count, and the sheet readout."),
        ]
        + _ctl(
            "Width · px",
            "Width of one sprite cell in the finished sheet.",
            options="1 to 1024 pixels",
            default="96",
            effect="Sets cell width and the sheet width (with layout).",
            gotcha="Oversized sheets are rejected before render. This is export size, not Base size.",
        )
        + _ctl(
            "Height · px",
            "Height of one sprite cell in the finished sheet.",
            options="1 to 1024 pixels",
            default="128",
            effect="Sets cell height and the sheet height (with layout).",
            gotcha="Fit mode still crops to this aspect. Extreme poses can clip.",
        )
        + _ctl(
            "Directions",
            "How many camera headings are rendered.",
            options="1, 4, 8, 16",
            default="8",
            effect="Changes sheet layout and the facing-button set after Render sheet.",
            gotcha="Does not auto-preview. Render sheet to bake the new layout. Does not rotate the mesh.",
        )
        + _ctl(
            "Frames",
            "How many samples are taken along the source range, per direction.",
            options="1 to 64",
            default="4",
            effect="Sampling density. Odd counts such as 11 are valid.",
            gotcha="Not duration. A static source repeats the same pose. Zero or negative is rejected.",
        )
        + _ctl(
            "Geometry readout",
            "Computed sheet pixels, sprite count (directions × frames), and estimated RGBA MiB.",
            options="Read-only",
            default="Updates as you edit geometry",
            effect="Warns you before a huge sheet.",
            gotcha="The estimate is uncompressed RGBA. Validation can still reject the job.",
        ),
        ("width · px", "height · px", "directions", "frames", "sheet size"),
    ),
    Article(
        "ref-appearance", "Appearance controls", "reference",
        [
            ("p", "03 / Studio → Appearance: camera, light, and colour. These refresh the preview after a short pause."),
        ]
        + _ctl(
            "Elevation · 90° is level",
            "Camera pitch around the character.",
            options="30° to 120°, 1° steps",
            default="90°",
            effect="Below 90 looks down from above. 90 is level.",
            gotcha="This is not orbit in 3D. There is no free tumble.",
        )
        + _ctl(
            "Framing mode",
            "How the orthographic scale and look-at are chosen.",
            options="Fit this clip, or Fixed world scale",
            default="Fit this clip",
            effect="Fit fills this clip to the cell. Fixed uses your scale and origin on every clip.",
            gotcha="Fit maximizes per clip. Related walk/idle/attack sheets need Fixed world scale and the same origin.",
        )
        + _ctl(
            "Fit multiplier",
            "Extra margin beyond the automatic cell fill. Visible in Fit mode.",
            options="0.5× to 4×",
            default="1.0×",
            effect="1.0 fills the cell. Raise for more breathing room; the model looks smaller.",
            gotcha="Hidden in Fixed mode. Viewer zoom does not change this.",
        )
        + _ctl(
            "Fit basis",
            "Which character extent Fit mode uses for the orthographic scale.",
            options="Height, Width, Fit whole character",
            default="Fit whole character",
            effect="Fit whole uses the larger of height and width so sides are not cropped. Height may crop wide poses. Width may crop tall ones.",
            gotcha="Visible only in Fit mode. Fixed mode ignores this.",
        )
        + _ctl(
            "Fixed world scale",
            "World-unit orthographic scale. Visible in Fixed mode.",
            options="Positive world units",
            default="2.0",
            effect="Identical size across clips that share this value.",
            gotcha="Hidden in Fit mode. Larger makes the model smaller.",
        )
        + _ctl(
            "World origin X / Y / Z",
            "World-unit look-at point used only in Fixed mode.",
            options="Any finite world coordinates",
            default="0, 0, 0",
            effect="The camera aims here on every clip.",
            gotcha="Do not use per-clip bounds XY in Fixed mode. Set an explicit origin (often the root at 0,0,0).",
        )
        + _ctl(
            "Anchor",
            "Vertical aim in Fit mode: bounds centre or feet / lowest point.",
            options="Bounds centre, Feet / lowest point",
            default="Bounds centre",
            effect="Shifts the crop up or down in Fit mode.",
            gotcha="Hidden in Fixed mode. Fixed uses the world origin instead.",
        )
        + _ctl(
            "Offset X · px / Offset Y · px",
            "Nudge the finished cell after framing.",
            options="Signed integers, pixels",
            default="0, 0",
            effect="+X right, +Y down in the cell.",
            gotcha="Finished-cell pixels, not world units. Viewer pan is not this.",
        )
        + _ctl(
            "Orbit distance · camera and light",
            "Places the camera and the key light.",
            options="0.5 to 10",
            default="2.52",
            effect="Moves both the camera and the light farther or closer.",
            gotcha="Orbit distance is not zoom. Use Framing or Fixed world scale to change how large the character is.",
        )
        + _ctl(
            "Light energy",
            "Strength of the key light.",
            options="0 to 3000",
            default="1000",
            effect="Brighter or dimmer direct light.",
            gotcha="0 is unlit except for ambient. Updates the preview after a pause.",
        )
        + _ctl(
            "Softness",
            "Shadow soft size on the key light.",
            options="0 to 2",
            default="0.1",
            effect="Softer or harder shadows.",
            gotcha="Does not change silhouette size.",
        )
        + _ctl(
            "Light colour",
            "Key light colour as #RGB or #RRGGBB.",
            options="#hex",
            default="#FFFFFF",
            effect="Tints the key light.",
            gotcha="Invalid hex is rejected on the field.",
        )
        + _ctl(
            "Ambient strength",
            "Fill light in the shadows.",
            options="0 to 8",
            default="1.0",
            effect="Lifts or crushes the dark side.",
            gotcha="Travels with appearance presets.",
        )
        + _ctl(
            "Ambient colour",
            "Fill colour as #hex.",
            options="#hex",
            default="#FFFFFF",
            effect="Tints the ambient.",
            gotcha="Invalid hex is rejected on the field.",
        )
        + _ctl(
            "View transform",
            "Blender colour management transform.",
            options="Standard, AgX, Filmic",
            default="Standard",
            effect="How render colours are mapped to the sprite.",
            gotcha="Presets may change this. Compare related clips with the same transform.",
        )
        + _ctl(
            "Exposure",
            "Colour-management exposure.",
            options="-3 to 3",
            default="0",
            effect="Overall brightness after lighting.",
            gotcha="Not the same as Light energy.",
        )
        + _ctl(
            "Gamma",
            "Colour-management gamma.",
            options="0.2 to 3",
            default="1.0",
            effect="Contrast of the mapped colours.",
            gotcha="Very low values crush midtones.",
        )
        + _ctl(
            "Specular IOR",
            "Specular reflection amount on the material.",
            options="0 to 1",
            default="0.5",
            effect="Shinier or flatter highlights.",
            gotcha="Does not change metalness. Updates the preview after a pause.",
        ),
        ("orbit distance", "fit multiplier", "specular ior", "fixed world scale",
         "output offset", "elevation"),
    ),
    Article(
        "ref-layout", "Layout and timing controls", "reference",
        [
            ("p", "03 / Studio → Layout & timing: sheet order, source facing, sampling, and first-frame replacement."),
        ]
        + _ctl(
            "First direction",
            "Which heading is the first cell of the sheet.",
            options="Names from the current direction set (S, N, E, W, and diagonals when present)",
            default="S",
            effect="Rotates the cell sequence. Does not rotate the mesh.",
            gotcha="Does not auto-preview. Render sheet to bake order.",
        )
        + _ctl(
            "Rotation",
            "Walk the compass clockwise or counter-clockwise from the first direction.",
            options="Clockwise, Counter-clockwise",
            default="Clockwise",
            effect="CW from N is N, NE, E, SE, S, SW, W, NW.",
            gotcha="Sheet order only. Source facing is separate.",
        )
        + _ctl(
            "Sheet layout",
            "Whether directions run as rows or as columns.",
            options="Directions as rows, Directions as columns",
            default="Directions as rows",
            effect="Rows: directions down, frames across. Columns: the transpose.",
            gotcha="Does not auto-preview. Match this mapping in your engine.",
        )
        + _ctl(
            "Resolved order",
            "The actual output order for the current first direction, rotation, and count.",
            options="Read-only",
            default="Updates as you edit order",
            effect="Copy this list into your game's direction table.",
            gotcha="Do not assume an importer uses the same convention.",
        )
        + _ctl(
            "Left 90° / Right 90°",
            "Quarter-turn the imported source and its animation around world Z.",
            options="±90° each click",
            default="Yaw 0",
            effect="Corrects a model that was authored facing the wrong axis.",
            gotcha="Independent of preview facing and sheet order. Up-axis correction is not provided.",
        )
        + _ctl(
            "Yaw · degrees",
            "Exact source yaw around world Z.",
            options="Any finite degrees",
            default="0",
            effect="Same as the quarter-turn buttons, with a precise value.",
            gotcha="Does not change cell sequence. Animated roots use a non-animated parent so yaw sticks.",
        )
        + _ctl(
            "Playback / sampling",
            "How the source range is sampled and how preview play behaves.",
            options="Loop (exclude end pose), One-shot (include end pose)",
            default="Loop",
            effect="Loop wraps and skips the final endpoint. One-shot includes both ends when there are two or more frames.",
            gotcha="Phase is ignored on one-shot. Preview play stops on the last one-shot frame.",
        )
        + _ctl(
            "Source start / Source end",
            "Trim the detected action range. Blank means use the detected value.",
            options="Integer frames, or empty",
            default="Empty (detected)",
            effect="Shortens the sampled span.",
            gotcha="Inverted ranges are rejected. Inspect still shows the full detected range.",
        )
        + _ctl(
            "First pose / phase",
            "Shifts which pose is frame 0. Loop only.",
            options="0 to 1",
            default="0",
            effect="Phase wraps inside the loop range.",
            gotcha="Hidden (and ignored) for one-shot clips.",
        )
        + _ctl(
            "Reverse playback",
            "Sample the range backwards.",
            options="On or off",
            default="Off",
            effect="Loop reverse wraps. One-shot reverse does not wrap. A single one-shot frame is the end pose if reverse is on.",
            gotcha="This is sampling order, not an in-engine playback flag. Metadata records loop_mode separately.",
        )
        + _ctl(
            "Remove root motion (re-center each frame)",
            "Keep a travelling clip framed at character size instead of the whole-clip travel box.",
            options="On or off",
            default="Off",
            effect="Fit uses the largest single-frame extent. The camera recenters on each frame (XY from that frame, Z from the shared target).",
            gotcha="Leave off for in-place cycles. When an idle replacement is set, idle uses the walk clip's fitted size.",
        )
        + _ctl(
            "Choose replacement model",
            "Optional second model that replaces cell 01 in each direction.",
            options="Same formats as the main source; clear with the close icon",
            default="No replacement model",
            effect="Keeps the total frame count: 11 requested frames become 1 replacement + 10 samples.",
            gotcha="No blending. Scale, origin, and orientation must match. Not an idle-sheet generator. CLI: --idle.",
        ),
        ("phase", "source start", "source facing", "first direction", "reverse playback",
         "first-frame replacement", "root motion"),
    ),
    Article(
        "ref-export", "Export dialog controls", "reference",
        [
            ("p", "Export sprite sheet dialog. Rendering never writes into the source folder. Re-export reuses the composed sheet."),
            ("note", _t(
                "Auto-normalize: BMP forces at least 24-bit. A non-32-bit job or BMP with a ",
                "transparent background switches to magic pink. Switching to 32-bit PNG resets ",
                "magic pink to transparent. Magic pink forces hard alpha.",
            )),
        ]
        + _ctl(
            "Output preset",
            "Named starting points for format, depth, background, and bleed.",
            options="PNG RGBA (modern), PNG engine atlas (dilated), TGA magic-pink (legacy 2D), BMP 8-bit indexed (DOS), or Custom",
            default="PNG RGBA (modern)",
            effect="Fills the other export fields. You can still edit them.",
            gotcha="Editing a field after a preset shows Custom output.",
        )
        + _ctl(
            "Format",
            "File type written by Export.",
            options="png, tga, bmp",
            default="png",
            effect="Sets the destination extension and legal depths.",
            gotcha="The CLI supports png and tga only. BMP is GUI-only.",
        )
        + _ctl(
            "Colour depth",
            "Bits per pixel of the written file.",
            options="32, 24, 8 (the legal set depends on format)",
            default="32",
            effect="32 keeps alpha. 24 and 8 need a solid or key background.",
            gotcha="BMP cannot be 32-bit. Indexed (8) enables palette and dithering.",
        )
        + _ctl(
            "Background",
            "What sits behind transparent pixels.",
            options="Transparent (alpha), Magic pink (colour key), Solid colour",
            default="Transparent",
            effect="Composites the sheet before write.",
            gotcha="Transparent is hidden when depth is not 32 or format is BMP. Those cases switch to magic pink.",
        )
        + _ctl(
            "Background colour",
            "Fill colour when Background is Solid.",
            options="#hex",
            default="#000000",
            effect="Paints opaque pixels behind the character.",
            gotcha="Hidden unless Background is Solid.",
        )
        + _ctl(
            "Alpha treatment",
            "How semi-transparent edges are kept or cut.",
            options="Soft (anti-aliased), Hard (1-bit cutout)",
            default="Soft",
            effect="Hard uses the alpha cutoff. Magic pink forces hard.",
            gotcha="Soft edges are anti-aliasing, not dithering.",
        )
        + _ctl(
            "Alpha cutoff",
            "Threshold for hard alpha.",
            options="1 to 255",
            default="128",
            effect="Pixels below the cutoff become fully transparent.",
            gotcha="Disabled unless Alpha treatment is Hard.",
        )
        + _ctl(
            "Edge bleed",
            "Copies RGB into neighbouring transparent pixels.",
            options="Off, 1, 2, 4, 8 pixels",
            default="Off (PNG RGBA); engine-atlas preset uses a dilated value",
            effect="Reduces dark fringes when the engine filters or keys the sheet.",
            gotcha="Does not enlarge the silhouette or add cell padding. It is not dithering.",
        )
        + _ctl(
            "Dithering",
            "How 8-bit indexed colour is reduced.",
            options="None, Ordered (Bayer), Floyd-Steinberg",
            default="None",
            effect="Spreads quantization error for indexed output.",
            gotcha="Disabled unless colour depth is 8-bit.",
        )
        + _ctl(
            "Palette",
            "Where the 8-bit palette comes from.",
            options="Adaptive (from this sheet), Master palette (share a scene palette), Custom fixed colours",
            default="Adaptive",
            effect="Chooses the index table.",
            gotcha="Master palette and Custom fixed colours keep exact index order. Adaptive may put a missing magic-pink key at index 0.",
        )
        + _ctl(
            "Maximum colours",
            "Cap for an adaptive palette.",
            options="2 to 256",
            default="256",
            effect="Fewer colours, smaller unique set.",
            gotcha="Visible only for adaptive 8-bit. Adaptive still prepends a missing key at index 0 and may truncate to 256.",
        )
        + _ctl(
            "Load palette (BMP / PNG / PAL / GPL / HEX) and Palette path",
            "Supply a master palette for indexed output.",
            options="Indexed .bmp/.png/.gif, or .pal/.gpl/.hex/.txt; path field",
            default="Empty",
            effect="Uses that palette in exact index order. Transparent pixels map to the magic-pink index.",
            gotcha="Visible only when Palette is Master palette. A truecolour image is rejected. Missing magic pink is an error.",
        )
        + _ctl(
            "Custom fixed colours",
            "Build a typed palette as an ordered list of colours.",
            options="Swatch list with index badges; #RRGGBB add field (spaces or commas); RGB sliders; Add magic pink; drag to reorder; Clear all",
            default="Empty",
            effect="The first colour is index 0. Transparent pixels map to the magic-pink index when that key is present.",
            gotcha="Visible only when Palette is Custom fixed colours. A missing key colour is an error; the list is not reordered or prepended.",
        )
        + _ctl(
            "Write JSON sidecar",
            "Write animation metadata next to the image.",
            options="On or off",
            default="Off",
            effect="Sidecar includes layout, sample times, playback_fps, source_fps, loop mode, and pivot.",
            gotcha="The image itself does not encode those rules. CLI: --metadata.",
        )
        + _ctl(
            "Export sprite sheet (dialog)",
            "Writes the processed sheet to a destination you pick.",
            options="Desktop save picker, or browser download",
            default="Suggested name is source_stem_sheet.ext",
            effect="Re-export updates processing without starting Blender again.",
            gotcha="Never writes into the source folder by itself. You choose the destination.",
        ),
        ("output preset", "edge bleed", "magic pink", "write json sidecar",
         "dithering", "alpha cutoff"),
    ),
    Article(
        "ref-dialogs", "Other dialogs", "reference",
        [
            ("p", "Path dialogs used in the browser preview, plus this Help window."),
        ]
        + _ctl(
            "Choose model dialog (web)",
            "Absolute path field when FRAMEMILL_WEB=1.",
            options="Existing .fbx / .glb / .gltf / .obj path",
            default="Empty",
            effect="Loads that file as the main source or as a replacement model.",
            gotcha="The desktop app uses a native picker instead.",
        )
        + _ctl(
            "Recipe dialog (web)",
            "Absolute path for Save recipe or Load recipe.",
            options="A .json path you can write or read",
            default="Empty",
            effect="Same recipe format as the desktop pickers.",
            gotcha="Load still rejects a missing source.",
        )
        + _ctl(
            "Help dialog",
            "Searchable articles: this window.",
            options="Search field, category list, article pane, Back to workspace",
            default="Opens on Getting started",
            effect="Search shows ranked results (title + category) instead of the tree.",
            gotcha="Hidden on the top bar below 1000 px width. Degrades to article-only below 900 px.",
        ),
        ("recipe dialog", "help dialog", "absolute path"),
    ),
]


WORKFLOW_KEYWORDS: tuple[str, ...] = (
    "mixamo", "tripo", "with skin", "in place", "t-pose",
)


CONTROL_KEYWORDS: tuple[str, ...] = (
    "orbit distance", "edge bleed", "magic pink", "fit multiplier", "specular ior",
    "phase", "anchor", "output preset", "write json sidecar", "recenter", "base size",
    "locate blender", "choose a model", "elevation", "source start", "first direction",
    "alpha cutoff", "viewer fps", "reset to defaults", "master palette",
    "remove root motion", "custom colours", "fixed colours",
    "master palette file", "create palette", "fit basis",
)


def _block_text(block: Block) -> str:
    kind = block[0]
    if kind in {"h", "p", "note", "kbd"}:
        return str(block[1])
    if kind == "li":
        return " ".join(str(item) for item in block[1])
    if kind == "link":
        return f"{block[1]} {block[2]}"
    return ""


def article_text(article: Article) -> str:
    return " ".join(_block_text(block) for block in article.body)


def article_by_id(article_id: str) -> Article:
    for article in ARTICLES:
        if article.id == article_id:
            return article
    raise KeyError(article_id)


def articles_in(category_id: str) -> list[Article]:
    return [article for article in ARTICLES if article.category == category_id]


def search(query: str) -> list[Article]:
    tokens = [part for part in query.casefold().split() if part]
    if not tokens:
        return []
    ranked: list[tuple[int, Article]] = []
    for article in ARTICLES:
        title = article.title.casefold()
        keywords = " ".join(article.keywords).casefold()
        body = article_text(article).casefold()
        haystack = f"{title} {keywords} {body}"
        if not all(token in haystack for token in tokens):
            continue
        score = 0
        phrase = " ".join(tokens)
        if phrase in title:
            score += 400
        elif all(token in title for token in tokens):
            score += 300
        elif any(token in title for token in tokens):
            score += 120
        if phrase in keywords:
            score += 200
        elif all(token in keywords for token in tokens):
            score += 80
        if phrase in body:
            score += 20
        elif all(token in body for token in tokens):
            score += 10
        ranked.append((score, article))
    ranked.sort(key=lambda item: (-item[0], item[1].title))
    return [article for _, article in ranked]


def check_invariants() -> None:
    category_ids = [category.id for category in CATEGORIES]
    if len(category_ids) != len(set(category_ids)):
        raise ValueError("Category ids must be unique.")
    known = set(category_ids)
    article_ids = [article.id for article in ARTICLES]
    if len(article_ids) != len(set(article_ids)):
        raise ValueError("Article ids must be unique.")
    for article in ARTICLES:
        if article.category not in known:
            raise ValueError(f"Article {article.id!r} refers to unknown category {article.category!r}.")
        if not article.id or not article.title.strip() or not article.body:
            raise ValueError(f"Article {article.id!r} is missing id, title or body.")
    for category in CATEGORIES:
        if not articles_in(category.id):
            raise ValueError(f"Category {category.id!r} has no articles.")
