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

        // Auto-check DB for existing analysis
        UI.showLoading('Vérification de l\'analyse...');

        try {
            const response = await API.analyzeVideo(currentVideoUrl, false);

            // Analysis found - render and show status
            await cache.set(currentVideoUrl, response.data);
            UI.renderResults(response.data);
            UI.showAnalysisStatus(response.data);

        } catch (error) {
            // No analysis found or error
            console.log('No existing analysis:', error.message);
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
        UI.showLoading(forceRefresh ? 'Nouvelle analyse en cours...' : 'Analyse en cours...');

        // Récupérer l'URL si pas encore fait
        if (!currentVideoUrl) {
            currentVideoUrl = await API.getCurrentVideoUrl();
        }

        // Appel API
        const response = await API.analyzeVideo(currentVideoUrl, forceRefresh);

        // Sauvegarder en cache
        await cache.set(currentVideoUrl, response.data);

        // Afficher les résultats
        UI.renderResults(response.data);
        UI.showAnalysisStatus(response.data);

        if (response.data.cached) {
            UI.showStatus('Résultat récupéré du cache', 'info');
        } else {
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
