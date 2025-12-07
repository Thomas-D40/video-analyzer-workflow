/**
 * Module UI - Rendu de l'interface utilisateur
 */

// Éléments DOM
let loadingDiv, resultsDiv, errorDiv, statusDiv;
let videoSummary, argumentsList, rawReport;
let modal, closeModalBtn, modalSourcesList;
let analyzeBtn, newAnalysisBtn, copyBtn, controlsDiv;
let analysisStatusDiv, statusMetadataDiv, toggleResultsBtn, reAnalyzeBtn, statusIcon, statusText;
let analysisModeSelect;

// État
let currentAnalysisData = null;
let resultsExpanded = false;

/**
 * Initialise les éléments DOM du module UI
 */
export function initUIElements() {
    loadingDiv = document.getElementById('loading');
    resultsDiv = document.getElementById('results');
    errorDiv = document.getElementById('error');
    statusDiv = document.getElementById('status');
    videoSummary = document.getElementById('videoSummary');
    argumentsList = document.getElementById('argumentsList');
    rawReport = document.getElementById('rawReport');
    controlsDiv = document.getElementById('controls');

    analyzeBtn = document.getElementById('analyzeBtn');
    newAnalysisBtn = document.getElementById('newAnalysisBtn');
    copyBtn = document.getElementById('copyBtn');
    analysisModeSelect = document.getElementById('analysisMode');

    // New status panel elements
    analysisStatusDiv = document.getElementById('analysisStatus');
    statusMetadataDiv = document.getElementById('statusMetadata');
    toggleResultsBtn = document.getElementById('toggleResultsBtn');
    reAnalyzeBtn = document.getElementById('reAnalyzeBtn');
    statusIcon = document.getElementById('statusIcon');
    statusText = document.getElementById('statusText');

    modal = document.getElementById('sourcesModal');
    closeModalBtn = document.getElementById('closeModalBtn');
    modalSourcesList = document.getElementById('modalSourcesList');

    // Event listeners pour modal
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeSourcesModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeSourcesModal();
        });
    }

    // Event listener for toggle button
    if (toggleResultsBtn) {
        toggleResultsBtn.addEventListener('click', toggleResults);
    }
}

/**
 * Affiche le loader avec progression optionnelle
 */
export function showLoading(message = 'Analyse en cours...', percent = null) {
    if (loadingDiv) {
        loadingDiv.classList.remove('hidden');

        // Update message
        const loadingText = loadingDiv.querySelector('p:first-of-type');
        if (loadingText) {
            loadingText.textContent = message;
        }

        // Update or create progress bar
        let progressBar = loadingDiv.querySelector('.progress-bar');
        let progressPercent = loadingDiv.querySelector('.progress-percent');

        if (percent !== null) {
            if (!progressBar) {
                const progressContainer = document.createElement('div');
                progressContainer.className = 'progress-container';
                progressContainer.innerHTML = `
                    <div class="progress-bar-track">
                        <div class="progress-bar" style="width: 0%"></div>
                    </div>
                    <div class="progress-percent">0%</div>
                `;
                loadingDiv.appendChild(progressContainer);
                progressBar = progressContainer.querySelector('.progress-bar');
                progressPercent = progressContainer.querySelector('.progress-percent');
            }

            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }
            if (progressPercent) {
                progressPercent.textContent = `${percent}%`;
            }
        }
    }

    if (resultsDiv) resultsDiv.classList.add('hidden');
    if (errorDiv) errorDiv.classList.add('hidden');
    if (controlsDiv) controlsDiv.classList.add('hidden');
}

/**
 * Masque le loader
 */
export function hideLoading() {
    if (loadingDiv) loadingDiv.classList.add('hidden');
}

/**
 * Affiche une erreur
 */
export function showError(message) {
    if (errorDiv) {
        errorDiv.textContent = `❌ ${message}`;
        errorDiv.classList.remove('hidden');
    }
    hideLoading();
    if (analyzeBtn) analyzeBtn.disabled = false;
}

