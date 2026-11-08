from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math

# Window size (updated on reshape)
width, height = 1280, 720
FONT_SMALL = GLUT_BITMAP_HELVETICA_12
FONT_LARGE = GLUT_BITMAP_HELVETICA_18

# Range layout in metres; distances are measured from the firing line
FIRE_Z = 8.0
DISTANCES = (5, 10, 20, 30, 50)
TARGET_Y = 1.75
TARGET_RADIUS = 1.5
RINGS = (1.2, 0.83, 0.5, 0.26)
RING_NAMES = ('EDGE', 'OUTER RING', 'MIDDLE RING', 'INNER RING', 'BULLSEYE')
BOT_CENTER_X = 2.35
BOT_STRAFE = 0.4
BOT_SCALE = 0.66
MAGAZINE_SIZE = 30

# Distance bar rows (top to bottom) and the position of their buttons
ROWS = ('5m', '10m', '20m', '30m', '50m', 'CLEAR', 'BOT', 'WALK', 'STRAFE')
ROW_CLEAR, ROW_BOT, ROW_WALK, ROW_STRAFE = 5, 6, 7, 8
BUTTON_X = -2.5
BUTTON_Z = 3.0

# Colours
ORANGE = (0.95, 0.45, 0.18)
RED = (1, 0.15, 0.1)
BLUE = (0.25, 0.55, 1)
LABEL_COLOR = (0.95, 0.95, 0.92)
PANEL_COLOR = (0.08, 0.14, 0.19)
TITLE_COLOR = (0.58, 0.83, 0.94)
TEXT_COLOR = (0.78, 0.84, 0.90)
TARGET_TEXT_COLOR = (1, 0.5, 0.5)
BOT_TEXT_COLOR = (0.55, 0.78, 1)

HELP_LINES = (
    'WASD MOVE  |  MOUSE AIM  |  CLICK / SPACE FIRE',
    'R RELOAD  |  ESC RELEASE / EXIT',
    '1-5 DISTANCE  |  C CLEAR  |  B BOT  |  V WALK  |  N STRAFE'
)

# Keyboard shortcuts for the distance bar rows
KEYS = {
    b'1': 0,
    b'2': 1,
    b'3': 2,
    b'4': 3,
    b'5': 4,
    b'c': ROW_CLEAR,
    b'b': ROW_BOT,
    b'v': ROW_WALK,
    b'n': ROW_STRAFE
}

# Camera and input state
eye_x, eye_y, eye_z = 0.0, 1.75, FIRE_Z
yaw, pitch = 0.0, 0.0
mouse_locked = True

# Shooting state
ammo = MAGAZINE_SIZE
distance = 5
shots = 0
last_hit = ('NO SHOTS YET', TEXT_COLOR)
target_hits = []        # (x, y) offsets from the bullseye
bot_hits = []           # (part, x, y, z) in the part's own frame
hit_note = ' '          # short hit label drawn at the crosshair
hit_note_color = BLUE
hit_note_timer = 0

# Bot and animation state
bot_visible = True
walking = False
strafing = False
clear_flash = 0
walk_phase = 0.0
walk_amplitude = 0.0
strafe_phase = 0.0
last_time = 0

# Training bot model, 1.7 m tall and facing +z (towards the shooter).
# Each part is (name, pivot, hit boxes, hit spheres, decorations), where
# boxes are (x, y, z, half width, half height, half depth, colour) and
# spheres are (x, y, z, radius, colour), all relative to the pivot.
# L and R refer to the bot's own sides.
BOT_DARK = (0.20, 0.22, 0.25)
BOT_MID = (0.32, 0.34, 0.37)


def scaleValues(*values):
    return tuple(v if isinstance(v, tuple) else v * BOT_SCALE for v in values)


