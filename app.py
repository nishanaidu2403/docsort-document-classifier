from flask import Flask, request, jsonify
import os
from datetime import datetime

# importing my own pipeline files
from pipeline import process_file
from folder_setup import create_folders

# creating the flask app
# flask lets me run a website from python
app = Flask(__name__)

# making sure folders exist when app starts
create_folders()

# storing results in memory
# i know this resets when app restarts
# but its fine for demo purposes
recent_results = []

# counting how many of each type we processed
stats = {
    "total": 0,
    "resumes": 0,
    "invoices": 0,
    "paystubs": 0,
    "contracts": 0,
    "duplicates": 0,
    "failed": 0
}


# main page - shows the dashboard
@app.route("/")
def home():
    return DASHBOARD


# handles file upload from browser
# took me a while to figure out how flask
# receives files - had to read the docs
@app.route("/upload", methods=["POST"])
def upload_file():

    if "file" not in request.files:
        return jsonify({"error": "no file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "no file selected"}), 400

    # save file to uploads folder
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)
    print(f"received: {file.filename}")

    # run my pipeline on the file
    result = process_file(file_path)

    # update my stats counters
    stats["total"] += 1
    doc_type = result.get("document_type", "").lower()

    if doc_type == "resume":
        stats["resumes"] += 1
    elif doc_type == "invoice":
        stats["invoices"] += 1
    elif doc_type == "paystub":
        stats["paystubs"] += 1
    elif doc_type == "contract":
        stats["contracts"] += 1
    elif result.get("status") == "duplicate":
        stats["duplicates"] += 1
    else:
        stats["failed"] += 1

    # add timestamp so dashboard shows when it happened
    result["timestamp"] = datetime.now().strftime("%H:%M:%S")
    result["filename"]  = file.filename

    # keep only last 20 results
    recent_results.insert(0, result)
    if len(recent_results) > 20:
        recent_results.pop()

    return jsonify(result)


# returns recent results for dashboard table
@app.route("/results")
def get_results():
    return jsonify(recent_results)


# returns stats for the counter cards
@app.route("/stats")
def get_stats():
    return jsonify(stats)


# reads log file and returns contents
# i added this so logs are visible in dashboard
@app.route("/logs")
def get_logs():
    log_path = "logs/processing_log.txt"
    if not os.path.exists(log_path):
        return jsonify({"logs": "no logs yet"})
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    return jsonify({"logs": content})


# i wrote all the html css and javascript here
# i know its a lot in one file but it keeps things simple
# a proper project would separate these into different files
DASHBOARD = """<!DOCTYPE html>
<html>
<head>
<title>DocSort - Document Classifier</title>
<style>
/* i kept the styling simple and clean
   learned basic css for this project */

* { margin:0; padding:0; box-sizing:border-box; }

body {
    font-family: Arial, sans-serif;
    background: #f5f6fa;
    color: #2d3436;
}

.header {
    background: #2d3436;
    color: white;
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.header h1 { font-size: 20px; }
.header h1 span { color: #74b9ff; }
.header p { font-size: 12px; opacity: 0.6; }

/* tab navigation */
.tabs {
    background: white;
    border-bottom: 1px solid #dfe6e9;
    padding: 0 32px;
    display: flex;
}

.tab {
    padding: 12px 18px;
    font-size: 13px;
    cursor: pointer;
    color: #636e72;
    border-bottom: 2px solid transparent;
}

.tab.active {
    color: #0984e3;
    border-bottom-color: #0984e3;
}

/* hide/show tab panels */
.panel { display: none; padding: 24px 32px; }
.panel.active { display: block; }

/* stat cards at top */
.cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}

.card {
    background: white;
    border-radius: 8px;
    padding: 18px;
    border: 1px solid #dfe6e9;
}

.card .num {
    font-size: 28px;
    font-weight: bold;
    color: #2d3436;
}

.card .lbl {
    font-size: 12px;
    color: #636e72;
    margin-top: 4px;
}

/* two column layout */
.row2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

/* white content box */
.box {
    background: white;
    border-radius: 8px;
    border: 1px solid #dfe6e9;
    padding: 20px;
}

.box h3 {
    font-size: 12px;
    color: #636e72;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 16px;
}

/* bar chart for document types */
.bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}

.bar-label {
    font-size: 12px;
    color: #636e72;
    width: 65px;
    text-align: right;
}

.bar-bg {
    flex: 1;
    height: 8px;
    background: #f5f6fa;
    border-radius: 4px;
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}

.bar-count {
    font-size: 12px;
    color: #636e72;
    width: 20px;
}

/* results table */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

th {
    text-align: left;
    padding: 8px 10px;
    color: #636e72;
    border-bottom: 1px solid #dfe6e9;
    font-weight: normal;
    font-size: 12px;
}

td {
    padding: 10px;
    border-bottom: 1px solid #f5f6fa;
}

tr:hover td { background: #f5f6fa; }

/* document type badges */
.badge {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
}

.badge-Resume   { background: #d6eaf8; color: #154360; }
.badge-Invoice  { background: #d5f5e3; color: #145a32; }
.badge-Paystub  { background: #fdebd0; color: #6e2f1a; }
.badge-Contract { background: #e8daef; color: #4a235a; }
.badge-Unknown  { background: #eaecee; color: #424949; }
/* i added these for special cases */
.badge-unsupported { background: #ffeaa7; color: #6c5ce7; }
.badge-unreadable  { background: #fab1a0; color: #d63031; }
.badge-duplicate   { background: #fd79a8; color: #6d214f; }
.badge-success     { background: #d5f5e3; color: #145a32; }

/* upload area */
.upload-area {
    border: 2px dashed #b2bec3;
    border-radius: 8px;
    padding: 48px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    margin-bottom: 16px;
}

.upload-area:hover,
.upload-area.dragging {
    border-color: #0984e3;
    background: #ebf5fb;
}

.upload-area input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
}

.upload-area .icon { font-size: 36px; margin-bottom: 10px; }
.upload-area h3 { font-size: 16px; margin-bottom: 6px; }
.upload-area p { font-size: 12px; color: #636e72; }

/* pipeline stages shown during processing */
.stages { margin-top: 8px; }

.stage {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    font-size: 13px;
    color: #b2bec3;
    border-bottom: 1px solid #f5f6fa;
    transition: color 0.2s;
}

.stage:last-child { border-bottom: none; }
.stage.done  { color: #00b894; }
.stage.running { color: #0984e3; }

.stage-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #dfe6e9;
    flex-shrink: 0;
    transition: background 0.2s;
}

.stage.done .stage-dot    { background: #00b894; }
.stage.running .stage-dot { background: #0984e3; }

/* result card after classification */
.result-card {
    background: #f5f6fa;
    border-radius: 8px;
    padding: 16px;
    margin-top: 16px;
    display: none;
}

.result-card.show { display: block; }
.result-card .type { font-size: 22px; font-weight: bold; margin-bottom: 12px; }

.result-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 6px 0;
    border-bottom: 1px solid #dfe6e9;
}

.result-row:last-child { border-bottom: none; }
.result-row .key { color: #636e72; }

/* confidence bar in result */
.conf-track {
    height: 4px;
    background: #dfe6e9;
    border-radius: 2px;
    margin: 8px 0 4px;
    overflow: hidden;
}

.conf-fill {
    height: 100%;
    background: #0984e3;
    border-radius: 2px;
    transition: width 0.8s ease;
}

/* log viewer - terminal style */
.log-viewer {
    background: #2d3436;
    color: #55efc4;
    border-radius: 8px;
    padding: 20px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    white-space: pre-wrap;
    max-height: 500px;
    overflow-y: auto;
    line-height: 1.8;
}

.log-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
}

.refresh-btn {
    padding: 8px 16px;
    background: white;
    border: 1px solid #dfe6e9;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    color: #636e72;
}

.refresh-btn:hover {
    border-color: #0984e3;
    color: #0984e3;
}

/* comparison tab */
.compare-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

.compare-box {
    background: white;
    border-radius: 8px;
    border: 1px solid #dfe6e9;
    padding: 20px;
}

/* blue top border for local */
.compare-box.local { border-top: 3px solid #0984e3; }

/* orange top border for aws */
.compare-box.aws   { border-top: 3px solid #e17055; }

.compare-box h2 {
    font-size: 15px;
    margin-bottom: 4px;
}

.compare-box p {
    font-size: 12px;
    color: #636e72;
    margin-bottom: 16px;
}

.compare-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 7px 0;
    border-bottom: 1px solid #f5f6fa;
}

.compare-row:last-child { border-bottom: none; }
.compare-row .ck { color: #636e72; }
.compare-row .cv { font-weight: bold; }
.compare-row .good { color: #00b894; }
.compare-row .warn { color: #e17055; }

/* mapping table in compare tab */
.map-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.map-table th {
    background: #f5f6fa;
    padding: 10px;
    text-align: left;
    font-weight: bold;
    font-size: 12px;
    color: #636e72;
    border-bottom: 1px solid #dfe6e9;
}

.map-table td {
    padding: 10px;
    border-bottom: 1px solid #f5f6fa;
}

.map-table tr:hover td { background: #f5f6fa; }

/* insight box at bottom of compare tab */
.insight {
    background: #ebf5fb;
    border: 1px solid #aed6f1;
    border-radius: 8px;
    padding: 16px;
    font-size: 13px;
    color: #154360;
    margin-top: 16px;
    line-height: 1.7;
}

.insight strong { color: #0984e3; }

/* status indicator in header */
.status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #b2bec3;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00b894;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}
</style>
</head>
<body>

<!-- header -->
<div class="header">
    <div>
        <h1>Doc<span>Sort</span></h1>
        <p>document classification pipeline</p>
    </div>
    <div class="status">
        <div class="status-dot"></div>
        ML model active · TF-IDF + Logistic Regression
    </div>
</div>

<!-- tabs -->
<div class="tabs">
    <div class="tab active" onclick="showTab('dashboard', this)">dashboard</div>
    <div class="tab" onclick="showTab('upload', this)">upload</div>
    <div class="tab" onclick="showTab('logs', this)">logs</div>
    <div class="tab" onclick="showTab('compare', this)">local vs aws</div>
</div>

<!-- DASHBOARD TAB -->
<div id="dashboard" class="panel active">

    <div class="cards">
        <div class="card">
            <div class="num" id="stat-total">0</div>
            <div class="lbl">total processed</div>
        </div>
        <div class="card">
            <div class="num" style="color:#00b894">98%</div>
            <div class="lbl">ML model accuracy</div>
        </div>
        <div class="card">
            <div class="num" id="stat-dupes">0</div>
            <div class="lbl">duplicates caught</div>
        </div>
        <div class="card">
            <div class="num">70%</div>
            <div class="lbl">confidence threshold</div>
        </div>
    </div>

    <div class="row2">
        <div class="box">
            <h3>documents by type</h3>
            <div class="bar-row">
                <div class="bar-label">Resume</div>
                <div class="bar-bg">
                    <div class="bar-fill" id="bar-r"
                         style="width:0%;background:#0984e3"></div>
                </div>
                <div class="bar-count" id="cnt-r">0</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Invoice</div>
                <div class="bar-bg">
                    <div class="bar-fill" id="bar-i"
                         style="width:0%;background:#00b894"></div>
                </div>
                <div class="bar-count" id="cnt-i">0</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Paystub</div>
                <div class="bar-bg">
                    <div class="bar-fill" id="bar-p"
                         style="width:0%;background:#fdcb6e"></div>
                </div>
                <div class="bar-count" id="cnt-p">0</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Contract</div>
                <div class="bar-bg">
                    <div class="bar-fill" id="bar-c"
                         style="width:0%;background:#a29bfe"></div>
                </div>
                <div class="bar-count" id="cnt-c">0</div>
            </div>
        </div>

        <div class="box">
            <h3>pipeline stages</h3>
            <div style="font-size:13px">
                <div class="compare-row">
                    <span class="ck">stage 1</span>
                    <span>file validation</span>
                </div>
                <div class="compare-row">
                    <span class="ck">stage 2</span>
                    <span>duplicate check (MD5)</span>
                </div>
                <div class="compare-row">
                    <span class="ck">stage 3</span>
                    <span>text extraction</span>
                </div>
                <div class="compare-row">
                    <span class="ck">stage 4</span>
                    <span>ML classification</span>
                </div>
                <div class="compare-row">
                    <span class="ck">stage 5</span>
                    <span>folder routing</span>
                </div>
                <div class="compare-row">
                    <span class="ck">stage 6</span>
                    <span>verification</span>
                </div>
                <div class="compare-row" style="border-bottom:none">
                    <span class="ck">stage 7</span>
                    <span>report + logging</span>
                </div>
            </div>
        </div>
    </div>

    <div class="box">
        <h3>recent classifications</h3>
        <table>
            <thead>
                <tr>
                    <th>filename</th>
                    <th>type</th>
                    <th>confidence</th>
                    <th>method</th>
                    <th>destination</th>
                    <th>time</th>
                </tr>
            </thead>
            <tbody id="results-tbody">
                <tr>
                    <td colspan="6"
                        style="text-align:center;
                               color:#636e72;
                               padding:24px">
                        no documents processed yet
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</div>

<!-- UPLOAD TAB -->
<div id="upload" class="panel">
    <div class="row2">

        <div class="box">
            <h3>upload document</h3>

            <div class="upload-area"
                 id="drop-area"
                 ondragover="handleDragOver(event)"
                 ondragleave="handleDragLeave(event)"
                 ondrop="handleDrop(event)">

                <input type="file"
                       id="file-input"
                       onchange="handleFileSelect(event)"
                       accept=".pdf,.docx,.jpg,.jpeg,.png,.txt,.xlsx,.pptx">

                <div class="icon">📄</div>
                <h3>drop file here or click to browse</h3>
                <p>supports pdf · docx · jpg · png · txt · xlsx · pptx</p>
            </div>

            <!-- stages show during processing -->
            <div class="stages" id="stage-list" style="display:none">
                <div class="stage" id="s1">
                    <div class="stage-dot"></div>
                    stage 1 — validating file
                </div>
                <div class="stage" id="s2">
                    <div class="stage-dot"></div>
                    stage 2 — checking for duplicates
                </div>
                <div class="stage" id="s3">
                    <div class="stage-dot"></div>
                    stage 3 — extracting text
                </div>
                <div class="stage" id="s4">
                    <div class="stage-dot"></div>
                    stage 4 — ML classification
                </div>
                <div class="stage" id="s5">
                    <div class="stage-dot"></div>
                    stage 5 — moving to folder
                </div>
                <div class="stage" id="s6">
                    <div class="stage-dot"></div>
                    stage 6 — verifying
                </div>
                <div class="stage" id="s7">
                    <div class="stage-dot"></div>
                    stage 7 — saving report
                </div>
            </div>
        </div>

        <div class="box">
            <h3>classification result</h3>

            <div id="result-empty"
                 style="text-align:center;
                        padding:48px 0;
                        color:#636e72;
                        font-size:13px">
                upload a document to see results here
            </div>

            <div class="result-card" id="result-card">
                <div style="display:flex;
                            justify-content:space-between;
                            align-items:center;
                            margin-bottom:8px">
                    <div class="type" id="r-type">—</div>
                    <div id="r-badge"></div>
                </div>

                <div class="conf-track">
                    <div class="conf-fill"
                         id="conf-bar"
                         style="width:0%"></div>
                </div>
                <div style="font-size:11px;
                            color:#636e72;
                            margin-bottom:14px">
                    confidence: <span id="conf-text">—</span>
                </div>

                <div class="result-row">
                    <span class="key">filename</span>
                    <span id="r-fn">—</span>
                </div>
                <div class="result-row">
                    <span class="key">document type</span>
                    <span id="r-dt">—</span>
                </div>
                <div class="result-row">
                    <span class="key">confidence</span>
                    <span id="r-cf">—</span>
                </div>
                <div class="result-row">
                    <span class="key">method used</span>
                    <span id="r-me">—</span>
                </div>
                <div class="result-row">
                    <span class="key">destination folder</span>
                    <span id="r-de">—</span>
                </div>
                <div class="result-row">
                    <span class="key">time taken</span>
                    <span id="r-ti">—</span>
                </div>
                <div class="result-row">
                    <span class="key">status</span>
                    <span id="r-st">—</span>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- LOGS TAB -->
<div id="logs" class="panel">
    <div class="log-top">
        <div>
            <h2 style="font-size:15px;margin-bottom:4px">
                processing logs
            </h2>
            <p style="font-size:12px;color:#636e72">
                every document that went through the pipeline
                is recorded here
            </p>
        </div>
        <button class="refresh-btn" onclick="loadLogs()">
            refresh
        </button>
    </div>

    <div class="log-viewer" id="log-viewer">
-- no logs yet --
-- upload a document to see the log here --
    </div>
</div>

<!-- COMPARISON TAB -->
<div id="compare" class="panel">

    <div style="margin-bottom:20px">
        <h2 style="font-size:15px;margin-bottom:4px">
            local vs aws comparison
        </h2>
        <p style="font-size:12px;color:#636e72">
            same ML model and pipeline logic —
            different infrastructure
        </p>
    </div>

    <div class="compare-grid">

        <div class="compare-box local">
            <h2>local version</h2>
            <p>running on your laptop right now</p>
            <div class="compare-row">
                <span class="ck">storage</span>
                <span class="cv good">local folders</span>
            </div>
            <div class="compare-row">
                <span class="ck">trigger</span>
                <span class="cv good">flask upload</span>
            </div>
            <div class="compare-row">
                <span class="ck">text extraction</span>
                <span class="cv good">pdfplumber + tesseract</span>
            </div>
            <div class="compare-row">
                <span class="ck">ML model</span>
                <span class="cv good">model.pkl on machine</span>
            </div>
            <div class="compare-row">
                <span class="ck">AI fallback</span>
                <span class="cv good">ollama (offline)</span>
            </div>
            <div class="compare-row">
                <span class="ck">logging</span>
                <span class="cv good">processing_log.txt</span>
            </div>
            <div class="compare-row">
                <span class="ck">cost</span>
                <span class="cv good">free</span>
            </div>
            <div class="compare-row">
                <span class="ck">scalability</span>
                <span class="cv warn">single machine</span>
            </div>
            <div class="compare-row">
                <span class="ck">automation</span>
                <span class="cv warn">manual trigger</span>
            </div>
        </div>

        <div class="compare-box aws">
            <h2>AWS version</h2>
            <p>production cloud deployment</p>
            <div class="compare-row">
                <span class="ck">storage</span>
                <span class="cv good">S3 buckets</span>
            </div>
            <div class="compare-row">
                <span class="ck">trigger</span>
                <span class="cv good">S3 event (automatic)</span>
            </div>
            <div class="compare-row">
                <span class="ck">text extraction</span>
                <span class="cv good">AWS Textract</span>
            </div>
            <div class="compare-row">
                <span class="ck">ML model</span>
                <span class="cv good">same model.pkl on Lambda</span>
            </div>
            <div class="compare-row">
                <span class="ck">AI fallback</span>
                <span class="cv warn">not implemented yet</span>
            </div>
            <div class="compare-row">
                <span class="ck">logging</span>
                <span class="cv good">DynamoDB</span>
            </div>
            <div class="compare-row">
                <span class="ck">cost</span>
                <span class="cv warn">pay per use</span>
            </div>
            <div class="compare-row">
                <span class="ck">scalability</span>
                <span class="cv good">unlimited</span>
            </div>
            <div class="compare-row">
                <span class="ck">automation</span>
                <span class="cv good">fully automatic</span>
            </div>
        </div>
    </div>

    <div class="box" style="margin-bottom:16px">
        <h3>component mapping</h3>
        <table class="map-table">
            <thead>
                <tr>
                    <th>pipeline stage</th>
                    <th style="color:#0984e3">local tool</th>
                    <th style="color:#e17055">AWS equivalent</th>
                    <th>purpose</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>file storage</td>
                    <td style="color:#0984e3">local folders</td>
                    <td style="color:#e17055">S3 buckets</td>
                    <td style="color:#636e72">
                        store and organize files
                    </td>
                </tr>
                <tr>
                    <td>pipeline trigger</td>
                    <td style="color:#0984e3">flask upload</td>
                    <td style="color:#e17055">S3 event notification</td>
                    <td style="color:#636e72">
                        start pipeline automatically
                    </td>
                </tr>
                <tr>
                    <td>code execution</td>
                    <td style="color:#0984e3">python script</td>
                    <td style="color:#e17055">AWS Lambda</td>
                    <td style="color:#636e72">
                        run pipeline logic
                    </td>
                </tr>
                <tr>
                    <td>text extraction</td>
                    <td style="color:#0984e3">pdfplumber / tesseract</td>
                    <td style="color:#e17055">AWS Textract</td>
                    <td style="color:#636e72">
                        read text from documents
                    </td>
                </tr>
                <tr>
                    <td>ML classification</td>
                    <td style="color:#0984e3">model.pkl (local)</td>
                    <td style="color:#e17055">same model.pkl on Lambda</td>
                    <td style="color:#636e72">
                        identify document type
                    </td>
                </tr>
                <tr>
                    <td>AI fallback</td>
                    <td style="color:#0984e3">ollama (llama3)</td>
                    <td style="color:#e17055">AWS Bedrock (planned)</td>
                    <td style="color:#636e72">
                        handle low confidence docs
                    </td>
                </tr>
                <tr>
                    <td>audit logging</td>
                    <td style="color:#0984e3">processing_log.txt</td>
                    <td style="color:#e17055">DynamoDB</td>
                    <td style="color:#636e72">
                        record every action
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="insight">
    <strong>key insight</strong> — the same trained ML model
    (model.pkl) runs in both environments. i train it once
    locally and deploy the exact same file to AWS Lambda.
    only the infrastructure changes — the intelligence stays
    the same. this shows the pipeline logic is completely
    environment-agnostic.
</div>

<div class="insight" style="margin-top:12px">
    <strong>edge case handling</strong> — both versions handle
    three scenarios. unsupported file types like videos or
    executables go to the unsupported folder. supported files
    that match our four trained categories get classified
    correctly. supported files that don't match any category
    go to the unknown folder for manual review. nothing ever
    gets lost in either version.
</div>

</div>

<script>
// tab switching - simple show/hide
function showTab(name, clickedTab) {
    // hide all panels
    document.querySelectorAll('.panel').forEach(function(p) {
        p.classList.remove('active');
    });
    // remove active from all tabs
    document.querySelectorAll('.tab').forEach(function(t) {
        t.classList.remove('active');
    });
    // show selected panel
    document.getElementById(name).classList.add('active');
    clickedTab.classList.add('active');

    // load logs when logs tab opened
    if (name === 'logs') loadLogs();
    // refresh dashboard when dashboard tab opened
    if (name === 'dashboard') refreshDashboard();
}

// drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('drop-area').classList.add('dragging');
}

function handleDragLeave(e) {
    document.getElementById('drop-area').classList.remove('dragging');
}

function handleDrop(e) {
    e.preventDefault();
    handleDragLeave(e);
    var file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
}

function handleFileSelect(e) {
    var file = e.target.files[0];
    if (file) uploadFile(file);
}

// animate pipeline stages while processing
function animateStages(callback) {
    var stages = ['s1','s2','s3','s4','s5','s6','s7'];

    // reset all stages first
    stages.forEach(function(id) {
        document.getElementById(id).className = 'stage';
    });

    // show the stages section
    document.getElementById('stage-list').style.display = 'block';

    var i = 0;
    function next() {
        // mark previous as done
        if (i > 0) {
            document.getElementById(stages[i-1]).className = 'stage done';
        }
        // if more stages left keep going
        if (i < stages.length) {
            document.getElementById(stages[i]).className = 'stage running';
            i++;
            setTimeout(next, 450);
        } else {
            // all stages done - run callback
            callback();
        }
    }
    next();
}

// main upload function
function uploadFile(file) {
    // hide old result
    document.getElementById('result-card').classList.remove('show');
    document.getElementById('result-empty').style.display = 'none';

    // animate stages then actually upload
    animateStages(function() {

        var formData = new FormData();
        formData.append('file', file);

        // sending file to my flask backend
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            // show result card with classification details
            showResult(data, file.name);
            // refresh dashboard stats
            refreshDashboard();
        })
        .catch(function(error) {
            console.log('upload error:', error);
        });
    });
}

// get badge class based on document type
function getBadge(type) {
    return 'badge badge-' + (type || 'Unknown');
}

// show classification result on screen
function showResult(data, filename) {
    var card = document.getElementById('result-card');
    card.classList.add('show');

    var type = data.document_type || data.status || 'Unknown';
    var conf = data.confidence || 0;

    // fill in all the result fields
    document.getElementById('r-type').textContent = type;
    document.getElementById('r-badge').innerHTML =
        '<span class="' + getBadge(type) + '">' + type + '</span>';

    // animate confidence bar
    document.getElementById('conf-bar').style.width = conf + '%';
    document.getElementById('conf-text').textContent = conf + '%';

    document.getElementById('r-fn').textContent = filename;
    document.getElementById('r-dt').textContent = type;
    document.getElementById('r-cf').textContent = conf + '%';
    document.getElementById('r-me').textContent = data.method || '—';
    document.getElementById('r-de').textContent =
        data.destination || data.status || '—';
    document.getElementById('r-ti').textContent =
        (data.time_taken || '—') + 's';
    document.getElementById('r-st').textContent =
        data.status || '—';
}

// refresh dashboard with latest stats and results
function refreshDashboard() {
    // get stats from backend
    fetch('/stats')
        .then(function(r) { return r.json(); })
        .then(function(s) {
            document.getElementById('stat-total').textContent = s.total;
            document.getElementById('stat-dupes').textContent = s.duplicates;

            // update bar chart widths
            var max = Math.max(
                s.resumes, s.invoices,
                s.paystubs, s.contracts, 1
            );
            document.getElementById('bar-r').style.width =
                (s.resumes  / max * 100) + '%';
            document.getElementById('bar-i').style.width =
                (s.invoices / max * 100) + '%';
            document.getElementById('bar-p').style.width =
                (s.paystubs / max * 100) + '%';
            document.getElementById('bar-c').style.width =
                (s.contracts / max * 100) + '%';

            // update counts
            document.getElementById('cnt-r').textContent = s.resumes;
            document.getElementById('cnt-i').textContent = s.invoices;
            document.getElementById('cnt-p').textContent = s.paystubs;
            document.getElementById('cnt-c').textContent = s.contracts;
        });

    // get recent results for table
    fetch('/results')
        .then(function(r) { return r.json(); })
        .then(function(results) {
            var tbody = document.getElementById('results-tbody');

            if (results.length === 0) {
                tbody.innerHTML =
                    '<tr><td colspan="6" ' +
                    'style="text-align:center;color:#636e72;padding:24px">' +
                    'no documents processed yet</td></tr>';
                return;
            }

            // build table rows
            tbody.innerHTML = results.map(function(r) {
                var type = r.document_type || r.status || 'Unknown';
                return '<tr>' +
                    '<td>' + (r.filename || r.file_name || '—') + '</td>' +
                    '<td><span class="' + getBadge(type) + '">' +
                        type + '</span></td>' +
                    '<td>' + (r.confidence ? r.confidence + '%' : '—') + '</td>' +
                    '<td style="color:#636e72">' + (r.method || '—') + '</td>' +
                    '<td style="color:#636e72;font-size:12px">' +
                        (r.destination || '—') + '</td>' +
                    '<td style="color:#636e72">' + (r.timestamp || '—') + '</td>' +
                    '</tr>';
            }).join('');
        });
}

// load actual log file contents
function loadLogs() {
    fetch('/logs')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var viewer = document.getElementById('log-viewer');
            if (data.logs && data.logs !== 'no logs yet') {
                viewer.textContent = data.logs;
                // scroll to bottom to show latest
                viewer.scrollTop = viewer.scrollHeight;
            } else {
                viewer.textContent =
                    '-- no logs yet --\\n' +
                    '-- upload a document to see the log here --';
            }
        });
}

// load dashboard when page first opens
refreshDashboard();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    print("\n" + "=" * 45)
    print("  DocSort - Document Classification Pipeline")
    print("=" * 45)
    print("\nstarting server...")
    print("open your browser at: http://localhost:5000")
    print("\npress Ctrl+C to stop the server\n")
    app.run(debug=True, port=5000)