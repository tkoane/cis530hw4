# David Zbarsky: dzbarsky@wharton.upenn.edu
# Yaou Wang: yaouwang@wharton.upenn.edu

from nltk.corpus import PlaintextCorpusReader
from nltk.tokenize import sent_tokenize, word_tokenize
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
#end of functions from hw1

def load_topic_words(topic_file):
    pass

def main():
    pass

if __name__ == "__main__":
    main()
