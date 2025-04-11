import requests
import os

BASE_URL = "https://api.congress.gov/v3"

def call_endpoint(endpoint:str, params:dict[str,str]={}):
    """Get information from the congress api"""
    if endpoint.startswith(BASE_URL):
        url = endpoint
    else:
        url = f"{BASE_URL}/{endpoint}"
    api_key = os.environ["CONGRESS_API_KEY"]
    r = requests.get(url, auth=(api_key,''), params=params, headers={'accept': 'application/json'})
    return r.status_code, r.json()

def list_bills(offset:int=0, limit:int=250, fromDate: str=None, toDate:str=None, congress:int=None):
    """List the bills considered by Congress"""
    if congress is None:
        endpoint = "bill"
    else:
        endpoint = f"bill/{congress}"
    sc, resp = call_endpoint(endpoint, {"offset": offset, "limit": limit, "fromDateTime": fromDate, "toDateTime": toDate})
    if sc == 200:
        return resp
