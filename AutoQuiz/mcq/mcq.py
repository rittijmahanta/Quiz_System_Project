import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import time
import torch
from transformers import T5ForConditionalGeneration,T5Tokenizer
import random
import spacy
import zipfile
import os
import json
from sense2vec import Sense2Vec
import requests
from collections import OrderedDict
import string
import pke
import nltk
from nltk import FreqDist
nltk.download('brown')
nltk.download('stopwords')
nltk.download('popular')
from nltk.corpus import stopwords
from nltk.corpus import brown
from similarity.normalized_levenshtein import NormalizedLevenshtein
from nltk.tokenize import sent_tokenize
from flashtext import KeywordProcessor



def MCQs_available(word, s2v):
    word = word.replace(" ", "_")
    # Try the exact match first
    if s2v.get_best_sense(word):
        return True
    # Try lowercase version
    if s2v.get_best_sense(word.lower()):
        return True
    # Try without punctuation
    clean_word = word.translate(str.maketrans('', '', string.punctuation))
    if clean_word != word and s2v.get_best_sense(clean_word):
        return True
    return False


def edits(word):
    "All edits that are one edit away from `word`."
    letters    = 'abcdefghijklmnopqrstuvwxyz '+string.punctuation
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def sense2vec_get_words(word,s2v):
    output = []

    word_preprocessed =  word.translate(word.maketrans("","", string.punctuation))
    word_preprocessed = word_preprocessed.lower()

    word_edits = edits(word_preprocessed)

    word = word.replace(" ", "_")

    sense = s2v.get_best_sense(word)
    most_similar = s2v.most_similar(sense, n=15)

    compare_list = [word_preprocessed]
    for each_word in most_similar:
        append_word = each_word[0].split("|")[0].replace("_", " ")
        append_word = append_word.strip()
        append_word_processed = append_word.lower()
        append_word_processed = append_word_processed.translate(append_word_processed.maketrans("","", string.punctuation))
        if append_word_processed not in compare_list and word_preprocessed not in append_word_processed and append_word_processed not in word_edits:
            output.append(append_word.title())
            compare_list.append(append_word_processed)


    out = list(OrderedDict.fromkeys(output))

    return out

# def get_options(answer,s2v):
#     distractors =[]

#     try:
#         distractors = sense2vec_get_words(answer,s2v)
#         if len(distractors) > 0:
#             print(" Sense2vec_distractors successful for word : ", answer)
#             return distractors,"sense2vec"
#     except:
#         print (" Sense2vec_distractors failed for word : ",answer)


#     return distractors,"None"

def get_options(answer, s2v):
    distractors = []
    source = "sense2vec"
    
    # Try sense2vec first
    try:
        distractors = sense2vec_get_words(answer, s2v)
        if not distractors:
            source = "None"
    except:
        source = "None"
    
    # Fallback: If no distractors, generate some simple variations
    if not distractors:
        distractors = [
            answer + " (incorrect)",
            "Not " + answer,
            "Alternative " + answer,
        ]
        source = "fallback"
    
    return distractors, source

def tokenize_sentences(text):
    sentences = [sent_tokenize(text)]
    sentences = [y for x in sentences for y in x]
    # Remove any short sentences less than 20 letters.
    sentences = [sentence.strip() for sentence in sentences if len(sentence) > 20]
    return sentences


def get_sentences_for_keyword(keywords, sentences):
    keyword_processor = KeywordProcessor()
    keyword_sentences = {}
    for word in keywords:
        word = word.strip()
        keyword_sentences[word] = []
        keyword_processor.add_keyword(word)
    for sentence in sentences:
        keywords_found = keyword_processor.extract_keywords(sentence)
        for key in keywords_found:
            keyword_sentences[key].append(sentence)

    for key in keyword_sentences.keys():
        values = keyword_sentences[key]
        values = sorted(values, key=len, reverse=True)
        keyword_sentences[key] = values

    delete_keys = []
    for k in keyword_sentences.keys():
        if len(keyword_sentences[k]) == 0:
            delete_keys.append(k)
    for del_key in delete_keys:
        del keyword_sentences[del_key]

    return keyword_sentences


def is_far(words_list,currentword,thresh,normalized_levenshtein):
    threshold = thresh
    score_list =[]
    for word in words_list:
        score_list.append(normalized_levenshtein.distance(word.lower(),currentword.lower()))
    if min(score_list)>=threshold:
        return True
    else:
        return False

def filter_phrases(phrase_keys,max,normalized_levenshtein ):
    filtered_phrases =[]
    if len(phrase_keys)>0:
        filtered_phrases.append(phrase_keys[0])
        for ph in phrase_keys[1:]:
            if is_far(filtered_phrases,ph,0.7,normalized_levenshtein ):
                filtered_phrases.append(ph)
            if len(filtered_phrases)>=max:
                break
    return filtered_phrases


