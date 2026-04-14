/**
 * main.js  —  AI Text Analysis Pro
 * Full frontend logic: Summarizer, Analytics, History, Comparison
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Elements ──────────────────────────────────────────────────────────────
    const tabs          = document.querySelectorAll('.nav-item[data-tab]');
    const tabContents   = document.querySelectorAll('.tab-content');
    const methodBtns    = document.querySelectorAll('.method-btn');
    const methodContents= document.querySelectorAll('.method-content');
    const summarizeBtn  = document.getElementById('summarizeBtn');
    const sourceText    = document.getElementById('sourceText');
    const resultsArea   = document.getElementById('resultsArea');
    const summaryResult = document.getElementById('summaryResult');
    const loader        = document.getElementById('loader');
    const loaderMsg     = document.getElementById('loaderMessage');

    // Stats Elements (Summarizer tab)
    const compressionVal = document.getElementById('compressionVal');
    const readabilityVal = document.getElementById('readabilityVal');
    const sentimentVal   = document.getElementById('sentimentVal');
    const inputTypeBadge = document.getElementById('inputTypeBadge');

    // Chart instances (so we can destroy/recreate)
    let sentimentChartInstance = null;
    let methodChartInstance    = null;
    let compareBarChartInstance= null;

    // ── Toast Notifications ───────────────────────────────────────────────────
    // Creates a non-blocking, auto-dismissing notification (replaces alert())
    function showToast(message, type = 'info', duration = 4500) {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.cssText = [
                'position:fixed', 'bottom:1.5rem', 'right:1.5rem',
                'display:flex', 'flex-direction:column', 'gap:0.6rem',
                'z-index:9999', 'max-width:360px'
            ].join(';');
            document.body.appendChild(container);
        }

        const colors = {
            info:    { bg: 'rgba(99,102,241,0.95)',  icon: 'ℹ️' },
            success: { bg: 'rgba(16,185,129,0.95)',  icon: '✅' },
            warning: { bg: 'rgba(245,158,11,0.95)',  icon: '⚠️' },
            error:   { bg: 'rgba(239,68,68,0.95)',   icon: '❌' },
        };
        const { bg, icon } = colors[type] || colors.info;

        const toast = document.createElement('div');
        toast.style.cssText = [
            `background:${bg}`, 'color:#fff', 'padding:0.75rem 1rem',
            'border-radius:12px', 'font-size:0.875rem', 'line-height:1.4',
            'box-shadow:0 4px 20px rgba(0,0,0,0.35)',
            'display:flex', 'align-items:flex-start', 'gap:0.5rem',
            'opacity:0', 'transform:translateY(12px)',
            'transition:opacity 0.3s ease, transform 0.3s ease',
            'backdrop-filter:blur(8px)', 'cursor:pointer'
        ].join(';');
        toast.innerHTML = `<span style="font-size:1rem;flex-shrink:0">${icon}</span><span>${message}</span>`;
        toast.onclick = () => dismissToast(toast);
        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });

        const timer = setTimeout(() => dismissToast(toast), duration);
        toast._timer = timer;

        function dismissToast(t) {
            clearTimeout(t._timer);
            t.style.opacity = '0';
            t.style.transform = 'translateY(12px)';
            setTimeout(() => t.remove(), 300);
        }
    }

    // ── Model Status Badge ────────────────────────────────────────────────────
    // Injects a live status pill into the navbar and polls /api/health every 30s
    function initModelStatusBadge() {
        const nav = document.querySelector('.nav-actions') || document.querySelector('nav');
        if (!nav) return;

        const badge = document.createElement('span');
        badge.id = 'modelStatusBadge';
        badge.style.cssText = [
            'font-size:0.72rem', 'padding:0.25rem 0.65rem', 'border-radius:999px',
            'font-weight:600', 'letter-spacing:0.03em', 'cursor:default',
            'transition:background 0.4s,color 0.4s', 'white-space:nowrap',
            'background:rgba(148,163,184,0.2)', 'color:var(--text-muted,#94a3b8)'
        ].join(';');
        badge.textContent = '⬤ Checking…';
        nav.prepend(badge);

        async function pollHealth() {
            try {
                const res  = await fetch('/api/health', { signal: AbortSignal.timeout(5000) });
                const data = await res.json();

                if (data.model_status === 'ready') {
                    badge.textContent = '🟢 AI Ready';
                    badge.style.background = 'rgba(16,185,129,0.15)';
                    badge.style.color = '#10b981';
                } else if (data.model_status === 'fallback') {
                    badge.textContent = '🟡 Fallback Mode';
                    badge.style.background = 'rgba(245,158,11,0.15)';
                    badge.style.color = '#f59e0b';
                } else {
                    throw new Error('unhealthy');
                }
            } catch (_) {
                badge.textContent = '🔴 Offline';
                badge.style.background = 'rgba(239,68,68,0.15)';
                badge.style.color = '#ef4444';
            }
        }

        pollHealth();
        setInterval(pollHealth, 30_000);
    }

    initModelStatusBadge();

    // ── Loader ────────────────────────────────────────────────────────────────
    function showLoader(show, msg = 'AI is thinking…') {
        if (loader) loader.style.display = show ? 'flex' : 'none';
        if (loaderMsg) loaderMsg.textContent = msg;
        if (summarizeBtn) summarizeBtn.disabled = show;
    }

    function getSentimentColor(label) {
        if (label === 'Positive') return '#10b981';
        if (label === 'Negative') return '#ef4444';
        return 'var(--primary)';
    }

    function formatModelName(key) {
        const map = {
            lsa: 'LSA', text_rank: 'TextRank', lex_rank: 'LexRank',
            abstractive: 'Transformer', extractive: 'Extractive'
        };
        return map[key] || key;
    }

    // ── Tab Management ────────────────────────────────────────────────────────
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            tabContents.forEach(c => c.classList.toggle('active', c.id === `${target}Tab`));

            const titleEl    = document.getElementById('pageTitle');
            const subtitleEl = document.getElementById('pageSubtitle');

            const titles = {
                summarizer: ['Smart Summarizer',        'AI-powered text analysis and distillation'],
                analytics:  ['Analytics Dashboard',     'Insights across all your summarizations'],
                history:    ['Summary History',         'Your recent summarization sessions'],
                compare:    ['Model Comparison',        'Run two models on the same text side-by-side'],
            };

            if (titles[target]) {
                titleEl.textContent    = titles[target][0];
                subtitleEl.textContent = titles[target][1];
            }

            if (target === 'history')   loadHistory();
            if (target === 'analytics') loadAnalytics();
        });
    });

    // ── Input Method Management ───────────────────────────────────────────────
    let activeMethod = 'text';
    methodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            activeMethod = btn.getAttribute('data-method');
            methodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            methodContents.forEach(c =>
                c.classList.toggle('active', c.id === `${activeMethod}Input`)
            );
        });
    });

    // ── File Upload Handlers ──────────────────────────────────────────────────
    const dropzone  = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                dropzone.querySelector('h3').textContent = 'File Selected:';
                dropzone.querySelector('p').textContent  = fileInput.files[0].name;
                dropzone.classList.add('file-selected');
            }
        });

        dropzone.addEventListener('dragover', e => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        ['dragleave', 'drop'].forEach(evt =>
            dropzone.addEventListener(evt, () => dropzone.classList.remove('drag-over'))
        );
        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }

    // ── Summarization Logic ───────────────────────────────────────────────────
    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', async () => {
            const method = document.getElementById('modelSelect')?.value || 'abstractive';
            const mode   = document.getElementById('modeSelect')?.value  || 'standard';

            showLoader(true, method === 'abstractive'
                ? 'Transformer model generating… (may take ~15-30 s on cold start)'
                : 'Extractive model summarizing…');

            try {
                let response;
                if (activeMethod === 'upload') {
                    const file = fileInput?.files[0];
                    if (!file) {
                        showToast('Please select a file before summarizing.', 'warning');
                        showLoader(false);
                        return;
                    }
                    const fd = new FormData();
                    fd.append('file', file);
                    fd.append('method', method);
                    fd.append('mode', mode);
                    response = await fetch('/api/upload', { method: 'POST', body: fd });
                } else {
                    const text = sourceText.value.trim();
                    if (!text || text.length < 50) {
                        showToast('Please enter at least 50 characters to summarize.', 'warning');
                        showLoader(false);
                        return;
                    }
                    response = await fetch('/api/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text, method, mode, length_ratio: 0.3 })
                    });
                }

                const data = await response.json();
                if (data.success) {
                    displayResults(data);
                    if (data.fallback_used) {
                        showToast(
                            'The AI model is loading. Extractive (LSA) fallback was used — try again in a moment for full BART output.',
                            'warning',
                            6000
                        );
                    }
                } else {
                    showToast(`Summarization failed: ${data.error || 'Server rejected the request.'}`, 'error');
                }
            } catch (err) {
                console.error('[Summarize]', err);
                showToast(
                    err.name === 'AbortError' || err.name === 'TimeoutError'
                        ? 'Request timed out. Try a shorter text or switch to LSA / TextRank.'
                        : 'Connection lost during processing. Please check your server and try again.',
                    'error'
                );
            } finally {
                showLoader(false);
            }
        });
    }

    function displayResults(data) {
        resultsArea.style.display = 'block';
        summaryResult.textContent = data.summary;

        if (data.stats && data.analysis) {
            const s = data.stats;
            const a = data.analysis;

            // Stat cards
            const statsGrid = document.getElementById('statsGrid');
            if (statsGrid) {
                statsGrid.innerHTML = `
                    <div class="glass-card stat-card">
                        <span class="stat-value">${s.compression_ratio}%</span>
                        <span class="stat-label">Compression</span>
                    </div>
                    <div class="glass-card stat-card">
                        <span class="stat-value" style="color:${getSentimentColor(a.sentiment?.label)}">${a.sentiment?.label || '—'}</span>
                        <span class="stat-label">Sentiment</span>
                    </div>
                    <div class="glass-card stat-card">
                        <span class="stat-value">${a.readability?.interpretation || '—'}</span>
                        <span class="stat-label">Readability</span>
                    </div>
                    <div class="glass-card stat-card">
                        <span class="stat-value">${s.processing_time_ms} ms</span>
                        <span class="stat-label">Processing Time</span>
                    </div>
                `;
            }

            if (inputTypeBadge) inputTypeBadge.textContent = data.input_type || 'General Text';

            // Keywords cloud (from summarizer result)
            renderSummarizerChart(data.analysis);
        }

        resultsArea.scrollIntoView({ behavior: 'smooth' });
    }

    function renderSummarizerChart(analysis) {
        const ctx = document.getElementById('sentimentChart');
        if (!ctx || !analysis?.sentiment) return;

        if (sentimentChartInstance) sentimentChartInstance.destroy();

        sentimentChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Positivity', 'Subjectivity', 'Neutrality'],
                datasets: [{
                    data: [
                        Math.abs(analysis.sentiment.score) * 100,
                        analysis.sentiment.subjectivity * 100,
                        (1 - Math.abs(analysis.sentiment.score)) * 100
                    ],
                    backgroundColor: ['#10b981', '#6366f1', '#94a3b8'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '70%',
                plugins: { legend: { position: 'bottom' } }
            }
        });

        const cloud = document.getElementById('keywordCloud');
        if (cloud && analysis.keywords) {
            cloud.innerHTML = analysis.keywords.map(kw =>
                `<span class="kw-tag">${kw}</span>`
            ).join('');
        }
    }

    // ── History ───────────────────────────────────────────────────────────────
    async function loadHistory() {
        const historyList = document.getElementById('historyList');
        if (!historyList) return;
        historyList.innerHTML = `<div class="empty-state" style="padding:2rem;"><div class="dna-spinner" style="margin:0 auto;"></div></div>`;

        try {
            const res  = await fetch('/api/history');
            const data = await res.json();

            if (data.success && data.history.length > 0) {
                historyList.innerHTML = data.history.map(item => {
                    // Convert UTC ISO timestamp → local time string
                    const localTime = new Date(item.timestamp).toLocaleString(undefined, {
                        year: 'numeric', month: '2-digit', day: '2-digit',
                        hour: '2-digit', minute: '2-digit', second: '2-digit',
                        hour12: false
                    });
                    const summaryHtml = item.summary
                        ? `<div class="history-summary">${item.summary}</div>`
                        : `<div class="history-summary" style="color:var(--text-muted);font-style:italic;">No summary text recorded.</div>`;
                    const methodLabel = (item.method || 'unknown').replace('_', ' ').toUpperCase();
                    return `
                        <div class="history-card">
                            <div class="history-header">
                                <span><i class="fas fa-clock"></i> ${localTime}</span>
                                <span class="badge">${methodLabel}</span>
                            </div>
                            ${summaryHtml}
                            <div class="history-footer">
                                <span style="color:${getSentimentColor(item.sentiment)}">
                                    <i class="fas fa-smile"></i> ${item.sentiment}
                                </span>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                historyList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-history" style="font-size:3rem;opacity:0.15;margin-bottom:1rem;"></i>
                        <p>No recent history found.</p>
                    </div>`;
            }
        } catch (err) {
            console.error('History load failed:', err);
            historyList.innerHTML = `<div class="empty-state"><p>Failed to load history.</p></div>`;
        }
    }

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            if (confirm('Clear all history? This cannot be undone.')) {
                document.getElementById('historyList').innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-history" style="font-size:3rem;opacity:0.15;margin-bottom:1rem;"></i>
                        <p>History cleared.</p>
                    </div>`;
            }
        });
    }

    // ── Analytics ─────────────────────────────────────────────────────────────
    async function loadAnalytics() {
        try {
            const res  = await fetch('/api/analytics');
            const data = await res.json();
            if (!data.success) return;

            const total    = data.db_total || 0;
            const sentMap  = data.sentiment_counts || {};
            const methMap  = data.method_counts    || {};
            const uploads  = data.stats?.file_uploads || 0;

            // KPI cards
            document.getElementById('kpiTotal').textContent    = total;
            document.getElementById('kpiPositive').textContent = sentMap['Positive'] || 0;
            document.getElementById('kpiNegative').textContent = sentMap['Negative'] || 0;
            document.getElementById('kpiUploads').textContent  = uploads;

            if (total === 0) return; // nothing to chart

            // ── Sentiment Doughnut ──
            const sCtx = document.getElementById('sentimentChart');
            if (sCtx) {
                if (sentimentChartInstance) sentimentChartInstance.destroy();
                const posCount  = sentMap['Positive'] || 0;
                const negCount  = sentMap['Negative'] || 0;
                const neutCount = sentMap['Neutral']  || 0;
                const dominant  = posCount >= negCount && posCount >= neutCount ? 'Positive'
                                : negCount >= neutCount ? 'Negative' : 'Neutral';

                document.getElementById('sentimentDominant').textContent = dominant;
                sentimentChartInstance = new Chart(sCtx.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Positive', 'Negative', 'Neutral'],
                        datasets: [{
                            data: [posCount, negCount, neutCount],
                            backgroundColor: ['#10b981', '#ef4444', '#94a3b8'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        cutout: '65%',
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom', labels: { padding: 16 } } }
                    }
                });
            }

            // ── Method Usage Bar ──
            const mCtx = document.getElementById('methodChart');
            if (mCtx) {
                if (methodChartInstance) methodChartInstance.destroy();
                const mKeys   = Object.keys(methMap);
                const mVals   = mKeys.map(k => methMap[k]);
                const topKey  = mKeys.reduce((a, b) => methMap[a] >= methMap[b] ? a : b, mKeys[0] || '');
                document.getElementById('topModel').textContent = formatModelName(topKey) || '—';

                methodChartInstance = new Chart(mCtx.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: mKeys.map(formatModelName),
                        datasets: [{
                            label: 'Summaries',
                            data: mVals,
                            backgroundColor: [
                                'rgba(99,102,241,0.7)',
                                'rgba(14,165,233,0.7)',
                                'rgba(16,185,129,0.7)',
                                'rgba(244,63,94,0.7)'
                            ],
                            borderRadius: 10,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { precision: 0 },
                                 grid: { color: 'rgba(148,163,184,0.1)' }},
                            x: { grid: { display: false } }
                        }
                    }
                });
            }

            // ── Keywords from history (pull from last 5 items) ──
            loadKeywordsFromHistory();

            // ── Readability arc (fetch last 5 summaries and get avg readability) ──
            loadAvgReadability();

        } catch (err) {
            console.error('Analytics load failed:', err);
        }
    }

    async function loadKeywordsFromHistory() {
        const cloud = document.getElementById('analyticsKeywordCloud');
        if (!cloud) return;
        try {
            const res  = await fetch('/api/history');
            const data = await res.json();
            if (!data.success || data.history.length === 0) return;

            // Collect words from all summaries, rank by frequency
            const wordFreq = {};
            data.history.forEach(item => {
                (item.full_summary || item.summary || '').toLowerCase()
                    .replace(/[^a-z\s]/g, '').split(/\s+/)
                    .filter(w => w.length > 4)
                    .forEach(w => { wordFreq[w] = (wordFreq[w] || 0) + 1; });
            });
            const sorted = Object.entries(wordFreq)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 20)
                .map(([w]) => w);

            if (sorted.length) {
                cloud.innerHTML = sorted.map(w => `<span class="kw-tag">${w}</span>`).join('');
            }
        } catch (_) {}
    }

    async function loadAvgReadability() {
        try {
            const res  = await fetch('/api/history');
            const data = await res.json();
            if (!data.success || data.history.length === 0) return;
            // We can't get flesch score from stored records, show total count instead
            // Animate the arc as a proxy (# summaries / max 50)
            const score = Math.min(data.history.length * 8, 100);
            animateArc(score);
            document.getElementById('arcScore').textContent = data.history.length;
            document.getElementById('readabilityLabel').textContent = `${data.history.length} session${data.history.length !== 1 ? 's' : ''} analyzed`;
        } catch (_) {}
    }

    function animateArc(pct) {
        const arcEl = document.getElementById('arcFill');
        if (!arcEl) return;
        const total  = 251.3;  // half-circle circumference at r=80
        const offset = total - (pct / 100) * total;
        arcEl.style.transition = 'stroke-dashoffset 1s ease';
        arcEl.style.strokeDashoffset = offset;
    }

    const refreshAnalyticsBtn = document.getElementById('refreshAnalyticsBtn');
    if (refreshAnalyticsBtn) {
        refreshAnalyticsBtn.addEventListener('click', () => {
            refreshAnalyticsBtn.querySelector('i').classList.add('fa-spin');
            loadAnalytics().finally(() =>
                setTimeout(() => refreshAnalyticsBtn.querySelector('i').classList.remove('fa-spin'), 600)
            );
        });
    }

    // ── Comparison ────────────────────────────────────────────────────────────
    const compareBtn = document.getElementById('compareBtn');
    if (compareBtn) {
        compareBtn.addEventListener('click', async () => {
            const text    = document.getElementById('compareText').value.trim();
            const modelA  = document.getElementById('compareModelA').value;
            const modelB  = document.getElementById('compareModelB').value;
            const mode    = document.getElementById('compareModeSelect').value;

            if (!text || text.length < 50) {
                alert('Please enter at least 50 characters to compare.');
                return;
            }

            const hasAbstractive = modelA === 'abstractive' || modelB === 'abstractive';
            showLoader(true, hasAbstractive
                ? 'Running both models — BART may take ~15-30 s on cold start…'
                : 'Running both extractive models…');

            try {
                const res  = await fetch('/api/compare', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, model_a: modelA, model_b: modelB, mode })
                });
                const data = await res.json();

                if (!data.success) {
                    showToast(`Comparison failed: ${data.error}`, 'error');
                    return;
                }

                renderCompareResults(data, modelA, modelB);
            } catch (err) {
                console.error('[Compare]', err);
                showToast('Comparison request failed. Ensure the backend server is running.', 'error');
            } finally {
                showLoader(false);
            }
        });
    }

    function renderCompareResults(data, modelAKey, modelBKey) {
        const resultsEl = document.getElementById('compareResults');
        resultsEl.style.display = 'block';
        resultsEl.scrollIntoView({ behavior: 'smooth' });

        const mA = data.model_a;
        const mB = data.model_b;

        // Labels
        const nameA = formatModelName(modelAKey);
        const nameB = formatModelName(modelBKey);
        document.getElementById('compareModelALabel').textContent = nameA;
        document.getElementById('compareModelBLabel').textContent = nameB;
        document.getElementById('tableHeaderA').textContent = nameA;
        document.getElementById('tableHeaderB').textContent = nameB;

        // Summaries
        document.getElementById('compareResultA').textContent = mA.summary;
        document.getElementById('compareResultB').textContent = mB.summary;

        // Word counts
        document.getElementById('statWordsA').textContent = `${mA.stats.summary_words} words`;
        document.getElementById('statWordsB').textContent = `${mB.stats.summary_words} words`;

        // Mini stats rows
        function buildStatsRow(stats, elId) {
            document.getElementById(elId).innerHTML = `
                <div class="cmp-stat">
                    <span class="cmp-stat-value">${stats.compression_ratio}%</span>
                    <span class="cmp-stat-label">Compression</span>
                </div>
                <div class="cmp-stat">
                    <span class="cmp-stat-value">${stats.summary_words}</span>
                    <span class="cmp-stat-label">Words</span>
                </div>
                <div class="cmp-stat">
                    <span class="cmp-stat-value">${stats.processing_time_ms} ms</span>
                    <span class="cmp-stat-label">Speed</span>
                </div>
            `;
        }
        buildStatsRow(mA.stats, 'statsRowA');
        buildStatsRow(mB.stats, 'statsRowB');

        // Winner banner
        const comprA = mA.stats.compression_ratio;
        const comprB = mB.stats.compression_ratio;
        const speedA = mA.stats.processing_time_ms;
        const speedB = mB.stats.processing_time_ms;

        let winnerMsg = '';
        if (comprA > comprB) winnerMsg = `${nameA} achieved higher compression (${comprA}% vs ${comprB}%)`;
        else if (comprB > comprA) winnerMsg = `${nameB} achieved higher compression (${comprB}% vs ${comprA}%)`;
        else winnerMsg = 'Both models achieved identical compression!';

        if (speedA < speedB) winnerMsg += ` · ${nameA} was faster`;
        else if (speedB < speedA) winnerMsg += ` · ${nameB} was faster`;

        document.getElementById('winnerText').textContent = winnerMsg;

        // Detail table
        const tbody = document.getElementById('compareTableBody');
        const rows = [
            ['Original Words',  data.text_length, data.text_length],
            ['Summary Words',   mA.stats.summary_words, mB.stats.summary_words],
            ['Compression %',   `${comprA}%`, `${comprB}%`],
            ['Processing Time', `${speedA} ms`, `${speedB} ms`],
            ['Sentences',       countSentences(mA.summary), countSentences(mB.summary)],
        ];

        tbody.innerHTML = rows.map(([metric, valA, valB]) => {
            const numA = parseFloat(String(valA));
            const numB = parseFloat(String(valB));
            const winA = !isNaN(numA) && !isNaN(numB) && numA > numB;
            const winB = !isNaN(numA) && !isNaN(numB) && numB > numA;
            return `<tr>
                <td>${metric}</td>
                <td class="model-a-col ${winA ? 'cell-winner' : ''}">${valA}</td>
                <td class="model-b-col ${winB ? 'cell-winner' : ''}">${valB}</td>
            </tr>`;
        }).join('');

        // Performance Bar Chart
        if (compareBarChartInstance) compareBarChartInstance.destroy();
        const bCtx = document.getElementById('compareBarChart');
        if (bCtx) {
            compareBarChartInstance = new Chart(bCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Compression %', 'Speed (ms)', 'Words in Summary'],
                    datasets: [
                        {
                            label: nameA,
                            data: [comprA, speedA, mA.stats.summary_words],
                            backgroundColor: 'rgba(99,102,241,0.75)',
                            borderRadius: 8,
                            borderSkipped: false
                        },
                        {
                            label: nameB,
                            data: [comprB, speedB, mB.stats.summary_words],
                            backgroundColor: 'rgba(14,165,233,0.75)',
                            borderRadius: 8,
                            borderSkipped: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'top' } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,0.1)' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // Copy / Speak buttons for compare
        document.getElementById('copyCompareA').onclick = () => {
            navigator.clipboard.writeText(mA.summary);
            showToast('Model A summary copied!', 'success', 2500);
        };
        document.getElementById('copyCompareB').onclick = () => {
            navigator.clipboard.writeText(mB.summary);
            showToast('Model B summary copied!', 'success', 2500);
        };
        document.getElementById('speakCompareA').onclick = () =>
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(mA.summary));
        document.getElementById('speakCompareB').onclick = () =>
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(mB.summary));
    }

    function countSentences(text) {
        return (text.match(/[.!?]+/g) || []).length || 1;
    }

    // ── PDF Download ──────────────────────────────────────────────────────────
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', async () => {
            const summary = summaryResult?.textContent;
            if (!summary) return;
            showLoader(true, 'Generating PDF…');
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ summary })
                });
                if (response.ok) {
                    const blob = await response.blob();
                    const url  = window.URL.createObjectURL(blob);
                    const a    = document.createElement('a');
                    a.href     = url;
                    a.download = `Summary_Report_${Date.now()}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    showToast('PDF downloaded successfully!', 'success', 3000);
                } else {
                    showToast('PDF generation failed on the server. Please try again.', 'error');
                }
            } catch (err) {
                console.error('Download error:', err);
                showToast('Connection error during PDF download. Please try again.', 'error');
            } finally {
                showLoader(false);
            }
        });
    }

    // ── Copy & Speak (Summarizer) ─────────────────────────────────────────────
    const copyBtn  = document.getElementById('copyBtn');
    const speakBtn = document.getElementById('speakBtn');

    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(summaryResult.textContent);
            showToast('Summary copied to clipboard!', 'success', 2500);
        });
    }
    if (speakBtn) {
        speakBtn.addEventListener('click', () => {
            window.speechSynthesis.speak(new SpeechSynthesisUtterance(summaryResult.textContent));
        });
    }

    // ── Voice Input ───────────────────────────────────────────────────────────
    const voiceBtn = document.getElementById('voiceBtn');
    if (voiceBtn && 'webkitSpeechRecognition' in window) {
        const recognition      = new webkitSpeechRecognition();
        recognition.continuous     = false;
        recognition.interimResults = false;

        voiceBtn.addEventListener('click', () => {
            recognition.start();
            voiceBtn.classList.add('pulse');
        });
        recognition.onresult = e => {
            sourceText.value += (sourceText.value ? ' ' : '') + e.results[0][0].transcript;
            voiceBtn.classList.remove('pulse');
        };
        recognition.onerror = () => voiceBtn.classList.remove('pulse');
    }

    // ── Theme Toggle ──────────────────────────────────────────────────────────
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const cur = document.documentElement.getAttribute('data-theme');
            const next = cur === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', next);
            themeToggle.querySelector('.nav-text').textContent = next === 'light' ? 'Dark Mode' : 'Light Mode';
            themeToggle.querySelector('i').className = next === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        });
    }
});
