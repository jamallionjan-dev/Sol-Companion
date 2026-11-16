"""Appends the 2026-11-15 first-run notes (s156b, s157, lab mod list) to DOCS/SOL_LEDGER.md once."""
import os
p = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "DOCS", "SOL_LEDGER.md"))
t = open(p, encoding="utf-8", newline="").read()
if "s157 phone_patience" in t:
    print("kept"); raise SystemExit(0)
nl = chr(13) + chr(10) if chr(13) + chr(10) in t else chr(10)
add = """

## 2026-11-15 - first in-game run of s152-s156 (Jamal, new world, LAB, Hotsco + EX on) and what followed
Runtime, his words (36-item list): PASS s152 magazine fill, Viewpoint corpse/car door, wardrobe tab/window/zoom/turn/list/search/
trial/apply/persist after reload, LF does not re-dress her, phone connection, no red errors. FAIL / notes below.

### s157 phone_patience (Mind switch, LAB on) - confirmed cause, offline PASS, runtime NOT tested
- Cause (sol_mind.log): the s155 card is ~6650 chars (was ~4600); the phone answered in ~5 s; the chat call waited 4 s. 28 of 31
  lines ended ProviderError('timeout') and fell to the word lists, which do not know the newer actions. Days before: 0-2 timeouts.
- Fix `apply_s157_phone_patience.py`: phone wait 12 s; model down + word lists empty -> `MR.offline_answer_s157` (example bank,
  similarity >= 0.85, plus the short forms he typed) through the normal route checks; the helicopter order without her name.
- Test `test_s157_phone_patience.py` 11/11. Cost: her answer takes ~5 s with the full card. `LIST_ALL_S155 = False` is the short card.

### s156b wardrobe 0.2.0 - offline PASS (45/45), runtime NOT tested
- His notes: no way out of a list without keeping a piece; no list for armor; a trial piece stayed after closing (the log shows
  4 take-backs on the window's own close, so another way of closing is the likely cause - inference).
- `edit_s156b_wardrobe_src.py`: "back, no change" in every list (header back leaves the list first); 15 lists (armor, vest, face,
  neck, hands, waist/bags, underwear added; unknown mod locations -> other); `WD.guard` takes a trial back when the window is
  gone by any way (tick) and on save. The per-part apply button is now inside the list.

### Hotsco - diagnosis (agent report, javap; no Java source for the body classes)
- confirmed: HNB keeps vanilla meshes but 414 clothingItems XML point m_FemaleModel at `HNBJavaMorph/Finished/*`, 278 swap
  m_BaseTextures to `hnb_surfacelink/*`. Sol's fitter (ClothingModels/AccessoryModels.select) takes whatever the winning XML
  names, so her garment starts from an HNB mesh shaped for Hotsco's chest and is fitted again: chest too big under mesh tops.
- confirmed (bytecode): HNB EX `Main.fail` latches `failed=true`; the log has one `NATIVE_IMPORT_NOT_VALIDATED
  model=garment_kate_trousers` at frame 140 between Sol's garment-fit lines -> EX morphing off for the session (trigger = inference).
- confirmed: `SolNPCAdapter.ok` gives the VSGirl body to every living female NPC IsoPlayer, not only Sol.
- not proven: why painted T-shirts change; the player's hair/shoes offset; the headless creation avatar.
- Plan (not built): remap to the vanilla model/texture names for private-body owners; tighten SolNPCAdapter.ok to the Sol marker.

### Lab mod list changed by Jamal in game (21:10), adopted on his word ("same current lab")
- +16: TombBody, TombBodyCompat, TombBodyCustom, TombBodyTexNUDE, TombFit, TombGothHair, TombGothMakeup, TombGothTexNUDE,
  TombWardrobeALT, SPNCCDetails, SPNCCDetailsHD, SpnCloth, SpnHair, SpnHairAPI, SpnOpenCloth, SpnOpenClothBase, FemaleModelFix, FH.
  -1: HotscoNewBodyEX (not in his list now). MODS_LAB_MIN.txt = his default.txt. His creation-screen screenshots (female: no
  head, shoes and hair off) were taken with THIS list, so they do not test the min list + Hotsco diagnosis.
- Backup `_backup/20261115_before_s157_and_modlist`. launch_lab.ps1 -CheckOnly: OK.
"""
open(p, "w", encoding="utf-8", newline="").write(t.rstrip(chr(13) + chr(10)) + add.replace(chr(10), nl))
print("appended")
