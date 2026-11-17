"""A dependency-free illustration for the desktop title screen.

The scene uses a 1000 by 400 drawing space and scales to the canvas.  Every
primitive carries the same tag, so a resize replaces this scene without
removing other canvas content or leaving an old drawing underneath it.
"""

from math import cos, pi, sin


ART_TAG = "entrance-art"
TORCH_TAG = "entrance-torches"


def _blend_color(dim: str, bright: str, amount: float) -> str:
    channels = (round(int(dim[i:i + 2], 16) * (1 - amount)
                      + int(bright[i:i + 2], 16) * amount)
                for i in (1, 3, 5))
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def _torch_shapes(index: int, elapsed: float):
    """Small, smooth variations, independent of character and combat rolls."""
    x = (284, 716)[index]
    phase = index * 2.37
    flicker = (0.55 * sin(elapsed * 4.1 + phase)
               + 0.30 * sin(elapsed * 9.7 + phase * 1.3)
               + 0.15 * sin(elapsed * 17.3 + phase * 0.7))
    sway = 2.2 * sin(elapsed * 7.7 + phase) + 1.1 * sin(elapsed * 13.1 + phase)
    brightness = (1 + flicker) / 2
    halos = ((46, "#354034", "#414a39"), (35, "#444532", "#54523a"),
             (24, "#5c4c33", "#705b3d"), (15, "#7d5d35", "#997343"))
    for layer, (radius, dim, bright) in enumerate(halos):
        radius *= 1 + 0.05 * flicker
        cx, cy = x + sway * 0.2, 174 + flicker * 0.6
        yield ("oval", f"torch-{index}-halo-{layer}",
               (cx - radius, cy - radius, cx + radius, cy + radius),
               _blend_color(dim, bright, brightness))
    flames = (
        ((-12, 190, -6, 178, -8, 163, 1, 151, 4, 167, 10, 159,
          13, 179, 8, 195, -8, 197), "#bf7930", "#df9b43"),
        ((-6, 190, -3, 176, 2, 165, 3, 180, 8, 180, 5, 196, -3, 197),
         "#e5a646", "#facb6a"),
        ((-2, 194, 0, 183, 3, 193, 2, 199), "#ffd58b", "#ffedb7"),
    )
    for layer, (points, dim, bright) in enumerate(flames):
        coords = []
        for px, py in zip(points[::2], points[1::2]):
            tip_weight = max(0, (197 - py) / 46)
            coords.extend((x + px * (1 + 0.08 * flicker) + sway * tip_weight,
                           197 + (py - 197) * (1 + 0.10 * flicker)))
        yield ("polygon", f"torch-{index}-flame-{layer}", coords,
               _blend_color(dim, bright, brightness))
    for ember in range(2):
        rise = (elapsed * (20 + ember * 7) + index * 12 + ember * 19) % 40
        cx = x + (9 if ember == 0 else -4) + 3 * sin(elapsed * 2.9 + phase + ember)
        cy = 162 - rise
        color = _blend_color("#514831", "#e5b75c", 1 - rise / 40)
        yield ("oval", f"torch-{index}-ember-{ember}",
               (cx - 1, cy - 1, cx + 1, cy + 1), color)


def animate_torches(canvas, width: float, height: float, elapsed: float) -> None:
    """Update existing torch shapes without rebuilding the static illustration."""
    if width <= 0 or height <= 0:
        return
    sx, sy = width / 1000, height / 400
    for index in range(2):
        for _, tag, points, color in _torch_shapes(index, elapsed):
            coords = [value * (sx if i % 2 == 0 else sy)
                      for i, value in enumerate(points)]
            canvas.coords(tag, *coords)
            canvas.itemconfigure(tag, fill=color)


