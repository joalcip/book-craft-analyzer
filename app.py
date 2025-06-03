from flask import Flask, render_template, request, jsonify
from anthropic import Anthropic
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads folder if it doesn't exist
os.makedirs('uploads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_book():
    try:
        # Get the uploaded file
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get API key from request
        api_key = request.form.get('api_key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 400
        
        # Get selected categories
        categories = request.form.getlist('categories[]')
        
        # Save and read the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            book_text = f.read()
        
        # Initialize Claude
        client = Anthropic(api_key=api_key)
        
        # Process the book in chunks
        chunk_size = 3000
        chunks = [book_text[i:i+chunk_size] for i in range(0, len(book_text), chunk_size)]
        
        # Limit to first 5 chunks to save API costs
        chunks = chunks[:5]
        
        results = []
        
        for i, chunk in enumerate(chunks):
            # Create prompt based on selected categories
            category_prompts = {
                'character': 'character development techniques, character voice, and personality reveals',
                'dialogue': 'dialogue techniques, subtext, and conversational patterns',
                'prose': 'prose style, sentence structure, rhythm, and word choice',
                'plot': 'plot structure, pacing, and tension building',
                'theme': 'thematic elements and how themes are developed'
            }
            
            selected_prompts = [category_prompts[cat] for cat in categories if cat in category_prompts]
            focus_areas = ', '.join(selected_prompts)
            
            prompt = f"""Analyze this excerpt from a book and extract specific writing craft techniques.

Focus on: {focus_areas}

For each technique found:
1. Name the specific technique
2. Provide a brief quote showing it (max 50 words)
3. Explain why it's effective (2-3 sentences)

Text excerpt:
{chunk}

Format your response as a clear list of techniques."""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            results.append({
                'chunk': i + 1,
                'analysis': response.content[0].text,
                'progress': int((i + 1) / len(chunks) * 100)
            })
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
