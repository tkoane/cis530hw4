import java.util.LinkedList;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.Hashtable;
import java.io.File;
import java.util.Enumeration;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.text.DecimalFormat;

   /**
    * To obtain the loglikelihood ratio values to compute Topic words as in
    * Lin and Hovy 2000.
    * @author Annie Louis
    */
public class TopicSignatures{
	
    LinkedList<String> stopWords = new LinkedList<String>(); //this list will be empty throughout if stopword=N option is specified
    vocabDist backgroundDist;
    boolean stemOption;
   
    /** 
     * Reads in any info files provided 
     * <br> 1. stopword list
     * <br> 2. file with frequency counts of words from a large background corpus (to use for computing topic signatures)
     * <br><br> If stopwords must not be filtered, then the string must be empty "". 
     */
    public TopicSignatures(String stopWordFile, String bgFrequencyFile, boolean stem) throws java.io.IOException, java.io.FileNotFoundException
    {
	stemOption = stem;  //if true, then all vocabulary distributions--input, background files are stemmed.
	if(!stopWordFile.equals(""))
	    {
		System.out.println("Reading stopwords from \""+stopWordFile+"\"");
		readStopWords(stopWordFile);
	    }
	if(!bgFrequencyFile.equals(""))
	    {
		System.out.println("Reading background corpus frequency counts from \""+bgFrequencyFile+"\"");
		readBackgroundCorpus(bgFrequencyFile);
	    }
    }
    


    /**
     * Read the stopwords from file into a list
     */
    public void readStopWords(String filepath) throws java.io.IOException, java.io.FileNotFoundException 
    {
	File stpfile = new File(filepath);
	if(!stpfile.exists())
	    error("Stopword file not found: "+filepath);
	BufferedReader br = new BufferedReader(new FileReader(filepath));
	String line;
	while ((line = br.readLine()) != null) {
	    if(line.trim().equals(""))
	       continue;
	    stopWords.add(line.trim().toLowerCase());
	}
    }
	
   
    /**
     * Reads the background corpus frequency counts from file 
     */
    public void readBackgroundCorpus(String filepath) throws java.io.IOException, java.io.FileNotFoundException
    {
	File bgfile = new File(filepath);
	if(!bgfile.exists())
	    error("Backgound frequency file not found: "+filepath);
	BufferedReader br = new BufferedReader(new FileReader(filepath));
	String line;

	int totalTokens = 0;
	LinkedList<String> words = new LinkedList<String>();
	LinkedList<Integer> freqs = new LinkedList<Integer>();
	while((line = br.readLine()) != null) 
	    {
		//System.out.println(line);
		String toks[] = line.trim().split("[ \t]+");	
                String wd = toks[0].toLowerCase();
		if(stopWords.contains(wd))
		    continue;
		int freq = Integer.parseInt(toks[1]);
		totalTokens += freq;
		if(stemOption)
		    wd = Stemmer.stem(wd);
		
		//update frequency if word already in list else add as new
		int indInVocab = words.indexOf(wd);
		if(indInVocab == -1)
		    {
			words.add(wd);
			freqs.add(freq);
		    }
		else
		    {
			int cur = freqs.get(indInVocab);
			freqs.set(indInVocab, cur+freq);
		    }
	    }
	//System.out.println("Total tokens: "+ totalTokens);
	//System.out.println("Bgwords "+words.get(0)+" "+words.get(1)+" "+words.get(2));
	//create aggregated vocabulary dist. Only one entry per stem with frequencies totalled over all words adding to the same stem.
	backgroundDist = new vocabDist(words, freqs, totalTokens);

	// //check if background counts are okay
// 	BufferedWriter bgcnts = new BufferedWriter(new FileWriter("bgFreqCounts"));
// 	bgcnts.write((new Integer(backgroundDist.numTokens)).toString());
// 	for(int d = 0 ; d < backgroundDist.vocabWords.size(); d++)
// 	    {
// 		bgcnts.write(backgroundDist.vocabWords.get(d)+" "+backgroundDist.vocabFreq.get(d));
// 		bgcnts.newLine();
// 	    }
// 	bgcnts.close();
    }



