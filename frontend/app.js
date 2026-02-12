/**
 * Logistics AI Assistant — Frontend Application
 * Handles: upload, ask, extract interactions
 */

// ── Configuration ──────────────────────────────────────────────────
// Auto-detect: when served by the backend (Render), use same origin.
// When opened as a local file, fall back to localhost:8000.
const API_BASE = window.location.protocol === "file:"
    ? "http://localhost:8000"
    : window.location.origin;

// ── State ──────────────────────────────────────────────────────────
const state = {
    documents: [],       // [{id, filename, chunks}]
    activeDocId: null,
    conversationHistory: [],
};

// ── DOM References ─────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Tab Navigation ─────────────────────────────────────────────────
$$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        // Update buttons
        $$('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Update panels
        $$('.tab-panel').forEach(p => p.classList.remove('active'));
        $(`#panel-${tab}`).classList.add('active');
    });
});

// ── Toast Notifications ────────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = $('#toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Loading Overlay ────────────────────────────────────────────────
function showLoading(text = 'Processing...') {
    $('#loading-text').textContent = text;
    $('#loading-overlay').style.display = 'flex';
}

function hideLoading() {
    $('#loading-overlay').style.display = 'none';
}

// ── File Upload ────────────────────────────────────────────────────
const uploadZone = $('#upload-zone');
const fileInput = $('#file-input');

// Click to browse
uploadZone.addEventListener('click', () => fileInput.click());

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileUpload(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
});

async function handleFileUpload(file) {
    // Validate extension
    const allowedExts = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
        showToast(`Unsupported file type: ${ext}`, 'error');
        return;
    }

    // Show progress
    $('#upload-progress').style.display = 'block';
    $('#upload-result').style.display = 'none';
    const progressFill = $('#progress-fill');
    const progressText = $('#progress-text');

    progressFill.style.width = '15%';
    progressText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        progressFill.style.width = '40%';
        progressText.textContent = 'Parsing and chunking document...';

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData,
        });

        progressFill.style.width = '80%';
        progressText.textContent = 'Creating embeddings...';

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await response.json();

        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';

        // Show result
        setTimeout(() => {
            $('#upload-progress').style.display = 'none';
            $('#upload-result').style.display = 'block';
            $('#result-filename').textContent = data.filename;
            $('#result-detail').textContent = `${data.num_chunks} chunks created and embedded`;
            $('#result-doc-id').textContent = data.document_id;

            // Add to state
            state.documents.push({
                id: data.document_id,
                filename: data.filename,
                chunks: data.num_chunks,
            });
            state.activeDocId = data.document_id;

            updateDocumentSelectors();
            updateDocumentHistory();
            showToast(`Document "${data.filename}" processed successfully!`, 'success');
        }, 600);

    } catch (error) {
        progressFill.style.width = '0%';
        $('#upload-progress').style.display = 'none';
        showToast(`Upload failed: ${error.message}`, 'error');
    }
}

// ── Document Selectors ─────────────────────────────────────────────
function updateDocumentSelectors() {
    const selects = ['#ask-doc-select', '#extract-doc-select'];
    selects.forEach(sel => {
        const select = $(sel);
        select.innerHTML = '';
        if (state.documents.length === 0) {
            select.innerHTML = '<option value="">— Upload a document first —</option>';
        } else {
            state.documents.forEach(doc => {
                const opt = document.createElement('option');
                opt.value = doc.id;
                opt.textContent = `${doc.filename} (${doc.id})`;
                if (doc.id === state.activeDocId) opt.selected = true;
                select.appendChild(opt);
            });
        }
    });

    // Enable/disable inputs
    const hasDoc = state.documents.length > 0;
    $('#question-input').disabled = !hasDoc;
    $('#ask-btn').disabled = !hasDoc;
    $('#extract-btn').disabled = !hasDoc;
}

function updateDocumentHistory() {
    if (state.documents.length === 0) {
        $('#doc-history-card').style.display = 'none';
        return;
    }

    $('#doc-history-card').style.display = 'block';
    const list = $('#doc-list');
    list.innerHTML = '';

    state.documents.forEach(doc => {
        const item = document.createElement('div');
        item.className = 'doc-item';
        item.innerHTML = `
            <span class="doc-item-name">📄 ${doc.filename}</span>
            <span class="doc-item-id">${doc.id} · ${doc.chunks} chunks</span>
        `;
        item.addEventListener('click', () => {
            state.activeDocId = doc.id;
            updateDocumentSelectors();
            showToast(`Selected: ${doc.filename}`, 'info');
        });
        list.appendChild(item);
    });
}

// ── Ask Questions ──────────────────────────────────────────────────
const questionInput = $('#question-input');
const askBtn = $('#ask-btn');

askBtn.addEventListener('click', () => submitQuestion());

questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !askBtn.disabled) submitQuestion();
});

// Quick question buttons
$$('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const q = btn.dataset.q;
        questionInput.value = q;
        if (!askBtn.disabled) submitQuestion();
    });
});

async function submitQuestion() {
    const docId = $('#ask-doc-select').value;
    const question = questionInput.value.trim();

    if (!docId) {
        showToast('Please select a document first.', 'error');
        return;
    }
    if (!question) {
        showToast('Please enter a question.', 'error');
        return;
    }

    showLoading('Searching document and generating answer...');

    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: docId, question }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Request failed');
        }

        const data = await response.json();
        displayAnswer(data, question);

        // Add to history
        state.conversationHistory.unshift({ question, answer: data });
        updateConversationHistory();

    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

