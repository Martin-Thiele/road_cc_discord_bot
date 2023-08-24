from typing import Any
import requests
import json

class HoldetDKService():
    @staticmethod
    def get_rider_values(tournament_id, game_id, stage) -> dict[str, Any]:
        resp = requests.get(f'https://api.holdet.dk/tournaments/{tournament_id}?appid=holdet&culture=da-DK')
        nameData = json.loads(resp.content)
        resp = requests.get(f'https://api.holdet.dk/games/{game_id}/rounds/{stage}/statistics?appid=holdet&culture=da-DK')
        riderData = json.loads(resp.content)
        

        nameDict = {item['id']: item for item in nameData['persons']}
        playerDict = {item['person']['id']: item for item in nameData['players']}
        riderDict = {item['player']['id']: item for item in riderData}
        d: dict[str, Any] = {}
        for (k,v) in nameDict.items():
            d[f"{v['firstname']} {v['lastname']}"] = riderDict[playerDict[v['id']]['id']]['values']
        return d
    
    @staticmethod
    def get_rider_values_dict(tournament_id, game_id, stage) -> dict[str, dict[str, Any]]:
        d = HoldetDKService.get_rider_values(tournament_id, game_id, stage)
        return {k: {
            'value': v['value'] / 1000000,
            'growth': v['growth'] / 1000000.0,
            'totalgrowth': v['totalGrowth'] / 1000000.0,
            'popularity': v['popularity'] * 100,
            'trend': v['trend']
        } for k,v in d.items() }

    @staticmethod
    def get_rider_values_formatted(tournament_id, game_id, stage) -> list[dict[str, Any]]:
        d = HoldetDKService.get_rider_values(tournament_id, game_id, stage)
        return [{
            'name': k, 
            'value': v['value'] / 1000000, 
            'growth': v['growth'] / 1000000.0,
            'totalgrowth': v['totalGrowth'] / 1000000.0,
            'popularity': v['popularity'] * 100,
            'trend': v['trend']
            } for k,v in d.items()]