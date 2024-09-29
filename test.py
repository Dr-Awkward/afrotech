from google.cloud import firestore
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_dialogflow_webhook():
    # Initialize Firestore DB
    db = firestore.Client()
    
    # Parse the incoming request
    req = request.get_json(silent=True, force=True)
    
    # Extract user information from parameters
    user_info = req['queryResult']['parameters']
    
    # Save user information to Firestore
    db.collection('transcript').add(user_info)

    # Send a response back to Dialogflow
    return jsonify({"fulfillmentText": "Thank you! Your information has been saved."})

# For local testing (optional)
if __name__ == '__main__':
    app.run(debug=True)
