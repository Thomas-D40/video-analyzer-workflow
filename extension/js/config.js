/**
 * Configuration de l'extension - Gestion des environnements
 *
 * Détecte automatiquement l'environnement et utilise le bon endpoint:
 * - Développement: HTTP (localhost ou IP directe)
 * - Production: HTTPS (avec certificat valide)
 */

/**
 * Détecte l'environnement d'exécution
 * @returns {'development'|'production'}
 */
function detectEnvironment() {
    // En développement, l'extension est chargée en mode "unpacked"
    // En production, elle a un ID stable
    const isUnpacked = chrome.runtime.getManifest().update_url === undefined;
    return isUnpacked ? 'development' : 'production';
}

/**
 * Configuration par environnement
 */
const config = {
    development: {
        apiUrl: 'http://46.202.128.11:8000/api/analyze',
        healthUrl: 'http://46.202.128.11:8000/health',
        useHttps: false
    },
    production: {
        apiUrl: 'https://46.202.128.11:8000/api/analyze',
        healthUrl: 'https://46.202.128.11:8000/health',
        useHttps: true
    }
};

// Détection automatique de l'environnement
const ENV = detectEnvironment();
const currentConfig = config[ENV];

console.log(`[Config] Environment: ${ENV}`);
console.log(`[Config] API URL: ${currentConfig.apiUrl}`);

/**
 * Obtient l'URL de l'API selon l'environnement
 * @returns {string}
 */
export function getApiUrl() {
    return currentConfig.apiUrl;
}

/**
 * Obtient l'URL de health check
 * @returns {string}
 */
export function getHealthUrl() {
    return currentConfig.healthUrl;
}

/**
 * Vérifie si HTTPS est activé
 * @returns {boolean}
 */
export function isHttpsEnabled() {
    return currentConfig.useHttps;
}

/**
 * Obtient l'environnement actuel
 * @returns {'development'|'production'}
 */
export function getEnvironment() {
    return ENV;
}

export default {
    getApiUrl,
    getHealthUrl,
    isHttpsEnabled,
    getEnvironment
};