def get_nouns_multipartite(text):
    out = []

    extractor = pke.unsupervised.MultipartiteRank()
    extractor.load_document(input=text, language='en')
    pos = {'PROPN', 'NOUN'}
    stoplist = list(string.punctuation)
    stoplist += stopwords.words('english')
    extractor.candidate_selection(pos=pos)
    # 4. build the Multipartite graph and rank candidates using random walk,
    #    alpha controls the weight adjustment mechanism, see TopicRank for
    #    threshold/method parameters.
    try:
        extractor.candidate_weighting(alpha=1.1,
                                      threshold=0.75,
                                      method='average')
    except:
        return out

    keyphrases = extractor.get_n_best(n=10)

    for key in keyphrases:
        out.append(key[0])

    return out


def get_phrases(doc):
    phrases={}
    for np in doc.noun_chunks:
        phrase =np.text
        len_phrase = len(phrase.split())
        if len_phrase > 1:
            if phrase not in phrases:
                phrases[phrase]=1
            else:
                phrases[phrase]=phrases[phrase]+1

    phrase_keys=list(phrases.keys())
    phrase_keys = sorted(phrase_keys, key= lambda x: len(x),reverse=True)
    phrase_keys=phrase_keys[:50]
    return phrase_keys



# def get_keywords(nlp,text,max_keywords,s2v,fdist,normalized_levenshtein,no_of_sentences):
#     doc = nlp(text)
#     max_keywords = int(max_keywords)

#     keywords = get_nouns_multipartite(text)
#     keywords = sorted(keywords, key=lambda x: fdist[x])
#     keywords = filter_phrases(keywords, max_keywords,normalized_levenshtein )

#     phrase_keys = get_phrases(doc)
#     filtered_phrases = filter_phrases(phrase_keys, max_keywords,normalized_levenshtein )

#     total_phrases = keywords + filtered_phrases

#     total_phrases_filtered = filter_phrases(total_phrases, min(max_keywords, 2*no_of_sentences),normalized_levenshtein )


#     answers = []
#     for answer in total_phrases_filtered:
#         if answer not in answers and MCQs_available(answer,s2v):
#             answers.append(answer)

#     answers = answers[:max_keywords]
#     return answers

# def get_keywords(nlp, text, max_keywords, s2v, fdist, normalized_levenshtein, no_of_sentences):
#     doc = nlp(text)
#     max_keywords = int(max_keywords)

#     # Get more candidates than needed to account for filtering
#     keyword_candidates = get_nouns_multipartite(text) or []
#     phrase_candidates = get_phrases(doc) or []
    
#     # Combine and deduplicate
#     all_candidates = list(OrderedDict.fromkeys(keyword_candidates + phrase_candidates))
    
#     # Sort by frequency and length
#     all_candidates.sort(key=lambda x: (fdist.get(x, 0), len(x)), reverse=True)
    
#     # Less aggressive filtering
#     filtered_candidates = filter_phrases(all_candidates, max_keywords*3, normalized_levenshtein)
    
#     # Get MCQs-available answers
#     answers = []
#     for candidate in filtered_candidates:
#         if MCQs_available(candidate, s2v):
#             answers.append(candidate)
#             if len(answers) >= max_keywords:
#                 break
                
#     return answers[:max_keywords]


def get_keywords(nlp, text, max_keywords, s2v, fdist, normalized_levenshtein, no_of_sentences):
    doc = nlp(text)
    max_keywords = int(max_keywords)
    
    # Step 1: Get all possible candidates (nouns, phrases)
    keyword_candidates = get_nouns_multipartite(text) or []
    phrase_candidates = get_phrases(doc) or []
    
    # Combine and deduplicate
    all_candidates = list(OrderedDict.fromkeys(keyword_candidates + phrase_candidates))
    
    # Sort by importance (frequency + length)
    all_candidates.sort(key=lambda x: (fdist.get(x, 0), len(x)), reverse=True)
    
    # Step 2: First pass - Try to get MCQs_available keywords
    answers = []
    for candidate in all_candidates:
        if MCQs_available(candidate, s2v):
            answers.append(candidate)
            if len(answers) >= max_keywords:
                return answers[:max_keywords]
    
    # Step 3: Fallback - If not enough, include some even if not in sense2vec
    remaining_needed = max_keywords - len(answers)
    if remaining_needed > 0:
        for candidate in all_candidates:
            if candidate not in answers:
                answers.append(candidate)
                remaining_needed -= 1
                if remaining_needed == 0:
                    break
    
    return answers[:max_keywords]


