import argparse
import agent
from dotenv import load_dotenv, find_dotenv

def run():
    load_dotenv(find_dotenv())
    parser = argparse.ArgumentParser(prog="run_agent", description="Runs the congress bot")
    parser.add_argument("-d", "--db_path", type=str, default=".chroma", help="location of the database")
    parser.add_argument("-t", "--temperature", type=float, default=1.0, help="model's temperature")
    parser.add_argument("-v", "--verbose", action="store_true", help="log the commands that are run")
    args = parser.parse_args()
    a = agent.CongressAgent(temperature=args.temperature, db_path=args.db_path, verbose=args.verbose)
    a.run()

if __name__ == "__main__":
    run()