def makePart(name, pivot, boxes=(), spheres=(), decorations=()):
    return (
        name,
        scaleValues(*pivot),
        [scaleValues(*b) for b in boxes],
        [scaleValues(*s) for s in spheres],
        [scaleValues(*d) for d in decorations]
    )


ARM_SHAPES = (
    [(0, -0.32, 0, 0.08, 0.33, 0.09, BOT_MID)],
    [(0, -0.68, 0, 0.10, BOT_DARK)]
)
LEG_SHAPES = (
    [(0, -0.41, 0, 0.10, 0.41, 0.10, BOT_DARK),
     (0, -0.88, 0.06, 0.12, 0.08, 0.17, BOT_MID)],
    []
)
BOT_PARTS = (
    makePart('HEAD', (0, 2.25, 0),
             spheres=[(0, 0, 0, 0.30, (0.68, 0.70, 0.73))],
             decorations=[(0, 0.03, 0.28, 0.07, (0.06, 0.08, 0.10))]),
    makePart('TORSO', (0, 1.62, 0),
             [(0, 0, 0, 0.26, 0.42, 0.15, BOT_DARK),
              (0, -0.59, 0, 0.16, 0.24, 0.11, BOT_MID)]),
    makePart('L ARM', (0.34, 2.0, 0), *ARM_SHAPES),
    makePart('R ARM', (-0.34, 2.0, 0), *ARM_SHAPES),
    makePart('L LEG', (0.18, 0.96, 0), *LEG_SHAPES),
    makePart('R LEG', (-0.18, 0.96, 0), *LEG_SHAPES)
)
PIVOTS = {part[0]: part[1] for part in BOT_PARTS}


def targetZ():
    # The target face and the bot sit exactly `distance` metres from the line
    return FIRE_Z - distance


def botX():
    return BOT_CENTER_X + BOT_STRAFE * math.sin(strafe_phase)


def rowY(i):
    return 2.7 - 0.3 * i


def activeRows():
    # Highlighted distance bar rows, in the same order as ROWS
    return [d == distance for d in DISTANCES] + [
        clear_flash > 0, bot_visible, walking, strafing
    ]


def viewDirection():
    return (
        math.cos(pitch) * math.sin(yaw),
        math.sin(pitch),
        -math.cos(pitch) * math.cos(yaw)
    )


def swingAngle(name):
    s = math.sin(walk_phase) * walk_amplitude
    return {
        'L LEG': 0.5 * s,
        'R LEG': -0.5 * s,
        'L ARM': -0.4 * s,
        'R ARM': 0.4 * s
    }.get(name, 0.0)


def drawBox(x, y, z, sx, sy, sz, color):
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glColor3f(*color)
    glutSolidCube(1)
    glPopMatrix()


def drawSphere(x, y, z, r, color, detail=(20, 16)):
    glPushMatrix()
    glTranslatef(x, y, z)
    glColor3f(*color)
    glutSolidSphere(r, *detail)
    glPopMatrix()


def drawRing(x, y, z, r, line_width, color, segments=48):
    glColor3f(*color)
    glLineWidth(line_width)
    glBegin(GL_LINE_LOOP)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        glVertex3f(x + r * math.cos(angle), y + r * math.sin(angle), z)
    glEnd()
    glLineWidth(1)


def drawDisc(x, y, z, r, color, segments=48):
    glColor3f(*color)
    glNormal3f(0, 0, 1)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(x, y, z)
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        glVertex3f(x + r * math.cos(angle), y + r * math.sin(angle), z)
    glEnd()


def drawLabel(x, y, text, font=FONT_LARGE, color=(1, 1, 1), z=0):
    glColor3f(*color)
    glRasterPos3f(x, y, z)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))


