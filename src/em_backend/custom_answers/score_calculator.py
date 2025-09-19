from typing import Any

class UserAnswer:
    def __init__(self, users_answer: int, wheights: str, Skipped: str, custom_answer: str):
        self.users_answer = users_answer
        self.wheights = wheights.lower() == "true"
        self.skipped = Skipped.lower() == "true"
        self.custom_answer = custom_answer

class PartyResult:
    def __init__(self, short_name: str, score: float, full_name: str, partyInfo: str):
        self.short_name = short_name
        self.score = score
        self.full_name = full_name
        self.partyInfo = partyInfo

    def to_dict(self):
        return {
            "short_name": self.short_name,
            "score": self.score,
            "full_name": self.full_name,
            "partyInfo": self.partyInfo
        }

def build_party_answers_matrix(questions_data: dict[str, Any], party_abbreviations: list[str]) -> list[list[int]]:
    matrix = []
    for question in questions_data["questions"]:
        positions = question["positions"]
        row = []
        for party in party_abbreviations:
            if party in positions.get("pro", {}).get("parties", {}):
                row.append(1)
            elif party in positions.get("contra", {}).get("parties", {}):
                row.append(-1)
            else:
                row.append(0)
        matrix.append(row)
    return matrix

def calculate_standard_scores(answers: list[UserAnswer], questions_data: dict[str, Any]) -> list[PartyResult]:
    # Filter out questions with custom answers
    standard_answers = [a for a in answers if not a.custom_answer.strip()]
    if not standard_answers:
        return []

    # Get party abbreviations and full names
    party_abbreviations = list(questions_data["parties"].keys())
    party_full_names = [questions_data["parties"][abbr]["full_name"] for abbr in party_abbreviations]
    party_info = [questions_data["parties"][abbr]["partyInfo"] for abbr in party_abbreviations]

    # Build matrices
    party_matrix = build_party_answers_matrix(questions_data, party_abbreviations)
    user_answers = [int(a.users_answer) for a in standard_answers]
    user_weights = [a.wheights for a in standard_answers]
    user_skipped = [a.skipped for a in standard_answers]

    # Build difference matrix
    diff_matrix = []
    for q, _ in enumerate(standard_answers):
        diff_row = []
        for j, _ in enumerate(party_abbreviations):
            diff = abs(user_answers[q] - party_matrix[q][j])
            diff_row.append(diff)
        diff_matrix.append(diff_row)

    # Apply weights and skips
    counter_weighted = 0
    counter_skipped = 0
    adjusted_matrix = []
    for q, _ in enumerate(standard_answers):
        factor = 1
        if user_skipped[q]:
            factor = 0
            counter_skipped += 1
        elif user_weights[q]:
            factor = 2
            counter_weighted += 1
            
        adjusted_row = [-1 * (diff - 2) * factor for diff in diff_matrix[q]]
        adjusted_matrix.append(adjusted_row)

    # Compute scores
    column_sums = [sum(col) for col in zip(*adjusted_matrix)]
    denominator = len(standard_answers) * 2 + 2 * counter_weighted - 2 * counter_skipped

    # Ensure denominator is not zero
    if denominator == 0:
        return [PartyResult(abbr, 0.0, full_name, info) for abbr, full_name, info in zip(party_abbreviations, party_full_names, party_info)]

    final_scores = [round((sum_col / denominator) * 100, 2) for sum_col in column_sums]

    # Create results
    results = []
    for i, abbr in enumerate(party_abbreviations):
        results.append(PartyResult(
            short_name=abbr,
            score=final_scores[i],
            full_name=party_full_names[i],
            partyInfo=party_info[i]
        ))

    # Sort descending
    results.sort(key=lambda x: x.score, reverse=True)
    return results

def combine_results(standard_results: list[PartyResult], custom_results: list[dict]) -> list[dict]:
    combined = {}
    
    # Add standard results
    for result in standard_results:
        combined[result.short_name] = result.to_dict()
    
    # Add/merge custom results
    for custom in custom_results:
        short_name = custom["short_name"]
        if short_name in combined:
            combined[short_name]["score"] += custom["score"]
        else:
            combined[short_name] = custom
    
    # Convert to sorted list
    sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results