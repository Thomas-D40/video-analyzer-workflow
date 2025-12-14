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
 * Flatten the argument tree structure for display
 */
function flattenArgumentTree(argumentStructure, enrichedThesisArgs) {
  const flatList = [];

  if (!argumentStructure) {
    return flatList;
  }

  // Create a map of thesis arguments to their enriched data (for reliability scores)
  const enrichedMap = new Map();
  if (enrichedThesisArgs) {
    enrichedThesisArgs.forEach((enriched) => {
      enrichedMap.set(enriched.argument, enriched);
    });
  }

  // Flatten each reasoning chain
  if (argumentStructure.reasoning_chains) {
    argumentStructure.reasoning_chains.forEach((chain, chainIndex) => {
      const thesis = chain.thesis;

      // Add thesis
      const enrichedData = enrichedMap.get(thesis.argument);
      flatList.push({
        argument: thesis.argument,
        argument_en: thesis.argument_en || thesis.argument,
        stance: thesis.stance,
        confidence: thesis.confidence,
        role: "thesis",
        depth: 0,
        chainId: chain.chain_id,
        enrichedData: enrichedData || null,
        isOrphan: false,
      });

      // Add sub-arguments
      if (thesis.sub_arguments) {
        thesis.sub_arguments.forEach((subArg) => {
          flatList.push({
            argument: subArg.argument,
            argument_en: subArg.argument_en || subArg.argument,
            stance: subArg.stance,
            confidence: subArg.confidence,
            role: "sub_argument",
            depth: 1,
            chainId: chain.chain_id,
            enrichedData: null,
            isOrphan: false,
          });

          // Add evidence for this sub-argument
          if (subArg.evidence) {
            subArg.evidence.forEach((ev) => {
              flatList.push({
                argument: ev.argument,
                argument_en: ev.argument_en || ev.argument,
                stance: ev.stance,
                confidence: ev.confidence,
                role: "evidence",
                depth: 2,
                chainId: chain.chain_id,
                enrichedData: null,
                isOrphan: false,
              });
            });
          }
        });
      }

      // Add counter-arguments
      if (thesis.counter_arguments) {
        thesis.counter_arguments.forEach((counterArg) => {
          flatList.push({
            argument: counterArg.argument,
            argument_en: counterArg.argument_en || counterArg.argument,
            stance: counterArg.stance,
            confidence: counterArg.confidence,
            role: "counter_argument",
            depth: 1,
            chainId: chain.chain_id,
            enrichedData: null,
            isOrphan: false,
          });

          // Add evidence for counter-arguments
          if (counterArg.evidence) {
            counterArg.evidence.forEach((ev) => {
              flatList.push({
                argument: ev.argument,
                argument_en: ev.argument_en || ev.argument,
                stance: ev.stance,
                confidence: ev.confidence,
                role: "evidence",
                depth: 2,
                chainId: chain.chain_id,
                enrichedData: null,
                isOrphan: false,
              });
            });
          }
        });
      }
    });
  }

  // Handle orphan arguments (backward compatibility for old cached data)
  // Note: With updated backend, orphan_arguments should be empty (converted to chains)
  if (
    argumentStructure.orphan_arguments &&
    argumentStructure.orphan_arguments.length > 0
  ) {
    console.warn(
      "[FlattenTree] Found orphan_arguments in old cache, adding to flat list"
    );
    argumentStructure.orphan_arguments.forEach((orphan, index) => {
      const enrichedData = enrichedMap.get(orphan.argument);
      flatList.push({
        argument: orphan.argument,
        argument_en: orphan.argument_en || orphan.argument,
        stance: orphan.stance,
        confidence: orphan.confidence,
        role: "thesis", // Treat orphans as standalone thesis
        depth: 0,
        chainId: (argumentStructure.reasoning_chains?.length || 0) + index,
        enrichedData: enrichedData || null,
        isOrphan: true,
      });
    });
  }

  return flatList;
}

/**
 * Get role icon and label
 */