def rayBox(origin, direction, box):
    # Returns the entry distance along the ray, or None if the box is missed
    t_min, t_max = 1e-4, 1e9
    for i in range(3):
        low = box[i] - box[i + 3]
        high = box[i] + box[i + 3]
        if abs(direction[i]) < 1e-9:
            if not low <= origin[i] <= high:
                return None
        else:
            t1, t2 = sorted((
                (low - origin[i]) / direction[i],
                (high - origin[i]) / direction[i]
            ))
            t_min, t_max = max(t_min, t1), min(t_max, t2)
    return t_min if t_min <= t_max and t_min > 1e-4 else None


def raySphere(origin, direction, sphere):
    offset = [origin[i] - sphere[i] for i in range(3)]
    b = sum(offset[i] * direction[i] for i in range(3))
    k = b * b - (sum(v * v for v in offset) - sphere[3] ** 2)
    if k < 0:
        return None
    t = -b - math.sqrt(k)
    return t if t > 1e-4 else None


def rayBot(origin, direction):
    # Tests each body part in its own swung frame so that hits follow the
    # animation. Returns (distance, part name, local hit point) or None.
    best = None
    for name, pivot, boxes, spheres, _ in BOT_PARTS:
        cos_a = math.cos(-swingAngle(name))
        sin_a = math.sin(-swingAngle(name))
        ox = origin[0] - botX() - pivot[0]
        oy = origin[1] - pivot[1]
        oz = origin[2] - targetZ() - pivot[2]
        local_origin = (ox, oy * cos_a - oz * sin_a, oy * sin_a + oz * cos_a)
        local_direction = (
            direction[0],
            direction[1] * cos_a - direction[2] * sin_a,
            direction[1] * sin_a + direction[2] * cos_a
        )
        distances = [rayBox(local_origin, local_direction, b) for b in boxes]
        distances += [raySphere(local_origin, local_direction, s) for s in spheres]
        distances = [t for t in distances if t is not None]
        if distances and (not best or min(distances) < best[0]):
            t = min(distances)
            best = (t, name, tuple(local_origin[i] + t * local_direction[i] for i in range(3)))
    return best


def clearAll():
    # Clears both boards, the bot markers, the counters and the labels
    global shots, last_hit, hit_note_timer, clear_flash
    target_hits.clear()
    bot_hits.clear()
    shots = hit_note_timer = 0
    last_hit = ('CLEARED', TEXT_COLOR)
    clear_flash = 25


def pressButton(i):
    global distance, bot_visible, walking, strafing
    if i < ROW_CLEAR:
        distance = DISTANCES[i]
    elif i == ROW_CLEAR:
        clearAll()
    elif i == ROW_BOT:
        bot_visible = not bot_visible
        if not bot_visible:
            walking = strafing = False
    elif i == ROW_WALK and bot_visible:
        walking = not walking
    elif i == ROW_STRAFE and bot_visible:
        strafing = not strafing


