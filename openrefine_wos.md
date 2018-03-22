# Clean-up of Web of Science dump
NB: OpenRefine can manipulate columns using both GREL and Python programming languages.  

<!-- NB: a macro has been recorded in Notepad++ to transform extracted json command to a minimized format. -->


Filter and reorganise data dump
--------------------------------
### Import raw files into OPENREFINE
- Uncheck quotation marks  
- Choose uft-16LE encoding  

### Remove all other types of content than "articles"
```json
[{"op":"core/row-star","description":"Star rows","engineConfig":{"mode":"row-based","facets":[{"omitError":false,"expression":"value","selectBlank":false,"selection":[{"v":{"v":"Article","l":"Article"}}],"selectError":false,"invert":false,"name":"DT","omitBlank":false,"type":"list","columnName":"DT"}]},"starred":true},  
{"op":"core/row-removal","description":"Remove rows","engineConfig":{"mode":"row-based","facets":[{"omitError":false,"expression":"row.starred","selectBlank":false,"selection":[{"v":{"v":false,"l":"false"}}],"selectError":false,"invert":false,"name":"Starred Rows","omitBlank":false,"type":"list","columnName":""}]}},  
{"op":"core/row-star","description":"Unstar rows","engineConfig":{"mode":"row-based","facets":[]},"starred":false}]
```
### Format columns
- Check selected columns for consistency and error
- Trim all cells! Important for generation of pub_uid/pub_nid
- Transform selected columns with text to number. grel: `value.toNumber()`
- Edit 2x organisation papers without author
- Convert names of months to numbers (Feb > 02). Text transform on cells in column 'month': grel `value.toDate('MMM').toString('M')`

Splitting columns into seperate files
-------------------------------------
A single article contains many different types of data that needs to be reconciled. It is, for example, very common that authors publish articles sometimes with one initial and other times with two initials. Similarily may the same institution or journal have different spellings. Another reason for splitting into several files is that some columns contains multiple values and must therefore be unpacked, before they can be reconsiled.

The python script 'gist_wos_split.py' will perform the following actions:
- Create a unique identifier for each publication 'pub-uid' which is needed to reconcile data after we split it in the following step.
- Delete, rename and export columns according to 'gist_wos_split_scheme.tsv'.

Output:
- au-affil.tsv (author-affiliation)
- cit.tsv (citation)
- fund.tsv (funding)
- jrn-prn.tsv (journal-publisher)
- txt.tsv (title, abstract, keywords)

All spreadsheets contain the 'pub-uid', so they can be reconciled again.

Reconcile Author-Affiliation (au-affil.tsv) 
-------------------------------------
- import 'au-affil.tsv' into openRefine. 

Problem: Many authors has a last name with two parts.  
Solution: Keep comma in 'au-full' and concatenate all intials at the end of 'au-short'.


### Split multi-value cells and remove punctuation.

* Multi-value split 'au-full' and 'au-short' into rows 
* Clean au-short. Uppercase, removes '. '\','\'.' and trim
```grel
value.replace(". ","").replace(".","").replace(",","").trim()
```

### Enforce initials-only on au-short
Problem: Sometimes the firstname appear in full in the 'au-short'.

1. Create a facet for all 'au-short' which has after the first word has more than 3 letters (= initials).

```python
import re
return len(re.split(' ',value,1)[1]) > 2
```
2. Star the ones that need to be shortened. Then filter with the start to apply the following only to starred items.

```python
import re
list = re.split(' ',value,1)
return list[0] +" " + re.sub('\s*([^\s])[^\s]*\s*', '\g<1>' , list[1])
```
Optional: `return re.sub('\s*([^\s])[^\s]*\s*', '\g<1>' , value)` # first letter of all words  
Optional: `return re.split(' ',value,1)[1]` # everything after first space

### Assigning orcid number to author row.
Method: row["record"]... will maintain the record value while iterating through the records rows.  
Assumption: Authors of the an article do not have the same lastname.

