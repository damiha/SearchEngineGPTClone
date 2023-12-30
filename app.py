from flask import Flask, request, jsonify
from flask_cors import CORS
from webcrawler import WebCrawler  # Import your WebCrawler class
from search_engine import SearchEngine

app = Flask(__name__)
CORS(app)

crawler = None
search_engine = SearchEngine()

@app.route('/crawler/start', methods=['POST'])
def start_crawler():
    global crawler
    if crawler and crawler.is_crawling:
        return jsonify({"message": "Crawler is already running."}), 400

    data = request.json
    start_url = data.get('start_url')
    if not start_url:
        return jsonify({"message": "No start URL provided."}), 400

    crawler = WebCrawler(start_url, uses_threadpool=True)
    crawler.start_crawl()
    return jsonify({"message": "Crawler started."}), 200

@app.route('/search_engine/get_urls', methods=['POST'])
def get_urls():

    data = request.json
    search_string = data.get('search_string')
    if not search_string:
        return jsonify({"message": "No search string provided."}), 400
    
    # english is the default language
    lang_code = data.get("lang_code", "en")

    urls = search_engine.get_urls(search_string, lang_code)
    return jsonify({"message": urls}), 200

@app.route('/crawler/stop', methods=['GET'])
def stop_crawler():
    global crawler
    if not crawler or not crawler.is_crawling:
        return jsonify({"message": "Crawler is not running."}), 400

    crawler.stop()

    # new information added => the indices need to be rebuilt
    search_engine.build_indices()

    return jsonify({"message": "Crawler stopped."}), 200

@app.route('/crawler/info', methods=['GET'])
def get_crawler_info():
    global crawler
    if not crawler:
        return jsonify({"message": "Crawler is not initialized."}), 400

    info = crawler._get_info()
    return jsonify(info), 200

if __name__ == '__main__':
    app.run(debug=True)