def shoot():
    global ammo, shots, hit_note, hit_note_color, hit_note_timer, last_hit
    origin = (eye_x, eye_y, eye_z)
    direction = viewDirection()
    target_z = targetZ()
    candidates = []

    if direction[2] < -1e-6:
        # Target face
        t = (target_z - eye_z) / direction[2]
        x = eye_x + t * direction[0]
        y = eye_y + t * direction[1] - TARGET_Y
        if x * x + y * y <= TARGET_RADIUS * TARGET_RADIUS:
            candidates.append((t, 'target', (x, y)))

        # Distance bar buttons
        t = (BUTTON_Z - eye_z) / direction[2]
        x = eye_x + t * direction[0]
        y = eye_y + t * direction[1]
        for i in range(len(ROWS)):
            if (bot_visible or i < ROW_WALK) and -2.95 <= x <= -1.85 and abs(y - rowY(i)) <= 0.15:
                candidates.append((t, 'button', i))

    # Target housing, cabinet and hit board stop bullets
    blockers = (
        (0, TARGET_Y, target_z - 0.27, 1.75, 1.75, 0.25),
        (2.3, 1.5, target_z - 0.45, 0.65, 1.0, 0.4),
        (-1.27, 1.9, 3.3, 0.5, 0.5, 0.05)
    )
    for blocker in blockers:
        t = rayBox(origin, direction, blocker)
        if t:
            candidates.append((t, 'solid', None))

    bot_hit = rayBot(origin, direction) if bot_visible else None
    if bot_hit:
        candidates.append((bot_hit[0], 'bot', bot_hit[1:]))

    candidates.sort(key=lambda c: c[0])
    if candidates:
        kind, value = candidates[0][1], candidates[0][2]
    else:
        kind, value = 'miss', None

    # Button presses do not use ammo
    if kind == 'button':
        pressButton(value)
        return
    if ammo <= 0:
        hit_note, hit_note_color, hit_note_timer = 'EMPTY - PRESS R', (1, 0.5, 0.4), 50
        return

    ammo -= 1
    shots += 1
    if kind == 'target':
        target_hits.append(value)
        ring = sum(math.hypot(*value) <= r for r in RINGS)
        hit_note, hit_note_color, hit_note_timer = RING_NAMES[ring], RED, 50
        last_hit = ('TARGET: %s (%d PTS)' % (RING_NAMES[ring], ring + 1), TARGET_TEXT_COLOR)
    elif kind == 'bot':
        part = value[0]
        bot_hits.append((part,) + value[1])
        hit_note, hit_note_color, hit_note_timer = part, BLUE, 50
        last_hit = ('BOT: ' + part, BOT_TEXT_COLOR)
    else:
        last_hit = ('MISS', TEXT_COLOR)


