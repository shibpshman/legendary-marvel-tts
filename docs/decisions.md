# Legendary Marvel TTS mod: decisions and status

Source: `cloud-session-transcript.txt` (CLI export of the cloud session `session_017T2dDTUJ2zPZwXgQPCX7tK`,
2026-10-14). The export covers only the later part of that session, from the scenario browser onward.
Earlier work (the 22-expansion build, player mat, turn flow, keyword glossary, icons) is visible only
through the commit history of branch `claude/adoring-hopper-02yzx7`.

## Decisions Stephen made

| Decision | Choice | Reason given |
|---|---|---|
| MCU and What If sets | Deliberately excluded from the mod, the audit and all recommendations | "they look ass" |
| Villains Core Set | Built as a normal 23rd expansion usable in ordinary random Setup, not only scenarios | "need to facilitate normal play as well" |
| Villains set extras | Starting Cards and the four extra Bystanders skipped | Only matter when playing the Villains game as designed |
| Heroes named "in Villain Deck" | Whole Hero deck is shuffled in | Same as the Trap Heroes scheme |
| "Use Villain Mat" scenarios | Setup runs as normal, prints a note | "villains play is essentially the same" |
| Two-Mastermind scenarios | Both in play, second above the Scheme slot with a snap point | Chosen over alternatives in a grill |
| Turn buttons | Top-centre bar | UI redesign |
| Panels | One tabbed panel docked right | Instead of four overlapping panels |
| Evil Wins tracker | Strip under the top bar | Visible during play |
| UI v2 order | Theme and no rebuilds, bar, tracker, Setup tab, Scenarios, Reference, Expansions | Icons and Hero/Villain/Henchman reference tabs deferred |

## Facts established

- Scenario source: `Marvel_History_Scenarios_v1.4_-_Venom_Dimensions_and_Revelations.pdf`, 780 scenarios,
  9 sections, 173 solo. Parsed by `build_scenarios.py` into `data/scenarios.json`.
