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

    def set_query(self):
        self.doc_mode = False

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
    docs = []
    if resp.status_code != 200:
        print(f"Error getting documents: {resp.status_code}\n{resp.text}")
        return []
    for f in resp.json()['files']:
        if f['folder']:
            docs += recursive_load(f['link'], load_path, id_path, metadata_paths)
        elif f['mimeType'] == 'application/xml':
            doc, doc_id, md = load_doc(f['link'], load_path, id_path, metadata_paths)
            docs.append((doc, doc_id, md))
    return docs

def load_docs(type: str, congress:int, load_path:str, id_path:str,
              metadata_paths:dict[str,str])->list[tuple[str, str, dict[str,str]]]:
    url = f"{BULK_URL}/{type}/{congress}"
    return recursive_load(url, load_path, id_path, metadata_paths)

BILL_SUMMARY_TABLE="billsummaries"

def load_bill_summaries(db_client: chromadb.api.client.Client, ai_client: genai.Client, congress:int):
    """Load the bills from the bulk data source"""
    documents = load_docs("BILLSUM", congress, "item/summary/summary-text", "item/@measure-id",
                          {'congress': 'item/@congress', 'type': 'item/@measure-type', 'number': 'item/@measure-number'})
    embed_fn = Embedder(True, ai_client)
    db = db_client.get_or_create_collection(name=BILL_SUMMARY_TABLE, embedding_function=embed_fn)
    for doc, id, metadata in documents:
        db.add(documents=doc, metadatas=metadata, ids=id)
    embed_fn.set_query()
    return db

def load(db_path:str, congress:int):
    load_dotenv(find_dotenv())
    db_client = chromadb.PersistentClient(path=db_path)
    ai_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    load_bill_summaries(db_client, ai_client, congress)
