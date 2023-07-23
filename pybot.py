import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import tasks
from discord.ext import commands
from datetime import datetime
import datetime as dt
import json
from thefuzz import fuzz
import re
import calendar
import os
import asyncio
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from HoldetDKService import HoldetDKService
from LeTourService import LeTourService

load_dotenv()
#####################################
# modified between each competition #
#####################################

params = {
    'ldtid': '6',
    'lid': '2142',
}
competition_name = "Tour de France"
puristId = 462
standardId = 461

restdays = [
    datetime(2023, 7, 10),
    datetime(2023, 7, 17),
]
startday = datetime(2023, 7, 1)
endday = datetime(2023, 7, 23)

holdet_tournament_id = 443
holdet_game_id = 663

##############################

total_stage_count = (endday - startday).days - len(restdays) + 1

intents = discord.Intents.default()
client = commands.Bot(command_prefix="?")

# endpoints
template = "template.json"
base_url = "https://fantasy.road.cc"
login_url = "https://fantasy.road.cc/login"
standard_url = "https://fantasy.road.cc/leagues"
stages_url = "https://fantasy.road.cc/stages"
context_url = "https://fantasy.road.cc/gotocomp"
user_url = "https://fantasy.road.cc/viewuser"
remaining_url = "https://fantasy.road.cc/common/ajax.php?action=transfersremaining"
deadline_url = "https://fantasy.road.cc/transfers"
available_riders_url = f"https://fantasy.road.cc/common/ajax.php?action=loadpicks&uid={os.getenv('ROAD_USERID')}&order=valuedesc&minval=3&maxval=40&page=NaN&bal=1.3&findphrase=&allriders=0"


comp_len = len(competition_name)

# local database
status_json = "fantasy_status.json"

# scores for current and old tournaments
rider_scores_json = "rider_scores.json"
giro23_rider_scores_json = "rider_scores_giro23.json"
tdf22_rider_scores_json = "rider_scores_tdf22.json"
vuelta22_rider_scores_json = "rider_scores_vuelta22.json"

login_data = {
    'user': os.getenv('ROAD_USERNAME'),
    'pass': os.getenv('ROAD_PASSWORD')
}
channelId = os.getenv('DISCORD_CHANNEL_ID')
discord_format = 'ml'
results_folder = 'results'

lts = LeTourService(os.getenv('LETOUR_TOKEN'), os.getenv('LETOUR_ACCESS_KEY'))

def get_profile(tour = None, stage = None):
    if(stage == None or stage < 1 or stage > 21):
        stage = get_current_stage()

    if tour == 'tdf22' or tour == 'tour22':
        return f"https://olympics.nbcsports.com/wp-content/uploads/sites/10/2022/06/stage{stage}.jpg"
    if tour == 'vuelta22' or tour == 'v22':
        return f"https://cdn.cyclingstage.com/images/vuelta-spain/2022/stage-{stage}-profile.jpg"
    if tour == 'giro23' or tour == 'g23':
        return f"https://www.alpecincycling.com/wp-content/uploads/2023/05/Giro-d-Italia-2023-{stage}-Etappe-Profil-1024x682.jpg"
    if tour == 'tdf23' or tour == 'tour23':
        return f'https://cdn.cyclingstage.com/images/tour-de-france/2023/stage-{stage}-profile.jpg'

    return f"https://cdn.cyclingstage.com/images/tour-de-france/2023/stage-{stage}-profile.jpg"

def get_tournament(str):
    lstr = str.lower()
    if lstr == "tdf22" or lstr == 'tour22':
        return ("tdf22", tdf22_rider_scores_json, True)

    if lstr == "vuelta22" or lstr == 'v22':
        return ("vuelta22", vuelta22_rider_scores_json, True)
    
    if lstr == "giro23" or lstr == 'g23':
        return ("giro23", giro23_rider_scores_json, True)

    return ("tdf23", rider_scores_json, False)

def player_points_url(uid, sid, cid): 
    return f"https://fantasy.road.cc/common/ajax.php?action=pointsoverlay&uid={uid}&sid={sid}&cid={cid}&ttid=undefined"

nl = '\n'

class FantasyRow():
    def __init__(self, rank, teamname, playername, daily_score, score, did_increase, increment):
        self.rank = rank
        self.teamname = teamname
        self.playername = playername
        self.daily_score = daily_score
        self.score = score
        self.did_increase = did_increase
        self.increment = increment
    
    def toString(self):
        icon = ""
        if self.did_increase:
            icon = ":chart_with_upwards_trend: "
            self.increment += " - "
        elif self.did_increase == False:
            icon = ":chart_with_downwards_trend: "
            self.increment += " - "
        return f"{icon}{self.increment}**{self.playername}** - _{self.daily_score}_ - **_{self.score}_**"

