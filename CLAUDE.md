# Gavin AI - Context for Claude

## What This Is
Python webcam tracker that uses OpenAI Vision API to detect if student is present/away/on-phone. Generates PDFs with AI summaries. NOT a general-purpose tracker - specifically for study focus.

## Critical Architecture Decisions (The "Why")

### Everything is AI-Powered (No Hardcoded Detection)
- Deleted all MediaPipe/OpenCV shape detection - too many false positives
- OpenAI Vision API at 1 FPS is the ONLY detection method
- Phone detection: looks for attention + active screen, not just "phone in frame" (prevents false positives when phone on desk)
- **Cost**: ~$0.06-0.12/min. This was intentional - accuracy > cost for study tracking

### Three Event Types Only
- `present`: At desk, focused
- `away`: Not visible  
- `phone_suspected`: Actively using phone (not just visible)

Events get: type, start_time, end_time, duration

### Critical Math Rule
In `tracking/analytics.py`, stats MUST add up: `present + away + phone = total`
This broke twice before, analytics table looked stupid in PDFs.

### Time Formatting
Always use `_format_time()` → "1m 30s" not "1.5 minutes"  
Had users confused by decimal minutes.

## File Structure That Matters

```
main.py                      # Entry point, runs camera loop
config.py                    # ALL constants (models, FPS, thresholds)
camera/vision_detector.py    # analyze_frame() - main detection
camera/capture.py            # OpenCV webcam wrapper
tracking/session.py          # Event logging, state changes
tracking/analytics.py        # Compute stats (math must add up!)
ai/summariser.py            # OpenAI GPT summaries (direct tone, no cheerleading)
reporting/pdf_report.py      # ReportLab PDFs (~/Downloads/)
data/sessions/              # JSON session files
```

Legacy files (`detection.py`, `phone_detector.py`) - ignore, kept for reference.

## Code Patterns That Matter

### Vision API Response Parsing
Vision API sometimes wraps JSON in markdown code blocks. `vision_detector.py` strips these:
```python
if response.startswith("```"):
    response = response.split("```")[1].strip()
```
This broke on production. Always handle it.

### Retry with Exponential Backoff
OpenAI API flakes. Always retry:
```python
for attempt in range(max_retries):
    try:
        return api_call()
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (2 ** attempt))
        else:
            raise
```

### Logging Not Print
Use `logger.info()` not `print()` for internal stuff. Console prints are ONLY for user-facing state changes ("Phone detected!", "Person away").

## Config Constants You'll Actually Touch

```python
DETECTION_FPS = 1                       # Don't increase, costs double
PHONE_CONFIDENCE_THRESHOLD = 0.5       # Vision API confidence
PHONE_DETECTION_DURATION_SECONDS = 2   # Sustained detection before triggering
OPENAI_MODEL = "gpt-4o-mini"           # Summaries (supports JSON mode)
OPENAI_VISION_MODEL = "gpt-4o-mini"    # Frame analysis
```

## Testing
```bash
# Unit tests
python3 -m unittest tests.test_session
python3 -m unittest tests.test_analytics

# OpenAI integration
python3 test_openai.py

# Phone detection (manual, use real phone)
python3 test_phone_detection.py
```

## Common Breakages

**"Vision API Error: Expecting value"**  
JSON parsing failed. Check if Vision API wrapped response in markdown. Already handled in `vision_detector.py` but new models might do it differently.

**"Statistics don't add up"**  
`analytics.py` broke again. Verify: `present + away + phone = total`. Check event consolidation logic.

**"Phone not detected"**  
- Is phone screen ON? (Detection requires active screen)
- Is person looking at it? (Attention-based)
- Check Vision API logs for actual response
- Threshold too high? (config.py)

**"Credits not decreasing"**  
Vision API not actually being called. Check logs for HTTP POST to OpenAI.

## Workflow-Specific Stuff

### Running a Test Session
```bash
source venv/bin/activate
python3 main.py
# Short session (~30s), press 'q' to quit
# Check PDF in ~/Downloads/
# Verify stats add up
```

### Checking OpenAI Usage
Dashboard: platform.openai.com → Usage  
Each frame = 1 vision call. 60s at 1 FPS = 60 calls = ~$0.06-0.12

### Adding New Detection Types
1. Update `vision_detector.py` prompt (add field to expected JSON)
2. Add event type to `config.py`
3. Handle in `session.py` state machine
4. Add stats computation in `analytics.py`
5. Update PDF table in `pdf_report.py`

## Python-Specific Quirks

- Python 3.9+ (uses pathlib, type hints)
- Use `pathlib.Path` not string paths
- Type hints required: `def func(x: int) -> str:`
- Dataclasses for structured data
- Docstrings on every function (not optional)

## Privacy/Data Flow

- Frames sent to OpenAI (base64 encoded)
- OpenAI keeps 30 days (abuse monitoring), then deletes
- Nothing saved locally except JSON events (timestamps + types)
- No video recordings ever

## AI Tone (Important)

Summaries should be **direct and factual**, not cheerleading:
- ❌ "Great job! You stayed focused for most of the session!"
- ✅ "Focused for 18 minutes (72%). 3 phone interruptions averaging 2 minutes each."

Implemented in `ai/summariser.py` system prompt. Users hated the generic encouragement.

## Dependencies (Square Artifactory)

Uses Square's internal Artifactory mirror. If pip fails:
```bash
# Check network, may need internal connection
pip install --index-url https://artifactory.squareup.com/...
```

All packages: `opencv-python`, `openai>=1.0.0`, `reportlab`, `python-dotenv`

## Environment Setup

`.env` file required:
```
OPENAI_API_KEY=sk-...
```

Without this, everything fails immediately.

## Current Known Issues

- None critical
- GUI planned but not started
- PDF visualizations could be better (just tables/text now)

## What NOT to Suggest

- ❌ Fallback detection methods (AI-only by design)
- ❌ Saving frames to disk (privacy)
- ❌ More frequent API calls (cost)
- ❌ Generic cheerleading in summaries (users hate it)
- ❌ Decimal minute displays (use _format_time())
- ❌ Stats that don't add up (math must be correct)

## When Editing Code

1. Type hints required
2. Docstrings required  
3. Use logger not print (except user-facing state changes)
4. Test with short session before long ones
5. Check OpenAI usage dashboard
6. Verify PDF output
7. Ensure stats add up (present + away + phone = total)
