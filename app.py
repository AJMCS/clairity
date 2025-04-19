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
    token=os.getenv('LETTA_API_KEY')
)

# Store agent ID for use in messages
AGENT_ID = os.getenv('LETTA_AGENT_ID')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    try:
        # Get message from request
        if request.method == 'GET':
            user_message = request.args.get('message', '')
        else:
            if not request.is_json:
                return jsonify({
                    'message': 'Request must be JSON',
                    'status': 'error'
                }), 400
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({
                    'message': 'No message provided',
                    'status': 'error'
                }), 400
            user_message = data['message']

        if not user_message:
            return jsonify({
                'message': 'No message provided',
                'status': 'error'
            }), 400

        logger.debug(f"Received message: {user_message}")
        logger.debug(f"Using agent ID: {AGENT_ID}")
        
        def generate():
            try:
                # Send message to Letta agent and get streaming response
                logger.debug("Starting streaming response from Letta")
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
                        logger.debug(f"Received chunk: {chunk}")
                        # Handle different types of responses
                        if hasattr(chunk, 'message_type'):
                            if chunk.message_type == 'assistant_message':
                                # Extract the content from the response
                                content = getattr(chunk, 'content', '')
                                if content:
                                    logger.debug(f"Sending content to client: {content}")
                                    yield f"data: {json.dumps({'message': content, 'status': 'success'})}\n\n"
                            elif chunk.message_type == 'usage_statistics':
                                # Skip usage statistics
                                continue
                        else:
                            # Fallback for other response types
                            content = str(chunk)
                            logger.debug(f"Sending fallback content to client: {content}")
                            yield f"data: {json.dumps({'message': content, 'status': 'success'})}\n\n"
                
                logger.debug("Streaming complete")
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'message': f'Error: {str(e)}', 'status': 'error'})}\n\n"
        
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