# Roadmap: character cartoons (phase 2 of the project)

This is the plan for moving from prop-only explainers to cartoon episodes, where characters walk, talk and act in scenes, with as little manual work as possible.
It's a plan, not code yet. The explainer pipeline comes first.

## The core idea: design for automation

Fully automated animation fails when it tries to imitate a film studio. It works when **every part is designed so a machine can do it reliably**:

1. **Characters built for automation.** Stylised, with a standard skeleton and a simple face system, so every motion and expression works on every character.
2. **Acting from a library, not hand keyframes.** A vocabulary of reusable motions and procedural "alive" layers like blinking and looking around.
3. **A director layer.** Code that turns a screenplay into staging and camera shots using film rules, with nobody placing cameras by hand.
4. **Stories written for the puppets.** The story writer knows what the system can and can't do. It writes dialogue-driven scenes and avoids things like fights or hugs that would look bad.
5. **Automatic quality checks.** Code and Claude check previews before a human ever looks.

Human touchpoints end up as: approve the story, approve each new character once, and watch the final video.

---

## 1. Story layer: the screenplay

Claude writes a structured screenplay. A **series bible** (`series/<name>/bible.md`) holds the world, the cast, the tone and the running jokes, so episodes stay consistent.

```json
{
  "scene": "kitchen_morning",
  "set": "desi_house_kitchen",
  "time_of_day": "morning",
  "cast": ["ammi", "ali"],
  "beats": [
    {"do": "ali enters from door, walks to table, sits"},
    {"say": "ammi", "line": "Exam results came today, na?", "emotion": "suspicious"},
    {"say": "ali", "line": "Results? What results?", "emotion": "nervous", "act": "looks_away"},
    {"do": "ammi crosses arms"},
    {"say": "ammi", "line": "Ali.", "emotion": "angry"},
    {"do": "ali gulps", "camera": "close_up"}
  ]
}
```

The writer is constrained to a list of **allowed actions**: those the motion library supports, plus each set's marks and props. Anything outside the list is rejected at validation, the same way unknown anchors are rejected today.

## 2. Director layer: from screenplay to shots (new)

The director turns beats into the existing episode format (shots, camera, events, overlays) automatically:

- **Blocking:** each set defines named **marks**, such as `door`, `table_seat_1`, `stove` and `sofa_left`. Characters are placed on marks, and `walk_to` moves them along simple waypoint paths between marks.
- **Coverage, using standard film grammar:**
  - an establishing wide shot at the start of each scene
  - a two-shot for exchanges
  - over-the-shoulder or a close-up on whoever is speaking
  - a reaction shot after punchlines
  - the 180° rule, so characters stay on consistent sides of the frame
  - cutting on dialogue boundaries
- **Timing** comes from the dialogue audio, as the timeline already does with narration, plus pauses for reactions.
- Claude can override choices ("hold on Ali's face for 2 s"), but the defaults should look fine without any input.

## 3. Characters

### 3a. Character card (one per character)
`characters/<id>/card.json` holds the name, height, colour palette, voice (backend + voice ID), personality notes for the writer, walk style, idle style, and a default expression.

### 3b. How characters get made (two tiers)

| Tier | How | Manual effort | Use for |
|---|---|---|---|
| **A: procedural toy characters** | Built entirely by code: rounded body, head, simple limbs, auto-generated skeleton. Colours and proportions come from the card | **None** | first mascot, background extras, testing the whole system |
| **B: AI-generated characters** | concept image (AI) → image-to-3D (Meshy, Tripo, TRELLIS or Hunyuan3D) → auto-rig (Meshy, Mixamo or AccuRig) → **retarget to the project's standard skeleton** → attach the face system | approve the design, then occasional cleanup | main cast |

**Standard skeleton:** every character is retargeted to one bone layout, the Mixamo naming. Because of that, any motion clip works on any character, and new characters cost almost nothing to animate.

### 3c. Face system: 2D faces on 3D heads (recommended)
Eyes, brows and mouths are **image textures swapped on the face**, like many stylised cartoons do, rather than a sculpted face rig.

- **Lip-sync:** Rhubarb Lip Sync (free) turns each dialogue clip into mouth shapes (about 9 visemes), and the pipeline swaps the mouth textures to match. This is reliable, cartoony and cheap to render.
- **Expressions:** sets of eye, brow and mouth textures for happy, sad, angry, surprised, nervous, thinking and so on. They're chosen automatically from each line's `emotion`.
- **Blinks:** an automatic texture swap at random natural intervals.
- Face textures can be generated with AI and kept consistent per character.
- **Why this beats a 3D face rig:** AI-generated meshes rarely come with usable face shapes, and texture faces never break.

A 3D shape-key face is possible later for hero characters, but it's optional.

## 4. Acting system

### 4a. Motion library (`assets/motions/`, standard skeleton)
| Category | Clips |
|---|---|
| Locomotion | idle (several variants), walk, run, turn left/right, start, stop |
| Talking | talk idle with small hand movements (several), emphatic gesture, explain gesture |
| Gestures | point, wave, shrug, nod, head shake, thumbs up, clap, facepalm, think (hand on chin), arms crossed |
| Emotion | happy bounce, sad slump, angry stomp, surprised jump, nervous fidget, laugh |
| Poses | sit down, sitting idle, stand up, lean, phone in hand |

