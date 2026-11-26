/* William's world, Wed 22 Oct 1595, evening — the content every desktop shares.
   Drawn from the william journal canon (world.md § 2.6, § 3, § 6: G081, S097, W406).
   Quoted play text is public-domain quarto text (R&J Q2 1599, R2 Q1 1597, Sonnets 1609)
   in an invented setting; everything else is new fiction for the demo journal. */
window.W1595 = {
  owner: "William Shakespeare",
  place: "Mistress Ansell's, St Helen's, Bishopsgate",
  // 1595 Julian is held on the same month/day in 2025 (identical calendar).
  start: "2025-10-22T20:05:00",

  sheets: [
    {
      id: "romeo-4-3",
      bundle: "romeo", meta: "today, 19:40",
      title: "Romeo — the girl's night, alone",
      label: "Romeo and Juliet, 4.3 (label only) · sheet half full",
      flag: "public-domain text (Q2, 1599) in an invented setting",
      html:
`<p class="sd">Enter Iuliet alone, the viall in her hand.</p>
<p><span class="sp">Iul.</span> Farewel, God knowes when we shall meete againe.<br>
I haue a faint cold feare thrills through my veines,<br>
That almost freezes vp the heate of life:<br>
Ile call them backe againe to comfort me.<br>
Nurse, what should she do here?<br>
My dismall sceane I needs must act alone.<br>
Come Viall, <s>what if this potion</s> what if this mixture do not worke at all?<br>
Shall I be married then to morrow morning?<br>
No, no, this shall forbid it, lie thou there.<span class="cross" title="return here">✠</span><br>
What if it be a poyson which the Frier<br>
Subtilly hath ministred to haue me dead,<br>
Least in this mariage he should be dishonourd,<br>
Because he married me before to Romeo?</p>
<p class="gap">&nbsp;</p>`
    },
    {
      id: "richard-3-2",
      bundle: "richard", meta: "Tue xxj Oct",
      title: "Richard II — the landing",
      label: "Richard II, 3.2 (label only) · sheet three-quarters full",
      flag: "public-domain text (Q1, 1597) in an invented setting",
      html:
`<p><span class="sp">King.</span> No matter where, of comfort no man speake:<br>
Lets talke of graues, of wormes, and Epitaphs,<br>
Make dust our paper, and with raynie eies<br>
Write sorrow on the bosome of the earth.</p>
<p>For Gods sake let vs sit vpon the ground,<br>
And tell sad stories of the death of Kings,<br>
How some haue been deposde, some slaine in warre,<br>
Some haunted by the ghosts they haue deposed,<br>
Some poisoned by their wiues, some sleeping kild,<br>
All murthered.</p>
<p class="note">Pope's Gaunt — Garnish's short cue stands. Larkham to copy into York and the Queene. viij d of the stock.</p>`
    },
    {
      id: "tables",
      bundle: "household", meta: "today, 18:24",
      title: "The tables",
      label: "pocket writing-tables · erasable leaf",
      flag: "new fiction",
      html:
`<p>Deare wife, the money went by Hobbins and I pray it came whole.</p>
<p>I am well, and the cold is gone with the leaues.</p>
<p>Kisse them all for me, and tell Hamnet his letter was a good one.</p>
<p class="gap">&nbsp;</p>`
    },
    {
      id: "sonnet-leaf",
      bundle: "verse",
      locked: true, meta: "Midsummer",
      title: "A single leaf",
      label: "private verse leaf · fair copy",
      flag: "public-domain text (Sonnets, 1609) in an invented setting",
      html:
`<p>When to the Sessions of sweet silent thought,<br>
I sommon vp remembrance of things past,<br>
I sigh the lacke of many a thing I sought,<br>
And with old woes new waile my deare times waste:<br>
Then can I drowne an eye (vn-vs'd to flow)<br>
For precious friends hid in deaths dateles night,<br>
And weepe a fresh loues long since canceld woe,<br>
And mone th' expence of many a vannisht sight.</p>`
    }
  ],

  // Letters: in = received, out = sent. via: carrier | boy | hand
  threads: [
    {
      id: "anne", who: "Anne Shakespeare", where: "Henley Street, Stratford",
      via: "carrier", cost: "ij d", seal: "#8a2a1c",
      letters: [
        { dir: "in", date: "Thursday the ij of October", via: "Hobbins, at the Bell",
          body: "Husband, I haue yours of Bartholomewtide. The harvest is in and thin, and the loaf here is as short as yours. Your father is well and merry and will not be told about the lime. Judith hath had the cough and is mending. Send by Hobbins the ribbon you promised Susanna, blue and not green, for she will know. From Stratford this Michaelmas week. Your wife, Anne." },
        { dir: "out", date: "Thursday the ij of October", via: "Hobbins, from the Bell",
          body: "Deare wife, the ribbon is blue. The money is in the fold. The king play draws and Burbage is a wonder in it. Commend me to my father and mother. From London this ij of October. W.S.",
          state: "delivered" }
      ],
      reply: { date: "Thursday the xxiij of October", via: "Hobbins, at the Bell",
        body: "The money came. Susanna is reading the Gospel to her grandmother of an evening and corrects the curate vnder her breath. Judith hath a new song off a pedlar and will not say what she gaue for it. Hamnet and the Sadler boy haue dammed the brook at Shottery and been made to vndam it. Master Quiney is for London at Martinmas on the town's business and means to find you. He is a good man. Keep your purse in your other hose. Anne." }
    },
    {
      id: "heminges", who: "John Heminges", where: "Aldermanbury",
      via: "boy", cost: "j d", seal: "#3a3a2a",
      letters: [
        { dir: "in", date: "this morning, after the trestle", via: "by the boy",
          body: "Item, Larkham's viij d out of the stock, and he marks every roll he mends so a stale one may be known. The king is billed againe Thursday week. Paper first, then mouths. J.H." }
      ],
      replies: [
        "Agreed, and the viij d stands. — J.H.",
        "Item, noted. Bryan asks who carries the court's money at Christmas. Not you. — J.H.",
        "Paper first. Then mouths. Then supper. — J.H."
      ]
    },
    {
      id: "burbage", who: "Richard Burbage", where: "Holywell Street, Shoreditch",
      via: "boy", cost: "j d", seal: "#5a2a4a",
      letters: [
        { dir: "in", date: "Tuesday, after the king", via: "by the boy",
          body: "Will — the Pomfret speech wants a breath after 'thoughts'. Mend it, or I take one anyway and the yard will think it mine. Dick." },
        { dir: "out", date: "Tuesday night", via: "by the boy",
          body: "Take the breath. It was always thine. W.", state: "delivered" }
      ],
      replies: [
        "Then I'll take two. — Dick",
        "The boy says thou wert writing by one candle. Buy another. — Dick",
        "Nick held the cue today. Hold the scene for him. — Dick"
      ]
    },
    {
      id: "field", who: "Richard Field", where: "Blackfriars, at the press",
      via: "boy", cost: "j d", seal: "#2a3a5a",
      letters: [
        { dir: "in", date: "the xvij of October", via: "by his prentice",
          body: "Master Shakespeare, my Holinshed hath lodged at St Helen's since Lent. I do not ask for it. I only note that it hath not paid rent. R. Field." }
      ],
      replies: [
        "Keep it till the king is done. Then keep it longer, I suppose. — R.F.",
        "The Plutarch sheets are dry, if you would see Caesar in clean ink. — R.F."
      ]
    },
    {
      id: "kemp", who: "Will Kemp", where: "the Theatre",
      via: "hand", cost: "—", seal: "#6a5a1a",
      letters: [
        { dir: "in", date: "Monday", via: "left on the tiring-house peg",
          body: "Thy king hath no fool. The yard will supply one, and it will be me, and it will be worse for the king. Kemp." }
      ],
      replies: [ "Words, words. Bring me a part with a dog in it. — Kemp" ]
    },
    {
      id: "lord", who: "my lord", where: "Holborn",
      via: "hand", cost: "—", seal: "#1a1a1a",
      letters: [
        { dir: "out", date: "Midsummer", via: "left at the gate",
          body: "My lord, I send these leaves as a pledge of what I owe and cannot reckon. Your lordship's in all duty. W.S.",
          state: "left at the gate · no answer" }
      ],
      replies: []
    }
  ],

  // Hobbins comes into the Bell about every third Thursday.
  carrierDays: ["2025-10-02", "2025-10-23", "2025-11-13", "2025-12-04", "2025-12-18"],

  // Account book. Amounts in pence. exp = expected, rec = received, paid = laid out.
  ledger: [
    { date: "Sat xviij Oct", item: "Told in the coffer this day", note: "count", rec: 7488 },
    { date: "Sun xix Oct", item: "Item to the poore boxe at St Helen's", paid: 1 },
    { date: "Mon xx Oct", item: "Item recd. of Mr Heminges, my share of the week, the King twice", exp: 400, rec: 400 },
    { date: "Mon xx Oct", item: "Item the Christmas playes at court, my share", exp: 720, rec: 0, note: "expected" },
    { date: "Tue xxj Oct", item: "Item a penny loafe, short of the notch", paid: 1 },
    { date: "Wed xxij Oct", item: "Item to Larkham for the copying, of the stock (my part)", paid: 1 },
    { date: "Wed xxij Oct", item: "Item a quire of paper", paid: 5 },
    { date: "Wed xxij Oct", item: "Item a horne of Mrs Ansell's inke", paid: 2 },
    { date: "Thu xxiij Oct", item: "Item to Hobbins, a letter", paid: 2, note: "tomorrow" }
  ],

  commonplace: [
    { day: "2025-10-22", head: "Of Kings", text: "They did not hang this one. They waited.", src: "said at the Jackdaw, of the earl in the Tower" },
    { day: "2025-10-02", head: "Of Kings", text: "A king that weepes like a begger. Note it, and do not pity him for it.", src: "mine" },
    { day: "2025-10-22", head: "Of Time", text: "Ten years, and then a Sunday.", src: "mine, tonight" },
    { day: "2025-10-22", head: "Words", text: "Paper first, then mouths.", src: "J.H., at the trestle" },
    { day: "2025-03-06", head: "Words", text: "Romeus. Romeo is better in the mouth.", src: "Lent, of Brooke" },
    { day: "2025-10-22", head: "Faces", text: "Nick at the cue: the voice holds, but he spends it like a man with a week's wages.", src: "this morning" },
    { day: "2025-10-18", head: "Prices", text: "The penny loafe on Saturday, a barley-corne short of the notch againe.", src: "Mrs Ansell's board" },
    { day: "2025-10-02", head: "Prices", text: "Oats deare at Oxford, malt dearer at home.", src: "Hobbins" },
    { head: "Of Love", text: "", src: "" }
  ],

  // The stalls of Paul's Churchyard and about the town: the Bookwheel's pages.
  pages: {
    "pauls": {
      sign: "Paules Church-yard", title: "The stalls of Paul's Churchyard",
      body: [
        ["h", "What is new at the stalls this weeke"],
        ["link", "white-greyhound", "At the signe of the White Greyhound", "Venus and Adonis, the fourth time imprinted. Lucrece, still selling."],
        ["link", "register", "The Register of the Stationers", "Enquire what is entred, and to whom."],
        ["link", "holinshed", "Holinshed's Chronicles, the second edition", "Of Richard the second, his deposing. Field's copie is elsewhere."],
        ["link", "bills", "The bills on the posts", "What the Rose and the Theatre play this weeke."],
        ["link", "news", "Newes, ballads and proclamations", "Bread, the Tower, and a new Mayor on the xxix."],
        ["p", "Bookes sold here in quires or bound in calf. Ballads a penny. No credit on Sundays."]
      ]
    },
    "white-greyhound": {
      sign: "the White Greyhound, Paules Church-yard", title: "At the signe of the White Greyhound",
      body: [
        ["title", "VENVS AND ADONIS", "Vilia miretur vulgus: mihi flavus Apollo / Pocula Castalia plena ministret aqua.", "Imprinted by Richard Field, and are to be sold at the signe of the white Greyhound in Paules Church-yard."],
        ["p", "Bound, xij d. In quires, vj d. The bookseller says the Inns men buy it in pairs, one to read and one to lend."],
        ["link", "pauls", "Back to the stalls", ""]
      ]
    },
    "register": {
      sign: "Stationers' Hall", title: "The Register of the Company of Stationers",
      search: true,
      entries: [
        ["xviij Aprilis 1593", "Richard Field", "a booke intituled Venus and Adonis"],
        ["ix Maij 1594", "John Harrison", "a booke intituled the Ravyshement of Lucrece"],
        ["xj Octobris 1594", "Simon Waterson", "the first fowre bookes of the civill warres, by Samuel Daniell"],
        ["1595", "Richard Field", "the lyves of the noble Grecians and Romanes, by Plutarke, Englished by Sir Thomas North"],
        ["1595", "a booke of Saint Peters complaint, with other poems"],
        ["1595", "Cuthbert Burby", "a ballad of the deare price of corne"],
        ["1595", "Thomas Creede", "the lamentable tragedie of Locrine"]
      ],
      body: [["p", "Enter a word of the title, or the name of a stationer, and the clerk will turn the leaves."]]
    },
    "holinshed": {
      sign: "Holinshed, the second volume", title: "The Chronicles of England, Scotland, and Irelande",
      body: [
        ["p", "Of king Richard the second. … Thus was king Richard deprived of all kinglie honour and princelie dignitie, by reason he was so given to follow evill counsell, and used such inconvenient waies and meanes, through insolent misgovernance, and youthfull outrage."],
        ["note", "Pomfret. a groome. the horse."],
        ["link", "pauls", "Back to the stalls", ""]
      ]
    },
    "bills": {
      sign: "the posts at Bishopsgate", title: "The bills on the posts, this weeke",
      body: [
        ["bills", [
          ["Mon xx", "The Rose", "Crack Me This Nut", "the Lord Admirall his Seruants"],
          ["Tue xxj", "The Theatre", "The Tragedie of King Richard the second", "the Lord Chamberlaine his Seruants"],
          ["Tue xxj", "The Rose", "Longshankes", "the Lord Admirall his Seruants"],
          ["Wed xxij", "The Rose", "The New Worlds Tragedie", "the Lord Admirall his Seruants"],
          ["Thu xxiij", "The Rose", "The Wonder of a Woman", "the Lord Admirall his Seruants"],
          ["Fri xxiiij", "The Rose", "Crack Me This Nut", "the Lord Admirall his Seruants"],
          ["Sat xxv", "The Rose", "The first part of Hercules", "the Lord Admirall his Seruants"],
          ["Thu xxx", "The Theatre", "The Tragedie of King Richard the second", "the Lord Chamberlaine his Seruants"]
        ]],
        ["link", "pauls", "Back to the stalls", ""]
      ]
    },
    "news": {
      sign: "the Stocks market", title: "Newes, ballads and proclamations",
      body: [
        ["h", "Said about the town"],
        ["p", "That Philip Howard, that was Earle of Arundel, is dead in the Tower on Sunday, ten yeares a prisoner. Said lowly, at the Jackdaw and at the parish clerk's."],
        ["p", "That the Lord Maior elect is sworne on the xxix, with the shewe upon the water if it be faire."],
        ["p", "That the penny loafe holdeth his price and loseth his weight."],
        ["h", "A ballad, a penny"],
        ["p", "A lamentable ditty of the deare price of corne, to the tune of Fortune my foe."],
        ["link", "pauls", "Back to the stalls", ""]
      ]
    }
  },

  // The almanack: October 1595 (Julian), on 2025's identical calendar.
  almanac: {
    "2025-10-02": ["Carrier in at the Bell", "The king first played · xj li vj s in the boxes"],
    "2025-10-04": ["The week reckoned"],
    "2025-10-06": ["S. Faith", "Full moone"],
    "2025-10-09": ["Michaelmas terme beginneth"],
    "2025-10-11": ["The dawn parting written, in the grey"],
    "2025-10-13": ["S. Edward", "The Sunne entreth Scorpio"],
    "2025-10-14": ["Last quarter"],
    "2025-10-18": ["S. Luke", "Coffer told"],
    "2025-10-19": ["The faire bundle tied, red thred"],
    "2025-10-20": ["Rose · Crack Me This Nut", "The court to Richmond"],
    "2025-10-21": ["Theatre · the king", "Rose · Longshankes"],
    "2025-10-22": ["New moone", "Theatre, ix · Larkham and the copying", "Playing at ij", "Rose · The New Worlds Tragedie"],
    "2025-10-23": ["Carrier in at the Bell", "Supper with Daniel, near Paul's", "Rose · The Wonder of a Woman"],
    "2025-10-24": ["Rose · Crack Me This Nut"],
    "2025-10-25": ["Rose · Hercules, the first part", "The week reckoned"],
    "2025-10-28": ["SS. Simon and Jude"],
    "2025-10-29": ["The Lord Maior sworne"],
    "2025-10-30": ["Theatre · the king, billed againe", "First quarter"],
    "2025-11-01": ["All Saints"],
    "2025-11-05": ["Full moone"],
    "2025-11-11": ["Martinmas · Master Quiney for London"],
    "2025-11-13": ["Carrier in at the Bell"],
    "2025-09-29": ["Michaelmas · quarter day"],
    "2025-09-21": ["S. Matthew"]
  },
  weather: ["Faire and colde", "Clowdy, with winde", "Raine toward night", "Mistie mornings", "Faire", "Windes and showres", "Colde and drie", "Foule weather"],
  physick: ["Good to let bloud", "Good to sowe", "Purge not", "Good to bathe", "Cut not the haire", "Indifferent", "Good to take physicke"]
};
