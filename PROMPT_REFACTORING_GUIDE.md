# Prompt Refactoring Guide

This guide documents the **hybrid approach** for organizing LLM prompts in agent modules. This pattern was established during the refactoring of `app/agents/extraction/arguments.py` and should be applied to all other agent files.

## Why Hybrid Approach?

After evaluating full separation (prompts in separate files) vs. hybrid (prompts as module constants), we chose the **hybrid approach** because:

### Advantages ✅
- **Tight coupling maintained**: Prompts stay with the logic that uses them
- **Context preserved**: Easy to see how prompts are parsed and validated
- **Single point of change**: Modify prompt and parsing logic together
- **Easier debugging**: Stack traces and errors reference a single file
- **No synchronization issues**: No risk of prompt/logic version mismatch
- **Industry standard**: Most production LLM systems (LangChain, LlamaIndex) use this pattern

### Avoiding Full Separation ❌
- Complex prompts need complex parsing → tight coupling is natural
- Separate files create synchronization burden
- Harder to maintain context when reviewing changes
- Stack traces become harder to follow

## Pattern Structure

Every agent module following this pattern has three sections:

```python
"""
Module docstring explaining the agent's purpose
"""
# Imports
from typing import ...
from ...constants import ...
from ...prompts import ...  # Only if using shared components

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = """..."""
USER_PROMPT_TEMPLATE = """..."""
VALIDATION_KEYWORDS = {...}
# ... other prompt-related constants

# ============================================================================
# LOGIC
# ============================================================================

def agent_function(...):
    """Function implementing the agent logic"""
    # Use constants from above
    prompt = SYSTEM_PROMPT.format(...)
    # ... rest of logic
```

## Before/After Example

### ❌ Before (Inline Prompts)

```python
def extract_arguments(transcript_text: str) -> List[Dict]:
    # ... setup code ...

    if language == "fr":
        system_prompt = """You are an expert...
        Long multi-line prompt here...
        ... (100+ lines)
        """
    else:
        system_prompt = """You are an expert...
        Different long prompt...
        ... (100+ lines)
        """

    user_prompt = f"Analyze this: {transcript_text}"

    response = client.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[...]
    )

    # ... validation logic with hardcoded keywords ...
    if any(word in text for word in ["peut", "maybe", "could"]):
        stance = "conditionnel"
```

**Problems:**
- Prompts buried in middle of function (lines 50-150)
- Configuration values hardcoded (model, temperature)
- Validation keywords hardcoded
- Hard to see overall structure

### ✅ After (Hybrid Pattern)

```python
from ...constants import (
    LLM_TEMP_ARGUMENT_EXTRACTION,
    TRANSCRIPT_MIN_LENGTH,
)

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT_FR = """You are an expert...
Long multi-line prompt here...
... (100+ lines)
"""

SYSTEM_PROMPT_EN = """You are an expert...
Different long prompt...
... (100+ lines)
"""

USER_PROMPT_TEMPLATE = "Analyze this: {transcript}"

STANCE_VALIDATION_KEYWORDS = {
    "conditionnel": ["peut", "maybe", "could", ...]
}

# ============================================================================
# LOGIC
# ============================================================================

def extract_arguments(transcript_text: str) -> List[Dict]:
    """Extracts arguments from transcript."""
    if len(transcript_text) < TRANSCRIPT_MIN_LENGTH:
        return []

    language = detect_language(transcript_text)

    # Select prompt based on language
    system_prompt = SYSTEM_PROMPT_FR if language == "fr" else SYSTEM_PROMPT_EN
    user_prompt = USER_PROMPT_TEMPLATE.format(transcript=transcript_text)

    response = client.create(
        model=settings.openai_smart_model,
        temperature=LLM_TEMP_ARGUMENT_EXTRACTION,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    # Validate stance using keywords
    if any(word in text for word in STANCE_VALIDATION_KEYWORDS["conditionnel"]):
        stance = "conditionnel"
```

**Benefits:**
- Prompts clearly visible at top of file
- Configuration centralized via constants
- Logic is clean and focused on orchestration
- Easy to modify prompts without touching logic

