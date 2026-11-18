# 06 · Scene seeds for 1595: the master list

**William journal sourcebook, part 6** (request deliverable 9). Built 2026-11-14 from the three deep-research reports in `research/`: chatgpt.md (GPT), gemini.md (GEM) and claude.md (CLA). Project: index.md · request and tier definitions: research-request.md.

Real history, invented days. Every seed below has a **true anchor with its tier** and an **invented scene** on top. The scene is always T5 unless the anchor says otherwise. Hamnet is ten this year and dies in August 1596; no seed plays on that (section 5).

## How to read this

| Item | Meaning |
|---|---|
| **Dates** | Julian (Old Style), as England reckoned them. Documents dated 1 Jan to 24 Mar say "1594"; those days are our 1595 and are written 1594/5 where a record is quoted. New Style ran 10 days ahead. The journal holds each date on the same month and day in 2025 (editor ruling), whose calendar matches 1595's exactly, so the weekdays below are 2025's too. |
| **Weekdays** | Computed in code from the Julian day number, not taken from the reports. Checked against three known 1595 points: 1 Jan is a Wednesday, the riot pamphlet's "Thursday the 24 of July", and Hoby's "Teusdaie" 9 Dec. Easter 1595 (Julian computus) is Sunday 20 April. |
| **Moon phases** | Recomputed (Meeus mean-phase method with periodic terms; tested on the known new moons of 6 Jan 2000 and 25 Jan 2024). GEM's moon times match to within minutes, except its 11 Jun full moon (GEM 08:57 UT; computed 22:06 UT). They are calculations, so this file never tiers them T1. |
| **Tiers** | T1 documented · T2 scholarly consensus · T3 contested · T4 tradition · T5 imagined. "T1/T3" means the record is T1 and its reading is T3. |
| **Journal source** | The capture a seed naturally exercises, main one first: `meeting` (audio meeting) · `call` · `memo` (voice memo) · `calendar` · `notes` (notes and drafts, letters) · `screen` (what he reads or watches) · `photo` · `location` · `body` (steps, sleep, heart rate, illness). |
| **Reports** | GPT seeds are cited by their date label (that report doesn't number them); GEM and CLA by their seed number. **ED** marks an anchor added by this edit from a checked source. |
| **Check** | OK = anchor stands. **Fixed** = a report's anchor was wrong and is corrected here. **Flag** = not settled; check before it carries weight. **Care** = see section 5. |

**Counting.** The reports supplied **207 seeds** (GPT 83 rows; GEM 62; CLA 62). Merged and deduplicated, that is **117 seeds** from the reports plus **1 added** here (S087, Burghley's gout, to cover illness): **118 in all**. Three seeds were dropped and are not in the list (section 5): GPT 18 May (a forged Henslowe entry), GEM 43 (Forman) and GEM 58 (Hawkins's death, news that can't reach London in 1595). Bare Rose listings, which are one play on one day, are folded into one "rival run" row per stretch; their new plays and notable days keep their own rows.

## 1. Master seed list

### January (documents date these 1594)

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S001 | Wed 1 Jan | Bishopsgate lodging | alone | Opens the year's book: tallies the two Christmas shows at Greenwich (St Stephen's and Innocents' Day 1594) and the £20 the Queen's warrant will bring. | Court plays 26 and 28 Dec 1594, paid on a Council warrant of 15 Mar 1594/5, TNA E 351/542 m.207d (T1). St Helen's as his 1595 lodging (T3). | notes, calendar | GPT 1 Jan; GEM 1; CLA 1 | Fixed: GEM has him 'entering his 31st year'; he turns 31 in April. |
| S002 | Wed–Mon 1–6 Jan | Greenwich (court news) | Alleyn and the Admiral's Men; Kemp | Company gossip: the rivals play before the Queen on New Year's Day and Twelfth Day. Kemp mocks Alleyn's thundering Tamburlaine. | Admiral's Men at court 1 and 6 Jan 1595 (T1, Colthorpe); the same membrane pays Alleyn, Jones and Singer £30 (T1). Tamburlaine in the Rose repertory (T1). | meeting, screen | GPT 1 Jan, 6 Jan; CLA 2 | OK. |
| S003 | early Jan | Gray's Inn, Holborn | law students | Talk of the 'Night of Errors' (28 Dec 1594), when the Gray's Inn revels fell into chaos and a Comedy of Errors was played by the players. The Prince of Purpoole's revels go on (3 Jan device). | Gesta Grayorum (printed 1688; T1 as text) and Colthorpe for 3 Jan (T1). That the players were his company (T2). How they also played Greenwich on 28 Dec (T3, unresolved). | meeting, memo | CLA 3; GPT 28 Dec | Flag: the 28 Dec clash with the court record is unresolved. Write it as an open question in his voice. |
| S004 | Wed 8 Jan | Bishopsgate | alone | Voice note at the first-quarter moon: first sketches toward Love's Labour's Lost or Richard II. | Both plays c.1595 (T2). Moon phase computed, not recorded. | memo | GEM 2 | Fixed tier: GEM labels moon phases T1; they are computed. |
| S005 | Fri–Mon 10–13 Jan | Shoreditch | word of mouth | The Rose's 'what's on': The Grecian Comedy, then A Knack to Know an Honest Man. | Henslowe's diary, Dulwich MSS 7 (T1). January dates from GPT, not rechecked. | screen | GPT 10 Jan, 13 Jan | OK (January dates not rechecked). |
| S006 | Wed 15 Jan | St Helen's, Bishopsgate | alone | Full moon on a hard winter night; photographs the frosted street by Crosby Place. | Full moon 15 Jan (computed). Cold 1590s winters (T2, general). No daily London weather record for 1595 (T3 gap). | photo, body | GEM 3 | Flag: the frost is invented; Crosby Place is a real St Helen's house. |
| S007 | mid-Jan | Cross Keys Inn, Gracechurch St | sharers, hired men | Morning rehearsal from cue scripts; afternoon play in cold daylight. | Hunsdon's letter of 8 Oct 1594 asking the Lord Mayor to let his new company play at the Cross Keys this winter (T1, Remembrancia II.33). That they did (T2/T3). The work rhythm (T2). | meeting, body, location | GPT mid-Jan | Fixed: GPT sets it at the Theatre; winter 1594/5 playing was more likely at the Cross Keys. |
| S008 | Thu 23 Jan | Westminster Hall | lawyers, clients | Hilary term opens; the town fills with lawyers and paper, and the audiences with Inns men. | Law-term rules (T1); the computed day (T2, ±1–2 days). | calendar, location | GEM 4; GPT late Jan | Fixed: dropped GEM's specific Common Pleas case (unverified, off-topic). |
| S009 | Sun 26 Jan | Greenwich (news) | the court; the Earl of Derby and Elizabeth de Vere | News of the Derby wedding at Greenwich with the Queen present. Did anyone think of a wedding play? | Wedding 26 Jan 1595 at Greenwich (T1, Colthorpe). As the occasion for the Dream (T3; Derby kept his own players). | meeting, calendar | CLA 4 | OK. |
| S010 | Thu 30 Jan | Cross Keys Inn | Shakespeare, Kemp, Burbage | Sharers plan the run to Shrovetide. | As above (T1 letter, T2 venue). New moon computed. | meeting | GEM 5 | OK. |

### February (documents date these 1594)

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S011 | Sat 1 Feb | Thames at Greenwich, then Tower Hill | the Gray's Inn 'Prince of Purpoole' (Henry Helmes) | The Prince comes up the river with 15 barges, music, trumpets and guns, lands at Tower Hill and rides through St Paul's Churchyard. He photographs it from the bank. | Gesta Grayorum, quoted in Colthorpe 1595 (T1). | photo, location | CLA 5 | OK (15 barges confirmed). |
| S012 | Sun 2 Feb | letter home | Hamnet and Judith; Anne | Candlemas: the twins turn ten. A short letter home. | Baptism 2 Feb 1585, Holy Trinity register (T1). The letter (T5; no letter by him survives). | notes, calendar | CLA 6 | Care: an ordinary birthday. Nothing foreshadowed (see section 5). |
| S013 | Wed 5 Feb | Bankside | — | The Rose plays Mahomet; talk compares it with Tamburlaine. | Henslowe (T1; not rechecked). | screen | GPT 5 Feb | OK. |
| S014 | Thu 6 Feb | Thames-side tavern | watermen, sailors | Raleigh's departure for Guiana is talked over, some days after he sailed from Plymouth. | Raleigh's own Discovery of Guiana (1596): 'On Thursday the sixth of February, in the year 1595, we departed England' (T1 for the date). The hearing (T5). | meeting, screen | GPT 6 Feb; GEM 6; CLA 7 | Fixed: CLA tiers it T2, but the date is Raleigh's own (T1). GEM has word spreading 'today', which is impossible from Plymouth. |
| S015 | Wed 12 Feb | Westminster | — | Hilary term ends; the lawyers drain away before Shrovetide. | Term rule (T2). | calendar | GEM 7 | OK. |
| S016 | Fri 14 Feb | The Rose, Bankside | Alleyn, the Admiral's Men | Valentine's Day. He slips across the river to watch Long Meg of Westminster. | Henslowe marks Long Meg '1' on 14 Feb (T1); 'probably new' (T3). Full moon computed. | screen, location | GPT 14 Feb; GEM 8 | Flag: GEM's £3 9s takings not rechecked. |
| S017 | Sun 16 Feb | St Helen's church | parishioners | Septuagesima: the parish turns toward Lent. | Septuagesima falls on 16 Feb, computed from Easter on 20 Apr (T1/T2). | calendar | GEM 9 | OK. |
| S018 | Thu 20 Feb | Westminster Hall (news) | Robert Southwell; Chief Justice Popham | Southwell tried for treason; he is reported to have said he was the age of Christ. | Trial 20 Feb (T1, Colthorpe). The remark comes from Catholic accounts (T2). | screen | CLA 8 | OK. |
| S019 | Fri 21 Feb | Bishopsgate (not Tyburn) | alone | Southwell hanged at Tyburn. A private voice note on faith, poets and the state. | Execution 21 Feb 1594/5 (T1). No evidence he went. A Southwell kinship (T3; the film Will invents one). | memo | GPT 21 Feb; GEM 10; CLA 9 | Care: he hears of it; nothing is witnessed (section 5). |

### March (1–24 March dated 1594 in documents; Lady Day, 25 March, starts 1595)

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S020 | Sat–Tue 1–4 Mar | Whitehall (news) | the Queen; Gray's Inn gentlemen | Shrovetide at court: tilts on 1, 2 and 4 March; the Gray's Inn masque of Proteus and the Rock Adamantine on Shrove Monday. Heard about, not seen. | Colthorpe 1595 (T1). | screen, meeting | CLA 11 | OK; anchor added from Colthorpe. |
| S021 | Sun 2 Mar | a London ordinary | friends | Shrove Sunday supper: the last meat before Lent. | Quinquagesima 2 Mar (computed); Lenten fasting law (T1). | meeting, body | GEM 11 | OK. |
| S022 | Tue 4 Mar | City streets | apprentices | Shrove Tuesday licence; he walks wide of trouble. | Shrove Tuesday apprentice disorder as a custom (T2). No 1595 Shrove Tuesday riot is documented. | location, body | GEM 12; CLA 11 | Fixed: GEM tiers a 1595 'riot' T1. The custom is T2; a riot that day is invented. |
| S023 | Wed 5 Mar | Bankside | Henslowe | Ash Wednesday, yet the Rose opens a new play, Seleo and Olympo, and Henslowe still writes '1594'. | Henslowe (T1, Nicol's transcription). | screen, calendar | CLA 12; GEM 13 | Fixed: GEM has Lent closures starting on Ash Wednesday. The Rose played on to 14 Mar. |
| S024 | Lent (5 Mar–19 Apr) | his desk | alone | Drafting Romeo with Brooke's Romeus and Juliet open beside him; candlelit notes on two feuding houses. Good Friday is a quiet hour for it. | Romeo c.1595 (T2). Brooke (1562) as the source (T1/T2). The day-level drafting (T5). | notes | GPT late Feb; CLA 16; GEM 19 | OK. |
| S025 | early Mar | the Cross Keys or the Theatre | Kemp, Burbage | Kemp grumbles at a rewritten clown bit; Burbage tries a king's speech. | Both are company men (T1/T2). Dialogue (T5). | meeting | GPT early Mar | OK. |
| S026 | Fri 14 Mar | Bankside | Henslowe's carpenters | The Rose shuts for Lent (The Siege of London, 14s); repairs begin, £105 19s laid out 'in lent'. | Henslowe (T1). | screen | GPT 14 Mar; CLA 13; GEM 13 | Flag: GEM's itemised timber and painter costs not rechecked. |
| S027 | Sat 15 Mar | Whitehall; then the company | Kemp, Burbage | The Council warrant for the £20. A sharers' meeting about splitting it, and the costume debt. | Warrant 'dated at Whitehall xv[to] Marcij 1594' (=1595), E 351/542 (T1). Who collected it and how it was shared (T5). | meeting, notes | GPT 15 Mar, mid-Mar; GEM 14; CLA 14 | Fixed: GEM tiers the date T2; it is the warrant's own date (T1). The actual pay-day is unknown. |
| S028 | Tue 25 Mar | his lodging | the landlord | Lady Day: quarter rent paid; the legal year turns 1595 in his account book. | Lady Day as quarter-day and legal New Year (T1). | notes, calendar | GPT 25 Mar; GEM 15; CLA 15 | Fixed: GEM adds 'gentry ambitions' from the 1596 arms grant; that is T5 for 1595. |
| S029 | Sun 30 Mar | Bishopsgate | Anne | Mid-Lent Sunday: he writes home to Anne before Easter. | Mid-Lent Sunday 30 Mar (T1, Colthorpe). New moon computed. The letter (T5). | notes | GEM 16 | OK. |
| S030 | Lent | the Oxford road | innkeepers | The ride home: about 100 miles by Oxford, two to three days, with inn stops. | Aubrey: he went to Warwickshire once a year (T4). The Oxford route (T4). Lent timing (T5). | location, body, photo | CLA 17 | Flag: no record places any 1595 visit. The Davenants' Crown Tavern tradition starts c.1600–04, so leave it out of 1595. |

### April

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S031 | Lent | Henley Street, Stratford | John Shakespeare (about 65) | Talk with his father about old debts and the coat of arms he once sought. | John's debts and his 1592 recusancy listing (T1). The 1596 arms draft refers back to an earlier application (T1/T3). This conversation (T5). | meeting | CLA 18 | Flag: arms talk in 1595 is invented; the grant was drafted in Oct 1596. |
| S032 | Lent or spring | Stratford: Chapel St, High St | Anne, Susanna, Judith, Hamnet | Family days. He walks past the rebuilding after the fire of May 1594. | Fire c.13 May 1594 (T1 Shrewsbury annal; redated by Bearman 2000, T3 against the old Sept date). Family in Stratford (T1). | photo, location, meeting | CLA 19; GEM 21 | OK. |
| S033 | early Apr | the Theatre | fellow players | Late-Lent rehearsals from parts and a backstage plot; he rewrites a cue overnight. | Parts and plots survive at Dulwich (T1 as objects). The process (T2). | meeting, notes | GPT early Apr; GEM 17 | OK. |
| S034 | Sun 13 Apr | St Helen's church | neighbours | Palm Sunday in raw spring weather. | Date (T1/T2). Weather (T5). | calendar | GEM 18 | Flag: no 1595 weather record. |
| S035 | Sun 20 Apr | St Helen's church | the parish | Easter communion beside Sir Thomas Gresham's tomb; an Easter table of beef and bread. | Easter 20 Apr (computed). Every parishioner was expected to take Easter communion (T2). Gresham's tomb in St Helen's (T1). His being there (T3). Prices (T2 ranges). | calendar, location, photo | GPT 20 Apr; GEM 20; CLA 20 | Flag: GEM's beef at 1d/lb looks low for a dearth year; take prices from the compendium. |
| S036 | Mon 21 Apr | The Rose | the Admiral's Men | Easter Monday: the rivals reopen with The French Doctor (53s). | Henslowe: 'easter mondaye 1595' (T1). | screen | GPT 21 Apr; CLA 21 | OK. Settles CLA's 21 vs 22 Apr query: Henslowe writes 'easter mondaye', and Easter Monday was 21 Apr. |
| S037 | Tue–Wed 22–30 Apr | The Rose | — | The post-Easter run as his watch history: A Knack (22), The Grecian Comedy (23, 51s), The Wise Man of West Chester (24, 58s; 25, £3), Godfrey of Boulogne (26), Warlamchester (28), Long Meg (29), Doctor Faustus (30). | Henslowe (T1), as dated by Nicol. | screen | GPT 24 Apr, 25 Apr, 26 Apr, 27 Apr, 29 Apr, 30 Apr | Fixed: GPT follows Henslowe's own day labels, which run one day ahead here; 27 Apr was a Sunday. |
| S038 | Wed 23 Apr | his lodging; Whitehall news | — | St George's Day and the Garter feast at Whitehall; his birthday by tradition. He is 31. | Garter ceremonies 22–24 Apr (T1, Colthorpe). Birth on 23 Apr (T4 tradition); baptism 26 Apr 1564 (T1). | memo, calendar | GPT 23 Apr, 26 Apr; CLA 22 | Fixed: GPT says he turns 31 'three days later based on baptism'. That is backwards: tradition puts the birth three days before the baptism. |
| S039 | Wed 30 Apr | Shoreditch | fellow players | A joke going round: Henslowe has dated a page 'the 31 of aprell'. | Henslowe's own label 'ye 31 of aprell 1595' (T1). That the Chamberlain's men saw his book (T5). | meeting | GEM 22 | OK: a true slip. |

### May

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S040 | Thu 1 May | Bankside | the crowd | May Day: maypoles in the morning, then Long Meg packs the Rose (50s). | May Day customs (T2). Henslowe (T1). | photo, screen | GPT 1 May; CLA 23 | OK. |
| S041 | Fri–Sat 2–31 May | The Rose | — | May's rival run: Seleo and Olympo, The French Doctor, A Knack, The Venetian Comedy (8th; a Venice play before Merchant), The French Comedy, Long Meg, Tasso's Melancholy, The Grecian Comedy, Godfrey, both Tamburlaines, and the new 2 Hercules on 23 May. | Henslowe (T1), as dated by Nicol. | screen | GPT 2 May, 3 May, 8 May, 10 May, 13 May, 14 May, 15 May, 16 May, 17 May | OK. GPT's 3 May '11s' not rechecked. |
| S042 | Mon 5 May | Shoreditch | — | Learning lines on a morning walk; that afternoon he hears A Knack is on at the Rose. | Process (T2). Henslowe (T1). | body, memo | GPT 5 May | OK. |
| S043 | Wed 7 May | The Rose | Alleyn | New at the Rose: The First Part of Hercules. Envy of the spectacle. | Henslowe marks it 'ne', 7 May (T1). | screen, meeting | GPT 7 May; CLA 24 | Fixed: GPT gives £4 4s; Nicol reads £3 13s. Use £3 13s until Greg or Foakes is checked. |
| S044 | Wed 7 May | Westminster; the playhouses | lawyers | Easter term opens (7 May to 2 June): Inns men back in the audience. | Term rule (T2). | calendar | GEM 23 | OK. |
| S045 | Tue 13 May | London, with Stratford news | Anne, John | A year since the Stratford fire of 1594. | Fire c.13 May 1594 (T1 annal; T3 date). Full moon computed. | memo, notes | GEM 24 | OK. |
| S046 | May | Blackfriars | Richard Field | He calls at Field's shop as the new North's Plutarch comes off the press. | Field printed the 1595 Plutarch (T1, imprint). Field and he were both Stratford-born and Field printed Venus and Lucrece (T1), so the friendship is T2. The visit (T5). | screen, photo, location | CLA 25 | Flag: the month of printing not checked. |
| S047 | spring–summer | St Paul's Churchyard | booksellers | He browses the stalls and buys Southwell's posthumous Saint Peters Complaint, with its epistle to a 'loving Cosen'. | 1595 edition printed by Windet for John Wolfe (T1, Folger catalogue). The unnamed cousin as Shakespeare (T3 at most). | screen, notes | CLA 10; GPT late May | Fixed: CLA dates the purchase Feb–Mar; the edition's month is unverified, so place it spring or later. |
| S048 | Sun–Tue 25–27 May | London (Irish news) | — | Clontibret: O'Neill's men maul Bagenal's relief column in Monaghan. The news reaches London in June. | Battle 25–27 May 1595 (T1/T2). Casualty figures disputed. | screen, meeting | GEM 25; GPT late Mar | Fixed: GPT dates Clontibret to 25–27 March; it was May. |
| S049 | Mon 26 May | letter home | Susanna | Susanna turns twelve. | Baptism 26 May 1583 (T1). | notes, calendar | CLA 26 | OK. |
| S050 | Thu 29 May | Bishopsgate | — | Ascension Day and the new moon; he buys cheese and notes a cold spring. | Ascension 29 May (computed). Prices (T2). Weather (T5). | notes | GEM 26 | Flag: the cold spring is invented. |

### June

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S051 | Mon 2 Jun | Shoreditch | Heminges, Burbage | Easter term ends; the sharers map the summer between Whitsun and Midsummer. | Term (T2). Heminges as sharer (T2). | meeting, calendar | GEM 27 | OK. |
| S052 | Wed 4 Jun | The Rose | Henslowe | Henslowe pays £7 2s for 'makinge the throne in the hevens'. The rivals can now lower a god onto the stage. | Henslowe (T1). | meeting, screen | CLA 27 | OK. |
| S053 | early Jun | London markets | — | Food prices bite; apprentices grow resentful. | Dearth of 1594–97 (T1/T2). | location, notes | GPT early Jun | OK. |
| S054 | Fri 6 Jun | Bedlam (news) | apprentices | Apprentices free a silkweaver held in Bedlam. | Manning; Past Tense (T1/T2). | meeting | GPT 6 Jun; CLA 28 | OK. |
| S055 | Sun 8 Jun | St Helen's church | — | Whitsunday. | Whitsunday 8 June (computed). | calendar | GEM 28 | Fixed: GEM adds 'floodwaters rise'. No flood is recorded in June 1595; the wet summer was 1594. |
| S056 | Mon 9 Jun | The Rose | — | Whitsun Monday holiday crowds: A Knack takes 55s. | Henslowe (T1). | screen, calendar | GEM 29 | OK. |
| S057 | Tue–Thu 10–26 Jun | The Rose | — | June's rival run: The Seven Days of the Week (new 3 June, £3 10s; the hit of the month), The Wise Man (11th, 47s), both Hercules (12th, 13th), Warlamchester, The French Comedy, Long Meg (19th), Vallia and Antony (20th), Caesar and Pompey (25th). | Henslowe (T1), checked against Nicol. | screen | GEM 30, 33, 35, 37, 38 | OK: GEM's June figures match Nicol. |
| S058 | Thu 12 Jun | Billingsgate | fishwives, apprentices | Trouble over fish prices. | GPT tiers T1/T2; Claude omits it; not rechecked. | meeting | GPT 12 Jun; GEM 31 | Flag: hold at T2 until checked against Manning or Stow. |
| S059 | Fri 13 Jun | Southwark market | apprentices, market women | The butter riot: apprentices take 500 lb of butter and sell it at 3d a pound, not the sellers' 5d. Across the river 2 Hercules takes £3 2s. | Stow, quoted by Past Tense (T1). Henslowe (T1). | memo, photo | GPT 13 Jun; GEM 32; CLA 29 | OK. |
| S060 | Sun 15 Jun | London | — | Trinity Sunday; the pulpits warn against disorder. | Date (T1/T2). Sermons (T5). | calendar | GPT 15 Jun; GEM 34 | OK. |
| S061 | Mon 16 Jun | near St Paul's | — | A larger crowd dispersed near Paul's amid talk of insurrection. | GPT tiers T1/T2; not rechecked. | location, memo | GPT 16 Jun | Flag: not rechecked. |
| S062 | Wed 18 Jun | The Rose | — | New: 2 Caesar (55s). Rome is box office. | Henslowe 'Ne' (T1). | screen, notes | CLA 30; GEM 40 | OK. |
| S063 | Thu 19 Jun | London | — | Corpus Christi: an old feast surviving only as memory. Long Meg at the Rose. | Date (T1); the feast's afterlife (T2). | calendar | GPT 19 Jun; GEM 36 | OK. |
| S064 | Fri 20 Jun | Westminster | — | Trinity term opens. | Term rule (T2). | calendar | GEM 37 | OK. |
| S065 | Mon–Tue 23–24 Jun | the City; the Thames | the marching watch, citizens | Midsummer Eve bonfires and the watch; on Midsummer Day he photographs the river. | Midsummer customs (T2). Weather (T5). | photo, location | GPT 24 Jun; GEM 39; CLA 31 | Fixed: GEM's 'summer storm', and GEM 38's storms 'inspiring' the Dream's flood speech. The drenched summer was 1594, and that link is T3. |
| S066 | Thu 26 Jun | The Rose | — | The rivals' last show before they stop for the summer (2 Caesar, 20s). | Henslowe (T1). | screen | CLA 32; GEM 41 | OK. |
| S067 | Fri 27 Jun | Southwark; the City | rioters; Lord Mayor Spencer | Butter rioters whipped and pilloried. The Mayor writes to Burghley about punishing the Weavers' pamphlet and the Southwark rioters. | Remembrancia II.98, 27 June 1595 (T1). Punishments (T1/T2). | screen, photo | GPT 27 Jun; GEM 41 | OK. |
| S068 | late Jun | the Theatre | sharers | Will the City now press to shut the playhouses? | Civic hostility in the Remembrancia, 1594–95 (T1). The meeting (T5). | meeting | GPT late Jun | OK. |
| S069 | Sun 29 Jun | Tower Hill; his door in Bishopsgate | about 1,000 apprentices | Riot at Tower Hill on a moonless night. He bars the door; his heart rate climbs. | Colthorpe: 'a crowd of 1000 rioted, with some Tower warders' (T1). New moon 27 June (computed). | body, memo, location | GEM 42; CLA 33 | OK. |

### July

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S070 | Fri 4 Jul | the City gates | Sir Thomas Wilford, provost marshal | Proclamation against unlawful assembly under martial law; patrols at the gates. | Proclamation 769, Greenwich, 4 July 1595 (T1, Colthorpe). | location, screen | CLA 34 | Fixed: CLA's secondary-source date is confirmed. |
| S071 | early Jul | the Thames | watermen | Heat, stink and river traffic. | General (T2). | photo, location | GPT early Jul | Flag: no weather asserted. |
| S072 | July | the Theatre | sharers | A 'meeting': tour, or wait out the summer? | No record of the company touring in 1595 (T3). The Admiral's Men did leave: the Rose was dark 27 June to 24 Aug (T1). | meeting | CLA 35; GEM 47 | OK. |
| S073 | Wed 9 Jul | Westminster | — | Trinity term ends; the long vacation begins. | Term rule (T2). | calendar | GEM 44 | Fixed: GEM's Admiral's tour 'to Maidstone and Bath' not verified; Nicol says only that they toured. |
| S074 | summer, probably July | letter from Stratford | Anne; neighbours | A letter or carrier brings word of a second fire in Stratford. | The 1595 fire happened by 16 Nov (T1). The old 21/22 Sept date is discredited; Bearman (2000) argues it was about July and much smaller than 1594's (T3). | notes, memo | GPT 21 Sep; GEM 52, 53; CLA 46 | Fixed: GPT dates it 21 Sept at T1. The date is T3, and July is likelier. |
| S075 | Tue 22 Jul | Guildhall (news) | — | The riot leaders are tried for treason. | Colthorpe (T1). | screen | GPT 22 Jul | OK. |
| S076 | Wed 23 Jul | Mount's Bay, Cornwall (news) | Amésquita's four galleys | Spaniards burn Mousehole, Paul, Newlyn and Penzance (23–25 July OS). The news reaches London days later. | Hannibal Vyvyan's letter of 23 July (T1). | screen, meeting | GPT 23 Jul; GEM 45; CLA 36 | OK. |
| S077 | Thu 24 Jul | Tower Hill (heard, not seen) | five apprentices | Five hanged, drawn and quartered; the pamphlet is hawked days later. He hears the bells and does not go. | The pamphlet's 'Thursday the 24 of July' (T1). | memo | GPT 24 Jul; GEM 46; CLA 37 | Care: see section 5. |
| S078 | late Jul | Paul's Walk; a tavern | newsmongers | Spaniards and quarterings in one breath; arguments about Spain and the Queen's government. | News (T1). The talk (T5). | meeting | GPT late Jul; CLA 38 | OK. |

### August

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S079 | Fri 1 Aug | London | — | Lammas: harvest worry in a dearth year. | Feast (T1). Dearth (T2). | calendar, notes | GPT 1 Aug | OK. |
| S080 | Aug | Stratford | family | Summer at home: harvest fears; the maltsters and the price of barley. | Stratford as a malting town (T1, Bearman). Poor 1595 harvest (T2). The visit (T4/T5). | location, body, meeting | CLA 39 | Flag: no record places a 1595 visit. |
| S081 | Sun 10 Aug | London | — | St Lawrence's day; work goes on under food prices. | Feast (T1). Context (T2). | calendar | GPT 10 Aug | OK (thin seed). |
| S082 | Sun 24 Aug | Smithfield | fairgoers | Bartholomew Fair: crowds, cloth, roast pig and pickpockets. | The fair at St Bartholomew's tide (T1/T2). | photo, location, body | GPT 24 Aug; CLA 41 | Note: 24 Aug 1595 was a Sunday; the fair ran across the feast. |
| S083 | Mon 25 Aug | The Rose | the Admiral's Men | The rivals are back after the summer (A Knack, 17s). | Henslowe (T1), per Nicol. | screen | GEM 48 | Fixed: CLA's 'c.25–27 Aug, unconfirmed' is 25 Aug. |
| S084 | Thu 28 Aug | Plymouth (news) | Drake, Hawkins | Drake and Hawkins sail on their last voyage with 27 ships and about 2,500 men. | 28 Aug OS (T1/T2). | screen | GPT 28–29 Aug; GEM 49; CLA 42 | OK. |
| S085 | Fri 29 Aug | The Rose | Alleyn | New: Longshanks (40s), a rival English history. | Henslowe 'ne' (T1). Its relation to Peele's Edward I (T3). | screen | CLA 43 | OK. |

### September

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S086 | Fri 5 Sep | The Rose | — | New: Crack Me This Nut. | Henslowe (T1; not rechecked). | screen | GEM 50 | OK. |
| S087 | early Sep | court news | Lord Burghley | Word that Burghley 'lies here very ill of the gout, and cannot stir hand nor foot, nor feed himself'. | Lady Wolley's letter from court, Sunday [31 Aug] 1595, in Colthorpe (T1). | meeting | ED | Added from Colthorpe to cover the illness gap. |
| S088 | Sat 13 Sep | the Theatre | sharers; Lord Mayor Spencer | The Mayor asks the Council to suppress plays on Bankside as a cause of crime. The company weighs Hunsdon's protection against the City. | Remembrancia II.103, 13 Sept 1595 (T1). The meeting (T5). | meeting | GPT early Sep, 13 Sep, mid-Sep | Fixed: the calendar entry names Bankside (and letters to the Surrey and Middlesex justices). GPT's 'the Theatre and Bankside' is the wording of the 1597 letter. |
| S089 | Sun–Mon 14–15 Sep | London (news) | Thomas Wilcox | Woburn burns; a pamphlet on it is rushed out. | Woburn fire 13 Sept 1595 and Wilcox's tract (T1 per GEM; not rechecked). | screen | GEM 51 | Flag: not rechecked. |
| S090 | Sun 21 Sep | court and City | Raleigh's men | Raleigh is back from Guiana. El Dorado tales spread among merchants into October. | News of his return at court, 21 Sept (T1, Colthorpe). | meeting, screen | CLA 40; GPT late Oct | Fixed: CLA has the tales in August; the news reached court on 21 Sept. |
| S091 | Tue 23 Sep | Southampton House, Holborn | the Earl of Southampton | Whyte reports that Southampton 'doth with too much familiarity court the fair Mistress Vernon'. A 'call' with the earl. | Rowland Whyte to Sir Robert Sidney, 23 Sept 1595 (T1). Any contact between him and Southampton in 1595 (T3); the dedications of 1593–94 are T1. | call | CLA 44 | OK, but keep the relationship at T3. |
| S092 | Mon 29 Sep | the City | — | Michaelmas quarter day: rents, accounts, new sheriffs. Also the Golden Pen, a public contest between writing-masters. | Quarter-day (T1). The Golden Pen contest, 29 Sept 1595 (T1, Colthorpe). | notes, calendar | GPT late Sep, 29 Sep; GEM 54; CLA 47; ED | OK; the Golden Pen added from Colthorpe. |
| S093 | autumn | the Theatre | Burbage | Rehearsing Richard II: majesty sliding into frailty. | Richard II c.1595 (T2). Burbage as Richard (T3). | meeting | CLA 45; GPT Oct (Burbage) | OK. |

### October

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S094 | Oct | his lodging | alone | Drafting the deposition; the day is invented. | Richard II c.1595 (T2). The deposition scene was first printed in 1608 (T1); whether it was played in 1595 is T3. | notes | GPT Oct (draft) | OK. |
| S095 | Thu 2 Oct | The Rose | — | New: The Disguises (43s). | Henslowe (T1). | screen | CLA 48 | OK. |
| S096 | Thu 9 Oct | Westminster | — | Michaelmas term opens (9 Oct to 28 Nov); Inns of Court audiences return. | Term rule (T2). | calendar | GEM 55; CLA 49 | Fixed: dropped GEM's Magna Carta case. |
| S097 | Wed 15 or Sun 19 Oct | the Tower (news) | Philip Howard, former Earl of Arundel | The Catholic former earl dies a prisoner in the Tower. | Death in the Tower, Oct 1595 (T1). | memo | CLA 51 | Flag: Colthorpe gives 15 Oct; Claude and others give 19 Oct. Check before use. |
| S098 | Fri 17 Oct | the Savoy (news) | Sir Thomas Heneage | Heneage, the Treasurer of the Chamber who paid March's £20, dies. Who pays at Christmas now? | Death 17 Oct 1595 at the Savoy (T1, Colthorpe). | call, meeting | CLA 50 | OK. |
| S099 | Sat 18 Oct | London | — | St Luke's day; candles earlier, longer sleep. | Feast (T1). Seasonal (T2). | body, calendar | GPT 18 Oct | OK. |
| S100 | mid to late Oct | his desk in Bishopsgate | alone | Drafting the Dream: Titania's speech on the ruined seasons. | Dream 1595–96 (T2). The speech's link to the wet summer of 1594 (T3). | notes | GEM 56 | Fixed: GEM says the 'flooded summer' of 1595; it was 1594. |
| S101 | Wed 29 Oct | Cheapside and the river | Sir Stephen Slany | The Lord Mayor's show: Slany in, Spencer out. | Slany mayor 1595–96 (T1). Show on 29 Oct (T2). | photo, location | CLA 52 | OK. |

### November

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S102 | Sat–Sun 1–2 Nov | his parish | — | All Saints and All Souls: old prayers for the dead set against reformed doctrine. | Dates (T1). Context (T2). | memo, calendar | GPT 1 Nov, 2 Nov | Care: keep it general; no child's death (section 5). |
| S103 | Mon 3 Nov | Richmond (court news) | Essex; the Queen | The Queen confronts Essex over the Conference about the Next Succession, dedicated to him; he keeps to his chamber. | Whyte's letter, in Colthorpe (T1). | screen, meeting | CLA 53 | OK. |
| S104 | Fri 7 Nov | the Theatre | Lord Hunsdon, the patron | A 'call' with the patron about the court season. | Hunsdon as patron (T1). Direct contact (T5). Full moon computed. | call | GEM 57 | OK. |
| S105 | Tue 11 Nov | London | — | Martinmas: winter provisioning. | Feast (T1). Texture (T2). | calendar, notes | GPT 11 Nov | OK. |
| S106 | Mon 17 Nov | Whitehall tiltyard; Paul's Cross | the Queen, Essex | Accession Day: the tilt (10 pairs), Essex's device, bells, guns and bonfires; Peele's verse. Five days later Whyte writes that Essex's device 'is much commended'. | Colthorpe; Whyte, 22 Nov (T1). | photo, location, screen | GPT 17 Nov; CLA 54, 55 | Fixed: one article says Greenwich; the court moved to Whitehall on 14 Nov. GPT's 'Southampton appears in Peele' not rechecked. |
| S107 | late Nov to mid-Dec | the company room | sharers | Choosing plays for court; polishing a court comedy, perhaps Love's Labour's Lost; costumes aired, parts recopied, debts settled. | Practice (T2). Which play (T3). | meeting, notes | GPT late Nov, early Dec, mid-Dec; CLA 59 | OK. |
| S108 | Fri 28 Nov | The Rose | — | The rivals' new Harry V. | Henslowe (T1). | screen | CLA 56 | OK. |
| S109 | Fri 28 Nov | Westminster | — | Michaelmas term ends. | Term rule (T2). | calendar | GEM 59 | Fixed: GEM's 'winter City-inn playing season deepens' has no 1595 record. |
| S110 | Sun 30 Nov | St Helen's church | — | Advent Sunday falls on St Andrew's Day. | Computed (T1/T2). | calendar | GPT 30 Nov; GEM 60 | OK. |

### December

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S111 | Mon 1 Dec | Stationers' Hall | Cuthbert Burby | Edward III is entered: a play he may have had a hand in. | Entry 1 Dec 1595 (T1). His share (T3). | screen, notes | CLA 57 | OK. |
| S112 | Sun–Tue 7–9 Dec | Canon Row, Westminster | Sir Edward Hoby, Sir Robert Cecil | Hoby's letter of Sunday 7 Dec invites Cecil to supper on Tuesday, where 'K. Richard present him selfe to your vewe'. A candlelit private show, and a cold walk home. | Letter (T1, Cecil Papers, Hatfield). Which Richard, which company, and whether a play was given (T3; contested, see EMLS). | location, meeting, body | GEM 61, 62; CLA 58 | OK. |
| S113 | Sun 21 Dec | London | — | St Thomas's Day: the shortest days, and doles to the poor. | Feast (T1). Texture (T2). | calendar | GPT 21 Dec | OK. |
| S114 | Thu 25 Dec | London | — | Christmas Day; the court has been at Richmond since 23 Dec. | Colthorpe (T1). | calendar | GPT 25 Dec | OK. |
| S115 | Fri–Sun 26–28 Dec | Richmond Palace | the Queen; the company | The company plays at court on St Stephen's, St John's and Innocents' days. A gold button set with five pearls is lost from the Queen's kirtle 'at a play at Richmond at Christmas 1595'. A year on from Greenwich. | Colthorpe 1595: Chamberlain's Men's plays on 26, 27 and 28 Dec (T1). Heminges and Bryan paid for five plays, Dec 1595 to Feb 1596 (T1). His presence (T2). The button (T1, Arnold). | location, meeting, photo, body | CLA 60; GPT 26 Dec, 28 Dec | Fixed: GPT treats 26 and 28 Dec only as anniversaries; there were real court plays. CLA's 'Richmond?' is confirmed. |
| S116 | Wed 31 Dec | his lodging | alone | Year-end accounts: theatre, poems, family, dearth, unease, plays unfinished. | Context (T2). Introspection (T5). | notes | GPT 31 Dec | OK. |

### Any day

| id | date | place | who | what happens | true anchor and tier | journal source | reports | check |
|---|---|---|---|---|---|---|---|---|
| S117 | any day | the Theatre | the gatherers | Counting pennies from the gatherers' boxes. | Practice (T2). | notes, meeting | CLA 61 | OK. |
| S118 | any evening | his lodging | alone | Sonnet drafts for 'private friends'. | Meres, 1598: 'sugred Sonnets among his private friends' (T1). Composition in 1595 (T3). | notes | CLA 62 | OK. |
## 2. Anchor check: what was wrong, and the fix

Where the reports disagreed, or one over-tiered, the anchor was checked against a primary record or a standard calendar of one. Agreement between reports was not taken as proof. Weekdays: every weekday the reports give for a seed date matches the computation; no weekday errors were found.

| seed | report said | the record says | verdict | checked against |
|---|---|---|---|---|
| S115 | GPT: 26 and 28 Dec 1595 are only anniversaries of 1594; CLA: court "Richmond?", to verify | Court at Richmond from 23 Dec. The Chamberlain's Men played on 26, 27 and 28 Dec 1595 (and on 6 Jan and 22 Feb 1596); Heminges and Bryan were paid for five plays. A pearl button was lost from the Queen's kirtle "at a play at Richmond at Christmas 1595". | **Fixed**: a documented court season (T1 for the company; his presence T2) | [Colthorpe, Elizabethan Court Day by Day, 1595](https://folgerpedia.folger.edu/images/a/ab/ECDbD_1595.pdf) · [1596](https://folgerpedia.folger.edu/mediawiki/media/images_pedia_folgerpedia_mw/c/c4/ECDbD_1596.pdf) |
| S074 | GPT: second Stratford fire 21 Sept 1595, T1; GEM: 21 Sept, disputed | Bearman (2000): the 21/22 Sept dates go back to Bayly's moralising of 1612–13 and are unreliable. The 1595 fire had happened by 16 Nov; the collection brief was authorised 24 Nov; the usual lag points to about July. It was much smaller than 1594's. | **Fixed**: fire T1, date T3, "summer, probably July" | [Bearman, "Stratford's Fires of 1594 and 1595 Revisited", Midland History 25 (2000)](https://www.stratfordsociety.co.uk/files/Stratford_Fires_of_1594_and_1595.pdf) |
| S032, S045 | Traditional date of the first fire, 22 Sept 1594 | A Shrewsbury annal dates it 13 May 1594 ("above 100 houses and barns"). | OK as GEM and CLA have it; T1 annal, T3 against the old date | Bearman (2000), above |
| S048 | GPT: Clontibret, 25–27 March | 25–27 May 1595, a two-day running fight in Co. Monaghan. | **Fixed**: moved to May | [Battle of Clontibret](https://en.wikipedia.org/wiki/Battle_of_Clontibret) (a March date appears only in stale mirrors) |
| S037 | GPT: Knack 23 Apr, Grecian Comedy 24, Wise Man 25 and 26, Godfrey 27 Apr… | Henslowe's own day labels run one day ahead from 22 to 30 April (he ends at "ye 31 of aprell"). 27 April was a Sunday. The true days are Knack 22, Grecian Comedy 23, Wise Man 24 and 25, Godfrey 26, Warlamchester 28, Long Meg 29, Faustus 30. | **Fixed**: redated | [Nicol, Henslowe's Diary as a blog, April 1595](https://hensloweasablog.blogspot.com/2019/04/) |
| S039 | GEM: Henslowe wrote "31 April" | True: his label is "ye 31 of aprell 1595". | OK (T1) | Nicol, April 1595, above |
| dropped | GPT 18 May: Galfrido and Bernardo at the Rose, T1 | The 18 May entry is a John Payne Collier forgery, not a performance. | **Dropped** | [Nicol, May 1595](https://hensloweasablog.blogspot.com/2019/05/) |
| S043 | GPT: 1 Hercules took £4 4s on 7 May | Nicol reads £3 13s, marked "ne". | **Fixed** to £3 13s pending Greg or Foakes | Nicol, May 1595, above |
| S057, S062, S066 | GEM and CLA June Rose figures | All match: 2 Caesar "Ne" 18 June, 55s; last show 26 June; the Rose stopped from 27 June. | OK | [Nicol, June 1595](https://hensloweasablog.blogspot.com/2019/06/) |
| S083, S085 | CLA: Rose reopened "c.25–27 Aug, unconfirmed" | Reopened Monday 25 Aug (A Knack, 17s); Longshanks "ne" 29 Aug, 40s. | **Fixed**: 25 Aug | [Nicol, August 1595](https://hensloweasablog.blogspot.com/2019/08/) |
| S070 | CLA: martial law 4 July, from a secondary source; check the proclamation | Proclamation 769, Greenwich, 4 July 1595, "Prohibiting Unlawful Assembly under Martial Law". Riot leaders tried at Guildhall 22 July; five executed 24 July. | OK, now T1 | Colthorpe 1595, above |
| S088 | GPT: the Mayor's 13 Sept letter attacks plays "at the Theatre and Bankside" | Remembrancia II.103, 13 Sept 1595: asks the Council to write to the Surrey and Middlesex justices to suppress plays on the Bankside. The "Theatre, Curtain and Bankside" wording is the 28 July 1597 letter (II.171). | **Fixed** wording | [BHO, Index to Remembrancia: plays and players](https://www.british-history.ac.uk/node/51463) |
| S007, S010 | GPT puts the January rehearsal at the Theatre | Hunsdon to the Lord Mayor, 8 Oct 1594 (II.33): let the new company play at the Cross Keys in Gracechurch Street this winter. | **Fixed** venue (T1 request, T2/T3 that they played there) | BHO plays and players, above |
| S067 | GEM: Mayor's letter of 27 June | II.98, 27 June 1595: the Mayor to the Lord Treasurer on punishing the Weavers' pamphlet and the Southwark rioters. | OK (T1) | [BHO, Remembrancia pp. 448–458](https://www.british-history.ac.uk/no-series/index-remembrancia/1579-1664/pp448-458) |
| S090 | CLA: Raleigh's men telling El Dorado tales in August | News of his return reached court on 21 Sept 1595. | **Fixed**: September | Colthorpe 1595, above |
| S106 | CLA: Whitehall, but one article says Greenwich | The court moved to Whitehall on 14 Nov; Accession Day tilt at Whitehall, 10 pairs. | OK: Whitehall | Colthorpe 1595, above |
| S011 | CLA: 15 barges | Gesta Grayorum, quoted by Colthorpe: "He and his retinue took to them 15 barges". | OK (T1) | Colthorpe 1595, above |
| S097 | CLA: Arundel died 19 Oct | Colthorpe gives 15 Oct (buried in the Tower 22 Oct); other sources give 19 Oct. | **Flag**: check before use | Colthorpe 1595, above |
| S112 | GEM, CLA: Hoby's "K. Richard" supper | The letter of 7 Dec 1595 is T1. Which Richard (II, III or another), which company, and whether it was a play at all are argued; one study holds the letter cannot date Richard II. | OK at T1/T3 | [Early Modern Literary Studies 11.2, on Richard II and the Hoby letter](https://extra.shu.ac.uk/emls/11-2/fittric2.htm) |
| S047 | CLA: buys Saint Peters Complaint in Feb–Mar | The 1595 edition (Windet for John Wolfe) opens with an epistle to an unnamed "loving Cosen". Its month is not established. | **Fixed**: spring or later | [Folger catalogue record](https://catalog.folger.edu/record/167115) |
| dropped | GEM 43: Forman in Lambeth, a "sick maid" and a false plague mob, early July | Forman practised in the City (Stone House, St Botolph Billingsgate, 1594); Lambeth from 1597 at the earliest (usually 1601). His casebooks begin in 1596. No record of the mob was found, and 1595 was a low-plague year. | **Dropped** | [BHO, London physicians: Forman](https://www.british-history.ac.uk/no-series/london-physicians/1550-1640/forman-simon) · [Casebooks Project](https://casebooks.lib.cam.ac.uk/reading-the-casebooks/who-were-the-practitioners/simon-forman) |
| dropped | GEM 58: Hawkins dies 12 Nov, "news still weeks away" | Hawkins died off Puerto Rico; the fleet did not come home until spring 1596. No 1595 entry can know it. | **Dropped** for 1595 | Claude report, Key Findings (Hawkins 12 Nov 1595, Drake 28 Jan 1595/6) |
| S001, S027 | All three: court plays 26 and 28 Dec 1594, warrant 15 Mar 1594/5 | Claude quotes E 351/542 via Shakespeare Documented ("vpon St Stephens daye & Innocentes daye"). The Folger page was not re-opened in this pass; the warrant itself is confirmed. | OK (T1); GEM's "T2" for the date is raised to T1 | [Internet Shakespeare Editions chronology, 1595–96](https://internetshakespeare.uvic.ca/Library/SLT/reference/chronology/years1595-1596.html) · Claude report, Key Findings |
| S038 | GPT: he turns 31 "approximately three days later based on baptism" | Baptism 26 Apr 1564 (T1); the traditional birthday, 23 Apr, is three days before it, not after. | **Fixed** | Logic from the T1 baptism date |
| S065, S100 | GEM: storms and a "flooded summer" in 1595 inspire the Dream | The notoriously wet summer was 1594 (Stow). 1595 had a poor harvest, but no daily weather record has been found. The Titania link is T3. | **Fixed** | Claude report, Key Findings ("Cold, wet summer of 1595": overstated) |
| S023 | GEM: Lent closures open on Ash Wednesday | The Rose opened a new play on Ash Wednesday and played to 14 March. | **Fixed** | Claude chronology (citing Nicol) |
| S022 | GEM: a Shrove Tuesday riot, T1 | Apprentice licence on Shrove Tuesday is a custom (T2). No 1595 Shrove Tuesday riot is documented. | **Fixed** tier | None found in the three reports or Colthorpe |
| S030 | CLA: the Oxford road with innkeepers | The Davenants' Crown Tavern tradition begins about 1600–04 (Claude's own gazetteer). | **Flag**: no Davenants in 1595 | Claude report, gazetteer |
| S004 and others | GEM: moon phases tiered T1 | They are computed. Recomputed here: all GEM times agree to minutes except 11 June full moon (22:06 UT, not 08:57). | **Fixed** tier | Computation in this pass |

## 3. Coverage

**How counted.** All 118 seeds. *Month*: the month the seed starts in; undated seasonal seeds count in the month they sort into (the three Lent seeds S030 to S032 sort to late March and early April; the two any-day seeds, S117 and S118, are counted apart). *Source*: "any" counts a seed once for every source it lists; "main" counts only the first-listed source, so the main column sums to 118.

| month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | any day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seeds | 10 | 9 | 11 | 9 | 11 | 19 | 9 | 7 | 8 | 8 | 9 | 6 | 2 |

| journal source | meeting | call | memo | calendar | notes | screen | photo | location | body |
|---|---|---|---|---|---|---|---|---|---|
| any | 35 | 3 | 13 | 31 | 24 | 37 | 15 | 21 | 12 |
| main | 24 | 3 | 8 | 19 | 14 | 30 | 9 | 8 | 3 |

**Thin spots.**

| thin spot | how thin | why | what would fill it |
|---|---|---|---|
| **Calls** | 3 seeds (S091 Southampton, S098 Heneage's death, S104 Hunsdon) | The reports think in meetings and news; only CLA 44 proposed a call | Hunsdon and his household, Field, a Stratford neighbour such as Richard Quiney; all T5 on T1/T2 relationships |
| **Body** | 12 seeds, 3 led by it | No record of his health at all (T1, absence) | Walking days (Bishopsgate to Shoreditch, about 2 km), the Stratford rides, performance-day heart rate, short winter sleep. Illness must be invented and mild |
| **Illness** | 2 seeds (S087 Burghley's gout, S103 Essex keeping his chamber), both other people | As above; 1595 was a low-plague year | An invented winter cold (carried by S006) and the dearth's toll; never plague, never the children |
| **Voice memos** | 13 seeds, 8 led by it | Easily added: any private reaction can be a memo | Reactions to Southwell, the riots, the executions, a line of verse on a walk |
| **December** | 6 seeds | The reports run out of rival-repertory days after November | The Richmond season (S115) and the Hoby night (S112) carry it |
| **August, September, October** | 7, 8 and 8 seeds | Rose dark until 25 Aug; news-heavy but personal-light | The summer trip home (S080), the Richard II and Dream drafting (S093, S094, S100) |
| **Family, love, travel** | 8, 6 and 3 seeds (by theme tag), mostly letters | No family document survives from 1595, and no journey is recorded | The two possible trips home (S030 to S032, S080) and letters on the children's true birthdays (S012, S049) |

Heavy spots: June (19 seeds: riots plus a full Rose month) and the screen source (37), because Henslowe gives a play for nearly every weekday. The rival run rows (S037, S041, S057) are a ready-made watch history; they don't need more seeds.

## 4. A light first cut: 33 seeds

Every month has at least one seed; every journal source appears at least three times. Counted from the table below (a seed counts once for every source it lists): meeting 12, call 3, memo 3, calendar 5, notes 8, screen 5, photo 11, location 13, body 8. Themes: work 14, news 9, money 8, love 4, friendship 4, weather 3, family 3, faith 3, travel 3, illness 1.

| id | date | seed | journal source | themes | why it is in |
|---|---|---|---|---|---|
| S001 | Wed 1 Jan | Opens the year's book: tallies the two Christmas shows at Greenwich (St Stephen's and Innocents' Day 1594)… | notes, calendar | work, money | The year opens on the one 1595 record that names him. |
| S006 | Wed 15 Jan | Full moon on a hard winter night; photographs the frosted street by Crosby Place | photo, body | weather | Weather and a night photo; carries an invented winter cold (body, illness). |
| S007 | mid-Jan | Morning rehearsal from cue scripts; afternoon play in cold daylight | meeting, body, location | work | The working day: rehearsal audio, steps across the City. |
| S009 | Sun 26 Jan | News of the Derby wedding at Greenwich with the Queen present | meeting, calendar | news, love, work | Love and court news, with the Dream question left open. |
| S011 | Sat 1 Feb | The Prince comes up the river with 15 barges, music, trumpets and guns, lands at Tower Hill and rides… | photo, location | news, friendship | The best documented spectacle of the winter, for a photo. |
| S012 | Sun 2 Feb | Candlemas: the twins turn ten | notes, calendar | family | Family on a true date, written lightly. |
| S019 | Fri 21 Feb | Southwell hanged at Tyburn | memo | faith, news | Faith under pressure, kept private, in a voice memo. |
| S024 | Lent (5 Mar–19 Apr) | Drafting Romeo with Brooke's Romeus and Juliet open beside him; candlelit notes on two feuding houses | notes | work, love | The signature work of the year, as drafts in the notes source. |
| S027 | Sat 15 Mar | The Council warrant for the £20 | meeting, notes | money, work | The only document naming him in 1595, as a meeting with the two men named beside him. |
| S030 | Lent | The ride home: about 100 miles by Oxford, two to three days, with inn stops | location, body, photo | travel | Travel across location, body and photo in one stretch. |
| S032 | Lent or spring | Family days | photo, location, meeting | family | Home: family audio and photos on a real fire-scarred street. |
| S035 | Sun 20 Apr | Easter communion beside Sir Thomas Gresham's tomb; an Easter table of beef and bread | calendar, location, photo | faith | Faith at its fullest: the Easter communion every parishioner was expected to take. |
| S036 | Mon 21 Apr | Easter Monday: the rivals reopen with The French Doctor (53s) | screen | work | The rival season restarts: the screen source comes back. |
| S046 | May | He calls at Field's shop as the new North's Plutarch comes off the press | screen, photo, location | work, friendship | Friendship with the Stratford printer; proof sheets on a screen. |
| S059 | Fri 13 Jun | The butter riot: apprentices take 500 lb of butter and sell it at 3d a pound, not the sellers' 5d | memo, photo | news, money | Dearth made concrete, with a price. |
| S065 | Mon–Tue 23–24 Jun | Midsummer Eve bonfires and the watch; on Midsummer Day he photographs the river | photo, location | weather, faith | Midsummer: light, fire and the river in one photo day. |
| S069 | Sun 29 Jun | Riot at Tower Hill on a moonless night | body, memo, location | news | The year's danger, felt in the body source. |
| S072 | July | A 'meeting': tour, or wait out the summer? | meeting | work, money, travel | The business decision of the summer, as a sharers' meeting. |
| S076 | Wed 23 Jul | Spaniards burn Mousehole, Paul, Newlyn and Penzance (23–25 July OS) | screen, meeting | news | The war comes ashore: Spanish troops burning English towns. |
| S080 | Aug | Summer at home: harvest fears; the maltsters and the price of barley | location, body, meeting | family, money, travel | The summer trip home: the long walk in body data, family in audio. |
| S082 | Sun 24 Aug | Bartholomew Fair: crowds, cloth, roast pig and pickpockets | photo, location, body | friendship | Sensory London for a photo and a crowded step count. |
| S088 | Sat 13 Sep | The Mayor asks the Council to suppress plays on Bankside as a cause of crime | meeting | work | The City's war on the playhouses reaches his company. |
| S091 | Tue 23 Sep | Whyte reports that Southampton 'doth with too much familiarity court the fair Mistress Vernon' | call | love, friendship | Love and the patron-friend; the call source. |
| S092 | Mon 29 Sep | Michaelmas quarter day: rents, accounts, new sheriffs | notes, calendar | money | Accounts at the quarter, plus a contest of pens for a writer. |
| S098 | Fri 17 Oct | Heneage, the Treasurer of the Chamber who paid March's £20, dies | call, meeting | money, news | The money thread: the man who paid them is gone. |
| S100 | mid to late Oct | Drafting the Dream: Titania's speech on the ruined seasons | notes | work, weather | The second great play of the year, in drafts; weather becomes verse. |
| S103 | Mon 3 Nov | The Queen confronts Essex over the Conference about the Next Succession, dedicated to him; he keeps to his… | screen, meeting | news, illness | Illness and politics at court: Essex takes to his chamber. |
| S104 | Fri 7 Nov | A 'call' with the patron about the court season | call | work | The patron call the brief asks for. |
| S106 | Mon 17 Nov | Accession Day: the tilt (10 pairs), Essex's device, bells, guns and bonfires; Peele's verse | photo, location, screen | news | The court's great public day: crowd, noise, photos. |
| S112 | Sun–Tue 7–9 Dec | Hoby's letter of Sunday 7 Dec invites Cecil to supper on Tuesday, where 'K. Richard present him selfe to… | location, meeting, body | work | A private performance on a true night: place, audio, the walk home. |
| S115 | Fri–Sun 26–28 Dec | The company plays at court on St Stephen's, St John's and Innocents' days | location, meeting, photo, body | work | The year ends where it began, at court, this time on a documented date. |
| S116 | Wed 31 Dec | Year-end accounts: theatre, poems, family, dearth, unease, plays unfinished | notes | money, work | The closing summary of the year in his own notes. |
| S118 | any evening | Sonnet drafts for 'private friends' | notes | love | Love in the notes source, kept at T3. |

## 5. Seeds to avoid or handle with care

| seed(s) | the risk | how to handle it |
|---|---|---|
| S012, S049, S032, S080, S102 | **Grief.** Hamnet dies in August 1596. A birthday, a family visit or All Souls can read as foreshadowing. | Write the children as ordinary and well. No illness, no "last" anything, no premonition, no dwelling on child mortality on All Souls. Don't borrow from O'Farrell's *Hamnet* (T5 fiction). Hamnet is one of three children, not a focus. |
| S019, S018, S077, S067 | **Executions and punishment.** Southwell at Tyburn; five apprentices hanged, drawn and quartered on Tower Hill; whippings. | He hears of them; he is never there, and no seed says he was. Keep to T1 facts and his private reaction. No gore. The Southwell kinship is T3 at best (the film *Will* invents it). |
| S069, S022, S058, S061 | **Riots.** Easy to place him in a crowd. | He stays home or walks wide. The riot facts are T1; his part is invented. |
| S016, S035, S030 to S032, S080, S115, S112, S091 | **Putting him somewhere.** No document places him anywhere on any day of 1595 except as a payee on 15 March. | Present-tense invention is fine, but keep the anchor tier honest: the trips home are T4/T5, the court nights T2, the Hoby night T3, any 1595 contact with Southampton T3. |
| S009, S024, S093, S094, S100, S111 | **Over-claiming the works.** Play dates are T2 and their order T3; the Dream's wedding occasion, Burbage as Richard, the 1595 deposition scene and Edward III are T3. | Draft notes can be dated invented days; never present a composition date as a record. Quote only the public-domain quarto text. |
| S031, S028 | **The coat of arms.** The grant is drafted in October 1596. | 1595 talk of arms is invention on a later T1 record. Keep it a wish, not a filing. |
| S006, S034, S050, S065, S071, S100 | **Weather.** No daily London weather record for 1595 survives; the famous wet summer was 1594. | Invent mild, local weather. Never "the floods of 1595". |
| dropped: GPT 18 May | **A forged record.** Galfrido and Bernardo is a Collier forgery. | Never use it. |
| dropped: GEM 43 | **Forman.** Wrong place for 1595, no record of the scene, and it brings plague into a low-plague year. | Leave Forman out of 1595. |
| dropped: GEM 58 | **Hawkins's death.** The news can't reach London until spring 1596. | Not in a 1595 journal. |
| S035, S050 and any price | **Prices.** GEM's specific prices (beef 1d a pound, cheese 1½d) are unverified and look low for a dearth year. | Take prices from the sourcebook's daily-life compendium as ranges. |
| S118, S091 | **Love and the sonnets.** The Fair Youth, the Dark Lady and the Rival Poet are T3. | Write the sonnets as drafts "among his private friends" with no named addressee. Keep Emilia Bassano and the rest out of 1595 as facts. |

## Sources used in this pass

- The three reports: chatgpt.md, gemini.md, claude.md.
- Marion Colthorpe, *The Elizabethan Court Day by Day*, [1595](https://folgerpedia.folger.edu/images/a/ab/ECDbD_1595.pdf) and [1596](https://folgerpedia.folger.edu/mediawiki/media/images_pedia_folgerpedia_mw/c/c4/ECDbD_1596.pdf) (Folgerpedia).
- David Nicol, *Henslowe's Diary as a blog*: [April](https://hensloweasablog.blogspot.com/2019/04/), [May](https://hensloweasablog.blogspot.com/2019/05/), [June](https://hensloweasablog.blogspot.com/2019/06/) and [August 1595](https://hensloweasablog.blogspot.com/2019/08/). This is a reconstruction; check against Greg (1904) or Foakes before publication.
- Robert Bearman, ["Stratford's Fires of 1594 and 1595 Revisited"](https://www.stratfordsociety.co.uk/files/Stratford_Fires_of_1594_and_1595.pdf), *Midland History* 25 (2000).
- British History Online, *Analytical Index to the Remembrancia*: [plays and players](https://www.british-history.ac.uk/node/51463); [pp. 448–458](https://www.british-history.ac.uk/no-series/index-remembrancia/1579-1664/pp448-458). [London physicians: Simon Forman](https://www.british-history.ac.uk/no-series/london-physicians/1550-1640/forman-simon).
- [Early Modern Literary Studies 11.2](https://extra.shu.ac.uk/emls/11-2/fittric2.htm) on the Hoby letter; [Folger catalogue, Saint Peters Complaint 1595](https://catalog.folger.edu/record/167115); [Battle of Clontibret](https://en.wikipedia.org/wiki/Battle_of_Clontibret) (popular source); [ISE chronology 1595–96](https://internetshakespeare.uvic.ca/Library/SLT/reference/chronology/years1595-1596.html).
- Weekdays, Easter and moon phases: computed in this pass (Julian day numbers; Julian Easter computus; Meeus mean phases with periodic terms).

*Not re-opened:* the Shakespeare Documented page for E 351/542 (the three reports agree and Claude quotes it), Henslowe's January, February and September 1595 entries, and GEM's Woburn and fish-riot anchors (flagged in place).