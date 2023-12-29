import os
import json

class SearchEngine:

    def __init__(self):
        
        self.folder_name = "webpages"

        self.inverted_index = self.build_inverted_index()

        with open(f"{self.folder_name}/index.json", 'r', encoding='utf-8') as file:
            self.index = json.load(file)

    def get_urls(self, search_string):
        # Convert search string to lowercase and split it
        words = search_string.lower().split()

        # Set to store the union of document IDs
        document_ids = set()

        # Loop over the words to find their document IDs and union them
        for word in words:
            if word in self.inverted_index:
                document_ids = document_ids.union(set(self.inverted_index[word]))

        # Map document IDs to URLs and dates
        results = []
        for doc_id in document_ids:
            doc_info = self.index[f"{doc_id}.txt"]
            if doc_info:
                results.append({"url": doc_info["url"], "date": doc_info["date"]})

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