import requests
import json

class HoldetDKService():
    @staticmethod
    def get_rider_values(tournament_id, game_id, stage):
        resp = requests.get(f'https://api.holdet.dk/tournaments/{tournament_id}?appid=holdet&culture=da-DK')
        nameData = json.loads(resp.content)
        resp = requests.get(f'https://api.holdet.dk/games/{game_id}/rounds/{stage}/statistics?appid=holdet&culture=da-DK')
        riderData = json.loads(resp.content)
        

        nameDict = {item['id']: item for item in nameData['persons']}
        playerDict = {item['person']['id']: item for item in nameData['players']}
        riderDict = {item['player']['id']: item for item in riderData}
        d = {}
        for (k,v) in nameDict.items():
            d[f"{v['firstname']} {v['lastname']}"] = riderDict[playerDict[v['id']]['id']]['values']
        return d