# 3D Tactical Shooting Range

A procedural first-person shooting-range simulation developed as a computer
graphics course project. The application uses Python and the fixed-function
OpenGL pipeline to render an interactive 3D range with adjustable target
distances, a training bot, ray-based shooting, hit visualization, and a
heads-up display (HUD).

## Academic Information

| Item | Information |
|---|---|
| University | Bangladesh Army University of Science and Technology (BAUST) |
| Department | Computer Science and Engineering (CSE) |
| Course | CSE 4104 – Computer Graphics Sessional |
| Project type | Computer Graphics Course Project |

## Project Overview

The project models a tactical shooting range viewed from a first-person
perspective. The player starts behind a marked firing line on a wooden deck
and can aim, move within the permitted area, fire at a circular target or
training bot, select target distances, and inspect hit statistics.

The target can be positioned at **5 m, 10 m, 20 m, 30 m, or 50 m** from the
firing line. A fixed distance bar provides the same selection controls inside
the 3D scene. The environment is built entirely from procedural primitives;
the repository does not require external 3D models, textures, or image assets.

## Objectives

- Apply fundamental OpenGL rendering techniques to a complete interactive
  scene.
- Construct a 3D environment from reusable geometric primitives.
- Implement first-person camera movement and mouse-based aiming.
- Implement ray-based shooting and geometric intersection tests.
- Visualize target and body-part hits in both the world and the HUD.
- Demonstrate animation, lighting, depth testing, blending, and user input.

## Features

- First-person camera with mouse aiming and constrained WASD movement.
- Procedurally rendered shooting-range environment containing:
  - Wooden deck and firing-line marker.
  - Table, tarp, ammunition objects, and crate.
  - Distance bar with selectable range, clear, bot, walk, and strafe rows.
  - Circular target with cabinet, housing, and moving-distance behavior.
  - Fixed hit board that mirrors target hits.
  - Fence, sky gradient, and floating rocks.
- Five selectable target distances: 5 m, 10 m, 20 m, 30 m, and 50 m.
- 30-round magazine with reload support.
- Target hit classification:
  - Bullseye
  - Inner ring
  - Middle ring
  - Outer ring
  - Edge
- Optional six-part training bot:
  - Head
  - Torso
  - Left/right arm
  - Left/right leg
- Optional bot walking animation and side-to-side strafing.
- Red target-hit markers and blue bot-hit markers.
- HUD showing distance, bot state, animation state, ammunition, hit labels,
  hit totals, and a front-facing hit-location panel.
- Target housing, cabinet, and hit board act as shooting blockers.
- Distance-bar buttons can be activated by shooting them without consuming
  ammunition.

## Technologies and Tools

- **Python 3.9+**
- **PyOpenGL**
- **OpenGL**, **GLU**, and **GLUT/FreeGLUT**
- Immediate-mode OpenGL primitives and GLUT window/input callbacks
- Python standard-library `math` module

No `requirements.txt`, build system, texture pack, model pack, or other
external project asset is included in the repository.

## Computer Graphics Concepts and Techniques

### Procedural geometric modeling

The scene is generated at runtime from cubes, spheres, discs, rings, line
segments, and quads. Helper functions such as `drawBox`, `drawSphere`,
`drawDisc`, and `drawRing` are reused to assemble the environment, target,
bot, and interface elements.

### Camera and perspective projection

The application uses a perspective projection created with `gluPerspective`
and a first-person view created with `gluLookAt`. Mouse movement updates the
camera yaw and pitch, while keyboard movement is constrained to the deck and
kept behind the firing line.

### Lighting and material color

OpenGL lighting is enabled with a single configured light source. Color
material mode, ambient light, diffuse light, and normal normalization are used
to shade the procedural geometry.

### Visibility and compositing

Depth testing and face culling support correct 3D visibility. Blending is
used for translucent HUD panels and the sky/HUD rendering switches between
depth-tested 3D drawing and orthographic 2D drawing.

### Ray casting and intersection testing

Each shot is represented by a ray from the camera through the crosshair.
Intersections are tested against:

- The circular target face.
- Distance-bar button regions.
- Axis-aligned blocking boxes.
- Bot body-part boxes and spheres.

The nearest valid intersection determines whether the shot selects a control,
hits the target, hits the bot, or misses. Bot intersections are transformed
into each body part’s local animated frame so hit markers remain attached
while the bot moves.

### Animation

