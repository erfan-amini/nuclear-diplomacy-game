# Nuclear Diplomacy Simulation

A moderator console for the K=1 Project's Nuclear Diplomacy Simulation, built for a
Frontiers of Science seminar at Columbia. Five groups play China, India, Pakistan,
Russia and the United States. The instructor projects this page, enters the decision
slips, and the app runs the attack stage, updates every GPR and handles sanctions.

## Running a game

The standings (GPR and weapons for every country, the world total and the attack odds)
stay on the left the whole time. The main area follows the round:

1. **Decisions.** Collect all five slips. Click each country's move. Lock them in.
2. **Attack.** The page shows the world total, the odds of a nuclear terrorist attack,
   and each country's chance of being hit. Click *Run the attack draw*. You can also
   call or skip the attack yourself (the teacher guide allows this). A hit plays a
   short full-screen explosion with the country's name.
3. **Sanctions.** The three most powerful countries decide whether to sanction one or
   both of the two weakest. Tick the boxes, or click *No sanctions*.

Repeat for four rounds (or as many as you like), then end the game.

- **Settings** holds everything else: the section name, rounds planned, undo, end
  game, new game, the public rules, and three switches (the secret-rule breakdown,
  the suspense before the result, and the explosion).
- **The address bar holds the game.** A refresh, or the same link opened later,
  brings it back exactly.
- **History** has the round-by-round tables and charts, and a CSV download.
- **Debrief** shows where each country's points came from, the secret rules and how
  often each fired, and a replay that re-draws the attacks 5,000 times to show how
  much of the result was luck.

## Rules implemented

From the K=1 Project teacher guide, the general student instructions and the five
country sheets.

| | |
|---|---|
| Start | U.S. 10 weapons, GPR 1. China 3, GPR 2. Russia 5, GPR 3. India 1, GPR 5. Pakistan 1, GPR 6. |
| Moves | U.S. up to 3 up or down, Russia 2, the others 1. Nobody goes below 0. |
| GPR | Lower is more powerful. +1 per secret rule tripped, +4 for an attack, +2 for ignoring a sanction. Never goes down. |
| Attack odds | World total 0: none. 1-5: 1 in 32. 6-11: 1 in 16. 12-18: 1 in 8. 19-27: 1 in 4. 28+: 1 in 2. |
| Victim | One of the three lowest GPRs at the start of the round: 1 in 2, 1 in 3, 1 in 6. Tied countries share their slots equally (the same as re-rolling the die). |
| Sanctions | After the GPR update, the three lowest GPRs may sanction one or both of the two highest. A sanctioned country must cut by the most it can next round, or take +2. |
| House rule | **A country with 0 weapons cannot be sanctioned.** It can still be hit by an attack. |
| Ties at the sanction line | Broken at random. The page says so when it happens. |

The engine (`game.py`) reproduces the sample game in the teacher guide number for
number; see `tests/test_game.py`.

## What the rules do (notes for the debrief)

- **Holding still is free.** If nobody moves, no secret rule fires at the start. Every
  GPR change then comes from attacks.
- **Building is pushed onto others.** No country pays a rule point for its own build at
  the start; its rivals do. One Chinese build costs India, Russia and the U.S. a point
  each. A U.S. or Russian build costs the other and China.
- **The only defence against a rival's build is to build too.** The "X built and you
  did not" rules punish anyone who stays put. That is the arms race in one line.
- **India and Pakistan cannot disarm alone.** If India cuts alone, India and Russia
  pay a point. If Pakistan cuts alone, Pakistan and China pay. If they cut together,
  nobody pays.
- **Disarmament by the big two is cheap.** A U.S. cut of 3 costs nobody anything and
  halves the attack odds (20 to 17 weapons: 1 in 4 to 1 in 8). A Russian cut of 2 costs
  India a point, since Pakistan plus China then outnumber Russia.
- **Attacks only fall on the top three.** India and Pakistan carry no attack risk at
  the start, so the odds give them no reason to disarm. Only sanctions do, and with
  the house rule a country at 0 weapons is out of reach of sanctions too.
- **The starting order matters.** GPR never goes down, so the U.S. starts with a lead.
  In 20,000 simulated four-round games where everyone holds and obeys sanctions, the
  U.S. finishes first about two times in three. India and Pakistan almost never do,
  so "winning" is best judged against each country's own goals.

## Run it yourself

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
python -m pytest -q
```

## Credits

Game design, rules and country briefs: the K=1 Project, Columbia University
(k1project.columbia.edu). Flags from Wikimedia Commons (public domain).
