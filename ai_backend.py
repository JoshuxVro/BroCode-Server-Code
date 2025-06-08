from flask import Flask, request, jsonify
from flask_cors import CORS
import groq
import logging
from datetime import datetime
import subprocess
import tempfile
import os



# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
chat_sessions = {}


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client (Replace with actual API key)
client = groq.Client(api_key="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")

# Supported languages
SUPPORTED_LANGUAGES = {
    "python3": {"extension": ".py", "command": ["C:\\Users\\joshu\\AppData\\Local\\Programs\\Python\\Python310\\python.exe"]},
    "javascript": {"extension": ".js", "command": ["node"]},
    "cpp": {"extension": ".cpp", "command": ["g++", "./a.out"]}
}

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/completion', methods=['POST'])
def get_completion():
    data = request.get_json()
    code = data.get('currentCode', '')
    language = data.get('language', '')
    prompt = data.get('prompt', '')

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    messages = [
        {"role": "system", "content": "Provide high-quality code completion."},
        {"role": "user", "content": f"Code:\n```{language}\n{code}\n```\n{prompt}"}
    ]
    
    chat_completion = client.chat.completions.create(
        messages=messages, model="mixtral-8x7b-32768", temperature=0.7, max_tokens=2000
    )
    return jsonify({"completion": chat_completion.choices[0].message.content})

@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', '')
    
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    lang_config = SUPPORTED_LANGUAGES[language]
    with tempfile.NamedTemporaryFile(suffix=lang_config["extension"], delete=False) as temp_file:
        temp_file.write(code.encode())
        temp_file_path = temp_file.name

    try:
        if language == "cpp":
            subprocess.run(["g++", temp_file_path, "-o", "a.out"], check=True)
            process = subprocess.run(["./a.out"], capture_output=True, text=True)
        else:
            process = subprocess.run(lang_config["command"] + [temp_file_path], capture_output=True, text=True)

        return jsonify({"output": process.stdout, "error": process.stderr})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr})
    finally:
        os.unlink(temp_file_path)
        if language == "cpp":
            os.unlink("a.out")

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    session_id = data.get("session_id", "default")  # Use a session ID if provided
    user_message = data.get("message", "")

    if session_id not in chat_sessions:
        chat_sessions[session_id] = [
            {"role": "system", "content": "You are a helpful AI assistant."}
        ]

    # Append user message to chat history
    chat_sessions[session_id].append({"role": "user", "content": user_message})

    # Generate AI response
    chat_completion = client.chat.completions.create(
        messages=chat_sessions[session_id], model="mixtral-8x7b-32768", temperature=0.7, max_tokens=2000
    )
    ai_response = chat_completion.choices[0].message.content

    # Append AI response to chat history
    chat_sessions[session_id].append({"role": "assistant", "content": ai_response})
    

    return jsonify({"response": ai_response})

@app.route('/api/languages', methods=['GET'])
def get_supported_languages():
    return jsonify(list(SUPPORTED_LANGUAGES.keys()))
@app.route('/api/suggest', methods=['POST'])
def get_suggestions():
    data = request.get_json()
    code = data.get('code', '')
    cursor_position = data.get('cursorPosition', 0)
    language = data.get('language', '')

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    # Get the context around the cursor position
    context_before = code[:cursor_position].split('\n')[-3:]  # Last 3 lines before cursor
    context_after = code[cursor_position:].split('\n')[:2]    # Next 2 lines after cursor
    
    context = '\n'.join(context_before + context_after)

    messages = [
        {"role": "system", "content": "You are a code completion assistant. Provide short, contextual code suggestions."},
        {"role": "user", "content": f"""
Given this code context in {language}:
```
{context}
```
Provide 2-3 likely next tokens or completions. Keep each suggestion under 50 characters.
Format response as a JSON array of strings."""}
    ]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768",
            temperature=0.2,
            max_tokens=100
        )
        
        # Parse the response to get suggestions
        response_text = chat_completion.choices[0].message.content
        # Extract suggestions from the response
        suggestions = eval(response_text) if response_text.startswith('[') else []
        
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', '')

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    messages = [
        {"role": "system", "content": "You are a code review assistant. Analyze code and provide brief, actionable improvements."},
        {"role": "user", "content": f"""
Analyze this {language} code and provide 2-3 specific suggestions for improvement:
```
{code}
```
Format each suggestion in 1-2 sentences."""}
    ]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768",
            temperature=0.3,
            max_tokens=20000
        )
        
        suggestions = chat_completion.choices[0].message.content.split('\n')
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        logger.error(f"Error analyzing code: {str(e)}")
        return jsonify({"error": str(e)}), 500
@app.route('/api/debug', methods=['POST'])
def debug_code():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', '')

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    lang_config = SUPPORTED_LANGUAGES[language]
    
    with tempfile.NamedTemporaryFile(suffix=lang_config["extension"], delete=False) as temp_file:
        temp_file.write(code.encode())
        temp_file_path = temp_file.name

    try:
        if language == "python3":
            process = subprocess.run(
                [lang_config["command"][0], "-m", "py_compile", temp_file_path],
                capture_output=True,
                text=True
            )
        elif language == "cpp":
            process = subprocess.run(["g++", temp_file_path, "-o", "a.out"], capture_output=True, text=True)
        else:
            process = subprocess.run(lang_config["command"] + [temp_file_path], capture_output=True, text=True)

        if process.returncode != 0:
            error_message = process.stderr

            # AI-powered debugging assistance
            messages = [
                {"role": "system", "content": "You are an AI that helps debug code by providing suggestions."},
                {"role": "user", "content": f"""
I encountered this error while running the following {language} code: {error_message} Can you suggest possible reasons and fixes for this error? Keep it brief."""}
            ]
            
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="mixtral-8x7b-32768",
                temperature=0.3,
                max_tokens=300
            )
            
            suggestions = chat_completion.choices[0].message.content

            return jsonify({"error": error_message, "suggestions": suggestions})

        return jsonify({"message": "No syntax errors found.", "output": process.stdout})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr})

    finally:
        os.unlink(temp_file_path)
        if language == "cpp":
            os.unlink("a.out")
@app.route('/api/run-test', methods=['POST'])
def run_test():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', '')
    test_input = data.get('input', '')
    
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400

    lang_config = SUPPORTED_LANGUAGES[language]
    
    # Create temporary file for the code
    with tempfile.NamedTemporaryFile(suffix=lang_config["extension"], delete=False) as temp_file:
        temp_file.write(code.encode())
        temp_file_path = temp_file.name

    try:
        if language == "cpp":
            # Compile C++ code
            compile_process = subprocess.run(["g++", temp_file_path, "-o", "a.out"], 
                                          capture_output=True, 
                                          text=True)
            if compile_process.returncode != 0:
                return jsonify({"error": compile_process.stderr})
            
            # Run with test input
            process = subprocess.run(["./a.out"], 
                                  input=test_input,
                                  capture_output=True, 
                                  text=True)
        else:
            # For Python and other interpreted languages
            process = subprocess.run(lang_config["command"] + [temp_file_path],
                                  input=test_input,
                                  capture_output=True,
                                  text=True)

        if process.returncode != 0:
            return jsonify({"error": process.stderr})
            
        return jsonify({"output": process.stdout})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)})
    finally:
        os.unlink(temp_file_path)
        if language == "cpp" and os.path.exists("a.out"):
            os.unlink("a.out")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
