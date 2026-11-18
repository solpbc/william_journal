"""The merge's additions: events from the Gemini build that Grok's book lacked.

Each one is an arranged thing the world dates (a § 6 entry with a time and a
place), rewritten in the book's own terse hand. Gemini's after-the-fact lines,
its logged calls and its civic sights are not taken: a calendar holds what was
planned. See ../merge.md.
"""

OWNER = "william_shakespeare"

# (date, start, end, title, location, place, organizer, attendees, created, layer, tier, entries, why)
EXTRAS = [
    ("2025-01-11", "18:15", "20:00", "Act 5 to Burbage, at the Jackdaw.", "the Jackdaw", "the_jackdaw",
     OWNER, ["richard_burbage"], "2025-01-09T21:00", "rehearsal", "T5", ["W004"],
     "The last act read to the man who will carry it. Put down two nights before, after the reckoning's hour."),
    ("2025-01-22", "10:30", "11:15", "Harrison, at Paul's.", "Paul's Churchyard", "pauls_churchyard",
     "john_harrison", [OWNER], "2025-01-20T19:00", "print", "T5", ["W111"],
     "The stationer who holds his poems, met at the stalls by word sent. How the poems sell is a question the book can answer."),
    ("2025-02-20", "18:30", "20:30", "Supper, after.", "the Cross Keys", "cross_keys_inn",
     "john_heminges", [OWNER, "george_bryan", "richard_burbage"], "2025-02-18T18:00", "social", "T5", ["S018"],
     "The first day's supper, set with the full rehearsal. What is talked of there stays in the entry, not on the line."),
    ("2025-03-10", "08:30", "11:00", "The baskets to Shoreditch.", "the Cross Keys", "cross_keys_inn",
     "john_heminges", [OWNER, "abel_garnish", "nick_sorrell", "sam_latchet"], "2025-03-08T18:00", "company_business", "T5", ["W118"],
     "Lent's first errand: the company's stuff carted from the inn to the Theatre for Easter."),
    ("2025-03-12", "10:00", "12:00", "Kemp's bit, at the Theatre.", "the Theatre", "the_theatre",
     OWNER, ["will_kemp", "richard_burbage", "abel_garnish", "thomas_pope"], "2025-03-10T20:00", "rehearsal", "T5", ["S025"],
     "A Lent morning's script-work. Kemp grumbles at it; the book only says whose bit."),
    ("2025-03-18", "08:30", "10:30", "The trap, with James Burbage.", "the Theatre", "the_theatre",
     "james_burbage", [OWNER, "humphrey_larkham", "sam_latchet"], "2025-03-15T18:00", "company_business", "T5", ["G019"],
     "The stage trap mended while the house is dark. The owner's errand, so his name is on it."),
    ("2025-04-04", "09:00", "11:00", "My father's shops. v li.", "the High Cross", "high_cross_market",
     OWNER, ["hamnet_sadler"], "2025-04-02T20:00", "money", "T5", ["W123"],
     "Three shop debts paid for his father, written as a sum to carry. Answers 'what did Stratford cost me'."),
    ("2025-04-25", "17:30", "19:00", "The first scene, to Burbage.", "the Jackdaw", "the_jackdaw",
     OWNER, ["richard_burbage"], "2025-04-24T21:00", "rehearsal", "T5", ["W036"],
     "Richard's first scene heard by Burbage, a fortnight into the season. Pairs with the Act 5 reading in January."),
    ("2025-07-25", "07:30", "11:30", "St James. Field's, in the morning.", "Field's printing house", "fields_printing_house",
     "richard_field", [OWNER, "jacqueline_field"], "2025-07-20T20:00", "social", "T5", ["W308"],
     "The holiday morning at the Fields' before the last playing days. Field stays traceable through the summer."),
    ("2025-08-05", "18:30", "20:30", "Quiney and Sturley, at my father's.", "Henley Street", "henley_street",
     "john_shakespeare", [OWNER, "richard_quiney", "abraham_sturley"], "2025-08-02T18:00", "social", "T5", ["S080"],
     "The harvest talk at the Henley Street table. A Stratford evening on the calendar."),
    ("2025-08-12", "07:00", "10:40", "The Sadlers' barn. To raise the frame.", "the fire ground", "stratford_fire_ground",
     "hamnet_sadler", [OWNER, "richard_shakespeare", "john_shakespeare"], "2025-08-09T19:00", "family_day", "T5", ["W069"],
     "The morning the back goes. The calendar holds only the plan; the strain is in the body data from today."),
    ("2025-10-24", "09:00", "11:00", "Rehearsal, 9. The vial, with Nick.", "the Theatre", "the_theatre",
     OWNER, ["nick_sorrell", "augustine_phillips", "abel_garnish"], "2025-10-22T20:00", "rehearsal", "T5", ["W091"],
     "Juliet's potion speech tried with the boy. What happens to his voice is the entry's, not the line's."),
    ("2025-10-29", "10:30", "13:00", "The Mayor's show.", "Old Swan Stairs", "old_swan_stairs",
     OWNER, [], "2025-10-25T18:00", "other", "T2", ["S101"],
     "Lord Mayor's Day, a public sight he means to see. The day's cross is its own line and is not linked to this one."),
    ("2025-11-11", "06:30", "08:45", "Martinmas. Leadenhall, with Mistress Ansell.", "Leadenhall", "leadenhall",
     "dorcas_ansell", [OWNER], "2025-11-08T19:00", "other", "T5", ["W093"],
     "Winter stores laid in, carrying for the household. Martinmas as an errand, not only a feast."),
    ("2025-11-12", "09:00", "10:00", "The book to Garnish.", "the Theatre", "the_theatre",
     OWNER, ["abel_garnish", "john_heminges"], "2025-11-11T20:00", "rehearsal", "T5", ["W411"],
     "Romeo finished on Martinmas, the book handed over next morning. Put down the night he finished."),
    ("2025-11-22", "18:30", "20:30", "Kemp, at the Jackdaw. Three pages.", "the Jackdaw", "the_jackdaw",
     OWNER, ["will_kemp", "richard_burbage", "abel_garnish"], "2025-11-20T21:00", "social", "T5", ["W097"],
     "The first pages of the Dream's clowns, given to the clown. After the reckoning, so it does not cross it."),
    ("2025-11-27", "18:00", "20:00", "The mechanicals, with Kemp and Phillips.", "the Theatre", "the_theatre",
     OWNER, ["will_kemp", "augustine_phillips", "humphrey_larkham"], "2025-11-25T20:00", "rehearsal", "T5", ["G088"],
     "An evening trying the weaver's pages. The Dream begins to have a calendar."),
    ("2025-12-08", "09:00", "10:15", "Rehearsal, 9. Richard, for Canon Row.", "the Theatre", "the_theatre",
     OWNER, ["nick_sorrell", "richard_burbage", "humphrey_larkham"], "2025-12-07T19:00", "rehearsal", "T5", ["G086"],
     "Set the night of the Hoby summons, for the private night on Tuesday."),
    ("2025-12-17", "09:00", "11:00", "Court stuff, with Edith.", "the Theatre", "the_theatre",
     "edith_kettlewood", [OWNER, "augustine_phillips", "nick_sorrell", "sam_latchet", "humphrey_larkham"], "2025-12-13T18:00", "company_business", "T5", ["G095"],
     "Apparel, parts and properties looked over before court. The tirewoman's morning, so her name leads."),
    ("2025-12-21", "12:30", "14:30", "Dinner at the Fields'. A goose.", "Field's printing house", "fields_printing_house",
     "richard_field", [OWNER, "jacqueline_field"], "2025-12-15T12:30", "social", "T5", ["W418"],
     "Asked on Monday's call: St Thomas's, dinner after sermon, before he goes up to court. Replaces Grok's habit Sundays."),
    ("2025-12-23", "09:30", "12:00", "Hose, baskets, the order of going.", "the Theatre", "the_theatre",
     "john_heminges", [OWNER, "george_bryan", "will_kemp", "thomas_pope", "abel_garnish", "sam_latchet", "nick_sorrell"], "2025-12-20T18:00", "company_business", "T5", ["W420"],
     "The muster for Richmond, the first dark day. Set at the last reckoning."),
    ("2025-12-29", "14:30", "17:00", "The Bull. Spiced ale.", "the Bull, Bishopsgate", "bull_inn",
     "richard_burbage", [OWNER, "will_kemp", "john_heminges", "augustine_phillips", "thomas_pope", "george_bryan"], "2025-12-28T23:30", "social", "T5", ["M056"],
     "The fellows' supper on the way home from court. Put down at Richmond, after the last night."),
]


def add_extras(book):
    for (d, start, end, title, loc, place, org, att, created, layer, tier, entries, why) in EXTRAS:
        book.add(
            d, title, start=start, end=end, location=loc, place=place,
            organizer=org, attendees=att or None, created=created,
            layer=layer, tier=tier, entries=entries, why=why,
        )
    return len(EXTRAS)
