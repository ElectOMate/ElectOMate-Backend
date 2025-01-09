import random

def get_random_party_scores(user_answers):
    """
    Step-by-step chain of thought for how we want to implement this:
    
    1) We receive the user_answers in the exact format requested. (We do NOT modify it.)
    2) We define a fixed list of parties, each with short_name, full_name, and partyInfo.
    3) For each party, we generate a random integer score between 0 and 100.
    4) We attach that random score to each party.
    5) We sort the list of parties by the generated score in descending order.
    6) We return the transformed list of parties (same fields, just new order and random scores).
    
    We do NOT change the user's input, nor do we alter the key structure of the output.
    The only changes in the output are the random scores and reordering of the parties.
    """
    parties = [
        {
            "score": 0,
            "short_name": "SPD",
            "full_name": "Sozialdemokratische Partei Deutschlands",
            "partyInfo": "The SPD is a social-democratic party advocating for social justice, welfare state expansion, and pro-EU policies."
        },
        {
            "score": 0,
            "short_name": "GRUENE",
            "full_name": "BÜNDNIS 90/DIE GRÜNEN",
            "partyInfo": "The Greens prioritize environmental protection, social justice, human rights, and grassroots democracy."
        },
        {
            "score": 0,
            "short_name": "FDP",
            "full_name": "Freie Demokratische Partei",
            "partyInfo": "The FDP is a liberal party focusing on free markets, individual rights, lower taxes, and pro-business policies."
        },
        {
            "score": 0,
            "short_name": "CDU/CSU",
            "full_name": "Christlich Demokratische Union Deutschlands",
            "partyInfo": "The CDU/CSU is a center-right political alliance with a focus on social market economy, European integration, and conservative values."
        },
        {
            "score": 0,
            "short_name": "LINKE",
            "full_name": "DIE LINKE",
            "partyInfo": "DIE LINKE is a left-wing party emphasizing anti-capitalism, social equality, wealth redistribution, and pacifism."
        },
        {
            "score": 0,
            "short_name": "AFD",
            "full_name": "Alternative für Deutschland",
            "partyInfo": "The AfD is a right-wing populist party, critical of the EU and immigration, with a focus on national sovereignty."
        }
    ]

    # Generate random scores for each party
    for party in parties:
        party["score"] = random.randint(0, 100)

    # Sort parties by score descending
    parties_sorted = sorted(parties, key=lambda x: x["score"], reverse=True)

    # Return the newly sorted and scored list
    return parties_sorted