import os
from google import genai
from google.genai import types
import congress

INSTRUCTION = """You are a helpful chatbot designed to help the user learn about bills in front of congress. 
You will use the congressional api to access information about these bills. Call list_bills to get a list of bills.
For any object in a response that contains a url, call call_endpoint to get more information on it"""

MODEL = "gemini-2.0-flash"

FUNCTIONS = [
    (congress.list_bills_schema, congress.list_bills)
]

class CongressAgent:
    """
    Agent for interacting with congress APIf
    """
    def __init__(self, instruction=INSTRUCTION, model=MODEL):
        tools = types.Tool(function_declarations=[schema for (schema, _) in FUNCTIONS])
        self.functions = {schema['name']: function for schema, function in FUNCTIONS}
        self.client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
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
                function_name = tool_call.name
                function = self.functions[function_name]
                args = tool_call.args
                print(f"-- calling {function_name}(**{args})")
                result = function(**args)
                result_part = types.Part.from_function_response(name=function_name,
                                                                response={"result": result})
                contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)]))
                contents.append(types.Content(role="user", parts=[result_part]))
                resp = self.gen_content(contents)
            print(resp.text)
