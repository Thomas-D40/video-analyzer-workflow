# Smart Multi-Mode Cache Strategy

## Overview

The video analyzer now implements an **intelligent multi-mode caching system** that balances quality, recency, and user preferences when serving cached analyses.

## Problem Solved

**Before:** Simple cache lookup by video_id only
- User A analyzes video in "hard" mode → expensive, thorough
- User B requests same video in "simple" mode → creates duplicate
- User C requests same video (no mode) → which one to return?

**After:** Smart cache selection with quality hierarchy
- Multiple analyses per video (one per mode)
- Automatic upgrade to better quality when available
- Age-based invalidation
- Full transparency about cache decisions

---

## Cache Selection Strategy

### Quality Hierarchy

```
hard (quality: 3) > medium (quality: 2) > simple (quality: 1)
```

### Decision Tree

```
User requests analysis in mode X
    ↓
1. Check if exact mode X exists and is < 7 days old
   ✅ YES → Return it (exact_match)
   ❌ NO → Continue to step 2
    ↓
2. Check if BETTER mode exists (higher quality) and is < 7 days old
   ✅ YES → Return it (upgraded)
   ❌ NO → Continue to step 3
    ↓
3. Check if ANY mode exists but too old (> 7 days)
   ✅ YES → Reject, create new analysis (too_old)
   ❌ NO → Continue to step 4
    ↓
4. Check if LOWER mode exists
   ✅ YES → Reject, create new analysis (insufficient_quality)
   ❌ NO → Create new analysis (no_cache)
```

---

## Real-World Scenarios

### Scenario 1: Quality Upgrade

```json
// User A creates analysis
POST /api/analyze {
  "url": "...",
  "analysis_mode": "hard"
}
→ Creates "hard" analysis (6 full-texts)

// User B requests simple mode (2 days later)
POST /api/analyze {
  "url": "...",
  "analysis_mode": "simple"
}
→ Returns HARD analysis! (better quality available)
→ Response includes:
{
  "cache_info": {
    "reason": "upgraded",
    "message": "Using higher quality 'hard' instead of 'simple' (2 days old)",
    "selected_mode": "hard",
    "requested_mode": "simple",
    "age_days": 2,
    "available_analyses": [
      {"mode": "hard", "age_days": 2, "updated_at": "..."}
    ]
  }
}
```

**Why?** User B wanted simple (cheap) but hard (expensive) was already done by User A. Give them the better result!

### Scenario 2: Insufficient Quality

```json
// User A creates analysis
POST /api/analyze {
  "url": "...",
  "analysis_mode": "simple"
}
→ Creates "simple" analysis (abstracts only)

// User B requests hard mode (1 day later)
POST /api/analyze {
  "url": "...",
  "analysis_mode": "hard"
}
→ Creates NEW "hard" analysis (not satisfied with simple)
→ Response includes:
{
  "cache_info": null  // New analysis, not cached
}

// Now database has BOTH:
// - simple: 1 day old
// - hard: fresh
```

**Why?** User B wants thorough analysis (6 full-texts). Existing simple (abstracts only) is insufficient. Create new one.

### Scenario 3: Age-Based Invalidation

```json
// Old analysis exists (10 days ago)
Database: {
  "id": "abc",
  "analysis_mode": "hard",
  "updated_at": "2025-11-25" // 10 days old
}

// User requests analysis
POST /api/analyze {
  "url": "...",
  "analysis_mode": "simple"
}
→ Rejects old cache (> 7 days)
→ Creates NEW "simple" analysis
→ Response includes:
{
  "cache_info": null  // New analysis created
}
```

**Why?** Video content might have changed, or facts might be outdated. Refresh after 7 days.

### Scenario 4: Multiple Modes Available

```json
// Database has 3 analyses:
// - simple: 1 day old
// - medium: 3 days old
// - hard: 5 days old

// User requests medium
POST /api/analyze {
  "url": "...",
  "analysis_mode": "medium"
}
→ Returns "hard" (best available, within age limit)
→ Response includes:
{
  "cache_info": {
    "reason": "upgraded",
    "selected_mode": "hard",
    "requested_mode": "medium",
    "age_days": 5,
    "available_analyses": [
      {"mode": "simple", "age_days": 1},
      {"mode": "medium", "age_days": 3},
      {"mode": "hard", "age_days": 5}
    ]
  }
}
```

**Why?** User wanted medium but hard is available and recent. Upgrade them!

---

## Database Structure

### Composite Key: (video_id, analysis_mode)

```javascript
// MongoDB collection: analyses

// Example documents
{
  "_id": ObjectId("..."),
  "id": "dQw4w9WgXcQ",
  "analysis_mode": "simple",
  "status": "completed",
  "created_at": ISODate("2025-12-01"),
  "updated_at": ISODate("2025-12-01"),
  "content": { /* arguments with abstracts */ }
}

{
  "_id": ObjectId("..."),
  "id": "dQw4w9WgXcQ",
  "analysis_mode": "hard",
  "status": "completed",
  "created_at": ISODate("2025-12-03"),
  "updated_at": ISODate("2025-12-03"),
  "content": { /* arguments with 6 full-texts */ }
}

// Unique index ensures no duplicates
db.analyses.createIndex(
  { id: 1, analysis_mode: 1 },
  { unique: true }
)
```