Sources:
- **Mixamo**, a free library. Check its current licence terms.
- **AI video motion capture**: act a move on your phone and convert it. Rokoko Vision, Move AI and DeepMotion do this, but they're untested here.
- **Text-to-motion AI models**, for custom clips.

Every clip gets tagged with its duration, whether it loops, and its stride length (for walks).

### 4b. Screenplay actions → Blender
| Action | Implementation |
|---|---|
| `walk_to(mark)` | follow a waypoint path, play an in-place walk clip, move the root at a speed matched to the clip's stride (no foot sliding), turn to face the direction of travel |
| `look_at(target)` | head/neck bone constraint with smooth blend in and out, eyes follow |
| `gesture(name)` / `emote(emotion)` | layer the clip on the timeline (Blender NLA) with blend in/out over the base idle |
| `sit(mark)` / `stand` | transition clip, then sitting idle |
| `say(line, emotion)` | audio + lip-sync + expression + automatic talking gestures |
| `pick_up(prop)` / `hold(prop)` | attach the prop to the hand bone (a Child Of constraint) at the right frame |

### 4c. Automatic "alive" layers (this is what avoids manual animation)
- **Idle variation:** swap and blend idle clips so nobody stands frozen.
- **Breathing:** subtle procedural chest/shoulder motion.
- **Blinks and eye darts:** randomised and natural.
- **Beat gestures while talking:** small gestures picked from the line's emotion and punctuation, such as emphasis on "!" or a shrug on "?".
- **Listener behaviour:** characters who aren't speaking look at the speaker, nod occasionally, and react to punchlines.
- **Settle:** characters ease into poses, without snapping.

## 5. Sets and backgrounds

A **set library** (`blender/sets/`). Each set is a Python module, like `street.py` today, that provides:
- geometry (code primitives plus AI-generated or library props)
- **marks** (named standing/sitting spots with facing directions)
- **camera presets** (wide, and angles on each mark)
- **lighting presets** (day, evening, night, mood)
- optional **painted backdrop planes**: AI-generated 2D background images for distant scenery like skylines, mountains or windows. They're cheap and look great in this style.

A series needs only a handful of sets (for example a house with kitchen, lounge and rooftop, plus a street, school or office, and a chai stall). After they're built, new episodes cost nothing in set work.

## 6. Voice, music, sound
- Each character has a voice (an ElevenLabs designed voice, or Kokoro voices), and lines carry emotion tags.
- Before choosing a backend, check support for the target language (English, Urdu, Spanish).
- Room tone and ambience per set, music cues per scene (licensed or AI music), and sound effects from the existing sfx system plus a library.

## 7. Automatic quality checks (to minimise human review)
Code checks after the preview:
- Each speaking character is in frame and not blocked by objects (screen tracking already exists).
- Characters don't intersect each other or furniture (bounding-box overlap checks).
- Feet are on the ground and no character is floating.
- Every line has lip-sync data, and the audio and shot timing agree.

Claude then reviews the contact sheet per scene: framing, readability and whether the staging fits the moment. It auto-fixes for up to N rounds, then flags anything left for a human.

## 8. What stays hard (and how we handle it)
| Hard thing | Mitigation |
|---|---|
| Subtle, nuanced acting | stylised characters plus expressive faces and comedy timing. The writer avoids moments that need subtle body acting |
| Physical contact (hugs, fights, handing objects) | the writer avoids it, or cuts away / uses off-screen sound. Simple prop handoffs via bone attachment come later |
| Crowds | a few background extras with idle loops, mostly out of focus |
| Character consistency of AI-made models | lock each character as a saved asset once approved, and never regenerate per episode |
| Render time for long episodes | Eevee, simple materials, render scene by scene with resume. A 2-3 min episode is realistic on the RTX 3060 |

---

## Phases

| Phase | Build | Proof that it works |
|---|---|---|
| **0 (now)** | explainer pipeline, first episodes published | traffic camera and smart meter Shorts |
| **1: character core** | procedural toy character, standard skeleton, motion clip loader, `walk_to` / `look_at` / `gesture` / `say`, 2D face + Rhubarb lip-sync, alive layers, multi-voice | a mascot walks in and presents an explainer |
| **2: director** | screenplay format, marks, automatic coverage + timing, 2 sets | a 1-minute, two-character dialogue scene from a screenplay, no manual staging |
| **3: character factory** | AI concept → 3D → rig → retarget → face textures, character cards | a cast of 3-5 characters |
| **4: story engine** | series bible, episode writer constrained to system capabilities, automatic QA loop, music and ambience | a 2-3 min episode from one prompt, with only the two approval stops |
| **5: polish** | video motion capture for custom moves, optional AI video for a few cinematic shots, long-form episodes | quality upgrades |

## Decisions to make before phase 1
1. **First series concept:** desi family comedy, office satire, or a mascot host for the explainers.
2. **Language:** English, Urdu or Spanish. This affects which voice backend to use.
3. **Character look:** procedural toy style first (recommended for testing) and AI-generated for the main cast.
4. **Face system:** 2D texture faces (recommended) or 3D shape keys.
