# SPDX-License-Identifier: CC-BY-NC-4.0
# Copyright (c) 2026 sol pbc

"""Canonical world data (§ 3 cast, § 4 places, § 7.8 body, § 7.9 location, facets)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import random
from typing import Any


@dataclass(frozen=True)
class CastEntity:
    slug: str
    name: str
    entity_type: str
    aka: tuple[str, ...]
    description: str
    facets: tuple[str, ...]
    is_principal: bool = False
    observations: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlaceCoord:
    slug: str
    name: str
    lat: float | None
    lon: float | None
    aliases: tuple[str, ...] = ()


FACET_DEFINITIONS: dict[str, dict[str, Any]] = {
    "company": {
        "id": "778cde83-0eb8-4a9a-af6b-573fe3c34b71",
        "title": "The Lord Chamberlain's Men",
        "description": (
            "Playing, rehearsing, casting and reckoning with the Lord Chamberlain's Men "
            "at the Cross Keys, the Theatre and court; not private drafting or Stratford family matters."
        ),
        "color": "#b45309",
        "emoji": "🎭",
        "activities": [
            {"id": "rehearsal", "priority": "high", "name": "Rehearsal", "description": "Rehearsals, part-checking, and stage work"},
            {"id": "performance", "priority": "high", "name": "Performance", "description": "Afternoon plays and court performances"},
            {"id": "reckoning", "priority": "high", "name": "Reckoning", "description": "Company accounts, sharer meetings, and stock"},
            {"id": "company_errand", "priority": "medium", "name": "Company Errand", "description": "Moving baskets, licensing, and court warrants"},
            {"id": "meeting", "priority": "high", "name": "Meeting", "description": "Meetings and calls with sharers and patrons"},
        ],
    },
    "writing": {
        "id": "29ed8ff0-379c-4042-812c-f8ff913588d7",
        "title": "Plays and Poems",
        "description": (
            "Drafting plays and poems at the desk, reading sources, and print business "
            "at Paul's and Blackfriars; not stage performance or company accounts."
        ),
        "color": "#4f46e5",
        "emoji": "🪶",
        "activities": [
            {"id": "drafting", "priority": "high", "name": "Drafting", "description": "Writing and revising scenes and poems at the desk"},
            {"id": "reading", "priority": "medium", "name": "Reading", "description": "Reading source books and taking commonplace notes"},
            {"id": "print_business", "priority": "medium", "name": "Print Business", "description": "Visiting bookstalls at Paul's and Field's printing house"},
            {"id": "reflection", "priority": "medium", "name": "Reflection", "description": "Voice memos and notes on lines in progress"},
        ],
    },
    "household": {
        "id": "64ea0001-e3b3-42fb-9cb5-9d4638052dc9",
        "title": "St Helen's and the Town",
        "description": (
            "Life in Mistress Ansell's house in Great St Helen's, the parish, taverns, "
            "meals, river crossings and town errands; not company business or Stratford."
        ),
        "color": "#059669",
        "emoji": "🕯️",
        "activities": [
            {"id": "household", "priority": "medium", "name": "Household", "description": "Accounts, meals, and talk at Mistress Ansell's"},
            {"id": "parish", "priority": "medium", "name": "Parish", "description": "Morning prayer and sermons at St Helen's"},
            {"id": "tavern", "priority": "low", "name": "Tavern", "description": "Dinners and suppers at the Bull, Split Hazel, and Jackdaw"},
            {"id": "errand", "priority": "low", "name": "Errand", "description": "Walks to Leadenhall, Finsbury Fields, and river stairs"},
        ],
    },
    "stratford": {
        "id": "07a10f34-c2dd-4d43-b579-a84cbb810f85",
        "title": "Stratford and Kin",
        "description": (
            "Anne, the children, John and Mary at Henley Street, Gilbert, Hobbins the carrier, "
            "Stratford neighbours, the journeys home and Warwickshire property; not London lodgings or the playhouse."
        ),
        "color": "#dc2626",
        "emoji": "🏡",
        "activities": [
            {"id": "family", "priority": "high", "name": "Family", "description": "Letters, parcels, calls, and time with Stratford kin"},
            {"id": "carrier", "priority": "medium", "name": "Carrier", "description": "Sending and fetching parcels with Thomas Hobbins at the Bell"},
            {"id": "journey", "priority": "medium", "name": "Journey", "description": "Riding or walking the Oxford and Banbury roads"},
        ],
    },
}


# All 71 canonical § 3 cast slugs from world/fold/00-canon.md
CANON_CAST: tuple[CastEntity, ...] = (
    # 3.1 William and family (11)
    CastEntity(
        slug="william_shakespeare",
        name="William Shakespeare",
        entity_type="Person",
        aka=("Will", "Master Shakespeare", "Shakespeare"),
        description="Owner; sharer, player, and house playwright in the Lord Chamberlain's Men; poet.",
        facets=("company", "writing", "household", "stratford"),
        is_principal=True,
    ),
    CastEntity(
        slug="anne_shakespeare",
        name="Anne Shakespeare",
        entity_type="Person",
        aka=("Anne", "Anne Hathaway"),
        description="William's wife at Henley Street in Stratford-upon-Avon.",
        facets=("stratford",),
        observations=("Manages the Henley Street household and quarterly remittances", "Writes letters by the carrier Thomas Hobbins"),
    ),
    CastEntity(
        slug="susanna_shakespeare",
        name="Susanna Shakespeare",
        entity_type="Person",
        aka=("Susanna",),
        description="Elder daughter at Henley Street; reads well and casts household tallies.",
        facets=("stratford",),
        observations=("Turns twelve on 26 May 1595", "Reads English books and casts household tallies"),
    ),
    CastEntity(
        slug="hamnet_shakespeare",
        name="Hamnet Shakespeare",
        entity_type="Person",
        aka=("Hamnet",),
        description="Son, Judith's twin, in the lower forms of the King's New School at Stratford; ordinary and well all year.",
        facets=("stratford",),
        observations=("Studies Latin grammar at the King's New School", "Fond of mechanisms, willow boats, and wooden foils"),
    ),
    CastEntity(
        slug="judith_shakespeare",
        name="Judith Shakespeare",
        entity_type="Person",
        aka=("Judith",),
        description="Younger daughter, Hamnet's twin, at Henley Street; sings and mimics.",
        facets=("stratford",),
        observations=("Sings and remembers everything said in her hearing",),
    ),
    CastEntity(
        slug="john_shakespeare",
        name="John Shakespeare",
        entity_type="Person",
        aka=("Father", "Master John Shakespeare"),
        description="William's father at Henley Street; glover, whittawer, and former bailiff of Stratford.",
        facets=("stratford",),
        observations=("Former bailiff of Stratford (1568) and glover on Henley Street", "Carries small shop debts in Stratford"),
    ),
    CastEntity(
        slug="mary_shakespeare",
        name="Mary Shakespeare",
        entity_type="Person",
        aka=("Mother", "Mary Arden"),
        description="William's mother (née Arden) at Henley Street.",
        facets=("stratford",),
        observations=("Keeps the keys and household memory at Henley Street",),
    ),
    CastEntity(
        slug="gilbert_shakespeare",
        name="Gilbert Shakespeare",
        entity_type="Person",
        aka=("Gilbert",),
        description="William's younger brother; journeyman haberdasher lodging in St Bride's parish, London.",
        facets=("stratford", "household"),
        observations=("Journeyman haberdasher in St Bride's parish near the Fleet", "Brings Stratford word from the Bell in Carter Lane"),
    ),
    CastEntity(
        slug="joan_shakespeare",
        name="Joan Shakespeare",
        entity_type="Person",
        aka=("Joan",),
        description="William's unmarried sister at Henley Street.",
        facets=("stratford",),
        observations=("Runs the Henley Street kitchen with Mary and spins",),
    ),
    CastEntity(
        slug="richard_shakespeare",
        name="Richard Shakespeare",
        entity_type="Person",
        aka=("Richard",),
        description="William's younger brother; works the glove shop at Henley Street with his father.",
        facets=("stratford",),
        observations=("Turns twenty-one on 11 March 1595; works the Henley Street glove shop",),
    ),
    CastEntity(
        slug="edmund_shakespeare",
        name="Edmund Shakespeare",
        entity_type="Person",
        aka=("Edmund", "Ned"),
        description="William's youngest brother at Henley Street; stage-struck.",
        facets=("stratford",),
        observations=("Youngest brother at Stratford, eager for playhouse stories",),
    ),
    # 3.2 Stratford (6)
    CastEntity(
        slug="richard_quiney",
        name="Richard Quiney",
        entity_type="Person",
        aka=("Dick Quiney", "Master Quiney"),
        description="Stratford mercer and borough man; 'loving countryman'.",
        facets=("stratford",),
        observations=("Stratford mercer and borough man on High Street",),
    ),
    CastEntity(
        slug="hamnet_sadler",
        name="Hamnet Sadler",
        entity_type="Person",
        aka=("Master Sadler",),
        description="Stratford baker on the High Street and godfather to the twins (not Hamnet Shakespeare).",
        facets=("stratford",),
        observations=("High Street baker and godfather to Hamnet and Judith",),
    ),
    CastEntity(
        slug="judith_sadler",
        name="Judith Sadler",
        entity_type="Person",
        aka=("Mistress Sadler",),
        description="Hamnet Sadler's wife and godmother to the twins.",
        facets=("stratford",),
        observations=("Godmother to the twins at Stratford",),
    ),
    CastEntity(
        slug="abraham_sturley",
        name="Abraham Sturley",
        entity_type="Person",
        aka=("Master Sturley",),
        description="Stratford alderman and ally of Richard Quiney.",
        facets=("stratford",),
        observations=("Stratford alderman and borough neighbour",),
    ),
    CastEntity(
        slug="bartholomew_hathaway",
        name="Bartholomew Hathaway",
        entity_type="Person",
        aka=("Bartholomew",),
        description="Anne's brother, farming at Hewlands in Shottery.",
        facets=("stratford",),
        observations=("Farms Hewlands at Shottery",),
    ),
    CastEntity(
        slug="thomas_hobbins",
        name="Thomas Hobbins",
        entity_type="Person",
        aka=("Hobbins", "the carrier"),
        description="The Stratford carrier between the High Cross and the Bell in Carter Lane.",
        facets=("stratford",),
        observations=("Rides fortnightly between Stratford High Cross and the Bell in Carter Lane",),
    ),
    # 3.3 The company (20)
    CastEntity(
        slug="richard_burbage",
        name="Richard Burbage",
        entity_type="Person",
        aka=("Dick Burbage", "Burbage"),
        description="Leading player and sharer in the Lord Chamberlain's Men; plays Berowne, Richard II, and Romeo.",
        facets=("company",),
        observations=("Leading player and sharer in the Lord Chamberlain's Men", "Plays Berowne, Richard II, and Romeo"),
    ),
    CastEntity(
        slug="will_kemp",
        name="Will Kemp",
        entity_type="Person",
        aka=("Kemp", "Master Kemp"),
        description="Clown and sharer in the Lord Chamberlain's Men; first name on the March court warrant.",
        facets=("company",),
        observations=("Clown and sharer; named first on the Greenwich court warrant", "Plays Costard, Launce, Dogberry/Peter, and Bottom"),
    ),
    CastEntity(
        slug="john_heminges",
        name="John Heminges",
        entity_type="Person",
        aka=("Heminges", "Master Heminges"),
        description="Sharer and man of account in the Lord Chamberlain's Men; holds the stock share and keeps the reckoning book.",
        facets=("company",),
        observations=("Keeps the company reckoning book and holds the stock share", "Collects the £20 Greenwich court warrant on 15 March"),
    ),
    CastEntity(
        slug="augustine_phillips",
        name="Augustine Phillips",
        entity_type="Person",
        aka=("Phillips", "Austin Phillips"),
        description="Sharer and musician in the Lord Chamberlain's Men; Nick's voice coach and Sam Latchet's master.",
        facets=("company",),
        observations=("Sharer and musician; master to Sam Latchet",),
    ),
    CastEntity(
        slug="thomas_pope",
        name="Thomas Pope",
        entity_type="Person",
        aka=("Pope", "Tom Pope"),
        description="Sharer in the Lord Chamberlain's Men; plays Armado, the Gardener, and the Nurse; Arthur Meeks's master.",
        facets=("company",),
        observations=("Sharer; plays Armado, the Gardener, and the Nurse",),
    ),
    CastEntity(
        slug="george_bryan",
        name="George Bryan",
        entity_type="Person",
        aka=("Bryan",),
        description="Sharer in the Lord Chamberlain's Men; court manners; Richmond payee with Heminges.",
        facets=("company",),
        observations=("Sharer in the Lord Chamberlain's Men with court experience",),
    ),
    CastEntity(
        slug="richard_cowley",
        name="Richard Cowley",
        entity_type="Person",
        aka=("Cowley",),
        description="Hired player in the Lord Chamberlain's Men (not a sharer); covers William when he is ill.",
        facets=("company",),
        observations=("Hired player who covers William's parts during illness",),
    ),
    CastEntity(
        slug="will_sly",
        name="William Sly",
        entity_type="Person",
        aka=("Will Sly", "Sly"),
        description="Player in the Lord Chamberlain's Men; plays Tybalt; quick with a foil.",
        facets=("company",),
        observations=("Player in the company; quick with a rapier and dagger",),
    ),
    CastEntity(
        slug="john_sincler",
        name="John Sincler",
        entity_type="Person",
        aka=("Sinklo", "Sincler"),
        description="Hired man in the Lord Chamberlain's Men, the thin one; plays Marcade and the Apothecary.",
        facets=("company",),
        observations=("Hired player known as Sinklo",),
    ),
    CastEntity(
        slug="hired_men",
        name="William Blackwage, Ralph Raye, Richard Hoope",
        entity_type="Person",
        aka=("Blackwage", "Ralph Raye", "Richard Hoope"),
        description="Hired men of the company at 10s a week.",
        facets=("company",),
    ),
    CastEntity(
        slug="humphrey_larkham",
        name="Humphrey Larkham",
        entity_type="Person",
        aka=("Larkham",),
        description="Hired player, gatherer when needed, and second copyist under Abel Garnish.",
        facets=("company",),
    ),
    CastEntity(
        slug="nick_sorrell",
        name="Nick Sorrell",
        entity_type="Person",
        aka=("Nick",),
        description="Leading boy player bound to John Heminges; plays the Princess of France, the Queen in Richard II, and Juliet.",
        facets=("company",),
    ),
    CastEntity(
        slug="arthur_meeks",
        name="Arthur Meeks",
        entity_type="Person",
        aka=("Arthur",),
        description="Second boy player, lodging with Thomas Pope; tall and shooting up; plays Rosaline, the Duchess of York, and Lady Capulet.",
        facets=("company",),
    ),
    CastEntity(
        slug="sam_latchet",
        name="Sam Latchet",
        entity_type="Person",
        aka=("Sam",),
        description="Small boy player bound to Augustine Phillips; plays Moth, Juliet's page, and Puck.",
        facets=("company",),
    ),
    CastEntity(
        slug="abel_garnish",
        name="Abel Garnish",
        entity_type="Person",
        aka=("Garnish", "Master Garnish"),
        description="Book-keeper to the Lord Chamberlain's Men; keeps the prompt book, parts, and plots.",
        facets=("company",),
    ),
    CastEntity(
        slug="margery_pell",
        name="Goodwife Margery Pell",
        entity_type="Person",
        aka=("Margery Pell", "Goodwife Pell"),
        description="Gatherer at the gallery stair; the company's eyes on the City's mood.",
        facets=("company",),
    ),
    CastEntity(
        slug="edith_kettlewood",
        name="Edith Kettlewood",
        entity_type="Person",
        aka=("Edith", "Mistress Kettlewood"),
        description="Seamstress and tire-mender to the company; owed 8s from January.",
        facets=("company",),
    ),
    CastEntity(
        slug="james_burbage",
        name="James Burbage",
        entity_type="Person",
        aka=("Old Burbage", "Master James Burbage"),
        description="Owner of the Theatre in Holywell and father to Richard and Cuthbert Burbage.",
        facets=("company",),
        observations=("Builder and owner of the Theatre in Holywell",),
    ),
    CastEntity(
        slug="cuthbert_burbage",
        name="Cuthbert Burbage",
        entity_type="Person",
        aka=("Cuthbert",),
        description="James Burbage's elder son and business envoy to ground landlord Giles Allen.",
        facets=("company",),
        observations=("Handles the Holywell lease negotiations with Giles Allen",),
    ),
    CastEntity(
        slug="giles_allen",
        name="Giles Allen",
        entity_type="Person",
        aka=("Master Allen",),
        description="Ground landlord of the Holywell site where the Theatre stands.",
        facets=("company",),
    ),
    # 3.4 Patrons, court and civic (12)
    CastEntity(
        slug="henry_carey_hunsdon",
        name="Henry Carey, 1st Lord Hunsdon",
        entity_type="Person",
        aka=("Lord Hunsdon", "the Lord Chamberlain", "Hunsdon"),
        description="Lord Chamberlain and patron of the company.",
        facets=("company",),
        observations=("Lord Chamberlain and patron of the company",),
    ),
    CastEntity(
        slug="ambrose_kettleby",
        name="Ambrose Kettleby",
        entity_type="Person",
        aka=("Kettleby", "Master Kettleby"),
        description="Gentleman usher to Lord Hunsdon at Somerset House.",
        facets=("company",),
    ),
    CastEntity(
        slug="henry_wriothesley_southampton",
        name="Henry Wriothesley, 3rd Earl of Southampton",
        entity_type="Person",
        aka=("the Earl of Southampton", "Southampton", "Lord Southampton"),
        description="3rd Earl of Southampton; dedicatee of Venus and Adonis and Lucrece.",
        facets=("writing",),
        observations=("Dedicatee of Venus and Adonis and The Rape of Lucrece",),
    ),
    CastEntity(
        slug="john_florio",
        name="John Florio",
        entity_type="Person",
        aka=("Florio", "Master Florio"),
        description="Italian tutor and secretary in the Earl of Southampton's household.",
        facets=("writing",),
        observations=("Italian tutor at Southampton House in Holborn",),
    ),
    CastEntity(
        slug="elizabeth_i",
        name="Queen Elizabeth",
        entity_type="Person",
        aka=("the Queen", "Her Majesty"),
        description="Queen Elizabeth I, seen at Greenwich, the Accession Day tilt, and Richmond.",
        facets=("company",),
    ),
    CastEntity(
        slug="edward_hoby",
        name="Sir Edward Hoby",
        entity_type="Person",
        aka=("Hoby",),
        description="Nephew to Lord Hunsdon; host of the supper performance at Canon Row on 9 December.",
        facets=("company",),
    ),
    CastEntity(
        slug="margaret_hoby",
        name="Margaret, Lady Hoby",
        entity_type="Person",
        aka=("Lady Hoby",),
        description="Daughter of Lord Hunsdon and wife of Sir Edward Hoby at Canon Row.",
        facets=("company",),
    ),
    CastEntity(
        slug="robert_cecil",
        name="Sir Robert Cecil",
        entity_type="Person",
        aka=("Cecil",),
        description="Privy Councillor and guest at Sir Edward Hoby's house in Canon Row.",
        facets=("company",),
    ),
    CastEntity(
        slug="edmund_tilney",
        name="Edmund Tilney",
        entity_type="Person",
        aka=("Tilney", "the Master of the Revels"),
        description="Master of the Revels at St John's, Clerkenwell.",
        facets=("company",),
        observations=("Master of the Revels at St John's, Clerkenwell",),
    ),
    CastEntity(
        slug="thomas_heneage",
        name="Sir Thomas Heneage",
        entity_type="Person",
        aka=("Heneage", "the Treasurer of the Chamber"),
        description="Treasurer of the Chamber, whose office pays court playing warrants; dies 17 October 1595.",
        facets=("company",),
    ),
    CastEntity(
        slug="robert_devereux",
        name="Robert Devereux, Earl of Essex",
        entity_type="Person",
        aka=("Essex", "the Earl of Essex"),
        description="2nd Earl of Essex, seen at the Accession Day tilt.",
        facets=("company",),
    ),
    CastEntity(
        slug="john_spencer",
        name="Sir John Spencer",
        entity_type="Person",
        aka=("Spencer", "the Lord Mayor"),
        description="Lord Mayor of London until 28 October 1595, residing at Crosby Place in Great St Helen's.",
        facets=("household",),
        observations=("Lord Mayor of London residing at Crosby Place, a hundred yards away",),
    ),
    # 3.5 London household and the town (11)
    CastEntity(
        slug="dorcas_ansell",
        name="Mistress Dorcas Ansell",
        entity_type="Person",
        aka=("Mistress Ansell", "Mrs Ansell"),
        description="William's landlady in Great St Helen's; a scrivener's widow who makes oak-gall ink.",
        facets=("household",),
        observations=("Scrivener's widow and landlady in Great St Helen's", "Makes oak-gall ink and keeps the bread-board notch"),
    ),
    CastEntity(
        slug="alse_pinder",
        name="Alse Pinder",
        entity_type="Person",
        aka=("Alse",),
        description="Mistress Ansell's maid in Great St Helen's, from Hertfordshire.",
        facets=("household",),
        observations=("Maid in Mistress Ansell's house in Great St Helen's",),
    ),
    CastEntity(
        slug="gillis_verbeke",
        name="Gillis Verbeke",
        entity_type="Person",
        aka=("Verbeke", "Gillis"),
        description="Flemish silk-weaver from Ghent and fellow lodger at Mistress Ansell's.",
        facets=("household",),
        observations=("Flemish silk-weaver lodging at Mistress Ansell's",),
    ),
    CastEntity(
        slug="josias_thwaite",
        name="Master Josias Thwaite",
        entity_type="Person",
        aka=("Master Thwaite", "Thwaite"),
        description="Reader and curate at St Helen's, Bishopsgate.",
        facets=("household",),
        observations=("Reader and curate at St Helen's, Bishopsgate",),
    ),
    CastEntity(
        slug="gib",
        name="Gib",
        entity_type="Animal",
        aka=("the cat",),
        description="Mistress Ansell's grey cat, often asleep on the book William needs.",
        facets=("household",),
        observations=("Mistress Ansell's grey cat in Great St Helen's",),
    ),
    CastEntity(
        slug="agnes_tipping",
        name="Agnes Tipping",
        entity_type="Person",
        aka=("Mistress Tipping",),
        description="Hostess of the Jackdaw in Holywell Lane, the company's weekday ordinary.",
        facets=("household", "company"),
        observations=("Hostess of the Jackdaw ordinary in Holywell Lane",),
    ),
    CastEntity(
        slug="alice_brambleby",
        name="Alice Brambleby",
        entity_type="Person",
        aka=("Alice", "Mistress Brambleby"),
        description="Keeper of the Split Hazel, the ordinary near Bishopsgate.",
        facets=("household",),
        observations=("Keeper of the Split Hazel ordinary near Bishopsgate",),
    ),
    CastEntity(
        slug="davy_gannet",
        name="Davy Gannet",
        entity_type="Person",
        aka=("Davy", "Gannet"),
        description="Waterman at Old Swan Stairs and veteran of '88.",
        facets=("household",),
        observations=("Waterman at Old Swan Stairs who rows William to Westminster and Richmond",),
    ),
    CastEntity(
        slug="barnaby_yaxley",
        name="Barnaby Yaxley",
        entity_type="Person",
        aka=("Yaxley", "Master Yaxley"),
        description="Barber-surgeon in Bishopsgate Street.",
        facets=("household",),
        observations=("Barber-surgeon on Bishopsgate Street",),
    ),
    CastEntity(
        slug="the_lady_unnamed",
        name="the lady of the parish",
        entity_type="Person",
        aka=("the lady",),
        description="A married gentlewoman of St Helen's parish who plays the virginals at Thomas Morley's music evenings; never named.",
        facets=("household",),
        observations=("Gentlewoman of St Helen's parish who plays the virginals",),
    ),
    CastEntity(
        slug="thomas_morley",
        name="Thomas Morley",
        entity_type="Person",
        aka=("Morley", "Master Morley"),
        description="Composer and parishioner in St Helen's, Bishopsgate; hosts chamber music evenings.",
        facets=("household",),
        observations=("Composer living in St Helen's parish",),
    ),
    # 3.6 Print, pens and rivals (11)
    CastEntity(
        slug="richard_field",
        name="Richard Field",
        entity_type="Person",
        aka=("Field", "Ric. Field"),
        description="Printer in Blackfriars and Stratford tanner's son; printer of Venus and Adonis, Lucrece, and North's Plutarch.",
        facets=("writing",),
        observations=("Blackfriars printer from Stratford; lends his 1587 Holinshed", "Prints North's Plutarch (1595) and supplies Rochelle paper"),
    ),
    CastEntity(
        slug="jacqueline_field",
        name="Jacqueline Field",
        entity_type="Person",
        aka=("Mistress Field", "Jacqueline"),
        description="Richard Field's wife (née Vautrollier); manages accounts and paper stock at the Blackfriars printing house.",
        facets=("writing",),
    ),
    CastEntity(
        slug="john_harrison",
        name="John Harrison",
        entity_type="Person",
        aka=("Master Harrison", "Harrison"),
        description="Stationer and publisher at the sign of the White Greyhound in St Paul's Churchyard.",
        facets=("writing",),
        observations=("Publisher at the White Greyhound in St Paul's Churchyard",),
    ),
    CastEntity(
        slug="thomas_nashe",
        name="Thomas Nashe",
        entity_type="Person",
        aka=("Nashe", "Tom Nashe"),
        description="Pamphleteer, playwright, and satirist.",
        facets=("household", "writing"),
        observations=("Satirist and diner at the Bull and the Split Hazel",),
    ),
    CastEntity(
        slug="samuel_daniel",
        name="Samuel Daniel",
        entity_type="Person",
        aka=("Daniel",),
        description="Poet of the First Fowre Bookes of the Civile Wars.",
        facets=("household", "writing"),
        observations=("Author of The First Fowre Bookes of the Civile Wars (1595)",),
    ),
    CastEntity(
        slug="michael_drayton",
        name="Michael Drayton",
        entity_type="Person",
        aka=("Drayton",),
        description="Warwickshire poet encountered at the bookstalls in St Paul's Churchyard.",
        facets=("household", "writing"),
        observations=("Warwickshire poet met at Paul's bookstalls",),
    ),
    CastEntity(
        slug="george_peele",
        name="George Peele",
        entity_type="Person",
        aka=("Peele",),
        description="Playwright and poet seen at the Accession Day tilt.",
        facets=("writing",),
    ),
    CastEntity(
        slug="edward_alleyn",
        name="Edward Alleyn",
        entity_type="Person",
        aka=("Alleyn", "Ned Alleyn"),
        description="Leading player of the Admiral's Men at the Rose.",
        facets=("company",),
    ),
    CastEntity(
        slug="philip_henslowe",
        name="Philip Henslowe",
        entity_type="Person",
        aka=("Henslowe", "Master Henslowe"),
        description="Owner of the Rose playhouse on Bankside.",
        facets=("company",),
    ),
    CastEntity(
        slug="francis_langley",
        name="Francis Langley",
        entity_type="Person",
        aka=("Langley",),
        description="Builder of the Swan playhouse in Paris Garden.",
        facets=("company",),
    ),
    CastEntity(
        slug="robert_southwell",
        name="Robert Southwell",
        entity_type="Person",
        aka=("Southwell",),
        description="Jesuit poet executed at Tyburn on 21 February 1595; author of Saint Peters Complaint.",
        facets=("writing",),
    ),
)


# Additional non-person entities named in content/facets.md top-20 lists
FACET_EXTRA_ENTITIES: tuple[CastEntity, ...] = (
    CastEntity(
        slug="lord_chamberlains_men",
        name="Lord Chamberlain's Men",
        entity_type="Company",
        aka=("the company", "my Lord Chamberlain's Men"),
        description="The playing company under the patronage of Henry Carey, 1st Lord Hunsdon.",
        facets=("company",),
        observations=("Plays at the Cross Keys in winter and the Theatre from Easter Monday",),
    ),
    CastEntity(
        slug="the_theatre",
        name="the Theatre",
        entity_type="Place",
        aka=("The Theatre", "the house in Shoreditch"),
        description="The company's playhouse in Holywell, Shoreditch, owned by James Burbage.",
        facets=("company",),
        observations=("Reopens on Easter Monday after Lent",),
    ),
    CastEntity(
        slug="cross_keys_inn",
        name="the Cross Keys",
        entity_type="Place",
        aka=("Cross Keys", "the Cross Keys in Gracechurch Street"),
        description="The company's winter playing inn on Gracechurch Street (1 January – 4 March).",
        facets=("company",),
        observations=("Winter playing inn on Gracechurch Street until Shrove Tuesday",),
    ),
    CastEntity(
        slug="loves_labours_lost",
        name="Love's Labour's Lost",
        entity_type="Work",
        aka=("the comedy of Navarre", "Navarre"),
        description="Comedy of the King of Navarre and his three lords.",
        facets=("writing", "company"),
        observations=("Played at the Cross Keys in February and revised during the year",),
    ),
    CastEntity(
        slug="richard_ii",
        name="Richard II",
        entity_type="Work",
        aka=("King Richard the Second", "the deposing play"),
        description="History play of the reign and deposition of King Richard II, drafted in spring 1595.",
        facets=("writing", "company"),
        observations=("Drafted from Holinshed and Daniel's Civil Wars in spring 1595",),
    ),
    CastEntity(
        slug="romeo_and_juliet",
        name="Romeo and Juliet",
        entity_type="Work",
        aka=("Verona", "the tragedy of two lovers"),
        description="Tragedy of the two houses of Verona, noted from Brooke in March and drafted from July.",
        facets=("writing", "company"),
        observations=("First commonplace notes taken from Arthur Brooke's Romeus and Juliet on 6 March",),
    ),
    CastEntity(
        slug="a_midsummer_nights_dream",
        name="A Midsummer Night's Dream",
        entity_type="Work",
        aka=("the play of the wood", "the wedding play"),
        description="Comedy of Athens, the wood, the workmen, and the fairies, begun on 28 October.",
        facets=("writing", "company"),
        observations=("Begun with Titania's ruined seasons speech on 28 October",),
    ),
    CastEntity(
        slug="venus_and_adonis",
        name="Venus and Adonis",
        entity_type="Work",
        aka=("Venus",),
        description="Narrative poem dedicated to the Earl of Southampton, printed by Richard Field and sold by John Harrison.",
        facets=("writing",),
        observations=("Sold at the White Greyhound in St Paul's Churchyard",),
    ),
    CastEntity(
        slug="lucrece",
        name="Lucrece",
        entity_type="Work",
        aka=("The Rape of Lucrece",),
        description="Narrative poem dedicated to the Earl of Southampton (1594).",
        facets=("writing",),
        observations=("Printed by Richard Field for John Harrison (1594)",),
    ),
    CastEntity(
        slug="sonnets",
        name="the Sonnets",
        entity_type="Work",
        aka=("Sonnets",),
        description="Private fourteen-line poems kept in loose sheets.",
        facets=("writing",),
        observations=("Kept in private sheets at the desk in Great St Helen's",),
    ),
    CastEntity(
        slug="holinshed",
        name="Holinshed",
        entity_type="Book",
        aka=("Holinshed's Chronicles",),
        description="Raphael Holinshed's Chronicles (1587 folio), borrowed from Richard Field on 19 March.",
        facets=("writing",),
        observations=("1587 folio borrowed from Richard Field for King Richard II",),
    ),
    CastEntity(
        slug="arthur_brooke",
        name="Arthur Brooke",
        entity_type="Book",
        aka=("Brooke", "Romeus and Juliet"),
        description="Arthur Brooke's The Tragicall Historye of Romeus and Iuliet (1562 octavo), bought in Paul's Churchyard on 6 March.",
        facets=("writing",),
        observations=("Bought worn for 6d in St Paul's Churchyard on 6 March",),
    ),
    CastEntity(
        slug="goldings_ovid",
        name="Golding's Ovid",
        entity_type="Book",
        aka=("Ovid", "Metamorphoses"),
        description="Arthur Golding's translation of Ovid's Metamorphoses.",
        facets=("writing",),
        observations=("Read for Pyramus and Thisbe and Titania's speech",),
    ),
    CastEntity(
        slug="norths_plutarch",
        name="Thomas North's Plutarch",
        entity_type="Book",
        aka=("Plutarch", "Lives of the Noble Grecians and Romanes"),
        description="Sir Thomas North's translation of Plutarch's Lives, printed by Richard Field in 1595.",
        facets=("writing",),
        observations=("Folio printed by Richard Field in Blackfriars in 1595",),
    ),
    CastEntity(
        slug="henley_street",
        name="Henley Street",
        entity_type="Place",
        aka=("the Henley Street house",),
        description="John Shakespeare's double house on Henley Street in Stratford-upon-Avon.",
        facets=("stratford",),
        observations=("Family home and glover's workshop in Stratford-upon-Avon",),
    ),
    CastEntity(
        slug="new_place",
        name="New Place",
        entity_type="Place",
        aka=("the great house by the chapel",),
        description="The brick-and-timber house opposite the Guild Chapel in Stratford-upon-Avon.",
        facets=("stratford",),
        observations=("The great house by the Guild Chapel in Stratford",),
    ),
)


# All 57 canonical § 4 place slugs and coordinates from world/world.md § 4
# Display names match the § 4 headings with `[invented]` / `[invented sign]` tags and parentheticals stripped.
CANON_PLACES: dict[str, PlaceCoord] = {
    p.slug: p
    for p in (
        PlaceCoord("ansell_house", "Mistress Ansell's house, Great St Helen's", 51.5150, -0.0815, ("nettlefold_house",)),
        PlaceCoord("st_helens_church", "St Helen's, Bishopsgate", 51.5148, -0.0817, ("st_helens",)),
        PlaceCoord("crosby_place", "Crosby Place", 51.5143, -0.0826, ("crosby_hall",)),
        PlaceCoord("bishopsgate", "Bishopsgate Street and the gate", 51.5165, -0.0812, ("bishopsgate_bedlam",)),
        PlaceCoord("bedlam", "Bethlem Hospital", 51.5175, -0.0815),
        PlaceCoord("bull_inn", "The Bull, Bishopsgate Street", 51.5157, -0.0833, ("bull_inn_bishopsgate",)),
        PlaceCoord("split_hazel", "The Split Hazel", 51.5155, -0.0830),
        PlaceCoord("cross_keys_inn", "The Cross Keys, Gracechurch Street", 51.5122, -0.0852, ("cross_keys",)),
        PlaceCoord("leadenhall", "Leadenhall market", 51.5127, -0.0834),
        PlaceCoord("tower_hill", "Tower Hill", 51.5098, -0.0767),
        PlaceCoord("the_theatre", "The Theatre, Holywell", 51.5248, -0.0795),
        PlaceCoord("the_curtain", "The Curtain", 51.5229, -0.0804),
        PlaceCoord("burbage_house_holywell", "The Burbage house, Holywell Street", 51.5251, -0.0790),
        PlaceCoord("the_jackdaw", "Tipping's ordinary, at the sign of the Jackdaw, Holywell Lane", 51.5243, -0.0788),
        PlaceCoord("st_leonards_shoreditch", "St Leonard's, Shoreditch", 51.5268, -0.0774),
        PlaceCoord("finsbury_fields", "Finsbury and Moorfields", 51.5205, -0.0870),
        PlaceCoord("pauls_churchyard", "St Paul's Churchyard and Paul's Walk", 51.5136, -0.0992),
        PlaceCoord("fields_printing_house", "Richard Field's house and shop, Blackfriars", 51.5126, -0.1029, ("field_printing_house",)),
        PlaceCoord("the_bell_carter_lane", "The Bell, Carter Lane", 51.5131, -0.1000),
        PlaceCoord("st_johns_clerkenwell", "The Revels Office, St John's", 51.5222, -0.1026, ("revels_office",)),
        PlaceCoord("southampton_house", "Southampton House, Holborn", 51.5181, -0.1115),
        PlaceCoord("grays_inn", "Gray's Inn hall, High Holborn", 51.5191, -0.1126),
        PlaceCoord("smithfield", "West Smithfield, Bartholomew Fair", 51.5187, -0.1008),
        PlaceCoord("somerset_house", "Somerset House, the Strand", 51.5117, -0.1174),
        PlaceCoord("tyburn", "Tyburn", 51.5133, -0.1603),
        PlaceCoord("old_swan_stairs", "Old Swan Stairs", 51.5094, -0.0889),
        PlaceCoord("london_bridge", "London Bridge", 51.5076, -0.0872),
        PlaceCoord("the_rose", "The Rose, Bankside", 51.5072, -0.0954),
        PlaceCoord("southwark_market", "Borough market and the Bankside walk", 51.5060, -0.0885),
        PlaceCoord("paris_garden_swan", "Paris Garden: the Swan a-building", 51.5073, -0.1027),
        PlaceCoord("whitehall_palace", "Whitehall Palace", 51.5046, -0.1260, ("whitehall",)),
        PlaceCoord("whitehall_tiltyard", "The Whitehall tiltyard", 51.5047, -0.1283),
        PlaceCoord("canon_row", "Sir Edward Hoby's house, Canon Row", 51.5014, -0.1255),
        PlaceCoord("westminster_hall", "Westminster Hall", 51.4999, -0.1254),
        PlaceCoord("greenwich_palace", "Greenwich Palace", 51.4822, -0.0067),
        PlaceCoord("richmond_palace", "Richmond Palace", 51.4612, -0.3089),
        PlaceCoord("the_feathers_richmond", "The Feathers, Richmond Green", 51.4616, -0.3060, ("richmond_lodging",)),
        PlaceCoord("henley_street", "The Henley Street house", 52.1939, -1.7080),
        PlaceCoord("holy_trinity", "Holy Trinity", 52.1866, -1.7075),
        PlaceCoord("guild_chapel_school", "The Guild Chapel and the King's New School", 52.1901, -1.7077, ("guild_chapel",)),
        PlaceCoord("new_place", "The great house by the chapel", 52.1907, -1.7076),
        PlaceCoord("high_cross_market", "The High Cross and the Thursday market", 52.1923, -1.7062, ("stratford_market",)),
        PlaceCoord("stratford_fire_ground", "The burned streets", 52.1945, -1.7068, ("stratford_north_lane",)),
        PlaceCoord("clopton_bridge", "Clopton Bridge", 52.1916, -1.7003),
        PlaceCoord("hewlands_shottery", "Hewlands, the Hathaway farm, Shottery", 52.1906, -1.7315, ("shottery",)),
        PlaceCoord("oxford_road", "The Oxford road", None, None),
        PlaceCoord("banbury_road", "The Aylesbury–Banbury road", None, None),
        PlaceCoord("uxbridge", "Uxbridge", 51.5450, -0.4817),
        PlaceCoord("beaconsfield", "Beaconsfield", 51.6083, -0.6571),
        PlaceCoord("high_wycombe", "High Wycombe", 51.6290, -0.7480),
        PlaceCoord("oxford", "Oxford", 51.7520, -1.2579),
        PlaceCoord("woodstock", "Woodstock", 51.8475, -1.3545),
        PlaceCoord("chipping_norton", "Chipping Norton", 51.9383, -1.5424),
        PlaceCoord("shipston_on_stour", "Shipston-on-Stour", 52.0630, -1.6247),
        PlaceCoord("chalfont_st_giles", "Chalfont St Giles", 51.6330, -0.5700),
        PlaceCoord("grendon_underwood", "Grendon Underwood", 51.8826, -1.0075),
        PlaceCoord("banbury", "Banbury", 52.0602, -1.3403),
    )
}


# § 7.8 Steps by day type
DAY_TYPE_STEP_BANDS: dict[str, tuple[int, int]] = {
    "Playing day": (9000, 15000),
    "Playing day (winter)": (6500, 11500),
    "Rehearsal-heavy day": (7000, 12000),
    "Writing day at the lodging": (2500, 6000),
    "Writing day at the lodging (Lent)": (4000, 7000),
    "Writing day at the lodging (Sunday)": (7000, 7000),
    "Rose day": (8000, 13000),
    "Household and rest": (2000, 5500),
    "Stratford ordinary day": (5000, 10500),
    "Riding day": (4500, 7000),
    "Foot road day": (44000, 68000),
    "Boat day": (3000, 7000),
    "Court day": (7500, 8500),
}


def sleeping_place_for_night(d: date) -> str:
    """Return the canonical place_slug where William sleeps on night of date `d` (§ 7.9)."""
    iso = d.isoformat()
    if "2025-01-01" <= iso <= "2025-03-25":
        return "ansell_house"
    if iso == "2025-03-26":
        return "high_wycombe"
    if iso == "2025-03-27":
        return "woodstock"
    if "2025-03-28" <= iso <= "2025-04-07":
        return "henley_street"
    if iso == "2025-04-08":
        return "woodstock"
    if iso == "2025-04-09":
        return "high_wycombe"
    if "2025-04-10" <= iso <= "2025-07-27":
        return "ansell_house"
    if iso == "2025-07-28":
        return "chalfont_st_giles"
    if iso == "2025-07-29":
        return "grendon_underwood"
    if iso == "2025-07-30":
        return "banbury"
    if "2025-07-31" <= iso <= "2025-08-17":
        return "henley_street"
    if iso == "2025-08-18":
        return "chipping_norton"
    if iso == "2025-08-19":
        return "oxford"
    if iso == "2025-08-20":
        return "beaconsfield"
    if iso == "2025-08-21":
        return "the_bell_carter_lane"
    if "2025-08-22" <= iso <= "2025-12-23":
        return "ansell_house"
    if "2025-12-24" <= iso <= "2025-12-28":
        return "the_feathers_richmond"
    return "ansell_house"


def season_body_params(d: date) -> dict[str, Any]:
    """Return seasonal sleep window, resting HR band, and active HR band from `world/world.md` § 7.8 (`5721-5737`)."""
    iso = d.isoformat()
    # Jan–Feb (`world.md:5723`): 21:15 → 06:45 | 7 h 30 – 8 h 15 | 60–64 (66–76 during the cold) | Walk 98–108
    if iso < "2025-03-01":
        if "2025-01-13" <= iso <= "2025-01-19":
            r_hr = (66, 76)
        elif iso == "2025-01-20":
            r_hr = (62, 66)
        else:
            r_hr = (60, 64)
        return {
            "bed_time": "21:15",
            "wake_time": "06:45",
            "sleep_min_range": (450, 495),
            "resting_hr": r_hr,
            "walk_hr": (98, 108),
        }
    # Mar (Lent, London) (`world.md:5724`): 21:45 → 05:45 | 7 h 15 – 7 h 45 | 58–62 | Walk 95–105
    if "2025-03-01" <= iso <= "2025-03-25":
        return {
            "bed_time": "21:45",
            "wake_time": "05:45",
            "sleep_min_range": (435, 465),
            "resting_hr": (58, 62),
            "walk_hr": (95, 105),
        }
    # Road, riding (26–28 Mar, 8–10 Apr) (`world.md:5725`): 21:30 → 04:45 | 5 h 30 – 6 h 30, broken | 62–66 | In the saddle 85–100; leading the horse uphill 110–120
    if iso in ("2025-03-26", "2025-03-27", "2025-03-28", "2025-04-08", "2025-04-09", "2025-04-10"):
        return {
            "bed_time": "21:30",
            "wake_time": "04:45",
            "sleep_min_range": (330, 390),
            "resting_hr": (62, 66),
            "walk_hr": (85, 120),
        }
    # Stratford, Lent (`world.md:5726`): 21:00 → 05:30 | 7 h 45 – 8 h 30 | 57–60 | —
    if "2025-03-29" <= iso <= "2025-04-07":
        return {
            "bed_time": "21:00",
            "wake_time": "05:30",
            "sleep_min_range": (465, 510),
            "resting_hr": (57, 60),
            "walk_hr": (92, 104),
        }
    # Apr–May (`world.md:5727`): 22:15 → 05:00 | 6 h 30 – 7 h | 58–61 | Stage 120–135; jig peaks 150–160
    if "2025-04-11" <= iso <= "2025-05-31":
        return {
            "bed_time": "22:15",
            "wake_time": "05:00",
            "sleep_min_range": (390, 420),
            "resting_hr": (58, 61),
            "walk_hr": (98, 135),
        }
    # Jun (riots) (`world.md:5728`): 23:00 → 04:20 | 4 h 45 – 5 h 45 | 62–68 | See special days
    if "2025-06-01" <= iso <= "2025-06-30":
        return {
            "bed_time": "23:00",
            "wake_time": "04:20",
            "sleep_min_range": (285, 345),
            "resting_hr": (62, 68),
            "walk_hr": (98, 124),
        }
    # Jul (`world.md:5729`): 23:00 → 04:30 | 5 h – 6 h | 60–65 | —
    if "2025-07-01" <= iso <= "2025-07-27":
        return {
            "bed_time": "23:00",
            "wake_time": "04:30",
            "sleep_min_range": (300, 360),
            "resting_hr": (60, 65),
            "walk_hr": (98, 120),
        }
    # Walk out (28–31 Jul) (`world.md:5730`): 21:30 → 03:45 | 5 h 30 – 6 h 15 | 62–70, rising with fatigue | Road average 108–118; hills 128–135
    if "2025-07-28" <= iso <= "2025-07-31":
        return {
            "bed_time": "21:30",
            "wake_time": "03:45",
            "sleep_min_range": (330, 375),
            "resting_hr": (62, 70),
            "walk_hr": (108, 135),
        }
    # Stratford, Aug (`world.md:5731`): 21:15 → 04:45 | 7 h – 7 h 45 | 57–60; 66–70 on 12–14 Aug (pain; 12–15 Aug per § 7.8 special days/illnesses) | —
    if "2025-08-01" <= iso <= "2025-08-17":
        r_hr = (66, 70) if "2025-08-12" <= iso <= "2025-08-15" else (57, 60)
        return {
            "bed_time": "21:15",
            "wake_time": "04:45",
            "sleep_min_range": (420, 465),
            "resting_hr": r_hr,
            "walk_hr": (92, 108),
        }
    # Walk back (18–21 Aug) (`world.md:5732`): 21:30 → 04:15 | 5 h 45 – 6 h 30 | 62–66 | Road 100–110
    if "2025-08-18" <= iso <= "2025-08-21":
        return {
            "bed_time": "21:30",
            "wake_time": "04:15",
            "sleep_min_range": (345, 390),
            "resting_hr": (62, 66),
            "walk_hr": (100, 110),
        }
    # Sep (and late Aug 22–31 return to London) (`world.md:5733`): 22:00 → 05:30 | 6 h 45 – 7 h 15 | 60–63; 64–70 from 25 Sep | —
    if "2025-08-22" <= iso <= "2025-09-30":
        r_hr = (64, 70) if iso >= "2025-09-25" else (60, 63)
        return {
            "bed_time": "22:00",
            "wake_time": "05:30",
            "sleep_min_range": (405, 435),
            "resting_hr": r_hr,
            "walk_hr": (96, 125),
        }
    # Oct (`world.md:5734`): 21:45 → 06:00 | 7 h – 7 h 45 | 10–16 Oct: 3 h 30 – 5 h | 66–70 on 10–11 Oct; 70–74 on 12–14 Oct; 59–62 by the 22nd | —
    if "2025-10-01" <= iso <= "2025-10-31":
        sleep_range = (210, 300) if "2025-10-10" <= iso <= "2025-10-16" else (420, 465)
        if "2025-10-01" <= iso <= "2025-10-09":
            r_hr = (64, 70)
        elif "2025-10-10" <= iso <= "2025-10-11":
            r_hr = (66, 70)
        elif "2025-10-12" <= iso <= "2025-10-14":
            r_hr = (70, 74)
        elif "2025-10-15" <= iso <= "2025-10-21":
            r_hr = (62, 66)
        else:
            r_hr = (59, 62)
        return {
            "bed_time": "21:45",
            "wake_time": "06:00",
            "sleep_min_range": sleep_range,
            "resting_hr": r_hr,
            "walk_hr": (96, 125),
        }
    # Nov (`world.md:5735`): 21:30 → 06:30 | 7 h 15 – 8 h | 58–62 | —
    if "2025-11-01" <= iso <= "2025-11-30":
        return {
            "bed_time": "21:30",
            "wake_time": "06:30",
            "sleep_min_range": (435, 480),
            "resting_hr": (58, 62),
            "walk_hr": (96, 125),
        }
    # Richmond (24–29 Dec) (`world.md:5737`): 00:30 → 06:45 | 5 h 30 – 6 h 15 | 60–64 | Stage peaks 140–150
    if "2025-12-24" <= iso <= "2025-12-29":
        return {
            "bed_time": "00:30",
            "wake_time": "06:45",
            "sleep_min_range": (330, 375),
            "resting_hr": (60, 64),
            "walk_hr": (100, 150),
        }
    # Dec (`world.md:5736`): 21:15 → 07:00 | 7 h 45 – 8 h 30 | 58–62 | —
    return {
        "bed_time": "21:15",
        "wake_time": "07:00",
        "sleep_min_range": (465, 510),
        "resting_hr": (58, 62),
        "walk_hr": (96, 130),
    }


# § 7.8 Special days (`world.md:5739-5768`) and Illnesses (`world.md:5770-5777`).
# Each date `YYYY-MM-DD` maps to overrides for that day's `body.jsonl` record
# (`experience-sleep-<YYYYMMDD>` ends on the morning of `YYYY-MM-DD`, so `night before` D
# lands on D and `night after` D lands on D + 1).
SPECIAL_DAY_BODY_OVERRIDES: dict[str, dict[str, Any]] = {
    # Cold with low fever (`world.md:5743-5745, 5774`):
    # Mon 13 – Sun 19 Jan: RHR 66 -> 76 at peak (17-18 Jan), back to 66 by 19th and 62 by 21st;
    # sleep disrupted 13-16 Jan, then long on 17-18 Jan.
    "2025-01-13": {"rhr_bpm": 66},
    "2025-01-14": {"sleep_min_range": (340, 390), "rhr_bpm": 69},
    "2025-01-15": {"steps": 3100, "sleep_min": 370, "rhr_bpm": 72, "hr_max_bpm": 96},
    "2025-01-16": {"sleep_min": 340, "rhr_bpm": 73},
    "2025-01-17": {"steps": 9400, "sleep_min": 350, "rhr_bpm": 74, "hr_max_bpm": 128},
    "2025-01-18": {"steps": 900, "sleep_min": 545, "rhr_bpm": 76},
    "2025-01-19": {"sleep_min": 520, "rhr_bpm": 66},
    "2025-01-21": {"rhr_bpm": 62},
    # Feb special days (`world.md:5746-5748`):
    "2025-02-14": {"steps": 11800},
    "2025-02-20": {"steps": 10900, "sleep_min": 330, "hr_max_bpm": 142},
    "2025-02-21": {"steps": 2700, "sleep_min": 360, "rhr_bpm": 66},
    "2025-02-22": {"sleep_min": 290},
    # Mar–May special days (`world.md:5749-5752`):
    "2025-03-15": {"steps": 9600},
    "2025-04-20": {"steps": 5200, "sleep_min": 460, "rhr_bpm": 58},
    "2025-05-17": {"steps": 3300},
    "2025-05-18": {"sleep_min": 230, "bed_time": "01:10", "wake_time": "05:00"},
    "2025-05-20": {"steps": 12600},
    # Jun–Jul special days (`world.md:5753-5755`):
    "2025-06-13": {"steps": 3900, "sleep_min": 310, "hr_max_bpm": 88},
    "2025-06-29": {"steps": 2100, "hr_max_bpm": 124},
    "2025-06-30": {"sleep_min": 160},
    "2025-07-24": {"steps": 1400, "sleep_min": 260, "rhr_bpm": 70},
    # Aug special days (`world.md:5756-5760, 4552, 4557, 4567, 4572, 4584, 4589`):
    "2025-08-09": {"steps": 8800},
    "2025-08-10": {"sleep_min": 135, "bed_time": "02:30", "wake_time": "04:45"},
    "2025-08-12": {"steps": 9200, "rhr_bpm": 68},
    "2025-08-13": {"steps": 400, "sleep_min": 310, "rhr_bpm": 69},
    "2025-08-14": {"steps": 700, "sleep_min": 320, "rhr_bpm": 67},
    "2025-08-15": {"sleep_min_range": (310, 360)},
    "2025-08-16": {"steps": 2900, "rhr_bpm": 61},
    "2025-08-17": {"steps": 4100},
    "2025-08-18": {"steps": 30000, "rhr_bpm": 64, "hr_max_bpm": 102},
    "2025-08-19": {"steps": 43500, "sleep_min": 370, "rhr_bpm": 63},
    "2025-08-20": {"steps": 66500, "sleep_min": 390},
    "2025-08-24": {"steps": 14200},
    "2025-08-27": {"steps": 7200, "rhr_bpm": 66},
    "2025-08-28": {"sleep_min": 370, "rhr_bpm": 65},
    # Oct–Dec special days (`world.md:5761-5768`):
    "2025-10-02": {"steps": 12900, "sleep_min": 285, "hr_max_bpm": 138},
    "2025-10-03": {"sleep_min": 500},
    "2025-10-10": {"sleep_min_range": (210, 285)},
    "2025-10-11": {"sleep_min_range": (210, 285)},
    "2025-10-12": {"sleep_min_range": (210, 285)},
    "2025-10-13": {"sleep_min_range": (210, 285)},
    "2025-10-14": {"steps": 1900, "sleep_min": 210, "hr_max_bpm": 148},
    "2025-10-15": {"sleep_min": 300},
    "2025-11-08": {"steps": 9900},
    "2025-11-09": {"sleep_min": 320, "bed_time": "00:30", "wake_time": "05:50"},
    "2025-11-17": {"steps": 15800},
    "2025-12-06": {"steps": 13400, "sleep_min": 250, "hr_max_bpm": 148},
    "2025-12-07": {"sleep_min": 390},
    "2025-12-09": {"steps": 16900, "hr_max_bpm": 96},
    "2025-12-10": {"sleep_min": 305, "bed_time": "01:20", "wake_time": "06:25"},
    "2025-12-24": {"steps": 6200},
    "2025-12-26": {"steps": 7500, "hr_max_bpm": 140},
    "2025-12-27": {"steps": 8200, "hr_max_bpm": 150},
    "2025-12-28": {"steps": 7900, "hr_max_bpm": 118},
    "2025-12-30": {"wake_time": "05:40"},  # the editor, 2026-11-17: the wall-to-wall day wakes "to one candle" at 05:50
}


def resolve_day_type_key(day_type_label: str, date_str: str) -> str:
    """Resolve a human day-type label from `dayplan.md` to a `DAY_TYPE_STEP_BANDS` key."""
    clean = day_type_label.strip()
    if clean in DAY_TYPE_STEP_BANDS:
        if clean == "Writing day at the lodging" and "2025-03-05" <= date_str <= "2025-04-19":
            return "Writing day at the lodging (Lent)"
        return clean
    lower = clean.lower()
    if "boat day" in lower:
        return "Boat day"
    if "rehearsal" in lower:
        return "Rehearsal-heavy day"
    if "writing day" in lower:
        if "2025-03-05" <= date_str <= "2025-04-19":
            return "Writing day at the lodging (Lent)"
        return "Writing day at the lodging"
    if "household" in lower or "rest" in lower:
        return "Household and rest"
    if "playing day" in lower:
        return "Playing day"
    if "rose day" in lower:
        return "Rose day"
    if "stratford" in lower:
        return "Stratford ordinary day"
    if "riding" in lower:
        return "Riding day"
    if "foot road" in lower:
        return "Foot road day"
    if "court" in lower:
        return "Court day"
    raise ValueError(f"Unrecognized day type label {day_type_label!r} on {date_str}")


def generate_body_metrics_for_day(
    date_str: str,
    day_type_key: str,
    explicit_steps: int | None = None,
) -> dict[str, Any]:
    """Deterministically generate a day's body metrics from § 7.8 for `date_str`.

    Precedence: a § 7.8 special day (`SPECIAL_DAY_BODY_OVERRIDES`) beats the season row;
    deterministic draws handle the rest.
    """
    d = date.fromisoformat(date_str)
    seed_int = int(hashlib.sha256(f"william-journal:body:{date_str}".encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed_int)
    special = SPECIAL_DAY_BODY_OVERRIDES.get(date_str, {})

    if "steps" in special:
        steps = int(special["steps"])
    elif explicit_steps is not None:
        steps = explicit_steps
    else:
        band = DAY_TYPE_STEP_BANDS[day_type_key]
        if day_type_key == "Writing day at the lodging (Lent)":
            # Draw in [4200, 5800] so it sits inside both general writing (2500-6000) and Lent (4000-7000)
            low, high = 4200, 5800
        else:
            low, high = band
        raw_steps = rng.randint(low // 50, high // 50) * 50
        steps = raw_steps

    season = season_body_params(d)
    sleep_low, sleep_high = special.get("sleep_min_range", season["sleep_min_range"])
    drawn_sleep_min = rng.randint(sleep_low // 5, sleep_high // 5) * 5
    sleep_min = int(special["sleep_min"]) if "sleep_min" in special else drawn_sleep_min
    deep_min = round(sleep_min * 0.18)
    rem_min = round(sleep_min * 0.22)
    awake_min = rng.randint(10, 25)
    core_min = max(20, sleep_min - deep_min - rem_min - awake_min)
    # Ensure exact sum
    sleep_min = deep_min + rem_min + core_min + awake_min

    rhr_low, rhr_high = season["resting_hr"]
    drawn_rhr = rng.randint(rhr_low, rhr_high)
    rhr_bpm = int(special["rhr_bpm"]) if "rhr_bpm" in special else drawn_rhr
    walk_low, walk_high = season["walk_hr"]
    hr_min_bpm = max(48, rhr_bpm - rng.randint(4, 7))
    hr_avg_bpm = rhr_bpm + rng.randint(10, 16)
    drawn_hr_max = rng.randint(walk_low, walk_high)
    hr_max_bpm = int(special["hr_max_bpm"]) if "hr_max_bpm" in special else drawn_hr_max
    hrv_ms = rng.randint(42, 64)

    # Foot distance only (river wherry distance on boat days is never turned into steps/walking distance)
    distance_km = round(steps * 0.00076, 2)
    active_energy_kcal = round(steps * 0.042 + 120)

    return {
        "date": date_str,
        "steps": steps,
        "distance_km": distance_km,
        "active_energy_kcal": active_energy_kcal,
        "sleep_min": sleep_min,
        "deep_min": deep_min,
        "rem_min": rem_min,
        "core_min": core_min,
        "awake_min": awake_min,
        "rhr_bpm": rhr_bpm,
        "hr_min_bpm": hr_min_bpm,
        "hr_avg_bpm": hr_avg_bpm,
        "hr_max_bpm": hr_max_bpm,
        "hrv_ms": hrv_ms,
        "bed_time": special.get("bed_time", season["bed_time"]),
        "wake_time": special.get("wake_time", season["wake_time"]),
    }