---

## API Response Format

### Cache Hit Response

```json
{
  "status": "success",
  "video_id": "dQw4w9WgXcQ",
  "youtube_url": "...",
  "arguments_count": 5,
  "report_markdown": "...",
  "data": {
    "cached": true,
    "cache_info": {
      "reason": "upgraded",
      "message": "Using higher quality 'hard' instead of 'simple' (2 days old)",
      "selected_mode": "hard",
      "requested_mode": "simple",
      "age_days": 2,
      "last_updated": "2025-12-03T10:30:00",
      "available_analyses": [
        {
          "mode": "hard",
          "age_days": 2,
          "updated_at": "2025-12-03T10:30:00"
        },
        {
          "mode": "medium",
          "age_days": 5,
          "updated_at": "2025-11-30T08:15:00"
        }
      ]
    },
    "arguments": [...]
  },
  "cache_info": { /* same as data.cache_info */ }
}
```

### Fresh Analysis Response

```json
{
  "status": "success",
  "video_id": "dQw4w9WgXcQ",
  "data": {
    "cached": false,
    "analysis_mode": "hard",
    "arguments": [...]
  },
  "cache_info": null
}
```

---

## Configuration

### Max Age (in workflow.py)

```python
cached_analysis, cache_metadata = await select_best_cached_analysis(
    video_id,
    requested_mode=analysis_mode,
    max_age_days=7  # ← Configurable threshold
)
```

**Default:** 7 days  
**Recommendation:** 
- News/current events: 1-3 days
- Scientific topics: 7-14 days
- Evergreen content: 30 days

---

## Benefits

### For Users

✅ **Automatic quality upgrades** - Get better analysis when available  
✅ **Transparency** - Know exactly what was used  
✅ **Choice** - See all available alternatives  
✅ **Freshness** - Old analyses automatically invalidated  

### For System

✅ **Cost optimization** - Reuse expensive "hard" analyses  
✅ **No redundancy** - Don't recreate when better exists  
✅ **Flexibility** - Users can still force specific modes  
✅ **Storage efficiency** - Only keep recent, useful analyses  

---

## Code Flow

### 1. Storage Service (`app/services/storage.py`)

```python
async def select_best_cached_analysis(video_id, requested_mode, max_age_days):
    """
    Smart cache selection:
    1. Get all analyses for video
    2. Filter by age (< max_age_days)
    3. Find exact match OR better quality
    4. Return best option with metadata
    """
```

### 2. Workflow (`app/core/workflow.py`)

```python
async def process_video(youtube_url, analysis_mode="simple"):
    # Step 1: Smart cache check
    cached_analysis, metadata = await select_best_cached_analysis(
        video_id, analysis_mode, max_age_days=7
    )
    
    if cached_analysis:
        # Return with cache_info
        result["cache_info"] = metadata
        return result
    else:
        # Create new analysis
        # Save with (video_id, analysis_mode) composite key
```

### 3. API (`app/api.py`)

```python
@app.post("/api/analyze")
async def analyze_video(request: AnalyzeRequest):
    result = await process_video(
        request.url,
        analysis_mode=request.analysis_mode
    )
    
    return AnalyzeResponse(
        cache_info=result.get("cache_info")  # Include metadata
    )
```

---

## Testing

### Test 1: Quality Upgrade

```bash
# Create hard analysis
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "hard"}'

# Request simple (should get hard)
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "simple"}'
# → Check cache_info.reason == "upgraded"
# → Check cache_info.selected_mode == "hard"
```

### Test 2: Insufficient Quality

```bash
# Create simple analysis
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "simple"}'

# Request hard (should create new)
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "hard"}'
# → Check cache_info == null (new analysis)
```

### Test 3: Age Invalidation

```bash
# Manually update database to make analysis old
db.analyses.updateOne(
  {id: "abc", analysis_mode: "simple"},
  {$set: {updated_at: new Date("2025-11-25")}}
)

# Request analysis (should create new)
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "simple"}'
# → Check cache_info.reason == "too_old" in logs
```

---

## Migration Notes

**Existing analyses (before this feature):**
- May not have `analysis_mode` field
- Will be treated as `"simple"` by default
- Consider adding migration script to set mode

**Recommended migration:**
```javascript
db.analyses.updateMany(
  { analysis_mode: { $exists: false } },
  { $set: { analysis_mode: "simple" } }
)
```

---

## Future Enhancements

- [ ] Configurable max_age_days per user or API key
- [ ] Cache warming: Pre-generate "hard" analyses for popular videos
- [ ] User preferences: "Always use hard mode" setting
- [ ] Analytics: Track cache hit rate per mode
- [ ] Admin endpoint: List all analyses for a video
- [ ] Cleanup job: Delete analyses older than 30 days

---

**Last Updated:** 2025-12-05  
**Status:** ✅ Implemented and tested
