"""Original, dependency-free first-person illustrations for the dungeon UI.

The view is a stylized room portrait rather than a tactical 3D simulation.
It consumes only a reduced visible-room snapshot; it never inspects the game,
chooses loot, schedules callbacks, or consumes random numbers.
"""

from math import cos, pi, sin
from sprite_art import draw_sprite, enemy_sprite_key, hand_sprite_key


VIEW_TAG = "dungeon-view"

# Ceiling, far wall, side wall, near floor, seams, highlights, and magical accent.
_PALETTES = {
    1: ("#111923", "#34424c", "#263440", "#23313a", "#17232d", "#5c6c73", "#d8aa55"),
    2: ("#111d1c", "#30443b", "#23372f", "#22372f", "#13251e", "#647c65", "#9ebc70"),
    3: ("#241918", "#4b3832", "#352925", "#382b28", "#241c1c", "#8e6c53", "#ee9d46"),
    4: ("#111322", "#31354d", "#24283f", "#25283e", "#181a2c", "#69718f", "#a3a4e7"),
    5: ("#21131b", "#48303c", "#34232e", "#33242e", "#21161f", "#946875", "#e2a18c"),
}


def draw_dungeon_view(canvas, width: float, height: float, view: dict) -> None:
    """Draw a scalable first-person room using standard Tk Canvas primitives.

    All items carry VIEW_TAG, with additional semantic tags for smoke checks.
    Callers may redraw or resize freely without advancing an adventure.
    """
    canvas.delete(VIEW_TAG)
    if width <= 0 or height <= 0:
        return
    view = view or {}
    floor = view.get("floor", 1)
    if type(floor) is not int or not 1 <= floor <= 5:
        floor = 1
    ceiling, wall, side, ground, seam, edge, accent = _PALETTES[floor]
    sx, sy = width / 1000, height / 400

    def points(values):
        return [v * (sx if i % 2 == 0 else sy) for i, v in enumerate(values)]

    def poly(values, fill, outline="", weight=1, tag="view-wall"):
        canvas.create_polygon(*points(values), fill=fill, outline=outline,
                              width=max(1, weight * min(sx, sy)),
                              tags=((VIEW_TAG, tag, "view-hands") if tag == "view-shield" else (VIEW_TAG, tag)))

    def rect(x1, y1, x2, y2, fill, outline="", weight=1, tag="view-wall"):
        canvas.create_rectangle(x1 * sx, y1 * sy, x2 * sx, y2 * sy,
                                fill=fill, outline=outline,
                                width=max(1, weight * min(sx, sy)),
                                tags=((VIEW_TAG, tag, "view-hands") if tag == "view-shield" else (VIEW_TAG, tag)))

    def oval(x1, y1, x2, y2, fill, outline="", weight=1, tag="view-wall"):
        canvas.create_oval(x1 * sx, y1 * sy, x2 * sx, y2 * sy,
                           fill=fill, outline=outline,
                           width=max(1, weight * min(sx, sy)),
                           tags=((VIEW_TAG, tag, "view-hands") if tag == "view-shield" else (VIEW_TAG, tag)))

    def line(values, fill, weight=1, tag="view-wall"):
        canvas.create_line(*points(values), fill=fill,
                           width=max(1, weight * min(sx, sy)),
                           capstyle="round", joinstyle="round",
                           tags=((VIEW_TAG, tag, "view-hands") if tag == "view-shield" else (VIEW_TAG, tag)))

    def arch(x1, top, x2, bottom, fill, outline="", tag="view-exit"):
        cx, rx = (x1 + x2) / 2, (x2 - x1) / 2
        ry = min(rx, (bottom - top) / 2)
        values = [x1, bottom]
        for i in range(17):
            angle = pi - i * pi / 16
            values.extend((cx + rx * cos(angle), top + ry - ry * sin(angle)))
        values.extend((x2, bottom))
        poly(values, fill, outline, 2, tag)

    def torch(x, y, tag="view-decoration"):
        for radius, color in ((29, "#494539"), (21, "#66533a"), (13, "#9a713e")):
            oval(x - radius, y - radius, x + radius, y + radius, color, tag=tag)
        line((x, y + 8, x, y + 43, x - 9, y + 49), "#171c21", 6, tag)
        poly((x - 6, y + 7, x + 6, y + 7, x + 3, y + 32, x - 3, y + 32),
             "#715035", "#221c1c", tag=tag)
        poly((x - 10, y + 9, x - 7, y - 7, x - 2, y - 19,
              x + 3, y - 9, x + 6, y - 14, x + 11, y + 4, x + 5, y + 14),
             "#d88b36", tag=tag)
        poly((x - 4, y + 10, x - 1, y - 8, x + 4, y + 3, x + 3, y + 14),
             "#ffe0a0", tag=tag)

    def portal(x=663, y=173):
        for rx, ry, color in ((47, 84, "#283c4f"), (38, 75, "#376b7b"),
                              (30, 65, "#63b9bd"), (23, 58, "#183740")):
            oval(x - rx, y - ry, x + rx, y + ry, color, tag="view-portal")
        for i in range(10):
            a = i * pi / 5
            px, py = x + 35 * cos(a), y + 71 * sin(a)
            line((px - 3, py, px + 3, py), "#b8ebe0", 2, "view-portal")
        poly((x - 59, y + 85, x + 59, y + 85, x + 76, y + 101, x - 76, y + 101),
             "#475b63", "#172831", tag="view-portal")

    def foe(enemy):
        # No official creature designs: simple silhouettes built for this project.
        kind = str(enemy.get("archetype", "humanoid")).lower()
        name = str(enemy.get("name", "")).lower()
        boss = bool(enemy.get("boss"))
        if draw_sprite(canvas, enemy_sprite_key(enemy, floor), 500 * sx, 307 * sy,
                       (440 if boss else 385) * sx, (310 if boss else 270) * sy,
                       anchor="s", tags=(VIEW_TAG, "view-enemy")):
            return
        armor = ("#8b9695", "#627c5b", "#9b7654", "#737eaa", "#9b6871")[floor - 1]
        shadow = "#111921"
        glow = ("#e2c68b", "#c1dd7e", "#ffbe69", "#bfccff", "#efb0a6")[floor - 1]
        oval(407, 273, 593, 305, "#14212a", tag="view-enemy")
        if boss:
            oval(412, 89, 588, 289, "", accent, 3, "view-enemy")
            for i in range(7):
                x = 439 + i * 20
                line((x, 115, x + 7, 99, x + 14, 115), accent, 2, "view-enemy")

        if any(word in kind for word in ("beast", "rat", "hound", "wolf")):
            oval(414, 221, 556, 280, armor, shadow, 2, "view-enemy")
            poly((528, 236, 562, 222, 581, 230, 596, 247, 566, 262, 536, 258),
                 armor, shadow, 2, "view-enemy")
            poly((548, 230, 542, 210, 562, 222), armor, shadow, tag="view-enemy")
            poly((566, 229, 568, 212, 579, 234), armor, shadow, tag="view-enemy")
            for x in (435, 465, 535, 556):
                poly((x, 261, x + 9, 261, x + 15, 290, x - 6, 290),
                     shadow, tag="view-enemy")
            line((420, 249, 390, 245, 375, 228, 382, 213), armor, 5, "view-enemy")
            oval(568, 236, 575, 243, glow, tag="view-enemy")
            line((583, 250, 593, 250), "#d7c4a2", 2, "view-enemy")
        elif any(word in kind for word in ("insect", "beetle", "spider", "crawling")):
            for direction in (-1, 1):
                for y, reach in ((224, 95), (244, 103), (263, 88)):
                    line((500 + direction * 31, y, 500 + direction * reach, y - 9,
                          500 + direction * (reach + 15), y + 25),
                         armor, 7, "view-enemy")
            oval(448, 207, 552, 284, armor, shadow, 3, "view-enemy")
            oval(474, 188, 526, 230, shadow, edge, 2, "view-enemy")
            line((500, 216, 500, 278), edge, 2, "view-enemy")
            for x in (485, 507):
                oval(x, 201, x + 9, 210, glow, tag="view-enemy")
            line((482, 195, 459, 177, 448, 183), armor, 3, "view-enemy")
            line((518, 195, 541, 177, 552, 183), armor, 3, "view-enemy")
        elif any(word in kind for word in ("serpent", "snake", "root", "vine", "plant")):
            for i in range(3):
                oval(426 + i * 14, 249 - i * 13, 575 - i * 7, 294 - i * 12,
                     armor, shadow, 3, "view-enemy")
            line((514, 261, 547, 239, 545, 207, 521, 190), armor, 23, "view-enemy")
            poly((497, 182, 527, 179, 551, 191, 540, 210, 511, 205),
                 armor, shadow, 2, "view-enemy")
            oval(513, 187, 521, 194, glow, tag="view-enemy")
            line((498, 198, 485, 202, 475, 198), "#ce9b87", 2, "view-enemy")
            for x in (450, 472, 493):
                line((x, 275, x + 8, 268), edge, 2, "view-enemy")
        elif any(word in kind for word in ("ooze", "slime", "blob")):
            poly((406, 281, 413, 253, 437, 239, 455, 214, 488, 203,
                  523, 211, 540, 236, 575, 250, 593, 281, 567, 294,
                  531, 290, 499, 301, 470, 291, 433, 298),
                 armor, shadow, 3, "view-enemy")
            oval(456, 220, 535, 259, "", edge, 2, "view-enemy")
            for x, y in ((470, 236), (506, 231)):
                oval(x, y, x + 12, y + 10, shadow, tag="view-enemy")
                oval(x + 3, y + 1, x + 7, y + 5, glow, tag="view-enemy")
            for x, y, radius in ((435, 268, 6), (553, 263, 7), (497, 281, 5)):
                oval(x - radius, y - radius, x + radius, y + radius,
                     "", edge, 1, "view-enemy")
        elif (any(word in kind for word in ("construct", "automaton", "golem", "machine"))
              or any(word in name for word in ("automaton", "colossus", "sentinel"))):
            for x in (461, 516):
                rect(x, 243, x + 25, 282, armor, shadow, 2, "view-enemy")
                poly((x - 9, 279, x + 31, 279, x + 39, 295, x - 13, 295),
                     "#3b444c", shadow, 2, "view-enemy")
            poly((444, 167, 555, 167, 547, 248, 452, 248), armor, shadow, 3, "view-enemy")
            for x in (417, 555):
                rect(x, 179, x + 30, 230, armor, shadow, 2, "view-enemy")
                oval(x - 2, 225, x + 34, 252, "#3b444c", shadow, 2, "view-enemy")
            rect(473, 125, 527, 169, armor, shadow, 3, "view-enemy")
            rect(482, 141, 518, 150, glow, tag="view-enemy")
            oval(477, 189, 523, 231, shadow, edge, 2, "view-enemy")
            oval(487, 199, 513, 224, glow, tag="view-enemy")
            for x in (454, 536):
                for y in (183, 224, 239):
                    oval(x, y, x + 7, y + 7, "#c4af80", tag="view-enemy")
        elif any(word in kind for word in ("specter", "spectre", "wisp", "shadow", "spirit", "ghost")):
            poly((500, 126, 526, 153, 538, 208, 568, 256, 541, 253,
                  552, 285, 516, 269, 500, 299, 481, 270, 447, 287,
                  463, 252, 435, 260, 461, 211, 472, 153),
                 armor, shadow, 3, "view-enemy")
            oval(477, 146, 523, 197, shadow, tag="view-enemy")
            for x in (485, 508):
                oval(x, 166, x + 9, 174, glow, tag="view-enemy")
            line((477, 202, 457, 228, 428, 227), armor, 8, "view-enemy")
            line((523, 202, 543, 228, 572, 227), armor, 8, "view-enemy")
            line((487, 218, 481, 248), edge, 2, "view-enemy")
            line((514, 221, 523, 253), edge, 2, "view-enemy")
        else:
            bones = any(word in kind + " " + name for word in ("bone", "skeleton", "undead"))
            cloth = "#343943" if bones else shadow
            for x in (468, 511):
                poly((x, 235, x + 20, 235, x + 19, 282, x - 7, 291, x - 10, 279),
                     armor if bones else cloth, shadow, 2, "view-enemy")
            poly((462, 172, 485, 161, 515, 161, 538, 172, 532, 237,
                  512, 256, 488, 256, 467, 237), armor, shadow, 3, "view-enemy")
            line((471, 186, 451, 212, 435, 228), armor, 13, "view-enemy")
            line((529, 186, 552, 210, 561, 239), armor, 13, "view-enemy")
            oval(478, 119, 522, 166, "#c2bba2" if bones else armor,
                 shadow, 2, "view-enemy")
            for x in (486, 508):
                oval(x, 137, x + 8, 146, shadow if bones else glow, tag="view-enemy")
            if bones:
                line((488, 154, 514, 154), "#5b5b55", 2, "view-enemy")
                for y in (188, 201, 214):
                    line((478, y, 522, y), "#c0b89e", 4, "view-enemy")
                line((500, 181, 500, 228), "#b7af98", 4, "view-enemy")
            else:
                line((476, 179, 524, 228), "#4d5665", 6, "view-enemy")
            line((559, 220, 567, 126), "#a5b8be", 6, "view-enemy")
            line((548, 221, 572, 224), "#b59b63", 4, "view-enemy")
        if boss:
            poly((476, 125, 468, 99, 487, 109, 500, 88, 512, 109,
                  532, 99, 524, 125), "#bd9c5c", "#554831", 2, "view-enemy")
            for x in (482, 498, 514):
                oval(x, 114, x + 5, 119, glow, tag="view-enemy")

    def hands(class_id):
        sprite_key = hand_sprite_key(view)
        tags = (VIEW_TAG, "view-hands", "view-shield") if sprite_key == "sword_shield" else (VIEW_TAG, "view-hands")
        heavy = sprite_key in ("greatsword", "greataxe")
        if draw_sprite(canvas, sprite_key, width * (.65 if heavy else .5), height + 3 * sy,
                       width * (.67 if heavy else .97), height * (.88 if heavy else .96),
                       anchor="s", tags=tags):
            return
        glove = "#303b40" if not view.get("hidden") else "#1c292b"
        skin = "#af8d73"
        if class_id == "wizard":
            line((796, 400, 734, 196), "#6a4a37", 15, "view-hands")
            line((791, 399, 729, 195), "#a58255", 3, "view-hands")
            oval(713, 151, 751, 198, "#3f677c", "#a5d5df", 2, "view-hands")
            poly((731, 145, 746, 170, 732, 194, 718, 172),
                 "#9bd9e5", "#d2f4eb", 2, "view-hands")
            poly((735, 356, 775, 342, 810, 400, 722, 400), glove, "#15222b", 2, "view-hands")
            poly((734, 339, 755, 328, 770, 348, 742, 368), skin, "#5a4944", 2, "view-hands")
            poly((185, 400, 234, 348, 280, 352, 302, 400), glove, "#15222b", 2, "view-hands")
            line((239, 354, 224, 327, 232, 307), skin, 12, "view-hands")
            line((250, 352, 252, 315, 263, 307), skin, 11, "view-hands")
            oval(232, 281, 272, 307, "#91c9db", "#d1f1ec", 2, "view-hands")
        elif class_id == "rogue":
            for mirror in (False, True):
                def xx(x):
                    return 1000 - x if mirror else x
                poly((xx(166), 400, xx(210), 353, xx(260), 351, xx(293), 400),
                     glove, "#17212a", 2, "view-hands")
                poly((xx(218), 354, xx(236), 328, xx(257), 342, xx(255), 365),
                     "#887463", "#343136", 2, "view-hands")
                poly((xx(237), 331, xx(244), 289, xx(276), 239, xx(257), 303, xx(250), 340),
                     "#b7c5c7", "#52616b", 2, "view-hands")
                line((xx(225), 334, xx(262), 346), "#ad9058", 5, "view-hands")
        else:
            # These are class illustrations; the shield respects actual handedness.
            if not view.get("two_handed"):
                poly((113, 304, 166, 284, 231, 298, 243, 354, 188, 400,
                      145, 381), "#445766", "#162631", 4, "view-shield")
                poly((132, 315, 169, 302, 213, 313, 222, 350, 184, 381,
                      153, 366), "#647783", "#8d999a", 2, "view-shield")
                line((172, 305, 186, 379), "#b6a274", 4, "view-shield")
            else:
                poly((614, 400, 704, 350, 750, 350, 741, 386, 698, 400),
                     glove, "#17212a", 2, "view-hands")
                poly((724, 349, 758, 340, 773, 351, 757, 365, 734, 370),
                     "#8b7966", "#343136", 2, "view-hands")
            poly((737, 400, 754, 354, 798, 350, 837, 400),
                 glove, "#17212a", 2, "view-hands")
            poly((759, 354, 765, 324, 792, 332, 793, 367),
                 "#8b7966", "#343136", 2, "view-hands")
            poly((771, 328, 768, 226, 787, 183, 800, 227, 786, 334),
                 "#b1c3cc", "#465b68", 2, "view-hands")
            line((786, 203, 780, 322), "#e0e5dc", 2, "view-hands")
            line((750, 329, 807, 342), "#b49a60", 7, "view-hands")

    # A restrained frame keeps the art separate from the command terminal.
    rect(0, 0, 1000, 400, ceiling)
    if view.get("scene") == "shop":
        rect(0, 0, 1000, 285, "#272625", tag="view-sanctuary")
        poly((0, 281, 1000, 281, 1000, 400, 0, 400), "#44382d", tag="view-sanctuary")
        for x in range(0, 1001, 100):
            line((x, 0, x, 280), "#38352d", 2, "view-sanctuary")
        for x in (125, 665):
            rect(x, 90, x + 210, 231, "#1c2021", "#6e583e", 6, "view-sanctuary")
            for y in (135, 185, 233):
                rect(x - 5, y, x + 215, y + 8, "#72583b", "#312820", 1, "view-sanctuary")
            for row in range(2):
                for column, color in enumerate(("#6d9a85", "#a38771", "#6c8b9c", "#b29c5c")):
                    bx, by = x + 18 + column * 49, 101 + row * 50
                    rect(bx + 9, by - 7, bx + 17, by + 3, "#b8a57d", tag="view-sanctuary")
                    oval(bx, by, bx + 27, by + 28, color, "#1a2022", 2, "view-sanctuary")
        # The merchant's original raster portrait sits behind the counter.
        if not draw_sprite(canvas, "mira", 500 * sx, 235 * sy, 225 * sx, 202 * sy,
                           anchor="s", tags=(VIEW_TAG, "view-sanctuary")):
            poly((437, 212, 443, 142, 466, 112, 500, 101, 534, 112,
                  557, 142, 563, 212), "#38544d", "#182c29", 3, "view-sanctuary")
            oval(474, 120, 526, 174, "#bd9f82", "#4e4940", 2, "view-sanctuary")
            poly((473, 139, 478, 115, 503, 108, 527, 121, 528, 147,
                  515, 128, 487, 127), "#92978b", tag="view-sanctuary")
            for x in (485, 509):
                line((x, 143, x + 5, 143), "#3d4544", 2, "view-sanctuary")
            line((491, 158, 508, 158), "#876c5a", 2, "view-sanctuary")
            line((465, 182, 447, 220), "#4b6960", 20, "view-sanctuary")
            line((535, 182, 553, 220), "#4b6960", 20, "view-sanctuary")
        rect(292, 217, 707, 241, "#9e7850", "#3a2d25", 3, "view-sanctuary")
        poly((307, 241, 691, 241, 711, 315, 289, 315),
             "#644936", "#382a25", 3, "view-sanctuary")
        for x in (332, 419, 506, 593, 680):
            line((x, 246, x, 309), "#3e3027", 2, "view-sanctuary")
        oval(375, 204, 404, 216, "#c6a35e", "#6f5937", 2, "view-sanctuary")
        rect(602, 192, 626, 216, "#668e80", "#384e49", 2, "view-sanctuary")
        torch(71, 121, "view-sanctuary")
        torch(929, 121, "view-sanctuary")
        # The known sanctuary always has an onward/departure portal.
        portal(822, 244)
    else:
        poly((0, 0, 1000, 0, 740, 68, 260, 68), ceiling)
        rect(260, 68, 740, 273, wall)
        poly((0, 0, 260, 68, 260, 273, 0, 400), side)
        poly((1000, 0, 740, 68, 740, 273, 1000, 400), side)
        poly((0, 400, 260, 273, 740, 273, 1000, 400), ground)
        # Mortar on the far wall and perspective lines along the side planes.
        for row in range(5):
            y = 72 + row * 40
            line((262, y, 738, y), seam, 2)
            offset = 43 if row % 2 else 0
            for col in range(6):
                x = 278 + col * 86 + offset
                if x < 735:
                    line((x, y, x, min(y + 40, 273)), seam, 2)
        for y in (91, 140, 190, 239):
            t = (y - 68) / 205
            outer_y = t * 400
            line((0, outer_y, 260, y), seam, 2)
            line((1000, outer_y, 740, y), seam, 2)
        for x in (94, 182):
            for y1, y2 in ((0, 105), (119, 226), (244, 367)):
                line((x, y1 + x * 0.15, x, y2 - x * 0.12), seam, 1)
                line((1000 - x, y1 + x * 0.15, 1000 - x, y2 - x * 0.12), seam, 1)
        for x in (40, 220, 400, 600, 780, 960):
            line((500 + (x - 500) * 0.28, 273, x, 400), seam, 2)
        for y in (292, 324, 365):
            t = (y - 273) / 127
            line((260 * (1 - t), y, 740 + 260 * t, y), edge, 1)
        line((260, 68, 260, 273, 0, 400), edge, 2)
        line((740, 68, 740, 273, 1000, 400), edge, 2)

        exits = view.get("exits") or {}
        if exits.get("front"):
            arch(409, 81, 591, 276, "#4d5c64", seam)
            arch(426, 101, 574, 274, "#0a1118", edge)
            poly((426, 274, 574, 274, 594, 288, 405, 288), "#536168", seam, tag="view-exit")
            line((446, 145, 446, 269), "#192731", 2, "view-exit")
            line((554, 145, 554, 269), "#192731", 2, "view-exit")
        else:
            oval(465, 115, 535, 185, side, edge, 3)
            poly((500, 125, 521, 147, 510, 172, 490, 172, 479, 147), wall, edge, 2)
            line((500, 133, 500, 165), seam, 3)
        for mirror, relative in ((False, "left"), (True, "right")):
            if exits.get(relative):
                def xx(x):
                    return 1000 - x if mirror else x
                poly((xx(47), 136, xx(170), 137, xx(180), 157,
                      xx(180), 274, xx(47), 337), "#111b22", edge, 3, "view-exit")
                line((xx(57), 145, xx(161), 148, xx(168), 164,
                      xx(168), 270, xx(57), 320), "#33434d", 2, "view-exit")
        # Floor-specific motifs are authored geometry, not downloaded textures.
        if floor == 2:
            for mirror in (False, True):
                def xx(x):
                    return 1000 - x if mirror else x
                line((xx(32), 0, xx(84), 75, xx(71), 143, xx(135), 210,
                      xx(185), 267, xx(234), 310), "#475b3d", 10, "view-decoration")
                line((xx(84), 76, xx(153), 84, xx(186), 134), "#5d714b", 5, "view-decoration")
                for x, y in ((80, 92), (115, 197), (181, 259)):
                    poly((xx(x), y, xx(x + 31), y - 10, xx(x + 23), y + 12),
                         "#637b4d", tag="view-decoration")
        elif floor == 3:
            for x in (292, 694):
                line((x, 70, x, 246), "#86634b", 9, "view-decoration")
                for y in (100, 161, 220):
                    line((x - 7, y, x + 7, y), "#bd8756", 3, "view-decoration")
            for x in (337, 649):
                rect(x, 221, x + 26, 256, "#1f2021", "#6a4c3d", 3, "view-decoration")
                for gx in range(x + 5, x + 25, 7):
                    line((gx, 226, gx, 250), "#d48a49", 2, "view-decoration")
            line((302, 361, 333, 343, 321, 329, 355, 311), "#986049", 3, "view-decoration")
        elif floor == 4:
            for x, y in ((135, 25), (283, 38), (420, 17), (604, 39), (753, 24), (896, 41)):
                line((x - 3, y, x + 3, y), "#a0acc8", 1, "view-decoration")
                line((x, y - 3, x, y + 3), "#a0acc8", 1, "view-decoration")
            for x in (300, 684):
                poly((x, 110, x + 15, 93, x + 28, 112, x + 17, 153),
                     "#52566e", "#949bb8", 2, "view-decoration")
        elif floor == 5:
            for x in (298, 674):
                line((x, 82, x + 14, 133, x + 5, 182, x + 22, 252),
                     "#82545d", 7, "view-decoration")
                for y in (119, 176, 226):
                    line((x + 7, y, x + 34, y + 11), "#a26a72", 3, "view-decoration")
            oval(397, 298, 603, 350, "", "#9d6972", 2, "view-decoration")
            for i in range(8):
                a = i * pi / 4
                x, y = 500 + 84 * cos(a), 324 + 19 * sin(a)
                line((x - 4, y, x + 4, y), accent, 2, "view-decoration")
        else:
            line((294, 82, 306, 111, 296, 124, 313, 153), seam, 3)
            line((708, 201, 688, 214, 701, 239, 691, 260), seam, 3)

        torch(358, 145)
        torch(642, 145)
        features_visible = not view.get("in_combat") and not view.get("enemy")
        if features_visible and view.get("portal"):
            portal()
        if features_visible and view.get("loot"):
            poly((302, 269, 355, 260, 384, 273, 384, 298, 307, 300),
                 "#71543a", "#30271f", 3, "view-loot")
            poly((302, 269, 310, 250, 356, 245, 376, 256, 384, 273),
                 "#8b6845", "#30271f", 3, "view-loot")
            line((319, 253, 321, 296), "#b29862", 4, "view-loot")
            line((366, 257, 367, 296), "#b29862", 4, "view-loot")
            rect(341, 272, 350, 283, "#c6ae72", "#4c412d", 1, "view-loot")
        if features_visible and view.get("note"):
            poly((652, 281, 681, 275, 698, 293, 667, 302),
                 "#c4b38a", "#6e644d", 1, "view-note")
            for x in (666, 672, 678):
                line((x, 285, x + 10, 289), "#7a7158", 1, "view-note")
        if view.get("enemy"):
            foe(view["enemy"])
        hands(str(view.get("class_id", "fighter")))

    # A constant frame avoids animation, randomness, or hidden game-state reads.
    rect(0, 0, 1000, 400, "", "#0a1119", 7, "view-frame")
    if view.get("hidden") and view.get("scene") != "shop":
        line((5, 395, 5, 5, 995, 5, 995, 395), "#314d43", 5, "view-frame")
    if view.get("dead"):
        rect(2, 2, 998, 398, "", "#833e45", 6, "view-frame")
