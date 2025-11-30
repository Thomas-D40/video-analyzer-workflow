/**
 * Module API - Communication avec le backend
 */

import browser from './polyfill.js';
import { getCurrentApiKey } from './auth.js';
import { getYouTubeCookies } from './cookies.js';

// Use HTTPS for secure communication
// Note: If using self-signed certificate, you may need to accept it in browser first
const API_URL = 'https://46.202.128.11:8000/api/analyze';

/**
 * Analyse une vidéo YouTube
 * @param {string} url - URL de la vidéo YouTube
 * @param {boolean} forceRefresh - Force une nouvelle analyse (ignore le cache)
 * @returns {Promise<Object>} - Données de l'analyse
 */
export async function analyzeVideo(url, forceRefresh = false) {
    const headers = { 'Content-Type': 'application/json' };

    // Ajouter la clé API si disponible
    const apiKey = getCurrentApiKey();
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }

    // Extraire les cookies YouTube
    const youtubeCookies = await getYouTubeCookies();

    const response = await fetch(API_URL, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
            url: url,
            force_refresh: forceRefresh,
            youtube_cookies: youtubeCookies  // Ajouter les cookies dans le body
        })
    });

    // Gestion des erreurs d'authentification
    if (response.status === 401 || response.status === 403) {
        const error = new Error('AUTH_REQUIRED');
        error.status = response.status;
        throw error;
    }

    // Gestion des autres erreurs HTTP
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `Erreur HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }

    return await response.json();
}

/**
 * Vérifie la santé du backend
 * @returns {Promise<Object>} - Statut du backend
 */
export async function checkHealth() {
    const response = await fetch('http://localhost:8000/health');

    if (!response.ok) {
        throw new Error('Backend non disponible');
    }

    return await response.json();
}

/**
 * Récupère l'URL de la vidéo YouTube active
 * @returns {Promise<string>} - URL de la vidéo
 */
export async function getCurrentVideoUrl() {
    try {
        // Essai 1: Fenêtre courante
        let tabs = await browser.tabs.query({ active: true, currentWindow: true });

        // Essai 2: Dernière fenêtre focus (fallback)
        if (!tabs || tabs.length === 0) {
            tabs = await browser.tabs.query({ active: true, lastFocusedWindow: true });
        }

        const tab = tabs[0];

        if (!tab) {
            throw new Error("Aucun onglet actif trouvé");
        }

        if (!tab.url) {
            throw new Error("Impossible de lire l'URL (Permissions?)");
        }

        if (!tab.url.includes('youtube.com/watch')) {
            throw new Error(`Pas une vidéo YouTube`);
        }

        return tab.url;
    } catch (e) {
        console.error("Erreur getCurrentVideoUrl:", e);
        throw e;
    }
}
