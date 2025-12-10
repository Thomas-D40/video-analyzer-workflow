/**
 * Module UI - Orchestration de l'interface utilisateur
 */

// DOM Management
import {
  initDOMElements,
  showLoading,
  hideLoading,
  showError,
  showStatus,
  showControls,
  hideControls,
  hideAnalysisStatus,
  showNotYouTubeMessage,
  getButtons,
  getRawReport,
  getSelectedMode,
} from "./ui/dom.js";

// Modal
import { initModal } from "./ui/modal.js";

// Modes
import { getBestAvailableAnalysis, showAvailableModes } from "./ui/modes.js";

// Results
import { renderResults } from "./ui/results.js";

// Mode labels for exports
import { MODE_LABELS } from "./constants.js";

// État global
let currentAnalysisData = null;

/**
 * Initialise les éléments DOM du module UI
 */
export function initUIElements() {
  initDOMElements();
  initModal();
}

/**
 * Affiche le panneau de statut avec les métadonnées de l'analyse
 */
export function showAnalysisStatus(videoData) {
  console.log("[UI] showAnalysisStatus called with videoData:", videoData);

  const best = getBestAvailableAnalysis(videoData.analyses);
  if (!best) {
    console.warn("[UI] No analysis found in videoData");
    showNoAnalysisState();
    return;
  }

  // Masquer le panneau de statut
  hideAnalysisStatus();

  // Afficher l'interface des modes disponibles
  showAvailableModes(videoData, best.mode, handleModeSwitch);

  // Masquer les contrôles
  hideControls();

  // Stocker les données
  currentAnalysisData = videoData;
}

/**
 * Affiche l'état "aucune analyse disponible"
 */
export function showNoAnalysisState() {
  hideAnalysisStatus();
  showControls();
}

/**
 * Gère le changement de mode d'analyse
 */
async function handleModeSwitch(mode, forceNew = false) {
  try {
    // Si on a déjà les données et qu'on ne force pas la nouvelle analyse
    if (
      !forceNew &&
      currentAnalysisData &&
      currentAnalysisData.analyses &&
      currentAnalysisData.analyses[mode]
    ) {
      console.log(`[UI] Switching to ${mode} using cached data`);
      renderResults(currentAnalysisData, mode, handleReanalyze);
      showAvailableModes(currentAnalysisData, mode, handleModeSwitch);
      return;
    }

    // Besoin de récupérer/créer l'analyse
    if (forceNew) {
      showLoading(`Création de l'analyse ${MODE_LABELS[mode]}...`, 0);
    } else {
      showLoading(`Chargement de l'analyse ${MODE_LABELS[mode]}...`);
    }

    const { getCurrentVideoUrl, analyzeVideo, analyzeVideoStreaming } =
      await import("./api.js");

    const currentUrl = await getCurrentVideoUrl();
    if (!currentUrl) {
      showNotYouTubeMessage();
      return;
    }

    let response;
    if (forceNew) {
      response = await analyzeVideoStreaming(
        currentUrl,
        true,
        mode,
        (percent, message) => {
          showLoading(message, percent);
        }
      );
    } else {
      response = await analyzeVideo(currentUrl, false, mode);
    }

    // Mise à jour du cache
    const browser = await import("./polyfill.js");
    const storageData = {};
    storageData[currentUrl] = response;
    await browser.default.storage.local.set(storageData);

    // Mise à jour de l'état
    currentAnalysisData = response;

    // Rendu des résultats
    renderResults(response, mode, handleReanalyze);
    showAvailableModes(response, mode, handleModeSwitch);

    const statusMsg = forceNew
      ? `Analyse ${MODE_LABELS[mode]} créée !`
      : `Analyse ${MODE_LABELS[mode]} chargée !`;
    showStatus(statusMsg, "success");
  } catch (error) {
    showError(`Erreur lors du changement de mode: ${error.message}`);
  }
}

/**
 * Gère la ré-analyse
 */
async function handleReanalyze(forceRefresh = true) {
  const { analyzeVideo } = await import("./main.js");
  if (analyzeVideo) {
    analyzeVideo(forceRefresh);
  }
}

/**
 * Rend les résultats de l'analyse
 * @param {Object} videoData - Données vidéo complètes
 * @param {string|null} mode - Mode spécifique (optionnel)
 */
export function renderAnalysisResults(videoData, mode = null) {
  renderResults(videoData, mode, handleReanalyze);
  currentAnalysisData = videoData;
}

// Alias pour compatibilité avec main.js
export { renderAnalysisResults as renderResults };

// Exports pour compatibilité
export {
  showLoading,
  hideLoading,
  showError,
  showStatus,
  showControls,
  hideControls,
  hideAnalysisStatus,
  showNotYouTubeMessage,
  getButtons,
  getRawReport,
  getSelectedMode,
};
