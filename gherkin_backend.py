
from flask import Flask, request, send_file, jsonify, make_response
from flask_cors import CORS
from docx import Document
import os, re, time

app = Flask(__name__)
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": FRONTEND_ORIGIN}})

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BLOCK_HEADER_RE = re.compile(r'^\[(?P<ref>[^\]]+)\]\s+(?P<title>.+)$')

def digits_from_ref(refcode):
    m = re.findall(r'(\d+)', refcode or "")
    return m[-1] if m else "UNKNOWN"

def get_mode_flags_guidelines(form):
    mode = (form.get('mode') or 'optimized').strip().lower()
    if mode not in ('optimized', 'atomized'):
        mode = 'optimized'
    flags = {
        'opt_outline': form.get('opt_outline') == '1',
        'opt_preserve_bullets': form.get('opt_preserve_bullets') == '1',
        'opt_strict_actor': form.get('opt_strict_actor') == '1'
    }
    guidelines = (form.get('guidelines') or '').strip()
    return mode, flags, guidelines

def build_rules(mode, flags):
    rules = []
    if mode == 'atomized':
        rules.append('Mode: Atomized — each FIT criterion becomes its own scenario')
    else:
        rules.append('Mode: Optimized — one scenario per requirement (no atomic splitting)')
    rules.append(f"Scenario Outline Optimization: {'ON' if flags['opt_outline'] else 'OFF'}")
    rules.append(f"Preserve Bullet Formatting: {'ON' if flags['opt_preserve_bullets'] else 'OFF'}")
    rules.append(f"Strict Actor Referencing: {'ON' if flags['opt_strict_actor'] else 'OFF'}")
    rules.extend([
        "Gherkin v46 style; third-person actors; no OR in steps; no UI implementation details",
        "Given the user is logged in (unless an explicit different actor is detected)"
    ])
    return rules

def parse_requirements_from_docx(path):
    doc = Document(path)
    items = []
    cur = None
    section = None

    def commit():
        nonlocal cur
        if cur:
            cur.setdefault('ReferenceCode', '')
            cur.setdefault('ReqID', digits_from_ref(cur.get('ReferenceCode')))
            cur.setdefault('Title', '')
            cur.setdefault('ReqName', f"[{cur.get('ReferenceCode','')}] {cur.get('Title','')}".strip())
            cur.setdefault('Requirement', '')
            cur.setdefault('Rationale', '')
            cur.setdefault('FitCriteria', [])
            items.append(cur)
            cur = None

    for p in doc.paragraphs:
        text = (p.text or '').strip()
        if not text:
            continue
        m = BLOCK_HEADER_RE.match(text)
        if m:
            commit()
            cur = {'ReferenceCode': m.group('ref').strip(), 'Title': m.group('title').strip(), 'FitCriteria': []}
            section = None
            continue
        if text.lower() == 'requirement':
            section = 'Requirement'
            cur.setdefault('Requirement', '')
            continue
        if text.lower() in ('rationale', 'rational'):
            section = 'Rationale'
            cur.setdefault('Rationale', '')
            continue
        if text.lower() in ('fit criteria', 'fitcriterion', 'fit-criteria', 'fit'):
            section = 'Fit'
            continue
        if not cur:
            continue
        if section == 'Requirement':
            cur['Requirement'] = cur.get('Requirement', '') + (' ' if cur.get('Requirement') else '') + text
        elif section == 'Rationale':
            cur['Rationale'] = cur.get('Rationale', '') + (' ' if cur.get('Rationale') else '') + text
        elif section == 'Fit':
            cur['FitCriteria'].append(text)

    commit()
    return [{
        'ReqID': it.get('ReqID'),
        'ReqName': it.get('ReqName'),
        'Topic': it.get('Title'),
        'Requirement': it.get('Requirement'),
        'Rationale': it.get('Rationale'),
        'FitCriteria': it.get('FitCriteria', [])
    } for it in items]

@app.route('/preview', methods=['POST'])
def preview():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.docx'):
        return jsonify({'error': 'Invalid file (.docx expected)'}), 400
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    mode, flags, guidelines = get_mode_flags_guidelines(request.form)
    t0 = time.perf_counter()
    data = parse_requirements_from_docx(path)
    elapsed = round(time.perf_counter() - t0, 3)
    return jsonify({
        'time': elapsed,
        'data': data,
        'rules': build_rules(mode, flags),
        'overview': [],
        'guidelines': guidelines
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False)