## Using Shared Components

The `/app/prompts/common.py` module provides reusable prompt components:

### Available Components

```python
from app.prompts import (
    # JSON Output Instructions
    JSON_OUTPUT_STRICT,          # "Return ONLY valid JSON..."
    JSON_OUTPUT_RELAXED,         # Less strict version

    # Language Context
    LANGUAGE_FRENCH_CONTEXT,     # "The video is in French..."
    LANGUAGE_ENGLISH_CONTEXT,    # "The video is in English..."

    # Analysis Principles
    OBJECTIVITY_INSTRUCTION,     # "Remain strictly neutral..."
    COMPREHENSIVENESS_INSTRUCTION, # "Aim for thorough coverage..."

    # Evidence Handling
    CITATION_INSTRUCTION,        # "Every claim must reference..."
    SOURCE_QUALITY_INSTRUCTION,  # "Consider reliability..."

    # Exclusions
    EXCLUSION_CRITERIA_ARGUMENTS, # "What to exclude: anecdotes..."

    # Stance
    STANCE_DEFINITIONS,          # "affirmatif vs conditionnel"

    # Schemas
    SCHEMA_ARGUMENT,             # JSON schema for arguments
    SCHEMA_SOURCE_REFERENCE,     # JSON schema for sources
    SCHEMA_PROS_CONS,           # JSON schema for pros/cons
)
```

### When to Use Shared Components

✅ **Use shared components when:**
- The instruction is truly generic (objectivity, JSON format)
- Multiple agents need identical instructions
- The component is self-contained and doesn't need context

❌ **Don't use shared components when:**
- The instruction is agent-specific
- You need to customize the wording for context
- The component would need heavy customization

### Example: Mixing Shared and Specific

```python
from app.prompts import JSON_OUTPUT_STRICT, OBJECTIVITY_INSTRUCTION

# ============================================================================
# PROMPTS
# ============================================================================

# Agent-specific prompt that incorporates shared components
SYSTEM_PROMPT = f"""You are a pros/cons analysis agent.

{OBJECTIVITY_INSTRUCTION}

**TASK:**
Analyze the following research sources and identify points that support
or contradict the given argument.

**SPECIFIC INSTRUCTIONS:**
1. Focus on factual evidence, not opinions
2. Cite sources with direct quotes
3. Classify each point as "pro" or "con"

{JSON_OUTPUT_STRICT}
"""

# Rest of module...
```

## Step-by-Step Refactoring Guide

Follow these steps to refactor an agent module:

### 1. Identify Prompts and Configuration

Read through the agent file and identify:
- [ ] System prompts (static instructions)
- [ ] User prompt templates (with placeholders)
- [ ] Hardcoded model names
- [ ] Hardcoded temperatures
- [ ] Hardcoded timeouts
- [ ] Hardcoded thresholds/limits
- [ ] Validation keywords/patterns

### 2. Import Constants

Add imports from `app.constants`:

```python
from ...constants import (
    LLM_TEMP_YOUR_AGENT,          # Temperature setting
    OPENAI_MODEL_FAST,            # or OPENAI_MODEL_SMART
    DEFAULT_TIMEOUT_HTTPX,        # Timeout setting
    YOUR_SPECIFIC_CONSTANT,       # Any agent-specific constant
)
```

### 3. Create Prompt Section

Add a new section at the top of the file (after imports):

```python
# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = """..."""
# or multiple prompts if needed:
SYSTEM_PROMPT_FR = """..."""
SYSTEM_PROMPT_EN = """..."""

USER_PROMPT_TEMPLATE = """..."""

VALIDATION_PATTERNS = {...}
```

### 4. Extract Inline Prompts

Move all inline prompts to the PROMPTS section:

```python
# Before
def analyze(text):
    prompt = f"""Analyze this: {text}"""

# After
USER_PROMPT_TEMPLATE = "Analyze this: {text}"

def analyze(text):
    prompt = USER_PROMPT_TEMPLATE.format(text=text)
```

### 5. Add Logic Section Header

