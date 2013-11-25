# David Zbarsky: dzbarsky@wharton.upenn.edu
# Yaou Wang: yaouwang@wharton.upenn.edu

from nltk.corpus import PlaintextCorpusReader
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
import math
import string
import random
import fileinput
import os
import itertools
import subprocess
import xml.etree.ElementTree as ET

'''
homework 4 by David Zbarsky and Yaou Wang
'''


#from hw1: functions for translating files/directory into tokens
def get_all_files(directory):
    # We assume that a filename with a . is always a file rather than a directory
    # IF we were passed a file, just return that file.  This simplifies representing documents because they need to handle single files.
    if directory.find('.') < 0:
        return PlaintextCorpusReader(directory, '.*').fileids()
    #if directory is a file return the file in a list
    return [directory]

def load_file_sentences(filepath):
    index = filepath.rfind('/')
    if index < 0:
        sents = sent_tokenize(PlaintextCorpusReader('.', filepath).raw().lower())
    else:
        sents = sent_tokenize(PlaintextCorpusReader(filepath[:index], filepath[index+1:]).raw().lower())
    return sents

def load_file_tokens(filepath):
    tokens = []
    for sentence in load_file_sentences(filepath):
        tokens.extend(word_tokenize(sentence))
    return tokens

def load_collection_tokens(directory):
    tokens = []
    for file in get_all_files(directory):
        tokens.extend(load_file_tokens(directory + '/' + file))
    return tokens

def load_collection_words(directory):
    return set(load_collection_tokens(directory))

#end of functions from hw1

def load_topic_words(topic_file):
    tokens = load_file_tokens(topic_file)
    map = dict()
    i = 0
    while i < len(tokens):
        map[tokens[i]] = float(tokens[i+1])
        i = i + 2
    return map

def get_top_n_topic_words(topic_words_dict, n):
    sort = sorted(topic_words_dict.items(), key=lambda x: x[1], reverse=True)
    words = []
    for i in range(n):
        words.append(sort[i][0])
    return words

'''
1.2.2

The top 20 words from data type 1 are:
['news', 'corp', 'stake', 'talks', 'conocophillips', 'interest', 'sale',
 'bid', 'comment', 'reported', 'sources', 'assets', 'reportedly', 'company',
  'media', 'lukoil', 'murdoch', 'aes', 'bids', 'heinz']
  
The top 20 words from data type 2 are:
['amount', 'fixed', 'offering', 'income', 'mm', 'filed', 'corp', 'completed',
 'registration', 'sec', 'aes', 'million', 'declared', 'effective', 'fpl',
  'corporation', 'announced', 'kimberly', 'offered', 'conocophillips']
  
We see that while there are some similar words such as 'corp', 'announced', 
etc., overall they are different. The first one has words like 'assets', 
'bids', and 'talks', while the second one has words like 'income', 
'fixed' and 'amount'.

'''

def is_noun(word):
    return len(wn.synsets(word, pos=wn.NOUN)) > 0

def get_similarity(word1, word2):
    synsets1 = wn.synsets(word1, pos=wn.NOUN)
    synsets2 = wn.synsets(word2, pos=wn.NOUN)
    sim = 0
    for synset1 in synsets1:
        for synset2 in synsets2:
            num = synset1.path_similarity(synset2)
            if num > sim:
                sim = num
    return sim

def get_all_pairs_similarity(word_list):
    ret = []
    for i in range(len(word_list)-1):
        for j in range(i+1, len(word_list)):
            ret.append((word_list[i], word_list[j], get_similarity(word_list[i], word_list[j])))
    return ret

#helper to remove elements that are not nouns in wordnet
def remove_elements(word_list):
    ret = []
    for word in word_list:
        if is_noun(word):
            ret.append(word)
    return ret

def gen_topic_edges(word_list, minimum):
    word_list = remove_elements(word_list)
    ret = []
    for i in range(len(word_list)-1):
        b = True
        for j in range(i+1, len(word_list)):
            if get_similarity(word_list[i], word_list[j]) >= minimum:
                ret.append((word_list[i],word_list[j]))
                b = False
        if b:
            ret.append((word_list[i],))
    return ret

def create_graphviz_file(edge_list, output_file):
    f = open(output_file, 'w')
    f.write('graph G {\n')
    for edge in edge_list:
        if len(edge) == 1:
            f.write(edge[0] + ';\n')
        else:
            f.write(edge[0] + ' -- ' + edge[1] + ';\n')
    f.write('}')
    f.close()

def get_most_specific(n, word_list):
    dictionary = dict()
    for word in word_list:
        if is_noun(word):
            synsets = wn.synsets(word, pos=wn.NOUN)
            depth = synsets[0].min_depth()
            for synset in synsets:
                if synset.min_depth() > depth:
                    depth = synset.min_depth()
            if depth > 1:
                dictionary[word] = depth
    dictionary = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)
    ret = []
    for i in range(n):
        ret.append(dictionary[i][0])
    return ret

