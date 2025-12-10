/**
 * Utils - Source management utilities
 */

import { SOURCE_ICONS, SOURCE_TYPES } from "../constants.js";

/**
 * Collecte toutes les URLs utilisées dans l'analyse
 */
export function collectUsedUrls(analysis) {
  const usedUrls = new Set();

  if (analysis?.pros) {
    analysis.pros.forEach((p) => {
      if (typeof p === "object" && p.source) {
        usedUrls.add(p.source);
      }
    });
  }

  if (analysis?.cons) {
    analysis.cons.forEach((c) => {
      if (typeof c === "object" && c.source) {
        usedUrls.add(c.source);
      }
    });
  }

  return usedUrls;
}

/**
 * Crée une map des sources par URL
 */
export function createSourceMap(sources) {
  const sourceMap = new Map();
  const allSources = [
    ...(sources?.scientific || []),
    ...(sources?.medical || []),
    ...(sources?.statistical || []),
  ];
  allSources.forEach((s) => sourceMap.set(s.url, s));
  return sourceMap;
}

/**
 * Compte les sources par type
 */
export function countSourcesByType(sources) {
  const scientific = sources?.scientific?.length || 0;
  const medical = sources?.medical?.length || 0;
  const statistical = sources?.statistical?.length || 0;

  return {
    scientific,
    medical,
    statistical,
    total: scientific + medical + statistical,
  };
}

/**
 * Génère les icônes de sources pour l'affichage
 */
export function generateSourceIcons(sources, argIndex = null) {
  const counts = countSourcesByType(sources);

  if (counts.total === 0) {
    return '<span style="color:#cbd5e0">∅</span>';
  }

  const iconsHtml = [];

  if (counts.scientific > 0) {
    iconsHtml.push(
      `<span title="${counts.scientific} sources scientifiques">${
        SOURCE_ICONS[SOURCE_TYPES.SCIENTIFIC]
      }${counts.scientific}</span><br>`
    );
  }

  if (counts.medical > 0) {
    iconsHtml.push(
      `<span title="${counts.medical} sources médicales">${
        SOURCE_ICONS[SOURCE_TYPES.MEDICAL]
      }${counts.medical}</span><br>`
    );
  }

  if (counts.statistical > 0) {
    iconsHtml.push(
      `<span title="${counts.statistical} sources statistiques">${
        SOURCE_ICONS[SOURCE_TYPES.STATISTICAL]
      }${counts.statistical}</span><br>`
    );
  }

  const content = iconsHtml.join(" ");

  if (argIndex !== null) {
    return `<div class="sources-trigger" data-arg-index="${argIndex}">${content}</div>`;
  }

  return content;
}

/**
 * Obtient le titre d'une source
 */
export function getSourceTitle(url, sourceData = null) {
  if (sourceData?.title) {
    return sourceData.title;
  }

  try {
    return new URL(url).hostname;
  } catch (e) {
    return url.length > 30 ? url.substring(0, 30) + "..." : url;
  }
}

/**
 * Obtient l'icône d'une source basée sur le nom du service
 */
export function getSourceIcon(source) {
  const sourceName = source?.source?.toLowerCase() || "";

  // Medical sources
  if (sourceName.includes("pubmed") || sourceName.includes("europe")) {
    return SOURCE_ICONS[SOURCE_TYPES.MEDICAL];
  }

  // Statistical sources
  if (sourceName.includes("oecd") || sourceName.includes("world bank")) {
    return SOURCE_ICONS[SOURCE_TYPES.STATISTICAL];
  }

  // Scientific sources (arxiv, semantic scholar, crossref, core, doaj)
  return SOURCE_ICONS[SOURCE_TYPES.SCIENTIFIC];
}
