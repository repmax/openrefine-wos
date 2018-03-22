# Processing Web of Science data and importing into Neo4j.
The overall aim is to process bibliographic data from Web of Science and import it into a graph database (Neo4j) to create a single multi-faceted network.

Status: Raw data dump is filtered, formatted and split up into a number of files. One of these files (Author-Affiliation) is fully processed and imported into Neo4j. Similar proceedures needs to be elaborated for remaining data files.

Files: 

- 'openrefine_wos.md' contains explanation and code snippets for openRefine.  

- 'split_wos.py' contains Python code used to split data file into several files  

- 'split-scheme_wos.tsv' contains a table with indication of which columns goes into which files.
