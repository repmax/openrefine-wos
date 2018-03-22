"""
#===============================================
Splitting up a Web of Science dump file into several interlinked files

Starting point:
 A: Bunch of wos dump files
 B: A single wos dump file (UTF-16LE)
 B: Cleaned up file from Openrefine. (UTF-8) (*Preferred. Cleaning up is better managed in Openrefine)    

Created: Feb 2018
Modified: Feb 2018
#===============================================
"""

# importing transformation schema file
import numpy as np
import pandas as pd
import re
import os

# Set env variables
os.chdir("c:/_dev/prj-bib/tb")
schema_file = 'D:/o-analytics/codebook/_rep_recipe/gist_wos_split_scheme.tsv'
readPath = r'C:\_dev\prj-bib\tb'

## A: load multiple files
all_files = os.listdir(readPath)
dfd = pd.concat((pd.read_csv(open(f,encoding='UTF-16LE'),sep='\t', index_col=False, skipinitialspace=True, quoting=3) for f in all_files), ignore_index=True) # works! Perfect.

## B: load single file
dfd = pd.read_csv(open(r'b_mdrtb_base.tsv',encoding='UTF-8'),sep='\t', index_col=False) # UTF-8 for Openrefine output, Dump is UTF-16LE

## Load schema
dfs = pd.read_csv(schema_file,sep='\t')

# Change titles
dfw = dfs[['wos','standard']][dfs["wos"].notnull()] # only selected relevant columns

// dfd.rename(columns={'OA': 'tester', 'HP': 'test2'}, inplace=True) # how to rename by direct annotation

dfd = dfd[dfw['wos']] # remove all columns which are not in list
dfd = dfd.rename(columns=dict(zip(dfw[dfw.columns[0]],dfw[dfw.columns[1]]))) # rename

# OPTIONAL: check health of dataframe

dfd_error = dfd[dfd['au-full'].isnull() | dfd['au-short'].isnull()]

# Create 'pub-uid' and 'pub-nid' NB: Error may occur.
dfd['pub-uid'] =  [re.sub(r'[^a-zA-Z0-9.]','_',row['doi'] if pd.notnull(row['doi']) else 'pub-0000'[0:8-len(str(index))]+str(index) for index, row in dfd.iterrows()]
dfd['pub-nid'] = [re.sub(r'[^a-zA-Z ]','',str(x.split(";")[0])).upper() + " " + str(y) + " " + z for x,y,z in zip(dfd['au-short'],dfd['year'],dfd['jrn-short'])]

# Export slices
batchList = ['pub','jrn-prn','au-affil','cit','txt','fund'] # the names of the columns that contain information about slicing

for x in batchList:
  dfs_out = dfs['standard'][dfs[x].notnull()] # list of relevant columns
  dfd_out = dfd[dfs_out] # extract only relevant columns to new dataframe
  dfd_out.to_csv('b_mdrtb_' + x + '.tsv', header=True, index=None, mode='a', sep='\t') # write tab-delimited file

# DONE