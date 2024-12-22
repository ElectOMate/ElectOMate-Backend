# calculation.py
import json
import numpy as np

party_names = {
    "short_partynames": [
        "CDU / CSU",
        "GRÜNE",
        "SPD",
        "AfD",
        "DIE LINKE",
        "FDP",
        "Die PARTEI",
        "FREIE WÄHLER",
        "Tierschutzpartei",
        "ÖDP",
        "FAMILIE",
        "Volt",
        "PIRATEN",
        "MERA25",
        "HEIMAT",
        "TIERSCHUTZ hier!",
        "PfsV",
        "BIG",
        "Bündnis C",
        "PdH",
        "MENSCHLICHE WELT",
        "DKP",
        "MLPD",
        "SGP",
        "ABG",
        "dieBasis",
        "BÜNDNIS DEUTSCHLAND",
        "BSW",
        "DAVA",
        "KLIMALISTE",
        "LETZTE GENERATION",
        "PDV",
        "PdF",
        "V-Partei³"
    ],
    "party_full_names": [
        "Christlich Demokratische Union Deutschlands / Christlich-Soziale Union in Bayern e.V.",
        "BÜNDNIS 90/DIE GRÜNEN",
        "Sozialdemokratische Partei Deutschlands",
        "Alternative für Deutschland",
        "DIE LINKE",
        "Freie Demokratische Partei",
        "Die PARTEI",
        "FREIE WÄHLER",
        "Tierschutzpartei",
        "Ökologisch-Demokratische Partei",
        "FAMILIE",
        "Volt",
        "PIRATEN",
        "MERA25",
        "HEIMAT",
        "TIERSCHUTZ hier!",
        "Partei für schulmedizinische Verjüngungsforschung",
        "Bündnis für Innovation & Gerechtigkeit",
        "Bündnis C - Christen für Deutschland",
        "Partei der Humanisten",
        "MENSCHLICHE WELT",
        "Deutsche Kommunistische Partei",
        "Marxistisch Leninistische Partei Deutschland",
        "Sozialistische Gleichheitspartei, Vierte Internationale",
        "Aktion Bürger für Gerechtigkeit",
        "dieBasis",
        "BÜNDNIS DEUTSCHLAND",
        "Bündnis Sahra Wagenknecht",
        "Demokratische Allianz für Vielfalt und Aufbruch",
        "KLIMALISTE",
        "LETZTE GENERATION",
        "Partei der Vernunft",
        "Partei des Fortschritts",
        "V-Partei³ - Partei für Veränderung, Vegetarier und Veganer"
    ]
}
     

     
def evaluate_answers(data_Party, data_User):
    num_questions = len(data_User)
    party_names = data_Party['party_names']
    party_full_names = data_Party['party_full_names']
    
    party_names_array = np.array(party_names)
    party_answers = data_Party['party_answers']  # List of dictionaries
    user_answers_matrix = np.zeros((num_questions, 1))
    user_answers_matrix_weights = [0] * num_questions
    user_answers_matrix_skipped = [0] * num_questions

    # Create an array with the User answers in -1,0,1
    for i, item in enumerate(data_User):
        if 'users_answer' in item:
            user_answers_matrix[i] = item['users_answer']
    
    # Create arrays with weights and skipped flags
    for i, item in enumerate(data_User):
        if 'wheights' in item:
            user_answers_matrix_weights[i] = 1 if item['wheights'].lower() == "true" else 0
        if 'Skipped' in item:
            user_answers_matrix_skipped[i] = 1 if item['Skipped'].lower() == "true" else 0

    # Initialize matrices
    num_parties = len(party_names)
    party_answers_matrix = np.zeros((num_questions, num_parties))
    difference_matrix = np.zeros((num_questions, num_parties))

    # Populate party_answers_matrix
    for i, party in enumerate(party_names):
        # Assuming each party has answers for all questions
        for q in range(num_questions):
            key = f"Party_Answer_Q{q+1}"
            party_answers_matrix[q, i] = party_answers[q][key]

    # Calculate the difference matrix
    for i in range(num_questions):
        for j in range(num_parties):
            difference_matrix[i, j] = abs(user_answers_matrix[i] - party_answers_matrix[i, j])
    
    counter_weighted = 0
    counter_skipped = 0
    for i in range(num_questions):
        weights_factor = 1
        if user_answers_matrix_skipped[i] == 1:
            weights_factor = 0
            counter_skipped += 1
        elif user_answers_matrix_weights[i] == 1:
            weights_factor = 2
            counter_weighted += 1
        
        for j in range(num_parties):
            difference_matrix[i, j] = (-1) * (difference_matrix[i, j] - 2) * weights_factor

    column_sums = np.sum(difference_matrix, axis=0)

    # Normalize to percentage
    column_sums = column_sums / (num_questions * 2 + 2 * counter_weighted - 2 * counter_skipped) * 100
    column_sums = np.round(column_sums, 1)

    combined_list = list(zip(column_sums, party_names, party_full_names))
    combined_list.sort(key=lambda x: x[0], reverse=True)

    # Convert to list of dictionaries for JSON serialization
    result = [
        {"score": score, "short_name": short_name, "full_name": full_name}
        for score, short_name, full_name in combined_list
    ]

    return result