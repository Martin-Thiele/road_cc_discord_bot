from dotenv import load_dotenv
import requests
import json

load_dotenv()

class LeTourService:
    def __init__(self, access_token, x_access_key):
        self.access_token = access_token
        self.x_access_key = x_access_key

    def get_rider_values(self, stage):
        url = "https://fantasybytissot.letour.fr/v1/private/searchjoueurs?lg=en"
        headers = {
            "authorization": f"Token {self.access_token}",
            "x-access-key": self.x_access_key,
        }

        data = {
            "filters": {
                "nom": "",
                "club": "",
                "position": "",
                "budget_ok": False,
                "engage": False,
                "partant": False,
                "dreamteam": False,
                "quota": "",
                "idj": str(stage),
                "pageIndex": 0,
                "pageSize": 250,
                "loadSelect": 0,
                "searchonly": 1,
            }
        }

        resp = requests.post(url, headers=headers, json=data)
        d = json.loads(resp.content)
        if "message" in d:
            return None
        riderDict = {item["nomcomplet"]: float(item["valeur"]) for item in d["joueurs"]}
        return riderDict

    def get_rider_values_dict(self, stage):
        d = self.get_rider_values(stage)
        if d is None:
            return {}

        return {k: {"value": float(v)} for k, v in d.items()} 
