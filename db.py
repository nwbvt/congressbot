import requests
import os
import html
from google import genai
from google.genai import types
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from google.api_core import retry
from lxml import etree
from dotenv import load_dotenv, find_dotenv

BULK_URL = "https://www.govinfo.gov/bulkdata/json"

def is_retriable(e):
    return isinstance(e, genai.errors.APIError) and e.code in {429, 503}

class Embedder(EmbeddingFunction):
    def __init__(self, doc_mode, client):
        self.doc_mode = doc_mode
        self.client = client

    def set_query_mode(self):
        self.doc_mode = False

    def set_doc_mode(self):
        self.doc_mode = True

    @retry.Retry(predicate=is_retriable)
    def __call__(self, to_embed: Documents) -> Embeddings:
        task = "retrieval_document" if self.doc_mode else "retrieval_query"
        resp = self.client.models.embed_content(
                model="models/text-embedding-004",
                contents=to_embed,
                config=types.EmbedContentConfig(task_type=task)
        )
        return [e.values for e in resp.embeddings]

def load_doc(url:str, load_path:str, id_path:str,
             metadata_paths:dict[str,str])->tuple[str, str, dict[str,str]]:
    resp = requests.get(url)
    body = ""
    metadata = {}
    if resp.status_code == 200:
        tree = etree.fromstring(resp.content)
        doc_id = tree.xpath(id_path)[0]
        for part in tree.xpath(load_path):
            body+=html.escape(part.text)
        for key in metadata_paths:
            metadata[key] = tree.xpath(metadata_paths[key])[0]
    return body, doc_id, metadata

def recursive_load(url:str, load_path:str, id_path:str,
                   metadata_paths:dict[str,str])->list[tuple[str, str, dict[str,str]]]:
    print(f"Loading from {url}")
    resp = requests.get(url, headers={"accept": "application/json"})
    if resp.status_code != 200:
        print(f"Error getting documents: {resp.status_code}\n{resp.text}")
        return
    for f in resp.json()['files']:
        if f['folder']:
            for doc in recursive_load(f['link'], load_path, id_path, metadata_paths):
                yield doc
        elif f['mimeType'] == 'application/xml':
            yield load_doc(f['link'], load_path, id_path, metadata_paths)

def load_docs(type: str, congress:int, load_path:str, id_path:str,
              metadata_paths:dict[str,str])->list[tuple[str, str, dict[str,str]]]:
    url = f"{BULK_URL}/{type}/{congress}"
    return recursive_load(url, load_path, id_path, metadata_paths)

BILL_SUMMARY_TABLE="billsummaries"

query_bill_summaries_schema = {
    "name": "query_bill_summaries",
    "description": "Finds bill summaries relevant to a given query",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string",
                      "description": "A natural language query to use to find relevant bills. "+
                      "It will return a map with the bill summary, the congress, bill type, bill number"+
                      ", and the endpoint you can access it with the api"},
            "n": {"type": "integer", "description": "the number of results to return"},
            "congress": {"type": "integer", "description": "use this to restrict results to a single congress"},
            "bill_type": {"type": "string", "description": "use this to restrict results to a single bill type",
                          "enum": ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]}
        },
        "required": ["query", "n"]
    }
}

class VectorDB:
    def __init__(self, db_path: str, ai_client: genai.Client, doc_mode: bool=True):
        self.db_client = chromadb.PersistentClient(path=db_path)
        self.embed_fn = Embedder(doc_mode, ai_client)

    def load_bill_summaries(self, congress:int):
        """Load the bills from the bulk data source"""
        documents = load_docs("BILLSUM", congress, "item/summary/summary-text", "item/@measure-id",
                              {'congress': 'item/@congress', 'type': 'item/@measure-type', 'number': 'item/@measure-number'})
        db = self.db_client.get_or_create_collection(name=BILL_SUMMARY_TABLE, embedding_function=self.embed_fn)
        self.embed_fn.set_doc_mode()
        i=0
        for doc, id, metadata in documents:
            db.add(documents=doc, metadatas=metadata, ids=id)
            i+=1
            print(f"Inserted {i} documents", end="\r")
        return db

    def query_bill_summaries(self, query:str, n:int, congress:int=None, bill_type:str=None):
        """Query the bill summaries"""
        try:
            db = self.db_client.get_collection(BILL_SUMMARY_TABLE, embedding_function=self.embed_fn)
        except chromadb.errors.NotFoundError:
            print("Error: bill summaries not loaded")
            return []
        where = {}
        if congress is not None:
            where['congress']=congress
        if bill_type is not None:
            where['type']=bill_type
        query_results = db.query(query_texts=query, n_results=n, where=where or None, include=["documents", "metadatas"])
        results = []
        for doc, metadata in zip(query_results['documents'][0], query_results['metadatas'][0]):
            congress = metadata["congress"]
            bill_type = metadata["type"]
            bill_number = metadata["number"]
            endpoint = f"/bill/{congress}/{bill_type}/{bill_number}"
            results.append({"bill_summary": doc, "congress": congress, "bill_type": bill_type,
                            "bill_number": bill_number, "endpoint": endpoint})
        return results

def load(db_path:str, congress:int):
    load_dotenv(find_dotenv())
    ai_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    db = VectorDB(db_path, ai_client)
    db.load_bill_summaries(congress)
