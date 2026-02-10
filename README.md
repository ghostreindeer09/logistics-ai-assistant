# 🚛 Logistics AI Assistant

> RAG-powered AI assistant for Transportation Management System (TMS) document intelligence. Upload logistics documents, ask natural language questions, extract structured shipment data, and get confidence-scored, guardrail-protected responses.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT-black?logo=openai)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## 🎯 What It Does

Upload real-world logistics documents (Rate Confirmations, Bills of Lading, Freight Invoices) and:

- **Ask questions** in plain English — grounded answers from your document, not hallucinations
- **Extract structured data** — 11 key shipment fields pulled automatically into JSON
- **Confidence scoring** — every response includes a composite confidence percentage
- **Guardrails** — low-confidence or ungrounded answers are refused, never fabricated

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)                        │
│        Upload Documents │ Ask Questions │ Extract Data           │
└──────────┬──────────────┬──────────────┬──────────────┬─────────┘
           │              │              │              │
       POST /upload   POST /ask    POST /extract   GET /health
           │              │              │              │
┌──────────▼──────────────▼──────────────▼──────────────▼─────────┐
│                     FastAPI Backend                              │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐ │
│  │  Document       │  │  RAG            │  │  Structured        │ │
│  │  Processor      │  │  Retriever      │  │  Extractor         │ │
│  │                 │  │                 │  │                    │ │
│  │ • Parse PDF/    │  │ • Embed query   │  │ • LLM-driven      │ │
│  │   DOCX/TXT     │  │ • Vector search │  │   extraction      │ │
│  │ • Smart chunk   │  │ • Context build │  │ • 50+ regex       │ │
│  │ • Embed chunks  │  │ • LLM generate  │  │   patterns        │ │
│  │ • Store vectors │  │ • Score answer  │  │ • PDF artifact    │ │
│  │                 │  │                 │  │   cleanup         │ │
│  └───────┬─────────┘  └───────┬─────────┘  └────────────────────┘ │
│          │                    │                                    │
│  ┌───────▼────────────────────▼──────────────────────────────┐   │
│  │            Guardrails & Confidence Scoring                │   │
│  │                                                           │   │
│  │  • Confidence threshold gate (composite weighted score)   │   │
│  │  • Retrieval similarity floor (cosine threshold)          │   │
│  │  • Hallucination phrase detection                         │   │
│  │  • Empty/non-answer detection                             │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐   │
│  │  sentence-transformers   │  │        ChromaDB              │   │
│  │  all-MiniLM-L6-v2       │  │   (local persistent store)   │   │
│  │  384-dim embeddings      │  │   cosine similarity index    │   │
│  └─────────────────────────┘  └──────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI | REST endpoints with auto-generated OpenAPI docs |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) | Local, fast, free 384-dim embedding generation |
| **Vector Store** | ChromaDB (PersistentClient) | Local vector index with cosine similarity search |
| **LLM** | OpenAI GPT-3.5/4 (optional) | Answer generation & structured extraction |
| **Document Parsing** | PyPDF2, python-docx | PDF, DOCX, TXT support |
| **Frontend** | Vanilla HTML/CSS/JS | Premium dark UI, no build step required |

### Data Flow

```
Document Upload:
  File → Parse Text → Smart Chunk → Generate Embeddings → Store in ChromaDB

Question Answering (RAG):
  Question → Embed → Vector Search → Top-K Chunks → Build Context → LLM Generate → Score → Guardrails → Response

Structured Extraction:
  Document Text → LLM Prompt (or Regex Fallback) → 11-Field JSON → Confidence Score
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- OpenAI API key (optional — system works fully with regex fallback)

### Run Locally

```bash
# 1. Clone and navigate
git clone https://github.com/rishitsharma/logistics-ai-assistant.git
cd logistics-ai-assistant

# 2. Run the start script (handles venv, deps, .env automatically)
chmod +x run.sh
./run.sh

