# DocSort — Automated Document Classification Pipeline

Built by **Nisha Mayilraj**

An automated pipeline that identifies document types and routes them to the correct nested folder structure using Machine Learning.

---

## What It Does

Upload a document → System reads it → ML model classifies it → Routes to correct folder → Logs everything → Zero manual work

**Supported Categories:**
- Resume → `documents/hr/resumes/`
- Invoice → `documents/finance/invoices/`
- Paystub → `documents/finance/paystubs/`
- Contract → `documents/legal/contracts/`

---

## Two Versions Built

### Local Version
- Flask web dashboard with drag and drop
- TF-IDF + Logistic Regression (98.21% accuracy)
- Ollama llama3 AI fallback for low confidence
- 7 file types supported
- MD5 duplicate detection
- Processing audit log

### AWS Version
- Fully automatic serverless pipeline
- S3 intake bucket → Lambda → S3 organized bucket
- AWS Textract for text extraction
- Same model.pkl deployed to Lambda
- DynamoDB for cloud logging
- Zero manual work

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Web Framework | Flask |
| ML Library | scikit-learn |
| ML Algorithm | TF-IDF + Logistic Regression |
| PDF Reading | pdfplumber |
| Word Reading | python-docx |
| Image OCR | pytesseract |
| AI Fallback | Ollama llama3 |
| Cloud Compute | AWS Lambda |
| Cloud Storage | Amazon S3 |
| Text Extraction | AWS Textract |
| Cloud Database | Amazon DynamoDB |
| Security | AWS IAM |

---

## Project Structure

```
document_classifier/
├── folder_setup.py     # Folder creation, validation, reports
├── train.py            # Train ML model
├── extractor.py        # Text extraction from all file types
├── classifier.py       # ML classification + Ollama fallback
├── pipeline.py         # 7-stage pipeline controller
├── app.py              # Flask web dashboard
├── lambda_function.py  # AWS Lambda function
├── ml_model/           # Trained model files (not in repo)
├── training_data/      # Training samples
├── uploads/            # Temporary file landing zone
├── documents/          # Organized output folders
└── logs/               # Processing audit trail
```

---

## ML Model

- **Algorithm:** TF-IDF Vectorizer + Logistic Regression
- **Training samples:** 277 (50 resumes, 78 invoices, 70 paystubs, 80 contracts)
- **Test accuracy:** 98.21%
- **Confidence threshold:** 70% (below → Ollama AI fallback)

---

## 7 Pipeline Stages

1. **Validation** — Check file exists and is not empty
2. **Duplicate Detection** — MD5 hash fingerprinting
3. **Text Extraction** — Format-specific library per file type
4. **Classification** — ML model with confidence threshold
5. **File Movement** — Route to correct nested folder
6. **Verification** — Confirm file arrived correctly
7. **Report & Log** — Append to audit trail

---

## Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Empty file | → unreadable folder |
| Duplicate file | → duplicates folder |
| Corrupted file | → unreadable folder |
| Unsupported type (.mp4, .exe) | → unsupported folder |
| PPTX/XLSX files | → unknown folder |
| Low confidence (<70%) | → Ollama AI fallback |
| Unknown document type | → unknown folder |

---

## AWS Architecture

```
Upload to S3 intake bucket
         ↓
S3 Event Notification fires
         ↓
Lambda wakes up automatically
         ↓
AWS Textract extracts text
         ↓
ML model classifies document
(same model.pkl as local)
         ↓
File moved to correct S3 folder
         ↓
DynamoDB logs the result
         ↓
Done in ~3 seconds
```

---

## How to Run Locally

```bash
# Install dependencies
pip install flask scikit-learn pdfplumber python-docx pytesseract openpyxl python-pptx ollama pillow

# Train the model (once)
python train.py

# Start the dashboard
python app.py

# Open browser
http://localhost:5000
```

---

## Key Engineering Decisions

- **TF-IDF over BERT** — 277 samples too small for neural networks. LR gives confidence scores. 98% accuracy proves it works.
- **70% confidence threshold** — Tested multiple values. 70% is the sweet spot between trusting ML and using Ollama.
- **Flask over Django** — Only need 4 API endpoints. Django would be overkill.
- **pdfplumber over PyPDF2** — PyPDF2 missed text in complex PDF layouts. Real decision made during development.
- **MD5 for duplicates** — Content-based detection. Renaming a file cannot fool it.
- **CloudShell for Lambda layer** — sklearn needs Amazon Linux binaries. CloudShell runs on Amazon Linux.
- **DynamoDB over RDS** — Serverless like Lambda. No running server cost.
- **Lambda over EC2** — Pay per millisecond. No server management. Auto scales.