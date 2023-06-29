import asyncio
from dotenv import load_dotenv
import requests
import json
import os

load_dotenv()

class LeTourService:
    def __init__(self, access_token, x_access_key):
        self.access_token = access_token
        self.x_access_key = x_access_key

    async def get_rider_values(self):
        url = 'https://fantasybytissot.letour.fr/v1/private/searchjoueurs?lg=en'
        headers = {
            'authorization': f'Token {self.access_token}',
            'x-access-key': self.x_access_key
        }

        data = {
            'filters': {
                'nom': '',
                'club': '',
                'position': '',
                'budget_ok': False,
                'engage': False,
                'partant': False,
                'dreamteam': False,
                'quota': '',
                'idj': '1',
                'pageIndex': 0,
                'pageSize': 250,
                'loadSelect': 0,
                'searchonly': 1
            }
        }

        resp = requests.post(url, headers=headers, json=data)
        d = json.loads(resp.content)
        riderDict = {item['nomcomplet']: item['valeur'] for item in d['joueurs']}
        return riderDict