/**
 * Affiche un message de statut
 */
export function showStatus(message, type = 'info') {
    if (!statusDiv) return;

    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.classList.remove('hidden');

    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            statusDiv.classList.add('hidden');
        }, 3000);
    }
}

/**
 * Affiche les contrôles (bouton analyser)
 */
export function showControls() {
    if (controlsDiv) controlsDiv.classList.remove('hidden');
}

/**
 * Masque les contrôles
 */
export function hideControls() {
    if (controlsDiv) controlsDiv.classList.add('hidden');
}

/**
 * Affiche le panneau de statut avec les métadonnées de l'analyse
 */
export function showAnalysisStatus(data) {
    if (!analysisStatusDiv) return;

    console.log('[UI] showAnalysisStatus called with data:', data);

    const argCount = data.arguments_count !== undefined ? data.arguments_count : (data.arguments ? data.arguments.length : 0);

    let dateStr = 'Date inconnue';
    // Check multiple possible date fields
    const dateSource = data.last_updated || data.cache_info?.last_updated || data.updated_at || data.created_at;
    console.log('[UI] Date source found:', dateSource);

    if (dateSource) {
        const date = new Date(dateSource);
        console.log('[UI] Parsed date:', date, 'isValid:', !isNaN(date.getTime()));

        if (!isNaN(date.getTime())) {
            dateStr = date.toLocaleString('fr-FR', {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            console.log('[UI] Formatted date:', dateStr);
        }
    }

    // Check multiple possible mode fields
    const modeRaw = data.analysis_mode || data.mode || data.cache_info?.selected_mode || 'simple';
    const modeLabels = {
        'simple': 'Rapide',
        'medium': 'Équilibré',
        'hard': 'Approfondi'
    };
    const mode = modeLabels[modeRaw] || modeRaw;

    if (statusIcon) statusIcon.textContent = '✓';
    if (statusText) statusText.textContent = 'Analyse disponible';

    if (statusMetadataDiv) {
        statusMetadataDiv.innerHTML = `
            <span class="status-metadata-item">📅 ${dateStr}</span>
            <span class="status-metadata-item">⚙️ Mode: ${mode}</span>
            <span class="status-metadata-item">💬 ${argCount} argument${argCount > 1 ? 's' : ''}</span>
        `;
    }

    // Show available modes if applicable
    showAvailableModes(data);

    analysisStatusDiv.classList.remove('hidden');
    if (toggleResultsBtn) toggleResultsBtn.classList.remove('hidden');
    hideControls();

    // Store data for potential re-use
    currentAnalysisData = data;
}

/**
 * Affiche les modes d'analyse disponibles
 */
function showAvailableModes(data) {
    // Remove existing available modes section
    const existingModes = document.getElementById('availableModesSection');
    if (existingModes) {
        existingModes.remove();
    }

    // Get current mode and available analyses
    const availableAnalyses = data.cache_info?.available_analyses || [];
    const currentMode = data.analysis_mode || data.cache_info?.selected_mode || 'simple';

    // All possible modes with descriptions and cost info
    const allModes = [
        {
            mode: 'simple',
            desc: '⚡ Rapide - Basé sur les abstracts uniquement',
            cost: 'Faible coût (~0.01€)'
        },
        {
            mode: 'medium',
            desc: '⚖️ Équilibré - 3 textes complets analysés',
            cost: 'Coût moyen (~0.05€)'
        },
        {
            mode: 'hard',
            desc: '🔬 Approfondi - 6 textes complets analysés',
            cost: 'Coût élevé (~0.10€)'
        }
    ];

    // Build list of other modes (excluding current)
    const otherModes = allModes.filter(m => m.mode !== currentMode);

    if (otherModes.length === 0) {
        return;
    }

    // Create HTML for each mode
    const modesHtml = otherModes.map(modeConfig => {
        const existingAnalysis = availableAnalyses.find(a => a.mode === modeConfig.mode);
        const exists = !!existingAnalysis;

        let statusHtml;
        let buttonText;
        let buttonClass = 'btn-switch-mode';

        if (exists) {
            const ageText = existingAnalysis.age_days === 0 ? "Aujourd'hui" :
                           existingAnalysis.age_days === 1 ? "Il y a 1 jour" :
                           `Il y a ${existingAnalysis.age_days} jours`;
            statusHtml = `<span class="available-mode-age">✓ Analyse existante (${ageText})</span>`;
            buttonText = 'Voir cette analyse';
        } else {
            statusHtml = `<span class="available-mode-cost">⚠️ ${modeConfig.cost}</span>`;
            buttonText = 'Créer cette analyse';
            buttonClass += ' btn-create-mode';
        }

        return `
            <div class="available-mode-item">
                <div class="available-mode-header">
                    <span class="available-mode-desc">${modeConfig.desc}</span>
                    ${statusHtml}
                </div>
                <button class="${buttonClass}" data-mode="${modeConfig.mode}" data-exists="${exists}">
                    ${buttonText}
                </button>
            </div>
        `;
    }).join('');

    const section = document.createElement('div');
    section.id = 'availableModesSection';
    section.className = 'available-modes-section';
    section.innerHTML = `
        <div class="available-modes-header">
            <span class="available-modes-icon">ℹ️</span>
            <span class="available-modes-title">Autres modes d'analyse disponibles</span>
        </div>
        <div class="available-modes-list">
            ${modesHtml}
        </div>
    `;

    // Insert after analysis status
    if (analysisStatusDiv && analysisStatusDiv.parentNode) {
        analysisStatusDiv.parentNode.insertBefore(section, analysisStatusDiv.nextSibling);
    }

    // Add click handlers
    section.querySelectorAll('.btn-switch-mode').forEach(btn => {
        btn.addEventListener('click', async () => {
            const mode = btn.dataset.mode;
            const exists = btn.dataset.exists === 'true';

            // If analysis doesn't exist, show cost warning
            if (!exists) {
                const modeLabels = {
                    'simple': 'Rapide',
                    'medium': 'Équilibré',
                    'hard': 'Approfondi'
                };
                const modeCosts = {
                    'simple': '~0.01€',
                    'medium': '~0.05€',
                    'hard': '~0.10€'
                };

                const confirmed = confirm(
                    `⚠️ ATTENTION - Nouvelle analyse requise\n\n` +
                    `Mode: ${modeLabels[mode]}\n` +
                    `Coût estimé: ${modeCosts[mode]}\n\n` +
                    `Cette analyse n'existe pas encore. Une nouvelle analyse sera créée, ce qui consommera des crédits API.\n\n` +
                    `Voulez-vous continuer ?`
                );

                if (!confirmed) {
                    return;
                }

                // Create new analysis
                await switchToMode(mode, true);
            } else {
                // Load existing analysis
                await switchToMode(mode, false);
            }
        });
    });
}

/**
 * Switch to a different analysis mode
 */
async function switchToMode(mode, forceNew = false) {
    try {
        const modeLabels = {
            'simple': 'Rapide',
            'medium': 'Équilibré',
            'hard': 'Approfondi'
        };

        if (forceNew) {
            showLoading(`Création de l'analyse ${modeLabels[mode]}...`, 0);
        } else {
            showLoading(`Chargement de l'analyse ${modeLabels[mode]}...`);
        }

        const { getCurrentVideoUrl, analyzeVideo, analyzeVideoStreaming } = await import('./api.js');

        const currentUrl = await getCurrentVideoUrl();

        let response;
        if (forceNew) {
            // Use streaming for new analysis with progress
            response = await analyzeVideoStreaming(
                currentUrl,
                true,  // force_refresh
                mode,
                (percent, message) => {
                    showLoading(message, percent);
                }
            );
        } else {
            // Load existing analysis
            response = await analyzeVideo(currentUrl, false, mode);
        }

        // Update cache
        const browser = await import('./polyfill.js');
        const storageData = {};
        storageData[currentUrl] = response.data;
        await browser.default.storage.local.set(storageData);

        // Render new results
        renderResults(response.data);
        showAnalysisStatus(response.data);

        const statusMsg = forceNew ? `Analyse ${modeLabels[mode]} créée !` : `Analyse ${modeLabels[mode]} chargée !`;
        showStatus(statusMsg, 'success');
    } catch (error) {
        showError(`Erreur lors du changement de mode: ${error.message}`);
    }
}

/**
 * Masque le panneau de statut
 */
export function hideAnalysisStatus() {
    if (analysisStatusDiv) analysisStatusDiv.classList.add('hidden');
}

/**
 * Affiche l'état "aucune analyse disponible"
 */
export function showNoAnalysisState() {
    if (!analysisStatusDiv) return;

    if (statusIcon) statusIcon.textContent = '⚠';
    if (statusText) statusText.textContent = 'Aucune analyse disponible';
    if (statusMetadataDiv) {
        statusMetadataDiv.innerHTML = '<span class="status-metadata-item">Lancez une nouvelle analyse pour commencer</span>';
    }

    analysisStatusDiv.classList.remove('hidden');
    showControls();

    if (toggleResultsBtn) toggleResultsBtn.classList.add('hidden');
}

/**
 * Toggle l'affichage des résultats
 */
function toggleResults() {
    resultsExpanded = !resultsExpanded;

    if (resultsExpanded) {
        if (resultsDiv) {
            resultsDiv.classList.remove('collapsed');
            resultsDiv.classList.remove('hidden');
        }
        if (toggleResultsBtn) {
            toggleResultsBtn.classList.add('expanded');
            const toggleText = toggleResultsBtn.querySelector('.toggle-text');
            if (toggleText) toggleText.textContent = 'Masquer l\'analyse';
        }
    } else {
        if (resultsDiv) {
            resultsDiv.classList.add('collapsed');
        }
        if (toggleResultsBtn) {
            toggleResultsBtn.classList.remove('expanded');
            const toggleText = toggleResultsBtn.querySelector('.toggle-text');
            if (toggleText) toggleText.textContent = 'Voir l\'analyse';
        }

        setTimeout(() => {
            if (!resultsExpanded && resultsDiv) {
                resultsDiv.classList.add('hidden');
            }
        }, 400);
    }
}

/**
 * Affiche les analyses disponibles
 * @param {Object} data - Données des analyses disponibles
 * @param {Function} onViewAnalysis - Callback pour voir une analyse
 */
export function renderAvailableAnalyses(data, onViewAnalysis) {
    if (!controlsDiv) return;

    // Si aucune analyse, ne rien afficher
    if (!data.analyses || data.analyses.length === 0) {
        return;
    }

    // Créer le conteneur pour les analyses disponibles
    const existingContainer = document.getElementById('availableAnalyses');
    if (existingContainer) {
        existingContainer.remove();
    }

    const container = document.createElement('div');
    container.id = 'availableAnalyses';
    container.className = 'available-analyses';

    const modeBadgeClass = {
        'simple': 'mode-badge-simple',
        'medium': 'mode-badge-medium',
        'hard': 'mode-badge-hard'
    };

    const modeLabel = {
        'simple': 'Rapide',
        'medium': 'Équilibré',
        'hard': 'Approfondi'
    };

    const analysesHtml = data.analyses.map(analysis => {
        const ageText = analysis.age_days === 0 ? "Aujourd'hui" :
                       analysis.age_days === 1 ? "Il y a 1 jour" :
                       `Il y a ${analysis.age_days} jours`;

        const ratingText = analysis.rating_count > 0
            ? `⭐ ${analysis.average_rating.toFixed(1)} (${analysis.rating_count})`
            : '✨ Pas encore noté';

        const badgeClass = modeBadgeClass[analysis.analysis_mode] || 'mode-badge-simple';
        const label = modeLabel[analysis.analysis_mode] || analysis.analysis_mode;

        return `
            <div class="analysis-card" data-mode="${analysis.analysis_mode}">
                <div class="analysis-header">
                    <span class="mode-badge ${badgeClass}">${label}</span>
                    <span class="analysis-age">${ageText}</span>
                </div>
                <div class="analysis-stats">
                    <span class="analysis-rating">${ratingText}</span>
                    <span class="analysis-args">${analysis.arguments_count} arguments</span>
                </div>
                <div class="analysis-actions">
                    <button class="btn-view-analysis btn-secondary" data-mode="${analysis.analysis_mode}">
                        👁️ Voir l'analyse
                    </button>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="available-analyses-header">
            <h3>📋 Analyses disponibles</h3>
            <p class="subtitle">Cette vidéo a déjà été analysée</p>
        </div>
        <div class="analyses-grid">
            ${analysesHtml}
        </div>
    `;

    // Insérer avant le bouton analyser
    controlsDiv.insertBefore(container, controlsDiv.firstChild);

    // Ajouter les event listeners pour les boutons "Voir"
    const viewButtons = container.querySelectorAll('.btn-view-analysis');
    viewButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const mode = btn.dataset.mode;
            if (onViewAnalysis) {
                onViewAnalysis(mode);
            }
        });
    });
}

