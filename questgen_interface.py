from AutoQuiz import main

qg = main.QGen()

def generate_mcqs(input_text, num_questions=4):  # default remains 4
    payload = {
        "input_text": input_text,
        "max_questions": num_questions
    }
    result = qg.predict_mcq(payload)
    return result.get("questions", [])