# 3. Open in browser
# → http://localhost:8000
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment (optional — works without OpenAI key)
cp .env.example .env
# Edit .env if you have an OpenAI API key

# Start the server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
docker build -t logistics-ai-assistant .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key logistics-ai-assistant
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key for LLM features (optional) |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model for Q&A and extraction |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE` | `512` | Maximum chunk size in characters |
| `CHUNK_OVERLAP` | `64` | Overlap between adjacent chunks |
| `TOP_K_RESULTS` | `5` | Number of chunks to retrieve per query |
| `CONFIDENCE_THRESHOLD` | `0.45` | Min confidence to return an answer (below = refused) |
| `PORT` | `8000` | Server port (auto-set by Render/Railway) |

---

## 🌐 Deployment

### Deploy to Render (Free Tier)

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add `OPENAI_API_KEY` in Environment Variables (optional)
6. Deploy → Your hosted URL is live

### Deploy to Railway

```bash
railway init
railway up
# Set environment variables in Railway dashboard
```

---

## 📡 API Endpoints

### `GET /health`
Health check with configuration info.

### `POST /upload`
Upload a logistics document for processing.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@sample_docs/rate_confirmation.txt"
```

**Response:**
```json
{
  "document_id": "ca43266893d33f9f",
  "filename": "rate_confirmation.txt",
  "num_chunks": 15,
  "message": "Document 'rate_confirmation.txt' processed successfully: 15 chunks created."
}
```

