"""
Lumalien house droid - reference models of every purchased/owned part, for chassis design.

Run inside Blender (Scripting tab -> Run Script, or via Blender MCP):
    ns = {"__name__": "droid_parts"}
    exec(compile(open(r"<path>/build_parts.py").read(), "build_parts.py", "exec"), ns)
    ns["build_all"]()

Conventions
  * 1 Blender unit = 1 mm (scene unit scale 0.001) so STL exports drop straight into Bambu Studio.
  * Z up. Each part's origin is its bottom centre, except the gearmotors, whose origin is on the
    output-shaft axis at the gearbox face.
  * Orange faces = power connections. Gold discs = mounting-hole locations.
  * Every object carries custom properties (N panel -> Item... or Object Properties -> Custom
    Properties): dims_mm, source, confidence, notes. "approx" parts are placeholders - measure
    them with calipers and update the numbers below before printing mounts.
  * Re-running deletes and rebuilds everything inside the "Droid Parts" collection only.
"""
import math

import bmesh
import bpy
from mathutils import Matrix

ROOT = "Droid Parts"
PREFIX = "DP_"

MATS = {
    "PCB_Green": (0.05, 0.25, 0.10, 1),
    "PCB_Black": (0.03, 0.03, 0.035, 1),
    "PCB_Blue": (0.05, 0.12, 0.45, 1),
    "Plastic_Black": (0.02, 0.02, 0.02, 1),
    "Plastic_Grey": (0.35, 0.36, 0.38, 1),
    "Plastic_White": (0.85, 0.85, 0.82, 1),
    "Metal": (0.75, 0.75, 0.78, 1),
    "Gold": (0.83, 0.65, 0.20, 1),
    "Terminal_Green": (0.10, 0.55, 0.20, 1),
    "Lens": (0.01, 0.01, 0.03, 1),
    "Heatsink": (0.12, 0.12, 0.13, 1),
    "Power_Port": (1.0, 0.40, 0.0, 1),
    "Scan_Plane": (1.0, 0.1, 0.1, 1),
    "Label": (0.95, 0.95, 0.95, 1),
    "Brass": (0.72, 0.55, 0.25, 1),
    "Wire_Red": (0.75, 0.05, 0.05, 1),
    "Pin_Yellow": (0.90, 0.78, 0.10, 1),
}
METALLIC = {"Metal", "Gold", "Heatsink", "Brass"}


# ----------------------------------------------------------------------------- helpers

def get_mat(name):
    m = bpy.data.materials.get(PREFIX + name)
    if m is None:
        m = bpy.data.materials.new(PREFIX + name)
    c = MATS[name]
    m.diffuse_color = c
    try:
        m.use_nodes = True
    except Exception:
        pass
    bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if bsdf:
        bsdf.inputs["Base Color"].default_value = c
        bsdf.inputs["Metallic"].default_value = 1.0 if name in METALLIC else 0.0
        bsdf.inputs["Roughness"].default_value = 0.35 if name in METALLIC else 0.6
    m.metallic = 1.0 if name in METALLIC else 0.0
    return m


def get_coll(name, parent):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if name not in parent.children:
        parent.children.link(c)
    return c


