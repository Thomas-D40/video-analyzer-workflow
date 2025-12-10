/**
 * UI - Mode selection rendering
 */

import {
  MODE_HIERARCHY,
  MODE_LABELS,
  MODE_COSTS,
  ALL_MODE_CONFIGS,
} from "../constants.js";
import { formatDate, getAgeText } from "../utils/format.js";

/**
 * Trouve la meilleure analyse disponible
 */
export function getBestAvailableAnalysis(analyses) {
  console.log("[Modes] getBestAvailableAnalysis called with:", analyses);

  for (const mode of MODE_HIERARCHY) {
    console.log(`[Modes] Checking mode ${mode}:`, analyses[mode]);
    if (analyses[mode] && analyses[mode].content) {
      console.log(`[Modes] Found best analysis: ${mode}`);
      return { mode, data: analyses[mode] };
    }
  }

  console.warn("[Modes] No analysis found with content");
  return null;
}

/**
 * Génère le HTML pour une carte de mode
 */
function generateModeCardHTML(modeConfig, existingAnalysis, isCurrent) {
  const exists = !!existingAnalysis;

  let dateInfoHtml = "";
  let buttonText;
  let buttonClass = "btn-switch-mode";
  let itemClass = "available-mode-item";

  if (exists) {
    const dateStr = formatDate(existingAnalysis.updated_at);
    const ageText = getAgeText(existingAnalysis.updated_at);

    if (isCurrent) {
      itemClass += " current-mode";
      dateInfoHtml = `<div class="mode-date-info">👁️ Affichée • ${
        dateStr || ageText
      }</div>`;
      buttonText = "Affichée ci-dessous";
      buttonClass += " btn-current-mode";
    } else {
      dateInfoHtml = `<div class="mode-date-info">✓ Disponible • ${
        dateStr || ageText
      }</div>`;
      buttonText = "Voir cette analyse";
    }
  } else {
    dateInfoHtml = `<div class="mode-date-info mode-not-created">⚠️ Non créée • ${modeConfig.cost}</div>`;
    buttonText = "Créer cette analyse";
    buttonClass += " btn-create-mode";
  }

  return `
    <div class="${itemClass}">
      <div class="available-mode-header">
        <div class="available-mode-info">
          <span class="available-mode-desc">${modeConfig.desc}</span>
          ${dateInfoHtml}
        </div>
        <button class="${buttonClass}" data-mode="${modeConfig.mode}" data-exists="${exists}" ${isCurrent ? "disabled" : ""}>
          ${buttonText}
        </button>
      </div>
    </div>
  `;
}

/**
 * Affiche la confirmation pour créer une nouvelle analyse
 */
export function confirmNewAnalysis(mode) {
  return confirm(
    `⚠️ ATTENTION - Nouvelle analyse requise\n\n` +
      `Mode: ${MODE_LABELS[mode]}\n` +
      `Coût estimé: ${MODE_COSTS[mode]}\n\n` +
      `Une nouvelle analyse sera créée, ce qui consommera des crédits API.\n\n` +
      `Voulez-vous continuer ?`
  );
}

/**
 * Affiche la section des modes disponibles
 * @param {Object} videoData - Données vidéo avec analyses
 * @param {string} displayedMode - Mode actuellement affiché
 * @param {Function} onModeSwitch - Callback(mode, forceNew) appelé lors du clic
 */
export function showAvailableModes(videoData, displayedMode, onModeSwitch) {
  console.log("[Modes] showAvailableModes called, displayedMode:", displayedMode);

  const existingModes = document.getElementById("availableModesSection");
  if (existingModes) existingModes.remove();

  const allAnalyses = videoData.analyses || {};

  const modesHtml = ALL_MODE_CONFIGS.map((modeConfig) => {
    const existingAnalysis = allAnalyses[modeConfig.mode];
    const isCurrent = modeConfig.mode === displayedMode;
    return generateModeCardHTML(modeConfig, existingAnalysis, isCurrent);
  }).join("");

  const section = document.createElement("div");
  section.id = "availableModesSection";
  section.className = "available-modes-section";
  section.innerHTML = `
    <div class="available-modes-header">
      <span class="available-modes-icon">📊</span>
      <span class="available-modes-title">Modes d'analyse</span>
    </div>
    <div class="available-modes-list">
      ${modesHtml}
    </div>
  `;

  const resultsPanel = document.getElementById("results");
  if (resultsPanel && resultsPanel.parentNode) {
    resultsPanel.parentNode.insertBefore(section, resultsPanel);
  }

  // Attacher les handlers
  section.querySelectorAll(".btn-switch-mode:not(:disabled)").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const mode = btn.dataset.mode;
      const exists = btn.dataset.exists === "true";

      if (!exists && !confirmNewAnalysis(mode)) {
        return;
      }

      if (onModeSwitch) {
        await onModeSwitch(mode, !exists);
      }
    });
  });
}
