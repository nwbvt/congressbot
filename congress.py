import requests
import os

BASE_URL = "https://api.congress.gov/v3"

call_endpoint_schema = {
    "name": "call_endpoint",
    "description": "call an endpoint on the congress API",
    "parameters": {
        "type": "object",
        "properties": {
            "endpoint": {
                "type": "string",
                "description": f"The endpoint to access. Can be absolute or relative to {BASE_URL}"
            },
        },
        "required": ["endpoint"]
    }
}

def call_endpoint(endpoint:str, params:dict[str,str]={}) -> tuple[int, dict]:
    """Get information from the congress api."""
    if endpoint.startswith(BASE_URL):
        url = endpoint
    else:
        url = f"{BASE_URL}/{endpoint}"
    api_key = os.environ["CONGRESS_API_KEY"]
    r = requests.get(url, auth=(api_key,''), params=params, headers={'accept': 'application/json'})
    return r.status_code, r.json()

list_bills_schema = {
    "name": "list_bills",
    "description": "Lists bills being considered by Congress",
    "parameters": {
        "type": "object",
        "properties": {
            "offset": {"type": "integer",
                       "description": "offset for the list of bills"},
            "limit": {"type": "integer",
                      "description": "the number of bills to return"},
            "fromDate": {"type": "string",
                         "description": "the date of the earliest bills to return, leave blank for no restriction"},
            "toDate": {"type": "string",
                       "description": "the date of the lastest bills to return, leave blank for no restriction"},
            "congress": {"type": "integer",
                         "description": "the number of the congress to gets bills from, leave blank for the current congress"}
        },
        "required": []
    }
}

def list_bills(offset:int=0, limit:int=250, fromDate: str=None, toDate:str=None, congress:int=None) -> list[map]:
    """List the bills considered by Congress."""
    if congress is None:
        endpoint = "bill"
    else:
        endpoint = f"bill/{congress}"
    sc, resp = call_endpoint(endpoint, {"offset": offset, "limit": limit, "fromDateTime": fromDate, "toDateTime": toDate})
    if sc == 200:
        return resp['bills']
    else:
        print(f"Error calling api, status code {sc}: {resp}")

get_bill_schema = {
    "name": "get_bill",
    "description": "Gets detailed information about a bill",
    "parameters": {
        "type": "object",
        "properties": {
            "congress": {"type": "integer",
                         "description": "the number of the congress which considered the bill"},
            "billType": {"type": "string",
                         "description": "the type of bill",
                         "enum": ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]},
            "billNumber": {"type": "integer",
                           "description": "the bill number"}
        },
        "required": ["congress", "billType", "billNumber"]
    }
}

def get_bill(congress:int, billType: str, billNumber: int) -> map:
    """get information about a specific bill"""
    endpoint = f"/bill/{congress}/{billType}/{billNumber}"
    sc, resp = call_endpoint(endpoint)
    if sc == 200:
        return resp
    else:
        print(f"Error calling api, status code {sc}: {resp}")
