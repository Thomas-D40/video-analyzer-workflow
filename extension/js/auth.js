/**
 * Module d'authentification - Gestion de la clé API
 */

import browser from './polyfill.js';

// Éléments DOM
let apiKeySetup, apiKeyInput, saveApiKeyBtn, toggleApiKeyVisibility;

// État
let apiKey = '';

/**
 * Initialise les éléments DOM du module auth
 */
export function initAuthElements() {
    apiKeySetup = document.getElementById('apiKeySetup');
    apiKeyInput = document.getElementById('apiKeyInput');
    saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    toggleApiKeyVisibility = document.getElementById('toggleApiKeyVisibility');

    // Event listeners
    if (saveApiKeyBtn) {
        saveApiKeyBtn.addEventListener('click', handleSaveApiKey);
    }

    if (toggleApiKeyVisibility) {
        toggleApiKeyVisibility.addEventListener('click', toggleKeyVisibility);
    }
}

/**
 * Récupère la clé API depuis le storage
 */
export async function getApiKey() {
    const result = await browser.storage.local.get(['apiKey']);
    apiKey = result.apiKey || '';
    return apiKey;
}

/**
 * Sauvegarde la clé API dans le storage
 */
export async function saveApiKey(key) {
    await browser.storage.local.set({ apiKey: key });
    apiKey = key;
}

/**
 * Affiche l'écran de configuration de la clé API
 */
export function showSetupScreen() {
    if (apiKeySetup) {
        apiKeySetup.classList.remove('hidden');
        if (apiKeyInput) apiKeyInput.focus();
    }
}

/**
 * Masque l'écran de configuration de la clé API
 */
export function hideSetupScreen() {
    if (apiKeySetup) {
        apiKeySetup.classList.add('hidden');
    }
}

/**
 * Gère la sauvegarde de la clé API
 */
async function handleSaveApiKey() {
    const key = apiKeyInput?.value.trim();
    if (key) {
        await saveApiKey(key);
        hideSetupScreen();

        // Notifier le main.js qu'une clé a été sauvegardée
        window.dispatchEvent(new CustomEvent('apiKeySaved', { detail: { key } }));
    }
}

/**
 * Toggle la visibilité de la clé API
 */
function toggleKeyVisibility() {
    if (!apiKeyInput) return;

    if (apiKeyInput.type === 'password') {
        apiKeyInput.type = 'text';
        toggleApiKeyVisibility.textContent = '🙈';
    } else {
        apiKeyInput.type = 'password';
        toggleApiKeyVisibility.textContent = '👁️';
    }
}

/**
 * Retourne la clé API actuelle (sans appel async)
 */
export function getCurrentApiKey() {
    return apiKey;
}
