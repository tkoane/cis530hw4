== Code to get topic signatures ==

The idea of topic words for summarization was introduced by 

C. Lin and E. Hovy. 2000. The automated acquisition
of topic signatures for text summarization. In Proceedings
of the 18th conference on Computational linguistics.

A topic word is a word with significantly greater probability in
a given text compared to that in a large background corpus. For 
each word in the text, the ratio between two hypotheses (a) 
and (b) is computed.

a) The word is not a topic word and so its probability would be the
same in both the given text and the background collection
b) The word is a topic word and hence its probability in the
given text is greater 

This ratio lambda is estimated and -2 * log(lamda) has a chisq 
distribution. So a cutoff can be chosen based on some significance
level and words obtained in this manner are called topic signatures.

Topic signatures are a very useful feature for content selection from
source documents in summarization.

This code computes topic words for a given document or a set of documents
considered as a whole using a background corpus of 5000 documents from 
the English GigaWord Corpus. 


== INSTALLING ==

Unzip TopicWords-v1.tar.gz 
   gunzip < TopicWords-v1.tar.gz | tar xvf -

The folder TopicWords-v1 contains the java source and class files. 



== SPECIFYING TEXTS AND CUTOFF ==

The texts for which topic words must be computed and the cutoff must be
specified in the config file. 

See the format of TopicWords-v1/config.example.

bgCounts.txt contains word counts obtained using a set of 5000 documents    
     from GigaWord corpus. 

stoplist-smart-sys.txt contains a list of frequently used words from the
     SMART information retrieval system.

Either the stems of words or the actual forms themselves can be obtained
as topic words. When "performStemming=Y" option is used in the config file,
the background corpus list will be stemmed and compared with stems from
the given documents to identify topic words. Porter stemmer is used. 

All stopwords will be removed. The background corpus was also stripped
of the same list of words before computing frequency counts. 

-2*log(lamda) has a chisq distribution, therefore a cutoff on the chisq
values can be used to obtain words with significantly high likelihood of
being topic words. This cutoff must be specified
with the option "topicWordCutoff". Only those words exceeding this cutoff
will be returned as topic signatures. The default is 10.0 which 
corresponds to a significance level of 0.001. 


The list of files for which topic words must be computed needs to be
specified with the "inputFile=[absolute_path_to_file]", one line for
each file. If topic words are required for a set of documents taken 
as a whole, for example, a multi-document summarization input, the path
to the folder containing these files must be specified with this option. 
The sample run contains one such example. 


== EXAMPLE RUN ==

cd into the TopicWords-v1 directory. A sample set of parameters are in config.example.
 
Example texts to compute topic words for are in the sampleTexts directory. These contain
newswire documents taken from the Newsblaster system archives 
(http://newsblaster.cs.columbia.edu/). 

The paths to some of these files are 
specified in the config file with the inputFile parameter. One of 
the runs is path to the folder "sampleTexts/input-cluster1"
which will produce the topic words for the set of documents under that folder
taken as a whole. The remaining runs in config.example correspond to single files.

java -Xmx1000m TopicSignatures config.example 


The input and output paths are specified with inputDir and outputFile, respectively.
