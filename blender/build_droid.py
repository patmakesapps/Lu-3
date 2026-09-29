"""
Lumalien house droid - v2 printable parts (three-leg droid, rotating dome, fixed LiDAR crown).

Run inside Blender (Scripting tab, or via Blender MCP):
    ns = {"__name__": "droid_v2"}
    exec(compile(open(r"<path>/build_droid.py").read(), "build_droid.py", "exec"), ns)
    ns["build_droid"]()            # build / rebuild the model
    ns["export_stls"]()            # write droid/stl/*.stl + PRINT_LIST.md

Reuses the reference part models from build_parts.py. 1 unit = 1 mm, Z up, front = -Y.

Collections under "Droid v1":
  Printed - Body / Head / Legs & Feet : one object per printed part (custom props: colour, qty,
      print, notes). Shapes are built from primitives + live Boolean modifiers whose operand
      objects live in the hidden "Helpers" collection - move/resize a helper to reshape a part.
  Electronics (placed) : reference parts in their mounted positions (prefix A_).
  Hardware (not printed) : bumper pads etc.
Joining: glue for printed-to-printed joints; heat-set inserts only where hardware mounts;
the N20 brackets use their own screws and nuts; zip-ties for the speakers, bank, AA pack and
anything whose dimensions are estimates.
"""
import math
import os
import struct

import bmesh
import bpy
from mathutils import Matrix, Vector

PARTS_FILE = os.path.join(os.path.dirname(bpy.data.filepath), "blender", "build_parts.py")
P = {"__name__": "droid_parts"}
exec(compile(open(PARTS_FILE, encoding="utf-8").read(), PARTS_FILE, "exec"), P)
P["MATS"].update({
    "PLA_White": (0.92, 0.92, 0.95, 1),
    "PLA_Purple": (0.45, 0.20, 0.75, 1),
    "PLA_Black": (0.06, 0.06, 0.07, 1),
    "PLA_Clear": (0.78, 0.88, 0.95, 1),
})
Part, get_coll, PREFIX = P["Part"], P["get_coll"], P["PREFIX"]

ROOT = "Droid v1"
PI = math.pi
W, PU, BK, CL = "PLA_White", "PLA_Purple", "PLA_Black", "PLA_Clear"
COLOUR = {W: "White PLA", PU: "Purple PLA", BK: "Black PLA", CL: "Clear PLA"}

# ----------------------------------------------------------------------------- key dimensions
BODY_R, BODY_WALL = 75.0, 3.0
BODY_RI = BODY_R - BODY_WALL
BODY_Z0, BODY_Z1 = 80.0, 290.0            # body shell bottom / top
DECK_R = BODY_RI - 0.2                    # decks slide inside the shell (glue / screw fit)
HEAD_Z0, DOME_Z0, DOME_ZS = 292.0, 310.0, 0.85
TT_Z0, TT_T, TT_R = 297.5, 3.0, 71.6      # turntable (glued inside the collar)
GEAR_M, GEAR_N = 1.25, 24                 # 1:1 head gears, 30 mm centres
SERVO_XY = (0.0, 30.0)
HUB_GEAR_Z = (292.6, 297.5)
SERVO_GEAR_Z = (294.4, 297.4)
LIDAR_BASE = 342.0
CROWN_R_IN, CROWN_R_OUT, CROWN_TOP = 36.5, 39.5, 366.0
MAST_R_IN, MAST_R_OUT, MAST_TOP = 7.0, 10.0, 336.0     # MAST_TOP = top of the mast cap
MAST_TUBE_TOP = MAST_TOP - 2.0            # plain tube ends inside the cap
DOME_OPENING_R = 41.5
LEG_X, LEG_T = 95.0, 30.0
LEG_TOP_Z, LEG_BOT_Z, LEG_SOCKET_Z = 255.0, 70.0, 66.0
LEG_W_BOT, LEG_W_TOP = 52.0, 60.0
SHOULDER_Z = 238.0
AXLE_R_IN, AXLE_R_OUT = 6.0, 9.9
AXLE_Y, AXLE_Z, WHEEL_R, WHEEL_W = 30.0, 32.0, 32.0, 12.0
MOTOR_FLOOR_Z = AXLE_Z - 5.0              # N20 is 10 mm tall, axis 5 mm above its floor
BRACKET_X = 82.0                          # N20 bracket centre (|x|)
BRACKET_HOLE_DY = 9.0                     # estimated - holes are slotted +/-1.5 mm
CASTER_Y = -60.0
EYE_Z = 320.0
IND_Z, IND_AZ = 313.0, math.radians(40)
SPK_Z = 165.0
JETSON_Y = 42.6                           # Jetson origin (its feet sit in 6 mm standoffs)

# hardware (check against your insert kit)
M2_INSERT_R, M3_INSERT_R = 1.6, 2.0       # 3.2 / 4.0 mm holes
M3_CLEAR_R, M2_CLEAR_R = 1.7, 1.2
SERVO_PILOT_R = 0.9


def leg_y(z):
    return AXLE_Y * (LEG_TOP_Z - z) / (LEG_TOP_Z - LEG_BOT_Z)


def leg_w(z):
    return LEG_W_BOT + (LEG_W_TOP - LEG_W_BOT) * (z - LEG_BOT_Z) / (LEG_TOP_Z - LEG_BOT_Z)


LEG_TILT = math.atan2(AXLE_Y, LEG_TOP_Z - LEG_BOT_Z)
SHOULDER_Y = leg_y(SHOULDER_Z)


# ----------------------------------------------------------------------------- geometry

def prism(p, pts, z0, h, mat):
    bot = [p.bm.verts.new((x, y, z0)) for x, y in pts]
    top = [p.bm.verts.new((x, y, z0 + h)) for x, y in pts]
    faces = [p.bm.faces.new(list(reversed(bot))), p.bm.faces.new(top)]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(p.bm.faces.new((bot[i], bot[j], top[j], top[i])))
    idx = p.mi(mat)
    for f in faces:
        f.material_index = idx


def tbox(p, b, bw, bd, t, tw, td, mat):
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    vb = [p.bm.verts.new((b[0] + sx * bw / 2, b[1] + sy * bd / 2, b[2])) for sx, sy in corners]
    vt = [p.bm.verts.new((t[0] + sx * tw / 2, t[1] + sy * td / 2, t[2])) for sx, sy in corners]
    faces = [p.bm.faces.new(list(reversed(vb))), p.bm.faces.new(vt)]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(p.bm.faces.new((vb[i], vb[j], vt[j], vt[i])))
    idx = p.mi(mat)
    for f in faces:
        f.material_index = idx


def cone(p, r1, r2, h, center, mat, segs=48):
    res = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r1, radius2=r2, depth=h,
                                matrix=Matrix.Translation(center))
    p._tag(res["verts"], mat)


def leg_section(p, x, z0, z1, grow, mat):
    tbox(p, (x, leg_y(z0), z0), LEG_T + 2 * grow, leg_w(z0) + 2 * grow,
         (x, leg_y(z1), z1), LEG_T + 2 * grow, leg_w(z1) + 2 * grow, mat)


