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
             "Install Blender, connect it, and render your first sheet."),
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
        ],
        ("tripo", "mixamo", "pipeline"),
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
                "Load an FBX, GLB, glTF or OBJ.",
                "Check the automatic South preview.",
                "Set directions and frame count.",
                "Render sheet, then Export sprite sheet.",
            ]),
        ],
        ("first render", "south preview"),
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
                "after you load a model. Start/end fields under Layout & timing trim that range.",
            )),
            ("kbd", "framemill inspect model.fbx"),
            ("p", "inspect reports the range, action name and source FPS used before overrides."),
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
                "Directions are 1, 4, 8 or 16. Frame count is 1–64. Cell width and height ",
                "are 1–1024 pixels. The readout shows finished sheet pixels, sprite count ",
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
                "Fit this clip sizes each clip from its own bounds. Fixed world scale ",
                "uses an explicit world-unit scale and origin (X/Y/Z) that stay identical ",
                "across clips; required for matching walk/idle/attack sheets.",
            )),
            ("p", "Fit multiplier and fixed world scale: larger values make the model smaller."),
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
        ("orbit distance", "fit multiplier", "fixed world scale", "output offset"),
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
        ],
        ("loop", "oneshot", "one-shot", "phase", "reverse", "playback_fps"),
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
                "Soft edges are anti-aliasing; dithering is for reduced-colour output.",
            )),
            ("h", "Edge bleed and palettes"),
            ("p", _t(
                "Edge bleed extends hidden RGB into transparent pixels without enlarging the ",
                "silhouette. It is not cell padding and not dithering.",
            )),
            ("p", _t(
                "Adaptive palettes can vary across sheets. Use a shared palette for related ",
                "animations. If the key colour is absent, Framemill prepends it and truncates to ",
                "256 entries, which can change palette indices. Verify the result against your ",
                "engine's exact index requirements.",
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
        ("magic pink", "dithering", "palette", "sidecar", "tga", "bmp"),
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
                "--frames: positive integer 1–64; zero or negative is an error.",
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
]


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
