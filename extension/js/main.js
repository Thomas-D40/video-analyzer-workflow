/**
 * Module principal - Orchestration de l'extension
 */

import browser from './polyfill.js';
import * as Auth from './auth.js';
import * as API from './api.js';
import * as UI from './ui.js';

// État global
let currentVideoUrl = '';

// Cache local
const cache = {
    async get(url) {
        const result = await browser.storage.local.get([url]);
        return result[url];
    },

    async set(url, data) {
        const storageData = {};
        storageData[url] = data;
        await browser.storage.local.set(storageData);
    }
};

/**
 * Initialisation de l'extension
 */
async function init() {
    // Initialiser les modules
    Auth.initAuthElements();
    UI.initUIElements();

    try {
        // Charger la clé API
        const apiKey = await Auth.getApiKey();

        // Si pas de clé, afficher l'écran de configuration
        if (!apiKey) {
            Auth.showSetupScreen();
            return;
        }

        // Récupérer l'URL de la vidéo YouTube
        currentVideoUrl = await API.getCurrentVideoUrl();

        // Check if analysis exists in local cache first
        const cachedData = await cache.get(currentVideoUrl);
        if (cachedData) {
            console.log("Données récupérées du cache local");
            UI.renderResults(cachedData);
            UI.showAnalysisStatus(cachedData);
            return;
        }

        // Check DB for existing analysis WITHOUT triggering new analysis
        UI.showLoading('Vérification de l\'analyse...');

        const videoId = API.extractVideoId(currentVideoUrl);
        if (!videoId) {
            UI.hideLoading();
            UI.showNoAnalysisState();
            return;
        }

        try {
            const availableAnalyses = await API.getAvailableAnalyses(videoId);

            if (availableAnalyses && availableAnalyses.analyses && availableAnalyses.analyses.length > 0) {
                // Analysis exists - fetch it (will return all analyses)
                const response = await API.analyzeVideo(currentVideoUrl, false);

                // New structure: response has {id, youtube_url, analyses, selected_mode}
                // Extract the selected analysis content
                const selectedAnalysis = response.analyses[response.selected_mode];
                if (selectedAnalysis && selectedAnalysis.content) {
                    const analysisData = {
                        ...selectedAnalysis.content,
                        // Add metadata about all available analyses
                        _all_analyses: response.analyses,
                        _selected_mode: response.selected_mode
                    };
                    await cache.set(currentVideoUrl, analysisData);
                    UI.renderResults(analysisData);
                    UI.showAnalysisStatus(analysisData);
                } else {
                    UI.hideLoading();
                    UI.showNoAnalysisState();
                }
            } else {
                // No analysis found
                UI.hideLoading();
                UI.showNoAnalysisState();
            }

        } catch (error) {
            // Error checking for analysis
            console.log('Error checking for analysis:', error.message);
            UI.hideLoading();
            UI.showNoAnalysisState();
        }

    } catch (e) {
        console.error("Erreur init:", e);
        UI.hideLoading();
        UI.showStatus(`⚠️ ${e.message}`, 'warning');
        UI.showNoAnalysisState();
    }
}

/**
 * Lance une analyse de vidéo
 */
async function analyzeVideo(forceRefresh = false) {
    try {
        // Reset UI
        UI.hideAnalysisStatus();
        UI.showLoading(forceRefresh ? 'Nouvelle analyse en cours...' : 'Analyse en cours...', 0);

        // Récupérer l'URL si pas encore fait
        if (!currentVideoUrl) {
            currentVideoUrl = await API.getCurrentVideoUrl();
        }

        // Get selected analysis mode
        const analysisMode = UI.getSelectedMode();
        console.log('[Main] Starting analysis with mode:', analysisMode);

        // Use streaming API for new analyses
        if (forceRefresh) {
            const response = await API.analyzeVideoStreaming(
                currentVideoUrl,
                forceRefresh,
                analysisMode,
                (percent, message) => {
                    // Progress callback
                    UI.showLoading(message, percent);
                }
            );

            // New structure: extract the selected analysis content
            const selectedAnalysis = response.analyses[response.selected_mode];
            if (selectedAnalysis && selectedAnalysis.content) {
                const analysisData = {
                    ...selectedAnalysis.content,
                    _all_analyses: response.analyses,
                    _selected_mode: response.selected_mode
                };

                // Sauvegarder en cache
                await cache.set(currentVideoUrl, analysisData);

                // Afficher les résultats
                UI.renderResults(analysisData);
                UI.showAnalysisStatus(analysisData);
                UI.showStatus('Analyse terminée !', 'success');
            }
        } else {
            // For cached analyses, use regular endpoint (faster)
            const response = await API.analyzeVideo(currentVideoUrl, false, analysisMode);

            // New structure: extract the selected analysis content
            const selectedAnalysis = response.analyses[response.selected_mode];
            if (selectedAnalysis && selectedAnalysis.content) {
                const analysisData = {
                    ...selectedAnalysis.content,
                    _all_analyses: response.analyses,
                    _selected_mode: response.selected_mode
                };

                // Sauvegarder en cache
                await cache.set(currentVideoUrl, analysisData);

                // Afficher les résultats
                UI.renderResults(analysisData);
                UI.showAnalysisStatus(analysisData);

                if (analysisData.cached) {
                    UI.showStatus('Résultat récupéré du cache', 'info');
                } else {
                    UI.showStatus('Analyse terminée !', 'success');
                }
            }
        }

    } catch (error) {
        console.error('Erreur:', error);

        if (error.message === 'AUTH_REQUIRED') {
            UI.showError("Clé API manquante ou invalide");
            Auth.showSetupScreen();
        } else {
            UI.showError(error.message);
            UI.showNoAnalysisState();
        }
    }
}

/**
 * Copie le rapport dans le presse-papiers
 */
function copyReport() {
    const rawReport = UI.getRawReport();
    if (rawReport) {
        navigator.clipboard.writeText(rawReport.textContent).then(() => {
            UI.showStatus('Rapport copié !', 'success');
        }).catch(err => {
            UI.showError('Erreur lors de la copie');
        });
    }
}

/**
 * Event listeners
 */
function setupEventListeners() {
    const { analyzeBtn, newAnalysisBtn, copyBtn, reAnalyzeBtn } = UI.getButtons();

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => analyzeVideo(false));
    }

    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener('click', () => analyzeVideo(true));
    }

    if (reAnalyzeBtn) {
        reAnalyzeBtn.addEventListener('click', () => analyzeVideo(true));
    }

    if (copyBtn) {
        copyBtn.addEventListener('click', copyReport);
    }

    // Écouter l'événement de sauvegarde de clé API
    window.addEventListener('apiKeySaved', async (e) => {
        UI.showStatus('Clé API enregistrée avec succès !', 'success');

        // Réinitialiser l'extension
        try {
            currentVideoUrl = await API.getCurrentVideoUrl();
            const cachedData = await cache.get(currentVideoUrl);

            if (cachedData) {
                UI.renderResults(cachedData);
            } else {
                UI.showControls();
            }
        } catch (e) {
            UI.showControls();
        }
    });
}

/**
 * Point d'entrée
 */
document.addEventListener('DOMContentLoaded', async () => {
    await init();
    setupEventListeners();
});