def drawEnvironment():
    # Sky gradient and deck plank seams
    glDisable(GL_LIGHTING)
    glBegin(GL_QUADS)
    glColor3f(0.92, 0.95, 0.99)
    glVertex3f(-900, -300, -400)
    glVertex3f(900, -300, -400)
    glColor3f(0.62, 0.78, 0.95)
    glVertex3f(900, 400, -400)
    glVertex3f(-900, 400, -400)
    glEnd()
    glColor3f(0.30, 0.20, 0.13)
    glLineWidth(2)
    glBegin(GL_LINES)
    for x in range(-9, 10):
        glVertex3f(x, 0.004, 1.8)
        glVertex3f(x, 0.004, 14)
    glEnd()
    glLineWidth(1)
    glEnable(GL_LIGHTING)

    # Deck (ends at the 5 m line), target track and firing line
    drawBox(0, -0.3, 7.9, 20, 0.6, 12.2, (0.55, 0.40, 0.29))
    drawBox(0, -0.25, -20, 0.25, 0.2, 44, (0.22, 0.22, 0.25))
    drawBox(0, 0.005, FIRE_Z, 20, 0.01, 0.14, (0.95, 0.85, 0.30))
    glDisable(GL_LIGHTING)
    drawLabel(8.4, 0.03, 'FIRING LINE', FONT_SMALL, (1, 0.95, 0.55), FIRE_Z - 0.6)
    glEnable(GL_LIGHTING)

    # Table, tarp and bullets
    drawBox(0, 0.35, 6.4, 6, 0.7, 2.4, (0.5, 0.37, 0.27))
    drawBox(-1.7, 0.70, 6.4, 2.6, 0.08, 2.3, (0.36, 0.5, 0.4))
    for i in range(6):
        drawBox(2.3 + 0.07 * (i % 3), 0.93, 6.3 + 0.09 * (i // 3),
                0.04, 0.03, 0.12, (0.8, 0.65, 0.25))

    # Crate
    drawBox(-8, 1.65, 3.8, 3.2, 3.3, 2.4, (0.58, 0.42, 0.27))
    for x in (-9.45, -6.55):
        drawBox(x, 1.65, 5.02, 0.16, 3.3, 0.06, (0.36, 0.25, 0.16))
    glPushMatrix()
    glTranslatef(-8, 1.65, 5.02)
    glRotatef(40, 0, 0, 1)
    drawBox(0, 0, 0, 0.18, 3.9, 0.06, (0.4, 0.28, 0.18))
    glPopMatrix()

    # Fence
    for z in (5.6, 2.2):
        drawBox(8, 0.9, z, 0.22, 1.8, 0.22, (0.5, 0.34, 0.2))
    for y in (0.8, 1.45):
        drawBox(8, y, 3.9, 0.14, 0.16, 3.7, (0.52, 0.36, 0.22))

    # Floating rocks
    rocks = (
        (-4.6, -1, 0, 1),
        (5.8, -1.2, 1, 0.8),
        (9.5, 2.6, -5, 0.45),
        (11, 1.4, -3, 0.35),
        (10.5, 3.3, -9, 0.3),
        (-7, -0.5, -6, 0.9)
    )
    for x, y, z, radius in rocks:
        drawSphere(x, y, z, radius, (0.38, 0.30, 0.26), (20, 50))


def drawBigTarget():
    # Built around the aiming face (local z = 0) and slid to the selected distance
    glPushMatrix()
    glTranslatef(0, 0, targetZ())
    drawBox(0.6, -0.07, 0, 5.6, 0.18, 2.6, (0.12, 0.12, 0.14))
    drawBox(0, TARGET_Y, -0.27, 3.5, 3.5, 0.5, (0.21, 0.18, 0.16))
    drawDisc(0, TARGET_Y, 0, TARGET_RADIUS, (0.68, 0.58, 0.5))
    drawDisc(1.38, TARGET_Y - 1.07, 0, 0.17, (0.95, 0.5, 0.12))
    for x in (-1.1, 1.1):
        drawBox(x, 0.12, -0.2, 0.5, 0.24, 0.6, (0.62, 0.58, 0.54))
    drawBox(0, 0.15, -0.1, 1.0, 0.3, 0.4, (0.55, 0.5, 0.45))
    drawBox(2.3, 1.5, -0.45, 1.3, 2.0, 0.8, (0.42, 0.37, 0.33))
    drawBox(2.3, 1.5, -0.04, 0.05, 2.0, 0.02, (0.2, 0.18, 0.17))

    glDisable(GL_LIGHTING)
    for radius in RINGS:
        drawRing(0, TARGET_Y, 0.01, radius, 3, ORANGE)
    for x, y in target_hits:
        drawRing(x, TARGET_Y + y, 0.02, 0.05, 2, RED)
    glEnable(GL_LIGHTING)
    glPopMatrix()


def drawSmallBoard():
    # Fixed board that mirrors every target hit
    cx, cy = -1.27, 1.9
    scale = 0.42 / TARGET_RADIUS
    drawBox(cx, cy, 3.3, 1.0, 1.0, 0.1, (0.2, 0.18, 0.17))
    drawDisc(cx, cy, 3.36, 0.46, (0.28, 0.25, 0.24))

    glDisable(GL_LIGHTING)
    for radius in (0.44, 0.36, 0.27, 0.18, 0.09):
        drawRing(cx, cy, 3.365, radius, 2, (0.6, 0.56, 0.52))
    drawLabel(cx - 0.4, cy + 0.57, 'HIT BOARD  %d' % len(target_hits), FONT_SMALL, LABEL_COLOR, 3.37)
    for x, y in target_hits:
        drawRing(cx + x * scale, cy + y * scale, 3.37, 0.03, 2, RED)
    glEnable(GL_LIGHTING)


def drawDistanceBar():
    # Fixed at the 5 m line; it does not follow the target
    wood = (0.55, 0.45, 0.37)
    drawBox(-2.4, 1.5, 2.92, 1.15, 3.0, 0.16, wood)
    drawBox(-3.45, 1.6, 2.8, 0.14, 3.2, 0.2, wood)
    drawBox(-2.63, 3.2, 2.8, 1.77, 0.14, 0.2, wood)
    glPushMatrix()
    glTranslatef(-3.2, 2.5, 2.8)
    glRotatef(40, 0, 0, 1)
    drawBox(0, 0, 0, 0.1, 1.0, 0.12, wood)
    glPopMatrix()

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    z = BUTTON_Z + 0.005
    for i, (name, active) in enumerate(zip(ROWS, activeRows())):
        # WALK and STRAFE are only available while the bot is shown
        if i >= ROW_WALK and not bot_visible:
            continue
        y = rowY(i)
        color = (0.6, 1, 0.9) if active else (0.7, 0.85, 0.8)
        glColor3f(*color)
        glLineWidth(2)
        glBegin(GL_LINES)

        # Corner brackets around the button
        for dx in (-1, 1):
            for dy in (-1, 1):
                a = BUTTON_X + dx * 0.12
                b = y + dy * 0.12
                glVertex3f(a, b, z)
                glVertex3f(a - dx * 0.07, b, z)
                glVertex3f(a, b, z)
                glVertex3f(a, b - dy * 0.07, z)

        # Crosshair ticks on the active button
        if active:
            for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                glVertex3f(BUTTON_X + a * 0.04, y + b * 0.04, z)
                glVertex3f(BUTTON_X + a * 0.1, y + b * 0.1, z)
        glEnd()
        glLineWidth(1)
        if active:
            drawRing(BUTTON_X, y, z, 0.07, 2, color, 24)
        drawLabel(BUTTON_X + 0.22, y - 0.04, name, FONT_SMALL, LABEL_COLOR, BUTTON_Z + 0.02)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


def drawBot():
    bx, bz = botX(), targetZ()
    for name, pivot, boxes, spheres, decorations in BOT_PARTS:
        glPushMatrix()
        glTranslatef(bx + pivot[0], pivot[1], bz + pivot[2])
        glRotatef(math.degrees(swingAngle(name)), 1, 0, 0)
        for b in boxes:
            drawBox(b[0], b[1], b[2], 2 * b[3], 2 * b[4], 2 * b[5], b[6])
        for s in spheres + decorations:
            drawSphere(s[0], s[1], s[2], s[3], s[4])

        # Hit markers stay attached to the body part
        glDisable(GL_LIGHTING)
        for hit in bot_hits:
            if hit[0] == name:
                drawSphere(hit[1], hit[2], hit[3], 0.035, BLUE, (8, 6))
        glEnable(GL_LIGHTING)
        glPopMatrix()


def setupLighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightfv(GL_LIGHT0, GL_POSITION, [-5, 10, 5, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1, 0.95, 0.86, 1])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.45, 0.52, 0.64, 1])


