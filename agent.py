import os
from google import genai
from google.genai import types
import congress
import db

INSTRUCTION = """You are a helpful chatbot designed to help the user learn about the activities congress. 
You will use the congressional api to access information about bills and members of congress.
If you don't know what value to include for an optional parameter, don't include anything.
For any object in a response that contains a url, call call_endpoint to get more information on it"""

MODEL = "gemini-2.0-flash"

FUNCTIONS = [
    (congress.list_bills_schema, congress.list_bills),
    (congress.call_endpoint_schema, congress.call_endpoint),
    (congress.get_members_schema, congress.get_members)
]

DB_METHODS = [
    db.query_bill_summaries_schema
]

class CongressAgent:
    """
    Agent for interacting with congress API
    """
    def __init__(self, instruction=INSTRUCTION, model=MODEL, db_path=".chroma"):
        self.client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        self.db = db.VectorDB(db_path, self.client)
        self.functions = {schema['name']: function for schema, function in FUNCTIONS}
        for method in DB_METHODS:
            self.functions[method['name']] = getattr(self.db, method['name'])
        function_tools = [schema for (schema, _) in FUNCTIONS]
        tools = types.Tool(function_declarations=function_tools+DB_METHODS)
        self.config = types.GenerateContentConfig(system_instruction=instruction, tools = [tools])
        self.model = model

    def gen_content(self, contents):
        return self.client.models.generate_content(
            model=self.model, config=self.config, contents=contents
        ).candidates[0].content.parts[0]

    def run(self):
        contents = []
        while True:
            s = input("-->")
            if s == 'q':
                return
            contents.append(types.Content(role="user", parts=[types.Part(text=s)]))
            resp = self.gen_content(contents)
            while resp.text is None:
                tool_call = resp.function_call
                contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)]))
                function_name = tool_call.name
                function = self.functions[function_name]
                args = tool_call.args
                print(f"-- calling {function_name}(**{args})")
                result = function(**args)
                result_part = types.Part.from_function_response(name=function_name,
                                                                response={"result": result})
                contents.append(types.Content(role="user", parts=[result_part]))
                resp = self.gen_content(contents)
            print(resp.text)
