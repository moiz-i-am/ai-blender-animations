# Episode format (`episodes/<id>.json`)

One JSON file describes a whole Short. See `episodes/traffic_camera.json` for a full example and `episodes/_template.json` for a starting point. To scaffold a new one, run `py make_episode.py new <id> --scene <scene>`.

## Top level

| Key | Example | Meaning |
|-----|---------|---------|
| `id` | `"traffic_camera"` | output folder name, snake_case |
| `title` | `"..."` | working title (for you; the on-screen title is an overlay) |
| `scene` | `"traffic_camera"` | module in `blender/scenes/` |
| `fps`, `resolution` | `30`, `[1080, 1920]` | vertical Shorts format |
| `language` | `"en"` | used for Whisper caption timing |
| `fact_checked` | `false` | set `true` only after a human checks the narration |
| `sources` | `["https://..."]` | research references |
| `voice` | `{"backend": "kokoro", "kokoro_voice": "am_michael", "speed": 1.0}` | overrides config |
| `music` | `{"file": "assets/music/x.mp3", "volume": 0.15, "duck": 0.45}` | background track, ducked under the voice |
| `style` | `{"outline": 0.025, "sky_top": "#8FD0F0", ...}` | ink thickness plus any overlay style key (see `pipeline/overlays.py` `DEFAULT_STYLE`) |
| `lighting` | `{"sun_rotation": [48, 8, 35], "sun_strength": 2.5}` | optional |
| `captions` | `{"max_words": 4, "word_timing": true}` | optional |
| `shots` | `[...]` | in order |

## Shot

```json
{
  "id": "reveal_pole",
  "duration": 5.5,
  "narration": "Spoken line. Wrap *key* words in asterisks to highlight them in captions.",
  "caption": "optional on-screen text instead of the narration",
  "captions": true,
  "voice_delay": 0.15,
  "camera": { ... },
  "events": [ ... ],
  "overlays": [ ... ],
  "sfx": [ ... ]
}
```

`duration` is a minimum: a shot is stretched if its narration audio is longer. All `t`, `start` and `end` values are **seconds from the start of the shot**.

### camera

```json
{"from": POSE, "to": POSE, "ease": "ease_in_out"}
{"to": POSE}                        // continue from the previous shot's end pose
{"orbit": {"center": POINT, "radius": 26, "height": 15, "start": -100, "end": -72, "lens": 30}}
```

- `POSE = {"pos": POINT, "target": POINT, "lens": 35}`. Lens is in mm: 25-30 is wide, 50+ is tight.
- `POINT = [x, y, z]` or `"object_name"` or `{"anchor": "object_name", "offset": [x, y, z]}`.
- `ease`: `ease_in_out` (default), `linear`, `constant`.
- Orbit angles are in degrees around Z, where 0 points along +X and -90 means the camera sits at -Y looking towards +Y.

World axes: **+Z up**. In the street set, the road runs along **Y** and cars drive towards **+Y**.

### events (3D animation)

```json
{"t": 0.6, "action": "radar_on", "duration": 1.0, "params": {}}
```

Generic actions, available in every scene:

| action | params |
|--------|--------|
| `move` | `object`, `to` or `by`, optional `from`, `ease` (default `linear`) |
| `rotate` | `object`, `by` [deg x, y, z], `ease` |
| `show` | `object`, `frames` - pops in from scale 0 |
| `hide` | `object`, `frames` |
| `blink` | `material` (a glow material), `period`, `on`, `off` |
| `flash` | `light` and/or `material`, `energy`, `glow` |
| `glow` | `material`, `to`, optional `from` - fades the glow strength |

Scene modules add their own actions. For example, `traffic_camera` adds `car_drive`, `radar_on`, `radar_off`, `camera_flash` and `rec_blink`.

### overlays (2D, drawn after rendering)

| type | keys |
|------|------|
| `title` | `text`, `pos` [x, y 0-1], `box` (yellow box), `upper`, `size` |
| `label` | `text`, `anchor` (3D object - the label follows it), `offset` [dx, dy] |
| `counter` | `from`, `to`, `suffix`, `decimals`, `sub`, `alert_above`, `count_time`, `pos` |
| `card` | `title`, `items` [..], `stagger`, `pos` |
| `flash` | `duration`, `strength` - white screen flash |
| `image` | `file`, `width` (fraction of frame width), `pos` |

Every overlay also takes `start` and `end`. `end` defaults to the end of the shot.
Captions are generated from `narration` automatically.

### sfx

```json
{"t": 0.3, "name": "click", "gain": 1.0}
```

The built-in sounds are `click`/`shutter`, `whoosh`, `beep`, `pop`, `ding`, `tick` and `alarm`. To use a real sound instead, drop `assets/sfx/<name>.wav`.

## Writing good episodes
- Total length 30-60 s. Put the hook in the first 3 s and tease the next episode at the end.
- Use one idea per shot and keep narration to 20 words or fewer per shot.
- Keep labels to 1-2 words and show at most 3 labels at once.
- Use the same `id` names in the scene module, camera targets, labels and events.
