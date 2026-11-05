"""All the numbers you may want to tune live here. Used by lua_patch.py and build_save.py."""

# ---- where the mat sits and how big it is (world units) -------------------------------------
CX, CZ = 0.25, 8.0               # board centre
BOUNDS_W = 29.4                  # width TTS reports for the whole board object, wooden frame included ("Mat width 29.4 OK")
IMG_W = 26.9                     # width of the printed image inside the frame; every slot position is computed from this
ASPECT = 4275 / 2175             # the 28_Inch skins (same aspect as the old universal mat)
STAGE_Z = 16.4                   # staging strip just above the mat, inside the cleanup zone

# ---- fine tuning (world units: +x right, +z up the screen). Rebuild the save after changing these ----
NUDGE_ALL = (0.0, 0.0)           # added to every slot
NUDGE = {}                       # per slot, e.g. {'wounds': (-0.2, 0.1), 'heroes': (0, -0.3)}

# ---- calibration measured in game -------------------------------------------------------------
# A board of scale MAT_REF_SCALE measured MAT_REF_WIDTH wide after loading (chat line "Mat fitted: width 31.7").
# The saved scale is MAT_REF_SCALE * BOUNDS_W / MAT_REF_WIDTH. If the load message ever reports a different width,
# put that scale and width here and rebuild.
MAT_REF_SCALE, MAT_REF_WIDTH = 0.6307, 31.7

# ---- slot centres as fractions of the mat image (u across, v down), read from the gridded 28_Inch_Template mats ---
# All nine 28_Inch skins share this layout. Horrors uses the unlabelled top-left box; Bindings and Pit are drawn over the logo band by
# make_mat_skins.py; Adversaries and Escape share the wide Escaped box; Villain K.O. receives the Scheme Twists and Master Strikes played from the Villain Deck; special Henchmen use the Pit position.
SLOT_UV = {
    'mastermind': (.2975, .4935), 'strike': (.202, .4935), 'scheme': (.2975, .186), 'twist': (.202, .186),
    'horrors': (.089, .186), 'bindings': (.545, .186), 'wounds': (.929, .186),
    'adversaries': (.417, .221), 'escape': (.417, .221), 'villains': (.929, .4935),
    'bystanders': (.8225, .186), 'shield': (.2975, .846), 'sidekick': (.202, .846), 'heroes': (.929, .846),
    'ko': (.0838, .846), 'henchspecial': (.645, .186), 'villainko': (.089, .4935), 'pit': (.645, .186),
}
CITY_U = [.407, .509, .611, .713, .815]      # Bridge .. Sewers (HQ/Lair uses the same columns)
CITY_V, HQ_V = .458, .80

# ---- mat art: the nine 28_Inch_Template images, made by make_mat_skins.py into TTS_work\\skins\\mat_skin_N.jpg ----
SKIN_NAMES = ['1 Heroes (orange)', '2 Venom (red)', '3 Dark grey', '4 Spider-Man', '5 Hulk', '6 Thanos', '7 X-Men', '8 Avengers', '9 Grey heroes']
MAT_SKIN = 1                     # which skin the save starts with (1-9)
SKIN_URLS = []                   # filled in by build_save.py: file:/// URLs of the copied skins

# ---- decks that start on the old board positions move onto their new slots in the save -----------
MOVES = {'22f0d7': 'shield', '15841b': 'bystanders', 'dab70e': 'wounds'}

# ---- cleanup zone over the mat (kept as tall as the original so the storage-row decks stay outside) --
ZONE = dict(posX=CX, posZ=8.05, rotY=0, scaleX=31.0, scaleZ=20.4)

# ---- player mats: the five Custom_Board objects, and where the official Player Mat PDF prints its piles ---------------
PLAYER_MATS = ['51edf5', '6212f9', '446b40', '17be32', '9d07a8']
PM_ASPECT = 2400 / 1697.7        # TTS_work\\playermat.png (make_player_mat.py)
PM_BOARD_H = 25.57               # world height of a Custom_Board at scale 1, frame included (measured from the main board)
PM_PRINTED_FRAC = 26.9 / 29.4    # printed image / framed object, as measured on the main board
# our own player mat (make_player_mat_v2.py): slot centres and the Played box as fractions of the image (u across, v down)
PM_VICTORY_UV, PM_DRAW_UV = (.1083, .2591), (.1083, .6832)
PM_ARTIFACTS_UV, PM_DISCARD_UV = (.8917, .2591), (.8917, .6832)
PM_PLAYED_BOX = (.2333, .0707, .7667, .6949)    # u0, v0, u1, v1: cards inside count as played and are swept by End Turn
PM_ATTACK_UV, PM_RECRUIT_UV = (.379, .848), (.621, .848)    # the Attack / Recruit counters are moved here at build time
PM_STARTER_DECKS = ['8bff16', '11148f', '973fd9', 'db28dc', 'bcc49a']   # one 12-card starting deck per seat
