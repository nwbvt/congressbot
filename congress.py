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

def call_endpoint(endpoint:str, params:dict[str,str]={}) -> dict:
    """Get information from the congress api."""
    if endpoint.startswith(BASE_URL):
        url = endpoint
    else:
        url = f"{BASE_URL}/{endpoint}"
    api_key = os.environ["CONGRESS_API_KEY"]
    r = requests.get(url, auth=(api_key,''), params=params, headers={'accept': 'application/json'})
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Error calling api, status code {r.status_code}: {r.text}")

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

def list_bills(offset:int=0, limit:int=250, fromDate: str=None, toDate:str=None, congress:int=None) -> list[dict]:
    """List the bills considered by Congress."""
    if congress is None:
        endpoint = "bill"
    else:
        endpoint = f"bill/{congress}"
    resp = call_endpoint(endpoint, {"offset": offset, "limit": limit, "fromDateTime": fromDate, "toDateTime": toDate})
    return resp['bills']

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

def get_bill(congress:int, billType: str, billNumber: int) -> dict:
    """get information about a specific bill"""
    endpoint = f"/bill/{congress}/{billType}/{billNumber}"
    resp = call_endpoint(endpoint)
    return resp

get_bill_text_schema = {
    "name": "get_bill_text",
    "description": "Gets the bill text",
    "parameters": {
        "type": "object",
        "properties": {
            "congress": {"type": "integer",
                         "description": "the number of the congress which considered the bill"},
            "billType": {"type": "string",
                         "description": "the type of bill",
                         "enum": ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]},
            "billNumber": {"type": "integer",
                           "description": "the bill number"},
            "asOf": {"type": "string",
                     "description": "set this to a date in YYYY/MM/DD format if you want to get the text before that date"}
        },
        "required": ["congress", "billType", "billNumber"]
    }
}

def get_bill_text(congress:int, billType: str, billNumber:int, asOf:str=None, format="Formatted XML") -> str:
    """get the bill text"""
    endpoint = f"/bill/{congress}/{billType}/{billNumber}/text"
    resp = call_endpoint(endpoint)
    versions = resp['textVersions']
    if asOf is not None:
        versions = [v for v in versions if v['date'] <= asOf]
    versions.sort(key=lambda x: x['date'], reverse=True)
    formats = versions[0]['formats']
    for text_format in formats:
        if text_format['type'] == format:
            resp = requests.get(text_format['url'])
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"Error {resp.status_code}: {resp.text}")
    print(f"Only found formats {formats}")

get_members_schema = {
    "name": "get_members",
    "description": "Gets a list of members of congress",
    "parameters": {
        "type": "object",
        "properties": {
            "congress": {"type": "integer",
                         "description": "search by a specific congress"},
            "state": {"type": "string",
                      "description": "Two letter identifier for the state"},
            "district": {"type": "integer",
                         "description": "The district number. Can only be specified if the state is also set"},
            "current": {"type": "boolean",
                        "description": "Whether to only return current members"}
        }
    }
}

def get_members(congress:int=None, state:str=None, district:int=None, current:int=True) -> list[dict]:
    """Get a list of members"""
    endpoint = "/member"
    if congress is not None:
        endpoint += f"/congress/{congress}"
    if state is not None:
        endpoint += f"/{state}"
        if district is not None:
            endpoint += f"/{district}"
    resp = call_endpoint(endpoint, {"currentMember": current})
    return resp["members"]
