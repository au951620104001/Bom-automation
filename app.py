from flask import Flask, render_template, request, jsonify
import os
import glob
from extractor import process_folder
from catia_extractor import process_folder_catia

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_bom():
    data = request.get_json()
    folder_path = data.get('folder_path', '').strip()
    
    if not folder_path:
        return jsonify({'success': False, 'message': 'Please provide a folder path.'})
        
    if not os.path.exists(folder_path):
        return jsonify({'success': False, 'message': 'The specified folder path does not exist.'})
        
    if not os.path.isdir(folder_path):
        return jsonify({'success': False, 'message': 'The path provided is a file, not a folder.'})

    try:
        # Determine whether to use PDF or CATIA extraction based on folder contents
        has_catdrawing = len(glob.glob(os.path.join(folder_path, '*.CATDrawing'))) > 0
        has_pdf = len(glob.glob(os.path.join(folder_path, '*.pdf'))) > 0
        
        if has_catdrawing:
            output_file, message = process_folder_catia(folder_path)
        elif has_pdf:
            output_file, message = process_folder(folder_path)
        else:
            return jsonify({'success': False, 'message': 'No .pdf or .CATDrawing files found in the directory.'})
            
        if output_file:
            return jsonify({'success': True, 'message': message, 'file': output_file})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})

if __name__ == '__main__':
    # Run the Flask app on localhost:5000
    app.run(debug=True, port=5000)
