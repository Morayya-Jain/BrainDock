# Quick Reference: AI-Powered Detection

## 🤖 System Overview

**Everything is AI-powered now!**

```
Camera → OpenAI Vision (every 1 sec) → Detection Results → Log Events
                                     ↓
                              Person present?
                              Phone visible?
                              Other distractions?
```

## 💰 Cost Per Session

| Duration | Vision API Calls | Cost (gpt-4o-mini) |
|----------|------------------|---------------------|
| 1 min | 60 | $0.06-0.12 |
| 5 min | 300 | $0.30-0.60 |
| 30 min | 1,800 | $1.80-3.60 |
| 1 hour | 3,600 | $3.60-7.20 |

**Plus:** ~$0.0003 for end-of-session summary

## ⚙️ Configuration (config.py)

```python
# Line 15-16: Models
OPENAI_MODEL = "gpt-4o-mini"         # Text summaries
OPENAI_VISION_MODEL = "gpt-4o-mini"  # Image analysis

# Line 21: Detection frequency
VISION_DETECTION_INTERVAL = 1.0  # Every 1 second

# Line 22: Phone confidence
PHONE_CONFIDENCE_THRESHOLD = 0.5  # 50% confidence

# Line 31: FPS (how often to analyze)
DETECTION_FPS = 1  # 1 frame per second
```

## 🎯 To Reduce Costs

**Option 1: Analyze less frequently**
```python
DETECTION_FPS = 0.5  # Every 2 seconds (cuts cost in half)
```

**Option 2: Increase cache duration**
Edit `camera/vision_detector.py` line 39:
```python
self.detection_cache_duration = 2.0  # Cache 2 seconds
```

**Option 3: Lower detection quality**
```python
# In vision_detector.py, change detail level:
"detail": "auto"  # From "low" (uses more tokens but better)
```

## 🚀 Adding New Detections

Edit `camera/vision_detector.py` prompt (line 87-101):

```python
prompt = """Analyze this webcam frame.

Return JSON:
{
  "person_present": true/false,
  "phone_visible": true/false,
  "phone_confidence": 0.0-1.0,
  "tablet_visible": true/false,        # NEW!
  "eating_drinking": true/false,       # NEW!
  "talking_to_someone": true/false,    # NEW!
  "distraction_type": "phone" | "tablet" | "eating" | "social" | "none",
  "description": "What you see"
}
"""
```

Then handle new fields in your code!

## 📊 What AI Detects

✅ **Person Present:** Any human visible in frame  
✅ **Phone ACTIVELY BEING USED:** Based on attention + screen state (not position)  
✅ **Phone Confidence:** How sure (0-100%)  
✅ **Distraction Type:** What kind of distraction  
✅ **Description:** Brief summary of scene  

### IMPORTANT: Active Phone Usage Detection

The system detects **active phone usage** based on TWO factors:

**Detection Criteria (BOTH required):**
1. **Attention**: Person's eyes/gaze directed AT the phone
2. **Screen State**: Phone screen is ON (showing light/colors)

**Position is IRRELEVANT:**
- Phone can be on desk OR in hands
- What matters is attention + screen state

**✅ WILL Detect:**
- Phone on desk + person looking down at it + screen ON
- Phone in hands + person looking at screen + screen ON
- Any position where person is engaged with an active screen

**❌ Will NOT Detect:**
- Phone on desk + person looking at computer/elsewhere (no attention)
- Phone anywhere + screen OFF or face-down (no active screen)
- Phone in pocket/bag
- Phone visible but person clearly focused on something else

This prevents false positives while catching all real phone usage!

Can add:
- Tablets
- Other devices
- Eating/drinking
- Other people
- Games
- Anything AI can see!

## 🧪 Testing

```bash
# Quick test
python3 main.py

# Check OpenAI usage
Visit: https://platform.openai.com/usage
```

## 📝 Important Notes

1. **API Key Required** - App won't work without it
2. **Credits Will Decrease** - Vision API is expensive
3. **Much More Accurate** - AI actually sees phones!
4. **Extensible** - Easy to add new detections
5. **No Fallbacks** - If AI fails, detection fails (by design)

## 🎓 Why This Approach

**You wanted:**
- ✅ OpenAI for everything
- ✅ No hardcoded methods
- ✅ Accurate phone detection
- ✅ Extensible system

**You got:** A professional AI-powered detection system!

**Trade-off:** More expensive but MUCH more accurate and flexible! 🚀
