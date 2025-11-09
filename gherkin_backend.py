
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

def digits_from_ref(refcode: str) -> str:
    m = re.findall(r'(\d+)', refcode or "")
    return m[-1] if m else "UNKNOWN"

def get_mode_flags_guidelines(form):
    mode = (form.get('mode') or 'optimized').strip().lower()
    if mode not in ('optimized', 'atomized'):
        mode = 'optimized'
    flags = {
        'opt_outline': form.get('opt_outline') == '1',
        'opt_preserve_bullets': form.get('opt_preserve_bullets') == '1',
        'opt_strict_actor': form.get('opt_strict_actor') == '1',
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
        "Given the user is logged in (unless an explicit different actor is detected)",
    ])
    return rules

def para_is_heading(text: str, label: str) -> bool:
    return (text or '').strip().lower() == label

def is_fit_heading(text: str) -> bool:
    t = (text or '').strip().lower()
    return t in ('fit criteria', 'fitcriterion', 'fit-criteria', 'fit')

def parse_requirements_from_docx(path: str):
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
        if not text: continue
        m = BLOCK_HEADER_RE.match(text)
        if m:
            commit()
            cur = {'ReferenceCode': m.group('ref').strip(), 'Title': m.group('title').strip(), 'FitCriteria': []}
            section = None
            continue
        if para_is_heading(text, 'requirement'):
            section = 'Requirement'; cur.setdefault('Requirement',''); continue
        if para_is_heading(text, 'rationale') or para_is_heading(text, 'rational'):
            section = 'Rationale'; cur.setdefault('Rationale',''); continue
        if is_fit_heading(text):
            section = 'Fit'; continue
        if not cur: continue
        if section == 'Requirement':
            cur['Requirement'] = (cur.get('Requirement','') + ("
" if cur.get('Requirement') else "") + text)
        elif section == 'Rationale':
            cur['Rationale'] = (cur.get('Rationale','') + ("
" if cur.get('Rationale') else "") + text)
        elif section == 'Fit':
            cur['FitCriteria'].append(text)
    commit()
    return [{
        'ReqID': it.get('ReqID'), 'ReqName': it.get('ReqName'), 'Topic': it.get('Title'),
        'Requirement': it.get('Requirement'), 'Rationale': it.get('Rationale'), 'FitCriteria': it.get('FitCriteria', [])
    } for it in items]

def scenario_count(fits, mode):
    if mode == 'atomized' and fits: return len(fits)
    return 1

def compute_overview(data, mode, flags):
    out = []
    for r in data:
        fits = r.get('FitCriteria') or []
        out.append({'ReqID': r.get('ReqID'), 'ReqName': r.get('ReqName'), 'FitCount': len(fits), 'ScenarioCount': scenario_count(fits, mode)})
    return out

def looks_like_kv(line: str) -> bool: return bool(re.search(r'[:=]\s', line))

def looks_like_mapping(line: str) -> bool: return '->' in line or '=>' in line

def actor_from_text(requirement_text: str, flags) -> str:
    if flags.get('opt_strict_actor'):
        m = re.search(r'As a[n]?\s+([A-Z][A-Za-z0-9 _/\-]+)', requirement_text or "", re.IGNORECASE)
        if m: return m.group(1).strip()
    return "the user"

def generate_gherkin_document(input_path, output_path, mode='optimized', flags=None, guidelines=''):
    flags = flags or {}
    data = parse_requirements_from_docx(input_path)
    doc = Document()
    for r in data:
        req_id = r.get('ReqID', 'UNKNOWN'); req_name = r.get('ReqName', ''); topic = r.get('Topic', '') or req_name
        requirement = r.get('Requirement', ''); rationale = r.get('Rationale', ''); fits = r.get('FitCriteria', [])
        doc.add_paragraph(f"REQ ID: {req_id}"); doc.add_paragraph(f"REQ NAME: {req_name}"); doc.add_paragraph("")
        doc.add_paragraph(f"Feature: {topic}")
        actor = actor_from_text(requirement, flags)
        doc.add_paragraph(f"  As a {actor}"); doc.add_paragraph(f"  I want {topic.lower()}"); doc.add_paragraph(f"  So that {rationale or 'business value is achieved'}"); doc.add_paragraph("")
        if mode == 'atomized' and fits:
            for i, fit in enumerate(fits, 1):
                doc.add_paragraph(f"  @REQ-{req_id}"); doc.add_paragraph(f"  Scenario: {topic} — FIT {i}")
                doc.add_paragraph(f"    Given the user is logged in" if actor=='the user' else f"    Given {actor} is authenticated")
                doc.add_paragraph(f"    When the system evaluates requirement {req_id}"); doc.add_paragraph(f"    Then {fit}"); doc.add_paragraph("")
            r['__scenarios'] = len(fits)
        else:
            use_outline = flags.get('opt_outline') and any(looks_like_mapping(x) or looks_like_kv(x) for x in fits) and len(fits)>1
            doc.add_paragraph(f"  @REQ-{req_id}"); doc.add_paragraph(f"  Scenario{' Outline' if use_outline else ''}: {topic}")
            doc.add_paragraph(f"    Given the user is logged in" if actor=='the user' else f"    Given {actor} is authenticated")
            doc.add_paragraph(f"    When the system evaluates requirement {req_id}")
            if use_outline:
                doc.add_paragraph(f"    Then the system should satisfy the following FIT criteria:")
                for line in fits: doc.add_paragraph(f"      - {line}")
            else:
                if fits:
                    doc.add_paragraph(f"    Then it should satisfy {len(fits)} FIT criteria")
                    for line in fits: doc.add_paragraph(f"    And {line}")
                else:
                    doc.add_paragraph(f"    Then it should meet the specified acceptance criteria")
            doc.add_paragraph(""); r['__scenarios'] = 1
    # Append Rules + Guidelines + Summary
    def append_meta(document):
        document.add_paragraph("Rules Applied", style='Heading 1')
        for rr in build_rules(mode, flags): document.add_paragraph(f"- {rr}")
        if guidelines:
            document.add_paragraph("Guidelines (provided)", style='Heading 1')
            for line in guidelines.splitlines(): document.add_paragraph(line)
    doc.save(output_path)
    doc2 = Document(output_path); append_meta(doc2)
    doc2.add_paragraph("Summary Table", style='Heading 1')
    tbl = doc2.add_table(rows=1, cols=5, style='Table Grid'); hdr=['Topic','Req ID','Name','# FIT Criteria','# Gherkin Scenarios']
    for i,h in enumerate(hdr): cell=tbl.rows[0].cells[i]; cell.text=h; [setattr(run,'bold',True) for run in cell.paragraphs[0].runs]
    for r in data:
        row = tbl.add_row().cells
        row[0].text = r.get('Topic',''); row[1].text = r.get('ReqID',''); row[2].text = r.get('ReqName','')
        row[3].text = str(len(r.get('FitCriteria',[]))); row[4].text = str(r.get('__scenarios',1))
    doc2.save(output_path)
    return data

@app.route('/preview', methods=['POST'])
def preview():
    if 'file' not in request.files: return jsonify({'error':'No file part'}), 400
    file = request.files['file']
    if file.filename=='' or not file.filename.lower().endswith('.docx'): return jsonify({'error':'Invalid file (.docx expected)'}), 400
    p = os.path.join(UPLOAD_FOLDER, file.filename); file.save(p)
    mode, flags, guidelines = get_mode_flags_guidelines(request.form)
    t0=time.perf_counter(); data=parse_requirements_from_docx(p); elapsed=round(time.perf_counter()-t0,3)
    return jsonify({'time':elapsed, 'data':data, 'rules':build_rules(mode,flags), 'overview':compute_overview(data,mode,flags), 'guidelines':guidelines})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files: return jsonify({'error':'No file part'}), 400
    file = request.files['file']
    if file.filename=='' or not file.filename.lower().endswith('.docx'): return jsonify({'error':'Invalid file (.docx expected)'}), 400
    p = os.path.join(UPLOAD_FOLDER, file.filename); file.save(p)
    mode, flags, guidelines = get_mode_flags_guidelines(request.form)
    out = os.path.join(OUTPUT_FOLDER, 'gherkin_output.docx')
    t0=time.perf_counter(); data=generate_gherkin_document(p, out, mode=mode, flags=flags, guidelines=guidelines); elapsed=round(time.perf_counter()-t0,3)
    resp = make_response(send_file(out, as_attachment=True)); resp.headers['X-Process-Time'] = str(elapsed); return resp

if __name__=='__main__':
    port=int(os.environ.get('PORT','5000')); app.run(host='0.0.0.0', port=port, debug=False)
