# User Rating System

## Overview

The video analyzer now includes a **user rating system** that allows users to rate the quality of analyses. Ratings influence which cached analysis is selected when multiple modes are available.

---

## Features

### Rating Submission

Users can rate any analysis from 1.0 to 5.0 stars:

```bash
POST /api/analyze/{video_id}/{analysis_mode}/rate
{
  "rating": 4.5
}
```

**Response:**
```json
{
  "status": "success",
  "video_id": "dQw4w9WgXcQ",
  "analysis_mode": "hard",
  "average_rating": 4.3,
  "rating_count": 15,
  "message": "Rating submitted successfully. New average: 4.3 (15 ratings)"
}
```

### Composite Scoring

When selecting which cached analysis to return, the system calculates a **composite score** based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Quality** | 40% | Analysis mode tier (hard=3, medium=2, simple=1) |
| **User Rating** | 30% | Average rating from users (0.0-5.0) |
| **Confidence** | 20% | Number of ratings (logarithmic scale) |
| **Recency** | 10% | Age of analysis (fresher is better) |

**Formula:**
```
composite_score = 
  (quality_tier / 3.0) * 0.40 +
  (avg_rating / 5.0) * 0.30 +
  log10(rating_count + 1) / 2.0 * 0.20 +
  (1 - age_days / max_age) * 0.10
```

---

## Real-World Scenarios

### Scenario 1: High-Rated Medium Beats Low-Rated Hard

```javascript
// Database state:
{
  id: "abc",
  analysis_mode: "hard",
  average_rating: 2.0,  // Poor rating!
  rating_count: 5,
  updated_at: "3 days ago"
}

{
  id: "abc",
  analysis_mode: "medium",
  average_rating: 4.8,  // Excellent rating!
  rating_count: 20,
  updated_at: "2 days ago"
}

// User requests "simple" mode
// Composite scores:
// - hard:   (3/3)*0.4 + (2/5)*0.3 + log(6)/2*0.2 + 0.7*0.1 = 0.61
// - medium: (2/3)*0.4 + (4.8/5)*0.3 + log(21)/2*0.2 + 0.8*0.1 = 0.85

// Result: Returns MEDIUM (better composite score)
```

**Why?** Even though "hard" is higher tier, users consistently rated "medium" much better, indicating higher quality.

### Scenario 2: Fresh Analysis Preferred

```javascript
// Database state:
{
  id: "def",
  analysis_mode: "hard",
  average_rating: 4.5,
  rating_count: 30,
  updated_at: "6 days ago"
}

{
  id: "def",
  analysis_mode: "hard",
  average_rating: 4.2,
  rating_count: 5,
  updated_at: "1 day ago"
}

// Both are "hard" mode, but different ages
// Composite scores:
// - old:  (3/3)*0.4 + (4.5/5)*0.3 + log(31)/2*0.2 + 0.14*0.1 = 0.88
// - new:  (3/3)*0.4 + (4.2/5)*0.3 + log(6)/2*0.2 + 0.86*0.1 = 0.82

// Result: Returns OLD (higher composite despite age)
```

**Why?** More ratings = higher confidence, outweighs slight freshness advantage.

### Scenario 3: Building Confidence Over Time

```javascript
// T=0: New analysis created
{
  id: "ghi",
  analysis_mode: "medium",
  average_rating: 0.0,
  rating_count: 0,
  composite_score: 0.60  // Quality only
}

// T=1: First rating (5.0 stars)
{
  average_rating: 5.0,
  rating_count: 1,
  composite_score: 0.69  // +9% boost
}

// T=2: 10 ratings (avg 4.5 stars)
{
  average_rating: 4.5,
  rating_count: 10,
  composite_score: 0.80  // +20% boost
}

// T=3: 100 ratings (avg 4.5 stars)
{
  average_rating: 4.5,
  rating_count: 100,
  composite_score: 0.87  // +27% boost
}
```

**Why?** Confidence increases logarithmically with ratings, preventing gaming with few votes.

---

## Database Schema

### VideoAnalysis Model

```javascript
{
  "_id": ObjectId("..."),
  "id": "dQw4w9WgXcQ",
  "analysis_mode": "hard",
  "status": "completed",
  "created_at": ISODate("2025-12-01"),
  "updated_at": ISODate("2025-12-03"),
  
  // Rating fields
  "average_rating": 4.3,      // Calculated average (0.0-5.0)
  "rating_count": 15,         // Total number of ratings
  "ratings_sum": 64.5,        // Sum of all ratings (for recalculation)
  
  "content": { /* ... */ }
}
```

### Atomic Rating Updates

```javascript
// MongoDB atomic operation (prevents race conditions)
db.analyses.findOneAndUpdate(
  { id: "abc", analysis_mode: "hard" },
  {
    $inc: {
      rating_count: 1,
      ratings_sum: 4.5  // New rating
    }
  }
)

// Then recalculate average
average_rating = ratings_sum / rating_count
```

---

## API Endpoints

### Submit Rating

```bash
POST /api/analyze/{video_id}/{analysis_mode}/rate

Body:
{
  "rating": 4.5  // 1.0 - 5.0
}

Response:
{
  "status": "success",
  "video_id": "dQw4w9WgXcQ",
  "analysis_mode": "hard",
  "average_rating": 4.3,
  "rating_count": 15,
  "message": "Rating submitted successfully. New average: 4.3 (15 ratings)"
}

Errors:
- 400: Invalid rating (not 1.0-5.0)
- 404: Analysis not found
```

### Get Analysis (with rating info)

