# CongressBot
## Description
A gen-ai based tool using the congress API and Google's Gemini LLM
## Local Setup
1. Generate a GOOGLE_API_KEY (available [here](https://aistudio.google.com/app/apikey)) and CONGRESS_API KEY (available [here](https://api.congress.gov/sign-up/)) and put both in a .env
2. Install the local depenedencies with `pip install -r requirements.txt`
3. Populate the database with data from the bulk api via `python load_db -c {congress_number}`
4. Run the jupyter notebook with 'jupyter notebook'
5. Load CongressBot.ipynb
