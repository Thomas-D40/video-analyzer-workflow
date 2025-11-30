/**
 * Module UI - Rendu de l'interface utilisateur
 */

// Éléments DOM
let loadingDiv, resultsDiv, errorDiv, statusDiv;
let videoSummary, argumentsList, rawReport;
let modal, closeModalBtn, modalSourcesList;
let analyzeBtn, newAnalysisBtn, copyBtn, controlsDiv;

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
}

/**
 * Affiche le loader
 */
export function showLoading(message = 'Analyse en cours...') {
    if (loadingDiv) loadingDiv.classList.remove('hidden');
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
 * Rend les résultats de l'analyse
 */
export function renderResults(data) {
    // 1. Résumé + Tableau récapitulatif
    const summaryTableHtml = renderSummaryTable(data);
    const argCount = data.arguments_count !== undefined ? data.arguments_count : (data.arguments ? data.arguments.length : 0);

    let dateHtml = '';
    if (data.last_updated) {
        const date = new Date(data.last_updated);
        const dateStr = date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        dateHtml = `<div class="summary-date">Mis à jour le ${dateStr}</div>`;
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

    // Affichage
    hideLoading();
    if (resultsDiv) resultsDiv.classList.remove('hidden');
    hideControls();
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
    card.className = 'arg-card';
    card.id = `arg-${index}`;
    card.innerHTML = `
        <div class="arg-header" style="cursor: default;">
            <div class="arg-title">"${arg.argument}"</div>
            <div class="reliability-container">
                <span class="reliability-badge ${reliabilityClass}">${reliabilityLabel}</span>
                <span class="reliability-score">${reliabilityPercent}</span>
            </div>
        </div>
        <div class="arg-details">
            ${contentHtml}
        </div>
    `;

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
    return { analyzeBtn, newAnalysisBtn, copyBtn };
}

/**
 * Retourne la référence au rawReport pour la copie
 */
export function getRawReport() {
    return rawReport;
}
