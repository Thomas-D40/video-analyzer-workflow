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
    },

    async clear(url) {
        await browser.storage.local.remove([url]);
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

        // Vérifier qu'on est sur YouTube
        currentVideoUrl = await API.getCurrentVideoUrl();
        if (!currentVideoUrl) {
            // Not on YouTube or can't access URL
            UI.hideLoading();
            UI.showNotYouTubeMessage();
            return;
        }

        // Check if analysis exists in local cache first
        const cachedData = await cache.get(currentVideoUrl);
        if (cachedData) {
            console.log("Données récupérées du cache local:", cachedData);

            // Validate cache structure - must have new format {id, youtube_url, analyses}
            if (cachedData.analyses && typeof cachedData.analyses === 'object') {
                console.log("Cache valide - structure nouvelle");
                UI.renderResults(cachedData);
                UI.showAnalysisStatus(cachedData);
                return;
            } else {
                // Old cache structure - clear it
                console.warn("Cache invalide (ancienne structure) - nettoyage...");
                await cache.clear(currentVideoUrl);
            }
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
                // Analysis exists - fetch all analyses at once
                const response = await API.analyzeVideo(currentVideoUrl, false);

                console.log('[Main] API response:', response);
                console.log('[Main] Response analyses:', response.analyses);

                // Response has {id, youtube_url, analyses: {simple, medium, hard}}
                // Cache the entire response
                await cache.set(currentVideoUrl, response);

                // Pass the whole response to UI
                UI.renderResults(response);
                UI.showAnalysisStatus(response);
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
        UI.showError(`Erreur: ${e.message}`);
    }
}

/**
 * Lance une analyse de vidéo
 */
export async function analyzeVideo(forceRefresh = false) {
    try {
        // Reset UI
        UI.hideAnalysisStatus();
        UI.showLoading(forceRefresh ? 'Nouvelle analyse en cours...' : 'Analyse en cours...', 0);

        // Récupérer l'URL si pas encore fait
        if (!currentVideoUrl) {
            currentVideoUrl = await API.getCurrentVideoUrl();
            if (!currentVideoUrl) {
                UI.hideLoading();
                UI.showNotYouTubeMessage();
                return;
            }
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

            // Response has {id, youtube_url, analyses: {simple, medium, hard}}
            // Cache the entire response
            await cache.set(currentVideoUrl, response);

            // Pass the whole response to UI
            UI.renderResults(response);
            UI.showAnalysisStatus(response);
            UI.showStatus('Analyse terminée !', 'success');
        } else {
            // For cached analyses, use regular endpoint (faster)
            const response = await API.analyzeVideo(currentVideoUrl, false, analysisMode);

            // Cache the entire response
            await cache.set(currentVideoUrl, response);

            // Pass the whole response to UI
            UI.renderResults(response);
            UI.showAnalysisStatus(response);
            UI.showStatus('Analyse terminée !', 'success');
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
        currentVideoUrl = await API.getCurrentVideoUrl();

        if (!currentVideoUrl) {
            UI.showNotYouTubeMessage();
            return;
        }

        const cachedData = await cache.get(currentVideoUrl);

        // Validate cache structure
        if (cachedData && cachedData.analyses && typeof cachedData.analyses === 'object') {
            UI.renderResults(cachedData);
        } else {
            if (cachedData) {
                // Clear invalid cache
                await cache.clear(currentVideoUrl);
            }
            UI.showNoAnalysisState();
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