class Part:
    """Accumulates primitives into one bmesh -> one object with per-face materials."""

    AXES = {
        "Z": Matrix.Identity(4),
        "X": Matrix.Rotation(math.pi / 2, 4, "Y"),
        "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
    }

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _tag(self, verts, mat):
        idx = self.mi(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = idx

    def box(self, size, center, mat):
        m = Matrix.Translation(center) @ Matrix.Diagonal((*size, 1.0))
        self._tag(bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)["verts"], mat)

    def cyl(self, r, h, center, mat, axis="Z", segs=32):
        m = Matrix.Translation(center) @ self.AXES[axis]
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                    radius1=r, radius2=r, depth=h, matrix=m)
        self._tag(res["verts"], mat)

    def rbox(self, w, d, h, rad, bottom_center, mat, segs=6):
        """Box with rounded vertical edges; bottom_center = (x, y, z0)."""
        cx, cy, z0 = bottom_center
        pts = []
        for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            ox, oy = cx + sx * (w / 2 - rad), cy + sy * (d / 2 - rad)
            for i in range(segs + 1):
                a = math.radians(a0 + 90 * i / segs)
                pts.append((ox + rad * math.cos(a), oy + rad * math.sin(a)))
        bot = [self.bm.verts.new((x, y, z0)) for x, y in pts]
        top = [self.bm.verts.new((x, y, z0 + h)) for x, y in pts]
        faces = [self.bm.faces.new(list(reversed(bot))), self.bm.faces.new(top)]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            faces.append(self.bm.faces.new((bot[i], bot[j], top[j], top[i])))
        idx = self.mi(mat)
        for f in faces:
            f.material_index = idx

    def ring(self, r_in, r_out, h, center, mat, segs=64):
        cx, cy, cz = center
        rings = []
        for r in (r_in, r_out):
            for z in (cz - h / 2, cz + h / 2):
                rings.append([self.bm.verts.new((cx + r * math.cos(2 * math.pi * i / segs),
                                                 cy + r * math.sin(2 * math.pi * i / segs), z))
                              for i in range(segs)])
        ib, it, ob, ot = rings
        idx = self.mi(mat)
        for i in range(segs):
            j = (i + 1) % segs
            for quad in ((it[i], ot[i], ot[j], it[j]), (ib[i], ib[j], ob[j], ob[i]),
                         (ob[i], ob[j], ot[j], ot[i]), (ib[i], it[i], it[j], ib[j])):
                self.bm.faces.new(quad).material_index = idx

    def build(self, coll, loc=(0, 0, 0), rot_z=0.0, props=None):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(PREFIX + self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(get_mat(m))
        ob = bpy.data.objects.new(self.name, me)
        ob.location = loc
        ob.rotation_euler.z = rot_z
        coll.objects.link(ob)
        for k, v in (props or {}).items():
            ob[k] = v
        return ob


def label(text, loc, coll, size=6):
    cu = bpy.data.curves.new(PREFIX + "lbl", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "TOP"
    cu.materials.append(get_mat("Label"))
    ob = bpy.data.objects.new("LBL_" + text.split("\n")[0][:40], cu)
    ob.location = loc
    coll.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------- parts

def jetson(coll, loc):
    """Jetson Orin Nano Super Developer Kit. I/O edge faces -Y."""
    p = Part("Jetson_Orin_Nano_Super_DevKit")
    W, D, FOOT, T = 100.0, 79.0, 3.4, 1.6
    top = FOOT + T
    holes = [(sx * 43, sy * 29) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in holes:
        p.cyl(3.0, FOOT, (x, y, FOOT / 2), "Plastic_Black")
    p.box((W, D, T), (0, 0, FOOT + T / 2), "PCB_Green")
    for x, y in holes:
        p.cyl(2.6, 0.1, (x, y, top + 0.05), "Gold")
    # module + heatsink + fan (fan top = 21 mm overall)
    p.box((66, 45, 4), (-12, 8, top + 2), "PCB_Black")
    p.box((62, 45, 12), (-12, 8, top + 4 + 6), "Heatsink")
    p.cyl(19, 0.4, (-12, 8, top + 16.2), "Plastic_Black")

    def io(w, d, h, x, mat):  # connector flush-ish with the -Y edge (1 mm overhang)
        p.box((w, d, h), (x, -40.5 + d / 2, top + h / 2), mat)

    io(9, 14, 11, -42, "Power_Port")    # DC jack 5.5 x 2.5 mm, 9-20 V
    io(19, 15, 5.5, -26, "Metal")       # DisplayPort
    io(14.5, 17.5, 15.6, -7, "Metal")   # 2x USB-A
    io(14.5, 17.5, 15.6, 10, "Metal")   # 2x USB-A
    io(16, 21, 13.5, 29, "Metal")       # RJ45
    io(9, 7.5, 3.2, 44, "Metal")        # USB-C (data only)
    # 40-pin header along the back edge
    p.box((51, 5.1, 2.5), (22, 35, top + 1.25), "Plastic_Black")
    p.box((50, 4, 6), (22, 35, top + 5.5), "Gold")
    return p.build(coll, loc, props={
        "dims_mm": "100 x 79 x 21 overall incl. feet and fan (NVIDIA)",
        "source": "https://developer.nvidia.com/embedded/jetson-developer-kits",
        "confidence": "outline verified; connector order/positions, heatsink footprint and "
                      "86 x 58 hole pattern approximate - measure before printing mounts",
        "notes": "Orange = DC jack (5.5 x 2.5 mm, 9-20 V). USB-C is data only. "
                 "Leave airflow above the fan.",
    })


def power_bank(coll, loc):
    p = Part("UGREEN_145W_25000mAh_PowerBank_90597A")
    L, W, H = 158.0, 72.0, 28.0
    p.rbox(L, W, H, 8, (0, 0, 0), "Plastic_Grey")
    p.box((0.8, 9.0, 3.4), (-L / 2 - 0.2, -20, H / 2), "Power_Port")   # USB-C1 -> Jetson
    p.box((0.8, 9.0, 3.4), (-L / 2 - 0.2, -6, H / 2), "Plastic_Black")  # USB-C2
    p.box((0.8, 13.0, 5.8), (-L / 2 - 0.2, 14, H / 2), "Plastic_Black")  # USB-A
    return p.build(coll, loc, props={
        "dims_mm": "~158 x 72 x 28 (retail listings disagree - measure)",
        "source": "https://us.ugreen.com/products/ugreen-145w-power-bank-for-laptop",
        "confidence": "approx",
        "notes": "Orange = USB-C1 (15 V / 3 A to the Jetson). Heaviest part (~0.5-0.7 kg): "
                 "mount low and between the wheels. Keep the port end reachable for charging.",
    })


def pd_cable(coll, loc):
    p = Part("Adafruit_5451_USB-C_PD_to_Barrel_15V_plugs")
    # USB-C plug (y=+15) and 5.5 x 2.5 barrel plug (y=-15), both pointing -X
    p.box((22, 12, 7), (0, 15, 3.5), "Plastic_Black")
    p.box((6.5, 8.3, 2.5), (-14.25, 15, 3.5), "Metal")
    p.cyl(2.0, 15, (18.5, 15, 3.5), "Plastic_Black", axis="X")
    p.cyl(5.0, 22, (0, -15, 5), "Plastic_Black", axis="X")
    p.cyl(2.75, 9.5, (-15.75, -15, 5), "Power_Port", axis="X")
    p.cyl(2.0, 15, (18.5, -15, 5), "Plastic_Black", axis="X")
    return p.build(coll, loc, props={
        "dims_mm": "plug bodies approx; barrel 5.5 OD / 2.5 ID, centre positive",
        "source": "https://www.adafruit.com/product/5451",
        "confidence": "approx (plug overmolds)",
        "notes": "Straight plugs: leave ~40 mm clear in front of the Jetson DC jack and the "
                 "bank's USB-C1 for plug + cable bend.",
    })


def lidar(coll, loc):
    p = Part("RPLIDAR_C1")
    S, H = 55.6, 41.3
    p.rbox(S, S, 26, 10, (0, 0, 0), "Plastic_Black")
    p.rbox(S - 1.0, S - 1.0, 10, 9.5, (0, 0, 26), "Lens")      # scan window band
    p.rbox(S, S, H - 36, 10, (0, 0, 36), "Plastic_Black")
    ob = p.build(coll, loc, props={
        "dims_mm": "55.6 x 55.6 x 41.3, 110 g (Waveshare)",
        "source": "https://www.waveshare.com/product/modules/sensors/rplidar-c1.htm",
        "confidence": "outline verified; window band height, scan-plane height (~31 mm) and "
                      "base hole pattern approximate - check the Slamtec drawing",
        "notes": "Mount level, on top, with nothing inside the window band's 360 deg view.",
    })
    sp = Part("RPLIDAR_C1_scan_plane_approx")
    sp.ring(29, 42, 0.2, (0, 0, 31), "Scan_Plane")
    child = sp.build(coll, props={"notes": "Visual aid only: approximate 2D scan plane."})
    child.parent = ob
    child.hide_render = True
    return ob


def lidar_adapter(coll, loc):
    p = Part("RPLIDAR_C1_USB_adapter_approx")
    p.box((30, 22, 1.6), (0, 0, 0.8), "PCB_Black")
    p.box((9, 7.5, 3.2), (0, -11 + 3.0, 3.2), "Metal")
    p.box((8, 5, 6), (0, 8, 4.6), "Plastic_White")
    return p.build(coll, loc, props={
        "dims_mm": "~30 x 22 x 8 (placeholder)", "confidence": "approx - measure",
        "notes": "Ships in the C1 kit; USB-A to USB-C cable goes to the Jetson.",
    })


def arducam(coll, loc):
    """Arducam B0385 (OV9782 global shutter, UVC). Standing up, lens looking -Y (forward)."""
    p = Part("Arducam_B0385_OV9782_USB_Camera")
    p.box((38, 1.6, 38), (0, 0, 19), "PCB_Black")
    p.box((16, 12, 16), (0, -6.8, 19), "Plastic_Black")         # M12 lens holder
    p.cyl(7, 14, (0, -19.8, 19), "Lens", axis="Y")               # M12 lens barrel
    p.box((6, 4, 3.5), (0, 2.8, 6), "Plastic_White")             # 4-pin cable connector (back)
    for pitch in (34, 28):                                       # both hole patterns
        for sx in (-1, 1):
            for sz in (-1, 1):
                p.cyl(1.1, 1.8, (sx * pitch / 2, 0, 19 + sz * pitch / 2), "Gold", axis="Y")
    return p.build(coll, loc, props={
        "dims_mm": "38 x 38 board; M2 holes on 34 x 34 and 28 x 28 pitch",
        "source": "https://www.arducam.com/100fps-global-shutter-color-usb-camera-board-1mp-ov9782-"
                  "uvc-webcam-module-with-low-distortion-m12-lens-without-microphones-for-computer-"
                  "laptop-android-device-and-raspberry-pi-arducam.html",
        "confidence": "board + hole pitch verified; lens holder/barrel length approx (~28 mm deep)",
        "notes": "70 deg (H) M12 lens. Cable plugs into the back - leave ~15 mm behind the board.",
    })


def usb_mic(coll, loc):
    p = Part("USB_Microphone_approx")
    p.box((16, 18, 7), (0, 9, 3.5), "Plastic_Black")
    p.box((12, 12, 4.5), (0, -6, 3.5), "Metal")
    return p.build(coll, loc, props={"confidence": "approx - generic dongle mic placeholder"})


def usb_audio(coll, loc):
    """Enclosed USB-stick style dongle; USB-A plug toward -X."""
    p = Part("Waveshare_USB_TO_AUDIO")
    L, W, H = 52.0, 18.0, 9.0
    p.rbox(L, W, H, 2, (0, 0, 0), "Plastic_Black")
    p.box((6, W + 0.2, H + 0.2), (-L / 2 + 3, 0, H / 2), "Terminal_Green")  # green end band
    p.box((12, 12, 4.5), (-L / 2 - 6, 0, H / 2), "Metal")                 # USB-A plug
    p.cyl(1.0, 0.2, (L / 2 - 6, 0, H + 0.1), "Metal")                     # mic hole
    for y, mat in ((-2, "Plastic_Black"), (2, "Wire_Red")):
        p.cyl(0.8, 15, (L / 2 + 7.5, y, H / 2), mat, axis="X")           # speaker lead
    return p.build(coll, loc, props={
        "dims_mm": "~52 x 18 x 9 case + 12 mm plug (scaled from product photo)",
        "source": "https://www.waveshare.com/wiki/USB_TO_AUDIO",
        "confidence": "approx - measure",
        "notes": "Plugs straight into a Jetson USB-A port (~65 mm sticks out) - or use a short "
                 "USB extension. PH2.0 speaker lead, 2.6 W/ch into 4 ohm BTL, onboard mic.",
    })


def speaker(coll, loc, name):
    """Waveshare 8 ohm 5 W enclosed speaker (WM8960 HAT pair). Front (two cones) faces +Z."""
    p = Part(name)
    L, W, H, EAR = 100.0, 45.0, 21.0, 6.0
    body = L - 2 * EAR
    p.rbox(body, W, H, 6, (0, 0, 0), "Plastic_Black")
    for sx in (-1, 1):                                        # 4 corner mounting ears
        for sy in (-1, 1):
            ex, ey = sx * (body / 2 + EAR / 2), sy * (W / 2 - 5)
            p.box((EAR, 10, 2.5), (ex, ey, H - 1.25), "Plastic_Black")
            p.cyl(1.5, 2.6, (ex, ey, H - 1.25), "Gold")
    # driver (with dust cap) toward -X, passive radiator toward +X
    p.cyl(17, 0.4, (-21, 0, H + 0.2), "Plastic_Grey")
    p.cyl(14, 0.6, (-21, 0, H + 0.3), "Lens")
    p.cyl(7, 1.5, (-21, 0, H + 0.75), "Plastic_Black")
    p.cyl(17, 0.4, (21, 0, H + 0.2), "Plastic_Grey")
    p.cyl(14.5, 0.6, (21, 0, H + 0.3), "Plastic_Black")
    for y, mat in ((-2, "Plastic_Black"), (2, "Wire_Red")):
        p.cyl(0.8, 20, (-body / 2 - 10, y, 6), mat, axis="X")  # lead stub
    return p.build(coll, loc, props={
        "dims_mm": "100 x 45 x 21 each incl. ears (Waveshare)",
        "source": "https://www.waveshare.com/8ohm-5w-speaker.htm",
        "confidence": "outline verified; ear size/hole spacing, cone sizes and lead exit from "
                      "photo - measure the ear hole spacing before printing mounts",
        "notes": "8 ohm 5 W. Front face (+Z) has the ears - it screws against the inside of a "
                 "grille panel. Keep both the driver and the passive radiator uncovered.",
    })


def motor_bonnet(coll, loc):
    p = Part("Adafruit_DC_Stepper_Motor_Bonnet_4280")
    W, D, T = 65.0, 30.5, 1.6
    p.box((W, D, T), (0, 0, T / 2), "PCB_Black")
    p.box((51, 5.1, 8.5), (0, 11.75, -4.25), "Plastic_Black")   # 2x20 female header (underside)
    for x in (-23, -4):
        p.box((17.5, 7.5, 10), (x, -11.25, T + 5), "Terminal_Green")  # M1/M2, M3/M4 (5-pos)
    p.box((7, 7.5, 10), (22, -11.25, T + 5), "Power_Port")      # motor power in (2-pos)
    p.box((4.5, 6, 3), (30, -3, T + 1.5), "Plastic_White")      # STEMMA QT
    p.box((7.8, 4.4, 1.2), (8, 3, T + 0.6), "Plastic_Black")    # PCA9685
    for x in (-18, -6):
        p.box((7.8, 6, 1.2), (x, 3, T + 0.6), "Plastic_Black")  # TB6612
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl(2.6, 0.1, (sx * 29, sy * 11.5, T + 0.05), "Gold")
    return p.build(coll, loc, props={
        "dims_mm": "65.2 x 30.6 x 14.0 listed; female header modelled 8.5 mm below the PCB",
        "source": "https://www.adafruit.com/product/4280",
        "confidence": "outline verified; terminal layout from product photo; chips approx. "
                      "Holes = Pi Zero 58 x 23 M2.5",
        "notes": "TB6612: 1.2 A/ch continuous, 3 A 20 ms peak, 4.5-13.5 V. On the Jetson wire it "
                 "with 4 jumpers (pin1 3.3V, pin3 SDA, pin5 SCL, pin6 GND) instead of stacking; "
                 "header faces down, so leave ~20 mm under it for Dupont plugs.",
    })


def gearmotor(coll, loc, name, rot_z):
    """Acxico N20 3-6 V full-metal gearbox. Local +X = output shaft; origin on shaft axis at the
    gearbox face."""
    p = Part(name)
    p.box((9, 12, 10), (-4.5, 0, 0), "Brass")            # full-metal gearbox
    p.box((13, 12, 10), (-15.5, 0, 0), "Metal")          # motor can
    p.box((2, 10, 8.5), (-23, 0, 0), "Plastic_Black")    # end cap (body total 24 mm)
    for y, mat in ((-2.5, "Plastic_Black"), (2.5, "Wire_Red")):
        p.cyl(0.6, 20, (-34, y, 0), mat, axis="X")       # lead stubs (real leads ~80-140 mm)
    p.cyl(2.0, 0.8, (0.4, 0, 0), "Metal", axis="X")      # bushing boss
    p.cyl(1.5, 9, (5.3, 0, 0), "Metal", axis="X")        # 3 mm D-shaft (flat not modelled)
    for y in (-4.5, 4.5):
        p.cyl(0.8, 0.2, (0.1, y, 0), "Gold", axis="X")   # M1.6 face-plate holes
    return p.build(coll, loc, rot_z, props={
        "dims_mm": "24 x 12 x 10 body + 9 mm x 3 mm D-shaft",
        "source": "https://www.amazon.com/Acxico-Micro-Motor-3V-6V-Gearbox/dp/B09DG3GCGK",
        "confidence": "body/shaft per listing; face-plate hole spacing approx - measure",
        "notes": "104 RPM @ 6 V, 52 RPM @ 3 V, 0.04 A no-load. Origin: output shaft axis at "
                 "gearbox face. Print wheel hubs with a 3 mm D bore (2.5 mm across the flat).",
    })


def aa_pack(coll, loc):
    p = Part("DAIERTEK_4xAA_Holder_switch_cover")
    L, W, H = 68.7, 64.2, 22.5
    p.box((L, W, H), (0, 0, H / 2), "Plastic_Black")
    p.box((10, 5, 3), (20, 0, H + 1.5), "Plastic_Grey")          # slide switch on cover
    p.cyl(2.5, 0.6, (-20, 0, H + 0.3), "Metal")                  # cover screw
    for y, mat in ((-3, "Wire_Red"), (3, "Plastic_Black")):
        p.cyl(0.8, 20, (-L / 2 - 10, y, 4), mat, axis="X")       # lead stubs (~150 mm real)
    return p.build(coll, loc, props={
        "dims_mm": "68.7 x 64.2 x 22.5 (listing)",
        "source": "https://www.amazon.com/DaierTek-Battery-Holder-Storage-Connector/dp/B09N1GDWQ9",
        "confidence": "outline per listing; switch/screw positions approx",
        "notes": "Motors only (optionally 2 servos, NiMH recommended). Never the Jetson. "
                 "Switch and screw cover are on top - keep them reachable for battery swaps.",
    })


def pca9685(coll, loc):
    """HiLetgo PCA9685 16-ch (Adafruit clone). Servo pins along -Y edge."""
    p = Part("HiLetgo_PCA9685_16ch_Servo_Driver")
    W, D, T = 61.0, 25.0, 1.6
    p.box((W, D, T), (0, 0, T / 2), "PCB_Blue")
    for x in (-19.05, -6.35, 6.35, 19.05):                      # 4 banks of 3x4 servo pins
        p.box((10.16, 7.62, 2.5), (x, -7.3, T + 1.25), "Plastic_Black")
        for dy, mat in ((-2.54, "Plastic_Black"), (0, "Wire_Red"), (2.54, "Pin_Yellow")):
            p.box((10.0, 2.2, 6), (x, -7.3 + dy, T + 5.5), mat)  # GND / V+ / PWM rows
    p.box((10.2, 7.5, 10), (0, 7.5, T + 5), "Terminal_Green")  # V+ servo power terminal
    p.cyl(4.0, 11.5, (-20, 7, T + 5.75), "Plastic_Black")       # on-board electrolytic cap
    p.cyl(3.6, 0.3, (-20, 7, T + 11.65), "Metal")
    for sx in (-1, 1):                                          # right-angle 6-pin headers
        p.box((2.54, 15.24, 2.5), (sx * 29.2, 1.5, T + 1.25), "Plastic_Black")
        p.box((8, 14.5, 0.8), (sx * 31.7, 1.5, T + 1.25), "Gold")
    p.box((7.8, 4.4, 1.2), (10, 5, T + 0.6), "Plastic_Black")  # PCA9685 chip
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl(2.2, 0.1, (sx * 27.5, sy * 9.5, T + 0.05), "Gold")
    return p.build(coll, loc, props={
        "dims_mm": "61 x 25 PCB (listing); right-angle headers stick out ~5 mm each end",
        "source": "HiLetgo 2pcs PCA9685 (Amazon)",
        "confidence": "outline per listing; hole spacing, cap size and header positions approx - "
                      "measure",
        "notes": "Default I2C 0x40 - coexists with the Motor Bonnet's PCA9685 at 0x60. "
                 "Servo power goes into the V+ terminal from its own supply, not the Jetson.",
    })


def ball_caster(coll, loc, name):
    """MARRTEUM mini ball caster, as mounted: ball on the ground, hex flange up."""
    p = Part(name)
    H = 22.9
    p.cyl(8, 16, (0, 0, 8), "Metal", segs=24)                   # ball (drawn as a short cylinder)
    p.cyl(12.5, 14, (0, 0, 12), "Plastic_Black")                # housing
    p.cyl(18.55, 3.9, (0, 0, H - 1.95), "Plastic_Black", segs=6)  # hex flange (mounting face)
    for sx in (-1, 1):
        p.cyl(1.6, 0.2, (sx * 14, 0, H + 0.1), "Gold")          # screw holes
    return p.build(coll, loc, props={
        "dims_mm": "37.1 across x 22.9 tall (1.46 x 0.9 in listing)",
        "source": "MARRTEUM 4pcs ball casters (Amazon)",
        "confidence": "overall size per listing; ball/housing/hole positions approx - measure",
        "notes": "Top face = mounting face (adhesive + 2 screw holes). 4 owned.",
    })


def mg90s(coll, loc, name):
    """Output spline offset toward +X."""
    p = Part(name)
    p.box((22.8, 12.2, 22.7), (0, 0, 11.35), "Plastic_Black")
    p.box((32.5, 12.2, 2.5), (0, 0, 17.15), "Plastic_Black")    # mounting tabs
    for sx in (-1, 1):
        p.cyl(1.0, 2.6, (sx * 13.9, 0, 17.15), "Gold")
    p.cyl(6.0, 4.0, (5.4, 0, 24.7), "Plastic_Black")            # gear boss
    p.cyl(2.4, 3.1, (5.4, 0, 28.25), "Metal")                   # output spline
    p.box((2, 4, 1.5), (-12.4, 0, 4), "Plastic_Grey")           # lead exit
    return p.build(coll, loc, props={
        "dims_mm": "22.8 x 12.2 x ~29.8 to spline top; 32.5 across tabs",
        "confidence": "typical MG90S datasheet dims - clones vary +/-0.5 mm",
        "notes": "Stall ~0.7-1 A at 6 V each. Optional - pan/tilt head idea.",
    })


# ----------------------------------------------------------------------------- scene

def setup_scene():
    us = bpy.context.scene.unit_settings
    us.system = "METRIC"
    us.scale_length = 0.001
    us.length_unit = "MILLIMETERS"
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for sp in area.spaces:
                    if sp.type == "VIEW_3D":
                        sp.clip_start = 0.5
                        sp.clip_end = 20000
                        sp.shading.color_type = "MATERIAL"


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
    for cu in list(bpy.data.curves):
        if cu.users == 0 and cu.name.startswith(PREFIX):
            bpy.data.curves.remove(cu)


def build_all():
    setup_scene()
    clear_root()
    scene_coll = bpy.context.scene.collection
    root = get_coll(ROOT, scene_coll)
    c_power = get_coll("Compute & Power", root)
    c_sense = get_coll("Sensors & Audio", root)
    c_drive = get_coll("Drive", root)
    c_servo = get_coll("Servos (optional)", root)
    c_lbl = get_coll("Labels", root)

    def lbl(text, x, y):
        label(text, (x, y, 0), c_lbl)

    # Row 1 - compute & power
    jetson(c_power, (0, 0, 0))
    lbl("Jetson Orin Nano Super\n100 x 79 x 21", 0, -50)
    power_bank(c_power, (170, 0, 0))
    lbl("UGREEN 145W bank\n~158 x 72 x 28", 170, -46)
    pd_cable(c_power, (300, 0, 0))
    lbl("USB-C PD > barrel 15V\n(plug ends)", 300, -30)

    # Row 2 - sensors & audio
    y = -140
    lidar(c_sense, (0, y, 0))
    lbl("RPLIDAR C1\n55.6 x 55.6 x 41.3", 0, y - 40)
    lidar_adapter(c_sense, (75, y, 0))
    lbl("C1 USB adapter\n(approx)", 75, y - 20)
    arducam(c_sense, (130, y, 0))
    lbl("Arducam B0385\n38 x 38", 130, y - 35)
    usb_mic(c_sense, (180, y, 0))
    lbl("USB mic\n(approx)", 180, y - 20)
    usb_audio(c_sense, (240, y, 0))
    lbl("USB TO AUDIO\n(approx)", 240, y - 18)
    speaker(c_sense, (340, y + 30, 0), "Waveshare_Speaker_8ohm_5W_L")
    speaker(c_sense, (340, y - 25, 0), "Waveshare_Speaker_8ohm_5W_R")
    lbl("Waveshare 8 ohm 5 W x2\n100 x 45 x 21 each", 340, y - 55)

    # Row 3 - drive
    y = -260
    motor_bonnet(c_drive, (0, y, 8.5))  # raised so the underside header sits on the ground
    lbl("Adafruit Motor Bonnet\n65.2 x 30.6", 0, y - 22)
    gearmotor(c_drive, (100, y + 12, 5), "N20_Motor_L", math.pi)
    gearmotor(c_drive, (100, y - 12, 5), "N20_Motor_R", 0.0)
    lbl("Acxico N20 L/R\n104 RPM @ 6 V", 100, y - 24)
    aa_pack(c_drive, (190, y, 0))
    lbl("DAIERTEK 4xAA\n68.7 x 64.2 x 22.5", 190, y - 40)
    ball_caster(c_drive, (275, y, 0), "Ball_Caster")
    lbl("Ball caster (4 owned)\n37 x 23", 275, y - 26)

    # Row 4 - optional servos
    y = -370
    pca9685(c_servo, (0, y, 0))
    lbl("HiLetgo PCA9685\n61 x 25", 0, y - 20)
    mg90s(c_servo, (80, y, 0), "MG90S_Pan")
    mg90s(c_servo, (125, y, 0), "MG90S_Tilt")
    lbl("MG90S x2 (pan / tilt)", 102, y - 14)

    return root


if __name__ == "__main__":
    build_all()
