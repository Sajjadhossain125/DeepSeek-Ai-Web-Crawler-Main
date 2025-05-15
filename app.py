from flask import Flask, render_template, jsonify, send_file, Response, request
import asyncio
from queue import Queue
from threading import Thread
from dotenv import load_dotenv

from utils.scraper_utils import (
    start_scraping_job,
    log_queue
)
from utils.data_utils import save_venues_to_csv

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Cache for venues
cached_venues = []


# ----------- Log Stream for SSE -----------
@app.route("/log-stream")
def log_stream():
    def event_stream():
        while True:
            msg = log_queue.get()
            yield f"data: {msg}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")


# ----------- Logging Helper -----------
def log(msg):
    print(msg)
    log_queue.put(msg)


# ----------- Home Page -----------
@app.route('/')
def index():
    return render_template('index.html')


# ----------- User-Based Scraping Route -----------
@app.route('/scrape', methods=['POST'])
def scrape_from_user():
    try:
        data = request.get_json()

        base_url = data.get("base_url")
        css_selector = data.get("css_selector")
        required_keys = data.get("required_keys")
        raw_max_pages = data.get("max_pages", 10)

        # Handle dynamic typing for max_pages
        if isinstance(raw_max_pages, dict):
            max_pages = int(raw_max_pages.get("value", 10))
        else:
            max_pages = int(raw_max_pages)

        # Validate required fields
        if not all([base_url, css_selector, required_keys]):
            return jsonify({"error": "Missing base_url, css_selector, or required_keys"}), 400

        log(f"[START] Scraping started for URL: {base_url} (up to {max_pages} pages)")

        # Run the scraper async job
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        venues = loop.run_until_complete(
            start_scraping_job(
                base_url=base_url,
                css_selector=css_selector,
                required_keys=required_keys,
                max_pages=max_pages 
            )
        )

        if venues:
            save_venues_to_csv(venues, "complete_venues.csv")
            log(f"[SAVE] Saved {len(venues)} venues to complete_venues.csv")

        return jsonify(venues)
    
    except Exception as e:
        log(f"[ERROR] {str(e)}")
        return jsonify({"error": "An error occurred during scraping", "details": str(e)}), 500



# ----------- Download CSV Route -----------
@app.route('/download', methods=['GET'])
def download_csv():
    return send_file('complete_venues.csv', as_attachment=True)


# ----------- Run Flask Server -----------
if __name__ == '__main__':
    app.run(debug=True, threaded=True)
