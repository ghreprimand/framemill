# Workflow: from artwork to sprite sheet

framemill renders the motion already present in a rigged 3D model. It does not create
animations or rig characters itself. This page covers the whole path, including the tools
before framemill and the exact export settings that matter.

## The pipeline at a glance

```
concept / T-pose art  ->  3D model (Tripo)  ->  rig + animate (Mixamo)  ->  framemill  ->  your engine
```

You need a **rigged, animated 3D model with its mesh**. If you already have one, skip to
[step 3](#3-load-and-render-in-framemill). If you are starting from a drawing or an idea,
steps 1 and 2 get you there.

## 1. Make a 3D model (Tripo)

[Tripo](https://www.tripo3d.ai/) turns a text prompt or an image into a textured 3D model.

- Aim for a character in a **T-pose or A-pose** (arms out, standing straight, facing
  forward). Auto-riggers need a clean neutral pose.
- Keep it a single connected humanoid mesh where possible.
- Export as **FBX** or **GLB**. Both carry the mesh and textures, which the next steps need.

You can substitute any other source here: Blender, a purchased model, a scan. The only
requirement is a humanoid mesh you can rig.

## 2. Rig and animate (Mixamo)

[Mixamo](https://www.mixamo.com) (free with an Adobe account) auto-rigs a humanoid and
applies ready-made animations.

**Upload your model**

- Mixamo accepts **FBX**, **OBJ**, or a **ZIP** (use ZIP for OBJ plus its `.mtl` and
  textures). An FBX or GLB with embedded textures is easiest.
- Place the auto-rig markers (chin, wrists, elbows, knees, groin) on the T/A-pose.

**Pick an animation**

- Choose a motion, for example "Walking", "Idle", or an attack.
- For anything the game moves across the ground, turn **In Place** on so the cycle keeps
  the character centered in every frame. If a clip already has its travel baked in, you can
  instead enable **Remove root motion** in framemill (Layout & timing) to re-center each
  frame at render time.

**Download with the settings framemill needs**

In the Mixamo download dialog:

- **Format:** `FBX Binary (.fbx)`.
- **Skin:** `With Skin`. This is the important one. "Without Skin" exports only the
  skeleton, and framemill has no mesh to render.
- **Frames per Second:** 30 or 60 is fine. framemill re-samples to the frame count you
  choose, so this mainly sets how smooth the source is.
- **Keyframe Reduction:** `None`, so the motion stays faithful to what you previewed.

For a static, non-animated sheet, download the character with the **T-Pose** animation,
still `With Skin`, then choose 1 frame per direction in framemill.

Download each animation you want as its own file (`walk.fbx`, `idle.fbx`, `attack.fbx`).

## 3. Load and render in framemill

1. Load the downloaded FBX as the **main source**. framemill accepts **FBX, glTF/GLB, OBJ**.
2. framemill reads the first action's range and shows the detected action, start, end,
   span, and source FPS. Trim with **Source start / Source end** if needed.
3. Set **Directions** (1 / 4 / 8 / 16) and **Frames** per direction.
4. Choose **Loop** for cycles (walk, idle) or **One-shot** for attacks and deaths.
5. If the character faces the wrong way, use **Layout & timing -> Source facing** (South is
   the front camera). See [Orientation](orientation.md).
6. **Preview**, then **Render sheet**, then **Export sprite sheet**.

## 4. Keep related sheets aligned

Export each animation separately (`hero_walk.png`, `hero_idle.png`, ...). So they line up in
your engine, use the same framing for all of them:

- Switch **Camera -> Framing mode** to **Fixed world scale**.
- Set the same world-unit origin (usually the character root at 0, 0, 0) and the same output
  offsets for every sheet.

Fit mode sizes each clip to its own bounds and will shift between clips whose poses differ.
See [Settings reference](settings-reference.md) for every control.

## File formats, end to end

| Stage | In | Out |
| --- | --- | --- |
| Tripo | text or image | FBX / GLB (textured) |
| Mixamo | FBX / OBJ / ZIP (T-pose) | FBX Binary, With Skin, In Place, no keyframe reduction |
| framemill | FBX / glTF / GLB / OBJ | PNG / TGA / BMP sprite sheet (+ optional JSON sidecar) |

## How frames are sampled

- framemill takes the range of the **first active action found on an imported object**. If
  none is found, it uses Blender's scene range. There is no NLA or multi-clip selector and no
  automatic stride detection. Export one intended animation per file.
- **Loop** keeps the walk-cycle formula: with phase zero and forward playback, sample `i` is
  `start + (i / frame_count) * (end - start)`. Fractional frames are evaluated. The final
  endpoint is excluded so a loop does not repeat its first pose. Phase wraps; reverse wraps.
- **One-shot** includes both endpoints when there are two or more frames, ignores phase, and
  reverses without wrapping. A single one-shot frame is the start pose (or the end pose if
  reverse is on). Preview playback stops on the last frame instead of looping.
- Odd counts such as 11 are valid; they change temporal sampling density, not the duration or
  content of the source motion.
- `framemill inspect model.fbx` reports the range, action name, and source FPS before overrides.
- The preview FPS control changes only viewer playback. Frame count changes sampling density.
  Optional metadata records both `playback_fps` and `source_fps`.

## First-frame replacement (advanced)

**For a normal idle animation, load the idle FBX as the main source and export its own
sheet.** The second-model control is not an idle-sheet generator.

Under **Layout & timing -> First-frame replacement (advanced)**, an optional second model
replaces the first output cell in each direction. CLI equivalent: `--idle`. The total count
stays unchanged: **11 requested frames = 1 replacement + 10 source animation samples**, not
11 walking frames plus idle. The remaining source samples keep their original sample times;
they are not redistributed into a complete 10-frame cycle.

The replacement uses the second model's animation end pose by default, framed with the main
model's bounds. It must have matching scale, origin, orientation, and appearance. framemill
does not blend the poses or create start/stop transitions. Preview playback includes the
replacement; even skipping it in-engine leaves an uneven sampling gap at the loop boundary.

Keep this option unset unless your target engine explicitly requires that layout and you
accept the timing tradeoff.
