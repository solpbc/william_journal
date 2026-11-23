#!/usr/bin/env python3
"""Build the person-face prompt set and the face/none list.

A face is owed only when an accepted day in content/weeks/*/merged/
tags the person (attendee) or (visible) on a meeting or a photo.
Calls, memos, notes and frames do not count, nor do (mentioned) or (heard).

Three further exclusions are policy, even if a tag would otherwise qualify:
william_shakespeare (§ 2.9, never his face), the_lady_unnamed (a face would
invite identifying her), and hired_men (three men in one entity).

Two people are included without an in-person meeting or photo tag, because a
person in a multi-person activity needs a face an agent can show (editor,
2026-11-22): john_florio (calls and mentions) and giles_allen (seen once at
the ditch; named on the 12 May lease imports).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PHOTOGEN_DIR = Path(__file__).resolve().parent
PROJECT = PHOTOGEN_DIR.parents[1]
WORLD_PATH = PROJECT / "world" / "world.md"
WEEKS = PROJECT / "content" / "weeks"
ENTITIES = PROJECT / "build" / "journal" / "entities"
YEAR_PROMPTS = PHOTOGEN_DIR / "prompts_year.json"
OUT_PROMPTS = PHOTOGEN_DIR / "prompts_faces.json"
OUT_REASONING = PROJECT / "photos" / "faces" / "reasoning.md"

SEE_KINDS = {"meeting", "photo"}
SEE_ROLES = {"attendee", "visible"}
POLICY_NONE = {
    "william_shakespeare": "§ 2.9: never his face, not a mirror, a reflection or a shadow.",
    "the_lady_unnamed": (
        "the editor's call, not world canon. A face would invite identifying her, "
        "and her § 3 rules forbid ruling that in or out."
    ),
    "hired_men": "Three men, William Blackwage, Ralph Raye and Richard Hoope, share one entity.",
}
# Included even when no meeting or photo tags them attendee or visible.
FACE_ALSO = ("giles_allen", "john_florio")
FACE_ALSO_HIT = {
    "giles_allen": {
        "date": "2025-05-12",
        "time": "16:20",
        "kind": "reading",
        "role": "mentioned",
        "title": "Memorandum of Giles Allen's Theatre lease heads",
        "place": "the_theatre",
        "file": "build/journal/facets/company/activities/20250512.jsonl",
    },
}

HEADING = re.compile(
    r"^## (\d{2}:\d{2}) · .+ · (meeting|call|memo|note|frame|photo) · (.+)$",
    re.M,
)
PEOPLE_LINE = re.compile(r"^- people: (.+)$", re.M)
PLACE_LINE = re.compile(r"^- place: ([a-z0-9_]+)\s*$", re.M)
PERSON_TAG = re.compile(r"([a-z][a-z0-9_]*) \((attendee|visible|mentioned|heard|participant)\)")
CAST_HEAD = re.compile(r"^#### `([a-z0-9_]+)` · (.+)$", re.M)

# sex, age told to the model, look, the candid action, light, one line for the sheet.
# Age is the 1595 model age. Where § 3 says "age unknown", the choice is named in reasoning.
CAST: dict[str, dict[str, str | int]] = {
    "abel_garnish": {
        "sex": "man", "age": 53,
        "look": "A fussy English book-keeper of 53. Thin grey hair combed across a high forehead, a small clipped grey beard, ink smudged on the right thumb and cuff, two plain brass pins in the lapel of a worn brown wool doublet. Narrow nose, watery grey eyes, no glasses.",
        "action": "He is pinning a folded paper part and whispering a correction, eyes on the page.",
        "light": "Daylight from a tiring-house doorway.",
        "who": "Book-keeper to the company, holder of the licensed book.",
    },
    "abraham_sturley": {
        "sex": "man", "age": 40,
        "look": "A precise Stratford alderman of 40. Pale indoor skin, receding dark-brown hair, a thin pointed brown beard kept very neat, a narrow scholarly face, grey-green eyes. A sober black gown over a plain falling band, no jewellery.",
        "action": "He is listening with a finger on a closed book, about to answer.",
        "light": "Cool daylight in a Wood Street parlour.",
        "who": "Alderman, Quiney's ally, a scholarly man of malt and Cicero.",
    },
    "agnes_tipping": {
        "sex": "woman", "age": 45,
        "look": "Hostess of an ordinary, 45, built solid from years of carrying pots. Red-brown hair under a linen cap pushed back, a broad ruddy face, laugh-lines, strong forearms, a stained canvas apron over russet wool. Not the same face as Alice Brambleby: rounder, warmer, louder.",
        "action": "She is wiping a trestle with one hand and talking to someone off to her left.",
        "light": "Firelight and a little daylight from the Jackdaw's door.",
        "who": "Hostess of the Jackdaw in Holywell Lane.",
    },
    "alice_brambleby": {
        "sex": "woman", "age": 41,
        "look": "Keeper of a smaller ordinary, 41. Darker and finer-boned than Agnes Tipping: straight black-brown hair under a close white cap, a long oval face, cool brown eyes, a thin mouth that can stop a room. Dark green wool, a clean apron, no rouge.",
        "action": "She is setting a wooden cup down and looking at the man who must pay, not at the camera.",
        "light": "Daylight through small leaded panes at the Split Hazel.",
        "who": "Keeper of the Split Hazel, near Bishopsgate.",
    },
    "alse_pinder": {
        "sex": "woman", "age": 16,
        "look": "A Hertfordshire maid of 16, not a child and not a grown woman of thirty. Fair mouse-brown hair escaping a linen cap, freckles across the nose, round young cheeks, grey eyes, quick. Plain blue-grey wool kirtle, sleeves rolled, a wooden basin in her hands.",
        "action": "She has paused on the stair with the basin, listening to a voice below.",
        "light": "Thin daylight on the lodging stair.",
        "who": "Mistress Ansell's maid, sixteen, from Hertfordshire.",
    },
    "ambrose_kettleby": {
        "sex": "man", "age": 44,
        "look": "A gentleman usher of 44 who has stood behind chairs for twenty years. Smooth olive-fair skin, dark hair silvering at the temples only, a neat small beard and moustache, heavy-lidded amused eyes. Black velvet, a plain linen band, no chain and no letters.",
        "action": "He stands just behind a chair, one hand on its back, watching the room with a faint amusement.",
        "light": "Candlelight in a chamber at court.",
        "who": "Gentleman usher to the Lord Chamberlain.",
    },
    "anne_shakespeare": {
        "sex": "woman", "age": 39,
        "look": "Anne Hathaway at 39, wife and manager of a house of nine. Dark brown hair mostly under a linen coif, a few strands at the temple, hazel eyes, a sharp intelligent face, not a portrait beauty. Work-strong hands, a grey-green kirtle, a practical apron. Warwickshire, kin to her brother Bartholomew in the dark hair and the straight nose, and to her daughter Susanna in the watchful eyes.",
        "action": "She is counting malt measures on a table and speaking to someone across it.",
        "light": "Daylight in the Henley Street kitchen.",
        "who": "Anne Shakespeare, his wife, at Henley Street.",
    },
    "arthur_meeks": {
        "sex": "boy", "age": 14,
        "look": "A boy player of 14, tall for his age and shooting up, all wrists and ankles. Dark hair cut to the nape, a long sardonic young face, dark eyes, a new thin shadow on the upper lip that is not yet a beard. A let-down hem on a faded blue doublet. Distinct from Nick, who is small and still, and from Sam, who is fair and round.",
        "action": "He is mimicking someone offstage, mouth twisted, eyes on a colleague, one long wrist raised.",
        "light": "Daylight in a Southwark tiring-room.",
        "who": "Second boy, lodged with Thomas Pope. Plays Rosaline and Lady Capulet.",
    },
    "augustine_phillips": {
        "sex": "man", "age": 34,
        "look": "A musician-sharer of 34. Warm medium-brown skin with a sun touch, wavy chestnut hair a little longer than the other sharers, a soft short beard, kind heavy-lidded eyes, a gentle mouth. A russet doublet, a lute under his arm. Not Burbage's oval intensity and not Pope's bulk.",
        "action": "He is tuning a lute, head tilted to the string, not performing for anyone.",
        "light": "Late daylight in a Southwark room.",
        "who": "Sharer and musician. Master of Sam Latchet.",
    },
    "barnaby_yaxley": {
        "sex": "man", "age": 50,
        "look": "A barber-surgeon of 50, cheerful about other people's pain. Balding crown with a fringe of sandy-grey hair, a short bristly beard, florid cheeks, bright small blue eyes, thick neck. Shirt sleeves rolled, a leather apron, no blood anywhere in the frame.",
        "action": "He is wiping a steel razor on a cloth and talking, eyes on the man in the chair who is out of frame.",
        "light": "Shop daylight on Bishopsgate Street.",
        "who": "Barber-surgeon in Bishopsgate. Draws the tooth in October.",
    },
    "bartholomew_hathaway": {
        "sex": "man", "age": 36,
        "look": "Anne's brother, a Shottery farmer. § 3 gives no age; cast at 36. Weathered fair-ruddy skin, dark brown hair like his sister's, a short unkempt beard, outdoor squint, broad farmer's shoulders, mud at the hem of a homespun coat. Fewer words in the face than Anne: heavier jaw, sunburned.",
        "action": "He is leaning on a gate with a cup, looking at a field, not at the camera.",
        "light": "Open daylight at Hewlands.",
        "who": "Anne's brother, a farmer at Hewlands in Shottery.",
    },
    "cuthbert_burbage": {
        "sex": "man", "age": 30,
        "look": "James Burbage's elder son, 30, not a player. The family likeness is the dark hair and the heavy straight brow, but he is clean-shaven, paler from indoors, narrower in the shoulder than his brother Richard, with a lawyer's still mouth. Black wool, a paper in his hand, no theatrical beauty.",
        "action": "He is reading a letter he does not like, one finger under the line.",
        "light": "Daylight in the Holywell house.",
        "who": "The business son. Gatherers, repairs, and the letters to Giles Allen.",
    },
    "davy_gannet": {
        "sex": "man", "age": 58,
        "look": "A Thames waterman of 58, a veteran of 1588. Deep windburn, a wild grey beard that is not John Shakespeare's neat one, salt in the eyebrows, a squint from river glare, a broken nose, thick neck. A plain kerchief, a tar-stained coat. No uniform.",
        "action": "He is holding a boat's gunwale and shouting a fare to someone up the stair.",
        "light": "Hard daylight at Old Swan Stairs.",
        "who": "His waterman at Old Swan Stairs.",
    },
    "dorcas_ansell": {
        "sex": "woman", "age": 52,
        "look": "A scrivener's widow and landlady, 52. Grey-streaked dark hair under a severe linen coif, a sharp nose, bright suspicious brown eyes, a firm small chin. Keys at her belt, a dark gown, London not country. Older and sharper than Agnes, nothing of Anne's warmth.",
        "action": "She has stopped on the landing with the keys in her hand, listening upward.",
        "light": "Daylight in the Great St Helen's stairwell.",
        "who": "His landlady at Mistress Ansell's house.",
    },
    "edith_kettlewood": {
        "sex": "woman", "age": 27,
        "look": "An independent seamstress of 27. Dark hair in a neat cap, a fine narrow face, straight brows, grey eyes, precise small mouth, slim hands. A clean grey kirtle, a needle trailing thread, no jewellery. Younger and quieter than Margery Pell.",
        "action": "She is biting a thread and looking at a seam, not at anyone.",
        "light": "Window daylight in a rented Shoreditch room.",
        "who": "Seamstress and mender to the company.",
    },
    "edmund_shakespeare": {
        "sex": "boy", "age": 15,
        "look": "Youngest Shakespeare brother, 15, stage-struck and not yet a player. Brown hair too long at the collar, no beard, an eager open face, hazel eyes like the family, a splash of freckles. A plain country doublet a little short in the arm. Kin to Hamnet but five years older, and not a twin of anyone.",
        "action": "He is reciting to a rain-barrel, mouth open on a line, eyes on the water.",
        "light": "Daylight in the Henley Street yard.",
        "who": "Youngest brother, at Henley Street. Not in the company this year.",
    },
    "edmund_tilney": {
        "sex": "man", "age": 59,
        "look": "Master of the Revels, 59. Long tired face, grey hair under a flat cap, a thin grey moustache and small beard, heavy lids, a bored cultivated mouth. Black gown, a goose quill with red ink on the nib. No paper with readable words.",
        "action": "He is dipping the quill and looking at a manuscript whose writing is only smudges.",
        "light": "Cool daylight at St John's, Clerkenwell.",
        "who": "Master of the Revels. Licenses the plays.",
    },
    "edward_alleyn": {
        "sex": "man", "age": 29,
        "look": "Edward Alleyn at 29, six foot even when seated in the crop by the length of his neck. Anchored on the Dulwich portrait: long face, high forehead, dark brown hair, a pointed beard and moustache, deep-set eyes, a mild offstage expression rather than a tragic roar. The portrait is later, so the skin here is younger. A dark doublet, no crown and no stage paint.",
        "action": "He is paused at a tiring-house stair with a pot of small beer, listening, one hand on the rail.",
        "light": "Daylight outside the Rose.",
        "who": "The Rose's star, Admiral's Men. Six foot, mild offstage.",
        "anchor": "Dulwich portrait of Edward Alleyn, read back to age 29.",
    },
    "edward_hoby": {
        "sex": "man", "age": 35,
        "look": "Sir Edward Hoby, 35, a scholar-courtier. Dark auburn hair, a short fashionable beard, a long assured face, watchful brown eyes, a silky half-smile that is not for the camera. Black satin and a small linen ruff with no embroidery that forms a letter.",
        "action": "He is turning to speak to a guest, cup in hand, at his own supper table.",
        "light": "Candlelight and fire at Canon Row.",
        "who": "Host at Canon Row. Hunsdon's son-in-law.",
    },
    "elizabeth_i": {
        "sex": "woman", "age": 62,
        "look": "Queen Elizabeth at 62, the Ditchley type of the early 1590s and not the young queen. Very pale skin, a high forehead, a curled red-gold wig, thin arched brows, a small tight mouth, dark eyes. A wired linen ruff, pearls, a dark gown. No crown letters, no motto, no readable jewel.",
        "action": "She is in profile behind a barrier at the tilt, watching the field, one hand still.",
        "light": "Hard November daylight at Whitehall.",
        "who": "The queen. Seen, almost never heard.",
        "anchor": "Ditchley-type portrait, about 1592, at her age in 1595.",
    },
    "george_bryan": {
        "sex": "man", "age": 40,
        "look": "A grave courtly sharer of 40. Long upright face, brown hair greying cleanly at the temples, a close beard trimmed square, calm grey eyes, a straight back even in a crop. Dark clothing of good wool, nothing flashy. Older and stiller than Heminges, less bulk than Pope.",
        "action": "He is standing in a great chamber as if the chair were occupied, eyes on the empty chair.",
        "light": "Cool daylight.",
        "who": "Sharer. The company's ambassador in a great chamber.",
    },
    "george_peele": {
        "sex": "man", "age": 39,
        "look": "An old playwright at 39 who already looks shabby. Thinning dark hair, a week's uneven beard, hollow cheeks, witty tired eyes, a frayed grey doublet, a manuscript rolled under his arm with no readable title. Not Nashe's hungry sharpness: Peele is worn, not electric.",
        "action": "He is walking and talking, the manuscript clamped under his arm, eyes on his companion.",
        "light": "November daylight in a London street.",
        "who": "Playwright. Seen on Accession Day with a manuscript under his arm.",
    },
    "gilbert_shakespeare": {
        "sex": "man", "age": 29,
        "look": "A journeyman haberdasher of 29, William's brother in London. Family brown hair and hazel eyes, but a city cut: short neat beard, cleaner collar, a felt-merchant's eye for cloth, less sun than the Stratford brothers. A decent tawny doublet, buttons of bone.",
        "action": "He is pricing a length of felt between his fingers, talking without looking up.",
        "light": "Shop daylight near the Fleet.",
        "who": "Brother. A haberdasher lodging in St Bride's.",
    },
    "giles_allen": {
        "sex": "man", "age": 60,
        "look": "A gentleman landlord of about 60, seen once across a ditch and never spoken with. Pale indoor skin, thin grey hair, a small pointed grey beard, a narrow cold face, light eyes that do not warm. A plain black gown of better cloth than the players wear, clean hands, no jewellery and no weapon.",
        "action": "He is standing on his own side of a muddy ditch, looking at timber, not at the camera.",
        "light": "Open daylight at the Holywell ditch, the Theatre behind him out of focus.",
        "who": "Ground landlord of the Theatre. William sees him once and never speaks with him.",
    },
    "gillis_verbeke": {
        "sex": "man", "age": 34,
        "look": "A Flemish silk-weaver of 34, a stranger. Flaxen hair, pale blue eyes, a long narrow devout face, a small light beard, careful mouth, weaver's stained fingertips. A plain grey jerkin, foreign in the cut of the collar, nothing English-brown about him.",
        "action": "He is holding a pin and a scrap of silk up to the light, concentrating.",
        "light": "Window light in the ground-floor back room.",
        "who": "Fellow lodger. A Flemish silk-weaver.",
    },
    "hamnet_sadler": {
        "sex": "man", "age": 34,
        "look": "A baker of 34, the twins' godfather. Big hands, flour in a full brown beard and on the eyebrows, a broad genial slow face, ruddy, thick neck, small kind eyes. A linen cap dusted white, shirt open at the throat. His wife Judith is quicker and unbearded beside this bulk, and she is not in the frame.",
        "action": "He is turning a loaf on a peel, eyes on the crust.",
        "light": "Warm bakehouse light and fire.",
        "who": "Baker on the High Street. The twins' godfather.",
    },
    "hamnet_shakespeare": {
        "sex": "boy", "age": 10,
        "look": "A boy of 10, Judith's twin. Tousled mid-brown hair, freckles, a loud open mouth, scratched knees out of the crop, hazel eyes, a smudge on the cheek. A plain child's doublet. He shares his twin's colouring but his face is broader and his hair is a mess. A real ten-year-old, not a small adult.",
        "action": "He is crouched over a little wooden wheel and string, explaining it to someone off-frame.",
        "light": "Daylight in the Henley Street yard. No church and no churchyard.",
        "who": "His son, ten. Loud, kind, a runner.",
    },
    "henry_carey_hunsdon": {
        "sex": "man", "age": 69,
        "look": "Henry Carey, Lord Hunsdon, at 69. The late portrait: a blunt soldier's face, bushy grey beard, weathered red-brown skin, small fierce eyes, a thick nose, a plain wired ruff, a dark gown with fur. Loud even when the mouth is shut. No Garter lettering and no readable chain.",
        "action": "He is mid-sentence at a supper, turned to bark at someone on his right.",
        "light": "Candlelight.",
        "who": "The Lord Chamberlain, his patron. Sixty-nine.",
        "anchor": "The late portrait of Henry Carey, 1st Lord Hunsdon.",
    },
    "henry_wriothesley_southampton": {
        "sex": "man", "age": 22,
        "look": "Henry Wriothesley, Earl of Southampton, at 22. Anchored on the early-1590s portrait of him as a young man: long chestnut hair worn loose over one shoulder, a long delicate face, small mouth, light eyes, no beard, a pearl in one ear, a black doublet and white linen. Young, not a bearded courtier of thirty. Distinct from Essex, who wears a pointed beard.",
        "action": "He is turning his head to a voice at his left, hair falling, not posing.",
        "light": "Daylight at a barrier, Accession Day.",
        "who": "Earl of Southampton, 22. Dedicatee of both poems.",
        "anchor": "The early-1590s portrait: long hair over one shoulder, no beard.",
    },
    "humphrey_larkham": {
        "sex": "man", "age": 29,
        "look": "A hired player and copyist of 29. Ordinary where the sharers are not: sandy hair, a short patchy beard, a square freckled face, pale lashes, ink on the fingers, a cheap grey-green doublet with a mended elbow. Not Sincler's starvation and not Sly's beauty.",
        "action": "He is checking a tally, lips moving on the figures, a blank scrap in his hand.",
        "light": "Daylight in a Shoreditch room.",
        "who": "Hired player, gatherer, and second copyist under Garnish.",
    },
    "jacqueline_field": {
        "sex": "woman", "age": 42,
        "look": "French, 42, Vautrollier's widow. Dark hair dressed close under a black cap, olive skin, controlled dark eyes, a firm jaw, no English rosiness. A black gown of good cloth, a plain linen partlet, keys and a shop's authority. Older than Edith, finer than Margery, nothing like Anne.",
        "action": "She is correcting a line of figures on a shop slate whose marks are smudges, not numerals.",
        "light": "Daylight in the Blackfriars printing house.",
        "who": "Richard Field's wife. Runs the shop's accounts.",
    },
    "james_burbage": {
        "sex": "man", "age": 64,
        "look": "James Burbage at 64, joiner and owner of the Theatre. The father's version of Richard's face: heavier, lined, grey beard full and square, oak dust in the eyebrows, a brawler's thick brows, brown eyes gone paler. A workman's doublet under a householder's gown. Smells of the yard even in a picture.",
        "action": "He is jabbing a finger at a timber length while he talks about a lease.",
        "light": "Daylight in the Holywell hall.",
        "who": "Owner of the Theatre. Father of Richard and Cuthbert.",
    },
    "joan_shakespeare": {
        "sex": "woman", "age": 26,
        "look": "His sister Joan at 26, unmarried, in the kitchen. Brown hair in a practical braid under a cap that has slipped, hazel eyes, a lively candid face, a quicker smile than Anne's and a rounder cheek than Mary's. A spinning woman's wool dress, flour nowhere. Family likeness, her own face.",
        "action": "She is teasing someone across a table, chin up, a spindle idle in her hand.",
        "light": "Kitchen daylight at Henley Street.",
        "who": "His sister. Runs the kitchen with Mary and spins.",
    },
    "john_florio": {
        "sex": "man", "age": 42,
        "look": "Southampton's Italian tutor at 42, sixteen years before William Hole's engraving. Swarthy skin, dark hair still thick and receding only at the temples, a nearly pointed dark beard, a mobile mouth, wide alert eyes, the first horizontal lines across the brow. A dark scholar's gown. A slip of paper in his hand with no readable word. The face is Mediterranean. Not an English courtier.",
        "action": "He is correcting a word on the slip, eyes on the paper, mouth already forming the next synonym.",
        "light": "Daylight from one small window in a Holborn closet.",
        "who": "Italian tutor and lexicographer in the Earl of Southampton's household.",
        "anchor": "William Hole's 1611 engraving, read back to age 42: pointed beard, dark eyes, swarthy skin.",
    },
    "john_harrison": {
        "sex": "man", "age": 60,
        "look": "A Paul's Churchyard bookseller of 60. Round genial face, grey hair, a tidy grey beard, shrewd pouchy eyes, a comfortable stomach, ink-free soft hands. A bookseller's black gown, no title visible on any book near him.",
        "action": "He is weighing a small unbound book in one hand and talking about its sale.",
        "light": "Daylight under the Churchyard shed.",
        "who": "Publisher at the White Greyhound. Holds Venus and Lucrece.",
    },
    "john_heminges": {
        "sex": "man", "age": 29,
        "look": "John Heminges at 29, the company's man of account. Solid, not fat. Neat mid-brown hair, a short disciplined beard, steady brown eyes, a grocer's clean collar, calm mouth. A good brown doublet. Younger and squarer than Bryan, nothing of Kemp's comedy.",
        "action": "He is counting coins into his palm, eyes down, mouth about to say the missing expense.",
        "light": "Daylight at a trestle.",
        "who": "Sharer. Holds the stock. Nick lodges in his house.",
    },
    "john_shakespeare": {
        "sex": "man", "age": 65,
        "look": "His father at 65, a glover. Merry-cheeked, as the tradition says: grey-brown hair thin on top, a full soft grey beard, weather and drink in the cheeks, teasing eyes, thick scarred hands. A leather apron over an old doublet. The family's older face, broader than Gilbert's.",
        "action": "He is paring a scrap of kid leather and joking, eyes on the knife.",
        "light": "Workshop daylight at Henley Street.",
        "who": "His father. Glover and whittawer at Henley Street.",
    },
    "john_sincler": {
        "sex": "man", "age": 29,
        "look": "The thin one, 29, a walking famine. Extremely narrow face, long neck, visible tendons, dark hair flat to the skull, almost no beard, large dark eyes, a wry mouth. A doublet that hangs. No other man in the set is this thin.",
        "action": "He is eating bread with concentration, and it has not changed him.",
        "light": "Daylight in Bishopsgate Without.",
        "who": "Hired man. Cast when a part needs a walking famine.",
    },
    "john_spencer": {
        "sex": "man", "age": 58,
        "look": "Sir John Spencer, Lord Mayor, about 58. Austere merchant's face, iron-grey hair, a square-cut grey beard, thin lips, cold eyes, a heavy plain gold chain with no letters, no badge and no motto. Black and fur. Rich, and not pleased.",
        "action": "He is looking out from a stone porch at a street he disapproves of.",
        "light": "Winter daylight at Crosby Place.",
        "who": "Lord Mayor until 28 October. Lives at Crosby Place.",
    },
    "josias_thwaite": {
        "sex": "man", "age": 60,
        "look": "Curate of St Helen's, 60. Thin, ascetic, white-grey hair, a long naked upper lip with only a wisp of beard, deep-set eyes, a sermon-worn throat. A plain black gown and a white band. No cross large enough to read, no book title.",
        "action": "He is watching a sand-glass and still speaking, eyes on the glass.",
        "light": "Dim church daylight, not a churchyard.",
        "who": "Reader and curate at St Helen's.",
    },
    "judith_sadler": {
        "sex": "woman", "age": 33,
        "look": "A baker's wife of 33, quicker than her husband. Flour on a strong forearm, brown hair under a cap, an amused narrow face, dark eyes, a fast mouth. Not Anne, not Joan: a townswoman in her own kitchen authority, slimmer than Agnes.",
        "action": "She is working dough and arguing at the same time, eyes on her hands.",
        "light": "Bakehouse daylight.",
        "who": "The baker's wife. The twins' godmother.",
    },
    "judith_shakespeare": {
        "sex": "girl", "age": 10,
        "look": "A girl of 10, Hamnet's twin. Same mid-brown hair and freckles, but her face is narrower, her braid is tidy, and her expression is a tease about to land. Hazel eyes. A child's kirtle and a small linen cap. A real ten-year-old girl.",
        "action": "She is mimicking an adult's walk in miniature, chin high, watching to see if it landed.",
        "light": "Kitchen daylight at Henley Street. No church and no churchyard.",
        "who": "His younger daughter, ten. Hamnet's twin.",
    },
    "margaret_hoby": {
        "sex": "woman", "age": 36,
        "look": "Margaret, Lady Hoby, 36, Hunsdon's daughter. Composed, fair-brown hair dressed high with no modern pins that show, a broad frank brow that recalls her father without his beard, grey eyes, a practical mouth. A good dark gown and a modest ruff, candlelight on pearls that are not lettered.",
        "action": "She is placing a chair and looking across the room to see if it will do.",
        "light": "Firelight and candles at Canon Row.",
        "who": "Hostess at Canon Row. Hunsdon's daughter, Hoby's wife.",
    },
    "margery_pell": {
        "sex": "woman", "age": 47,
        "look": "Gatherer at the gallery stair, 47. A broad capable face, grey-brown hair under a coif, sharp counting eyes, a ruddy nose, a strong jaw. A heavy wool gown, a leather purse, nothing pretty about the job. Older and coarser than Edith, less tavern-warm than Agnes.",
        "action": "She is taking a coin at the stair and already looking at the next face in the queue, which is out of frame.",
        "light": "Daylight on the gallery stair.",
        "who": "Gatherer at the gallery stair. Knows every face and what it paid.",
    },
    "mary_shakespeare": {
        "sex": "woman", "age": 57,
        "look": "His mother at 57. Soft where John is merry-cheeked: grey-brown hair entirely under a linen coif, fine bones, calm grey eyes, a small exact mouth, gentry stillness she never mentions. A dark gown, keys. The oldest woman of the Henley Street household, and not Dorcas's London sharpness.",
        "action": "She is setting down a bowl and answering someone with a look, not a speech.",
        "light": "Soft daylight at Henley Street.",
        "who": "His mother, Mary Arden, at Henley Street.",
    },
    "michael_drayton": {
        "sex": "man", "age": 32,
        "look": "A Warwickshire poet of 32, met at the stalls. Friendly outdoor brown, a short untidy beard, bright competitive eyes, hair the colour of a hedge, a decent but not rich doublet. More sun than Samuel Daniel, less hunger than Nashe.",
        "action": "He is standing at a bookstall with a closed book, talking, a half-smile that is slightly competitive.",
        "light": "Daylight in Paul's Churchyard.",
        "who": "A Warwickshire poet at Paul's. Not the Rival Poet.",
    },
    "nick_sorrell": {
        "sex": "boy", "age": 15,
        "look": "Leading boy, 15. Small, dark-eyed, small-boned, a fierce still concentration. Straight black-brown hair, a grave narrow face, no beard, a boy's smooth throat. A careful dark doublet. The opposite of Arthur's height and of Sam's softness.",
        "action": "He is reading a part under his breath, one finger on a smudged line, eyes down.",
        "light": "Window light at Aldermanbury.",
        "who": "Leading boy, bound to Heminges. Plays Juliet and the queens.",
    },
    "philip_henslowe": {
        "sex": "man", "age": 40,
        "look": "Owner of the Rose, about 40. Affable and calculating: a broad face, thinning brown hair, a short practical beard, pawnbroker's eyes, dye-stained fingers, a comfortable lined forehead. A plain wealthy doublet, shorter in the neck than Alleyn and heavier in the cheek.",
        "action": "He is tapping a table while he adds a sum in his head, eyes on his own fingers.",
        "light": "Daylight on Bankside.",
        "who": "Dyer, pawnbroker, and owner of the Rose.",
    },
    "richard_burbage": {
        "sex": "man", "age": 27,
        "look": "Richard Burbage at 27. Anchored on the Dulwich portrait, taken younger: dark brown hair, a small moustache and pointed beard, an oval face, dark lively eyes, a generous mouth, colour in the cheeks. An actor's energy in the hands. Smoother skin than the later portrait. Kin to his father and to Cuthbert in the brow, and unlike both in the light in the face.",
        "action": "He is on his feet with a rolled paper he will not let be read to him, speaking a line to someone off-frame, eyes on that person.",
        "light": "Daylight in the tiring-house.",
        "who": "Leading player and sharer. Berowne, Richard, Romeo.",
        "anchor": "Dulwich portrait of Richard Burbage, read back to age 27.",
    },
    "richard_cowley": {
        "sex": "man", "age": 27,
        "look": "A hired player of 27, Kemp's straight man. A worried oval face, thin brown hair, almost no beard, raised brows, a high anxious forehead, a narrow chest. A plain doublet. Deadpan, not handsome like Sly and not starved like Sincler.",
        "action": "He is waiting for a cue, lips parted, eyes on Kemp who is out of frame.",
        "light": "Daylight at rehearsal.",
        "who": "Hired player, not a sharer. Kemp's straight man.",
    },
    "richard_field": {
        "sex": "man", "age": 34,
        "look": "A Stratford tanner's son turned printer, 34. Family-adjacent brown hair and a dry mouth, but a printer's slight stoop, blackened nails, a short sober beard, Huguenot-house neatness. Dark clothes. Not as weathered as his Stratford cousins.",
        "action": "He is looking at a pulled sheet whose type is only black smudges, deciding.",
        "light": "Workshop daylight at Blackfriars.",
        "who": "Printer at Blackfriars. Printed Venus and Lucrece.",
    },
    "richard_quiney": {
        "sex": "man", "age": 38,
        "look": "A Stratford mercer and alderman of 38. Warm winding face, brown hair, a full but tidy beard, anxious kind eyes, a civic stomach just starting, a good wool gown of a country town, not London black. More warmth than Sturley, less flour than Sadler.",
        "action": "He is mid-ask, one hand open, the other holding a folded letter that shows no writing.",
        "light": "Market daylight at the High Cross.",
        "who": "Mercer and borough man. A tireless civic fixer.",
    },
    "richard_shakespeare": {
        "sex": "man", "age": 21,
        "look": "His brother Richard at 21, in the glove shop. Quiet. Brown hair, a new short beard, steady eyes, a closed mouth, capable hands stained with leather. A work apron. Younger and stiller than Gilbert, less eager than Edmund.",
        "action": "He is stacking gloves and has just decided not to speak.",
        "light": "Workshop daylight at Henley Street.",
        "who": "Brother. Works the glove shop with his father.",
    },
    "robert_cecil": {
        "sex": "man", "age": 32,
        "look": "Sir Robert Cecil at 32, the still man by the fire. A short man, narrow intelligent face, neat short dark beard, thin mouth, watchful eyes, black clothes, a small ruff. A slight stoop as he sits, not a caricature. Young, not the later heavier statesman.",
        "action": "He sits small and still in a chair by the fire, listening, hands quiet.",
        "light": "Firelight at Canon Row.",
        "who": "Privy Councillor. Silent at Hoby's supper.",
        "anchor": "Portraits of the younger Cecil: short, narrow face, neat beard, black clothes.",
    },
    "robert_devereux": {
        "sex": "man", "age": 30,
        "look": "Robert Devereux, Earl of Essex, at 30. The mid-1590s portraits: a long face, auburn hair, a pointed auburn beard, confident eyes, a soldier-courtier's jaw. Steel of a tilt armour at the edges of the crop, or a rich tawny doublet. Bearded and broader than Southampton, who is beside the same barrier and is not this man.",
        "action": "He is just in from the tilt, looking off at the queen's barrier, catching his breath.",
        "light": "Hard November daylight.",
        "who": "Earl of Essex. Seen at the tilt, never visited.",
        "anchor": "Mid-1590s portraits: long face, auburn pointed beard.",
    },
    "sam_latchet": {
        "sex": "boy", "age": 12,
        "look": "The small boy, 12. Fairer than Nick and Arthur: soft light-brown curls, a round face, a wide mouth, sleepy-bright eyes, small for twelve. A costume a size tight at the shoulder, ordinary shoes just in frame if the crop allows. A real child.",
        "action": "He is singing a note and has forgotten where his feet go, eyes on the lutenist off-frame.",
        "light": "Daylight in Phillips's Southwark house.",
        "who": "The small boy, bound to Augustine Phillips.",
    },
    "samuel_daniel": {
        "sex": "man", "age": 33,
        "look": "A grave court poet of 33. Pale, a high forehead, fine brown hair already thinning, a neat short beard, quiet grey eyes, a measured mouth. Black, scholarly, faint weariness of someone wary of playhouses. Still where Drayton is sunny.",
        "action": "He is listening to a sentence he may not agree with, hands folded.",
        "light": "Soft daylight in a Holborn room.",
        "who": "Poet of the Civil Wars. A likely source for Richard II.",
    },
    "susanna_shakespeare": {
        "sex": "girl", "age": 12,
        "look": "His elder daughter, 12. A girl's face trying on a grown phrase: straight brown hair in a braid, Anne's watchful hazel eyes, a solemn mouth, clear skin, no freckles where her brother is freckled. A plain kirtle. Twelve, not sixteen.",
        "action": "She is letting an adult finish, arms folded, already knowing the sentence is wrong.",
        "light": "Daylight at Henley Street. No church and no churchyard.",
        "who": "Elder daughter, twelve. Anne's right hand.",
    },
    "thomas_hobbins": {
        "sex": "man", "age": 49,
        "look": "The Stratford carrier, 49. Weather-beaten, mud-spattered boots out of a tight crop, a grey-brown beard crusted at the edge with road dust, deep lines, patient small eyes, a heavy frieze coat and a felt hat dark with rain. Slow in the face. Not the waterman's wild beard: this beard is trimmed by weather, not by a razor.",
        "action": "He is checking a pack-strap and answering a question about the price of the road.",
        "light": "Open daylight by the horses, who stay mostly out of frame.",
        "who": "The carrier between Stratford and the Bell in Carter Lane.",
    },
    "thomas_morley": {
        "sex": "man", "age": 37,
        "look": "Thomas Morley, composer, about 37. Dark curls, a witty mobile face, a small pointed beard, bright eyes, a musician's hands. A slightly more Italian cut of doublet than the players wear, still 1595 wool and linen. Candlelit, not theatrical.",
        "action": "He is beating a rhythm on a closed book and talking, delighted by a cadence.",
        "light": "Candlelight in a room near St Helen's.",
        "who": "Composer and organist, a neighbour in Great St Helen's.",
    },
    "thomas_nashe": {
        "sex": "man", "age": 28,
        "look": "A satirist of 28, brilliant and broke. Unruly dark hair, a thin hungry face, almost no beard, intense dark eyes, a frayed collar, ink on a knuckle. Faster in the face than Peele and younger, with no shabby middle-age yet.",
        "action": "He is talking too fast, one hand up, laughing at his own sentence.",
        "light": "Garret daylight, a cheap candle unlit beside him.",
        "who": "Satirist and pamphleteer. Shifting garrets.",
    },
    "thomas_pope": {
        "sex": "man", "age": 38,
        "look": "A big comic sharer of 38. Broad shoulders that fill the frame, a thick brown beard, a wide unembarrassable face, small bright eyes, a booming stillness. A heavy doublet. The largest man in the company, larger than Kemp, who is stocky and round rather than broad.",
        "action": "He is listening to another man explain himself, arms folded, about to finish the thought for him.",
        "light": "Daylight in Southwark.",
        "who": "Sharer. Keeps the boy Arthur Meeks. Plays the Nurse.",
    },
    "will_kemp": {
        "sex": "man", "age": 35,
        "look": "Will Kemp at 35, anchored on the woodcut in Nine Days' Wonder: a round comic face, a short bushy beard, a soft cap over brown hair, a dancer's stocky body, bright mocking eyes, hose and a short cloak. Not a portrait beauty. Caught in motion, not standing like a gentleman.",
        "action": "He is mid-jig, one shoulder dropped, talking to the room as if it were two thousand people, eyes on them and not on the lens.",
        "light": "Daylight in a yard.",
        "who": "Clown and sharer. First name on the warrant.",
        "anchor": "The woodcut of Kemp in Nine Days' Wonder (1600), read at the model's age of 35.",
    },
    "will_sly": {
        "sex": "man", "age": 23,
        "look": "A young player. § 3 gives no age; cast at 23 because the entry calls him young and handsome and quick with a foil. Fair brown hair, clean-shaven, a straight nose, clear skin, a quick light-eyed face, slim. A fitted doublet. Handsomer than Cowley and nothing like Burbage's dark beard.",
        "action": "He is lowering a foil and looking at where the point landed, off-frame.",
        "light": "Yard daylight.",
        "who": "Player. Young, handsome, quick with a foil. Membership in 1595 is contested.",
    },
}


def people_entities() -> dict[str, dict]:
    found = {}
    for path in sorted(ENTITIES.glob("*/entity.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("type") == "Person":
            found[path.parent.name] = data
    return found


def cast_headings() -> dict[str, str]:
    text = WORLD_PATH.read_text(encoding="utf-8")
    return {m.group(1): m.group(2).strip() for m in CAST_HEAD.finditer(text)}


def scan() -> dict[str, list[dict]]:
    evidence: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(WEEKS.glob("*/merged/2025-*.md")):
        text = path.read_text(encoding="utf-8")
        for part in re.split(r"(?=^## \d{2}:\d{2} · )", text, flags=re.M):
            head = HEADING.match(part)
            if not head:
                continue
            people = PEOPLE_LINE.search(part)
            if not people or people.group(1).strip() == "none":
                continue
            place_m = PLACE_LINE.search(part)
            place = place_m.group(1) if place_m else ""
            for slug, role in PERSON_TAG.findall(people.group(1)):
                evidence[slug].append({
                    "date": path.stem,
                    "time": head.group(1),
                    "kind": head.group(2),
                    "role": role,
                    "title": head.group(3).strip(),
                    "place": place,
                    "file": str(path.relative_to(PROJECT)),
                })
    return evidence


def seen(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["kind"] in SEE_KINDS and row["role"] in SEE_ROLES]


def role_summary(rows: list[dict]) -> str:
    if not rows:
        return "never tagged in an accepted day"
    counts = Counter((row["kind"], row["role"]) for row in rows)
    return ", ".join(f"{kind}/{role} ×{n}" for (kind, role), n in sorted(counts.items()))


def cite(row: dict) -> str:
    return (
        f"{row['date']} {row['time']} {row['kind']} ({row['role']}) "
        f"“{row['title']}”, `{row['place']}`, `{row['file']}`"
    )


def build() -> None:
    entities = people_entities()
    headings = cast_headings()
    evidence = scan()
    if len(entities) != 70:
        raise SystemExit(f"expected 70 Person entities, found {len(entities)}")

    face_slugs = []
    none_rows = []
    for slug in sorted(entities):
        rows = evidence.get(slug, [])
        hits = seen(rows)
        if slug in POLICY_NONE:
            none_rows.append((slug, POLICY_NONE[slug], rows, hits))
        elif hits or slug in FACE_ALSO:
            face_slugs.append(slug)
        else:
            why = (
                "Never tagged in an accepted day."
                if not rows
                else f"No meeting or photo where they are attendee or visible. Tags: {role_summary(rows)}."
            )
            none_rows.append((slug, why, rows, hits))

    missing = sorted(set(face_slugs) - set(CAST))
    extra = sorted(set(CAST) - set(face_slugs))
    if missing or extra:
        raise SystemExit(f"cast does not match the scan. missing={missing} extra={extra}")

    year = json.loads(YEAR_PROMPTS.read_text(encoding="utf-8"))
    framing = year["framings"][0]
    if framing["id"] != "C":
        raise SystemExit("prompts_year.json no longer leads with Framing C")

    shots = []
    for index, slug in enumerate(face_slugs, start=1):
        spec = CAST[slug]
        hits = seen(evidence.get(slug, []))
        if hits:
            hit = hits[0]
        elif evidence.get(slug):
            hit = evidence[slug][0]
        elif slug in FACE_ALSO_HIT:
            hit = FACE_ALSO_HIT[slug]
        else:
            raise SystemExit(f"no cite for included face {slug}")
        name = entities[slug]["name"]
        age = int(spec["age"])
        sex = str(spec["sex"])
        child = ""
        if sex == "boy":
            child = f" He is a real boy of {age}, with a boy's face and proportions, not a teenager and not a small adult."
        elif sex == "girl":
            child = f" She is a real girl of {age}, with a girl's face and proportions, not a teenager and not a small adult."
        elif age <= 16:
            child = f" This is a person of {age}, not a child and not a face of thirty."
        subject = (
            f"One candid photograph of {name}, a {sex} of {age}, in England in 1595. "
            f"{spec['look']} {spec['action']} {spec['light']} "
            f"The crop is head and shoulders. The face is large, unobstructed, three-quarter or profile. "
            f"The eyes are on the work or on a person outside the frame. "
            f"The eyes do not meet the camera. This is not a posed portrait.{child} "
            f"One person only. No second face. No William Shakespeare. "
            f"No glasses, no zip, no modern haircut, no makeup, no plastic, no electric light. "
            f"No legible lettering, numeral, shop sign, title, or embroidery that forms a word. "
            f"Paper and metalwork are blank or smudged. "
            f"A good 2025 phone camera, true colour, available light only. Not a painting."
        )
        shots.append({
            "shot_index": index,
            "id": slug,
            "date": hit["date"],
            "time": hit["time"],
            "title": name,
            "place": hit["place"] or "london",
            "segment_key": "",
            "day_key": hit["date"].replace("-", ""),
            "entries": "",
            "shot_list_ref": cite(hit),
            "day_file": hit["file"],
            "photo_text": subject,
            "world_text": headings.get(slug, ""),
            "people_present": True,
            "subject_prompt": subject,
            "parameters": {"aspectRatio": "1:1", "seed": 159500 + index},
            "face_sex": sex,
            "face_age": age,
            "face_who": spec["who"],
            "face_anchor": spec.get("anchor", ""),
        })

    prompt_set = {
        "schema_version": 1,
        "description": (
            "One Framing C head-and-shoulders face for each person William sees "
            "in person in 1595. Square 1:1, to be cropped to 256 pixels."
        ),
        "default_model": year.get("default_model", "gemini-nano-banana-2.1"),
        "default_parameters": {
            "aspectRatio": "1:1",
            "imageSize": "1K",
            "responseModalities": ["IMAGE"],
        },
        "framings": [framing],
        "shots": shots,
    }
    OUT_PROMPTS.write_text(json.dumps(prompt_set, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Person faces",
        "",
        "Who gets a face in the william journal, and what the picture is of. "
        "The images and `install.json` come after this list.",
        "",
        "## How someone qualifies",
        "",
        "Counted on 2026-11-17 from the 70 `entity.json` files under "
        "`build/journal/entities/` whose `type` is `Person`, checked against every "
        "`content/weeks/*/merged/2025-*.md` day file (365 files).",
        "",
        "A qualifying sighting is a segment whose heading kind is `meeting` or `photo`, "
        "with that slug tagged `(attendee)` or `(visible)` on the `people:` line. "
        "A call does not count. `(mentioned)` and `(heard)` do not count. "
        "Memos, notes and frames do not count: those are his voice, his page, or a surface, "
        "not a person in the room.",
        "",
        "The first qualifying sighting is the evidence below. `n` is how many such sightings "
        "the year holds for that person.",
        "",
        f"**Face: {len(face_slugs)}. None: {len(none_rows)}. Person entities: {len(entities)}.**",
        "",
        "## Face",
        "",
        "| Slug | Name | § 3 age | Model age | First sighting | n |",
        "|---|---|---|---|---|---|",
    ]
    for slug in face_slugs:
        spec = CAST[slug]
        hits = seen(evidence.get(slug, []))
        rows = evidence.get(slug, [])
        if hits:
            cited, count = hits[0], len(hits)
        elif rows:
            cited, count = rows[0], 0
        elif slug in FACE_ALSO_HIT:
            cited, count = FACE_ALSO_HIT[slug], 0
        else:
            raise SystemExit(f"no cite for included face {slug}")
        name = entities[slug]["name"]
        heading_age = headings[slug].split(" · ")[1] if slug in headings else ""
        lines.append(
            f"| `{slug}` | {name} | {heading_age} | {spec['age']} | {cite(cited)} | {count} |"
        )

    lines += ["", "## What the face is", ""]
    for slug in face_slugs:
        spec = CAST[slug]
        name = entities[slug]["name"]
        anchor = spec.get("anchor")
        extra = f" Anchored on {anchor}" if anchor else ""
        lines.append(f"- **{name}** (`{slug}`), {spec['sex']} of {spec['age']}. {spec['look']} {spec['action']}{extra}")

    lines += [
        "",
        "## Anchors",
        "",
        "Where a contemporary picture exists, the prompt keeps that face at the 1595 age.",
        "",
    ]
    for slug in face_slugs:
        anchor = CAST[slug].get("anchor")
        if anchor:
            lines.append(f"- `{slug}`: {anchor}")

    lines += [
        "",
        "Ages § 3 leaves unknown, chosen here and used only for the picture:",
        "",
        "- `will_sly`: no age in § 3. Cast at 23 because the entry says young, handsome, and quick with a foil.",
        "- `bartholomew_hathaway`: no age in § 3. Cast at 36, a working farmer and Anne's brother.",
        "",
        "Kin share a colouring and stay different faces: the Henley Street household in brown hair and hazel eyes; "
        "James, Richard and Cuthbert Burbage in the dark brow; Hamnet and Judith Shakespeare as twins of ten; "
        "Anne and Bartholomew in the dark hair and the straight nose. "
        "No two prompts share a body. The contact sheet is the check.",
        "",
        "## None",
        "",
    ]
    for slug, why, rows, hits in none_rows:
        name = entities[slug]["name"]
        extra = ""
        if hits:
            extra = f" The year would otherwise qualify them: {cite(hits[0])}, n={len(hits)}."
        lines.append(f"- `{slug}` · {name}. {why}{extra}")

    lines += [
        "",
        "`gib` is the cat. The scan sees the slug and there is no Person entity, so there is no face.",
        "",
    ]
    OUT_REASONING.parent.mkdir(parents=True, exist_ok=True)
    OUT_REASONING.write_text("\n".join(lines), encoding="utf-8")
    print(f"faces {len(face_slugs)} none {len(none_rows)} prompts {OUT_PROMPTS}")


if __name__ == "__main__":
    build()