```python
import re
orcidRecord = row["record"]['cells']["orcid"]["value"][0]
myvalue = ""
pattern = re.compile(r'[ ]?([^0-9]+)/([0-9-]+[X]?)[;]?')
for (name, num) in re.findall(pattern, orcidRecord):
  if (str(name).split(",")[0].upper().strip() == str(cells["au-full"]["value"].split(",")[0].upper().strip())):
    myvalue = num
return  myvalue
```
### Assign affiliation to author row. Seperate with "|".
Method: With regex pattern create a tuple list. Check lastname occurence in name part and if match add affil to a list. Finally convert list to string.  
NB: sometime '[0]' is need to access value.

```python
import re
record = row["record"]['cells']["au-affil"]["value"][0]
affils = []
pattern = re.compile(r'.?\[([^\]]*)\] ?([^;]+)')
for (name, affil) in re.findall(pattern, record):
    if str(cells["au-full"]["value"].split(",")[0].upper().strip()) in name.upper():
        affils.append(affil)
return "|".join(affils)
```

Tip:  regex:`'.?\[([^\]]*)\] ?([^;]+)'` =>  
[\*Kapata, Nathan; Chanda-Kapata*/] \**Minist Hlth, Dept Control & Res, Lusaka, Zambia**/; [\*Kapata, Nathan; Grobusch*/] \**Univ Amsterdam, Amsterdam, Netherlands**/

### Compressing
- Remove superflous colums (au-affil, orcid)
- Add a row index so first author can be determined.Grel: row.index - row.record.fromRowIndex
- Fill down 'pub-uid'
- Test if any cell contains future delimiters. Grel: `or(contains(value, ";"),contains(value,"|"))`
- Merge 'pub-uid' with 'au-rank'. Custom transform on 'pub-uid'. Grel: `value+"|"+ cells["au-rank"].value`. 
- Delete 'au-rank'.

### Almost unique temporary author id with affil (au-tid) 
Problem: a temporary unique id is needed until items has been reconciled with an authoriative list  
NB: Solution also works if 'affil' cell is empty. Assumes 'au-full' is not empty.

Create column from *generic
```python
import re
list1 = [cells["au-full"]["value"]]
try:
  affil = cells["affil"]["value"].split("|")[0]
  commalist = affil.split(",")
  if len(commalist[0])>1:
    list1.append(commalist[0][:18])
    list1.append(commalist[-1][-15:])
except:
  pass
list2 = ["-".join(re.sub(r'[^a-zA-Z0-9_ ]+','', item).split()) for item in list1]
return "_".join(list2).lower()
```
### Clustering column 'affil'
Challenge: 'affil' is a multi-value cell.  
* Split multi-value cell in column 'affil'
* Create column 'affil-short' from *generic

```python
import re
try:
  affil = cells["affil"]["value"].split("|")[0]
  commalist = affil.split(",")
  list1 = []
  if len(commalist[0])>1:
    list1.append(commalist[0][:18])
    list1.append(commalist[-1][-15:])
    list2 = ["-".join(re.sub(r'[^a-zA-Z0-9_ ]+','', item).split()) for item in list1]
    return "_".join(list2).lower()
except:
  pass
```