- Card catalog: BGG wiki "Legendary Marvel Complete Card Text" (four pages, saved by hand because the
  cloud session's network blocks boardgamegeek.com). Parsed by `build_catalog.py` into `data/catalog.json`.
- Villains set vocabulary: Adversary = Villain, Backup Adversary = Henchman, Commander = Mastermind,
  Plot = Scheme, Bindings = Wounds, Overrun Pile = Escape Pile, Lair = HQ, Ally = Hero.
- Ambitions deck lives in the mat's Bindings slot (it was wrongly parked on the Escaped box).
- TTS Text defaults to `verticalOverflow=Truncate`, which caused the clipped last lines. The v2 theme
  sets wrap and no truncation.
- Library audit (offline simulation, not run in TTS after the last changes): 332 scenarios ready,
  189 waiting only on an expansion that can be switched on, 4 built by hand.

## Not yet verified in real TTS

Everything after the scenario browser was tested only in a Lua mock harness (`scripts/test_scenarios.py`
and the menu suite, 606 setups with 0 failures). Stephen's screenshots confirmed: the scenario panel and
audit render, Villains appears in Expansions, and the v1 top bar and dock layout. Not confirmed in game:

- Scenario Set up end to end, including two-Mastermind and single-card Villain group setups
  ("King Hyperion, with Dr. Doom", "On the Trail of the Amazing Spider-Man").
- UI v2: progress bar fill colour, `<textcolor>` rich text, the detail table scroll area, tooltips,
  greyed-out buttons, the 3 second poll.
- End Turn on real cards and the Evil Wins counters on every mat.

## Open work, in the last stated order

1. Shakedown: one full game, collecting chat errors and screenshots.
2. Remaining scenario notes: Phoenix/Magik/Dr. Strange swap (4), Hulk deck (3), other notes shown only.
3. Four scenarios still refused (Avengers/Defenders War, Avengers Under Siege, Civil War part 4,
   The Apocalypse Twins).
4. Campaign tracker: Won, Lost, Skipped per scenario, random unplayed button.
5. Hero, Villain and Henchman reference tabs from the catalog (about 400 KB, global script is already 623 KB).
6. Hand-setup Schemes: Secret Empire, Adam Warlock, the Wedding stacks, Divide and Conquer, and four
   Villains-set Plots.
7. Icons (needs a UI asset step, `file:///` support unknown), solo preset, undo for Play Villain Card.
8. Missing sets (excluding MCU and What If): Fear Itself adds 29 scenarios.
9. Villains-set keywords Demolish, Elusive and X-Treme Attack are only explained in
   `Villains Core Set Rules.pdf`, which has not been read.

## Known limits

- Crush HYDRA Plot needs New Recruits and Madame HYDRA from the Starting Cards, which are not built.
- New Heroes' own card text still uses Villains-set wording (Adversary, Commander Tactics).

## Played count (2026-11-03)

Gating question: do base-mod cards carry printed Attack / Recruit? No. A scan of `2410733963.json`
(4525 card objects) found no GMNotes, `Value` 0 on every card, Description on 11 (Deathbird's bag
note and the ten Mandarin's Rings), no card scripts, and tags holding only name / Hero / set / team /
class. The 66 `States` cards are transforming cards, not divided ones.

So the numbers come from the BGG export: `scripts/build_card_values.py` parses
`source-text/...Heroes And Allies.txt` (only the 24 sets the mod has, so Second Edition and Marvel
Studios reprints do not clash) and `...Complete Card Text.txt` (starting cards), applies
`data/card_aliases.json` (18 base-mod names that differ from the export, plus S.H.I.E.L.D. Agent and
Trooper) and writes `data/card_values.json`. All 797 Hero card names in the base mod resolve.

Decisions:
- Suggest, do not overwrite. Each player sees a "Played" line (visible to their colour only) with an
  Apply button that copies the totals into their Attack / Recruit counters. The counters stay manual.
- Apply turns amber ("Apply") while the counters by the mat differ from the Played totals and dim
  ("Applied") once they match; hand edits to a counter are noticed by the 3-second UI poll.
- Recount automatically on drop and pick-up (debounced 0.7 s), and after End Turn.
- "X+" cards (about 40% of Heroes) add the printed X and mark the total as a minimum ("6+").
  Divided cards are not counted; the line says how many to add by hand. Card bonuses are never evaluated.
- Played area = `tfPlayedOn(mat)`, split out of `tfEndTurn` so both use one definition; cards held in
  a hand are excluded.
- If the base Global defines `onObjectDrop` / `onObjectPickUp`, `lua_patch.py` renames it to
  `_base_...` and ours chains to it (reported in the build report either way).

The starting S.H.I.E.L.D. Agents and Troopers have no Nickname in the base mod; they are found by CardID
(`by_id` in `card_aliases.json`): decks 44-48 are the Player1-5Starter decks, index 03 = Agent (8 per
player), 05 = Trooper (4 per player). Inside a stacked Deck on the mat they still count as unknown,
because deck entries carry no CardID.

Not yet confirmed in game: the per-colour panels and their placement, and the event chaining.

## Player mat v2 (2026-11-05)

The official PDF mat is replaced by our own (`scripts/make_player_mat_v2.py`, writes `TTS_work\playermat.png`, keeps the
old one as `playermat_official.png`). Same pixel size and aspect, so the placement maths is unchanged.

- Zones: Victory, Draw, Artifacts (new, outside the sweep), Discard, a big Played box, and Attack / Recruit boxes.
- The zone positions live in `mat_config.py` (`PM_*`); the art script and `turn_lua.py` both read them.
- The Played area is now the printed box (`PM_PLAYED_BOX`), not "anywhere on the mat". The Played count and End Turn
  both use it through `tfPlayedOn`, so cards can be stacked or spread inside it.
- `build_save.py` moves each Attack / Recruit counter into its box on the nearest mat, and gives the 12 starting cards per
  seat a Nickname (S.H.I.E.L.D. Agent / Trooper) so they are counted inside a deck. This fixes the "starting cards in a
  stack show as not in the card list" limit.
- Background is generated, not art: navy gradient, a soft glow behind the Played box, faint halftone dots in the corners. A first version used cropped Hulk art from `boardA`; it was too busy behind the boxes.

Not confirmed in game: card size against the slots (slots are sized for about 2.2 x 3.1 world units), counter rotation
and height in their boxes, and whether the Played box is big enough for a long turn.

## Calibration, bags and side mats (2026-11-05)

- **Board and mat sizes, measured in game (2026-11-05).** The load check printed the real sizes (`--calibrate` build, `cal_lua.py`): board object
  33.62 x 17.10 at scale 0.5849, mat object 16.53 x 11.69 at scale 0.4. Both give a height of 29.2 per unit of scale, so `PM_BOARD_H` was stale
  (25.57), as was `MAT_REF_SCALE / MAT_REF_WIDTH` (0.6307 / 31.7). A top-down shot showed the visible art is 93 % of the object on both axes
  (31.2 of 33.62 wide, 15.9 of 17.10 high), and the computed slot positions then landed on the printed slots within a few pixels.
  Constants now: `PM_BOARD_H` 29.2, `PM_PRINTED_FRAC` 0.93, `IMG_W` 27.34 (0.93 x the intended 29.4 board width), board scale 0.5115.
  Earlier guesses (26.9, then 29.4) were partial fixes. Use `python build_save.py --calibrate` to re-measure; rebuild without it for the normal save.
- **Counter pads.** Attack, Recruit and Shards pads of a seat were chained with fixed joints; the build now releases them and puts each
  pad on its own box (`PM_ATTACK_UV`, `PM_RECRUIT_UV`, `PM_SHARDS_UV`). Pads face their seat (mat rotY + 180).
- **Seats.** Five hand zones (Red, Green, White front; Yellow left; Purple right) beside the mats; Orange, Pink, Blue removed.
- **Side mats** are both at z 7.25, with their cleanup triggers moved by the same amount.
- **Bags.** Four core bags stay in the back row; the other 24 are in two rows of 12, 5.0 apart.
- **Image names** carry a content hash (`playermat_<hash>.png`, `table_<hash>.png`) because TTS caches images by URL.
