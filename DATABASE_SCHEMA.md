# Database Schema Documentation

This document provides a comprehensive reference for the MongoDB database schema used in the Video Analyzer Workflow application.

## Overview

The application uses a **nested document structure** where each video has one document containing multiple analysis modes. This design allows:

- Single document per YouTube video
- Multiple analysis modes (simple, medium, hard) per video
- Independent status tracking and ratings per mode
- Efficient cache management and retrieval

## Collections

### `video_analyses`

**Database**: `video_analyzer`
**Primary Key**: `_id` (YouTube video ID)

## Document Schema

### VideoAnalysis (Root Document)

```javascript
{
  "_id": String,              // YouTube video ID (e.g., "dQw4w9WgXcQ")
  "youtube_url": String,      // Full YouTube URL
  "analyses": {               // Map of analysis modes
    "simple": AnalysisData | null,
    "medium": AnalysisData | null,
    "hard": AnalysisData | null
  }
}
```

### AnalysisData (Nested Structure)

Each entry in the `analyses` map follows this structure:

```javascript
{
  "status": String,           // "pending" | "processing" | "completed" | "failed"
  "created_at": ISODate,      // When this specific analysis was started
  "updated_at": ISODate,      // Last modification of this analysis
  "content": Object | null,   // Analysis results (see Content Structure below)
  "average_rating": Float,    // User rating average (0.0-5.0)
  "rating_count": Integer,    // Total number of ratings
  "ratings_sum": Float        // Sum of all ratings (for average calculation)
}
```

**Field Details**:

| Field            | Type     | Required | Default   | Description                               |
| ---------------- | -------- | -------- | --------- | ----------------------------------------- |
| `status`         | String   | Yes      | "pending" | Analysis status (see AnalysisStatus enum) |
| `created_at`     | DateTime | Yes      | now()     | When this analysis mode was initiated     |
| `updated_at`     | DateTime | Yes      | now()     | Last update to this specific analysis     |
| `content`        | Object   | No       | null      | Analysis results (null until completed)   |
| `average_rating` | Float    | Yes      | 0.0       | Average user rating (0.0-5.0)             |
| `rating_count`   | Integer  | Yes      | 0         | Number of user ratings submitted          |
| `ratings_sum`    | Float    | Yes      | 0.0       | Sum of all ratings (for recalculation)    |

---

## Content Structure

The `content` field contains the actual analysis results. Its structure depends on the analysis mode and workflow:

```javascript
{
  "transcript": String,              // Video transcript text
  "arguments": [                     // Extracted arguments
    {
      "argument": String,            // Argument statement
      "stance": String,              // "affirmatif" | "conditionnel"
      "sources": [                   // Research sources
        {
          "title": String,
          "authors": [String],
          "url": String,
          "date": String,
          "abstract": String,
          "access_type": String,     // "free" | "restricted" | "paid"
          "relevance_score": Float,  // 0.0-1.0
          "pros": [String],          // Supporting evidence
          "cons": [String]           // Contradicting evidence
        }
      ],
      "reliability_score": Float,    // 0.0-1.0
      "reliability_label": String    // "Très fiable" | "Fiable" | "Peu fiable" | etc.
    }
  ],
  "metadata": {
    "video_id": String,
    "analysis_mode": String,
    "processed_at": ISODate,
    "model_versions": {
      "extraction": String,
      "analysis": String
    }
  }
}
```

---

## Analysis Modes

The application supports three analysis modes with different depth levels:

| Mode     | Description            | Research Depth   | Sources per Argument |
| -------- | ---------------------- | ---------------- | -------------------- |
| `simple` | Fast analysis          | Basic sources    | 3-5                  |
| `medium` | Balanced analysis      | Multiple sources | 5-10                 |
| `hard`   | Comprehensive analysis | Deep research    | 10+                  |

**Mode Hierarchy** (for cache selection): `hard` > `medium` > `simple`

---

## Analysis Status Values

Defined in `app/constants.py` as `AnalysisStatus` enum:

| Status       | Description                     |
| ------------ | ------------------------------- |
| `pending`    | Analysis queued but not started |
| `processing` | Currently being analyzed        |
| `completed`  | Analysis finished successfully  |
| `failed`     | Analysis encountered an error   |

---

## Cache Strategy

The application uses a simple cache retrieval strategy via `get_available_analyses()`:

### Cache Logic

1. **Check if video exists**: Query database for video document
2. **Check requested mode**: See if the specific analysis mode exists and is completed
3. **Return all analyses**: If mode exists, return complete document with all three modes (simple, medium, hard)
4. **Generate if missing**: If requested mode doesn't exist, generate it and add to document

**Key Points:**

- Always returns ALL analysis modes when cache hit occurs
- No automatic cache invalidation based on age
- Frontend/extension decides which mode to display to user
- Users can see timestamps and decide themselves if analysis is too old
- Scientific sources don't become outdated quickly, so age-based invalidation is unnecessary

## User Rating System

Each analysis mode has independent ratings:

### Rating Submission

```python
await submit_rating(
    video_id="dQw4w9WgXcQ",
    analysis_mode=AnalysisMode.SIMPLE,
    rating=4.5  # 0.0-5.0
)
```

### Rating Calculation

- **Incremental Updates**: Uses MongoDB `$inc` operators
- **Atomic Operations**: Prevents race conditions
- **Average Calculation**: `average_rating = ratings_sum / rating_count`

### Rating Constraints

- **Min Rating**: 0.0 (configurable via `RATING_MIN`)
- **Max Rating**: 5.0 (configurable via `RATING_MAX`)
- **Precision**: Float (supports decimals)

## API Access

### Storage Service Functions

Located in `app/services/storage.py`:

| Function                   | Description                                                    |
| -------------------------- | -------------------------------------------------------------- |
| `save_analysis()`          | Create or update analysis for specific mode                    |
| `get_available_analyses()` | Get all analysis modes for a video (returns complete document) |
| `submit_rating()`          | Submit user rating for specific mode                           |
| `list_analyses()`          | List recent video documents (sorted by most recent analysis)   |

### Example Usage

```python
from app.services.storage import save_analysis, get_available_analyses
from app.constants import AnalysisMode

# Save a new analysis
await save_analysis(
    video_id="dQw4w9WgXcQ",
    youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    content={"arguments": [...]},
    analysis_mode=AnalysisMode.SIMPLE
)

# Get all analyses for a video (recommended approach)
all_analyses = await get_available_analyses(video_id="dQw4w9WgXcQ")
if all_analyses:
    # Returns: {"video_id": "...", "youtube_url": "...", "analyses": {...}}
    simple_analysis = all_analyses["analyses"].get("simple")
    medium_analysis = all_analyses["analyses"].get("medium")
    hard_analysis = all_analyses["analyses"].get("hard")
```
