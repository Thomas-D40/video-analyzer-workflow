/**
 * Constants - Configurations centralisées
 */

// Mode configurations
export const MODES = {
  SIMPLE: "simple",
  MEDIUM: "medium",
  HARD: "hard",
};

export const MODE_HIERARCHY = [MODES.HARD, MODES.MEDIUM, MODES.SIMPLE];

export const MODE_LABELS = {
  [MODES.SIMPLE]: "Rapide",
  [MODES.MEDIUM]: "Équilibré",
  [MODES.HARD]: "Approfondi",
};

export const MODE_COSTS = {
  [MODES.SIMPLE]: "~0.01€",
  [MODES.MEDIUM]: "~0.05€",
  [MODES.HARD]: "~0.10€",
};

export const MODE_DESCRIPTIONS = {
  [MODES.SIMPLE]: "⚡ Rapide - Basé sur les abstracts uniquement",
  [MODES.MEDIUM]: "⚖️ Équilibré - 3 textes complets analysés",
  [MODES.HARD]: "🔬 Approfondi - 6 textes complets analysés",
};

export const MODE_BADGE_CLASSES = {
  [MODES.SIMPLE]: "mode-badge-simple",
  [MODES.MEDIUM]: "mode-badge-medium",
  [MODES.HARD]: "mode-badge-hard",
};

export const ALL_MODE_CONFIGS = [
  {
    mode: MODES.SIMPLE,
    desc: MODE_DESCRIPTIONS[MODES.SIMPLE],
    cost: MODE_COSTS[MODES.SIMPLE],
  },
  {
    mode: MODES.MEDIUM,
    desc: MODE_DESCRIPTIONS[MODES.MEDIUM],
    cost: MODE_COSTS[MODES.MEDIUM],
  },
  {
    mode: MODES.HARD,
    desc: MODE_DESCRIPTIONS[MODES.HARD],
    cost: MODE_COSTS[MODES.HARD],
  },
];

// Reliability thresholds
export const RELIABILITY = {
  HIGH_THRESHOLD: 0.8,
  MEDIUM_THRESHOLD: 0.5,
  CLASSES: {
    HIGH: "reliability-high",
    MEDIUM: "reliability-medium",
    LOW: "reliability-low",
    NONE: "reliability-none",
  },
  LABELS: {
    HIGH: "Fiable",
    MEDIUM: "Discutable",
    LOW: "Douteux",
    NONE: "Non vérifié",
  },
};

// Source types
export const SOURCE_TYPES = {
  SCIENTIFIC: "scientific",
  MEDICAL: "medical",
  STATISTICAL: "statistical",
};

export const SOURCE_ICONS = {
  [SOURCE_TYPES.SCIENTIFIC]: "🔬",
  [SOURCE_TYPES.MEDICAL]: "⚕️",
  [SOURCE_TYPES.STATISTICAL]: "📊",
};

// UI timeouts
export const TIMEOUTS = {
  STATUS_MESSAGE: 3000,
  COLLAPSE_ANIMATION: 400,
};

// Date format options
export const DATE_FORMAT_OPTIONS = {
  FULL: {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  },
  SHORT: {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  },
};