function displayAnswer(data, question) {
    // Show answer card
    const card = $('#answer-card');
    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Confidence badge
    const badge = $('#confidence-badge');
    const confVal = $('#confidence-value');
    const confPercent = Math.round(data.confidence_score * 100);
    confVal.textContent = `${confPercent}%`;

    badge.className = 'confidence-badge';
    if (confPercent >= 70) badge.classList.add('high');
    else if (confPercent >= 45) badge.classList.add('medium');
    else badge.classList.add('low');

    // Guardrail alert
    const guardrailAlert = $('#guardrail-alert');
    if (data.guardrail_triggered) {
        guardrailAlert.style.display = 'flex';
        $('#guardrail-text').textContent = data.guardrail_message || 'Guardrail triggered — answer may not be fully grounded.';
    } else {
        guardrailAlert.style.display = 'none';
    }

    // Answer body
    $('#answer-body').textContent = data.answer;

    // Sources
    const sourcesList = $('#sources-list');
    sourcesList.innerHTML = '';

    if (data.sources && data.sources.length > 0) {
        $('#sources-section').style.display = 'block';
        data.sources.forEach((source, i) => {
            const score = Math.round(source.similarity_score * 100);
            let scoreClass = 'low';
            if (score >= 70) scoreClass = 'high';
            else if (score >= 45) scoreClass = 'medium';

            const item = document.createElement('div');
            item.className = 'source-item';
            item.innerHTML = `
                <div class="source-meta">
                    <span>Chunk #${source.chunk_index}</span>
                    <span class="source-badge ${scoreClass}">${score}% match</span>
                </div>
                <div class="source-text">${escapeHtml(source.text)}</div>
            `;
            sourcesList.appendChild(item);
        });
    } else {
        $('#sources-section').style.display = 'none';
    }

    questionInput.value = '';
}

function updateConversationHistory() {
    if (state.conversationHistory.length === 0) {
        $('#history-card').style.display = 'none';
        return;
    }

    $('#history-card').style.display = 'block';
    const container = $('#conversation-history');
    container.innerHTML = '';

    state.conversationHistory.slice(0, 10).forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';
        const confPercent = Math.round(item.answer.confidence_score * 100);
        div.innerHTML = `
            <div class="history-question">❓ ${escapeHtml(item.question)}</div>
            <div class="history-answer">${escapeHtml(item.answer.answer)}</div>
            <div class="history-confidence">Confidence: ${confPercent}%${item.answer.guardrail_triggered ? ' · ⚠️ Guardrail triggered' : ''}</div>
        `;
        div.addEventListener('click', () => {
            questionInput.value = item.question;
        });
        container.appendChild(div);
    });
}

$('#clear-history-btn').addEventListener('click', () => {
    state.conversationHistory = [];
    updateConversationHistory();
    showToast('History cleared', 'info');
});

// ── Structured Extraction ──────────────────────────────────────────
$('#extract-btn').addEventListener('click', async () => {
    const docId = $('#extract-doc-select').value;
    if (!docId) {
        showToast('Please select a document first.', 'error');
        return;
    }

    showLoading('Extracting structured shipment data...');

    try {
        const response = await fetch(`${API_BASE}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: docId }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Extraction failed');
        }

        const data = await response.json();
        displayExtraction(data);

    } catch (error) {
        showToast(`Extraction error: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
});

function displayExtraction(data) {
    const card = $('#extract-result-card');
    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Confidence
    const confPercent = Math.round(data.confidence_score * 100);
    const badge = $('#extract-confidence-badge');
    $('#extract-confidence-value').textContent = `${confPercent}%`;
    badge.className = 'confidence-badge';
    if (confPercent >= 70) badge.classList.add('high');
    else if (confPercent >= 45) badge.classList.add('medium');
    else badge.classList.add('low');

    // Notes
    const notesEl = $('#extract-notes');
    notesEl.innerHTML = '';
    if (data.extraction_notes) {
        data.extraction_notes.forEach(note => {
            const p = document.createElement('p');
            p.className = 'extract-note';
            p.textContent = `ℹ️ ${note}`;
            notesEl.appendChild(p);
        });
    }

    // Table
    const tbody = $('#extract-tbody');
    tbody.innerHTML = '';
    const fieldLabels = {
        shipment_id: 'Shipment ID',
        shipper: 'Shipper',
        consignee: 'Consignee',
        pickup_datetime: 'Pickup Date/Time',
        delivery_datetime: 'Delivery Date/Time',
        equipment_type: 'Equipment Type',
        mode: 'Mode',
        rate: 'Rate',
        currency: 'Currency',
        weight: 'Weight',
        carrier_name: 'Carrier Name',
    };

    const shipment = data.shipment_data;
    for (const [key, label] of Object.entries(fieldLabels)) {
        const val = shipment[key];
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${label}</td>
            <td class="${val ? 'field-found' : 'field-null'}">${val || 'null'}</td>
        `;
        tbody.appendChild(tr);
    }

    // JSON output
    const jsonEl = $('#json-output');
    jsonEl.textContent = JSON.stringify(data.shipment_data, null, 2);
}

// Copy JSON
$('#copy-json-btn').addEventListener('click', () => {
    const json = $('#json-output').textContent;
    navigator.clipboard.writeText(json).then(() => {
        showToast('JSON copied to clipboard', 'success');
    });
});

// ── Utilities ──────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Initialize ─────────────────────────────────────────────────────
updateDocumentSelectors();
console.log('🚛 Logistics AI Assistant loaded');