Add a clear separator before the first function:

```python
# ============================================================================
# LOGIC
# ============================================================================

def your_agent_function(...):
```

### 6. Replace Hardcoded Values

Replace all hardcoded configuration with constants:

```python
# Before
response = client.create(
    model="gpt-4o-mini",
    temperature=0.3,
    timeout=60.0
)

# After
response = client.create(
    model=settings.openai_model,
    temperature=LLM_TEMP_YOUR_AGENT,
    timeout=DEFAULT_TIMEOUT_HTTPX
)
```

### 7. Consider Shared Components

Review `app/prompts/common.py` and incorporate shared components where appropriate:

```python
from app.prompts import JSON_OUTPUT_STRICT, OBJECTIVITY_INSTRUCTION

SYSTEM_PROMPT = f"""Your specific instructions...

{OBJECTIVITY_INSTRUCTION}

More specific instructions...

{JSON_OUTPUT_STRICT}
"""
```

### 8. Test

Run tests to ensure refactoring didn't break functionality:

```bash
# Test the specific agent
python -m pytest tests/test_your_agent.py -v

# Or test the full workflow
python test_improved_search.py
```

## Agents to Refactor

The following agent files should be refactored following this pattern:

### Analysis Agents
- [ ] `app/agents/analysis/pros_cons.py`
- [ ] `app/agents/analysis/aggregate.py`

### Orchestration Agents
- [ ] `app/agents/orchestration/topic_classifier.py`
- [ ] `app/agents/orchestration/query_generator.py`

### Research Agents (if applicable)
Most research agents are API-based and may not have large prompts, but check:
- [ ] `app/agents/enrichment/screening.py` (uses LLM for source screening)
- [ ] Any other agent with embedded prompts

## Common Patterns

### Multi-Language Prompts

```python
SYSTEM_PROMPT_FR = """French instructions..."""
SYSTEM_PROMPT_EN = """English instructions..."""

def agent_function(text, language):
    prompt = SYSTEM_PROMPT_FR if language == "fr" else SYSTEM_PROMPT_EN
```

### Parameterized Prompts

```python
USER_PROMPT_TEMPLATE = """Analyze argument: {argument}

Using these sources:
{sources}

Return JSON with pros and cons."""

def agent_function(argument, sources):
    prompt = USER_PROMPT_TEMPLATE.format(
        argument=argument,
        sources="\n".join(sources)
    )
```

### Conditional Prompts

```python
PROMPT_ABSTRACT_ONLY = """Analyze this abstract: {text}"""
PROMPT_FULL_TEXT = """Analyze this full text: {text}

Consider methodology, results, and conclusions."""

def agent_function(text, has_full_text):
    template = PROMPT_FULL_TEXT if has_full_text else PROMPT_ABSTRACT_ONLY
    prompt = template.format(text=text)
```

## Best Practices

### ✅ DO

- **Extract all prompts** to module-level constants
- **Use constants** from `app.constants` for configuration
- **Name prompts clearly**: `SYSTEM_PROMPT_FR`, not `PROMPT1`
- **Add comments** explaining prompt purpose if not obvious
- **Use f-strings** to incorporate shared components
- **Test after refactoring** to ensure behavior unchanged
- **Group related constants**: All prompts together, all validation patterns together

### ❌ DON'T

- **Don't over-modularize**: Keep prompts in the same file as logic
- **Don't create separate files**: Resist temptation to put prompts in `prompts/agent_name.py`
- **Don't hardcode values**: Always use constants for models, temperatures, thresholds
- **Don't force shared components**: Only use them when they truly fit
- **Don't break working code**: Refactor incrementally and test frequently

## Example: Complete Refactored Agent

See `app/agents/extraction/arguments.py` for the reference implementation of this pattern.

Key features demonstrated:
- Clear separation of prompts and logic
- Use of constants from `app.constants`
- Language-specific prompts
- Validation keyword constants
- Template-based user prompts
- Clean, readable logic section

## Questions?

If you're unsure about how to apply this pattern to a specific agent, refer to the reference implementation in `arguments.py` or review this guide.
