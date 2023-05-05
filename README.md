# Description

This is a discord bot made for the fantasy game over at https://fantasy.road.cc.

## Events
- New transfers of tracked players
- Warnings of upcoming deadline together with an image of the next stage
- Notification of when points have been distributed for the day

## Command examples
<details>
    <summary>?prider tdf22 > 500</summary>

```python
Tadej Pogacar: 722 (0)
Wout Van Aert: 712 (0)
Jonas Vingegaard: 512 (0)
```
</details>
<details>
    <summary>?prider vuelta22 roglic</summary>

```python
Primoz Roglic - Jumbo-Visma
Stage 1: 29
Stage 2: 7
Stage 3: 8
Stage 4: 52
Stage 5: 6
Stage 6: 29
Stage 7: 8
Stage 8: 24
Stage 9: 19
Stage 10: 41
Stage 11: 10
Stage 12: 13
Stage 13: 21
Stage 14: 38
Stage 15: 32
Stage 16: 12
Total: 349 (0)
```
</details>
<details> <summary>?vrider (todo since it's new with giro 2023)</summary>

Todo - Shows `total points / cost of rider`
</details>
<details>
    <summary>?pteam tdf22</summary>

```python
Jumbo-Visma: 1746
UAE-Team Emirates: 1036
INEOS Grenadiers: 977
Quick-Step Alpha Vinyl Team: 602
EF Education-EasyPost: 584
Trek - Segafredo: 552
Groupama - FDJ: 536
Bora - Hansgrohe: 518
Alpecin-Fenix: 492
Team BikeExchange Jayco: 473
Intermarché - Wanty - Gobert Matériaux: 421
Israel - Premier Tech: 400
Cofidis: 381
Team Arkéa Samsic: 364
Bahrain - Victorious: 362
Team TotalEnergies: 350
Movistar: 332
Lotto Soudal: 326
Team DSM: 308
B&B Hotels - KTM: 243
AG2R Citroën Team: 202
Astana Qazaqstan Team: 126
```
</details>
<details>
    <summary>?pteam tdf22 jumbo</summary>

```python
Jumbo-Visma
Wout Van Aert: 712
Jonas Vingegaard: 512
Christophe Laporte: 202
Primoz Roglic: 99
Sepp Kuss: 71
Tiesj Benoot: 58
Nathan Van Hooydonck: 47
Steven Kruijswijk: 45
```
</details>
<details>
    <summary>?pstage tdf22 1</summary>

```python
Yves Lampaert: 50
Wout Van Aert: 43
Tadej Pogacar: 41
Filippo Ganna: 31
Mathieu van der Poel: 27
Mads Pedersen: 23
Jonas Vingegaard: 20
Primoz Roglic: 17
Bauke Mollema: 14
Dylan Teuns: 12
Thomas Pidcock: 10
Frederic Frison: 10
Magnus Cort: 10
Bob Jungels: 9
Adam Yates: 8
Stefan Kung: 7
Mattia Cattaneo: 6
Kasper Asgreen: 5
Andrea Bagioli: 5
Jan Tratnik: 5
Mikkel Frolich Honore: 5
Florian Senechal: 5
Fabio Jakobsen: 5
Michael Morkov: 5
```
</details>
<details>
	<summary>?standard, ?rank</summary>

```python
STANDARD
Brintos - 123 - 1805
Uglen - 135 - 1784
Rammusser - 139 - 1756
Pemo - 135 - 1498
```
Todays points - total points
</details>
<details>
	<summary>?purist, ?rankp</summary>

```python
PURIST
Uglen - 68 - 534
Brintos - 44 - 362
Rammusser - 46 - 288
Pemo - 41 - 227
```
Todays points - total points
</details>
<details>
    <summary>?track 501492</summary>
```python
Added 501492 to players to track.
```
</details>
<details>
    <summary>?untrack 501492</summary>
```python
Removed 501492 from players to track.
```
</details>
<details>
    <summary>?transfers</summary>

Transfers for Brintos. 0 Remaining
```python
No transfers
```
Transfers for tony kappler. 0 remaining
```python
Miguel Angel  Lopez -> Mads Pedersen
Richard Carapaz -> Pascal Ackermann
Carlos Rodriguez -> Kaden Groves
Rigoberto Uran -> Danny van Poppel
```
</details>
<details>
    <summary>?transfers 669253</summary>

Transfers for 11waterloo. 4 remaining
```python
Carlos Rodriguez -> Alfred Wright
Jay Vine -> Rigoberto Uran
```
</details>

## Setup
This will be a losely written guide.



1. Create a `.env` file with the following settings filled out with your details


```
DISCORD_KEY=
DISCORD_CHANNEL_ID=
ROAD_USERNAME=
ROAD_PASSWORD=
ROAD_USERID=
```
2 run `pip install -r requirements.txt` to install python dependencies

3 run bot with `python pybot.py`


## Setting the bot up for a new competition
A lot of things could have been done prettier, but this was intended to be a simple bot for use between friends, as such things aren't streamlined.

1. Update the settings defined at the top of `pybot.py`
2. For new pictures of stages, do similar to what has been done in the `get_profile` function
3. For old competitions to be functional for commands do similar to what has been done in the `get_tournament` function
4. Outcomment `job.start` and `client.run` and run the `main` function to keep a list of riders, teams, value, age, etc. in a local file. Rename the generated file from `riders_new.json` to `rider_scores.json`, and make a copy of it called `template.json`. Don't override your old one if you want to keep it(!)
5. Maybe(?) reset `fantasy_status.json`. `Date` should be the date of the first stage, `found` should be false, `previousHigh` should be 0 and `deadline` should be the deadline of the transfer window.