    /**
     * Given a path to a plaintext file (summary or single document input) or multiple files (multidocument input), computes the vocabulary
     * distribution--unique words and and their counts overall in the file/files.
     */ 
    public vocabDist computeVocabulary(String path) throws java.io.IOException, java.io.FileNotFoundException
    {
	File fp = new File(path);
	if(!fp.exists())
	    error("Cannot compute vocabulary for : non-existent file path : "+path);
	Hashtable<String, Integer> counts = new Hashtable<String, Integer>();
	if(fp.isDirectory())
	    {
		String files[] = fp.list();
		for(int f = 0; f < files.length; f++)
		    {
			BufferedReader brf = new BufferedReader(new FileReader(path+File.separator+files[f]));
			String fline;
			while((fline = brf.readLine())!=null)
			    {
				if(fline.trim().equals(""))
				    continue;
				fline = fline.replaceAll("[^A-Za-z ]", " ");
				String toks[] = fline.trim().split("[ ]+");
				for(int t = 0; t < toks.length; t++)
				    updateCounts(toks[t].toLowerCase(), counts);
			    }
		    }
	    }
	else
	    {
		BufferedReader bx = new BufferedReader(new FileReader(path));
		String ll;
		while((ll = bx.readLine())!=null)
		    {
			if(ll.trim().equals(""))
			    continue;
			ll =ll.replaceAll("[^a-zA-Z ]", " ");
			String tks[] = ll.trim().split("[ ]+");
			for(int tk = 0 ; tk < tks.length; tk++)
			    updateCounts(tks[tk].toLowerCase(), counts);
		    }
	    }
	LinkedList<String> words = new LinkedList<String>();
	LinkedList<Integer> freq = new LinkedList<Integer>();
	int totalToks = 0;
	Enumeration em = counts.keys();
	while(em.hasMoreElements())
	    {
		String wd = (String)em.nextElement();
		int fr = counts.get(wd);
		words.add(wd);
		freq.add(fr);
		totalToks += fr;
	    }
	//System.out.println("Input : "+words.get(0)+" "+words.get(1)+" "+words.get(2));
	return new vocabDist(words, freq, totalToks);
    }

    /**
     * Given a new token updates the frequency count of that word in the vocabulary distribution
     */
    public void updateCounts(String word, Hashtable<String, Integer> currCounts)
    {
	if(stopWords.contains(word))
	    return;
	if(stemOption)
	    word = Stemmer.stem(word);
	if(word.trim().equals(""))
	    return;
	if(currCounts.containsKey(word))
	    {
		int cur = currCounts.get(word);
		currCounts.put(word, cur+1);
	    }
	else
	    currCounts.put(word, 1);
    }


	
    /**
     * Given a set of words and frequency counts, this function computes the 
     * loglikelihood ratios in comparison with the background corpus supplied.
     * Returns a list of loglikelihood ratios corresponding to each of
     * the words in the given vocabulary distribution.
     */
   public LinkedList<Double> computeLogLikelihoodRatio(vocabDist dist)
    { 
    	LinkedList<Double> chisqValues = new LinkedList<Double>();
    	for(int i =0 ; i< dist.vocabWords.size(); i++)
	    {
	    	double wfreq = dist.vocabFreq.get(i);
	    	int bgIndex = backgroundDist.vocabWords.indexOf(dist.vocabWords.get(i));
	    	double bgfreq;
	    	if(bgIndex == -1)
		    bgfreq = 0.0;
	    	else
		    bgfreq = backgroundDist.vocabFreq.get(bgIndex);
    		double o11 = wfreq;
	    	double o12 = bgfreq;
	        double o21 = (double)dist.numTokens - wfreq;
	        double o22 = (double)backgroundDist.numTokens - bgfreq;
	        double N = o11 + o12 + o21 + o22;
	        double p = (o11 + o12) / N;
	        double p1 = o11 / (o11 + o21);
	        double p2 = o12 / (o12 + o22);
	        double t1, t2, t3, t4, t5, t6;
	        if(p == 0)
	        	t1 = 0.0;
	        else
	        	t1 = Math.log10(p) * (o11 + o12);
	        if(p == 1)
	        	t2 = 0.0;
	        else
	        	t2 = (o21+o22) * Math.log10(1 - p);
	        
	        if(p1 == 0)
	        	t3 = 0.0;
	        else
	        	t3 = o11 * Math.log10(p1);
	        if(p1 == 1)
	        	t4 = 0.0;
	        else
	        	t4 = o21 * Math.log10(1-p1);
	        	
	        if(p2 == 0)
	        	t5 = 0.0;
	        else
	        	t5 = o12 * Math.log10(p2);
	        if(p2 == 1)
	        	t6 = 0.0;
	        else
	        	t6 = o22 * Math.log10(1-p2);
	        
	        double loglik = -2.0 * (t1+ t2 - (t3 + t4 + t5 + t6));
		chisqValues.add(loglik);
	    }
       return chisqValues;
    }