def dome(p, r, zscale, z0, mat, cap=False, segs=64, rings=20):
    ringsv = []
    for i in range(rings):
        phi = (PI / 2) * i / rings
        rr, zz = r * math.cos(phi), z0 + r * zscale * math.sin(phi)
        ringsv.append([p.bm.verts.new((rr * math.cos(2 * PI * k / segs),
                                       rr * math.sin(2 * PI * k / segs), zz))
                       for k in range(segs)])
    pole = p.bm.verts.new((0, 0, z0 + r * zscale))
    idx = p.mi(mat)
    for i in range(rings - 1):
        a, b = ringsv[i], ringsv[i + 1]
        for k in range(segs):
            m = (k + 1) % segs
            p.bm.faces.new((a[k], a[m], b[m], b[k])).material_index = idx
    for k in range(segs):
        p.bm.faces.new((ringsv[-1][k], ringsv[-1][(k + 1) % segs], pole)).material_index = idx
    if cap:
        p.bm.faces.new(list(reversed(ringsv[0]))).material_index = idx


def involute_pts(m, n, cx=0.0, cy=0.0, phase=0.0, backlash=0.15, pa=math.radians(20)):
    rp = m * n / 2
    rb, ra, rf = rp * math.cos(pa), rp + m, rp - 1.25 * m
    inv = lambda a: math.tan(a) - a  # noqa: E731
    half_t = (PI * m / 2 - backlash / 2) / (2 * rp) + inv(pa)

    def psi(r):
        return half_t - inv(math.acos(min(1.0, rb / r)))

    radii = [rb + (ra - rb) * i / 6 for i in range(7)]
    pts = []
    for k in range(n):
        c = phase + 2 * PI * k / n
        flank = [(rf, c - half_t)] + [(r, c - psi(r)) for r in radii]
        flank += [(r, c + psi(r)) for r in reversed(radii)] + [(rf, c + half_t)]
        flank.append((rf, c + PI / n))                     # root midpoint
        pts += [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in flank]
    return pts


def window_pts(w, h, ch):
    """Rectangle with 45 deg chamfered top corners (printable without supports)."""
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2 - ch), (w / 2 - ch, h / 2),
            (-w / 2 + ch, h / 2), (-w / 2, h / 2 - ch)]


def d_bore_pts(r=1.6, flat=1.05, segs=24):
    a0 = math.acos(flat / r)
    return [(r * math.cos(a0 + (2 * PI - 2 * a0) * i / segs),
             r * math.sin(a0 + (2 * PI - 2 * a0) * i / segs)) for i in range(segs + 1)]


# ----------------------------------------------------------------------------- objects

_C = {}


def mk(name, coll, build, loc=(0, 0, 0), rot=None, mode="XYZ", props=None):
    p = Part(name)
    build(p)
    ob = p.build(coll, loc, props=props)
    if rot:
        ob.rotation_mode = mode
        ob.rotation_euler = rot
    return ob


_MW = {}   # helper world matrices at creation (matrix_world is stale until a depsgraph update)


def helper(name, build, loc=(0, 0, 0), rot=None, mode="XYZ"):
    """Hidden boolean operand. Never shown in the viewport or renders."""
    ob = mk("H_" + name, _C["help"], build, loc, rot, mode)
    ob.display_type = "WIRE"
    ob.hide_render = True
    ob.hide_viewport = True
    ob.hide_select = True
    _MW[ob.name] = ob.matrix_basis.copy()
    return ob


def _bool(ob, op, others):
    """Boolean modifiers whose operands are parented to the part, so moving/rotating the part
    (inspection, exploded views) carries its cutters along. Shared helpers get one copy per
    part."""
    target_mw = ob.matrix_basis.copy()          # printed parts are never parented
    for o in others:
        mw = _MW[o.name]
        if o.parent is not None and o.parent is not ob:
            dup = o.copy()                       # shares mesh data with the original helper
            dup.name = f"{o.name}__{ob.name}"
            _C["help"].objects.link(dup)
            _MW[dup.name] = mw
            o = dup
        if o.parent is not ob:
            o.parent = ob
            o.matrix_parent_inverse = target_mw.inverted()
            o.matrix_basis = mw
        m = ob.modifiers.new(f"{op[:3].lower()}_{o.name}", "BOOLEAN")
        m.operation = op
        m.object = o
        m.solver = "MANIFOLD"   # robust + fast; operands must be clean closed meshes


def union(ob, *o):
    _bool(ob, "UNION", o)


def cut(ob, *o):
    _bool(ob, "DIFFERENCE", o)


def bevel_edges(ob, weight, width, segs=6):
    """Bevel modifier (first in the stack) driven by per-edge weights: weight(v0, v1) -> 0..1
    times `width` mm."""
    me = ob.data
    attr = me.attributes.get("bevel_weight_edge") or me.attributes.new(
        "bevel_weight_edge", "FLOAT", "EDGE")
    for e in me.edges:
        attr.data[e.index].value = weight(me.vertices[e.vertices[0]].co,
                                          me.vertices[e.vertices[1]].co)
    m = ob.modifiers.new("bevel", "BEVEL")
    m.limit_method = "WEIGHT"
    m.width = width
    m.segments = segs
    m.profile = 0.5
    return m


def printed(name, coll, build, colour, prn, notes="", qty=1, loc=(0, 0, 0), rot=None,
            mode="XYZ"):
    ob = mk(name, coll, build, loc, rot, mode,
            props={"printed": 1, "colour": COLOUR[colour], "qty": qty, "print": prn,
                   "notes": notes})
    return ob


def place(ob, loc, rot=(0, 0, 0), mode="XYZ"):
    for o in [ob, *ob.children]:
        o.name = "A_" + o.name.split(".")[0]
    ob.location = loc
    ob.rotation_mode = mode
    ob.rotation_euler = rot
    return ob


def neopixel_ring(coll, loc):
    p = Part("NeoPixel_Ring_12_1643")
    p.ring(11.65, 18.4, 1.6, (0, 0, 0.8), "PCB_Black")
    for i in range(12):
        a = 2 * PI * i / 12
        p.box((5, 5, 1.6), (15 * math.cos(a), 15 * math.sin(a), 2.4), "Plastic_White")
    return p.build(coll, loc, props={
        "dims_mm": "36.8 OD x 23.3 ID (Adafruit)",
        "source": "https://www.adafruit.com/product/1643",
        "notes": "5 V pin 2, GND pin 6, data SPI MOSI pin 19 (neopixel_spi). ~330 ohm in data, "
                 "1000 uF across power. Glue into the indicator pod recess.",
    })


# common helpers ---------------------------------------------------------------

def outside_trim(name, r=BODY_RI - 0.1, z0=60, z1=300):
    """Everything outside radius r (for parts glued against the inside of the shell)."""
    return helper(name, lambda p: p.ring(r, r + 150, z1 - z0, (0, 0, (z0 + z1) / 2), W,
                                         segs=128))


def insert_holes(name, pts, r, depth, axis="Z", sign=1):
    """Insert/pilot holes. pts are the hole-mouth centres; holes go `depth` in -axis*sign."""
    def build(p):
        for c in pts:
            c = Vector(c)
            d = Vector({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis]) * sign
            p.cyl(r, depth + 0.5, tuple(c - d * (depth - 0.5) / 2), W, axis=axis, segs=20)
    return helper(name, build)