The bot’s limbs use a time-based walking phase. Its horizontal position can
also oscillate when strafing is enabled. Animation state is updated by a
16-millisecond GLUT timer callback.

## Demo and Screenshots

The repository does not currently include screenshots, recorded video, or
other image assets. To view the application, follow the setup and execution
steps below. The application opens its own interactive OpenGL window.

## Project Structure

```text
project/
├── main.py                 # Complete application and rendering loop
├── README.md               # Project documentation
└── .vscode/
    └── settings.json      # VS Code Python environment setting
```

## Prerequisites

Before running the project, install:

1. **Python 3.9 or newer**
2. **PyOpenGL**
3. A working **GLUT implementation**. FreeGLUT is recommended on Windows.

The source imports `OpenGL.GL`, `OpenGL.GLU`, and `OpenGL.GLUT`, so the GLUT
runtime must be available to the Python process. On Windows, ensure
`freeglut.dll` is on `PATH` or placed beside the Python executable.

## Installation

Open PowerShell in the project directory and install PyOpenGL:

```powershell
py -m pip install PyOpenGL
```

If the `py` launcher is unavailable, use:

```powershell
python -m pip install PyOpenGL
```

Install and configure FreeGLUT separately according to the distribution
available on your system, then verify that `freeglut.dll` can be found through
`PATH` or beside `python.exe`.

## Running the Application

From the project directory, run:

```powershell
py main.py
```

Alternatively:

```powershell
python main.py
```

The program creates a 1280 × 720 OpenGL window, captures the mouse for aiming,
and enters the GLUT main loop.

## Controls

| Input | Action |
|---|---|
| Mouse movement | Aim the first-person camera |
| Left mouse button | Fire while the mouse is captured; recapture the mouse when released |
| `W` / `A` / `S` / `D` | Move on the deck; movement is clamped behind the firing line |
| `Space` | Fire |
| `R` | Reload the 30-round magazine |
| `1` | Select 5 m |
| `2` | Select 10 m |
| `3` | Select 20 m |
| `4` | Select 30 m |
| `5` | Select 50 m |
| `C` | Clear target hits, bot hits, counters, and hit labels |
| `B` | Toggle the training bot |
| `V` | Toggle the bot walking animation |
| `N` | Toggle the bot side-to-side strafing |
| `Esc` | Release the mouse; press again to exit |

The distance bar can also be activated by aiming at and shooting its labeled
rows. Distance-bar selections and state toggles do not consume ammunition.

## Technical Implementation

The implementation is contained in [`main.py`](main.py). Important parts of
the program include:

- **Scene constants and state:** range dimensions, target distances, bot
  configuration, colors, ammunition, hit lists, and animation state.
- **Reusable drawing helpers:** procedural boxes, spheres, discs, rings,
  labels, rectangles, and HUD markers.
- **Target and bot rendering:** the selected target distance is applied to the
  target assembly, cabinet, and bot position; the distance bar and small hit
  board remain fixed.
- **Shooting pipeline:** a camera ray is tested against controls, target,
  blockers, and bot geometry, then the closest candidate is resolved.
- **Hit persistence:** target hit coordinates and bot local hit coordinates
  remain visible until `C` is pressed, including when the distance changes.
- **Input and timing:** GLUT callbacks handle keyboard, mouse, reshape,
  display, and timer events.
- **HUD rendering:** an orthographic overlay displays controls, state,
  ammunition, last-hit feedback, and target/bot hit statistics.

## Learning Outcomes

This project demonstrates practical experience with:

- OpenGL context setup and GLUT event-driven application structure.
- 3D coordinate systems, transformations, and camera control.
- Procedural modeling using reusable geometric primitives.
- Perspective projection, lighting, depth testing, and blending.
- Ray casting and analytical intersection tests.
- Local-coordinate transformations for animated-object collision detection.
- Real-time animation driven by timer updates.
- Integrating keyboard, mouse, and on-screen feedback in an interactive
  graphics application.

## Academic Submission

This repository is prepared as a submission for **CSE 4104 – Computer
Graphics Sessional** at the **Department of Computer Science and Engineering,
Bangladesh Army University of Science and Technology (BAUST)**.

Student name, student ID, section, instructor name, and submission date were
not included in the available project files and are therefore intentionally
omitted.

## License

No license file or licensing terms are included in the repository. The project
should be treated as unlicensed unless the author adds and publishes explicit
licensing information.
