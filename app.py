import os
import json
import requests # For making HTTP requests to Knack API
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv # For local development

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

app = Flask(__name__)

# Configure CORS: Allow requests from your Knack domain
# In a production environment, you might want to be more specific
# with origins, methods, and headers.
CORS(app, resources={r"/api/*": {"origins": "https://vespaacademy.knack.com"}})

# Knack API Configuration (retrieve from environment variables)
KNACK_APP_ID = os.environ.get('KNACK_APP_ID')
KNACK_API_KEY = os.environ.get('KNACK_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') # For later use

KNACK_BASE_URL = f"https://api.knack.com/v1/objects"

@app.route('/')
def index():
    return "Hello from the VESPA Dashboard Backend!"

@app.route('/api/knack-data', methods=['GET'])
def get_knack_data():
    object_key = request.args.get('objectKey')
    filters_param = request.args.get('filters') # This will be a JSON string

    if not object_key:
        return jsonify({"error": "Missing objectKey parameter"}), 400
    if not KNACK_APP_ID or not KNACK_API_KEY:
        return jsonify({"error": "Knack API credentials not configured on the server."}), 500

    headers = {
        'X-Knack-Application-Id': KNACK_APP_ID,
        'X-Knack-REST-API-Key': KNACK_API_KEY,
        'Content-Type': 'application/json' # Though for GET, this might not be strictly needed by Knack
    }
    
    knack_api_url = f"{KNACK_BASE_URL}/{object_key}/records"
    
    # Add filters if provided
    query_params = {}
    if filters_param:
        try:
            # Knack API expects filters as a URL-encoded JSON string
            # The frontend is already sending it URL-encoded.
            # Here, we just pass it along.
            # If you needed to parse and rebuild, you'd do:
            # filters_list = json.loads(filters_param)
            # query_params['filters'] = json.dumps(filters_list)
            query_params['filters'] = filters_param # Assuming it's already correctly formatted from client
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid filters format. Must be a JSON string."}), 400
            
    # Add rows_per_page to get more than the default 25 records if needed
    # Knack's default is 25, max is 1000 per request.
    # You might need to implement pagination if you expect more than 1000 records.
    query_params['rows_per_page'] = '1000' 

    try:
        response = requests.get(knack_api_url, headers=headers, params=query_params)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        # Knack returns data in a structure like {"records": [...]}
        return jsonify(response.json())
        
    except requests.exceptions.HTTPError as http_err:
        return jsonify({
            "error": "HTTP error occurred when calling Knack API",
            "details": str(http_err),
            "knack_response_text": response.text if response else "No response"
        }), response.status_code if response else 500
    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": "Request exception occurred", "details": str(req_err)}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/api/interrogation-questions', methods=['GET'])
def get_interrogation_questions():
    try:
        # Ensure 'Question Level Analysis - Interrogation Questions.txt' is in the same directory
        # or provide the correct path.
        with open('Question Level Analysis - Interrogation Questions.txt', 'r') as f:
            questions = [line.strip() for line in f if line.strip()]
        return jsonify(questions)
    except FileNotFoundError:
        return jsonify({"error": "Interrogation questions file not found."}), 404
    except Exception as e:
        return jsonify({"error": "Error reading questions file", "details": str(e)}), 500

# Placeholder for QLA Chat - to be implemented
@app.route('/api/qla-chat', methods=['POST'])
def qla_chat():
    # This endpoint will receive a query and data, then interact with OpenAI
    # For now, just a placeholder
    if not OPENAI_API_KEY:
        return jsonify({"error": "OpenAI API Key not configured on the server."}), 500
        
    data = request.json
    user_query = data.get('query')
    # question_data_context = data.get('questionData') # You'll use this later

    if not user_query:
        return jsonify({"error": "No query provided for AI chat."}), 400

    # TODO: Implement OpenAI API call logic here
    # Example (very basic, you'll need to format prompts correctly):
    # response_from_openai = openai.Completion.create(engine="davinci", prompt=user_query, max_tokens=150)
    # ai_answer = response_from_openai.choices[0].text.strip()
    
    ai_answer = f"Placeholder AI response to: {user_query}. (Full AI integration pending.)"
    
    return jsonify({"answer": ai_answer})


if __name__ == '__main__':
    # Port is dynamically set by Heroku. For local, Flask default is 5000.
    port = int(os.environ.get('PORT', 5000)) 
    app.run(host='0.0.0.0', port=port, debug=True) # debug=True for development