* Cluster 'affil-short'. Go through the different clustering algorithms. The result will be that many full name 'affil' get the same 'affil-short'. 
* Create a new column with the same full name ('affil') for identical 'affil-short'. 
* Create column affil-clustered at index 7 based on column affil-short using expression:  
Grel: `cell.cross("b_mdrtb_au affil_tsv","affil-short").cells["affil"]["value"][0]`  
(see: http://kb.refinepro.com/2011/08/vlookup-in-google-refine.html)
* Delete 'affil'/'affil-short'. Rename 'affil-clustered' to 'affil'.
* Join multi-valued cells in column 'affil'.    

### Clustering column 'au-tid'
* Cluster. Step through large collections with `and(row.index>10000, row.index<12100)` as a facet.
* Check that ';' and '@' is not present in pub-uid or affil as we will be using them as seperators.NB use '[' and ']' as demarkes instead.
* Merge affil, pub-uid, au-rank together into 'comp'. Make 'affil' first so first affiliation can easily be extracted.

New column 'pub-uid-au-rank'. Grel: `"[" + cells["pub-uid"].value + "|" + cells["au-rank"].value + "]"`  
New column 'action' (NB: 'affil' may be empty):
```python
mystring = ""
try:
  mystring = cells["affil"]["value"]
except:
  pass
return mystring + cells["pub-uid-au-rank"]["value"]
```

* Delete superflous columns now in 'action' (affil, pub-uid, au-rank, pub-uid-au-rank)
* Blank down au-tid
* join multi-cell 'comp'
* join multi-cell 'orcid'
* join multi-cell 'au-full' and delete all but the longest
* Repeat similar process for orcid to merge cells with same value. This time no clustering needed though, just sort. NB: Order the orcid column with error and blanks first. If not the last orcid value will be the record for all empty orcid rows below.
* Repeat clustering process for 'au-full'. There may still be obvious matches.
* Delete repeats value in multi-value cells. Grel: `join(value.split(";").uniques(),";")` or with a 'trim': `join(forEach(value.split(";"),v,v.trim()).uniques(),";")`
* Create column 'au-full' based on column au-full-aka using expression jython:
`return max(value.split(";"), key=len).strip()`

Import Author-Affilliation into Neo4j
-----------------------------------------

### Convert multi-cell (and spreadsheet) to json
First rearrange the 'action' cell so pub_uid is first. 'affil' needs to be first to easily retrieve information for reconsiliation, but pub-uid is the essential parameter and should be first. Furthermore, "%" is used as delimiter.

Grel: `join(forEach(value.split(";"),v,join(v.split("[").reverse(),"")),";")`  
Grel: `replace(value,"]","%")`

1. Convert column to json. Works when creating new column

```python
import json
taskList = value.split(";")
for x in taskList:
  uid_rank, affilDump = x.split("%",1)
  uid, rank = uid_rank.split("|",1)
  obj = {'pub_uid':uid, 'rank':int(rank)}
  if affilDump:
    obj["affils"]=affilDump.split("|") 
return json.dumps(obj)
```

2. Convert to all to a single Json file. Works in openrefine templating
NB: {} cannot be used within templating. '{{jython" needed to use Python.

Prefix:
```
{"records" : 
  [
```
Main:
```python
{{jython:
import json
record = dict([])
record["author"]=dict([])
record["tasks"]=dict([])

props = [
['au-full',cells["au-full"]["value"]],
['au-full-aka',cells["au-full-aka"]["value"].split(";")],
['au-short',cells["au-short"]["value"]],
['au-short-aka',cells["au-short-aka"]["value"].split(";")]]

try:
  props.append(['orcids',cells["orcid"]["value"].split(";")])
except:
  pass

record["author"]["props"] = dict(props)
cActions = cells["action"]["value"].split(";")
for x in cActions:
 uid_rank_affils = x.split("%",1)
 uid, rank = uid_rank_affils[0].split("|",1)
 record["tasks"]["pub"] = dict([('pub_uid',uid),('rank',int(rank))])
 try:
  record["tasks"]["affils"] = uid_rank_affils[1].split("|")
 except:
  pass
return json.dumps(record)
}}

```
Row seperator:
```
,
```
Suffix:
```
  ]
}
```
### Importing json into neo4j

```sql (cypher)
CALL apoc.load.json("file:///C:/_dev/prj-bib/tb/try_b_mdrtb_au-affil_12.json") YIELD value
UNWIND value.records AS record
FOREACH (r IN record|
  CREATE (t:TASK)
  CREATE (au:Author)
  SET au = r.author.props
  CREATE (au)-[:PERFORMED]->(t)
  CREATE (pu:Pub)
  SET pu.pub_uid = r.tasks.pub.pub_uid
  CREATE (t)-[rel:PRODUCED]->(pu)
  SET rel.rank = r.tasks.pub.rank  
  FOREACH (affil in r.tasks.affils|
    CREATE (af:Affiliation)
    SET af.name = affil
    CREATE (af)-[:HOSTED]->(t)
	)
  )
RETURN record
LIMIT 5
```

Assigned parameters are in the same format as in json.  
Check values with e.g. `MATCH (n:Author {`au-short`:'Farnia P'}) RETURN n.orcids[0]` or `MATCH p = (n:Pub {pub_uid:'10.3109_09273948.2013.874447'})-[]-()-[]-() RETURN p`