def get_least_specific(n, word_list):
    dictionary = dict()
    for word in word_list:
        if is_noun(word):
            synsets = wn.synsets(word, pos=wn.NOUN)
            depth = synsets[0].min_depth()
            for synset in synsets:
                if synset.min_depth() < depth and synset.min_depth() > 1:
                    depth = synset.min_depth()
            if depth > 1: 
                dictionary[word] = depth
    dictionary = sorted(dictionary.items(), key=lambda x: x[1])
    ret = []
    for i in range(n):
        ret.append(dictionary[i][0])
    return ret

def get_polysemous(n, word_list, part_of_speech):
    if part_of_speech == 'noun':
        pos = wn.NOUN
    elif part_of_speech == 'verb':
        pos = wn.VERB
    elif part_of_speech == 'adjective':
        pos = wn.ADJ
    elif part_of_speech == 'adverb':
        pos = wn.ADV

    mapping = dict();
    for word in word_list:
        if len(wn.synsets(word, pos=pos)) > 0:
            mapping[word] = len(wn.synsets(word, pos=pos))

    return [i[0] for i in sorted(mapping.items(), key=lambda x: x[1], reverse=True)]

def get_most_polysemous(n, word_list, part_of_speech):
    return get_polysemous(n, word_list, part_of_speech)[:n]

def get_least_polysemous(n, word_list, part_of_speech):
    return list(reversed(get_polysemous(n, word_list, part_of_speech)))[:n]

#helper to convert sentences into tokenized form
def get_tokenized_sentences(filepath):
    sents = load_file_sentences(filepath)
    ret = []
    for sent in sents:
        ret.append(word_tokenize(sent))
    return ret

def get_context(word, tok_sents):
    context = set()
    for sent in tok_sents:
        if word in sent:
            for tok in sent:
                if word != tok:
                    context.add(tok.lower())
    return context - set(stopwords.words('english'))

def lesk_disambiguate(word, context):
    synsets = wn.synsets(word, pos=wn.NOUN)
    best_sense = synsets[0]
    max_overlap = 0
    best_defn = synsets[0].definition
    for synset in synsets:
        defn = synset.definition
        overlap = len(set(defn).intersection(context))
        if overlap > max_overlap:
            max_overlap = overlap
            best_sense = synset
            best_defn = defn
    return (best_sense, best_defn)

#helper to run the lesk algorithm on a group of files
def run_lesk(directory, word_list):
    for file in get_all_files(directory):
        tok_sents = get_tokenized_sentences(directory + '/' + file)
        for word in word_list:
            context = get_context(word, tok_sents)
            sense, defn = lesk_disambiguate(word, context)
            print (file, word, sense, defn, context)

'''
2.3.3

The lesk algorithm does a decent job at word sense disambiguation.
The performance accuracy of the algorithm, by simply looking through
the 8 different files in the data_wsd folder, is around 70 to 80 percent
(we counted around 2 to 3 wrong senses per 10 occurrences). The reason
why such a crude algorithm can do a good job is that the words in
the definition are frequently mentioned in the context. So when media
is taken to mean a channel of communication, the token 'communication'
is typically in the context. However, the algorithm can easily be improved
if we choose to use hypernyms or synonyms of the definition as well in our
calculation of the overlap.

'''
            
def main():
    #Part 1 test: load topic words
    type1 = load_topic_words('type1.ts')
    type2 = load_topic_words('type2.ts')
    type1_list = get_top_n_topic_words(type1, 20)
    type2_list = get_top_n_topic_words(type2, 20)
    #Test is_noun
    print is_noun('chess')
    #Test similarity functions
    print get_similarity('operation', 'find')
    print get_all_pairs_similarity(['settlement', 'camp', 'base', 'country'])
    type1_list = remove_elements(type1_list)
    type2_list = remove_elements(type2_list)
    #1.3.3 running get_all_pairs_similarity on the top 20 words for each topic
    print get_all_pairs_similarity(type1_list)
    print get_all_pairs_similarity(type2_list)
    #creating the graphviz file
    create_graphviz_file(gen_topic_edges(type1_list, 0.25), 'type1.viz')
    create_graphviz_file(gen_topic_edges(type2_list, 0.25), 'type2.viz')
    #Test specific words
    print get_most_specific(5, type1_list)
    print get_least_specific(5, type1_list)
    #Test polysemous words
    poly_list = get_most_polysemous(5, type1_list, 'noun')
    #Running lesk algorithm
    run_lesk('data_wsd', poly_list)
    
    
if __name__ == "__main__":
    main()