### `POST /ask`
Ask a natural language question about an uploaded document.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"document_id": "ca43266893d33f9f", "question": "What is the carrier rate?"}'
```

**Response:**
```json
{
  "answer": "The total rate is $3,575.00, including a line haul rate of $3,250.00 and a fuel surcharge of $325.00.",
  "confidence_score": 0.82,
  "sources": [
    {
      "text": "Line Haul Rate: $3,250.00\nFuel Surcharge: $325.00 (10%)\nTotal Rate: $3,575.00\nCurrency: USD",
      "chunk_index": 7,
      "similarity_score": 0.89
    }
  ],
  "guardrail_triggered": false,
  "guardrail_message": null
}
```

### `POST /extract`
Extract structured shipment data from a document.

```bash
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"document_id": "ca43266893d33f9f"}'
```

**Response:**
```json
{
  "document_id": "ca43266893d33f9f",
  "shipment_data": {
    "shipment_id": "SH-2024-56789",
    "shipper": "Acme Manufacturing Corp",
    "consignee": "Pacific Distribution Center",
    "pickup_datetime": "January 16, 2024",
    "delivery_datetime": "January 18, 2024",
    "equipment_type": "53' Dry Van",
    "mode": "FTL (Full Truckload)",
    "rate": "3575.00",
    "currency": "USD",
    "weight": "42,500 lbs",
    "carrier_name": "FastFreight Logistics LLC"
  },
  "confidence_score": 1.0,
  "extraction_notes": ["Extraction method: regex-based (LLM unavailable)", "Fields found: 11/11"]
}
```

---

## 🧩 Chunking Strategy

The system uses **intelligent, logistics-aware chunking** designed specifically for semi-structured TMS documents:

### 1. Section-Based Splitting (Primary)

Logistics documents have predictable structure. The chunker detects section boundaries using:

- **Header patterns**: Regex matching logistics-specific headers (`SHIPMENT DETAILS`, `RATE INFORMATION`, `CARRIER INFORMATION`, `CONSIGNEE`, etc.)
- **ALL-CAPS detection**: Lines that are entirely uppercase and < 60 chars are treated as headers
- **Short uppercase lines**: Common in rate confirmations and BOLs

Splits occur **at section boundaries**, keeping related fields (e.g., shipper name + address + contact) together in a single chunk.

### 2. Sentence-Boundary Splitting (Secondary)

For sections exceeding `CHUNK_SIZE` (default 512 chars):
- Splits at sentence terminators (`.`, `!`, `?`)
- Never breaks mid-sentence
- Preserves semantic coherence within each chunk

### 3. Character-Level Fallback (Rare)

For very long sentences (uncommon in logistics docs):
- Splits at `CHUNK_SIZE` with configurable `CHUNK_OVERLAP` (default 64 chars)
- Overlap ensures context continuity at boundaries

### Why This Approach?

| Approach | Pros | Cons |
|----------|------|------|
| **Fixed-size chunks** | Simple, predictable | Breaks mid-field, poor for structured docs |
| **Recursive text splitter** | Better boundaries | Not domain-aware |
| **Our approach** | Domain-aware, keeps fields together | Requires header detection heuristics |

Logistics documents are semi-structured with clear labeled sections. Section-aware chunking ensures related information stays together, **dramatically improving retrieval precision** — a question about "carrier rate" retrieves the rate section, not fragments scattered across chunks.

---

## 🔍 Retrieval Method

### Vector Similarity Search (RAG Pipeline)

```
Question → Embed (all-MiniLM-L6-v2) → ChromaDB Cosine Search → Top-K Chunks → LLM Context → Answer
```

**Step by step:**

1. **Query Embedding**: The user's question is embedded into a 384-dimensional vector using `all-MiniLM-L6-v2`
2. **Vector Search**: ChromaDB performs cosine similarity search across all stored chunks for that document
3. **Top-K Retrieval**: The K most similar chunks (default K=5) are returned with similarity scores
4. **Context Assembly**: Retrieved chunks are concatenated into a context prompt with metadata (source chunks, scores)
5. **LLM Generation**: OpenAI GPT generates an answer grounded strictly in the provided context
6. **Confidence Scoring**: The response is scored using a composite signal (see below)
7. **Guardrail Check**: If confidence < threshold, the answer is refused

### Extractive Fallback (No LLM)

When OpenAI is unavailable, the system uses **keyword-overlap extractive answering**:
- Tokenizes the question into significant words (stopwords removed)
- Scores each sentence in the top chunk by keyword overlap
- Returns the highest-scoring sentences as the answer
- This ensures the system is always functional, even without an API key

---

## 🛡️ Guardrails Approach

Four independent layers prevent hallucinated, fabricated, or low-quality answers:

| # | Guardrail | Trigger Condition | Action |
|---|-----------|-------------------|--------|
| 1 | **Confidence Threshold** | Composite score < 0.45 | Refuses answer: *"Confidence too low to provide a reliable answer"* |
| 2 | **Low Retrieval Similarity** | Top chunk similarity < 0.25 | Refuses answer: *"No relevant content found in the document"* |
| 3 | **Hallucination Detection** | Answer contains phrases like "as an AI", "based on my training", "I don't have access" | Flags with warning: answer may not be grounded |
| 4 | **Empty Answer Detection** | Answer < 10 characters or generic non-answers | Refuses answer: *"Unable to find relevant information"* |

### Prompt-Level Guardrails

The LLM system prompt enforces:
- **Strict context grounding**: "Answer ONLY based on the provided context"
- **No external knowledge**: "Never use your general training knowledge"
- **Explicit uncertainty**: "If information is not in the context, say 'not found in the document'"
- **Low temperature** (0.1): Minimizes creative/speculative outputs

### Why Multiple Layers?

Single guardrails have gaps. Our layered approach catches failures from **different sources**:
- Layer 1+2: Catches poor retrieval (question unrelated to document)
- Layer 3: Catches LLM prompt injection / hallucination leakage
- Layer 4: Catches degenerate LLM outputs (empty, refusal loops)

---

## 📊 Confidence Scoring Method

Every response includes a **composite confidence score** (0.0–1.0) built from three independent signals:

### Composite Formula

```
Confidence = (0.40 × Retrieval) + (0.35 × Coverage) + (0.25 × Agreement)
```

### Signal Breakdown

| Signal | Weight | What It Measures | How |
|--------|--------|------------------|-----|
| **Retrieval Confidence** | 40% | How well the vector search matched | Weighted blend of top-1 score (50%), score gap between #1 and #2 (20%), mean score (30%) |
| **Answer Coverage** | 35% | How grounded the answer is in sources | Fraction of significant answer words that appear in source chunks |
| **Chunk Agreement** | 25% | Cross-chunk corroboration | How many retrieved chunks independently contain the key terms from the answer |

### Sub-Signal: Retrieval Confidence

```
Retrieval = (0.50 × top1_score) + (0.20 × score_gap) + (0.30 × mean_score)
```

- **Top-1 Score**: Direct cosine similarity of the best match (0–1)
- **Score Gap**: Difference between #1 and #2 results — a large gap means the answer is distinctive and focused
- **Mean Score**: Average similarity across all K results — higher means the whole document is relevant

### Score Interpretation

| Range | Label | Meaning |
|-------|-------|---------|
| **≥ 0.70** | ✅ High | Answer is well-grounded, likely correct |
| **0.45–0.69** | ⚠️ Medium | Answer probably correct, verify important details |
| **< 0.45** | ❌ Low | Guardrail triggers — answer is refused |

### For Extraction (`/extract`)

The extraction confidence is simpler: `fields_found / total_fields`. If 9 out of 11 fields are extracted, confidence = 0.818.

---

## 🔧 Structured Data Extraction

The `/extract` endpoint pulls 11 key logistics fields from any uploaded document:

| Field | Description | Example |
|-------|-------------|---------|
| `shipment_id` | Shipment/load/reference number | `LD53657`, `SH-2024-56789` |
| `shipper` | Origin company/party | `Acme Manufacturing Corp` |
| `consignee` | Destination company/party | `Pacific Distribution Center` |
| `pickup_datetime` | Pickup date/time | `02-08-2026`, `January 16, 2024` |
| `delivery_datetime` | Delivery date/time | `02-08-2026` |
| `equipment_type` | Trailer/equipment type | `Flatbed`, `53' Dry Van`, `Reefer` |
| `mode` | Transportation mode | `FTL`, `LTL`, `Intermodal` |
| `rate` | Freight rate (numeric) | `400.00`, `3575.00` |
| `currency` | Rate currency | `USD`, `CAD`, `EUR` |
| `weight` | Shipment weight | `56000.00 lbs`, `42,500 lbs` |
| `carrier_name` | Carrier company | `SWIFT SHIFT LOGISTICS LLC` |