/**
 * Rend les résultats de l'analyse
 */
export function renderResults(data) {
    // 1. Résumé + Tableau récapitulatif
    const summaryTableHtml = renderSummaryTable(data);
    const argCount = data.arguments_count !== undefined ? data.arguments_count : (data.arguments ? data.arguments.length : 0);

    let dateHtml = '';
    // Check multiple possible date fields
    const dateSource = data.last_updated || data.cache_info?.last_updated || data.updated_at || data.created_at;
    if (dateSource) {
        const date = new Date(dateSource);
        if (!isNaN(date.getTime())) {
            const dateStr = date.toLocaleString('fr-FR', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit'
            });
            dateHtml = `<div class="summary-date">Mis à jour le ${dateStr}</div>`;
        }
    }

    if (videoSummary) {
        videoSummary.innerHTML = `
            <div class="summary-card">
                <div class="summary-header-row">
                    <div class="summary-title">VIDÉO ANALYSÉE</div>
                    <div class="summary-stats">${argCount} arguments</div>
                </div>
                ${dateHtml}
                ${summaryTableHtml}
            </div>
        `;
    }

    // Event delegation pour le tableau
    const summaryTable = document.getElementById('summaryTable');
    if (summaryTable) {
        summaryTable.addEventListener('click', (e) => {
            const trigger = e.target.closest('.sources-trigger');
            if (trigger) {
                e.stopPropagation();
                const index = parseInt(trigger.dataset.argIndex);
                if (data.arguments[index]) {
                    openSourcesModal(data.arguments[index], e);
                }
                return;
            }

            const row = e.target.closest('.summary-row');
            if (row) {
                const index = parseInt(row.dataset.argIndex);
                const targetEl = document.getElementById(`arg-${index}`);
                if (targetEl) {
                    targetEl.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    }

    // 2. Liste des arguments détaillés
    if (argumentsList) {
        argumentsList.innerHTML = '';
        data.arguments.forEach((arg, index) => {
            const card = createArgumentCard(arg, index);
            argumentsList.appendChild(card);
        });
    }

    // 3. Rapport brut
    if (rawReport) {
        rawReport.textContent = data.report_markdown;
    }

    // Store analysis data
    currentAnalysisData = data;

    // Don't auto-expand results - let the toggle button control it
    hideLoading();
}

/**
 * Crée le tableau récapitulatif
 */
function renderSummaryTable(data) {
    if (!data.arguments || data.arguments.length === 0) return '';

    const rows = data.arguments.map((arg, index) => {
        const webCount = arg.sources?.web?.length || 0;
        const sciCount = arg.sources?.scientific?.length || 0;
        const totalSources = webCount + sciCount;

        const usedUrls = new Set();
        if (arg.analysis?.pros) arg.analysis.pros.forEach(p => { if (typeof p === 'object' && p.source) usedUrls.add(p.source); });
        if (arg.analysis?.cons) arg.analysis.cons.forEach(c => { if (typeof c === 'object' && c.source) usedUrls.add(c.source); });
        const usedSourceCount = usedUrls.size;

        let reliabilityClass = getReliabilityClass(arg.reliability_score);
        let scoreDisplay = Math.round(arg.reliability_score * 100);

        if (totalSources === 0 || usedSourceCount === 0) {
            reliabilityClass = 'reliability-none';
            scoreDisplay = '-';
        }

        let sourceIcons = '';
        if (totalSources === 0) {
            sourceIcons = '<span style="color:#cbd5e0">∅</span>';
        } else {
            const iconsHtml = [];
            if (sciCount > 0) iconsHtml.push(`<span title="${sciCount} sources scientifiques">🔬${sciCount}</span>`);
            if (webCount > 0) iconsHtml.push(`<span title="${webCount} sources web">🌐${webCount}</span>`);
            sourceIcons = `<div class="sources-trigger" data-arg-index="${index}">${iconsHtml.join(' ')}</div>`;
        }

        return `
            <tr class="summary-row" data-arg-index="${index}" style="cursor:pointer">
                <td><span class="mini-badge ${reliabilityClass}">${scoreDisplay}</span></td>
                <td class="summary-arg-text">${arg.argument}</td>
                <td class="summary-sources">${sourceIcons}</td>
            </tr>
        `;
    }).join('');

    return `
        <div class="summary-table-container">
            <table class="summary-table" id="summaryTable">
                <thead>
                    <tr>
                        <th width="15%">Note</th>
                        <th width="65%">Argument</th>
                        <th width="20%">Sources</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Crée une carte d'argument
 */
function createArgumentCard(arg, index) {
    const sourceMap = new Map();
    const allSources = [
        ...(arg.sources?.web || []),
        ...(arg.sources?.scientific || [])
    ];
    allSources.forEach(s => sourceMap.set(s.url, s));

    const renderPoint = (point) => {
        const isObj = typeof point === 'object';
        const text = isObj ? point.claim : point;
        const url = isObj ? point.source : null;

        let sourceLink = '';
        if (url) {
            const sourceData = sourceMap.get(url);
            let sourceTitle = url;

            if (sourceData && sourceData.title) {
                sourceTitle = sourceData.title;
            } else {
                try {
                    sourceTitle = new URL(url).hostname;
                } catch (e) {
                    sourceTitle = url.length > 30 ? url.substring(0, 30) + '...' : url;
                }
            }

            const icon = sourceData?.source === 'scientific' ? '🔬' : '🌐';
            sourceLink = `
                <a href="${url}" target="_blank" class="inline-source-link" title="${sourceTitle}">
                    ${icon} Source
                </a>`;
        }

        return `<li><span class="point-text">${text}</span> ${sourceLink}</li>`;
    };

    const usedUrls = new Set();
    if (arg.analysis?.pros) arg.analysis.pros.forEach(p => { if (typeof p === 'object' && p.source) usedUrls.add(p.source); });
    if (arg.analysis?.cons) arg.analysis.cons.forEach(c => { if (typeof c === 'object' && c.source) usedUrls.add(c.source); });
    const usedSourceCount = usedUrls.size;

    let reliabilityClass = getReliabilityClass(arg.reliability_score);
    let reliabilityLabel = getReliabilityLabel(arg.reliability_score);
    let reliabilityPercent = Math.round(arg.reliability_score * 100) + '/100';

    if (usedSourceCount === 0) {
        reliabilityClass = 'reliability-none';
        reliabilityLabel = 'Non vérifiable';
        reliabilityPercent = 'Pas de sources liées';
    }

    const prosHtml = arg.analysis?.pros?.length
        ? `<div class="pros-box">
             <div class="section-title" style="color:#276749; margin-top:0;">✅ Points qui corroborent</div>
             <ul class="pros-list">${arg.analysis.pros.map(p => renderPoint(p)).join('')}</ul>
           </div>`
        : '';

    const consHtml = arg.analysis?.cons?.length
        ? `<div class="cons-box">
             <div class="section-title" style="color:#9b2c2c; margin-top:0;">❌ Points qui contredisent</div>
             <ul class="cons-list">${arg.analysis.cons.map(c => renderPoint(c)).join('')}</ul>
           </div>`
        : '';

    let contentHtml = '';
    if (!prosHtml && !consHtml) {
        contentHtml = `
            <div class="no-analysis-msg">
                <p>Aucun point corroborant ou contradictoire n'a été extrait des sources pour cet argument.</p>
            </div>
        `;
    } else {
        contentHtml = prosHtml + consHtml;
    }

    const card = document.createElement('div');
    card.className = 'arg-card collapsed';
    card.id = `arg-${index}`;
    card.innerHTML = `
        <div class="arg-header" style="cursor: pointer;">
            <div class="arg-title-container">
                <span class="expand-arrow">▼</span>
                <div class="arg-title">"${arg.argument}"</div>
            </div>
            <div class="reliability-container">
                <span class="reliability-badge ${reliabilityClass}">${reliabilityLabel}</span>
                <span class="reliability-score">${reliabilityPercent}</span>
            </div>
        </div>
        <div class="arg-details">
            ${contentHtml}
        </div>
    `;

    // Add click handler to toggle collapse
    const header = card.querySelector('.arg-header');
    header.addEventListener('click', () => {
        card.classList.toggle('collapsed');
    });

    return card;
}

/**
 * Ouvre la modal des sources
 */
function openSourcesModal(arg, event) {
    if (event) event.stopPropagation();

    if (modalSourcesList) {
        modalSourcesList.innerHTML = '';
        const allSources = [...(arg.sources?.web || []), ...(arg.sources?.scientific || [])];

        if (allSources.length === 0) {
            modalSourcesList.innerHTML = '<div style="padding:20px; text-align:center; color:#718096">Aucune source disponible</div>';
        } else {
            allSources.forEach(source => {
                const isSci = source.source === 'scientific';
                const icon = isSci ? '🔬' : '🌐';
                const title = source.title || (new URL(source.url).hostname);

                const item = document.createElement('div');
                item.className = 'source-item';
                item.innerHTML = `
                    <span class="source-icon">${icon}</span>
                    <div class="source-info">
                        <a href="${source.url}" target="_blank" class="source-title">${title}</a>
                        <div class="source-url">${source.url}</div>
                    </div>
                `;
                modalSourcesList.appendChild(item);
            });
        }
    }

    if (modal) modal.classList.remove('hidden');
}

/**
 * Ferme la modal des sources
 */
function closeSourcesModal() {
    if (modal) modal.classList.add('hidden');
}

/**
 * Helpers
 */
function getReliabilityClass(score) {
    if (score >= 0.8) return 'reliability-high';
    if (score >= 0.5) return 'reliability-medium';
    if (score > 0) return 'reliability-low';
    return 'reliability-none';
}

function getReliabilityLabel(score) {
    if (score >= 0.8) return 'Fiable';
    if (score >= 0.5) return 'Discutable';
    if (score > 0) return 'Douteux';
    return 'Non vérifié';
}

/**
 * Retourne les références aux boutons pour les event listeners
 */
export function getButtons() {
    return { analyzeBtn, newAnalysisBtn, copyBtn, reAnalyzeBtn };
}

/**
 * Retourne la référence au rawReport pour la copie
 */
export function getRawReport() {
    return rawReport;
}

/**
 * Retourne le mode d'analyse sélectionné
 */
export function getSelectedMode() {
    return analysisModeSelect ? analysisModeSelect.value : 'simple';
}
