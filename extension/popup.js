// Configuration
const API_URL = 'http://localhost:8000/api/analyze';

// Éléments DOM
const analyzeBtn = document.getElementById('analyzeBtn');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');
const loadingDiv = document.getElementById('loading');
const resultsDiv = document.getElementById('results');
const errorDiv = document.getElementById('error');
const statusDiv = document.getElementById('status');
const videoSummary = document.getElementById('videoSummary');
const argumentsList = document.getElementById('argumentsList');
const copyBtn = document.getElementById('copyBtn');
const rawReport = document.getElementById('rawReport');

// État
let currentVideoUrl = '';

// --- Fonctions Utilitaires ---

async function getCurrentVideoUrl() {
    try {
        // Essai 1: Fenêtre courante
        let tabs = await chrome.tabs.query({ active: true, currentWindow: true });

        // Essai 2: Dernière fenêtre focus (fallback)
        if (!tabs || tabs.length === 0) {
            console.log("Aucun onglet dans currentWindow, essai lastFocusedWindow");
            tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        }

        const tab = tabs[0];
        console.log("Tab trouvé:", tab);

        if (!tab) {
            throw new Error("Aucun onglet actif trouvé");
        }

        if (!tab.url) {
            throw new Error("Impossible de lire l'URL (Permissions?)");
        }

        if (!tab.url.includes('youtube.com/watch')) {
            console.log("URL ignorée:", tab.url);
            throw new Error(`Pas une vidéo YouTube (URL: ${tab.url.substring(0, 30)}...)`);
        }

        return tab.url;
    } catch (e) {
        console.error("Erreur getCurrentVideoUrl:", e);
        throw e;
    }
}

function showStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type}`;
    statusDiv.classList.remove('hidden');

    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            statusDiv.classList.add('hidden');
        }, 3000);
    }
}

function showError(message) {
    errorDiv.textContent = `❌ ${message}`;
    errorDiv.classList.remove('hidden');
    loadingDiv.classList.add('hidden');
    analyzeBtn.disabled = false;
}

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

// --- Modal Logic ---

const modal = document.getElementById('sourcesModal');
const closeModalBtn = document.getElementById('closeModalBtn');
const modalSourcesList = document.getElementById('modalSourcesList');

function openSourcesModal(arg, event) {
    if (event) event.stopPropagation(); // Empêcher le scroll vers le détail

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

    modal.classList.remove('hidden');
}

function closeSourcesModal() {
    modal.classList.add('hidden');
}

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', closeSourcesModal);
}

if (modal) {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeSourcesModal();
    });
}

// --- Rendu UI ---

function renderSummaryTable(data) {
    if (!data.arguments || data.arguments.length === 0) return '';

    const rows = data.arguments.map((arg, index) => {
        // Compter les sources
        const webCount = arg.sources?.web?.length || 0;
        const sciCount = arg.sources?.scientific?.length || 0;
        const totalSources = webCount + sciCount;

        // Calculer les sources utilisées (liées) pour la cohérence avec le détail
        const usedUrls = new Set();
        if (arg.analysis?.pros) arg.analysis.pros.forEach(p => { if (typeof p === 'object' && p.source) usedUrls.add(p.source); });
        if (arg.analysis?.cons) arg.analysis.cons.forEach(c => { if (typeof c === 'object' && c.source) usedUrls.add(c.source); });
        const usedSourceCount = usedUrls.size;

        let reliabilityClass = getReliabilityClass(arg.reliability_score);
        let scoreDisplay = Math.round(arg.reliability_score * 100);

        // Si aucune source brute, pas de notation
        if (totalSources === 0) {
            reliabilityClass = 'reliability-none';
            scoreDisplay = '-';
        }
        // Si sources existent mais aucune liée, on considère aussi comme non vérifiable
        else if (usedSourceCount === 0) {
            reliabilityClass = 'reliability-none';
            scoreDisplay = '-';
        }

        let sourceIcons = '';
        if (totalSources === 0) sourceIcons = '<span style="color:#cbd5e0">∅</span>';
        else {
            // On rend les icônes cliquables via delegation (pas de onclick inline pour CSP)
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

function renderResults(data) {
    // 1. Résumé Vidéo + Tableau Récapitulatif
    const summaryTableHtml = renderSummaryTable(data);

    // Correction: data.arguments.length au lieu de data.arguments_count si undefined
    const argCount = data.arguments_count !== undefined ? data.arguments_count : (data.arguments ? data.arguments.length : 0);

    // Formatage de la date si présente
    let dateHtml = '';
    if (data.last_updated) {
        const date = new Date(data.last_updated);
        const dateStr = date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        dateHtml = `<div class="summary-date">Mis à jour le ${dateStr}</div>`;
    }

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

    // Event Delegation pour le tableau récapitulatif (CSP safe)
    const summaryTable = document.getElementById('summaryTable');
    if (summaryTable) {
        summaryTable.addEventListener('click', (e) => {
            // 1. Clic sur les sources (Modal)
            const trigger = e.target.closest('.sources-trigger');
            if (trigger) {
                e.stopPropagation(); // Important : ne pas déclencher le clic de la ligne
                const index = parseInt(trigger.dataset.argIndex);
                if (data.arguments[index]) {
                    openSourcesModal(data.arguments[index], e);
                }
                return;
            }

            // 2. Clic sur la ligne (Scroll)
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

    // 2. Liste des Arguments (Détails)
    argumentsList.innerHTML = '';

    data.arguments.forEach((arg, index) => {
        // 1. Créer une map URL -> Source Object pour récupérer les titres
        const sourceMap = new Map();
        const allSources = [
            ...(arg.sources?.web || []),
            ...(arg.sources?.scientific || [])
        ];
        allSources.forEach(s => sourceMap.set(s.url, s));

        // 2. Fonction pour générer le HTML d'un point avec sa source
        const renderPoint = (point, type) => {
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
                        // Fallback for invalid URLs
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

        // 3. Calculer les sources UNIQUES utilisées pour le score
        const usedUrls = new Set();
        if (arg.analysis?.pros) arg.analysis.pros.forEach(p => { if (typeof p === 'object' && p.source) usedUrls.add(p.source); });
        if (arg.analysis?.cons) arg.analysis.cons.forEach(c => { if (typeof c === 'object' && c.source) usedUrls.add(c.source); });

        const usedSourceCount = usedUrls.size;

        // 4. Logique de fiabilité basée sur les sources UTILISÉES
        let reliabilityClass = getReliabilityClass(arg.reliability_score);
        let reliabilityLabel = getReliabilityLabel(arg.reliability_score);
        let reliabilityPercent = Math.round(arg.reliability_score * 100) + '/100';

        if (usedSourceCount === 0) {
            reliabilityClass = 'reliability-none';
            reliabilityLabel = 'Non vérifiable';
            reliabilityPercent = 'Pas de sources liées';
        }

        // 5. Création des listes Pros/Cons
        const prosHtml = arg.analysis?.pros?.length
            ? `<div class="pros-box">
                 <div class="section-title" style="color:#276749; margin-top:0;">✅ Points qui corroborent</div>
                 <ul class="pros-list">${arg.analysis.pros.map(p => renderPoint(p, 'pro')).join('')}</ul>
               </div>`
            : '';

        const consHtml = arg.analysis?.cons?.length
            ? `<div class="cons-box">
                 <div class="section-title" style="color:#9b2c2c; margin-top:0;">❌ Points qui contredisent</div>
                 <ul class="cons-list">${arg.analysis.cons.map(c => renderPoint(c, 'con')).join('')}</ul>
               </div>`
            : '';

        // 6. Message si aucune analyse (pros/cons vides)
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

        // Carte HTML
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

        argumentsList.appendChild(card);
    });

    // 3. Stockage du rapport brut
    rawReport.textContent = data.report_markdown;

    // Affichage
    loadingDiv.classList.add('hidden');
    resultsDiv.classList.remove('hidden');
    document.getElementById('controls').classList.add('hidden');
}

// --- Logique Principale ---

async function checkExistingAnalysis(url) {
    return new Promise((resolve) => {
        chrome.storage.local.get([url], (result) => {
            resolve(result[url]);
        });
    });
}

async function saveAnalysis(url, data) {
    const storageData = {};
    storageData[url] = data;
    await chrome.storage.local.set(storageData);
}

async function analyzeVideo(forceRefresh = false) {
    try {
        // Reset UI
        errorDiv.classList.add('hidden');
        resultsDiv.classList.add('hidden');
        document.getElementById('controls').classList.add('hidden'); // Cacher le bouton principal
        loadingDiv.classList.remove('hidden');

        currentVideoUrl = await getCurrentVideoUrl();

        // Appel API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: currentVideoUrl,
                force_refresh: forceRefresh
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de l\'analyse');
        }

        const data = await response.json();

        // Sauvegarde et Affichage
        await saveAnalysis(currentVideoUrl, data.data);
        renderResults(data.data);

        if (data.data.cached) {
            showStatus('Résultat récupéré du cache', 'info');
        } else {
            showStatus('Analyse terminée !', 'success');
        }

    } catch (error) {
        console.error('Erreur:', error);
        showError(error.message);
        document.getElementById('controls').classList.remove('hidden'); // Réafficher bouton si erreur
    }
}

// --- Initialisation ---

document.addEventListener('DOMContentLoaded', async () => {
    try {
        currentVideoUrl = await getCurrentVideoUrl();

        // Vérifier si une analyse existe déjà
        const existingData = await checkExistingAnalysis(currentVideoUrl);

        if (existingData) {
            console.log("Données récupérées du cache");
            renderResults(existingData);
        } else {
            // Afficher l'état initial
            document.getElementById('controls').classList.remove('hidden');
        }

    } catch (e) {
        console.error("Erreur init:", e);
        // On affiche l'erreur exacte pour le debug
        showStatus(`⚠️ ${e.message}`, 'warning');
        // On laisse le bouton activé pour permettre de réessayer manuellement
        analyzeBtn.disabled = false;
    }
});

// --- Event Listeners ---

analyzeBtn.addEventListener('click', () => analyzeVideo(false));

newAnalysisBtn.addEventListener('click', () => {
    // Forcer une nouvelle analyse
    analyzeVideo(true);
});

copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(rawReport.textContent).then(() => {
        showStatus('Rapport copié !', 'success');
    }).catch(err => {
        showError('Erreur lors de la copie');
    });
});
