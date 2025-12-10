/**
 * Utils - Formatting utilities
 */

import { RELIABILITY, DATE_FORMAT_OPTIONS } from "../constants.js";

/**
 * Formate une date en français
 */
export function formatDate(dateString, options = DATE_FORMAT_OPTIONS.SHORT) {
  if (!dateString) return null;

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return null;

  return date.toLocaleString("fr-FR", options);
}

/**
 * Calcule l'âge d'une date en texte
 */
export function getAgeText(dateString) {
  if (!dateString) return "Date inconnue";

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "Date inconnue";

  const now = new Date();
  const ageDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

  if (ageDays === 0) return "Aujourd'hui";
  if (ageDays === 1) return "Il y a 1 jour";
  return `Il y a ${ageDays} jours`;
}

/**
 * Retourne la classe CSS pour un score de fiabilité
 */
export function getReliabilityClass(score) {
  if (score >= RELIABILITY.HIGH_THRESHOLD) return RELIABILITY.CLASSES.HIGH;
  if (score >= RELIABILITY.MEDIUM_THRESHOLD) return RELIABILITY.CLASSES.MEDIUM;
  if (score > 0) return RELIABILITY.CLASSES.LOW;
  return RELIABILITY.CLASSES.NONE;
}

/**
 * Retourne le label pour un score de fiabilité
 */
export function getReliabilityLabel(score) {
  if (score >= RELIABILITY.HIGH_THRESHOLD) return RELIABILITY.LABELS.HIGH;
  if (score >= RELIABILITY.MEDIUM_THRESHOLD) return RELIABILITY.LABELS.MEDIUM;
  if (score > 0) return RELIABILITY.LABELS.LOW;
  return RELIABILITY.LABELS.NONE;
}

/**
 * Formate un score de fiabilité pour l'affichage
 */
export function formatReliabilityScore(score, hasUsedSources = true) {
  if (!hasUsedSources) {
    return {
      class: RELIABILITY.CLASSES.NONE,
      label: RELIABILITY.LABELS.NONE,
      display: "-",
      percent: "Pas de sources liées",
    };
  }

  return {
    class: getReliabilityClass(score),
    label: getReliabilityLabel(score),
    display: Math.round(score * 100),
    percent: `${Math.round(score * 100)}/100`,
  };
}
