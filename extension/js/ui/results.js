/**
 * UI - Results rendering
 */

import { getElement, hideLoading } from "./dom.js";
import { formatDate } from "../utils/format.js";
import { formatReliabilityScore } from "../utils/format.js";
import {
  collectUsedUrls,
  createSourceMap,
  countSourcesByType,
  generateSourceIcons,
  getSourceTitle,
  getSourceIcon,
} from "../utils/sources.js";
import { getBestAvailableAnalysis } from "./modes.js";
import { openSourcesModal } from "./modal.js";

/**
 * Rend un point (pro ou con) avec son lien source
 */
function renderPoint(point, sourceMap) {
  const isObj = typeof point === "object";
  const text = isObj ? point.claim : point;
  const url = isObj ? point.source : null;

  let sourceLink = "";
  if (url) {
    const sourceData = sourceMap.get(url);
    const sourceTitle = getSourceTitle(url, sourceData);
    const icon = getSourceIcon(sourceData);

    sourceLink = `
      <a href="${url}" target="_blank" class="inline-source-link" title="${sourceTitle}">
        ${icon} Source
      </a>`;
  }

  return `<li><span class="point-text">${text}</span> ${sourceLink}</li>`;
}

/**
 * Crée le tableau récapitulatif
 */
function renderSummaryTable(data) {
  if (!data.arguments || data.arguments.length === 0) return "";

  const rows = data.arguments
    .map((arg, index) => {
      const counts = countSourcesByType(arg.sources);
      const usedUrls = collectUsedUrls(arg.analysis);
      const usedSourceCount = usedUrls.size;

      const reliability = formatReliabilityScore(
        arg.reliability_score,
        usedSourceCount > 0
      );

      const sourceIcons = generateSourceIcons(arg.sources, index);

      return `
        <tr class="summary-row" data-arg-index="${index}" style="cursor:pointer">
          <td><span class="mini-badge ${reliability.class}">${reliability.display}</span></td>
          <td class="summary-arg-text">${arg.argument}</td>
          <td class="summary-sources">${sourceIcons}</td>
        </tr>
      `;
    })
    .join("");

  return `
    <div class="summary-table-container">
      <table class="summary-table" id="summaryTable">
        <thead>
          <tr>
            <th width="15%">Note</th>
            <th width="65%">Argument</th>
            <th width="20%">Sources</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Crée une carte d'argument
 */
function createArgumentCard(arg, index) {
  const sourceMap = createSourceMap(arg.sources);
  const usedUrls = collectUsedUrls(arg.analysis);
  const reliability = formatReliabilityScore(
    arg.reliability_score,
    usedUrls.size > 0
  );

  const prosHtml = arg.analysis?.pros?.length
    ? `<div class="pros-box">
         <div class="section-title" style="color:#276749; margin-top:0;">✅ Points qui corroborent</div>
         <ul class="pros-list">${arg.analysis.pros
           .map((p) => renderPoint(p, sourceMap))
           .join("")}</ul>
       </div>`
    : "";

  const consHtml = arg.analysis?.cons?.length
    ? `<div class="cons-box">
         <div class="section-title" style="color:#9b2c2c; margin-top:0;">❌ Points qui contredisent</div>
         <ul class="cons-list">${arg.analysis.cons
           .map((c) => renderPoint(c, sourceMap))
           .join("")}</ul>
       </div>`
    : "";

  let contentHtml = "";
  if (!prosHtml && !consHtml) {
    contentHtml = `
      <div class="no-analysis-msg">
        <p>Aucun point corroborant ou contradictoire n'a été extrait des sources pour cet argument.</p>
      </div>
    `;
  } else {
    contentHtml = prosHtml + consHtml;
  }

  const card = document.createElement("div");
  card.className = "arg-card collapsed";
  card.id = `arg-${index}`;
  card.innerHTML = `
    <div class="arg-header" style="cursor: pointer;">
      <div class="arg-title-container">
        <span class="expand-arrow">▼</span>
        <div class="arg-title">"${arg.argument}"</div>
      </div>
      <div class="reliability-container">
        <span class="reliability-badge ${reliability.class}">${reliability.label}</span>
        <span class="reliability-score">${reliability.percent}</span>
      </div>
    </div>
    <div class="arg-details">
      ${contentHtml}
    </div>
  `;

  const header = card.querySelector(".arg-header");
  header.addEventListener("click", () => {
    card.classList.toggle("collapsed");
  });

  return card;
}

/**
 * Attache les event handlers au tableau récapitulatif
 */
function attachSummaryTableHandlers(argumentsData) {
  const summaryTable = document.getElementById("summaryTable");
  if (!summaryTable) return;

  summaryTable.addEventListener("click", (e) => {
    const trigger = e.target.closest(".sources-trigger");
    if (trigger) {
      e.stopPropagation();
      const index = parseInt(trigger.dataset.argIndex);
      if (argumentsData[index]) {
        openSourcesModal(argumentsData[index], e);
      }
      return;
    }

    const row = e.target.closest(".summary-row");
    if (row) {
      const index = parseInt(row.dataset.argIndex);
      const targetEl = document.getElementById(`arg-${index}`);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: "smooth" });
      }
    }
  });
}

/**
 * Rend les résultats de l'analyse
 * @param {Object} videoData - Données complètes de la vidéo
 * @param {string|null} mode - Mode spécifique à afficher (optionnel)
 * @param {Function} onReanalyze - Callback pour ré-analyser
 */
export function renderResults(videoData, mode = null, onReanalyze = null) {
  console.log("[Results] renderResults called with:", videoData);

  let selectedAnalysis = null;
  const analyses = videoData.analyses;

  if (mode) {
    console.log(`[Results] Checking mode ${mode}:`, analyses[mode]);
    if (analyses[mode] && analyses[mode].content) {
      selectedAnalysis = { mode, data: analyses[mode] };
    }
  } else {
    selectedAnalysis = getBestAvailableAnalysis(analyses);
  }

  if (!selectedAnalysis) {
    console.error("[Results] No analysis to render");
    return;
  }

  console.log("[Results] Selected analysis:", selectedAnalysis.mode);

  const data = selectedAnalysis.data.content;
  if (!data) {
    console.error("[Results] No content in analysis");
    return;
  }

  // 1. Résumé + Tableau récapitulatif
  const videoSummary = getElement("videoSummary");
  const summaryTableHtml = renderSummaryTable(data);
  const argCount = data.arguments ? data.arguments.length : 0;

  let dateHtml = "";
  if (selectedAnalysis.data.updated_at) {
    const dateStr = formatDate(selectedAnalysis.data.updated_at);
    if (dateStr) {
      dateHtml = `<div class="summary-date">Mis à jour le ${dateStr}</div>`;
    }
  }

  if (videoSummary) {
    videoSummary.innerHTML = `
      <div class="summary-card">
        <div class="summary-header-row">
          <div class="summary-title">VIDÉO ANALYSÉE</div>
          <div class="summary-stats">
            ${argCount} arguments
            <button id="reAnalyzeBtn" class="btn-secondary" style="margin-left: 12px;" title="Nouvelle analyse">🔄 Refaire</button>
          </div>
        </div>
        ${dateHtml}
        ${summaryTableHtml}
      </div>
    `;
  }

  // Attacher le handler pour le bouton refaire
  const reAnalyzeBtn = document.getElementById("reAnalyzeBtn");
  if (reAnalyzeBtn && onReanalyze) {
    reAnalyzeBtn.addEventListener("click", () => onReanalyze(true));
  }

  // Event delegation pour le tableau
  attachSummaryTableHandlers(data.arguments || []);

  // 2. Liste des arguments détaillés
  const argumentsList = getElement("argumentsList");
  if (argumentsList) {
    argumentsList.innerHTML = "";
    data.arguments.forEach((arg, index) => {
      const card = createArgumentCard(arg, index);
      argumentsList.appendChild(card);
    });
  }

  // 3. Rapport brut
  const rawReport = getElement("rawReport");
  if (rawReport) {
    rawReport.textContent = data.report_markdown;
  }

  // Afficher les résultats
  const resultsDiv = getElement("results");
  if (resultsDiv) {
    resultsDiv.classList.remove("hidden");
    resultsDiv.classList.remove("collapsed");
  }
  hideLoading();
}
