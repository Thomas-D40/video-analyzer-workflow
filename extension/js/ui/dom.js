/**
 * UI - DOM element management
 */

import { TIMEOUTS } from "../constants.js";

// DOM element references
let elements = {};

/**
 * Initialise les références aux éléments DOM
 */
export function initDOMElements() {
  elements = {
    loading: document.getElementById("loading"),
    results: document.getElementById("results"),
    error: document.getElementById("error"),
    status: document.getElementById("status"),
    videoSummary: document.getElementById("videoSummary"),
    argumentsList: document.getElementById("argumentsList"),
    rawReport: document.getElementById("rawReport"),
    controls: document.getElementById("controls"),
    analyzeBtn: document.getElementById("analyzeBtn"),
    newAnalysisBtn: document.getElementById("newAnalysisBtn"),
    copyBtn: document.getElementById("copyBtn"),
    analysisModeSelect: document.getElementById("analysisMode"),
    analysisStatus: document.getElementById("analysisStatus"),
    statusMetadata: document.getElementById("statusMetadata"),
    toggleResultsBtn: document.getElementById("toggleResultsBtn"),
    reAnalyzeBtn: document.getElementById("reAnalyzeBtn"),
    statusIcon: document.getElementById("statusIcon"),
    statusText: document.getElementById("statusText"),
    modal: document.getElementById("sourcesModal"),
    closeModalBtn: document.getElementById("closeModalBtn"),
    modalSourcesList: document.getElementById("modalSourcesList"),
  };

  return elements;
}

/**
 * Retourne un élément DOM
 */
export function getElement(key) {
  return elements[key];
}

/**
 * Retourne tous les éléments DOM
 */
export function getAllElements() {
  return elements;
}

/**
 * Affiche le loader avec progression optionnelle
 */
export function showLoading(message = "Analyse en cours...", percent = null) {
  const loadingDiv = elements.loading;
  if (!loadingDiv) return;

  loadingDiv.classList.remove("hidden");

  const loadingText = loadingDiv.querySelector("p:first-of-type");
  if (loadingText) {
    loadingText.textContent = message;
  }

  let progressBar = loadingDiv.querySelector(".progress-bar");
  let progressPercent = loadingDiv.querySelector(".progress-percent");

  if (percent !== null) {
    if (!progressBar) {
      const progressContainer = document.createElement("div");
      progressContainer.className = "progress-container";
      progressContainer.innerHTML = `
        <div class="progress-bar-track">
          <div class="progress-bar" style="width: 0%"></div>
        </div>
        <div class="progress-percent">0%</div>
      `;
      loadingDiv.appendChild(progressContainer);
      progressBar = progressContainer.querySelector(".progress-bar");
      progressPercent = progressContainer.querySelector(".progress-percent");
    }

    if (progressBar) progressBar.style.width = `${percent}%`;
    if (progressPercent) progressPercent.textContent = `${percent}%`;
  }

  if (elements.results) elements.results.classList.add("hidden");
  if (elements.error) elements.error.classList.add("hidden");
  if (elements.controls) elements.controls.classList.add("hidden");
}

/**
 * Masque le loader
 */
export function hideLoading() {
  if (elements.loading) {
    elements.loading.classList.add("hidden");
  }
}

/**
 * Affiche une erreur
 */
export function showError(message) {
  if (elements.error) {
    elements.error.textContent = `❌ ${message}`;
    elements.error.classList.remove("hidden");
  }
  hideLoading();
  if (elements.analyzeBtn) {
    elements.analyzeBtn.disabled = false;
  }
}

/**
 * Affiche un message de statut
 */
export function showStatus(message, type = "info") {
  if (!elements.status) return;

  elements.status.textContent = message;
  elements.status.className = `status ${type}`;
  elements.status.classList.remove("hidden");

  if (type === "success" || type === "error") {
    setTimeout(() => {
      elements.status.classList.add("hidden");
    }, TIMEOUTS.STATUS_MESSAGE);
  }
}

/**
 * Affiche les contrôles (bouton analyser)
 */
export function showControls() {
  if (elements.controls) {
    elements.controls.classList.remove("hidden");
  }
}

/**
 * Masque les contrôles
 */
export function hideControls() {
  if (elements.controls) {
    elements.controls.classList.add("hidden");
  }
}

/**
 * Masque le panneau de statut
 */
export function hideAnalysisStatus() {
  if (elements.analysisStatus) {
    elements.analysisStatus.classList.add("hidden");
  }
}

/**
 * Affiche le message "pas sur YouTube"
 */
export function showNotYouTubeMessage() {
  hideLoading();
  hideControls();
  hideAnalysisStatus();

  if (elements.error) elements.error.classList.add("hidden");
  if (elements.status) elements.status.classList.add("hidden");

  const existingModes = document.getElementById("availableModesSection");
  if (existingModes) existingModes.remove();

  if (elements.results) {
    elements.results.innerHTML = `
      <div style="padding: 40px 20px; text-align: center;">
        <div style="font-size: 48px; margin-bottom: 20px;">📺</div>
        <div style="font-size: 18px; font-weight: 600; color: #2d3748; margin-bottom: 12px;">
          Page YouTube requise
        </div>
        <div style="color: #718096; font-size: 14px; line-height: 1.6;">
          Cette extension fonctionne uniquement sur les vidéos YouTube.<br>
          Ouvrez une vidéo YouTube pour analyser son contenu.
        </div>
      </div>
    `;
    elements.results.classList.remove("hidden");
    elements.results.classList.remove("collapsed");
  }
}

/**
 * Retourne les boutons pour les event listeners
 */
export function getButtons() {
  return {
    analyzeBtn: elements.analyzeBtn,
    newAnalysisBtn: elements.newAnalysisBtn,
    copyBtn: elements.copyBtn,
    reAnalyzeBtn: elements.reAnalyzeBtn,
  };
}

/**
 * Retourne le rawReport
 */
export function getRawReport() {
  return elements.rawReport;
}

/**
 * Retourne le mode d'analyse sélectionné
 */
export function getSelectedMode() {
  return elements.analysisModeSelect
    ? elements.analysisModeSelect.value
    : "simple";
}
