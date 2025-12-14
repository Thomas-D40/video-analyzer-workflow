# Argument Extraction Pipeline

Complete 7-step extraction pipeline with hierarchical argument structure.

---

## Architecture

```
app/agents/extraction/
├── arguments.py                   # Pipeline orchestrator
├── constants_extraction.py        # Prompts & constants
├── segmentation.py                # Step 1: Break into chunks
├── local_extractor.py             # Step 2: Extract per segment
├── consolidator.py                # Step 3: Deduplicate
├── validators.py                  # Step 4: Validate quality
├── translator.py                  # Step 5: Translate to English
├── hierarchy.py                   # Step 6: Build structure
└── tree_builder.py                # Step 7: Create nested tree
```

---

## Pipeline Steps

### 1. Segmentation
- Breaks transcript into 2000-char segments with 200-char overlap
- Preserves context across boundaries
- Handles long videos without degradation

### 2. Local Extraction
- Uses GPT-4o to extract arguments from each segment
- Extracts in source language (no translation yet)
- Applies explanatory argument definition
- Returns: `{argument, stance, segment_id, source_language}`

### 3. Consolidation
- Merges arguments from all segments
- Uses OpenAI embeddings for semantic deduplication
- Cosine similarity threshold: 0.85
- Keeps most complete version of duplicates

### 4. Validation (Updated)
**Criteria** - Accepts arguments meeting **AT LEAST ONE**:
- Causal/logical relationship (WHY/HOW something happens)
- Mechanistic explanation (describes process/reasoning)
- Substantive claim (significant factual/theoretical assertion)

**Accepts**:
- ✅ Causal claims: "X causes Y because..."
- ✅ Mechanisms: "The process works by..."
- ✅ Scientific claims: "Coffee contains polyphenols that inhibit..."
- ✅ Theoretical assertions: "Dark matter affects galaxy rotation"
- ✅ Hypotheses: "This might occur due to..."

**Rejects**:
- ❌ Pure descriptions: "The sky is blue"
- ❌ Simple narration: "Then he went to the store"
- ❌ Vague opinions: "I think it's interesting"
- ❌ Basic statistics without context: "50% of people..."

**Implementation**:
- Uses GPT-4o-mini for efficiency
- Provides detailed validation reasons
- Fail-open strategy (accepts on API errors)

### 5. Translation
- Separate step after validation (prevents semantic drift)
- Uses GPT-4o-mini with low temperature (0.1)
- Preserves causal/mechanistic meaning
- Adds `argument_en` field

### 6. Hierarchy Building
- Classifies each argument by role: thesis | sub_argument | evidence | counter_argument
- Identifies parent-child relationships
- Adds `role` and `parent_id` fields
- Uses GPT-4o-mini for classification

### 7. Tree Building
- Converts flat list with parent_id to nested structure
- Creates ReasoningChains: thesis → sub_arguments → evidence
- Returns ArgumentStructure with reasoning_chains array
- Preserves complete argumentative flow

---

## Output Structure

### Hierarchical ArgumentStructure
```json
{
  "reasoning_chains": [
    {
      "chain_id": 0,
      "total_arguments": 5,
      "thesis": {
        "argument": "Le café réduit les risques de cancer du foie",
        "argument_en": "Coffee reduces liver cancer risk",
        "stance": "affirmatif",
        "confidence": 0.9,
        "sub_arguments": [
          {
            "argument": "Les polyphénols ont un effet antioxydant",
            "argument_en": "Polyphenols have antioxidant effect",
            "stance": "affirmatif",
            "confidence": 0.85,
            "evidence": [
              {
                "argument": "Étude de Smith et al. 2023 montre...",
                "argument_en": "Smith et al. 2023 study shows...",
                "stance": "affirmatif",
                "confidence": 0.8,
                "segment_id": 2
              }
            ]
          }
        ],
        "counter_arguments": []
      }
    }
  ],
  "metadata": {
    "total_chains": 3,
    "total_arguments": 15
  }
}
```

---

## Benefits

### Quality
- **Selective extraction**: Only explanatory arguments (causal/mechanistic/substantive)
- **Validation**: Filters trivial descriptions and pure narration
- **Relaxed criteria**: Accepts legitimate scientific claims (not overly restrictive)

### Coverage
- **Segment-based**: No blind spots in long videos
- **Deduplication**: Semantic similarity removes redundancy
- **Complete**: Captures all substantive arguments

### Structure
- **Hierarchical**: Thesis → sub-arguments → evidence
- **Relationships**: Clear parent-child connections
- **Context**: Preserves reasoning chains

### Accuracy
- **Separate translation**: No semantic drift from mixed extraction/translation
- **Source language first**: Validates before translating
- **Low temperature**: Faithful translations

---

## Configuration

All settings in `constants_extraction.py`:

```python
# Segmentation
MAX_SEGMENT_LENGTH = 2000
SEGMENT_OVERLAP = 200

# Deduplication
DEDUPLICATION_THRESHOLD = 0.85  # Cosine similarity

# Models
EXTRACTION_MODEL = "gpt-4o"           # Smart for extraction
CLASSIFICATION_MODEL = "gpt-4o-mini"  # Fast for validation/hierarchy
TRANSLATION_MODEL = "gpt-4o-mini"     # Fast for translation

# Temperatures
EXTRACTION_TEMP = 0.3
CLASSIFICATION_TEMP = 0.2
TRANSLATION_TEMP = 0.1
VALIDATION_TEMP = 0.2
```

---

## Usage

```python
from app.agents.extraction import extract_arguments

# Full pipeline (returns ArgumentStructure)
language, argument_structure = extract_arguments(
    transcript_text,
    video_id="abc123",
    enable_hierarchy=True,    # Build tree structure
    enable_validation=True    # Validate quality
)

# Access reasoning chains
for chain in argument_structure.reasoning_chains:
    thesis = chain.thesis
    print(f"Thesis: {thesis.argument_en}")
    print(f"Sub-arguments: {len(thesis.sub_arguments)}")
```

---

## Testing

```bash
# Test on sample video
python -c "
from app.agents.extraction import extract_arguments

transcript = '''
Le café est une boisson populaire. Des études montrent que le café
réduit les risques de cancer du foie par un mécanisme antioxydant.
Les polyphénols du café inhibent la prolifération cellulaire.
'''

language, structure = extract_arguments(transcript, 'test')

print(f'Language: {language}')
print(f'Chains: {structure.total_chains}')
print(f'Total arguments: {structure.total_arguments}')
"
```

---

## Validation Update (2024)

**Previous**: Required ALL three criteria (too strict)
**Current**: Requires AT LEAST ONE criterion (balanced)

This change ensures popular science videos with legitimate scientific claims are properly captured while still filtering out pure descriptions and narration.