```bash
POST /api/analyze

Response:
{
  "status": "success",
  "data": {
    "cached": true,
    "cache_info": {
      "reason": "upgraded",
      "selected_mode": "hard",
      "requested_mode": "simple",
      "age_days": 2,
      "average_rating": 4.5,       // Rating of selected analysis
      "rating_count": 20,
      "composite_score": 0.87,
      "available_analyses": [
        {
          "mode": "hard",
          "age_days": 2,
          "average_rating": 4.5,
          "rating_count": 20
        },
        {
          "mode": "medium",
          "age_days": 5,
          "average_rating": 3.8,
          "rating_count": 8
        }
      ]
    }
  }
}
```

---

## Weight Tuning

Current weights can be adjusted in `app/services/storage.py`:

```python
# In calculate_composite_score()
composite = (
    quality_score * 0.40 +    # ← Adjust these weights
    rating_score * 0.30 +
    confidence_score * 0.20 +
    recency_score * 0.10
)
```

**Recommendations:**

**Quality-First (Current):**
```python
quality: 0.40, rating: 0.30, confidence: 0.20, recency: 0.10
# Best for: Encouraging high-quality analysis modes
```

**User-First:**
```python
quality: 0.25, rating: 0.45, confidence: 0.25, recency: 0.05
# Best for: Trusting user feedback over mode tier
```

**Balanced:**
```python
quality: 0.35, rating: 0.35, confidence: 0.20, recency: 0.10
# Best for: Equal weight on quality and user opinion
```

---

## Confidence Scoring

Logarithmic scale prevents gaming:

| Ratings | Confidence Score | Boost |
|---------|------------------|-------|
| 0 | 0.00 | None |
| 1 | 0.15 | +15% |
| 3 | 0.30 | +30% |
| 10 | 0.50 | +50% |
| 30 | 0.74 | +74% |
| 100 | 1.00 | +100% |

**Why logarithmic?**
- Prevents single user from heavily influencing score
- Requires many ratings to reach max confidence
- 10 ratings = 50% confidence (reasonable threshold)
- 100 ratings = 100% confidence (high trust)

---

## Example Workflow

### User A: Creates Analysis

```bash
# User A requests hard analysis
POST /api/analyze {
  "url": "...",
  "analysis_mode": "hard"
}

# Database after creation:
{
  "analysis_mode": "hard",
  "average_rating": 0.0,
  "rating_count": 0
}
```

### User B: Rates Analysis

```bash
# User B uses the analysis and rates it
POST /api/analyze/dQw4w9WgXcQ/hard/rate {
  "rating": 5.0
}

# Database after rating:
{
  "analysis_mode": "hard",
  "average_rating": 5.0,
  "rating_count": 1,
  "ratings_sum": 5.0
}
```

### User C: Benefits from Rating

```bash
# User C requests simple mode
POST /api/analyze {
  "url": "...",
  "analysis_mode": "simple"
}

# System calculates composite score for "hard":
# quality: (3/3) * 0.4 = 0.40
# rating: (5/5) * 0.3 = 0.30
# confidence: log(2)/2 * 0.2 = 0.06
# recency: 1.0 * 0.1 = 0.10
# Total: 0.86

# Returns "hard" analysis (auto-upgraded)
# Response includes:
{
  "cache_info": {
    "reason": "upgraded",
    "average_rating": 5.0,
    "rating_count": 1,
    "composite_score": 0.86
  }
}
```

### Users D-F: Build Confidence

```bash
# More users rate the analysis
POST .../rate { "rating": 4.0 }  # User D
POST .../rate { "rating": 4.5 }  # User E
POST .../rate { "rating": 5.0 }  # User F

# Database after 4 ratings:
{
  "average_rating": 4.625,
  "rating_count": 4,
  "composite_score": 0.82  # Higher confidence now
}
```

---

## Benefits

### For Users

✅ **Quality signal** - Know which analyses are trusted  
✅ **Influence selection** - Your feedback matters  
✅ **Transparency** - See ratings before using  
✅ **Community-driven** - Crowdsourced quality  

### For System

✅ **Better cache hits** - Serve highest quality  
✅ **User engagement** - Encourage participation  
✅ **Quality improvement** - Identify bad analyses  
✅ **Cost optimization** - Reuse well-rated analyses  

---

## Future Enhancements

- [ ] Per-user rating tracking (prevent duplicate votes)
- [ ] Rating explanations (why did you rate this?)
- [ ] Downvote threshold (archive poorly rated analyses)
- [ ] Admin dashboard (view rating distributions)
- [ ] Rating notifications (email when your analysis is rated)
- [ ] Badge system (trusted raters, frequent contributors)
- [ ] Rating decay (older ratings weigh less)

---

## Testing

### Test 1: Submit Rating

```bash
# Create analysis
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "hard"}'

# Submit rating
curl -X POST /api/analyze/dQw4w9WgXcQ/hard/rate \
  -H "Content-Type: application/json" \
  -d '{"rating": 4.5}'

# Verify response
# → average_rating: 4.5
# → rating_count: 1
```

### Test 2: Composite Scoring

```bash
# Create two analyses with different ratings
# ... (hard with 2.0 rating, medium with 4.8 rating)

# Request simple mode
curl -X POST /api/analyze -d '{"url": "...", "analysis_mode": "simple"}'

# Verify returns medium (higher composite score)
# → cache_info.selected_mode: "medium"
# → cache_info.composite_score: ~0.85
```

### Test 3: Confidence Building

```bash
# Submit 10 ratings
for i in {1..10}; do
  curl -X POST /api/analyze/abc/hard/rate -d '{"rating": 4.5}'
done

# Check final stats
# → average_rating: 4.5
# → rating_count: 10
# → confidence_score: 0.50 (50%)
```

---

**Last Updated:** 2025-12-05  
**Status:** ✅ Implemented and tested
