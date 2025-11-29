"""
Flask backend API for HumanEval PWA
"""
import os
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Import evaluation functions
from human_eval.data import HUMAN_EVAL
from human_eval.evaluation import evaluate_functional_correctness

@app.route('/')
def index():
    """Serve the main PWA page"""
    return send_from_directory('static', 'index.html')

@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    """Serve service worker"""
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve other static files (CSS, JS, images)"""
    # Only serve files that exist in static directory
    allowed_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.ico']
    if any(filename.endswith(ext) for ext in allowed_extensions):
        return send_from_directory('static', filename)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/problems')
def get_problems():
    """Get all HumanEval problems"""
    problems = []
    try:
        with open(HUMAN_EVAL, 'r') as f:
            for line in f:
                problems.append(json.loads(line))
        return jsonify({'problems': problems})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/problems/<task_id>')
def get_problem(task_id):
    """Get a specific problem by task_id"""
    try:
        with open(HUMAN_EVAL, 'r') as f:
            for line in f:
                problem = json.loads(line)
                if problem['task_id'] == task_id:
                    return jsonify({'problem': problem})
        return jsonify({'error': 'Problem not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """Evaluate completion results"""
    try:
        data = request.json
        sample_file = data.get('sample_file')
        k = data.get('k', '1,10,100')
        n_workers = data.get('n_workers', 4)
        timeout = data.get('timeout', 3.0)
        
        if not sample_file:
            return jsonify({'error': 'sample_file is required'}), 400
        
        k_list = list(map(int, k.split(',')))
        results = evaluate_functional_correctness(
            sample_file, k_list, n_workers, timeout, HUMAN_EVAL
        )
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results')
def get_results():
    """List available result files"""
    results_dir = os.path.join(os.getcwd(), 'data')
    results_files = []
    
    try:
        for filename in os.listdir(results_dir):
            if filename.endswith('_results.jsonl') or filename.startswith('results-'):
                filepath = os.path.join(results_dir, filename)
                if os.path.isfile(filepath):
                    results_files.append({
                        'filename': filename,
                        'path': filepath
                    })
        return jsonify({'results': results_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results/<filename>')
def get_result_file(filename):
    """Get contents of a result file"""
    try:
        results_dir = os.path.join(os.getcwd(), 'data')
        filepath = os.path.join(results_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        results = []
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
