# Workflow and sampling

framemill renders the motion already present in your model. It does not create animations,
identify footsteps, or generate transitions. Walking is one use case; idle breathing,
running, talking, and other imported animations use the same pipeline.

## From model to sheet

1. Create a textured character in Tripo or another modelling tool.
2. Rig it and apply an animation in Mixamo, Blender, or another animation tool. For Mixamo,
   upload a compatible model, apply the chosen motion, and download an animated FBX **with
   skin** so the file contains the character mesh too. See
   [Adobe's rigging and animation guide](https://helpx.adobe.com/creative-cloud/help/mixamo-rigging-animation.html).
3. Load that animated file as framemill's **main source**. Set the sprite count and
   directions. Choose **Loop** (walk cycles) or **One-shot** (attacks, deaths). Trim the
   detected source start/end if needed. Save a recipe to reopen the same setup later.
4. Export each animation separately: load `walk.fbx` and export `hero_walk.png`, then load
   `idle.fbx` as the main source and export `hero_idle.png`. Lock **Fixed world scale** and
   the same world-unit origin (typically the character's root at 0,0,0) plus output offsets
   so related sheets match. Fit mode sizes each clip from its own bounds and will shift if
   poses differ.
5. Configure your game to select the idle or walk animation, its frame sequence, direction
   mapping, playback speed, and looping. Optionally enable **Write JSON sidecar** on export
   for layout, sample times, playback vs source FPS, loop mode, and pivot. The image itself
   does not encode those rules.

A static model works too: choose **1 frame** per direction. Requesting more frames from a
static source repeats the same pose; it does not animate the model.

## How frames are sampled

- The renderer takes the range of the **first active action found on an imported object**.
  If none is found, it uses Blender's scene range. The workspace shows the detected action,
  start, end, span, and source FPS. Start/end fields trim that range. There is no full NLA
  or multi-clip selector and no automatic stride detection. Export one intended animation
  per source file.
- **Loop** keeps the walk-cycle formula: with phase zero and forward playback, sample `i`
  is `start + (i / frame_count) * (end - start)`. Fractional frames are evaluated. The final
  endpoint is excluded so a loop does not repeat its first pose. Phase wraps; reverse wraps.
- **One-shot** includes both endpoints when there are two or more frames, ignores phase, and
  reverses without wrapping. A single one-shot frame is the start pose (or the end pose if
  reverse is on). Preview playback stops on the last frame instead of looping.
- Odd counts such as 11 are valid; they change temporal sampling density, not the duration
  or content of the source motion.
- `framemill inspect model.fbx` reports the range, action name, and source FPS before overrides.
- The preview FPS control changes only viewer playback. Frame count changes sampling
  density. Optional metadata records both `playback_fps` and `source_fps`.

## First-frame replacement (advanced)

**For a normal idle animation, load the idle FBX as the main source and export its own
sheet.** The second-model control is not an idle-sheet generator.

Under **Layout & timing → First-frame replacement (advanced)**, an optional second model
replaces the first output cell in each direction. CLI equivalent: `--idle`. The total count
stays unchanged: **11 requested frames = 1 replacement + 10 source animation samples**, not
11 walking frames plus idle. The remaining source samples keep their original sample times;
they are not redistributed into a complete 10-frame cycle.

The replacement uses the second model's animation end pose by default, framed with the main
model's bounds. It must have matching scale, origin, orientation, and appearance. framemill
does not blend the poses or create start/stop transitions. Preview playback includes the
replacement; even skipping it in-engine leaves an uneven sampling gap at the loop boundary.

Keep this option unset unless your target engine explicitly requires that layout and you
accept the timing tradeoff. This compatibility option is not the recommended way to author
idle and walk animations.
