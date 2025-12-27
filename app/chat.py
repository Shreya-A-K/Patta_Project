from flask import Blueprint, request, jsonify, current_app
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

@chat_bp.route('/ask', methods=['POST'])
def ask_gemini():
    """Citizen asks Gemini about Patta verification"""
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    try:
        # Patta-specific system prompt
        system_prompt = """
        You are PattaBot, expert in Tamil Nadu land records verification.
        Help citizens with:
        - Patta verification process
        - Required documents
        - Status checking
        - Boundary disputes
        - Revenue department contacts
        
        Always respond in simple Tamil/English mix.
        Be helpful, accurate, and official.
        """
        
        response = model.generate_content([system_prompt, question])
        answer = response.text
        
        return jsonify({
            'question': question,
            'answer': answer,
            'timestamp': current_app.db.collection('chat_logs').add({
                'question': question,
                'answer': answer,
                'user_role': 'citizen'
            })[1].id
        })
    
    except Exception as e:
        return jsonify({'error': 'Chat service unavailable', 'details': str(e)}), 503

@chat_bp.route('/history', methods=['GET'])
def chat_history():
    """Get chat history"""
    from flask import current_app
    chats = current_app.db.collection('chat_logs').order_by('timestamp').limit(20).stream()
    return jsonify([chat.to_dict() for chat in chats])
