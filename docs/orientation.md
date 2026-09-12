# Direction and orientation

This is the part most likely to trip up a first import, so it has its own page.

## South is the front camera

New sources preview facing **South**, which is the front camera, regardless of the sheet's
start direction. South is a camera convention, not a property of your mesh.

Two things that do **not** rotate the mesh:

- **Sheet start direction** changes the cell order only.
- **Preview facing buttons** change the view only.

To actually rotate the imported source (and its animation), use **Source facing** in
**Layout & timing**: Left/Right 90 degrees, or a numeric yaw value. This is independent of
sheet order and preview facing.

## Direction order

Clockwise from North is:

```
N -> NE -> E -> SE -> S -> SW -> W -> NW
```

The **Layout & timing** panel shows the actual resolved order for your current
`start_direction`, `rotation`, and `layout_axis`. Match that order in your game; do not
assume your engine's importer uses the same convention.

- `rotation`: `cw` or `ccw`.
- `layout_axis`: `rows` (directions down, frames across) or `cols` (transposed).
- `angles`: 1, 4, 8, or 16 directions.

## Matching your engine

Export the [metadata sidecar](recipes-and-metadata.md) to record the exact per-direction
order, camera azimuths, and cell positions. That removes guesswork when you wire the sheet
into an engine that numbers directions differently.

## Common facing problems

- **Model faces sideways or backward:** use Source facing (quarter turns or yaw). Sheet
  order and preview facing will not fix it.
- **Character drifts, is small, or is clipped:** framemill does not remove root motion.
  Prepare an in-place animation when the game moves the actor. For matching walk, idle, and
  attack sheets, use Fixed world scale with the same world-unit origin and output offsets
  rather than Fit-this-clip. Increase the fit multiplier or fixed scale to make the sprite
  smaller.
- **Up-axis correction and free 3D orbit are not provided.** The viewer shows rendered
  sprites, not a freely orbitable 3D model.