# ----------------------------------------------------------------------------- build

def clear_root():
    root = bpy.data.collections.get(ROOT)
    if root is None:
        return
    for c in [root, *root.children_recursive]:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0 and me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)


def find_layer_coll(lc, name):
    if lc.name == name:
        return lc
    for ch in lc.children:
        r = find_layer_coll(ch, name)
        if r:
            return r
    return None


def add_rails(shell, name, y0, y1, zb, zt, r_plate=BODY_RI - 0.3):
    """Slide-in slot for a 3 mm plate (y0..y1) against the inside of the shell: a rib either
    side of each plate edge plus a bottom stop. Plates drop in from the open top."""
    def x_wall(y):
        return math.sqrt(BODY_RI ** 2 - y ** 2)

    def ribs(p):
        for ya, yb in ((y0 - 2.2, y0 - 0.2), (y1 + 0.2, y1 + 2.2)):
            x_in = math.sqrt(r_plate ** 2 - max(abs(ya), abs(yb)) ** 2) - 6
            x_out = x_wall(max(abs(ya), abs(yb))) + 1.5
            for sx in (-1, 1):
                p.box((x_out - x_in, yb - ya, zt - zb + 3),
                      (sx * (x_in + x_out) / 2, (ya + yb) / 2, (zb - 3 + zt) / 2), W)

    def stops(p):
        ya, yb = y0 - 1.2, y1 + 1.2
        x_in = math.sqrt(r_plate ** 2 - max(abs(ya), abs(yb)) ** 2) - 6
        x_out = x_wall(max(abs(ya), abs(yb))) + 1.5
        for sx in (-1, 1):
            p.box((x_out - x_in, yb - ya, 3), (sx * (x_in + x_out) / 2, (ya + yb) / 2, zb - 1.5),
                  W)
    union(shell, helper(f"{name}_Rails", ribs), helper(f"{name}_Stops", stops))


# Lumalien Robotics logo: an "L" with a right triangle nested in its corner (unit coords, CCW)
LOGO_L = [(0, 0), (1.0, 0), (0.92, 0.2), (0.28, 0.2), (0.28, 1.12), (0, 1.12)]
LOGO_TRI = [(0.37, 0.29), (0.9, 0.29), (0.37, 1.0)]
LOGO_W, LOGO_H = 1.0, 1.12


