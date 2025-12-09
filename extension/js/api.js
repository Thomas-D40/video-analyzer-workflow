/**
 * Module API - Communication avec le backend
 */

import browser from "./polyfill.js";
import { getCurrentApiKey } from "./auth.js";
import { getYouTubeCookies } from "./cookies.js";
import { getApiUrl } from "./config.js";

/**
 * Analyse une vidéo YouTube
 * @param {string} url - URL de la vidéo YouTube
 * @param {boolean} forceRefresh - Force une nouvelle analyse (ignore le cache)
 * @param {string} analysisMode - Mode d'analyse: 'simple', 'medium', 'hard'
 * @returns {Promise<Object>} - Données de l'analyse
 */
export async function analyzeVideo(
  url,
  forceRefresh = false,
  analysisMode = "simple"
) {
  const headers = { "Content-Type": "application/json" };

  // Ajouter la clé API si disponible
  const apiKey = getCurrentApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  // Extraire les cookies YouTube
  const youtubeCookies = await getYouTubeCookies();

  const response = await fetch(getApiUrl(), {
    method: "POST",
    headers: headers,
    body: JSON.stringify({
      url: url,
      force_refresh: forceRefresh,
      analysis_mode: analysisMode,
      youtube_cookies: youtubeCookies, // Ajouter les cookies dans le body
    }),
  });

  // Gestion des erreurs d'authentification
  if (response.status === 401 || response.status === 403) {
    const error = new Error("AUTH_REQUIRED");
    error.status = response.status;
    throw error;
  }

  // Gestion des autres erreurs HTTP
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(
      errorData.detail || `Erreur HTTP ${response.status}`
    );
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
  const { getHealthUrl } = await import("./config.js");
  const response = await fetch(getHealthUrl());

  if (!response.ok) {
    throw new Error("Backend non disponible");
  }

  return await response.json();
}

/**
 * Extrait l'ID d'une vidéo YouTube depuis l'URL
 * @param {string} url - URL YouTube
 * @returns {string|null} - ID de la vidéo ou null
 */
export function extractVideoId(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.searchParams.get("v");
  } catch (e) {
    return null;
  }
}

/**
 * Récupère les analyses disponibles pour une vidéo
 * @param {string} videoId - ID de la vidéo YouTube
 * @returns {Promise<Object>} - Liste des analyses disponibles
 */
export async function getAvailableAnalyses(videoId) {
  const headers = { "Content-Type": "application/json" };

  // Ajouter la clé API si disponible
  const apiKey = getCurrentApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const { getApiBaseUrl } = await import("./config.js");
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/api/analyze/${videoId}`, {
    method: "GET",
    headers: headers,
  });

  if (!response.ok) {
    // Si l'API retourne une erreur, on retourne juste une liste vide
    // (pas besoin de bloquer l'utilisateur)
    console.warn("Failed to fetch available analyses:", response.status);
    return { analyses: [], total_count: 0 };
  }

  return await response.json();
}

/**
 * Récupère l'URL de la vidéo YouTube active
 * @returns {Promise<string|null>} - URL de la vidéo ou null si pas sur YouTube
 */
export async function getCurrentVideoUrl() {
  try {
    // Essai 1: Fenêtre courante
    let tabs = await browser.tabs.query({ active: true, currentWindow: true });

    // Essai 2: Dernière fenêtre focus (fallback)
    if (!tabs || tabs.length === 0) {
      tabs = await browser.tabs.query({
        active: true,
        lastFocusedWindow: true,
      });
    }

    const tab = tabs[0];

    if (!tab || !tab.url) {
      // Expected case: no active tab or no URL access
      return null;
    }

    if (!tab.url.includes("youtube.com/watch")) {
      // Expected case: not on YouTube video page
      return null;
    }

    return tab.url;
  } catch (e) {
    // Unexpected error (permissions, etc.)
    console.error("Erreur getCurrentVideoUrl:", e);
    return null;
  }
}

/**
 * Analyse une vidéo avec progression en streaming (SSE)
 * @param {string} url - URL de la vidéo YouTube
 * @param {boolean} forceRefresh - Force une nouvelle analyse
 * @param {string} analysisMode - Mode d'analyse
 * @param {Function} onProgress - Callback appelé pour chaque mise à jour: (percent, message) => void
 * @returns {Promise<Object>} - Données de l'analyse finale
 */
export async function analyzeVideoStreaming(
  url,
  forceRefresh = false,
  analysisMode = "simple",
  onProgress
) {
  const headers = { "Content-Type": "application/json" };

  // Ajouter la clé API si disponible
  const apiKey = getCurrentApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  // Extraire les cookies YouTube
  const youtubeCookies = await getYouTubeCookies();

  const { getApiBaseUrl } = await import("./config.js");
  const baseUrl = getApiBaseUrl();

  const response = await fetch(`${baseUrl}/api/analyze/stream`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify({
      url: url,
      force_refresh: forceRefresh,
      analysis_mode: analysisMode,
      youtube_cookies: youtubeCookies,
    }),
  });

  // Gestion des erreurs HTTP
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      const error = new Error("AUTH_REQUIRED");
      error.status = response.status;
      throw error;
    }
    throw new Error(`HTTP error ${response.status}`);
  }

  // Lire le stream SSE
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Garde la dernière ligne incomplète

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const eventData = JSON.parse(line.substring(6));

          if (eventData.type === "progress") {
            // Appeler le callback de progression
            if (onProgress) {
              onProgress(eventData.percent, eventData.message);
            }
          } else if (eventData.type === "complete") {
            // Analyse terminée
            finalResult = eventData.data;
          } else if (eventData.type === "error") {
            throw new Error(eventData.message);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalResult) {
    throw new Error("Analysis completed but no result received");
  }

  return finalResult;
}
