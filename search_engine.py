import os
import json
from search_engine_utils import *
import math
from langdetect import detect, detect_langs

class SearchEngine:

    def __init__(self):
        
        self.folder_name = "webpages"

        self.has_indices = False

        self.inverted_index = None
        self.forward_index = None

        # document x word -> tfidf of word inside document
        self.tfidf_index = None

        # document -> language code (from langdetect)
        self.lang_index = None

        try:

            self.build_indices()

            self.has_indices = True

        except:
            pass

    def get_urls(self, search_string, lang_code="en"):

        if not self.has_indices:
            return []
        
        # Convert search string to lowercase and split it
        words = search_string.lower().split()

        # Set to store the union of document IDs
        document_ids = set()

        # Loop over the words to find their document IDs and union them
        for word in words:
            if word in self.inverted_index:
                document_ids = document_ids.union(set(self.inverted_index[word]))

        return self.get_ordered_results(document_ids=document_ids, search_words=words, lang_code=lang_code)
    
    def get_ordered_results(self, document_ids, search_words, lang_code="en"):
        
        results = []

        # Create a dictionary to keep track of the count of search words in each document
        word_count_per_doc = {}

        # Get the words in the search query
        search_words_set = set(search_words)

        for doc_id in document_ids:
            if doc_id in self.forward_index:
                # Initialize word count for this document
                word_count = 0

                # Iterate through each word in the search query
                for word in search_words_set:
                    # Check if the word exists in the forward index for this document
                    if word in self.forward_index[doc_id]:
                        # Increment the word count for this document
                        word_count += 1

                # Store the word count for this document
                word_count_per_doc[doc_id] = word_count

        def get_word_positions(doc_id):
            return [self.forward_index[doc_id][word] for word in search_words_set if word in self.forward_index[doc_id]]
        
        def get_tfidf_sum(tfidf_index, search_words, doc_id):
            # Initialize the sum of TF-IDF scores
            tfidf_sum = 0.0
            
            # Check if the document ID exists in the TF-IDF index
            if doc_id in tfidf_index:
                # Iterate over the search words
                for word in search_words:
                    # Check if the word exists in the TF-IDF dictionary for the document
                    if word in tfidf_index[doc_id]:
                        # Add the TF-IDF score of the word to the sum
                        tfidf_sum += tfidf_index[doc_id][word]
            
            return tfidf_sum
        
        def get_language_matching_score(doc_id, lang_code, lang_index):
            
            # language and probability
            lang_obj = lang_index[doc_id]

            if lang_obj["language"] == lang_code:
                return lang_obj["prob"]
            
            # show english results if we don't find anything in the preferred language
            elif lang_obj["language"] == "en":
                return lang_obj["prob"] * 0.5
            
            # rank results as low as possible
            return 0

        def custom_key(doc_id):
            return (
                -word_count_per_doc.get(doc_id, 0),  # First criterion: word count 
                -get_language_matching_score(doc_id, lang_code=lang_code, lang_index=self.lang_index),
                -get_tfidf_sum(self.tfidf_index, search_words_set, doc_id),
                get_minimal_position_variance(get_word_positions(doc_id))
            )
        
        def get_snippet_text(doc_id, search_words_set):
            positions = set()
            f_value = self.forward_index[doc_id]

            for word in search_words_set:
                if word in f_value.keys():
                    positions = positions.union(f_value[word])

            positions = list(positions)

            snippet_size = 20

            snipped_starts = group_positions(positions, snippet_size)

            full_text = build_string_from_dict(f_value)

            full_words = list(filter(lambda l: len(l) > 0, full_text.split(" ")))

            individual_snippets = []

            for start in snipped_starts:
                individual_snippets.append(" ".join(full_words[start:start + snippet_size]))

            print(individual_snippets)
            
            return "...".join(individual_snippets)

        # Sort document IDs based on the word count in descending order
        sorted_doc_ids = sorted(document_ids, key=custom_key)

        # Create results based on the sorted document IDs
        for doc_id in sorted_doc_ids:
            doc_info = self.index.get(f"{doc_id}.txt", {})
            if doc_info:
                # Extract words contained in the document
                contained_words = [word for word in search_words_set if word in self.forward_index.get(doc_id, {})]

                position_variance = get_minimal_position_variance(get_word_positions(doc_id))
                tfidf_sum = get_tfidf_sum(self.tfidf_index, search_words_set, doc_id)
                language = self.lang_index[doc_id]

                language_matching_score = get_language_matching_score(doc_id, lang_code=lang_code, lang_index=self.lang_index)

                snipped_text = get_snippet_text(doc_id, search_words_set)

                results.append({"url": doc_info.get("url", ""), "date": doc_info.get("date", ""), "contains": contained_words, "tfidf_sum": tfidf_sum, "position_variance": position_variance, "language": language,
                                "lang_matching_score": language_matching_score,
                                "snippet": snipped_text})

        return results

    def build_inverted_index(self):
        inverted_index = {}
        
        for filename in os.listdir(self.folder_name):
            if filename.endswith(".txt"):
                # Extracting the document ID from the filename (e.g., '123.txt' -> 123)
                doc_id = int(filename.split('.')[0])
                
                with open(os.path.join(self.folder_name, filename), 'r', encoding='utf-8') as file:
                    words = file.read().split()
                    words = [word.lower() for word in words if word]  # Filter out empty strings

                    for word in words:
                        if word not in inverted_index:
                            inverted_index[word] = set()
                        if doc_id not in inverted_index[word]:
                            inverted_index[word].add(doc_id)

        return inverted_index
    
    def build_forward_index(self):
        forward_index = {}

        for filename in os.listdir(self.folder_name):
            if filename.endswith(".txt"):
                # Extracting the document ID from the filename (e.g., '123.txt' -> 123)
                doc_id = int(filename.split('.')[0])

                with open(os.path.join(self.folder_name, filename), 'r', encoding='utf-8') as file:
                    words = file.read().split()
                    words = [word.lower() for word in words if word]  # Filter out empty strings

                    # Initialize the document's entry in the forward index
                    forward_index[doc_id] = {}

                    for position, word in enumerate(words):
                        if word not in forward_index[doc_id]:
                            forward_index[doc_id][word] = []
                        forward_index[doc_id][word].append(position)

        return forward_index
    
    def get_tfidf(self, n_word, n_words_in_doc, n_docs_total, n_docs_with_word):
        
        # how relevant inside the document
        term_frequency = n_word / n_words_in_doc

        # how relevant compared to other documents
        document_frequency = n_docs_with_word / n_docs_total

        idf = 1 / document_frequency

        return term_frequency * math.log(idf)
    
    def build_lang_index(self):
        
        lang_index = {}

        for doc_id, words_and_positions in self.forward_index.items():

            words_in_document = list(words_and_positions.keys())

            words_as_text = " ".join(words_in_document)

            try:
                lang = detect_langs(words_as_text)[0]
                language_dict = {"language": lang.lang, "prob": lang.prob}
            except:
                language_dict = {"language": "unknown", "prob": 1.0}

            lang_index[doc_id] = language_dict

        return lang_index
    
    def build_tfidf_index(self):

        tfidf_index = {}

        n_docs_total = len(self.forward_index.keys())

        for doc_id, words_and_positions in self.forward_index.items():

            n_words_in_doc = sum(list(map(lambda l: len(l), words_and_positions.values())))

            tfidf_index[doc_id] = {}

            for word, positions in words_and_positions.items():
                
                n_word = len(positions)

                n_docs_with_word = len(self.inverted_index[word])

                tfidf_index[doc_id][word] = self.get_tfidf(n_word=n_word, n_words_in_doc=n_words_in_doc, n_docs_total=n_docs_total, n_docs_with_word=n_docs_with_word)

        return tfidf_index
    
    def build_indices(self):
        self.inverted_index = self.build_inverted_index()
        self.forward_index = self.build_forward_index()

        # the forward and the inverted index need to exist for this to work
        self.tfidf_index = self.build_tfidf_index()
        self.lang_index = self.build_lang_index()

        with open(f"{self.folder_name}/index.json", 'r', encoding='utf-8') as file:
                self.index = json.load(file)

        self.has_indices = True