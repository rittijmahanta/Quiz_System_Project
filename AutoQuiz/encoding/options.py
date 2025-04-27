import google.generativeai as genai
import json

# Configure Gemini
api_key = 'AIzaSyAiDrJ2Gee2TL9o5iZOxCFwp_FiTM4owfs'  # You may want to move this to a .env file for security!
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
            "You are an expert MCQ setter. Improve these MCQ questions and options. "
            "Fix grammar, make distractors realistic, and ensure clarity. "
            "Return ONLY a JSON array of dicts with keys: 'question', 'options', 'answer'.\n\n"
        ),
        'bool': (
            "You are an expert at writing True/False questions. Improve clarity and correctness. "
            "Return ONLY a JSON array of dicts with keys: 'question' and 'answer' (True/False).\n\n"
        ),
        'faq': (
            "You are an expert FAQ editor. Improve the quality of these question-answer pairs. "
            "Return ONLY a JSON array of dicts with keys: 'question' and 'answer'.\n\n"
        ),
    }

    prompt = prompts.get(method)
    if not prompt:
        return questions

    full_prompt = prompt + json.dumps(questions, indent=2)

    try:
        response = model.generate_content(full_prompt)
        if hasattr(response, 'text') and response.text:
            cleaned_text = response.text.strip().strip('```json').strip('```').strip()
            return json.loads(cleaned_text)
        else:
            return questions
    except Exception as e:
        print(f"Error refining questions with Gemini: {e}")
        return questions