def offset_poly(pts, d):
    """Offset a simple CCW polygon outward by d (mitred corners)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((e0.y, -e0.x)), Vector((e1.y, -e1.x))
        bis = (n0 + n1).normalized()
        out.append(tuple(p1 + bis * (d / max(0.2, bis.dot(n0)))))
    return out


def logo_polys(height, grow=0.0):
    """Logo polygons scaled to `height` mm, centred on the origin, offset by `grow` mm."""
    k = height / LOGO_H
    polys = []
    for poly in (LOGO_L, LOGO_TRI):
        pts = [((x - LOGO_W / 2) * k, (y - LOGO_H / 2) * k) for x, y in poly]
        polys.append(offset_poly(pts, grow) if grow else pts)
    return polys


def logo_on_plane(p, height, grow, w0, w1, to_world, mat):
    """Extrude the logo from w0 to w1 along the local normal; to_world(u, v, w) -> xyz."""
    for poly in logo_polys(height, grow):
        tmp = Part("tmp")
        prism(tmp, poly, w0, w1 - w0, mat)
        for v in tmp.bm.verts:
            v.co = to_world(v.co.x, v.co.y, v.co.z)
        bmesh.ops.recalc_face_normals(tmp.bm, faces=tmp.bm.faces[:])
        me = bpy.data.meshes.new("tmp")
        tmp.bm.to_mesh(me)
        tmp.bm.free()
        p.bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    idx = p.mi(mat)
    for f in p.bm.faces:
        f.material_index = idx


FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
ENGRAVE_DEPTH = 1.0
LOGO_SIZE, LOGO_DEPTH = 26.0, 1.5         # shoulder logo height / inlay depth (mm)


def text_mesh(text, size, thickness, spacing=1.0):
    """Solid text mesh (glyphs in XY, extruded +/- thickness/2 in Z), centred on the origin."""
    cu = bpy.data.curves.new(PREFIX + "txt", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = thickness / 2
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = spacing
    if os.path.exists(FONT_PATH):
        cu.font = bpy.data.fonts.load(FONT_PATH, check_existing=True)
    ob = bpy.data.objects.new(PREFIX + "txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return me


def engrave_on_cylinder(target, name, lines, angle, radius=BODY_R, depth=ENGRAVE_DEPTH):
    """Engrave text wrapped around a vertical cylinder. lines = [(text, size, z, spacing)].
    angle 0 = front (-Y), PI = back; text reads correctly from outside."""
    def build(p):
        idx = p.mi(W)
        for text, size, zc, spacing in lines:
            t = depth + 1.0                      # pokes 1 mm out so the cut is clean
            me = text_mesh(text, size, t, spacing)
            tmp = bmesh.new()
            tmp.from_mesh(me)
            bpy.data.meshes.remove(me)
            bmesh.ops.remove_doubles(tmp, verts=tmp.verts[:], dist=1e-4)
            for v in tmp.verts:
                x, y, z = v.co
                r = radius - depth + t / 2 + z
                th = angle + x / radius
                v.co = (r * math.sin(th), -r * math.cos(th), zc + y)
            for f in tmp.faces:
                f.material_index = idx
            me2 = bpy.data.meshes.new("tmp")
            tmp.to_mesh(me2)
            tmp.free()
            p.bm.from_mesh(me2)
            bpy.data.meshes.remove(me2)
    cut(target, helper(name, build))


def build_body(c):
    # ---- shell
    shell = printed("P_Body_Shell", c, lambda p: p.ring(
        BODY_RI, BODY_R, BODY_Z1 - BODY_Z0, (0, 0, (BODY_Z0 + BODY_Z1) / 2), W, segs=128),
        W, "Upright, bottom down. Window tops are chamfered - no supports. 3 walls, 15% infill.",
        "Bottom deck glues up against the inner lip. Top deck screws to the 4 tabs (M3 inserts).")

    def tabs(p):
        for ang in (0, 90, 180, 270):
            rz = Matrix.Rotation(math.radians(ang), 4, "Z")
            q = Part("tmp")  # build one tab at +X then rotate its verts
            tbox(q, (72.2, 0, 268), 2.6, 11, (67.25, 0, 286), 12.5, 11, W)   # buried 1.5 mm in the wall
            for v in q.bm.verts:
                v.co = rz @ v.co
            bmesh.ops.recalc_face_normals(q.bm, faces=q.bm.faces[:])
            me = bpy.data.meshes.new("tmp")
            q.bm.to_mesh(me)
            q.bm.free()
            p.bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    union(shell,
          helper("Shell_Lip", lambda p: p.ring(BODY_RI - 3, BODY_RI + 0.5, 2, (0, 0, 85), W,
                                               segs=128)),
          helper("Shell_Tabs", tabs))
    tab_pts = [(66.5, 0, BODY_Z1 - 4), (-66.5, 0, BODY_Z1 - 4), (0, 66.5, BODY_Z1 - 4),
               (0, -66.5, BODY_Z1 - 4)]
    win = lambda name, w, h, y, z, ch=20: helper(  # noqa: E731
        name, lambda p: prism(p, window_pts(w, h, ch), -30, 60, W), (0, y, z), (PI / 2, 0, 0))
    cut(shell,
        win("Rear_Window", 98, 96, 60, 191, 12),     # clears the Jetson's 40-pin header
        win("Front_Upper_Window", 80, 80, -60, 198),
        win("Front_Lower_Window", 72, 58, -60, 119),
        insert_holes("Shell_Tab_Inserts", [(x, y, BODY_Z1 - 4) for x, y, _ in tab_pts],
                     M3_INSERT_R, 6.5),
        *[helper(f"Shoulder_Bore_{s}", lambda p, sd=sd: p.cyl(
            10.4, 14, (sd * BODY_R, SHOULDER_Y, SHOULDER_Z), W, axis="X"))
          for s, sd in (("L", -1), ("R", 1))])

    engrave_on_cylinder(shell, "Text_LU3", [("LU-3", 20, 250, 1.05)], 0.0)
    engrave_on_cylinder(shell, "Text_Lumalien", [("LUMALIEN", 12, 128, 1.05),
                                                 ("ROBOTICS", 8, 111, 1.3)], PI)
    add_rails(shell, "Rack", -20, -17, 155, 236)
    add_rails(shell, "Jetson_Plate", 37, 40, 145, 232)

    # ---- bands, pillars
    printed("P_Body_Band_Bottom", c, lambda p: p.ring(BODY_R + 0.2, BODY_R + 1.7, 6,
                                                      (0, 0, 87), PU, segs=128),
            PU, "Flat.", "Slides over the shell bottom; glue.")
    printed("P_Body_Band_Top", c, lambda p: p.ring(BODY_R + 0.2, BODY_R + 1.7, 8,
                                                   (0, 0, 266), PU, segs=128),
            PU, "Flat.", "Slides over the shell top; glue.")

    def pillars(p):
        for sx in (-1, 1):
            p.box((4, 7, 80), (sx * 44, -61, 198), PU)
            p.box((4, 6, 93), (sx * 51, 57, 189.5), PU)
    pil = printed("P_Window_Pillars", c, pillars, PU,
                  "Flat outer face down (4 pieces).", "Inner face is curved to the shell; glue.",
                  qty=1)
    cut(pil, helper("Shell_Envelope_Pillars", lambda p: p.cyl(BODY_R, 260, (0, 0, 185), W,
                                                             segs=128)))

    # ---- bottom deck
    bdeck = printed("P_Bottom_Deck", c, lambda p: p.cyl(DECK_R, 4, (0, 0, BODY_Z0 + 2), BK,
                                                       segs=128),
                    BK, "Flat, walls up.",
                    "Glued inside the shell bottom against the lip. Walls locate the bank and "
                    "AA pack; zip-tie the AA pack through the side slots. Center strut screws "
                    "up from below (2x M3x10).")

    def walls(p):
        z = BODY_Z0 + 4 + 4
        p.box((75, 2, 8), (0, -15.5, z), BK)          # bank tray
        p.box((75, 2, 8), (0, 15.5, z), BK)
        for sx in (-1, 1):
            p.box((2, 28.8, 8), (sx * 37.5, 0, z), BK)
            p.box((2, 20, 8), (sx * 35.55, -38, z), BK)   # AA pack sides
        p.box((60, 2, 8), (0, -25.8, z), BK)          # AA pack back
    union(bdeck, helper("Deck_Walls", walls))

    def bdeck_holes(p):
        for sx in (-1, 1):
            p.cyl(M3_CLEAR_R, 10, (sx * 8, CASTER_Y, BODY_Z0 + 2), W)
            p.box((3, 5, 10), (sx * 38.8, -38, BODY_Z0 + 2), W)   # AA zip-tie slots
    cut(bdeck, helper("Bottom_Deck_Holes", bdeck_holes))

    # ---- top deck + mast (one print)
    tdeck = printed("P_Top_Deck_Mast", c, lambda p: p.cyl(DECK_R, 4, (0, 0, BODY_Z1 - 2), W,
                                                         segs=128),
                    W, "Deck down, mast up (flare at the top is 45 deg).",
                    "Screws to the shell tabs (4x M3x8). MG90S hangs under it with its own "
                    "screws. Mast is fixed - the head turns around it.")
    union(tdeck,
          helper("Mast_Tube", lambda p: p.ring(MAST_R_IN, MAST_R_OUT, MAST_TUBE_TOP - 286.5,
                                               (0, 0, (MAST_TUBE_TOP + 286.5) / 2), W)),
          helper("Mast_Thrust_Flange", lambda p: p.cyl(13, 3, (0, 0, BODY_Z1 + 1), W)))
    sx0, sy0 = SERVO_XY

    def tdeck_holes(p):
        p.box((23.4, 12.8, 12), (sx0 - 5.4, sy0, BODY_Z1 - 2), W)      # servo body
        for dx in (-13.9, 13.9):
            p.cyl(SERVO_PILOT_R, 10, (sx0 - 5.4 + dx, sy0, BODY_Z1 - 2), W, segs=12)
        p.box((24, 9, 12), (-32, -12, BODY_Z1 - 2), W)                 # head cables
        for x in (15, 49):
            p.box((2.6, 5, 12), (x, -22, BODY_Z1 - 2), W)   # zip-tie for the C1 adapter below
        for x, y, _ in tab_pts:
            p.cyl(M3_CLEAR_R, 12, (x, y, BODY_Z1 - 2), W, segs=16)
    cut(tdeck,
        helper("Mast_Bore", lambda p: p.cyl(MAST_R_IN, 70, (0, 0, 311), W)),
        helper("Top_Deck_Holes", tdeck_holes))

    # ---- hip blocks (inside the shell at the shoulders)
    for s, sd in (("L", -1), ("R", 1)):
        hb = printed(f"P_Hip_Block_{s}", c, lambda p: p.box(
            (14.5, 37.3, 40), (sd * 65.25, SHOULDER_Y + 1.35, SHOULDER_Z), BK),
            BK, "Stand on the flat inner face (bore vertical).",
            "Glued inside the shell. Shoulder axle slides through; M3 set screw (insert on top) "
            "locks it so the leg can come off.")
        cut(hb, outside_trim(f"Hip_Trim_{s}"),
            helper(f"Hip_Bore_{s}", lambda p: p.cyl(10.2, 40, (sd * 65, SHOULDER_Y, SHOULDER_Z),
                                                    W, axis="X")),
            insert_holes(f"Hip_SetScrew_{s}", [(sd * 65, SHOULDER_Y, SHOULDER_Z + 20)],
                         M3_INSERT_R, 11))

    # ---- Jetson plate
    jp = printed("P_Jetson_Plate", c, lambda p: p.box((124, 3, 87), (0, 38.5, 188.5), BK),
                 BK, "Flat, standoffs up.",
                 "Slides down into rails on the shell wall (glue optional). 4x M2 inserts in "
                 "the 6 mm standoffs (86 x 58 pattern - "
                 "measure your Jetson first). Centre cut-out for airflow and cables.")
    jholes = [(sx * 43, 46, 190 + sz * 29) for sx in (-1, 1) for sz in (-1, 1)]
    union(jp, helper("Jetson_Standoffs", lambda p: [p.cyl(3.5, 7, (x, 42.5, z), W, axis="Y")
                                                    for x, _, z in jholes]))
    cut(jp, outside_trim("Jetson_Plate_Trim", BODY_RI - 0.3),
        helper("Jetson_Plate_Window", lambda p: p.box((50, 10, 40), (0, 38.5, 190), W)),
        insert_holes("Jetson_Inserts", jholes, M2_INSERT_R, 6, axis="Y"))

    # ---- board rack
    rk = printed("P_Board_Rack", c, lambda p: p.box((140, 3, 81), (0, -18.5, 195.5), BK),
                 BK, "Flat, standoffs up.",
                 "Slides down into rails on the shell wall (glue optional). Motor Bonnet + "
                 "PCA9685 on 22 mm standoffs (M2 inserts). "
                 "Slots: jumpers behind the Bonnet, motor wires at the sides, 2 zip-ties hold "
                 "the power bank.")
    bpts = [(sx * 29, -42, 215 + sz * 11.5) for sx in (-1, 1) for sz in (-1, 1)]
    ppts = [(sx * 27.5, -42, 175 + sz * 9.5) for sx in (-1, 1) for sz in (-1, 1)]
    union(rk, helper("Rack_Standoffs", lambda p: [p.cyl(2.8, 23, (x, -30.5, z), W, axis="Y")
                                                  for x, _, z in bpts + ppts]))

    def rack_holes(p):
        p.box((44, 10, 10), (0, -18.5, 226), W)                   # jumpers to the Jetson
        for sx in (-1, 1):
            p.box((16, 10, 30), (sx * 58, -18.5, 200), W)         # motor wires
            for z in (158, 233.5):
                p.box((2.6, 10, 5), (sx * 40.5, -18.5, z), W)     # bank zip-ties
    cut(rk, outside_trim("Rack_Trim", BODY_RI - 0.3), helper("Rack_Holes", rack_holes),
        insert_holes("Rack_Inserts", bpts + ppts, M2_INSERT_R, 6, axis="Y", sign=-1))

    # ---- LiDAR crown (floor + ring)
    cr = printed("P_Lidar_Crown", c, lambda p: p.cyl(CROWN_R_OUT, 3, (0, 0, MAST_TOP + 1.5),
                                                    PU, segs=64),
                 PU, "Floor down.",
                 "Glued onto the mast cap. The ring centres the C1; drill its base holes "
                 "after measuring (or zip-tie through the vents). Top stays below the scan "
                 "window.")
    cap = printed("P_Mast_Cap", c, lambda p: cone(p, 14.5, 16, MAST_TOP - 321,
                                                  (0, 0, (MAST_TOP + 321) / 2), BK),
                  BK, "Wide end down.",
                  "Slides onto the mast AFTER the head (hub gear, turntable, collar, dome) is on, "
                  "held by an M2 set screw (insert in the side). Loosen it to lift the head off.")
    cut(cap, helper("Cap_Socket", lambda p: p.cyl(MAST_R_OUT + 0.2, 14, (0, 0, 327), W)),
        helper("Cap_Cable_Hole", lambda p: p.cyl(MAST_R_IN, 12, (0, 0, MAST_TOP - 2), W)),
        insert_holes("Cap_SetScrew_Insert", [(15.2, 0, 326)], M2_INSERT_R, 4, axis="X"),
        helper("Cap_SetScrew_Clear", lambda p: p.cyl(M2_CLEAR_R, 6, (12.2, 0, 326), W,
                                                     axis="X")))
    union(cr, helper("Crown_Ring", lambda p: p.ring(
        CROWN_R_IN, CROWN_R_OUT - 0.05, CROWN_TOP - MAST_TOP - 2.9,
        (0, 0, (CROWN_TOP + MAST_TOP + 2.9) / 2), W, segs=64)))

    def crown_vents(p):
        for k in range(6):
            a = math.radians(30 + 60 * k)
            q = Part("tmp")
            q.box((7, 10, 16), (0, -CROWN_R_OUT, 352), W)
            rz = Matrix.Rotation(a, 4, "Z")
            for v in q.bm.verts:
                v.co = rz @ v.co
            me = bpy.data.meshes.new("tmp")
            q.bm.to_mesh(me)
            q.bm.free()
            p.bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    cut(cr, helper("Crown_Center_Hole", lambda p: p.cyl(MAST_R_IN, 20, (0, 0, MAST_TOP), W)),
        helper("Crown_Cable_Slot", lambda p: p.box((8, 30, 8), (0, 18, MAST_TOP + 1.5), W)),
        helper("Crown_Vents", crown_vents))


def build_head(c):
    env_cyl = helper("Head_Env_Collar", lambda p: p.cyl(BODY_R, 32, (0, 0, DOME_Z0 - 14), W,
                                                        segs=128))
    env_dome = helper("Head_Env_Dome", lambda p: dome(p, BODY_R, DOME_ZS, DOME_Z0, W, cap=True))
    band_env = helper("Head_Band_Env", lambda p: p.ring(BODY_R - 1, BODY_R + 1.9, 5.4,
                                                        (0, 0, 302.5), W, segs=128))
    lens_hole = helper("Lens_Hole", lambda p: p.cyl(12, 40, (0, -72, EYE_Z), W, axis="Y"))
    rz = Matrix.Rotation(IND_AZ, 4, "Z")
    wire_hole = helper("Indicator_Wire_Hole",
                       lambda p: p.cyl(6, 40, (0, -72, IND_Z), W, axis="Y"), rot=(0, 0, IND_AZ))

    col = printed("P_Head_Collar", c, lambda p: p.ring(
        BODY_RI, BODY_R, DOME_Z0 - HEAD_Z0, (0, 0, (HEAD_Z0 + DOME_Z0) / 2), W, segs=128),
        W, "Upright.", "Glued around the turntable; dome lip glues inside the top.")
    cut(col, lens_hole, wire_hole)
    printed("P_Head_Band", c, lambda p: p.ring(BODY_R + 0.2, BODY_R + 1.7, 5, (0, 0, 302.5),
                                               PU, segs=128),
            PU, "Flat.", "Slides over the collar; glue.")

    dm = printed("P_Dome", c, lambda p: dome(p, BODY_R, DOME_ZS, DOME_Z0, W),
                 W, "Base down. Tree supports inside for the top ~15 mm around the opening.",
                 "Lip glues into the collar. Turns with the head; the LiDAR crown sits in the "
                 "opening with a 2 mm gap.")
    sol = dm.modifiers.new("shell", "SOLIDIFY")
    sol.thickness = BODY_WALL
    sol.offset = -1.0
    sol.use_even_offset = True
    union(dm, helper("Dome_Lip", lambda p: p.ring(BODY_RI - 2.6, BODY_RI - 0.2, 5.5,
                                                  (0, 0, DOME_Z0 - 2.25), W, segs=128)),
          helper("Dome_Lip_Bond", lambda p: p.ring(BODY_RI - 2.6, BODY_RI + 1.0, 2.8,
                                                   (0, 0, DOME_Z0 + 1.6), W, segs=128)))
    cut(dm, helper("Crown_Opening", lambda p: p.cyl(DOME_OPENING_R, 40, (0, 0, 365), W)),
        lens_hole, wire_hole)

    eye = printed("P_Eye_Pod", c, lambda p: p.cyl(24, 22, (0, -73, EYE_Z), PU, axis="Y",
                                                   segs=64),
                  PU, "Front face down.", "Back is shaped to the head; glue.")
    cut(eye, env_cyl, env_dome, band_env,
        helper("Eye_Bore", lambda p: p.cyl(12, 40, (0, -72, EYE_Z), W, axis="Y")))
    printed("P_Lens_Hood", c, lambda p: p.ring(9, 13, 4, (0, 0, 2), BK, segs=48),
            BK, "Flat.", "Glue to the eye face around the lens.", loc=(0, -84, EYE_Z),
            rot=(PI / 2, 0, 0))

    ind = printed("P_Indicator_Pod", c, lambda p: p.cyl(21, 18, (0, -76, IND_Z), PU, axis="Y",
                                                         segs=64),
                  PU, "Front face down.",
                  "NeoPixel ring glues into the recess, wires through the centre hole.",
                  rot=(0, 0, IND_AZ))
    cut(ind, env_cyl, env_dome, band_env, wire_hole,
        helper("Indicator_Recess", lambda p: p.cyl(19.5, 12, (0, -86, IND_Z), W, axis="Y"),
               rot=(0, 0, IND_AZ)))
    printed("P_Indicator_Lens", c, lambda p: p.cyl(19.2, 2, (0, 0, 1), CL, segs=64),
            CL, "Flat.", "Clear disc over the ring; glue at the edge.",
            loc=rz @ Vector((0, -83.5, IND_Z)), rot=(PI / 2, 0, IND_AZ))

    # ---- turntable + camera bracket (one print), hub gear (glued under it)
    tt = printed("P_Turntable", c, lambda p: p.cyl(TT_R, TT_T, (0, 0, TT_Z0 + TT_T / 2), BK,
                                                   segs=128),
                 BK, "Disc down, bracket up.",
                 "Rotates around the mast. Collar glues around its edge, hub gear glues "
                 "underneath. Camera on 4x M2 inserts (34 mm pattern).")
    cam_pts = [(sx * 17, -56.45, EYE_Z + sz * 17) for sx in (-1, 1) for sz in (-1, 1)]
    union(tt,
          helper("Camera_Bracket", lambda p: p.box((44, 5, 41.1), (0, -49.5, 320.95), W)),
          helper("Camera_Bosses", lambda p: [p.cyl(3.2, 4.6, (x, -54.2, z), W, axis="Y")
                                             for x, _, z in cam_pts]))
    ix, iy = math.sin(IND_AZ) * 55, -math.cos(IND_AZ) * 55

    def tt_holes(p):
        p.box((14, 8, 12), (0, -49.5, 306), W)                   # camera cable notch
        p.box((16, 8, 8), (-20, -38, TT_Z0 + 1.5), W)            # camera cable to body
        p.cyl(5, 8, (ix, iy, TT_Z0 + 1.5), W)                    # NeoPixel wires
    cut(tt, helper("Turntable_Bore", lambda p: p.cyl(10.3, 60, (0, 0, 310), W)),
        helper("Turntable_Holes", tt_holes),
        insert_holes("Camera_Inserts", cam_pts, M2_INSERT_R, 6, axis="Y", sign=-1))

    hg = printed("P_Hub_Gear", c, lambda p: prism(p, involute_pts(GEAR_M, GEAR_N),
                                                  HUB_GEAR_Z[0], HUB_GEAR_Z[1] - HUB_GEAR_Z[0],
                                                  BK),
                 BK, "Flat.", "24T m1.25. Glue under the turntable; the pair slides down the "
                              "mast (before the mast cap) and rests on the thrust flange - a dab "
                              "of grease helps.")
    cut(hg, helper("Hub_Gear_Bore", lambda p: p.cyl(10.3, 20, (0, 0, 295), W)))
    sg = printed("P_Servo_Gear", c, lambda p: prism(
        p, involute_pts(GEAR_M, GEAR_N, *SERVO_XY, phase=PI / GEAR_N),
        SERVO_GEAR_Z[0], SERVO_GEAR_Z[1] - SERVO_GEAR_Z[0], PU),
        PU, "Flat.", "24T m1.25 (1:1 -> head turns +/-90). Press onto the MG90S spline "
                     "(4.6 mm hole) and add a drop of glue.")
    cut(sg, helper("Servo_Spline_Hole", lambda p: p.cyl(2.3, 10, (*SERVO_XY, 296), W, segs=24)))


def build_legs(c):
    for s, sd in (("L", -1), ("R", 1)):
        x = sd * LEG_X
        spk_loc = (sd * (LEG_X + LEG_T / 2 - 20.5), leg_y(SPK_Z), SPK_Z)
        spk_rot = (LEG_TILT, sd * PI / 2, 0)
        channel = helper(f"Leg_Wire_Channel_{s}", lambda p: tbox(
            p, (sd * (LEG_X - LEG_T / 2 + 5), AXLE_Y, 35), 6, 14,
            (sd * (LEG_X - LEG_T / 2 + 5), leg_y(244), 244), 6, 14, W))

        leg = printed(f"P_Leg_{s}", c, lambda p: leg_section(p, x, LEG_SOCKET_Z, LEG_TOP_Z + 5,
                                                             0, W),
                      W, "Upright on the socket end (194 mm tall) so the rounded top prints "
                         "cleanly; speaker pocket roof is a 46 mm bridge - fine on the A1. Brim "
                         "recommended.",
                      "Bottom glues into the foot socket. Speaker drops into the pocket and is "
                      "held by 2 zip-ties in the side grooves. Wire channel runs from the foot "
                      "up into the shoulder bore.")

        top_z = LEG_TOP_Z + 5
        bevel_edges(leg, lambda a, b: 1.0 if min(a.z, b.z) > top_z - 0.1 else
                    (0.3 if abs(a.z - b.z) > 1 else 0.0), width=10)

        def zip_grooves(p):
            for gx in (-41, 41):
                for gy in (-24.2, 24.2):
                    p.box((4.5, 2.2, 36), (gx, gy, 5.5), W)
        cut(leg,
            helper(f"Speaker_Pocket_{s}", lambda p: p.box((101.5, 46.5, 40.5), (0, 0, 19.75), W),
                   spk_loc, spk_rot, "YXZ"),
            helper(f"Speaker_Zip_Grooves_{s}", zip_grooves, spk_loc, spk_rot, "YXZ"),
            channel,
            helper(f"Leg_Shoulder_Bore_{s}", lambda p: p.cyl(10.2, 40, (x, SHOULDER_Y,
                                                                        SHOULDER_Z), W,
                                                             axis="X")))

        band = printed(f"P_Ankle_Band_{s}", c, lambda p: leg_section(p, x, 80, 92, 2.5, PU),
                       PU, "Flat.", "Slides down the leg onto the foot; glue.")
        cut(band, helper(f"Ankle_Band_Hole_{s}", lambda p: leg_section(p, x, 78, 94, 0.2, W)))
        sh = printed(f"P_Shoulder_{s}", c, lambda p: p.cyl(
            22, 6, (sd * (LEG_X + LEG_T / 2 + 3), SHOULDER_Y, SHOULDER_Z), PU, axis="X",
            segs=64), PU, "Flat back down (logo recess up).",
            "Glue over the axle end on the leg's outer face. White logo inlay glues into the "
            "recess.")
        face_x = sd * (LEG_X + LEG_T / 2 + 6)          # outer face of the disc

        def to_world(u, v, w, face_x=face_x, sd=sd):
            # u -> viewer's right, v -> up, w -> out of the disc (reads correctly from outside)
            return (face_x - sd * LOGO_DEPTH + sd * w, SHOULDER_Y + sd * u, SHOULDER_Z + v)
        cut(sh, helper(f"Logo_Recess_{s}", lambda p: logo_on_plane(
            p, LOGO_SIZE, 0.15, 0, LOGO_DEPTH + 1, to_world, W)))
        printed(f"P_Logo_Inlay_{s}", c, lambda p: logo_on_plane(
            p, LOGO_SIZE, 0.0, 0, LOGO_DEPTH, to_world, W),
            W, "Flat (2 small pieces: the L and the triangle).",
            "Lumalien logo. Glue into the shoulder disc recess (0.15 mm gap).")
        printed(f"P_Shoulder_Axle_{s}", c, lambda p: p.ring(AXLE_R_IN, AXLE_R_OUT, 50,
                                                            (0, 0, 0), BK, segs=48),
                BK, "Upright.", "Glued into the leg, set-screwed in the hip block. Wires run "
                                "through the middle.",
                loc=(sd * 85, SHOULDER_Y, SHOULDER_Z), rot=(0, PI / 2, 0))

        # ---- foot
        foot = printed(f"P_Foot_{s}", c, lambda p: tbox(
            p, (x, AXLE_Y, 6), 52, 92, (x, AXLE_Y, 78), 40, 62, W),
            W, "Bottom down.",
            "N20 slides in from the inner side and is clamped by its bracket (bracket screws "
            "up from below through the slots, nuts inside). Leg glues into the top socket.")
        # rounded top (4 mm - the rim around the leg socket is only 3-6 mm), 3 mm corners,
        # 1 mm on the bed edges to hide first-layer squish
        bevel_edges(foot, lambda a, b: 1.0 if min(a.z, b.z) > 77.9 else
                    (0.75 if abs(a.z - b.z) > 1 else 0.25), width=4, segs=4)
        bx = sd * BRACKET_X

        def bracket_slots(p):
            for dy in (-BRACKET_HOLE_DY, BRACKET_HOLE_DY):
                p.box((2.4, 5.4, 25), (bx, AXLE_Y + dy, 17.5), W)

        def bracket_recesses(p):                                               # screw heads
            for dy in (-BRACKET_HOLE_DY, BRACKET_HOLE_DY):
                p.box((5.2, 8.2, 18), (bx, AXLE_Y + dy, 14), W)
        cut(foot,
            helper(f"Wheel_Well_{s}", lambda p: p.box((39, 72, 73), (sd * 115.5, AXLE_Y, 31.5),
                                                      W)),
            helper(f"Motor_Bay_{s}", lambda p: p.box((37.5, 13, 11),
                                                     (sd * 78.75, AXLE_Y, MOTOR_FLOOR_Z + 5.5), W)),
            helper(f"Bracket_Bay_{s}", lambda p: p.box((13, 26, 12),
                                                       (bx, AXLE_Y, MOTOR_FLOOR_Z + 6), W)),
            helper(f"Bracket_Slots_{s}", bracket_slots),
            helper(f"Bracket_Recesses_{s}", bracket_recesses),
            helper(f"Leg_Socket_{s}", lambda p: leg_section(p, x, LEG_SOCKET_Z - 0.1, 82, 0.25,
                                                            W)),
            channel)

        # ---- wheel
        wl, wr = (sd * 104, AXLE_Y, AXLE_Z), (0, PI / 2, 0)
        hub = printed(f"P_Wheel_Hub_{s}", c, lambda p: p.cyl(26.05, 10, (0, 0, 0), PU, segs=96),
                      PU, "Flat.", "3 mm D-bore press-fits the N20 shaft (glue if loose). "
                                   "Tire stretches/glues over the rim.", loc=wl, rot=wr)

        def lighten(p):
            for k in range(5):
                a = 2 * PI * k / 5
                p.cyl(5.5, 14, (15.5 * math.cos(a), 15.5 * math.sin(a), 0), W, segs=32)
        cut(hub, helper(f"D_Bore_{s}", lambda p: prism(p, d_bore_pts(), -8, 16, W), wl, wr),
            helper(f"Hub_Lightening_{s}", lighten, wl, wr))
        printed(f"P_Wheel_Tire_{s}", c, lambda p: p.ring(26.0, WHEEL_R, WHEEL_W, (0, 0, 0), BK,
                                                         segs=96),
                BK, "Flat. TPU 95A recommended (black PLA works on hard floors).",
                "64 mm OD.", loc=wl, rot=wr)

    # ---- center foot + strut (one print)
    cf = printed("P_Center_Foot", c, lambda p: tbox(
        p, (0, CASTER_Y, 22.9), 56, 56, (0, CASTER_Y, 58), 44, 44, W),
        W, "Bottom down.", "Ball caster sticks (and optionally screws) to the flat underside. "
                           "Strut top screws to the bottom deck: 2x M3 inserts.")
    bevel_edges(cf, lambda a, b: 1.0 if min(a.z, b.z) > 57.9 else
                (0.75 if abs(a.z - b.z) > 1 else 0.25), width=4, segs=4)
    union(cf, helper("Center_Strut", lambda p: p.box((30, 24, 25), (0, CASTER_Y, 67.5), W)))
    cut(cf, insert_holes("Center_Strut_Inserts", [(sx * 8, CASTER_Y, BODY_Z0)
                                                  for sx in (-1, 1)], M3_INSERT_R, 7))


def build_electronics(c):
    place(P["jetson"](c, (0, 0, 0)), (0, JETSON_Y, 190), (-PI / 2, PI, 0))
    place(P["power_bank"](c, (0, 0, 0)), (0, -14, 163), (0, PI / 2, PI / 2))
    place(P["aa_pack"](c, (0, 0, 0)), (0, -27, 117), (PI / 2, 0, 0))
    place(P["motor_bonnet"](c, (0, 0, 0)), (0, -42, 215), (PI / 2, 0, 0))
    place(P["pca9685"](c, (0, 0, 0)), (0, -42, 175), (PI / 2, 0, 0))
    place(P["usb_audio"](c, (0, 0, 0)), (2.5, 59.5, 121.5), (0, PI / 2, 0))
    place(P["usb_mic"](c, (0, 0, 0)), (-10, 56.0, 147.5), (-PI / 2, 0, 0))
    place(P["mg90s"](c, (0, 0, 0), "MG90S_Head"), (SERVO_XY[0] - 5.4, SERVO_XY[1], 267.6))
    place(P["arducam"](c, (0, 0, 0)), (0, -57.2, 301))
    place(neopixel_ring(c, (0, 0, 0)), Matrix.Rotation(IND_AZ, 4, "Z") @ Vector((0, -80, IND_Z)),
          (PI / 2, 0, IND_AZ))
    lidar = place(P["lidar"](c, (0, 0, 0)), (0, 0, LIDAR_BASE))
    for ch in lidar.children:
        ch.hide_viewport = True
    place(P["lidar_adapter"](c, (0, 0, 0)), (32, -22, BODY_Z1 - 4), (PI, 0, 0))  # under deck
    place(P["ball_caster"](c, (0, 0, 0), "Ball_Caster"), (0, CASTER_Y, 0))
    for s, sd in (("L", -1), ("R", 1)):
        place(P["gearmotor"](c, (0, 0, 0), f"N20_Motor_{s}", 0.0),
              (sd * 97, AXLE_Y, AXLE_Z), (0, 0, 0 if sd > 0 else PI))
        place(P["speaker"](c, (0, 0, 0), f"Speaker_{s}"),
              (sd * (LEG_X + LEG_T / 2 - 20.5), leg_y(SPK_Z), SPK_Z),
              (LEG_TILT, sd * PI / 2, 0), "YXZ")


def build_droid():
    clear_root()
    root = get_coll(ROOT, bpy.context.scene.collection)
    for old in ("Cutters",):
        oc = bpy.data.collections.get(old)
        if oc and not oc.objects:
            bpy.data.collections.remove(oc)
    _C["help"] = get_coll("Helpers", root)
    build_body(get_coll("Printed - Body", root))
    build_head(get_coll("Printed - Head", root))
    build_legs(get_coll("Printed - Legs & Feet", root))
    build_electronics(get_coll("Electronics (placed)", root))
    hw = get_coll("Hardware (not printed)", root)
    for s, sd in (("L", -1), ("R", 1)):
        mk(f"HW_Bumper_Pad_{s}", hw, lambda p: p.cyl(6.35, 3.5, (sd * LEG_X, 72, 4.25),
                                                    "Plastic_Black"),
           props={"notes": "12.7 x 3.5 mm bumper pad on the heel: anti-tip skid."})
    vl = bpy.context.view_layer.layer_collection
    for name in ("Helpers", "Droid Parts"):
        lc = find_layer_coll(vl, name)
        if lc:
            lc.hide_viewport = True
    smooth_all()
    return root


def smooth_all(angle=math.radians(35)):
    """Smooth shading on every mesh (Smooth by Angle modifier, last in the stack)."""
    obs = [o for c in (ROOT, "Droid Parts") if bpy.data.collections.get(c)
           for o in [*bpy.data.collections[c].objects,
                     *[x for ch in bpy.data.collections[c].children_recursive for x in ch.objects]]
           if o.type == "MESH" and not o.name.startswith("H_")]
    for ob in obs:
        if any(m.type == "NODES" and m.node_group and "Smooth by Angle" in m.node_group.name
               for m in ob.modifiers):
            continue
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob],
                                       selected_editable_objects=[ob]):
            bpy.ops.object.shade_auto_smooth(use_auto_smooth=True, angle=angle)


# ----------------------------------------------------------------------------- export

def printed_objects():
    root = bpy.data.collections[ROOT]
    return [o for c in root.children_recursive for o in c.objects if o.get("printed")]


def check_part(ob, dg):
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ob.matrix_world)
    bad = sum(1 for ed in bm.edges if not ed.is_manifold)
    vol = bm.calc_volume(signed=True)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) if bm.verts else (0, 0, 0)
    bm.free()
    e.to_mesh_clear()
    return bad, vol, dims


def write_stl(ob, dg, path):
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    me.calc_loop_triangles()
    mw = ob.matrix_world
    tris = [[mw @ me.vertices[i].co for i in t.vertices] for t in me.loop_triangles]
    with open(path, "wb") as f:
        f.write(b"Lumalien droid part".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            n = (b - a).cross(c - a)
            n = n.normalized() if n.length else n
            f.write(struct.pack("<12fH", *n, *a, *b, *c, 0))
    e.to_mesh_clear()
    return len(tris)


def export_stls(folder=None):
    folder = folder or os.path.join(os.path.dirname(bpy.data.filepath), "stl")
    os.makedirs(folder, exist_ok=True)
    dg = bpy.context.evaluated_depsgraph_get()
    rows, report = [], []
    for ob in sorted(printed_objects(), key=lambda o: o.name):
        bad, vol, dims = check_part(ob, dg)
        fits = max(dims) <= 256
        n = write_stl(ob, dg, os.path.join(folder, ob.name[2:] + ".stl"))
        report.append((ob.name, bad, round(vol / 1000, 1), tuple(round(d, 1) for d in dims),
                       fits, n))
        rows.append(f"| {ob.name[2:]} | {ob['colour']} | {ob['qty']} | "
                    f"{dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} | {ob['print']} | "
                    f"{ob['notes']} |")
    with open(os.path.join(folder, "PRINT_LIST.md"), "w", encoding="utf-8") as f:
        f.write("# Lumalien droid - print list\n\n"
                "All STLs are in mm, positioned as assembled - lay each flat in Bambu Studio "
                "as noted. Joints marked glue are 0.2 mm clearance fits.\n\n"
                "| Part | Colour | Qty | Size (mm) | Print | Notes |\n|---|---|---|---|---|---|\n")
        f.write("\n".join(rows) + "\n\n" + HARDWARE_MD)
    return report


HARDWARE_MD = """## Hardware

| Item | Qty | Where |
|---|---|---|
| M2 heat-set inserts (3.2 mm hole, check your kit) | 16 | Jetson plate 4, board rack 8, camera bracket 4 |
| M2 x 5 / x 8 screws | 16 | Jetson, Motor Bonnet, PCA9685, camera |
| M3 heat-set inserts (4.0 mm hole, check your kit) | 8 | Shell tabs 4, hip blocks 2 (set screws), center strut 2 |
| M3 x 8 button screws | 4 | Top deck to shell tabs |
| M3 x 10 screws | 4 | Hip block set screws 2, bottom deck to center strut 2 |
| N20 brackets + their screws/nuts | 2 | Feet |
| MG90S screws (in the servo bag) | 2 | Servo under the top deck |
| Zip-ties (~2.5 mm) | 8 | Speakers 4, power bank 2, AA pack 1, C1 adapter 1 |
| Bumper pads 12.7 x 3.5 | 2 | Heel anti-tip skids |
| Strong glue | - | All printed-to-printed joints |
"""


if __name__ == "__main__":
    build_droid()