# def generate_questions_mcq(keyword_sent_mapping,device,tokenizer,model,sense2vec,normalized_levenshtein):
#     batch_text = []
#     answers = keyword_sent_mapping.keys()
#     for answer in answers:
#         txt = keyword_sent_mapping[answer]
#         context = "context: " + txt
#         text = context + " " + "answer: " + answer + " </s>"
#         batch_text.append(text)

#     encoding = tokenizer.batch_encode_plus(batch_text, pad_to_max_length=True, return_tensors="pt")


#     print ("Running model for generation")
#     input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

#     with torch.no_grad():
#         outs = model.generate(input_ids=input_ids,
#                               attention_mask=attention_masks,
#                               max_length=150)

#     output_array ={}
#     output_array["questions"] =[]
# #     print(outs)
#     for index, val in enumerate(answers):
#         individual_question ={}
#         out = outs[index, :]
#         dec = tokenizer.decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)

#         Question = dec.replace("question:", "")
#         Question = Question.strip()
#         individual_question["question_statement"] = Question
#         individual_question["question_type"] = "MCQ"
#         individual_question["answer"] = val
#         individual_question["id"] = index+1
#         individual_question["options"], individual_question["options_algorithm"] = get_options(val, sense2vec)

#         individual_question["options"] =  filter_phrases(individual_question["options"], 10,normalized_levenshtein)
#         index = 3
#         individual_question["extra_options"]= individual_question["options"][index:]
#         individual_question["options"] = individual_question["options"][:index]
#         individual_question["context"] = keyword_sent_mapping[val]
     
#         if len(individual_question["options"])>0:
#             output_array["questions"].append(individual_question)

#     return output_array


def generate_questions_mcq(keyword_sent_mapping, device, tokenizer, model, sense2vec, normalized_levenshtein, max_questions=None):
    batch_text = []
    answers = list(keyword_sent_mapping.keys())
    
    # Ensure we have enough answers (pad if necessary)
    if max_questions and len(answers) < max_questions:
        # If not enough keywords, reuse some (or modify logic to generate more)
        answers += answers[:max_questions - len(answers)]
    
    for answer in answers:
        txt = keyword_sent_mapping[answer]
        context = "context: " + txt
        text = context + " " + "answer: " + answer + " </s>"
        batch_text.append(text)

    encoding = tokenizer.batch_encode_plus(batch_text, pad_to_max_length=True, return_tensors="pt")
    
    input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

    with torch.no_grad():
        outs = model.generate(input_ids=input_ids, attention_mask=attention_masks, max_length=150)

    output_array = {"questions": []}
    
    for index, val in enumerate(answers[:max_questions] if max_questions else answers):
        individual_question = {
            "question_statement": tokenizer.decode(outs[index], skip_special_tokens=True).replace("question:", "").strip(),
            "question_type": "MCQ",
            "answer": val,
            "id": index + 1,
            "context": keyword_sent_mapping[val],
        }
        
        # Get options (force at least 1 option if possible)
        options, algo = get_options(val, sense2vec)
        options = filter_phrases(options, 10, normalized_levenshtein)
        
        # If no options, add a dummy one to ensure question is kept
        if not options:
            options = ["None"]  # Or generate synthetic options
        
        individual_question["options"] = options[:3]  # First 3 as main options
        individual_question["extra_options"] = options[3:]
        individual_question["options_algorithm"] = algo
        
        output_array["questions"].append(individual_question)
    
    return output_array

def generate_normal_questions(keyword_sent_mapping,device,tokenizer,model):  #for normal one word questions
    batch_text = []
    answers = keyword_sent_mapping.keys()
    for answer in answers:
        txt = keyword_sent_mapping[answer]
        context = "context: " + txt
        text = context + " " + "answer: " + answer + " </s>"
        batch_text.append(text)

    encoding = tokenizer.batch_encode_plus(batch_text, pad_to_max_length=True, return_tensors="pt")


    print ("Running model for generation")
    input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

    with torch.no_grad():
        outs = model.generate(input_ids=input_ids,
                              attention_mask=attention_masks,
                              max_length=150)

    output_array ={}
    output_array["questions"] =[]
    
    for index, val in enumerate(answers):
        individual_quest= {}
        out = outs[index, :]
        dec = tokenizer.decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        
        Question= dec.replace('question:', '')
        Question= Question.strip()

        individual_quest['Question']= Question
        individual_quest['Answer']= val
        individual_quest["id"] = index+1
        individual_quest["context"] = keyword_sent_mapping[val]
        
        output_array["questions"].append(individual_quest)
        
    return output_array

def random_choice():
    a = random.choice([0,1])
    return bool(a)
    
