/**
 * UI - Modal management
 */

import { getElement } from "./dom.js";
import { getSourceTitle, getSourceIcon } from "../utils/sources.js";

/**
 * Initialise les event listeners de la modal
 */
export function initModal() {
  const modal = getElement("modal");
  const closeModalBtn = getElement("closeModalBtn");

  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", closeSourcesModal);
  }

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeSourcesModal();
    });
  }
}

/**
 * Ouvre la modal des sources
 */
export function openSourcesModal(arg, event = null) {
  if (event) event.stopPropagation();

  const modal = getElement("modal");
  const modalSourcesList = getElement("modalSourcesList");

  if (!modalSourcesList) return;

  modalSourcesList.innerHTML = "";

  const allSources = [
    ...(arg.sources?.scientific || []),
    ...(arg.sources?.medical || []),
    ...(arg.sources?.statistical || []),
  ];

  if (allSources.length === 0) {
    modalSourcesList.innerHTML =
      '<div style="padding:20px; text-align:center; color:#718096">Aucune source disponible</div>';
  } else {
    allSources.forEach((source) => {
      const icon = getSourceIcon(source);
      const title = getSourceTitle(source.url, source);

      const item = document.createElement("div");
      item.className = "source-item";
      item.innerHTML = `
        <span class="source-icon">${icon}</span>
        <div class="source-info">
          <a href="${source.url}" target="_blank" class="source-title">${title}</a>
          <div class="source-url">${source.url}</div>
        </div>
      `;
      modalSourcesList.appendChild(item);
    });
  }

  if (modal) modal.classList.remove("hidden");
}

/**
 * Ferme la modal des sources
 */
export function closeSourcesModal() {
  const modal = getElement("modal");
  if (modal) modal.classList.add("hidden");
}
