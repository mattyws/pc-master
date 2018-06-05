import json
import os
import signal
import atexit
import config
import xml.etree.ElementTree as ET

from textblob import TextBlob


def process_claims(xml_claims):
    claims = []
    for claim in xml_claims.iter('claim'):
        for claimText in claim.iter('claim-text'):
            if claimText.text is not None:
                claims.append(claimText.text.strip().replace('\n', ' '))
    return claims


def process_description(xml_description):
    description = ""
    for p in xml_description.iter("p"):
        if p.text is not None:
            description += p.text.strip().replace('\n', ' ') + '\n'
    return description.strip()


def get_patent_classifications(technicalData):
    classifications = []
    for xml_classification in technicalData.iter('classification-ipcr'):
        classification = dict()
        classification["complete"] = xml_classification.text.replace('\t', ' ').strip()
        classification["section"] = xml_classification.text[0]
        classification["class"] = xml_classification.text[:3]
        classification["subclass"] = xml_classification.text[:4]
        classifications.append(classification)
    return classifications



def get_patent_title(technicalData):
    patent_title = None
    for title in technicalData.iter('invention-title'):
        if title.get('lang').lower() == 'en':
            patent_title = title.text
    return patent_title

def get_consumed_files():
    with open(config.CONSUMED_FILE, 'r') as f:
        return f.read().split('\n')
    return []


max_files_per_batch = 100
A_num = 0
B_num = 0
A_patent_files = []
B_patent_files = []
consumed_files = get_consumed_files()
with open(config.CONSUMED_FILE, 'a', 1) as consumed_file_handler:
    for dir, subdir, files in os.walk(config.CLEF_FILES_PATH):
        if len(A_patent_files) >= max_files_per_batch:
            # Writing batch file
            with open(config.JSON_FILES_PATH_A+'/A-'+str(A_num)+'.json', 'w') as f:
                json.dump(A_patent_files, f)
            A_patent_files = []
            A_num += 1
        if len(B_patent_files) >= max_files_per_batch:
            # Writing batch file
            with open(config.JSON_FILES_PATH_B+'/B-'+str(B_num)+'.json', 'w') as f:
                json.dump(B_patent_files, f)
            B_patent_files = []
            B_num += 1

        if len(files) > 0:
            for file in files:
                if file not in consumed_files:
                    #Adding file to consumed and wrinting to the end of the file
                    consumed_files.append(file)
                    consumed_file_handler.write(file+'\n')
                    #Start xml processing
                    tree = ET.parse(dir+"/"+file)
                    root = tree.getroot()
                    claims = None
                    descriptions = None
                    abstracts = None
                    technicalData = None
                    if len(root.findall('claims')) > 0:
                        claims = root.findall('claims')
                    if len(root.findall('description')) > 0 :
                        descriptions = root.findall('description')
                    if root.find('bibliographic-data').find('technical-data') is not None:
                        technicalData = root.find('bibliographic-data').find('technical-data')
                    if (claims is not None) and (descriptions is not None) and (technicalData is not None):
                        print(file)
                        english_claim = None
                        english_description = None
                        document_technicalData = None
                        # Processing claims
                        for claim in claims:
                            if claim.get('lang').lower() == 'en':
                                english_claim = process_claims(claim)
                                # print(english_claim)
                                if english_claim is not None and len(english_claim) > 0 :

                                    '''
                                    Checking if language is really english. The dataset have some documents using 'en' as language
                                    with text writed in other language (FR or DE). If TextBlob accuse any text to not be writed in english,
                                    discard all claims.
                                    '''
                                    for text in english_claim:
                                        if len(text) > 3:
                                            lang = TextBlob(text).detect_language().lower()
                                            if not lang == 'en':
                                                english_claim = None
                                                break

                        # Processing descriptions
                        for description in descriptions:
                            if description.get('lang').lower() == 'en':
                                english_description = process_description(description)
                                if len(english_description) == 0:
                                    english_description = None
                                else:
                                    '''
                                    Checking if language is really english. The dataset have some documents using 'en' as language
                                    with text writed in other language (FR or DE). If TextBlob accuse any text to not be writed in english,
                                    discard the description.
                                    '''
                                    lang = TextBlob(english_description).detect_language().lower()
                                    if not lang == 'en':
                                        english_description = None

                        classifications = get_patent_classifications(technicalData)
                        title = get_patent_title(technicalData)
                        #Start the dictionary construction
                        if (len(classifications) > 0) and (english_claim is not None) and (english_description is not None):
                            patent = dict()
                            patent['filename'] = file
                            patent['title'] = title
                            patent['description'] = english_description
                            patent['claims'] = english_claim
                            if 'B' in file:
                                print('B File')
                                B_patent_files.append(patent)
                            elif 'A' in file:
                                print('A File')
                                A_patent_files.append(patent)
                else:
                    print("Consumed :" + file)