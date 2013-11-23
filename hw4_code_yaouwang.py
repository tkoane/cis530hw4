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
        if isnoun(word):
            synsets = wn.synsets(word, pos=wn.NOUN)
            depth = synsets[0].min_depth()
            for synset in synsets:
                if synset.min_depth() < depth:
                    depth = synset.min_depth()
            dictionary[word] = depth
    dictionary = sorted(dictionary.items(), key=lambda x: x[1], reverse=True)
    ret = []
    for i in range(n):
        ret.append(dictionary[i][0])
    return ret

def get_least_specific(n, word_list):
    dictionary = dict()
    for word in word_list:
        if isnoun(word):
            synsets = wn.synsets(word, pos=wn.NOUN)
            depth = synsets[0].min_depth()
            for synset in synsets:
                if synset.min_depth() > depth:
                    depth = synset.min_depth()
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
        mapping[word] = len(wn.synsets(word, pos=pos))

    return [i[0] for i in sorted(mapping.items(), key=lambda x: x[1], reverse=True)]

def get_most_polysemous(n, word_list, part_of_speech):
    return get_polysemous(n, word_list, part_of_speech)[:n]

def get_least_polysemous(n, word_list, part_of_speech):
    return list(reversed(get_polysemous(n, word_list, part_of_speech)))[:n]

def get_context(word, tok_sents):
    context = set()
    for sent in tok_sents:
        if word in tok_sents:
            context.extend(sent)
    return context - set(stopwords.words('english'))

def main():
    #type1 = load_topic_words('type1.ts')
    #type2 = load_topic_words('type2.ts')
    #type1_list = get_top_n_topic_words(type1, 20)
    #type2_list = get_top_n_topic_words(type2, 20)
    #print is_noun('chess')
    #print get_similarity('operation', 'find')
    #print get_all_pairs_similarity(['settlement', 'camp', 'base', 'country'])
    #type1_list = remove_elements(type1_list)
    #type2_list = remove_elements(type2_list)
    #1.3.3 running get_all_pairs_similarity on the top 20 words for each topic
    #print get_all_pairs_similarity(type1_list)
    #print get_all_pairs_similarity(type2_list)
    #create_graphviz_file(gen_topic_edges(type1_list, 0.25), 'type1.viz')
    #create_graphviz_file(gen_topic_edges(type2_list, 0.25), 'type2.viz')
    word_list = load_collection_words('data_type1/')
    print get_most_polysemous(25, word_list, 'verb')
    print get_least_polysemous(15, word_list, 'adjective')
    
if __name__ == "__main__":
    main()
