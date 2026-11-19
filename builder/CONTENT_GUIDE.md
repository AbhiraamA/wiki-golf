# Wiki Golf: content rules for starts and targets

This guide decides which Wikipedia articles may be used as a hole's **start** or **target**. It applies only to those two endpoints. Any article may appear mid-route, because players choose their own path.

The file is safe to keep in the public repo: it lists categories and rules, never upcoming holes.

## How to read this

| Tier | Start | Target | Meaning |
|---|---|---|---|
| **A: Never** | ✗ | ✗ | Distressing, offensive or risky to show as the day's headline. |
| **B: Not a target** | ✓ | ✗ | Fine to begin on and read, but not something to celebrate "reaching" or share. |
| **C: Bad endpoint** | ✗ | ✗ | Not offensive, just dull, meta or unaimable. |
| **D: Date-sensitive** | depends | depends | Fine most of the time, wrong at certain moments. |

When in doubt, leave it out. There are always plenty of good articles.

---

## Tier A: never a start or target

**Violence and death**
- Murderers, serial killers, mass shooters, terrorists and their attacks
- Massacres, genocides, the Holocaust and other atrocities, war crimes
- Terrorist and extremist organisations, hate groups
- Torture, executions, methods of execution
- Suicide, self-harm, and people best known for dying by suicide
- Notable deaths whose article is mainly about the death (assassinations, killings)

**Abuse and exploitation**
- Child abuse, sexual abuse, human trafficking, and people convicted of them
- Abusers whose fame comes mainly from the abuse

**Sexual content**
- Sex acts, pornography, porn performers, sexual fetishes, prostitution
- Sexual anatomy as a topic (general anatomy like "Heart" is fine)

**Hate and slurs**
- Slurs and derogatory terms, and articles about them
- Racism or bigotry presented as the subject (e.g. articles about racist ideologies)

**Drugs**
- Illegal and recreational drugs, drug trafficking, cartels
- Fine: everyday substances and medicines (Caffeine, Aspirin, Penicillin)

**Disasters and tragedy**
- Recent or high-casualty disasters, plane crashes, shipwrecks with mass loss of life
- Pandemics framed around deaths (the disease article "Influenza" is fine)

**Politics and conflict right now**
- Living politicians who are currently in office or running for office
- Ongoing wars and conflicts
- Divisive current controversies (abortion, gun control, immigration policy, etc.)
- Fine: historical figures and events that are settled history (Abraham Lincoln, Roman Empire, Napoleon)

**Conspiracy and misinformation**
- Conspiracy theories (Illuminati, flat Earth, moon-landing hoax)
- Pseudoscience framed as fact

**Real private harm**
- Living people known mainly for a scandal, crime or being a victim
- Living people who are not public figures

## Tier B: fine as a start, not as a target

Players land on the start and can read it, but the target is the day's headline and shows up in shares.

- Historical wars and battles (World War II, Battle of Hastings)
- Diseases and medical conditions
- Weapons and military equipment
- Historical dictators and controversial historical leaders
- Religious figures and texts (respectful, but a share like "I reached the Qur'an in 4" can read badly)
- Alcohol and tobacco brands
- Gambling

## Tier C: bad endpoints (dull or unaimable)

- Wikipedia and Wikimedia projects (Wikipedia, Wikiquote, Wiktionary, Wikidata, MediaWiki, etc.)
- Technical standards and codes (ISO 4217, ISO 8601, RFCs, Unicode blocks)
- Lists, outlines, indexes, glossaries, timelines ("List of…", "Outline of…", "Timeline of…")
- Year, decade, century and date pages ("1999", "1990s", "March 3")
- "X in Y" pages ("1999 in film", "Sport in Brazil")
- "X at the Olympics/Paralympics" and other country-at-event pages
- Disambiguation pages and set indexes
- Stubs (very short articles)
- Tiny administrative units (communes, parishes, electorates, wards, villages)
- Individual albums, singles, songs and episodes (the artist or show itself is fine)
- Taxonomic ranks people don't know ("Cnidaria"); common animals are fine ("Jellyfish")
- Sports seasons, single matches and squads ("2014–15 Premier League")
- Articles whose title needs specialist knowledge to even read

## Tier D: date-sensitive

- **Recent deaths:** no person who died in the last 90 days.
- **Ongoing news:** nothing tied to a disaster, crisis or scandal currently in the news.
- **Elections:** no politicians or parties, ever, and be extra strict in the month before a major election.
- **Tragic anniversaries:** never schedule a related article on the anniversary of a tragedy (e.g. nothing about planes or New York on September 11).
- **Themed days:** the theme calendar can override the fame filter but **never** Tier A.

---

## How the builder should detect these

Apply checks in this order, cheapest first. A hit at any step excludes the article for the blocked role(s).

1. **Manual blocklist** (`builder/blocklist.txt`), with exact titles and the tier.
2. **Title patterns** (regex): lists, years, "X in Y", "at the Olympics", ISO codes, Wikimedia projects, "(album)", "(song)", "(episode)", "(disambiguation)".
3. **Wikidata properties** for the article's item:
   - `P31` (instance of): exclude album, single, song, episode, sports season, list, disambiguation, terrorist attack, massacre, mass shooting, conspiracy theory, recreational drug, administrative unit below county level, etc. The agent should look up the exact item IDs and keep them in config.
   - `P1399` (convicted of): any value on a person means Tier A.
   - `P106` (occupation): exclude serial killer, terrorist, pornographic actor, drug trafficker, etc.
   - `P570` (date of death): within the last 90 days means skip (Tier D).
   - `P39` (position held) / `P102` (party), when the person is living and currently in office or a candidate: Tier A.
4. **Short-description keywords** as a safety net: "murderer", "serial killer", "mass shooting", "terrorist", "massacre", "genocide", "pornographic", "conspiracy theory", "drug", "suicide", "sex offender", "cult leader".
5. **Final human or agent review** of the coming week's targets before approval, done locally and never in public logs.

## Ground rules

- Every exclusion lists its tier, so a Tier B article can still be a start.
- Log only counts in public CI ("12 targets excluded by P1399"), never titles.
- When a new dud slips through, add a **rule** that generalises (a pattern or Wikidata class), not just the one title.
- Review this file before the English Wikipedia launch and every few months after.
