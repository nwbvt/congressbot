import argparse
import db

def run():
    parser = argparse.ArgumentParser(prog="load_db", description="Loads the db to be used by congress bot")
    parser.add_argument("-l", "--location", type=str, default=".chroma", help="location of the database")
    parser.add_argument("-c", "--congress", type=int, default=119, help="congress to load")
    args = parser.parse_args()
    db.load(args.location, args.congress)


if __name__ == "__main__":
    run()

