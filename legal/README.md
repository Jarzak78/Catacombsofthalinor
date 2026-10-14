# Licensing and content provenance

This directory records the third-party permissions used by Catacombs of
Thalinor. It is a maintenance record, not an assurance that every possible
copyright, trademark, patent, or publicity-rights issue has been cleared.
The project owner has not selected a general license for the separate
project-specific code, story, or artwork. Adding third-party notices does
not make the entire game CC BY or change the owner's licensing choice.
Recipients retain the permissions granted directly for third-party
material; no project-level terms may restrict those permissions.

## Rules references

The original project documentation referenced SRD 5.2. The current review
also checked the shared rules and the attribution in SRD 5.2.1. Both exact
official attribution statements are retained in [CREDITS.txt](../CREDITS.txt)
so that the historical reference is not silently replaced. This record
does not claim that every implemented rule comes from both versions, or
that the game implements every rule or correction in the later version.

Primary sources, reviewed on 2026-10-14:

- [Official SRD landing page](https://www.dndbeyond.com/srd).
- [SRD 5.2 PDF](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.pdf),
  page 1, Legal Information, including its required attribution statement.
- [SRD 5.2.1 PDF](https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf),
  page 1, Legal Information, including its required attribution statement.
- [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode),
  including attribution and indication of changes in Section 3(a), no
  downstream restrictions in Section 2(a)(5), no endorsement in Section
  2(a)(6), and the exclusion of trademark rights in Section 2(b)(2).
- [Official plain-text license](https://creativecommons.org/licenses/by/4.0/legalcode.txt),
  reproduced locally as [CC-BY-4.0.txt](CC-BY-4.0.txt). The license text
  itself is dedicated to the public domain by its publisher, as described
  in its closing notice.

Selected material used or adapted:

| Game material | Reference chapters | Implementation locations |
| --- | --- | --- |
| Ability scores, checks, initiative, attacks, critical hits, Advantage/Disadvantage, rests, and turn budgets | Playing the Game; Rules Glossary | `character_creation.py`, `combat.py`, `player.py`, `game.py` |
| Warrior/Fighter, Rogue, and Wizard features | Classes: Fighter, Rogue, Wizard | `player.py`, `game.py` |
| Named spells and selected spell effects | Spells | `player.py`, `game.py` |
| Weapon/armor profiles, weapon properties/masteries, and enchantment tiers | Equipment; Magic Items | `equipment.py`, `player.py`, `loot_library.py` |

This is a simplified solo adaptation. The change notice in CREDITS.txt
identifies the major house rules. The room-based campaign, five armor
slots, armor buffs, treasure probabilities, and shop prices must not be
presented as unchanged SRD rules. The project's item prose does not imply
that every custom item is a licensed tabletop item.

The SRD permission applies to material in those documents. A name,
illustration, monster, character, setting, or passage found in another
book or game is not covered merely because it is associated with the same
rules system. Keep marketing neutral and avoid official logos, branded
trade dress, or claims of official status. SRD attribution is not a
license to use another party's trademarks.

## Project content and dependencies

The present source contains project-developed lore in `floor_lore.py`
and `lore_notes.py`, dialogue in `campaign.py`, creature text in
`monster_catalog.py` and `enemy_lore.py`, and flavor text in
`battle_flavor.py` and `loot_flavor.py`. The entrance illustration and
torch animation are drawn in code in `entrance_art.py`; the terminal
entrance is ASCII in `title_screen.py`. No external image, music, or font
asset is intentionally supplied with this version. Interface fonts use
the user's installed system fonts.

This records the project's known sources; it is not proof that a name or
passage has never been used elsewhere. Development includes AI assistance.
Do not infer exclusive copyright in generated output or assign it a
fabricated human author. Preserve evidence of actual human contributions
and applicable service terms when making ownership or registration claims.

The Windows bundle contains third-party runtime software. The release
packaging process collects dependency license notices into this directory
from the actual build installation. Preserve those generated notices,
including any further third-party notices within Python's license file.
Do not replace them with only a list of website links. A build-tool
exception allowing redistribution of a packaged program is not a blanket
exception for all bundled dependencies.

In the Windows download, the whole installed Python license is retained
as `legal/runtime/Python-Windows-LICENSE.txt`, together with
`Python-incorporated-notices.rst`. The directory also contains the XZ,
PyInstaller, bootloader, runtime-hook, Apache 2.0, and GPL 2.0 notices,
plus `notice-manifest.json` identifying the collected files. A separate
`build-manifest.json` records the packaged native components and hashes.
Those generated records describe that particular build, not a generic
dependency version guessed from a different machine.

The Microsoft runtime redistribution terms retained in the Python Windows
license concern the Microsoft runtime components. Preserve and follow
those applicable terms; they do not select a new license for the game's
separate code, story, or artwork, or restrict the permissions granted for
the SRD material. Likewise, including a GPL notice for a build dependency
with a distribution exception does not itself apply the GPL to this game.

[END_USER_TERMS.txt](END_USER_TERMS.txt) passes through the Microsoft
runtime conditions described in the official CPython 3.12.10
[`PC/crtlicense.txt`](https://github.com/python/cpython/blob/v3.12.10/PC/crtlicense.txt).
The Windows packaged GUI shows a readable terms dialog and the terminal
launcher prompts for acceptance once per process before play. The
terminal option `--accept-runtime-terms` supplies explicit acceptance
for automation. Credits and license viewing remain available without
acceptance. Running this project's Python source does not add that prompt;
the interpreter installation has its own applicable licensing terms.

These narrow terms preserve the original notice separately and leave the
game's separate content, Python, other dependencies, and the CC BY grant
outside their scope. They are an implementation of the documented
pass-through conditions, not a conclusion that all possible Microsoft
requirements or other legal issues have received comprehensive review.

## Guidance for future changes

The owner has asked that licensing risks be flagged when new ideas are
suggested. Apply these checks during the normal implementation work; they
are not a separate approval gate for routine original or properly licensed
changes.

- Prefer project-created material or a clearly licensed source. For an
  imported asset, text passage, data table, font, sound, library, or code
  snippet, record its creator, original URL, version/date, license,
  permission evidence, required credit, modifications, and files using it.
- Check that permission covers the intended distribution, modification,
  and possible commercial use. Free to download, personal testing, a
  marketplace purchase, and credit alone do not establish those rights.
- Keep applicable attribution, copyright, license, and change notices with
  both source and packaged releases. Check new dependencies' transitive
  notices and any source-distribution obligations before bundling them.
  Recheck native runtime redistribution terms when changing the Python
  version or Windows toolchain; do not assume this build's terms cover
  all future components.
- Flag a concrete licensing or IP concern promptly, explain the evidence
  and uncertainty plainly, and offer an original or properly licensed
  alternative. Do not label an uncertain request illegal as a certainty.
  If adequate permission cannot be established, do not incorporate that
  external material while resolving the issue; continue unrelated work.
- Avoid another game's distinctive characters, setting, dialogue, artwork,
  logos, or music unless their use is authorized. Similar gameplay ideas
  do not authorize copying their creative expression or branding.
- Before a public commercial launch or a consequential ownership dispute,
  obtain an appropriate legal review, including a title/trademark search.
  No comprehensive trademark search for this game's title or names is
  recorded here. Preserve the owner's choice of the project's license;
  do not silently apply a license or claim all generated content is
  exclusively owned.

New provenance entries should be added below or linked to a dedicated
asset/source record in this directory. Keep the short contributor rules
in [AGENTS.md](../AGENTS.md) aligned with this record.
