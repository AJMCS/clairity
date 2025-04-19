from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os
from dotenv import load_dotenv
from letta_client import Letta, MessageCreate, TextContent
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
load_dotenv()

# Initialize Letta client
letta_client = Letta(
    token=os.getenv('LETTA_API_KEY')  # Remove base_url to use default API endpoint
)

# Store agent ID for use in messages
AGENT_ID = os.getenv('LETTA_AGENT_ID')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Check if request has JSON data
        if not request.is_json:
            return jsonify({
                'message': 'Request must be JSON',
                'status': 'error'
            }), 400

        # Get message from request
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'message': 'No message provided',
                'status': 'error'
            }), 400

        user_message = data['message']
        logger.debug(f"Received message: {user_message}")
        logger.debug(f"Using agent ID: {AGENT_ID}")
        
        def generate():
            # Send message to Letta agent and get streaming response
            response = letta_client.agents.messages.create_stream(
                agent_id=AGENT_ID,
                messages=[
                    MessageCreate(
                        role="user",
                        content=[
                            TextContent(
                                text=user_message,
                            )
                        ],
                    )
                ],
            )
            
            for chunk in response:
                if chunk:
                    yield f"data: {json.dumps({'message': str(chunk), 'status': 'success'})}\n\n"
            
            yield "data: [DONE]\n\n"
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'message': f"Error: {str(e)}",
            'status': 'error'
        }), 500

if __name__ == '__main__':
    # Check if templates directory exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
        logger.info("Created templates directory")
    
    app.run(debug=True) 