def set_fetched_status(status, newscore, deadline, warned):
    try:
        data = {
            "date": dt.date.today().strftime("%d%m%Y"),
            "found": status,
            "previoushigh": newscore,
            "deadline": deadline.strftime("%d%m%Y,%H:%M") if deadline != None else None,
            "warned": warned
        }
        with open(status_json, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file)
    except Exception as e:
        print("Error in set fetched status", e)      

def get_current_time():
    return datetime.utcnow() + dt.timedelta(hours=2)

def compare_string(a, b):
    t = a.lower()
    if t == "ef":
        a = "EF Education"
    elif t == "dsm":
        a = "Team DSM"
    elif t == "quickstep":
        a = "Quick-Step"
    elif t == "fdj":
        a = "Groupama - FDJ"
    elif t == "b&b":
        a = "B&B Hotels"
    elif t == "uae":
        a = "UAE-Team Emirates"
    elif t == "bora":
        a = "Bora - Hansgrohe"
    elif t == "Trek":
        a = "Trek - Segafredo"
    elif t == 'arkea':
        a = 'samsic'

    return fuzz.partial_ratio(a,b.lower())

def get_fetched_status():
    data = {}
    lastscore = None
    deadline = None
    try:
        with open(status_json, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        day = data["date"][0:2]
        month = data["date"][2:4]
        year = data["date"][4:8]
        today = dt.date.today().strftime("%d%m%Y")
        tday = today[0:2]
        tmonth = today[2:4]
        tyear = today[4:8]
        lastscore = data["previoushigh"]
        deadline = datetime.strptime(data["deadline"], "%d%m%Y,%H:%M") if data["deadline"] != None else None

        # if we found the date we return its status
        if(tday == day and tmonth == month and tyear == year):
            return (data["found"], lastscore, deadline, data["warned"])

        # otherwise assume it wasn't set
        return (False, lastscore, deadline, False)
    except Exception as e:
        print("Error in get fetched status", e)
        return (False, lastscore, deadline)

async def get_rider(rid, s):
    page = s.get(f'https://fantasy.road.cc/common/ajax.php?action=rideroverlay&rid={rid}')
    soup = BeautifulSoup(page.content, "html.parser")
    soup.prettify()
    name = soup.find('h3').text.strip()
    infotable = soup.find('table')
    rows = infotable.find_all('tr')
    team = rows[0].find_all('td')[1].text.strip()
    nationality = rows[1].find_all('td')[1].text.strip()
    bday = rows[2].find_all('td')[1].text.split(' ')
    birthday = None
    if len(bday) == 2:
        birthday = bday[1][1:-1]
    value = rows[3].find_all('td')[1].text
    form = rows[4].find_all('td')[1].text
    return(name, team, nationality, birthday, value, form)

async def get_riders():
    d = {}
    s = await login()
    s = await set_context(s, standard)
    p = 0
    while True:
        url = f'https://fantasy.road.cc/common/ajax.php?action=loadpicks&uid={os.getenv("ROAD_USERID")}&order=valuedesc&minval=3&maxval=40&page={p}&bal=1.2&findphrase=&allriders=0'
        page = s.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        soup.prettify()
        rows = soup.find("table", class_="riderlist").find_all('tr')
        if len(rows) <= 1:
            break
        for r in rows[1:]:
            rid = r.td.a.attrs['href'][len("javascript:showrider('"):-2]
            rider = await get_rider(rid, s)
            d[rider[0]] = {
                'team': rider[1],
                'nationality': rider[2],
                'birthday': rider[3],
                'value': float(rider[4]),
                'form': float(rider[5]),
                'stages': []
            }
        p+=1

    with open('riders_new.json', 'w+', encoding='utf-8') as f:
        json.dump(d, f)
    return d

async def login():
    s = requests.Session()
    x = s.post(login_url, data = login_data)
    if "Login failed" in str(x.content):
        print("Couldn't login")
        raise Exception("Couldn't login")
    return s

async def set_context(s, standard = True):
    s.get(context_url, params={"cid": standardId if standard else puristId})
    return s

async def get_ordered_rankings(standard = True):
    s = await login()
    s = await set_context(s, standard)
    
    # fetch rankings
    page = s.get(standard_url, params=params)

    # parse rankings
    soup = BeautifulSoup(page.content, "html.parser")
    soup.prettify()
    rows = soup.find_all('tr')
    players = []
    for row in rows:
        tds = row.find_all('td')
        if(len(tds) == 4):
            if tds[2].text == '-':
                return []
            (uid, sid, cid) = list(map(lambda x: x.replace('\'', '').strip(),(tds[2].find("a").attrs["href"][25:-1]).split(',')))
            pos = tds[0].text.strip()
            name = tds[1].text.strip()
            lst = name.split(' ')
            teamname = ' '.join(lst[0:len(lst)-1]).replace('\xa0', '')
            playername = lst[-1]
            score = tds[2].text.strip()
            did_increase = None 
            rankclass = tds[3].find("div").attrs["class"][1]
            if rankclass == "rankup":
                did_increase = True
            elif rankclass == "rankdown":
                did_increase = False
            increment = tds[3].text.strip()

            # get daily points
            subpage = s.get(player_points_url(uid, sid, cid))
            soup = BeautifulSoup(subpage.content, "html.parser")
            soup.prettify()
            daily_score = soup.find('table').find_all("th")[-1].text
            row = FantasyRow(pos, teamname, playername, daily_score, score, did_increase, increment)
            players.append(row)
    return players

async def get_stage_page(s, url):
    page = s.get(url, params=params)
    soup = BeautifulSoup(page.content, "html.parser")
    soup.prettify()
    t = soup.find('table', {"class": "leagues"})
    if t == None:
        return []
    rows = t.find_all('tr')
    ret = []
    for row in rows[1:]:
        tds = row.find_all('td')
        rider = tds[0].text.strip()
        team = tds[1].text.strip()
        score = int(tds[2].text.strip())
        ret.append((rider, team, score))
    return ret

async def sum_stages():
    s = await login()
    s = await set_context(s, standard)

    page = s.get(stages_url, params=params)

    soup = BeautifulSoup(page.content, "html.parser")
    soup.prettify()
    rows = soup.find_all('tr')
    d = get_from_template()
    for i in range (1, min(total_stage_count, get_current_stage())+1):
        r = rows[i] # skip header row
        url = base_url + "/stages" + r.find("a").attrs["href"]
        lst = await get_stage_page(s, url)
        for (rider, team, score) in lst:
            if rider in d:
                d[rider]["stages"].append({"stage": i, "points": score})
            else:
                print(rider + "("+ team +")" +" not found in template")
                d[rider] = {"team": team, "stages": [{"stage": i, "points": score}]}
    with open(f'{results_folder}/{rider_scores_json}', 'w+', encoding='utf-8') as f:
        json.dump(d, f)
    return d

def get_from_template():
    with open(template, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_rider_scores(fx=rider_scores_json):
    d = {}
    if(fx == rider_scores_json):
        with open(template, 'r', encoding='utf-8') as t:
            d = json.load(t)
    
    with open(f'{results_folder}/{fx}', 'r', encoding='utf-8') as f:
        riders = json.load(f)
        for k,v in riders.items():
            d[k] = v
    return d

def get_current_stage():
    now = get_current_time()
    return max(1, 1 + (now - startday).days - len(list(filter(lambda r: r <= now, restdays))))

def get_tomorrow_stage():
    curr = get_current_stage()
    now = get_current_time()
    if now < startday:
        curr = 0
    return curr + 1

def get_stage_points(stage, scores):
    try:
        if stage == None:
            stage = get_current_stage()
        points = []
        for k,v in scores.items():
            found_stages = list(filter(lambda x: x["stage"] == stage, v["stages"]))

            # rider scored points on the stage
            if(len(found_stages) > 0):
                points.append((k, found_stages[0]["points"]))
        
        points.sort(key=lambda x: x[1], reverse=True)

        ret = list(map(lambda x: f"{x[0]}: {str(x[1])}", points))
        if len(points) > 0:
            return f"```{discord_format}\n{nl.join(ret)}```"
        else:
            return f"No points given for this stage."


    except Exception as e:
        print(e)
        return "'{stage}' could not be found. He probably got 0 points or you spelled wrong."

async def get_deadline(stage=None):
    try:
        if stage == None:
            stage = get_current_stage()
        s = await login()
        s = await set_context(s, True)
        page = s.get(deadline_url)
        soup = BeautifulSoup(page.content, "html.parser")
        script = soup.find_all('script')[10]
        p = re.search('var nextStageTime = \d+', script.text)
        return (datetime.utcfromtimestamp(int(p.group()[20:])) + dt.timedelta(hours=2))
    except Exception as e:
        print(e)
        return None

async def get_transfers(s):
    # fetch rankings
    s = await set_context(s, True)
    # page = s.get(standard_url, params=params)

    current_stage = get_current_stage()

    d = {}
    players = get_tracked()
    for p in players:
        remaining_transfers_page = s.get(remaining_url, params={"uid": p})
        remaining = BeautifulSoup(remaining_transfers_page.content, "html.parser")

        todays_transfers_page = s.get(user_url, params={"uid": p})
        transfer_soup = BeautifulSoup(todays_transfers_page.content, "html.parser")
        transfer_soup.prettify()
        
        playername = transfer_soup.find("div", {"class": "gamewindow-title"}).find("h1").text[11:]
        d[playername] = {"remaining": remaining, "transfers": []}
        ts = transfer_soup.find_all("table", {"class": "leagues"})
        if(len(ts) < 2):
            return d
        t = ts[1]
        rows = t.find_all("tr")[1:]
        for r in rows:
            tds = r.find_all("td")
            stage = tds[1].text
            rider_in = tds[3].text
            rider_out = tds[4].text
            if(stage[0:comp_len] == competition_name and stage[comp_len:] == " stage "+str(current_stage)):
                c = d[playername]["transfers"]
                c.append((rider_out, rider_in))
                d[playername]["transfers"] = c

    return d

async def get_transfers_for_player(s, uid, current_stage):
    remaining_transfers_page = s.get(remaining_url, params={"uid": uid})
    remaining = BeautifulSoup(remaining_transfers_page.content, "html.parser")

    todays_transfers_page = s.get(user_url, params={"uid": uid})
    transfer_soup = BeautifulSoup(todays_transfers_page.content, "html.parser")
    transfer_soup.prettify()
    
    d = {}
    playername = transfer_soup.find("div", {"class": "gamewindow-title"}).find("h1").text[11:]
    d[playername] = {"remaining": remaining, "transfers": []}
    ts = transfer_soup.find_all("table", {"class": "leagues"})
    if(len(ts) < 2):
        return d
    t = ts[1]
    rows = t.find_all("tr")[1:]
    for r in rows:
        tds = r.find_all("td")
        stage = tds[1].text
        rider_in = tds[3].text
        rider_out = tds[4].text
        if(stage[0:comp_len] == competition_name and stage[comp_len:] == " stage "+str(current_stage)):
            c = d[playername]["transfers"]
            c.append((rider_out, rider_in))
            d[playername]["transfers"] = c
    return d

def get_tracked():
    with open("tracked.json", 'r', encoding='utf-8') as f:
        return json.load(f)

def AddToTransferTracker(uid):
    d = get_tracked()
    d[str(uid)] = True
    with open("tracked.json", 'w', encoding='utf-8') as f:
        return json.dump(d, f)

def remove_from_transfer_tracker(uid):
    d = get_tracked()
    del d[str(uid)]
    with open("tracked.json", 'w', encoding='utf-8') as f:
        return json.dump(d, f)

@client.command()
async def shrewbs(ctx):
    await ctx.send(f":)")

@client.command()
async def track(ctx):
    uid = ctx.message.content[7:].strip()
    try:
        AddToTransferTracker(uid)
        await ctx.send(f"Added {uid} to players to track.")
    except Exception as e:
        print(e)
        await ctx.send(f"Added {uid} from players to track.")

@client.command()
async def untrack(ctx):
    uid = ctx.message.content[8:].strip()
    try:
        remove_from_transfer_tracker(uid)
        await ctx.send(f"Removed {uid} from players to track.")
    except Exception as e:
        print(e)
        await ctx.send(f"{uid} could not be added.")

@client.command()
async def tracked(ctx):
    d = get_tracked()
    user_ids = d.keys()
    stringified = '\n'.join((map(lambda u: u, user_ids)))
    await ctx.send(f'```{discord_format}\n{stringified}```')

@client.command()
async def transfers(ctx):
    msg = ctx.message.content[10:].strip()
    try:
        if msg != '':
            stage = get_current_stage()
            s = await login()
            s = await set_context(s, True)
            d = await get_transfers_for_player(s, msg, stage)
            for k,v in d.items():
                out = '\n'.join(list(map(lambda t: f"{t[0]} -> {t[1]}", v["transfers"])))
                await ctx.send(f"Transfers for {k}. {v['remaining']} remaining\n```{discord_format}\n{out if out != '' else 'No transfers'}```")
    except Exception as e:
        print(e)
        await ctx.send(f"{msg} is not a valid user id")

    try:
        if msg == '':
            s = await login()
            d = await get_transfers(s)
            for k,v in d.items():
                out = '\n'.join(list(map(lambda t: f"{t[0]} -> {t[1]}", v["transfers"])))
                await ctx.send(f"Transfers for {k}. {v['remaining']} remaining\n```{discord_format}\n{out if out != '' else 'No transfers'}```")
    except Exception as e:
        print(e)
        await ctx.send(f'error in transfers: {str(e)}')

@client.command()
async def rank(ctx):
        rankings = await get_ordered_rankings()
        res = '**STANDARD**\n'+'\n'.join(list(map(lambda x: x.toString(), rankings)))
        await ctx.send(f"{res}")
        if rankings == None:
            await ctx.send(f"bot couldn't login")
            return

@client.command()
async def standard(ctx):
    await rank(ctx)

@client.command()
async def rankp(ctx):
    rankings = await get_ordered_rankings(False)
    if rankings == None:
        await ctx.send(f"bot couldn't login")
        return
    res = '**PURIST**\n' + '\n'.join(list(map(lambda x: x.toString(), rankings)))
    await ctx.send(f"{res}")

@client.command()
async def purist(ctx):
    await rankp(ctx)

@client.command()
async def stage(ctx):
    stage = None
    try:
        msg = ctx.message.content[7:].strip()
        splmsg = msg.split(' ')
        mbytour = splmsg[0]
        tour = None

        tour, _, old = get_tournament(mbytour)

        if(old):
            stage = int(splmsg[1].strip()) if len(splmsg) > 1 else None
        else:
            stage = int(msg.strip()) if len(msg) > 0 else None

        if(stage > 21):
            await ctx.send("No more stages left.")

        if(stage == None):
            await ctx.send(get_profile(tour))
        else:
            await ctx.send(get_profile(tour, stage))
    except Exception as e:
        print(e)
        await ctx.send(f"{stage} is not a valid stage")

@client.command()
async def prider(ctx):
    rider = ''
    try:
        msg = ctx.message.content[8:].strip()
        splmsg = msg.split(' ')
        mbytour = splmsg[0]
        scores = {}
        
        _, scores_json, old = get_tournament(mbytour)

        if(old):
            rider = ' '.join(splmsg[1:]).strip() if len(splmsg) > 1 else ''
        else:
            rider = msg.strip()
        scores = get_rider_scores(scores_json)

        greaterThan = rider[0] == ">" if len(rider) > 0 else False
        lessThan = rider[0] == "<" if len(rider) > 0 else False

        if rider == '' or greaterThan or lessThan:
            lst = []
            for k,v in scores.items():
                amount = 0
                total = sum(map(lambda x: x["points"], v["stages"]))
                ppptotal = str(round(total / v["value"], 2)) if 'value' in v else '0'
                
                if greaterThan or lessThan:
                    amount = float(rider[1:].strip())

                if not ((greaterThan and total <= amount) or (lessThan and total >= amount)):
                    lst.append((k, total, ppptotal))

            lst.sort(key=lambda x: x[1], reverse=True)
            ret = list(map(lambda x: f"{x[0]}: {str(x[1])} ({x[2]})", lst))
            chunks = [ret[x:x+60] for x in range(0, len(ret), 60)]
            nl = '\n'
            if(len(ret) == 0):
                await ctx.send("No rider fits the description")
            else:
                for c in chunks:
                    await ctx.send(f"```{discord_format}\n{nl.join(c)}```")
        else:
            matches = list(map(lambda x: (x, compare_string(rider, x)), scores.keys()))
            matches.sort(key=lambda x: x[1], reverse=True)
            name = matches[0][0]
            match = matches[0][1]

            if(match < 60):
                await ctx.send(f"No good result was found. The best guess was {name}. Type more of their name to finish the query.")
                return
            
            result = scores[name]
            total = sum(map(lambda x: x["points"], result["stages"]))
            ppptotal =  str(round(total / result["value"],2)) if 'value' in result else '0' 
            nl = '\n'

            name_line = f"{name} - {result['team']}"

            if 'nationality' in result:
                name_line += f", {result['nationality']}"
            if 'birthday' in result:
                parsed = datetime.strptime(result["birthday"], "%d/%m/%Y") if result["birthday"] != None else "Unknown"
                age = relativedelta(datetime.utcnow(), parsed).years if result["birthday"] != None else "Unknown"
                name_line += f", age: {age}"
            if 'value' in result:
                name_line += f", value: {result['value']}"
            if 'form' in result:
                name_line += f", form: {result['form']}"
            await ctx.send(f"```{discord_format}\n{name_line}\n{nl.join(list(map(lambda x: 'Stage ' + str(x['stage']) + ': ' + str(x['points']), result['stages'])))}\nTotal: {total} ({'0' if ppptotal == None else ppptotal})```")
    except Exception as e:
        print(e)
        await ctx.send(f"prider error: {str(e)}")

@client.command()
async def vrider(ctx):
    rider = ''
    try:
        msg = ctx.message.content[8:].strip()
        splmsg = msg.split(' ')
        mbytour = splmsg[0]
        scores = {}
        
        _, scores_json, old = get_tournament(mbytour)

        if(old):
            rider = ' '.join(splmsg[1:]).strip() if len(splmsg) > 1 else ''
        else:
            rider = msg.strip()
        scores = get_rider_scores(scores_json)    

        greaterThan = rider[0] == ">" if len(rider) > 0 else False
        lessThan = rider[0] == "<" if len(rider) > 0 else False

        if rider == '' or greaterThan or lessThan:
            lst = []
            for k,v in scores.items():
                amount = 0
                total = sum(map(lambda x: x["points"], v["stages"]))
                ppptotal = total / v["value"] if 'value' in v else 0
                
                if greaterThan or lessThan:
                    amount = float(rider[1:].strip())

                if not ((greaterThan and ppptotal <= amount) or (lessThan and ppptotal >= amount)):
                    lst.append((k, total, ppptotal))

            lst.sort(key=lambda x: x[2], reverse=True)
            ret = list(map(lambda x: f"{x[0]}: {str(round(x[2], 2))} ({x[1]})", lst))
            chunks = [ret[x:x+60] for x in range(0, len(ret), 60)]
            nl = '\n'
            if(len(ret) == 0):
                await ctx.send("No rider fits the description")
            else:
                for c in chunks:
                    await ctx.send(f"```{discord_format}\n{nl.join(c)}```")
        else:
            matches = list(map(lambda x: (x, compare_string(rider, x)), scores.keys()))
            matches.sort(key=lambda x: x[1], reverse=True)
            name = matches[0][0]
            match = matches[0][1]

            if(match < 60):
                await ctx.send(f"No good result was found. The best guess was {name}. Type more of their name to finish the query.")
                return
            
            result = scores[name]
            total = sum(map(lambda x: x["points"], result["stages"]))
            ppptotal =  str(round(total / result["value"],2)) if 'value' in result else None 
            nl = '\n'
            name_line = f"{name} - {result['team']}"

            if 'nationality' in result:
                name_line += f", {result['nationality']}"
            if 'birthday' in result:
                parsed = datetime.strptime(result["birthday"], "%d/%m/%Y") if result["birthday"] != None else "Unknown"
                age = relativedelta(datetime.utcnow(), parsed).years if result["birthday"] != None else "Unknown"
                name_line += f", age: {age}"
            if 'value' in result:
                name_line += f", value: {result['value']}"
            if 'form' in result:
                name_line += f", form: {result['form']}"
            await ctx.send(f"```{discord_format}\n{name_line}\n{nl.join(list(map(lambda x: 'Stage ' + str(x['stage']) + ': ' + (str(round(x['points']/result['value'],2))) if 'value' in result else '0' + ' (' + str(x['points']) + ')', result['stages'])))}\nTotal: {'0' if None else ppptotal} ({total})```")
    except Exception as e:
        print(e)
        await ctx.send(f"'{rider}' could not be found.")

@client.command()
async def pteam(ctx):
    try:
        msg = ctx.message.content[7:].strip()
        splmsg = msg.split(' ')
        mbytour = splmsg[0]
        scores = {}
        
        _, scores_json, old = get_tournament(mbytour)

        if(old):
            team = ' '.join(splmsg[1:]) if len(splmsg) > 1 else ''
        else:
            team = msg

        scores = get_rider_scores(scores_json)

        if(team == ''):
            d = {}
            for k,v in scores.items():
                total = sum(map(lambda x: x["points"], v["stages"]))
                if(v["team"] in d):
                    d[v["team"]] = d[v["team"]] + total
                else:
                    d[v["team"]] = total

            lst = list(d.items())
            lst.sort(key=lambda x: x[1], reverse=True)
            ret = list(map(lambda x: f"{x[0]}: {str(x[1])}", lst))
            nl = '\n'
            await ctx.send(f"```{discord_format}\n{nl.join(ret)}```")
        else:
            all_teams = {v["team"]:True for (k,v) in scores.items()}.keys()
            matches = list(map(lambda x: (x, compare_string(team, x)), all_teams))
            matches.sort(key=lambda x: x[1], reverse=True)
            name = matches[0][0]
            riders = {k:v for (k,v) in scores.items() if v["team"] == name}
            points = []
            for k, v in riders.items():
                rider = k
                total = sum(map(lambda x: x["points"], v["stages"]))
                points.append((rider, total))
            points.sort(key=lambda x: x[1], reverse=True)

            ret = list(map(lambda x: f"{x[0]}: {str(x[1])}", points))

            nl = '\n'
            await ctx.send(f"```{discord_format}\n{name}\n{nl.join(ret)}```")
    except Exception as e:
        print(e)
        await ctx.send(f'pteam error: {str(e)}')

@client.command()
async def pstage(ctx):
    try:
        msg = ctx.message.content[7:].strip()
        splmsg = msg.split(' ')
        mbytour = splmsg[0]
        scores = {}
        stage = None

        _, scores_json, old = get_tournament(mbytour)
        if(old):
            stage = int(splmsg[1]) if len(splmsg) > 1 else None
        else:
            stage = int(msg) if len(msg) > 0 else None
        scores = get_rider_scores(scores_json)
        

        await ctx.send(get_stage_points(stage, scores))
    except Exception as e:
        print(e)
        await ctx.send(f'pstage error: {str(e)}')

@client.command()
async def forcefix(ctx):
    try:
        await ctx.send("...")
        rankings = await get_ordered_rankings(True)
        await sum_stages()
        new_highscore = rankings[0].score
        set_fetched_status(False, int(new_highscore), await get_deadline(), False)
        await ctx.send("Tried to fix points")
    except Exception as e:
        await ctx.send(f"error in forcefix: {str(e)}")

@client.command()
async def holdet(ctx):
    try:
        msg = ctx.message.content[7:].strip()
        spl = msg.split(' ')
        sortby = 'value'
        if(len(spl) > 0):
            if spl[0] in ['name', 'value', 'growth', 'totalgrowth', 'popularity', 'trend']:
                sortby = spl[0]
            else:
                await ctx.send(f"'{spl[0]}' is not a valid sort metric. Valid metrics are: name, value, growth, totalgrowth, popularity, trend")
                return
        d = HoldetDKService.get_rider_values(holdet_tournament_id, holdet_game_id, get_current_stage())
        data = [{
            'name': k, 
            'value': v['value'] / 1000000, 
            'growth': v['growth'] / 1000000.0,
            'totalgrowth': v['totalGrowth'] / 1000000.0,
            'popularity': v['popularity'] * 100,
            'trend': v['trend']
            } for k,v in d.items()]
        data.sort(key=lambda r: r[sortby], reverse=False if sortby == 'name' else True)

        if(len(spl) > 2):
            if spl[1] == '<':
                data = list(filter(lambda r: r[sortby] < float(spl[2]) , data))
            if spl[1] == '>':
                data = list(filter(lambda r: r[sortby] > float(spl[2]) , data))

        output_data = list(map(lambda r: f'{r["name"]}, {r["value"]:.3f}, {r["growth"]:.3f}, {r["totalgrowth"]:.3f}, {r["popularity"]:.2f}%, {r["trend"]}', data))
        if(len(output_data) == 0):
            await ctx.send("No riders found")
        else:
            chunks = [output_data[x:x+40] for x in range(0, len(output_data), 40)]
            chunks[0] = [(f'Rider, value, growth, total growth, popularity, trend')] + chunks[0]
            for c in chunks:
                await ctx.send(f"```{discord_format}\n{nl.join(c)}```")
    
    except Exception as e:
        await ctx.send(f'error in holdet: {[str(e)]}')


@client.command()
async def letour(ctx):
    try:
        msg = ctx.message.content[7:].strip()
        spl = msg.split(' ')
        d = await lts.get_rider_values(get_current_stage())
        if d == None:
            d = await lts.get_rider_values(get_current_stage() + 1)
        
        if d == None:
             await ctx.send(f"Couldn't get rider values from letour.fr")
             return
        data = [{
            'name': k, 
            'value': float(v), 
            } for k,v in d.items()]
        data.sort(key=lambda r: r['value'], reverse=True)

        if(len(spl) > 1):
            if spl[0] == '<':
                data = list(filter(lambda r: r['value'] < float(spl[1]) , data))
            if spl[0] == '>':
                data = list(filter(lambda r: r['value'] > float(spl[1]) , data))

        output_data = list(map(lambda r: f'{r["name"]} - {r["value"]}', data))
        if(len(output_data) == 0):
            await ctx.send("No riders found")
        else:
            chunks = [output_data[x:x+40] for x in range(0, len(output_data), 40)]
            chunks[0] = [(f'Rider - Value')] + chunks[0]
            for c in chunks:
                await ctx.send(f"```{discord_format}\n{nl.join(c)}```")
    
    except Exception as e:
        print(e)
        await ctx.send(f'error in letour: {[str(e)]}')

# TODO: list value from road, holdet, and letour. Note biggest prize jump
# @client.command()
# async def prices(ctx):


@tasks.loop(minutes=10)
async def job():
    channel = None
    try:
        channel = client.get_channel(int(channelId))
        if channel == None:
            return

        now = get_current_time()
        tomorrow = now + dt.timedelta(days=1)

        (dont_look, lasthighscore, deadline, warned) = get_fetched_status()
        look_for_scores = not dont_look

        # Daily reminder
        if(
            now.hour >= 21 and not warned and 
            now >= startday - dt.timedelta(days=1) and now < endday and
            len(list(filter(lambda d: d.day == tomorrow.day and d.month == tomorrow.month and d.year == tomorrow.year, restdays))) == 0
        ):
            dl = await get_deadline() if deadline == None else deadline 
            stage = get_tomorrow_stage()
            hour = "" if dl == None else "0"+dl.hour if dl.minute < 10 else dl.hour
            minute = "" if dl == None else "0"+dl.minute if dl.minute < 10 else dl.minute
            await channel.send(f":warning: Remember to set your team! :warning: It is stage {stage}.{f' Deadline is {hour}:{minute}' if hour != None else ''}")
            await channel.send("Following is next stage!")
            await channel.send(get_profile(None, stage))
            set_fetched_status(dont_look, lasthighscore, dl, True)

        # don't do anything on days without a race
        if(now < startday or now > endday or len(list(filter(lambda d: d.day == now.day and d.month == now.month and d.year == now.year, restdays))) > 0):
            return

        # wait for deadline to find peoples transfers
        if deadline != None and now > deadline+dt.timedelta(minutes=2): # offset to ensure minor time differences
            s = await login()
            d = await get_transfers(s)
            for k,v in d.items():
                out = '\n'.join(list(map(lambda t: f"{t[0]} -> {t[1]}", v["transfers"])))
                await channel.send(f"Transfers for {k}. {v['remaining']} remaining\n```{discord_format}\n{out}```")

            set_fetched_status(dont_look, lasthighscore, None, warned)


        # look for new scores if its between 17 and 6 and we haven't found any new scores yet
        if((now.hour >= 17 or now.hour < 6) and look_for_scores):
            # check for scores in standard
            rankings = await get_ordered_rankings(True)
            
            if rankings == None:
                await channel.send(f"bot couldn't login")
                return

            new_highscore = rankings[0].score
            # ensure a score is found such that we continue checking
            if(new_highscore != "-" and int(new_highscore) > lasthighscore):
                
                # update the rider rankings
                scores = await sum_stages()
                msg = get_stage_points(None, scores)
                await channel.send("**POINTS!**")
                await channel.send(msg)
                res = '**STANDARD**\n' + '\n'.join(list(map(lambda x: x.toString(), rankings)))
                
                
                rankingsp = await get_ordered_rankings(False)
                # check for scores in purist
                if rankingsp == None:
                    await channel.send(f"bot couldn't login")
                    return

                res += '\n\n**PURIST**\n' + '\n'.join(list(map(lambda x: x.toString(), rankingsp)))

                # no longer look for new scores
                new_deadline = await get_deadline()
                set_fetched_status(True, int(new_highscore), new_deadline, warned)

                # send message to discord
                await channel.send(res)

        # reset to track for new scores
        if(now.hour == 6):
            set_fetched_status(False, lasthighscore, deadline, False)
    except Exception as e:
        if channel:
            channel.send(f"Error in loop: {str(e)}")
        print(e)

print("bot started")
job.start()
client.run(os.getenv('DISCORD_KEY'))

# async def main():
#      await letour('> 5')

# if __name__ ==  '__main__':
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())

