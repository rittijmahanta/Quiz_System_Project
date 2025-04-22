from AutoQuiz import main

# qg = main.QGen()


from AutoQuiz.main import AnswerPredictor

qe = main.BoolQGen()
qg = main.QGen()
ans = AnswerPredictor()

def generate_mcqs(input_text, num_questions=4):  # default remains 4
    payload = {
        "input_text": input_text,
        "max_questions": num_questions
    }
    result = qg.predict_mcq(payload)
    return result.get("questions", [])

def generate_bool(text, max_qs=4):
    return qe.predict_boolq({"input_text": text, "max_questions": max_qs})["Boolean Questions"]

def generate_faq(text, max_qs=4):
    return qg.predict_shortq({"input_text": text, "max_questions": max_qs})["questions"]

def generate_paraphrase(text, max_qs=3):
    return qg.paraphrase({"input_text": text})["Paraphrased Questions"]

def generate_answers(text, questions):
    return ans.predict_answer({"input_text": text, "input_question": questions})