def draw_entrance(canvas, width: float, height: float) -> None:
    """Paint the torchlit entrance of the Catacombs of Thalinor.

    ``canvas`` only needs the usual Tk Canvas drawing methods.  Keeping the
    illustration independent of Tk initialization also makes it easy to
    check with a small recording canvas in headless environments.
    """
    canvas.delete(ART_TAG)
    if width <= 0 or height <= 0:
        return
    sx, sy = width / 1000, height / 400

    def polygon(points, fill, outline="", line_width=1, tags=()):
        coords = [value * (sx if index % 2 == 0 else sy)
                  for index, value in enumerate(points)]
        canvas.create_polygon(*coords, fill=fill, outline=outline,
                              width=max(1, line_width * min(sx, sy)),
                              tags=(ART_TAG, *tags))

    def rectangle(x1, y1, x2, y2, fill, outline="", line_width=1):
        canvas.create_rectangle(x1 * sx, y1 * sy, x2 * sx, y2 * sy,
                                fill=fill, outline=outline,
                                width=max(1, line_width * min(sx, sy)),
                                tags=(ART_TAG,))

    def oval(x1, y1, x2, y2, fill, outline="", line_width=1, tags=()):
        canvas.create_oval(x1 * sx, y1 * sy, x2 * sx, y2 * sy,
                           fill=fill, outline=outline,
                           width=max(1, line_width * min(sx, sy)),
                           tags=(ART_TAG, *tags))

    def line(points, fill, line_width=1):
        coords = [value * (sx if index % 2 == 0 else sy)
                  for index, value in enumerate(points)]
        canvas.create_line(*coords, fill=fill,
                           width=max(1, line_width * min(sx, sy)),
                           capstyle="round", joinstyle="round",
                           tags=(ART_TAG,))

    # Night sky and distant ridges remain quiet around the central doorway.
    for index, shade in enumerate(("#111820", "#141d26", "#17222b",
                                   "#1b2730", "#202d35")):
        rectangle(0, index * 80, 1000, (index + 1) * 80, shade)
    for x, y, radius in ((90, 35, 1), (170, 19, 1), (246, 56, 1),
                          (751, 22, 1), (862, 53, 1.3), (934, 28, 1),
                          (810, 77, 0.8)):
        oval(x - radius, y - radius, x + radius, y + radius, "#65747d")
    polygon((0, 180, 67, 111, 106, 143, 168, 76, 225, 149,
             280, 122, 374, 208, 1000, 215, 1000, 400, 0, 400), "#202d37")
    polygon((640, 216, 716, 121, 754, 149, 820, 91, 876, 161,
             934, 119, 1000, 166, 1000, 400, 640, 400), "#1c2933")
    polygon((0, 247, 68, 190, 135, 226, 208, 164, 302, 241,
             1000, 267, 1000, 400, 0, 400), "#15212a")

    # The facade is carved into a broken cliff, with cool angular rock planes.
    polygon((118, 317, 151, 149, 203, 74, 283, 47, 367, 53,
             428, 27, 498, 21, 576, 36, 688, 51, 788, 78,
             848, 164, 882, 323), "#2b3944")
    polygon((151, 149, 203, 74, 283, 47, 264, 181, 211, 308,
             118, 317), "#23313c")
    polygon((203, 74, 283, 47, 264, 181, 220, 200, 247, 102), "#3b4a56")
    polygon((688, 51, 788, 78, 848, 164, 882, 323, 793, 309,
             736, 188), "#22313b")
    polygon((788, 78, 848, 164, 793, 309, 811, 181, 754, 100), "#354551")
    line((174, 212, 204, 140, 247, 102, 227, 176), "#52616a", 1.4)
    line((823, 222, 790, 186, 754, 100), "#4a5a65", 1.3)

    # Masonry blocks form a readable, weathered wall rather than a flat slab.
    rectangle(240, 100, 760, 315, "#303f4b")
    stone_colors = ("#384854", "#33434f", "#3d4d58", "#354651")
    for row in range(6):
        y = 104 + row * 35
        offset = 0 if row % 2 == 0 else 38
        for col in range(8):
            x = 243 - offset + col * 74
            left, right = max(242, x), min(758, x + 70)
            if left >= right:
                continue
            rectangle(left, y, right, y + 31,
                      stone_colors[(row + col * 3) % len(stone_colors)],
                      "#23333e")
            line((left + 3, y + 2, right - 3, y + 2), "#53636c")
    # Long cracks and a few chipped stones break the regular block pattern.
    line((262, 115, 276, 127, 267, 151, 286, 165, 279, 189), "#202d37", 2)
    line((737, 111, 723, 139, 731, 151, 715, 176, 721, 195), "#202d37", 2)
    polygon((246, 259, 261, 265, 255, 277, 243, 272), "#263540")
    polygon((738, 229, 755, 224, 758, 239, 748, 237), "#263540")

    # A black vault behind the arch; shallow steps disappear into its depth.
    opening = []
    for index in range(25):
        angle = pi - index * pi / 24
        opening.extend((500 + 139 * cos(angle), 207 - 124 * sin(angle)))
    opening.extend((639, 321, 361, 321))
    polygon(opening, "#060b10")
    polygon((384, 221, 409, 173, 435, 149, 418, 247, 399, 294,
             373, 306), "#101a22")
    polygon((616, 221, 591, 173, 565, 149, 582, 247, 601, 294,
             627, 306), "#111b22")
    for index in range(6):
        y = 247 + index * 11
        half = 56 + index * 10
        rectangle(500 - half, y, 500 + half, y + 7,
                  ("#1a252d", "#202d35", "#25323a")[index % 3])
        line((500 - half, y, 500 + half, y), "#3d494f", 1)

    # Side piers and their beveled edges support eleven wedge-shaped stones.
    for left in (309, 639):
        rectangle(left, 194, left + 52, 320, "#283843", "#1e2c36")
        rectangle(left + 5, 195, left + 12, 316, "#596872")
        rectangle(left + 43, 195, left + 50, 316, "#1c2a34")
        for y in (196, 229, 263, 297):
            rectangle(left + 13, y, left + 43, y + 29, "#41525e", "#2b3b47")
            line((left + 15, y + 2, left + 41, y + 2), "#657580")
        rectangle(left - 8, 302, left + 59, 321, "#43535e", "#263742")
        line((left - 6, 304, left + 57, 304), "#697780", 1.4)

    for index in range(11):
        a1, a2 = pi - index * pi / 11, pi - (index + 1) * pi / 11
        outer1 = (500 + 191 * cos(a1), 207 - 172 * sin(a1))
        outer2 = (500 + 191 * cos(a2), 207 - 172 * sin(a2))
        inner2 = (500 + 141 * cos(a2), 207 - 126 * sin(a2))
        inner1 = (500 + 141 * cos(a1), 207 - 126 * sin(a1))
        polygon((*outer1, *outer2, *inner2, *inner1),
                ("#485a66", "#41535f", "#53646e")[index % 3], "#202f3a", 2)
        line((*outer1, *outer2), "#75818a", 1.6)
        line((*inner1, *inner2), "#293a45", 2.5)
    # A heavy central keystone bears a small skull carved into the lintel.
    polygon((477, 37, 523, 37, 518, 93, 482, 93), "#596b76", "#273944", 2)
    line((480, 40, 520, 40), "#81909a", 1.6)
    oval(485, 48, 515, 75, "#8c999e", "#3c4d59")
    polygon((490, 66, 510, 66, 508, 82, 492, 82), "#849296", "#3c4d59")
    oval(489, 57, 498, 66, "#26333d")
    oval(502, 57, 511, 66, "#26333d")
    polygon((500, 64, 496, 72, 504, 72), "#33414a")
    for x in (495, 500, 505):
        line((x, 76, x, 82), "#3d4d56")

    # Iron gate remnants and hanging chains frame the open passage.
    for mirror in (False, True):
        def gate_x(x):
            return 1000 - x if mirror else x

        for x, top in ((370, 198), (382, 174), (394, 155)):
            line((gate_x(x), top, gate_x(x), 297), "#27343d", 3)
            polygon((gate_x(x), top - 8, gate_x(x - 3), top,
                     gate_x(x + 3), top), "#36444c")
        line((gate_x(369), 238, gate_x(397), 232), "#42515a", 2)
        line((gate_x(369), 280, gate_x(397), 271), "#34424b", 2)
        for y in range(112, 171, 10):
            oval(gate_x(421) - 2, y, gate_x(421) + 2, y + 8,
                 "", "#3d484f", 1.2)

    # Torches are painted from dark halo to bright core; no bitmap assets.
    for index, x in enumerate((284, 716)):
        shapes = list(_torch_shapes(index, 0))
        for _, tag, points, color in shapes[:4]:
            oval(*points, color, tags=(TORCH_TAG, tag))
        polygon((x - 17, 231, x - 17, 240, x + 17, 240,
                 x + 17, 231), "#202b32", "#56606a")
        line((x, 239, x, 214, x - 9, 205), "#161f25", 6)
        polygon((x - 7, 195, x + 7, 195, x + 4, 225,
                 x - 4, 225), "#564532", "#242b2b")
        for kind, tag, points, color in shapes[4:]:
            if kind == "polygon":
                polygon(points, color, tags=(TORCH_TAG, tag))
            else:
                oval(*points, color, tags=(TORCH_TAG, tag))

    # Foreground paving guides the eye toward the light and the dark stairs.
    polygon((0, 339, 182, 304, 320, 310, 364, 307, 636, 307,
             680, 310, 818, 304, 1000, 339, 1000, 400, 0, 400), "#19242c")
    polygon((362, 314, 638, 314, 718, 400, 282, 400), "#2e3c46")
    steps = ((315, 324, 359, 641), (331, 342, 344, 656),
             (352, 365, 325, 675), (378, 394, 302, 698))
    for index, (top, bottom, left, right) in enumerate(steps):
        polygon((left, top, right, top, right + 11, bottom,
                 left - 11, bottom), "#44525b")
        rectangle(left - 11, bottom, right + 11, bottom + 5, "#202f3a")
        line((left + 2, top + 1, right - 2, top + 1), "#6a747a", 1.4)
        seam = 475 if index % 2 == 0 else 539
        line((seam, top + 2, seam + 2, bottom), "#283843", 1)
    for points in ((98, 347, 191, 328, 255, 339, 189, 359),
                   (748, 340, 810, 328, 904, 347, 818, 362),
                   (26, 390, 108, 368, 187, 380, 166, 400),
                   (810, 383, 878, 369, 970, 391, 945, 400)):
        polygon(points, "#25333d", "#131f28")
    polygon((209, 309, 224, 291, 251, 298, 270, 319), "#43515a", "#1d2c35")
    polygon((741, 310, 759, 295, 782, 302, 796, 321), "#35454f", "#1d2c35")

    # Bare foreground branches frame the image without covering the gate.
    for points, weight in (((57, 400, 79, 326, 80, 259, 101, 189, 97, 151), 9),
                           ((80, 268, 49, 245, 25, 196, 11, 184), 5),
                           ((88, 230, 119, 207, 145, 164), 4),
                           ((47, 241, 55, 201, 42, 166), 3),
                           ((113, 211, 125, 177, 120, 153), 2),
                           ((935, 400, 915, 320, 916, 251, 887, 188, 891, 144), 9),
                           ((915, 276, 950, 241, 967, 189, 987, 164), 5),
                           ((900, 220, 865, 201, 848, 169), 4),
                           ((948, 245, 944, 210, 929, 185), 3),
                           ((887, 190, 863, 164, 864, 141), 2)):
        line(points, "#0d161d", weight)
    # Dark foreground corners keep the title-screen controls visually calm.
    polygon((0, 371, 84, 386, 178, 400, 0, 400), "#0f1921")
    polygon((817, 400, 907, 384, 1000, 373, 1000, 400), "#0f1921")
