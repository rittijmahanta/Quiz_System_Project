import random

def arrange_options(questions, method):
    if not questions or method not in ['mcq', 'yes/no', 'faq']:
        return questions

    updated_questions = []

    for q in questions:
        question_text = q.get('question')
        answer = q.get('answer')

        if method == 'faq':
            # Do nothing for FAQ
            updated_questions.append(q)
            continue

        if method == 'yes/no':
            # Yes/No type - simple True/False options
            options = ['Yes', 'No']
            correct_answer = 'Yes' if str(answer).lower() in ['yes', 'true', '1'] else 'No'
        else:  # mcq
            options = q.get('options', [])
            # Make sure the answer is