### Dual Extraction Strategy

1. **LLM-based** (primary): Sends full document text to OpenAI with a structured extraction prompt. Works across any document format.

2. **Regex-based** (fallback): 50+ specialized regex patterns handle:
   - **Label:value formats**: `Shipper: Acme Corp`
   - **Section header formats**: `Shipper Information` followed by data lines
   - **Table-based formats**: `CARRIER MC PHONE EQUIPMENT` column headers with data rows below
   - **PDF concatenation artifacts**: `FTLShipping Date` → `FTL Shipping Date`
   - **TMS-specific patterns**: Ultraship TMS `Pickup`/`Drop` sections, `Reference ID` fields
   - **Value validation**: Rejects table headers, dash-only values, and implausible numbers

### Supported Document Formats

| Format | Tested With |
|--------|------------|
| Rate Confirmations (TXT, PDF) | Sample rate confirmations, Ultraship TMS RC PDFs |
| Bills of Lading (TXT, PDF) | Sample BOLs, Ultraship TMS BOL PDFs |
| Freight Invoices (TXT) | Sample freight invoices |

---

## ❌ Known Failure Cases

### Document Parsing

1. **Scanned/image-based PDFs**: No OCR — scanned PDFs produce empty text and are rejected with an error
2. **Complex nested tables**: Multi-level nested tables in PDFs may parse with jumbled text ordering
3. **Very short documents**: Documents with < 20 characters of extractable text are rejected
4. **Password-protected PDFs**: Cannot be opened or processed