function getRoleDisplay(role) {
  const roleMap = {
    thesis: { icon: "💡", label: "Thèse", class: "role-thesis" },
    sub_argument: { icon: "↳", label: "Support", class: "role-sub" },
    evidence: { icon: "📌", label: "Preuve", class: "role-evidence" },
    counter_argument: { icon: "⚠️", label: "Contre", class: "role-counter" },
    orphan: { icon: "🔸", label: "Standalone", class: "role-orphan" },
  };
  return roleMap[role] || { icon: "•", label: role, class: "role-other" };
}

/**
 * Crée le tableau récapitulatif
 */
function renderSummaryTable(data) {
  console.log("[SummaryTable] Data structure:", {
    hasArgumentStructure: !!data.argument_structure,
    hasEnrichedThesis: !!data.enriched_thesis_arguments,
    argumentStructure: data.argument_structure,
    enrichedCount: data.enriched_thesis_arguments?.length || 0,
  });

  const flatArguments = flattenArgumentTree(
    data.argument_structure,
    data.enriched_thesis_arguments
  );

  console.log(
    "[SummaryTable] Flattened arguments:",
    flatArguments.length,
    flatArguments
  );

  if (flatArguments.length === 0) {
    console.warn("[SummaryTable] No flattened arguments to display");
    return "";
  }

  const rows = flatArguments
    .map((arg, index) => {
      const roleDisplay = getRoleDisplay(arg.role);
      const indentStyle = `padding-left: ${arg.depth * 20 + 8}px;`;

      // Thesis arguments can have reliability scores if they have enrichedData
      let reliabilityHtml = "";
      let sourcesHtml = "";
      const isClickable = arg.role === "thesis" && arg.enrichedData;

      if (isClickable) {
        const usedUrls = collectUsedUrls(arg.enrichedData.analysis);
        const reliability = formatReliabilityScore(
          arg.enrichedData.reliability_score,
          usedUrls.size > 0
        );
        reliabilityHtml = `<span class="mini-badge ${reliability.class}">${reliability.display}</span>`;
        sourcesHtml = generateSourceIcons(arg.enrichedData.sources, index);
      } else {
        reliabilityHtml = '<span style="opacity: 0.3;">—</span>';
        sourcesHtml = '<span style="opacity: 0.3;">—</span>';
      }

      return `
        <tr class="summary-row ${isClickable ? "clickable" : ""}"
            data-arg-index="${index}"
            data-role="${arg.role}"
            data-has-enriched="${isClickable ? "true" : "false"}"
            style="${isClickable ? "cursor:pointer" : ""}">
          <td style="text-align: center;">
            <span class="role-badge ${roleDisplay.class}" title="${
        roleDisplay.label
      }">
              ${roleDisplay.icon}
            </span>
          </td>
          <td>${reliabilityHtml}</td>
          <td class="summary-arg-text" style="${indentStyle}">${
        arg.argument
      }</td>
          <td class="summary-sources">${sourcesHtml}</td>
        </tr>
      `;
    })
    .join("");

  console.log("[SummaryTable] Generated", flatArguments.length, "rows");

  return `
    <div class="summary-table-container">
      <table class="summary-table" id="summaryTable">
        <thead>
          <tr>
            <th width="8%">Type</th>
            <th width="12%">Note</th>
            <th width="60%">Argument</th>
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
 * Render a sub-argument or evidence node
 */
function renderSubNode(node, depth = 1, type = "sub") {
  const iconMap = {
    sub: "↳",
    evidence: "📌",
    counter: "⚠️",
  };
  const icon = iconMap[type] || "•";
  const indent = depth * 20;

  let html = `
    <div class="arg-tree-node" style="margin-left: ${indent}px; margin-top: 8px;">
      <div class="node-content">
        <span class="node-icon">${icon}</span>
        <span class="node-text">${node.argument}</span>
      </div>
  `;

  // Render evidence if this is a sub-argument
  if (type === "sub" && node.evidence && node.evidence.length > 0) {
    node.evidence.forEach((ev) => {
      html += renderSubNode(ev, depth + 1, "evidence");
    });
  }

  html += `</div>`;
  return html;
}

/**
 * Crée une carte d'argument basée sur une reasoning chain
 */
function createArgumentCard(chain, enrichedData, index) {
  const thesis = chain.thesis;

  // Build structure HTML (sub-arguments and evidence)
  let structureHtml = "";

  // Add sub-arguments
  if (thesis.sub_arguments && thesis.sub_arguments.length > 0) {
    structureHtml +=
      '<div class="arg-structure-section"><div class="section-title" style="color:#2e7d32; margin-top:12px;">Arguments supports</div>';
    thesis.sub_arguments.forEach((subArg) => {
      structureHtml += renderSubNode(subArg, 1, "sub");
    });
    structureHtml += "</div>";
  }

  // Add counter-arguments
  if (thesis.counter_arguments && thesis.counter_arguments.length > 0) {
    structureHtml +=
      '<div class="arg-structure-section"><div class="section-title" style="color:#c62828; margin-top:12px;">Arguments contraires</div>';
    thesis.counter_arguments.forEach((counterArg) => {
      structureHtml += renderSubNode(counterArg, 1, "counter");
    });
    structureHtml += "</div>";
  }

  // Add research analysis if available
  let researchHtml = "";
  if (enrichedData) {
    const sourceMap = createSourceMap(enrichedData.sources);
    const usedUrls = collectUsedUrls(enrichedData.analysis);

    const prosHtml = enrichedData.analysis?.pros?.length
      ? `<div class="pros-box">
           <div class="section-title" style="color:#276749; margin-top:12px;">✅ Points qui corroborent (recherche)</div>
           <ul class="pros-list">${enrichedData.analysis.pros
             .map((p) => renderPoint(p, sourceMap))
             .join("")}</ul>
         </div>`
      : "";

    const consHtml = enrichedData.analysis?.cons?.length
      ? `<div class="cons-box">
           <div class="section-title" style="color:#9b2c2c; margin-top:12px;">❌ Points qui contredisent (recherche)</div>
           <ul class="cons-list">${enrichedData.analysis.cons
             .map((c) => renderPoint(c, sourceMap))
             .join("")}</ul>
         </div>`
      : "";

    if (prosHtml || consHtml) {
      researchHtml = `<div class="research-section" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0;">${prosHtml}${consHtml}</div>`;
    }
  }

  // Calculate reliability score
  let reliability = { class: "neutral", label: "Non évalué", percent: "—" };
  if (enrichedData && enrichedData.reliability_score !== undefined) {
    const usedUrls = collectUsedUrls(enrichedData.analysis);
    reliability = formatReliabilityScore(
      enrichedData.reliability_score,
      usedUrls.size > 0
    );
  }

  const card = document.createElement("div");
  card.className = "arg-card collapsed";
  card.id = `arg-${index}`;
  card.innerHTML = `
    <div class="arg-header" style="cursor: pointer;">
      <div class="arg-title-container">
        <span class="expand-arrow">▼</span>
        <div class="arg-title">💡 "${thesis.argument}"</div>
      </div>
      <div class="reliability-container">
        <span class="reliability-badge ${reliability.class}">${
    reliability.label
  }</span>
        <span class="reliability-score">${reliability.percent}</span>
      </div>
    </div>
    <div class="arg-details">
      ${
        structureHtml ||
        '<div class="no-structure-msg" style="opacity: 0.6; font-style: italic;">Aucun argument support ou contre trouvé.</div>'
      }
      ${researchHtml}
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
function attachSummaryTableHandlers(
  flattenedArgs,
  reasoningChains,
  enrichedMap
) {
  const summaryTable = document.getElementById("summaryTable");
  if (!summaryTable) return;

  // Create a map from flattened table index to reasoning chain index
  const tableToChainMap = new Map();
  let chainIndex = 0;

  flattenedArgs.forEach((arg, flatIndex) => {
    if (arg.role === "thesis") {
      // This thesis corresponds to a reasoning chain
      tableToChainMap.set(flatIndex, chainIndex);
      chainIndex++;
    }
  });

  summaryTable.addEventListener("click", (e) => {
    const trigger = e.target.closest(".sources-trigger");
    if (trigger) {
      e.stopPropagation();
      const flatIndex = parseInt(trigger.dataset.argIndex);
      const chainIdx = tableToChainMap.get(flatIndex);
      if (chainIdx !== undefined && reasoningChains[chainIdx]) {
        const chain = reasoningChains[chainIdx];
        const enrichedData = enrichedMap.get(chain.thesis.argument);
        if (enrichedData) {
          openSourcesModal(enrichedData, e);
        }
      }
      return;
    }

    const row = e.target.closest(".summary-row");
    if (row && row.dataset.role === "thesis") {
      const flatIndex = parseInt(row.dataset.argIndex);
      const chainIdx = tableToChainMap.get(flatIndex);
      if (chainIdx !== undefined) {
        const targetEl = document.getElementById(`arg-${chainIdx}`);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
          // Highlight the target card briefly
          targetEl.style.boxShadow = "0 0 20px rgba(59, 130, 246, 0.5)";
          setTimeout(() => {
            targetEl.style.boxShadow = "";
          }, 2000);
        }
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

  // Get counts from argument structure
  const totalArgs = data.argument_structure?.metadata?.total_arguments || 0;
  const thesisCount = data.argument_structure?.reasoning_chains?.length || 0;
  const enrichedThesisArgs = data.enriched_thesis_arguments || [];

  // Flatten the argument tree for table display
  const flattenedArgs = flattenArgumentTree(
    data.argument_structure,
    enrichedThesisArgs
  );

  console.log("[Results] Flattened args count:", flattenedArgs.length);
  console.log("[Results] Enriched thesis count:", enrichedThesisArgs.length);

  const summaryTableHtml = renderSummaryTable(data);

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
            ${totalArgs} arguments (${thesisCount} ${
      thesisCount > 1 ? "thèses" : "thèse"
    })
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

  // Create a map of thesis arguments to their enriched data
  const enrichedMap = new Map();
  if (enrichedThesisArgs) {
    enrichedThesisArgs.forEach((enriched) => {
      enrichedMap.set(enriched.argument, enriched);
    });
  }

  // Get reasoning chains
  const reasoningChains = data.argument_structure?.reasoning_chains || [];

  // Handle orphan arguments (backward compatibility for old cached data)
  const orphanArguments = data.argument_structure?.orphan_arguments || [];
  if (orphanArguments.length > 0) {
    console.warn(
      "[Results] Found",
      orphanArguments.length,
      "orphan arguments (old cache) - converting to chains"
    );

    // Convert orphans to standalone chains
    orphanArguments.forEach((orphan) => {
      reasoningChains.push({
        chain_id: reasoningChains.length,
        total_arguments: 1,
        thesis: {
          argument: orphan.argument,
          argument_en: orphan.argument_en || orphan.argument,
          stance: orphan.stance || "affirmatif",
          confidence: orphan.confidence || 1.0,
          sub_arguments: [],
          counter_arguments: [],
        },
      });
    });
  }

  // Event delegation pour le tableau
  attachSummaryTableHandlers(flattenedArgs, reasoningChains, enrichedMap);

  // 2. Liste des arguments détaillés (show all reasoning chains from argument_structure)
  const argumentsList = getElement("argumentsList");
  if (argumentsList && reasoningChains.length > 0) {
    argumentsList.innerHTML = "";

    // Render each reasoning chain
    reasoningChains.forEach((chain, index) => {
      const enrichedData = enrichedMap.get(chain.thesis.argument);
      const card = createArgumentCard(chain, enrichedData, index);
      argumentsList.appendChild(card);
    });

    console.log(
      "[Results] Rendered",
      reasoningChains.length,
      "reasoning chains (including",
      orphanArguments.length,
      "orphans)"
    );
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
