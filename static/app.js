// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Service Worker registered'))
            .catch(err => console.log('Service Worker registration failed:', err));
    });
}

// Install button
let deferredPrompt;
const installBtn = document.getElementById('installBtn');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    installBtn.style.display = 'block';
});

installBtn.addEventListener('click', async () => {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response: ${outcome}`);
        deferredPrompt = null;
        installBtn.style.display = 'none';
    }
});

// API base URL
const API_BASE = '/api';

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Update tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');
        
        // Load content
        if (tabName === 'problems') {
            loadProblems();
        } else if (tabName === 'results') {
            loadResults();
        }
    });
});

// Load problems
async function loadProblems() {
    const problemsList = document.getElementById('problemsList');
    problemsList.innerHTML = '<div class="loading">Loading problems...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/problems`);
        const data = await response.json();
        
        if (data.error) {
            problemsList.innerHTML = `<div class="error">Error: ${data.error}</div>`;
            return;
        }
        
        displayProblems(data.problems);
    } catch (error) {
        problemsList.innerHTML = `<div class="error">Error loading problems: ${error.message}</div>`;
    }
}

// Display problems
function displayProblems(problems) {
    const problemsList = document.getElementById('problemsList');
    const searchInput = document.getElementById('searchInput');
    
    function renderProblems(filteredProblems) {
        if (filteredProblems.length === 0) {
            problemsList.innerHTML = '<div class="loading">No problems found</div>';
            return;
        }
        
        problemsList.innerHTML = filteredProblems.map(problem => `
            <div class="problem-card" onclick="showProblem('${problem.task_id}')">
                <div class="task-id">${problem.task_id}</div>
                <h3>${problem.entry_point || 'Problem'}</h3>
                <div class="prompt-preview">${escapeHtml(problem.prompt)}</div>
            </div>
        `).join('');
    }
    
    renderProblems(problems);
    
    // Search functionality
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = problems.filter(p => 
            p.task_id.toLowerCase().includes(query) ||
            p.prompt.toLowerCase().includes(query) ||
            (p.entry_point && p.entry_point.toLowerCase().includes(query))
        );
        renderProblems(filtered);
    });
}

// Show problem detail
async function showProblem(taskId) {
    try {
        const response = await fetch(`${API_BASE}/problems/${taskId}`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error}`);
            return;
        }
        
        const problem = data.problem;
        const modal = document.getElementById('problemModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        
        modalTitle.textContent = problem.task_id;
        modalBody.innerHTML = `
            <div class="form-group">
                <label>Entry Point:</label>
                <div class="code-block">${escapeHtml(problem.entry_point)}</div>
            </div>
            <div class="form-group">
                <label>Prompt:</label>
                <div class="code-block">${escapeHtml(problem.prompt)}</div>
            </div>
            ${problem.test ? `
            <div class="form-group">
                <label>Test:</label>
                <div class="code-block">${escapeHtml(problem.test)}</div>
            </div>
            ` : ''}
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        alert(`Error loading problem: ${error.message}`);
    }
}

// Close modal
document.querySelector('.close').addEventListener('click', () => {
    document.getElementById('problemModal').style.display = 'none';
});

window.onclick = (event) => {
    const modal = document.getElementById('problemModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

// Load results
async function loadResults() {
    const resultsList = document.getElementById('resultsList');
    resultsList.innerHTML = '<div class="loading">Loading results...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/results`);
        const data = await response.json();
        
        if (data.error) {
            resultsList.innerHTML = `<div class="error">Error: ${data.error}</div>`;
            return;
        }
        
        if (data.results.length === 0) {
            resultsList.innerHTML = '<div class="loading">No results files found</div>';
            return;
        }
        
        resultsList.innerHTML = data.results.map(result => `
            <div class="result-item" onclick="loadResultFile('${result.filename}')">
                <h3>${result.filename}</h3>
            </div>
        `).join('');
    } catch (error) {
        resultsList.innerHTML = `<div class="error">Error loading results: ${error.message}</div>`;
    }
}

// Load result file
async function loadResultFile(filename) {
    try {
        const response = await fetch(`${API_BASE}/results/${filename}`);
        const data = await response.json();
        
        if (data.error) {
            alert(`Error: ${data.error}`);
            return;
        }
        
        const modal = document.getElementById('problemModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        
        modalTitle.textContent = filename;
        modalBody.innerHTML = `
            <div class="form-group">
                <label>Total Results: ${data.results.length}</label>
                <div class="code-block" style="max-height: 400px; overflow-y: auto;">
${JSON.stringify(data.results, null, 2)}
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    } catch (error) {
        alert(`Error loading result file: ${error.message}`);
    }
}

// Evaluate
document.getElementById('evaluateBtn').addEventListener('click', async () => {
    const sampleFile = document.getElementById('sampleFile').value;
    const kValues = document.getElementById('kValues').value;
    const nWorkers = parseInt(document.getElementById('nWorkers').value);
    const timeout = parseFloat(document.getElementById('timeout').value);
    const resultsDiv = document.getElementById('evaluationResults');
    
    if (!sampleFile) {
        resultsDiv.innerHTML = '<div class="error">Please provide a sample file path</div>';
        return;
    }
    
    resultsDiv.innerHTML = '<div class="loading">Running evaluation...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sample_file: sampleFile,
                k: kValues,
                n_workers: nWorkers,
                timeout: timeout
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
            return;
        }
        
        resultsDiv.innerHTML = `
            <div class="form-group">
                <label>Evaluation Results:</label>
                <div class="code-block">
${JSON.stringify(data.results, null, 2)}
                </div>
            </div>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
});

// Refresh button
document.getElementById('refreshBtn').addEventListener('click', () => {
    const activeTab = document.querySelector('.tab.active');
    if (activeTab) {
        const tabName = activeTab.dataset.tab;
        if (tabName === 'problems') {
            loadProblems();
        } else if (tabName === 'results') {
            loadResults();
        }
    }
});

// Utility function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load initial content
loadProblems();
