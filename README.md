<h1 align="center">🚛 Logistics AI Assistant</h1>

<p align="center">
  <b>RAG-powered AI assistant for Transportation Management System (TMS) document intelligence.</b><br>
  Upload logistics documents • Ask natural language questions • Extract structured shipment data • Get confidence-scored, guardrail-protected responses
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python">
  <img src="https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi">
  <img src="https://img.shields.io/badge/ChromaDB-Vector_Store-orange">
  <img src="https://img.shields.io/badge/OpenAI-GPT-black?logo=openai">
  <img src="https://img.shields.io/badge/License-MIT-purple">
</p>

<hr>

<h2>🎯 What It Does</h2>

<ul>
  <li><b>Ask questions in plain English</b> — grounded answers from your document (no hallucinations)</li>
  <li><b>Extract structured shipment data</b> — 11 key logistics fields into clean JSON</li>
  <li><b>Confidence scoring</b> — every response includes a composite confidence score</li>
  <li><b>Guardrails</b> — low-confidence or ungrounded answers are refused</li>
</ul>

<hr>

<h2>📐 Architecture Overview</h2>

<pre>
<img width="1046" height="300" alt="image" src="https://github.com/user-attachments/assets/ad4c9945-0dbf-47db-b412-77c511f5313c" />

</pre>

<hr>

<h2>🧠 Data Flow</h2>

<h3>Document Upload</h3>
<pre>
File → Parse Text → Smart Chunk → Generate Embeddings → Store in ChromaDB
</pre>

<h3>Question Answering (RAG)</h3>
<pre>
Question → Embed → Vector Search → Top-K → Build Context → LLM → Score → Guardrails
</pre>

<h3>Structured Extraction</h3>
<pre>
Document Text → LLM Prompt (or Regex Fallback) → 11-Field JSON → Confidence Score
</pre>

<hr>

<h2>🚀 Quick Start</h2>

<h3>Prerequisites</h3>
<ul>
  <li>Python 3.9+</li>
  <li>OpenAI API key (optional)</li>
</ul>

<h3>Run Locally</h3>

<pre><code>git clone https://github.com/rishitsharma/logistics-ai-assistant.git
cd logistics-ai-assistant
chmod +x run.sh
./run.sh
</code></pre>

Open → <b>http://localhost:8000</b>

<h3>Manual Setup</h3>

<pre><code>python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
</code></pre>

<h3>Docker</h3>

<pre><code>docker build -t logistics-ai-assistant .
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key logistics-ai-assistant
</code></pre>

<hr>

<h2>📡 API Endpoints</h2>

<table>
  <tr>
    <th>Endpoint</th>
    <th>Description</th>
  </tr>
  <tr>
    <td><code>GET /health</code></td>
    <td>Health check & configuration info</td>
  </tr>
  <tr>
    <td><code>POST /upload</code></td>
    <td>Upload a logistics document</td>
  </tr>
  <tr>
    <td><code>POST /ask</code></td>
    <td>Ask a question about an uploaded document</td>
  </tr>
  <tr>
    <td><code>POST /extract</code></td>
    <td>Extract structured shipment data</td>
  </tr>
</table>

<hr>

<h2>🛡️ Guardrails System</h2>

<ul>
  <li><b>Confidence Threshold</b> — refuses answers below 0.45</li>
  <li><b>Retrieval Similarity Floor</b> — rejects weak vector matches</li>
  <li><b>Hallucination Detection</b> — flags AI-style phrases</li>
  <li><b>Empty Answer Detection</b> — prevents non-answers</li>
</ul>

<p><b>Composite Confidence Formula:</b></p>

<pre>
Confidence = (0.40 × Retrieval) + (0.35 × Coverage) + (0.25 × Agreement)
</pre>

<hr>

<h2>📊 Structured Data Extraction</h2>

<p>Extracts 11 logistics fields:</p>

<ul>
  <li>shipment_id</li>
  <li>shipper</li>
  <li>consignee</li>
  <li>pickup_datetime</li>
  <li>delivery_datetime</li>
  <li>equipment_type</li>
  <li>mode</li>
  <li>rate</li>
  <li>currency</li>
  <li>weight</li>
  <li>carrier_name</li>
</ul>

<p><b>Dual Strategy:</b></p>
<ul>
  <li>LLM-based structured extraction (primary)</li>
  <li>50+ logistics-specific regex fallback patterns</li>
</ul>

<hr>

<h2>🧩 Chunking Strategy</h2>

<ul>
  <li><b>Section-aware splitting</b> (logistics headers detection)</li>
  <li><b>Sentence-boundary splitting</b> (no mid-sentence breaks)</li>
  <li><b>Character fallback</b> with overlap continuity</li>
</ul>

<p><b>Result:</b> Higher retrieval precision for semi-structured TMS documents.</p>

<hr>

<h2>⚠️ Known Limitations</h2>

<ul>
  <li>No OCR (scanned PDFs unsupported)</li>
  <li>Single-document queries only</li>
  <li>English-optimized embeddings</li>
  <li>Multiple shipments → extracts first only</li>
</ul>

<hr>

<h2>💡 Roadmap</h2>

<h3>Short-Term</h3>
<ul>
  <li>OCR support (Tesseract / Textract)</li>
  <li>Table-aware PDF parsing</li>
  <li>Multi-document queries</li>
</ul>

<h3>Long-Term</h3>
<ul>
  <li>Fine-tuned logistics embedding model</li>
  <li>ERP/TMS integrations (SAP TM, Oracle, MercuryGate)</li>
  <li>Anomaly detection for rates & weights</li>
</ul>

<hr>

<h2>🗂️ Project Structure</h2>

<pre>
backend/
  main.py
  document_processor.py
  retriever.py
  extractor.py
  guardrails.py
frontend/
  index.html
  styles.css
  app.js
sample_docs/
Dockerfile
Procfile
run.sh
README.md
</pre>

<hr>

<h2>🧪 Testing</h2>

<p>Swagger UI: <a href="http://localhost:8000/docs">http://localhost:8000/docs</a></p>
<p>ReDoc: <a href="http://localhost:8000/redoc">http://localhost:8000/redoc</a></p>

<hr>

<h2>📄 License</h2>

<p>MIT License — see <a href="LICENSE">LICENSE</a></p>

<hr>

<p align="center">
  Built for intelligent logistics document understanding 🚛
</p>