### Retrieval & Answering

5. **Ambiguous questions**: "What is the rate?" may match multiple rate types (per-mile, total, fuel surcharge). Returns all relevant info but confidence may be lower
6. **Cross-document queries**: Only supports single-document queries per request
7. **Non-English documents**: Embedding model optimized for English — other languages have degraded retrieval
8. **Very large documents**: Text > 12,000 chars is truncated for LLM extraction (full text still used for RAG)

### Extraction

9. **Non-standard field labels**: Documents using unusual terminology (e.g., "Transportation Provider" instead of "Carrier") may miss fields
10. **Merged/concatenated cells**: PDF extraction sometimes merges adjacent cells — the regex engine handles common patterns but can't cover all variations
11. **Multiple shipments in one document**: Extracts data from the first/most prominent shipment only

---

## 💡 Improvement Ideas

### Short-term (Days)
1. **OCR integration**: Add Tesseract or AWS Textract for scanned PDF support
2. **Table-aware parsing**: Use Camelot or Tabula for better structured table extraction from PDFs
3. **Multi-document queries**: Cross-reference data across multiple uploaded documents
4. **Streaming responses**: Use SSE for real-time answer streaming

### Medium-term (Weeks)
5. **Fine-tuned embedding model**: Train a logistics-domain embedding model for better retrieval
6. **Confidence calibration**: Calibrate scores against human-labeled ground truth
7. **Entity linking**: Link extracted entities to master data (carrier databases, SCAC codes, UN/LOCODE)
8. **Batch processing**: Upload and process multiple documents simultaneously
9. **Document comparison**: Compare two documents (e.g., Rate Confirmation vs. Invoice) for discrepancies

### Long-term (Months)
10. **Custom LLM fine-tuning**: Fine-tune on logistics documents for better extraction and answering
11. **Multi-language support**: Extend to Spanish, Chinese, etc. with multilingual embeddings
12. **Audit trail & compliance**: Log all queries and answers with tamper-proof audit trail
13. **ERP/TMS integration**: Direct API integration with SAP TM, Oracle, MercuryGate, etc.
14. **Anomaly detection**: Flag unusual rates, weights, or routes automatically

---

## 🗂️ Project Structure

```
logistics-ai-assistant/
├── backend/
│   ├── main.py                  # FastAPI app, endpoints, static file serving
│   ├── document_processor.py    # Parse → chunk → embed → store pipeline
│   ├── retriever.py             # RAG: vector search → context → LLM → score
│   ├── extractor.py             # Structured extraction (LLM + 50+ regex patterns)
│   ├── guardrails.py            # Confidence scoring & guardrail logic
│   ├── models.py                # Pydantic request/response schemas
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── index.html               # Main UI page (semantic HTML5)
│   ├── styles.css               # Premium dark theme design system
│   └── app.js                   # Frontend application logic (vanilla JS)
├── sample_docs/
│   ├── rate_confirmation.txt    # Sample rate confirmation
│   ├── bill_of_lading.txt       # Sample bill of lading
│   └── freight_invoice.txt      # Sample freight invoice
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
├── Dockerfile                   # Container deployment
├── Procfile                     # Render/Railway deployment
├── run.sh                       # One-command local start script
└── README.md                    # This documentation
```

---

## 🧪 Testing

### Quick Test with curl

```bash
# Upload a document
curl -X POST http://localhost:8000/upload -F "file=@sample_docs/rate_confirmation.txt"

# Ask a question (use the document_id from upload response)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"document_id": "YOUR_DOC_ID", "question": "What is the total freight rate?"}'

# Extract structured data
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"document_id": "YOUR_DOC_ID"}'
```

### Interactive API Docs

FastAPI auto-generates interactive documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