    /**
     * Print error and exit. 
     */	
    public static void error(String msg)
    {
	System.out.println("Error - CorpusBasedUtilities.java\n\n"+msg+"\n\n");
	Runtime cur = Runtime.getRuntime();
	cur.exit(1);
    }


    public static void main(String args[]) throws java.io.IOException, java.io.FileNotFoundException
    {
	if(args.length != 1)
	    error("One argument - configFile.txt");
	String configFile = args[0];
	if(!(new File(configFile)).exists())
	    error("Config file not found: "+ configFile);
	
	// Read configuration options as provided in config file argument to main function
	BufferedReader bcr = new BufferedReader(new FileReader(configFile));
	String cline;
	String stopFile = "", bgFile ="";
	LinkedList<String> inputFiles = new LinkedList<String>();
	//by default stopwords are removed but no stemming is done. A cutoff of 10.0 is used.
        // stopwords will always be removed because the background corpus has no stopwords
	double topicCutoff = 0.1;
	boolean performStemming = false;
	
	// Alex - Added
	String inputDir = "", outputFile = "";
	
	while((cline = bcr.readLine())!=null)
	    {
		cline = cline.trim();
		if(cline.equals(""))
		    continue;
		if(cline.startsWith("-"))
		    continue;
		if(cline.startsWith("="))
		    continue;
		cline = cline.replaceAll(" ","");
		String clineToks[] = cline.split("[=]");
		if(clineToks[0].equals("performStemming"))
		    {
			if(clineToks[1].equalsIgnoreCase("y"))
			    performStemming = true;
		    }
		if(clineToks[0].equals("backgroundCorpusFreqCounts"))
		    bgFile = clineToks[1];
		if(clineToks[0].equals("stopFilePath"))
		    stopFile = clineToks[1];
		// Alex - Don't use
		if(clineToks[0].equals("inputFile"))
		    inputFiles.add(clineToks[1]);
		if(clineToks[0].toLowerCase().equals("topicwordcutoff"))
		    topicCutoff = Double.parseDouble(clineToks[1]);

		// Alex - Added
		if(clineToks[0].equals("outputFile"))
		    outputFile = clineToks[1];
		if(clineToks[0].equals("inputDir"))
		    inputDir = clineToks[1];
	    }
	if(stopFile.equals(""))
		    error("Error in config file: must specify file with stopwords");				
	
	if(bgFile.equals(""))
	    error("Error in config file: must specify file with background corpus counts to compute topic word based features");		

	TopicSignatures ts = new TopicSignatures(stopFile, bgFile, performStemming);
	System.out.println("Computing topic words ...");
	
	DecimalFormat myFormatter = new DecimalFormat("0.####");
	/*
	  Alex - Made for single directory
	for(int i = 0; i < inputFiles.size(); i++)
	    {
		String curFile = inputFiles.get(i);
	*/
	        String curFile = inputDir;
		System.out.println("Processing " + curFile + " ...");
		vocabDist idist = ts.computeVocabulary(curFile);
		LinkedList<Double> chisqValues = ts.computeLogLikelihoodRatio(idist);
		System.out.println("Writing to " + outputFile + " ...");
		BufferedWriter bw = new BufferedWriter(new FileWriter(outputFile));
		for(int c = 0; c < idist.vocabWords.size(); c++)
		    {
			if(chisqValues.get(c) >= topicCutoff)
			    {
				bw.write(idist.vocabWords.get(c)+" "+myFormatter.format(chisqValues.get(c)));
				bw.newLine();
			    }
		    }
		bw.close();
	/*
	    }
	*/
	System.out.println("done");
    }
	
}