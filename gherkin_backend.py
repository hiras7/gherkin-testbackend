
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from docx import Document
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.docx'):
        return jsonify({'error': 'Invalid file format'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    output_path = os.path.join(OUTPUT_FOLDER, 'gherkin_output.docx')
    generate_gherkin_document(filepath, output_path)

    return send_file(output_path, as_attachment=True)

def generate_gherkin_document(input_path, output_path):
    doc = Document(input_path)
    output_doc = Document()

    for para in doc.paragraphs:
        output_doc.add_paragraph(para.text, style='Normal')

    output_doc.add_paragraph("
Summary Table", style='Heading 1')
    table = output_doc.add_table(rows=1, cols=5, style='Table Grid')
    hdr_cells = table.rows[0].cells
    headers = ['Topic', 'Req ID', 'Name', '# FIT Criteria', '# Gherkin Scenarios']
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
        for cell in hdr_cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = 1
                for run in paragraph.runs:
                    run.bold = True

    output_doc.save(output_path)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