def drawRect(x0, y0, x1, y1, color, alpha=1):
    glColor4f(*color, alpha)
    glBegin(GL_QUADS)
    glVertex2f(x0, y0)
    glVertex2f(x1, y0)
    glVertex2f(x1, y1)
    glVertex2f(x0, y1)
    glEnd()


def drawMark(x, y, color):
    # Hit marker on the hit panel
    drawDisc(x, y, 0, 3.6, (1, 1, 1), 12)
    drawDisc(x, y, 0, 2.6, color, 12)


def drawStat(x, y, name, value, color, offset):
    drawLabel(x, y, name, FONT_SMALL, TEXT_COLOR)
    drawLabel(x + offset, y, str(value), FONT_SMALL, color)


def drawHitPanel():
    # Mirrors the hit boards: red marks for the target, blue for the bot
    x0, top = width - 280, height - 20
    drawRect(x0, top - 285, x0 + 260, top, PANEL_COLOR, 0.72)
    drawLabel(x0 + 12, top - 22, 'HIT LOCATIONS', FONT_SMALL, TITLE_COLOR)
    drawLabel(x0 + 130, top - 22, 'HITS %d  SHOTS %d' % (len(target_hits) + len(bot_hits), shots),
              FONT_SMALL, ORANGE)

    # Target replica
    cx, cy = x0 + 58, top - 98
    target_scale = 40 / TARGET_RADIUS
    drawDisc(cx, cy, 0, TARGET_RADIUS * target_scale, (0.16, 0.18, 0.20))
    for radius in RINGS:
        drawRing(cx, cy, 0, radius * target_scale, 1, ORANGE)
    for x, y in target_hits:
        drawMark(cx + x * target_scale, cy + y * target_scale, RED)

    # Bot silhouette seen from the front; parts that were hit are lit
    hit_parts = [hit[0] for hit in bot_hits]
    fx, fy = x0 + 170, top - 150
    bot_scale = 56
    for name, pivot, boxes, spheres, _ in BOT_PARTS:
        color = (0.62, 0.70, 0.78) if name in hit_parts else (0.26, 0.31, 0.34)
        for b in boxes:
            x = fx + (pivot[0] + b[0]) * bot_scale
            y = fy + (pivot[1] + b[1]) * bot_scale
            drawRect(x - b[3] * bot_scale, y - b[4] * bot_scale,
                     x + b[3] * bot_scale, y + b[4] * bot_scale, color)
        for s in spheres:
            drawDisc(fx + (pivot[0] + s[0]) * bot_scale, fy + (pivot[1] + s[1]) * bot_scale,
                     0, s[3] * bot_scale, color)
    for hit in bot_hits:
        drawMark(fx + (PIVOTS[hit[0]][0] + hit[1]) * bot_scale,
                 fy + (PIVOTS[hit[0]][1] + hit[2]) * bot_scale, BLUE)
    drawLabel(fx - 30, fy + 60, 'R', FONT_SMALL, TEXT_COLOR)
    drawLabel(fx + 22, fy + 60, 'L', FONT_SMALL, TEXT_COLOR)

    # Hit counters and the last hit
    for i, name in enumerate(PIVOTS):
        drawStat(x0 + 14 + 108 * (i % 2), top - 178 - 18 * (i // 2),
                 name, hit_parts.count(name), BOT_TEXT_COLOR, 54)
    drawStat(x0 + 14, top - 232, 'BOT TOTAL', len(bot_hits), BOT_TEXT_COLOR, 74)
    drawStat(x0 + 122, top - 232, 'TARGET', len(target_hits), TARGET_TEXT_COLOR, 56)
    drawLabel(x0 + 14, top - 250, 'LAST HIT', FONT_SMALL, TITLE_COLOR)
    drawLabel(x0 + 14, top - 268, last_hit[0], FONT_SMALL, last_hit[1])


def drawHud():
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glEnable(GL_POINT_SMOOTH)

    # Status strip
    status = ('OFF', 'ON')
    drawRect(width / 2 - 230, height - 55, width / 2 + 230, height - 16, PANEL_COLOR, 0.72)
    drawLabel(width / 2 - 212, height - 44, 'DIST  %d m' % distance)
    drawLabel(width / 2 - 80, height - 42,
              'BOT %s   WALK %s   STRAFE %s' % (status[bot_visible], status[walking], status[strafing]),
              FONT_SMALL, TEXT_COLOR)

    # Key help
    drawRect(16, height - 135, 446, height - 70, PANEL_COLOR, 0.55)
    for i, line in enumerate(HELP_LINES):
        drawLabel(26, height - 85 - 20 * i, line, FONT_SMALL, TEXT_COLOR)

    # Crosshair dot with a dark outline
    for size, color in ((8, (0, 0, 0)), (5, (0.2, 1, 0.45))):
        glPointSize(size)
        glColor3f(*color)
        glBegin(GL_POINTS)
        glVertex2f(width / 2, height / 2)
        glEnd()

    # Hit label with a drop shadow, ammo and hit panel
    if hit_note_timer:
        drawLabel(width / 2 + 17, height / 2 + 9, hit_note, FONT_LARGE, (0, 0, 0))
        drawLabel(width / 2 + 16, height / 2 + 10, hit_note, FONT_LARGE, hit_note_color)
    drawLabel(width - 230, 28, 'MAG  %02d / %d' % (ammo, MAGAZINE_SIZE))
    drawHitPanel()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


def keyboard(key, x, y):
    global eye_x, eye_z, ammo, mouse_locked
    key = key.lower()
    forward = (key == b'w') - (key == b's')
    side = (key == b'd') - (key == b'a')
    if key == b'\x1b':
        if mouse_locked:
            mouse_locked = False
            glutSetCursor(GLUT_CURSOR_INHERIT)
        else:
            glutLeaveMainLoop()
    elif key == b'r':
        ammo = MAGAZINE_SIZE
    elif key == b' ':
        shoot()
    elif key in KEYS:
        pressButton(KEYS[key])

    # Keep the player on the deck and behind the firing line
    eye_x = max(-7.5, min(7.5, eye_x + (forward * math.sin(yaw) + side * math.cos(yaw)) * 0.42))
    eye_z = max(FIRE_Z, min(12, eye_z + (-forward * math.cos(yaw) + side * math.sin(yaw)) * 0.42))


def mouseClick(button, state, x, y):
    global mouse_locked
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if mouse_locked:
            shoot()
        else:
            mouse_locked = True
            glutSetCursor(GLUT_CURSOR_NONE)
            glutWarpPointer(width // 2, height // 2)


def mouseMove(x, y):
    global yaw, pitch
    if mouse_locked:
        yaw += (x - width // 2) * 0.0025
        pitch = max(-1.15, min(1.15, pitch + (height // 2 - y) * 0.0025))
        glutWarpPointer(width // 2, height // 2)


def reshape(w, h):
    global width, height
    width, height = max(1, w), max(1, h)


def update(value):
    global walk_phase, walk_amplitude, strafe_phase, last_time
    global hit_note_timer, clear_flash
    now = glutGet(GLUT_ELAPSED_TIME)
    dt = min(0.05, (now - last_time) / 1000.0) if last_time else 0.016
    last_time = now

    # Ease the walk cycle in and out
    walk_amplitude += ((1.0 if walking else 0.0) - walk_amplitude) * min(1.0, dt * 8)
    if walk_amplitude > 0.01:
        walk_phase += dt * 6
    if strafing:
        strafe_phase += dt * 1.2
    hit_note_timer = max(0, hit_note_timer - 1)
    clear_flash = max(0, clear_flash - 1)
    glutPostRedisplay()
    glutTimerFunc(16, update, 0)


def main():
    setupLighting()
    drawEnvironment()
    drawBigTarget()
    drawSmallBoard()
    drawDistanceBar()
    if bot_visible:
        drawBot()
    drawHud()


def showScreen():
    glClearColor(0.8, 0.88, 0.97, 1)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(68, width / height, 0.1, 600)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    d = viewDirection()
    gluLookAt(eye_x, eye_y, eye_z, eye_x + d[0], eye_y + d[1], eye_z + d[2], 0, 1, 0)
    main()
    glutSwapBuffers()


glutInit()
glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
glutInitWindowSize(width, height)
glutInitWindowPosition(60, 40)
glutCreateWindow(b"3D Tactical Shooting Range")
glEnable(GL_DEPTH_TEST)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glEnable(GL_CULL_FACE)
glutDisplayFunc(showScreen)
glutReshapeFunc(reshape)
glutKeyboardFunc(keyboard)
glutMouseFunc(mouseClick)
glutPassiveMotionFunc(mouseMove)
glutMotionFunc(mouseMove)
glutSetCursor(GLUT_CURSOR_NONE)
glutWarpPointer(width // 2, height // 2)
glutTimerFunc(16, update, 0)
glutMainLoop()
