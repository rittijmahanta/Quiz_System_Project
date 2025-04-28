import google.generativeai as genai
import json

# Configure Gemini
api_key = 'AIzaSyAiDrJ2Gee2TL9o5iZOxCFwp_FiTM4owfs'  # Move to .env for security in production!
genai.configure(api_key=api_key)

# Load the model
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

def arrange_options(questions, method):
    """
    Refine and arrange questions using Google Gemini.

    Args:
        questions (list): List of questions (dict format).
        method (str): 'mcq', 'bool', 'faq'.

    Returns:
        list: Refined questions.
    """
    if not questions:
        return questions

    prompts = {
        'mcq': (
            "You are an expert MCQ setter. Improve these MCQ questions and options but not too much. "
            "Fix grammar, make distractors realistic, and ensure clarity. "
            "Return ONLY a JSON array of dicts with keys: 'question_statement', 'options', 'answer'.\n\n"
        ),
        'bool': (
            "You are an expert at writing True/False questions. Improve clarity and correctness but not too much. "
            "Return ONLY a JSON array of dicts with keys: 'question_statement' , 'answer' .\n\n"
        ),
        'faq': (
            "You are an expert FAQ editor. Improve the quality of these question-answer pairs but not too much. Keep the answers very short "
            "Return ONLY a JSON array of dicts with keys: 'question_statement' and 'answer'.\n\n"
        ),
    }

    prompt = prompts.get(method)
    if not prompt:
        return questions

    full_prompt = prompt + json.dumps(questions, indent=2)

    try:
        response = model.generate_content(full_prompt)

        if hasattr(response, 'text') and response.text:
            cleaned_text = (
                response.text.strip()
                .removeprefix("```json")
                .removesuffix("```")
                .strip()
            )

            refined_questions = json.loads(cleaned_text)

            if method == 'bool':
                for q in refined_questions:
                    if 'question' in q:
                        q['question_statement'] = q.pop('question')
                    if 'answer' in q and not isinstance(q['answer'], bool):
                        q['answer'] = q['answer'].strip().lower() == 'true'

            return refined_questions
        else:
            return questions

    except json.JSONDecodeError:
        return questions

    except Exception:
        return questions
