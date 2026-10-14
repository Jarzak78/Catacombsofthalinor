"""Pure ASCII title artwork for terminal frontends."""


_FULL_TITLE = r"""                 CATACOMBS OF THALINOR
        ==============================================

                        .--^--^--.
                        \  V  V  /
                         '------'
                     .-'          '-.
                   .'     .----.     '.
                  /      / o  o \      \
          _______/       \  /\  /       \_______
         |  _  _ |        '----'        | _  _  |
         | | || ||     .----------.    || || | |
         | |_||_||    /            \   ||_||_| |
         |_______|   /              \  |_______|
            /|\  |  |      ___       | |  /|\
            |*|  |  |     |___|      | |  |*|
            |_|  |  |    /_____\     | |  |_|
             |   |  |   /_______\    | |   |
         ____|___|  |  /_________\   | |___|____
        /________|__|_/___________\__|_|________\

          Beneath the stones, a king still waits.""".splitlines()

_COMPACT_TITLE = r"""       CATACOMBS OF THALINOR
       ====================
             .-^-^-.
             '-----'
          .-'       '-.
         /    (o o)    \
        |      ^=      |
    /|\ |   .------.   | /|\
    |*| |   | ___  |   | |*|
    |_| |   /_____\   | |_|
     |  |  /_______\  |  |
    _|__|_/_________\_|__|_
     The depths await.""".splitlines()


def title_screen(width: int = 80) -> list[str]:
    """Return a title scene that fits the available terminal columns."""
    width = max(1, width)
    if width >= max(map(len, _FULL_TITLE)):
        return list(_FULL_TITLE)
    if width >= max(map(len, _COMPACT_TITLE)):
        return list(_COMPACT_TITLE)

    # Keep the game name readable even in an unusually narrow terminal.
    lines: list[str] = []
    current = ""
    for word in "CATACOMBS OF THALINOR".split():
        if current and len(current) + 1 + len(word) <= width:
            current += " " + word
            continue
        if current:
            lines.append(current)
            current = ""
        while len(word) > width:
            lines.append(word[:width])
            word = word[width:]
        current = word
    if current:
        lines.append(current)
    return lines
