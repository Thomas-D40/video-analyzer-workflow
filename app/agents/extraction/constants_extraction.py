"""
Constants and prompts for argument extraction pipeline.

All prompts and definitions for the multi-stage extraction process.
"""

# ============================================================================
# DEFINITIONS (AXIS 2)
# ============================================================================

EXPLANATORY_ARGUMENT_DEFINITION = """
An explanatory argument must satisfy AT LEAST ONE of these criteria:

1. **Causal/Logical relationship**: Asserts WHY or HOW something happens/works
2. **Mechanistic explanation**: Describes the process, mechanism, or reasoning chain
3. **Substantive claim**: Makes a significant factual or theoretical assertion

IMPORTANT - Do NOT extract:
- Simple descriptions without explanation (e.g., "The sky is blue")
- Pure narrative steps (then X did Y, next we see Z)
- Rhetorical questions without assertions
- Vague opinions without reasoning (e.g., "I think it's interesting")
- Basic statistics without context (e.g., "50% of people...")

ACCEPT - These ARE valid explanatory arguments:
- Causal claims (e.g., "X causes Y because...")
- Mechanism descriptions (e.g., "The process works by...")
- Scientific claims (e.g., "Coffee contains polyphenols that inhibit...")
- Theoretical assertions (e.g., "Dark matter affects galaxy rotation")
- Explanatory hypotheses (e.g., "This might occur due to...")
"""

# ============================================================================
# SEGMENTATION CONSTANTS (AXIS 1)
# ============================================================================

MAX_SEGMENT_LENGTH = 2000  # Characters per segment
SEGMENT_OVERLAP = 200      # Character overlap between segments
MIN_SEGMENT_LENGTH = 500   # Minimum viable segment size

# ============================================================================
# EXTRACTION PROMPTS (AXIS 1 + 2)
# ============================================================================

LOCAL_EXTRACTION_SYSTEM_PROMPT = "You are a precise argument extractor that identifies only causal and mechanistic reasoning."

LOCAL_EXTRACTION_USER_PROMPT = """
{definition}

Analyze this transcript segment and extract ONLY the explanatory arguments.

**Segment:**
{segment}

**Language:** {language}

For each argument you extract:
1. Verify it meets ALL criteria in the definition above
2. Extract the core explanatory claim IN THE SOURCE LANGUAGE ({language})
3. Identify the stance:
   - "affirmatif": Presented as definitive fact
   - "conditionnel": Presented as hypothesis, possibility, or conditional

**Do NOT translate yet. Keep original language.**

{json_instruction}

**Response format:**
{{{{
  "arguments": [
    {{{{
      "argument": "The exact explanatory claim in {language}",
      "stance": "affirmatif or conditionnel"
    }}}}
  ]
}}}}
"""

# ============================================================================
# CONSOLIDATION PROMPTS (AXIS 1)
# ============================================================================

DEDUPLICATION_THRESHOLD = 0.85  # Cosine similarity threshold for duplicates

# ============================================================================
# HIERARCHY PROMPTS (AXIS 3)
# ============================================================================

ROLE_CLASSIFICATION_SYSTEM_PROMPT = "You are an expert at analyzing argumentative structure."

ROLE_CLASSIFICATION_USER_PROMPT = """
Classify the role of this argument within the overall reasoning.

**Argument:** "{argument}"

**Context (other arguments):**
{context}

**Roles:**
- **thesis**: Main claim or central assertion (top-level)
- **sub_argument**: Supporting claim that backs up a thesis
- **evidence**: Specific data, study, or fact used as support
- **counter_argument**: Opposing view the author addresses

{json_instruction}

**Response format:**
{{{{
  "role": "thesis|sub_argument|evidence|counter_argument",
  "parent_argument": "The thesis or sub-argument this supports (if applicable)",
  "confidence": 0.0-1.0
}}}}
"""

# ============================================================================
# TRANSLATION PROMPTS (AXIS 4)
# ============================================================================

TRANSLATION_SYSTEM_PROMPT = "You are a precise translator that preserves technical and argumentative meaning."

TRANSLATION_USER_PROMPT = """
Translate this argument to {target_language}.

**Critical requirements:**
1. Preserve the EXACT causal/mechanistic meaning
2. Keep technical terms accurate
3. Maintain the argumentative structure
4. Do NOT add or remove reasoning

**Original ({source_language}):**
{argument}

{json_instruction}

**Response format:**
{{{{
  "translation": "The faithful translation in {target_language}"
}}}}
"""

# ============================================================================
# VALIDATION PROMPTS (AXIS 4)
# ============================================================================

VALIDATION_SYSTEM_PROMPT = "You are an argument validator. Accept arguments that explain, assert causation, or make substantive claims. Reject only trivial descriptions or pure narration."

VALIDATION_USER_PROMPT = """
{definition}

Does this extracted text qualify as an explanatory argument according to the definition above?

**Text:** "{argument}"

Evaluate whether it meets AT LEAST ONE of these criteria:
1. Does it assert a causal/logical relationship (WHY/HOW)? (Yes/No)
2. Does it describe a mechanism/process/reasoning? (Yes/No)
3. Does it make a substantive factual or theoretical claim? (Yes/No)

**Important:** An argument is VALID if it meets ANY of these criteria.
It is INVALID only if it's purely descriptive, narrative, or trivial.

{json_instruction}

**Response format:**
{{{{
  "is_valid": true/false,
  "meets_causal_criterion": true/false,
  "meets_mechanistic_criterion": true/false,
  "meets_substantive_criterion": true/false,
  "reasoning": "Brief explanation of why it's valid or invalid"
}}}}
"""

# ============================================================================
# LLM SETTINGS
# ============================================================================

# Model selection
EXTRACTION_MODEL = "gpt-4o"           # Smart model for extraction
CLASSIFICATION_MODEL = "gpt-4o-mini"  # Fast model for classification/validation
TRANSLATION_MODEL = "gpt-4o-mini"     # Fast model for translation

# Temperature settings
EXTRACTION_TEMP = 0.3       # Low temp for consistent extraction
CLASSIFICATION_TEMP = 0.2   # Very low for classification
TRANSLATION_TEMP = 0.1      # Minimal creativity for translation
VALIDATION_TEMP = 0.2       # Low for strict validation

# Token limits
EXTRACTION_MAX_TOKENS = 2000
CLASSIFICATION_MAX_TOKENS = 500
TRANSLATION_MAX_TOKENS = 500
VALIDATION_MAX_TOKENS = 500
