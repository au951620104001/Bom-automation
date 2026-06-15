import os
import tempfile
import glob
import shutil
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, after_this_request
from extractor import process_folder
from catia_extractor import process_folder_catia

app = Flask(__name__)
# Set a secret key for session management
app.secret_key = 'super_secret_bom_automation_key'

# Credentials as requested
USERNAME = 'cyient'
PASSWORD = 'binith123'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid username or password.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_bom():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'message': 'No files uploaded.'})
        
    files = request.files.getlist('files[]')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': 'No valid files selected.'})
        
    # Create a temporary directory to save the uploaded files
    temp_dir = tempfile.mkdtemp()
    
    try:
        has_catdrawing = False
        has_pdf = False
        
        for file in files:
            if file.filename:
                filepath = os.path.join(temp_dir, file.filename)
                file.save(filepath)
                if file.filename.lower().endswith('.catdrawing'):
                    has_catdrawing = True
                elif file.filename.lower().endswith('.pdf'):
                    has_pdf = True
                    
        # Process files
        if has_catdrawing:
            output_file, message = process_folder_catia(temp_dir)
        elif has_pdf:
            output_file, message = process_folder(temp_dir)
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({'success': False, 'message': 'No .pdf or .CATDrawing files uploaded.'})
            
        if output_file and os.path.exists(output_file):
            download_url = url_for('download_file', path=output_file)
            return jsonify({'success': True, 'message': message, 'download_url': download_url})
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})

@app.route('/download')
def download_file():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    path = request.args.get('path')
    if path and os.path.exists(path):
        
        @after_this_request
        def cleanup(response):
            try:
                # Get the directory of the temp file
                dir_path = os.path.dirname(path)
                # Recursively delete the temp directory and its contents
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception as e:
                print(f"Error cleaning up temp files: {e}")
            return response
            
        return send_file(path, as_attachment=True, download_name="master_bom.xlsx")
    return "File not found.", 404

if __name__ == '__main__':
    # Run Flask app on port 5000
    app.run(debug=True, port=5000)
