import json

def extract_and_print_questions(json_file_path: str):
    # Load the JSON data from the file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract and print questions
    questions = data.get('questions', [])
    for question in questions:
        question_id = question.get('id')
        question_text = question.get('q')
        print(f"Question {question_id}: {question_text}")

if __name__ == "__main__":
    # Specify the path to your JSON file
    json_file_path = 'app/custom_answer_evaluation/Partyanswers copy.json'
    extract_and_print_questions(json_file_path) 