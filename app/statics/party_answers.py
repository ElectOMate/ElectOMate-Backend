from pathlib import Path
import json

party_answers = dict()
file_path = Path(__file__).parent / 'party_answer.json'

def load_party_answers():
    global party_answers
    with file_path.open('r', encoding='utf-8') as f:
        party_answers = json.load(f)