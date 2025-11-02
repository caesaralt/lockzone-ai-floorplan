# 🧠 AI Learning System - Complete Guide

## Overview

The Integratd Living AI Learning System allows you to teach the AI your custom standards, symbols, and preferences. The AI uses **extended thinking** to learn from your examples and apply them consistently across all future analyses.

---

## 🎯 What You Can Teach The AI

### 1. **Custom Symbol Standards**
Upload floor plans with your company's specific symbol markup standards:
- Custom electrical symbols
- Automation device icons
- Security system symbols
- HVAC control markers
- Audio/visual equipment notation

### 2. **Counting & Placement Rules**
Teach the AI how you count and place components:
- "Always place 2 lights per bedroom"
- "Count 3-gang switches as 3 separate switches"
- "Include one thermostat per floor"
- "Place speakers in corners of living rooms"

### 3. **Correction Patterns**
When the AI makes mistakes, it learns:
- Components it commonly misses
- Incorrect count patterns
- Symbol recognition improvements
- Room-specific requirements

### 4. **Natural Language Instructions**
Simply tell the AI what to do:
- "Always include climate control in master bedrooms"
- "Use premium tier for lighting in living areas"
- "Security cameras are required at all entry points"

---

## 📋 How To Use The Learning System

### Method 1: Upload Training Examples

**Location:** Quote Automation page → Learning tab

**Steps:**
1. Click **"Upload Training Files"**
2. Select one or more floor plans (PDF, PNG, JPG)
3. Add notes describing what the AI should learn:
   ```
   Example: "This floor plan shows our standard for a 3-bedroom home.
   Note the speaker placement in corners and the thermostat placement
   in the hallway. Always follow this pattern for similar layouts."
   ```
4. Click **"Upload Training Data"**

**What Happens:**
- Files are saved to `learning_data/` folder
- AI analyzes each example
- Patterns are stored in `learning_index.json`
- Future analyses will reference these examples

### Method 2: Natural Language Instructions

**Location:** Quote Automation page → Learning tab

**Steps:**
1. Go to **"AI Instructions"** section
2. Type instructions in plain English:
   ```
   - Always place 2 downlights per bedroom
   - Master bedrooms get premium tier automation
   - Include one security camera per external door
   - Bathrooms require humidity sensors
   ```
3. Click **"Save Instructions"**

**What Happens:**
- Instructions are stored as learning examples
- AI receives them in every future analysis prompt
- Extended thinking applies rules systematically

### Method 3: Correction Feedback (AI Mapping)

**Location:** Electrical Mapping page

**Steps:**
1. Upload and analyze a floor plan
2. Review AI's component placement
3. Add/move/remove components as needed
4. Rate the accuracy (1-5 stars)
5. Click **"Save Corrections"**

**What Happens:**
- Corrections are saved to `mapping_learning/learning_index.json`
- AI learns what it missed or got wrong
- High-rated examples (4-5 stars) are prioritized
- Future mappings improve based on feedback

---

## 🔬 How The AI Uses Learning Data

### Extended Thinking Process

When you upload a new floor plan, the AI:

1. **Loads Learning Database**
   - Retrieves last 20 examples
   - Groups by type (symbols, corrections, instructions)
   - Prioritizes high-rated examples

2. **Thinks Through Patterns**
   - Identifies common symbol placements
   - Recognizes counting methods
   - Applies custom standards
   - Considers past corrections

3. **Applies Learning**
   - Follows uploaded symbol standards
   - Uses natural language instructions
   - Adapts based on correction patterns
   - Maintains consistency with examples

4. **Generates Analysis**
   - Counts components using learned methods
   - Places symbols according to standards
   - Applies tier recommendations from examples
   - Returns results following learned patterns

### Learning Context Structure

The AI receives learning data in this format:

```
═══════════════════════════════════════════════════════════
LEARNING DATABASE - Apply These Verified Examples
═══════════════════════════════════════════════════════════

📐 CUSTOM SYMBOL STANDARDS:
────────────────────────────────────────────────────────────

▸ Example from 2025-01-15:
  Standard: Use our company's automation symbols
  Symbols: {
    "light": "⊕",
    "switch": "┤├",
    "sensor": "◉",
    "camera": "🎥"
  }

🔧 CORRECTION PATTERNS:
────────────────────────────────────────────────────────────

▸ Correction from 2025-01-14:
  Issue: Missed sensors in bathrooms
  ⚠ Commonly missed: humidity sensors
  ⚠ Count errors: Undercounted switches by 30%

📝 CUSTOM INSTRUCTIONS:
────────────────────────────────────────────────────────────

  • Always place 2 lights per bedroom
  • Include climate control in living rooms
  • Use premium tier for master bedroom automation
  • Security cameras required at all entry points

═══════════════════════════════════════════════════════════
APPLY ALL LEARNINGS ABOVE TO YOUR ANALYSIS
Use your reasoning to understand patterns and apply them consistently.
═══════════════════════════════════════════════════════════
```

---

## 💾 Data Storage

### File Structure

```
lockzone-ai-floorplan/
├── learning_data/
│   ├── learning_index.json          # Main learning database
│   ├── learning_20250115_plan1.pdf  # Uploaded examples
│   └── learning_20250116_plan2.pdf
│
└── mapping_learning/
    └── learning_index.json           # Mapping corrections
```

### Learning Index Format

```json
{
  "examples": [
    {
      "id": "uuid-here",
      "timestamp": "2025-01-15T10:30:00",
      "type": "upload",
      "filename": "learning_20250115_example.pdf",
      "notes": "Standard 3-bedroom layout with our symbols",
      "analysis_result": {...}
    },
    {
      "id": "uuid-here",
      "timestamp": "2025-01-15T11:00:00",
      "type": "instruction",
      "instruction": "Always place 2 lights per bedroom",
      "notes": "User instruction: Always place 2 lights per bedroom..."
    },
    {
      "id": "uuid-here",
      "timestamp": "2025-01-15T11:30:00",
      "type": "correction",
      "corrections": {
        "missed_components": "humidity sensors in bathrooms",
        "incorrect_counts": "switches undercounted by 2"
      },
      "rating": 4
    }
  ],
  "last_updated": "2025-01-15T11:30:00"
}
```

---

## 🚀 Best Practices

### For Symbol Standards

1. **Upload Clear Examples**
   - High-resolution PDFs
   - Clear symbol markings
   - Consistent labeling

2. **Provide Context**
   - Explain what each symbol means
   - Note any special cases
   - Describe placement rules

3. **Use Multiple Examples**
   - Upload 3-5 similar layouts
   - Show variations of same pattern
   - Demonstrate edge cases

### For Instructions

1. **Be Specific**
   - ❌ "Add lights"
   - ✅ "Place 2 LED downlights per bedroom, centered in ceiling"

2. **Use Room Names**
   - ❌ "More sensors"
   - ✅ "Place 1 motion sensor in each hallway and corridor"

3. **Specify Tiers**
   - ❌ "Good automation"
   - ✅ "Use premium tier for master bedroom, basic for guest rooms"

### For Corrections

1. **Rate Honestly**
   - 5 stars = Perfect, no changes needed
   - 4 stars = Good, minor corrections
   - 3 stars = Okay, several issues
   - 1-2 stars = Poor, major problems

2. **Add Detailed Feedback**
   - Explain what was missed
   - Note patterns in errors
   - Suggest improvements

3. **Review Regularly**
   - Check if accuracy improves
   - Update instructions as needed
   - Remove outdated examples

---

## 📊 Monitoring Learning Performance

### Check Learning Stats

**AI Mapping page** shows:
- Total corrections saved
- Average accuracy rating
- Improvement rate over time
- Number of learning examples

### View Learning Examples

```bash
# View current learning data
cat learning_data/learning_index.json | python3 -m json.tool

# Count examples
cat learning_data/learning_index.json | grep '"type"' | wc -l
```

---

## 🔧 Troubleshooting

### AI Not Applying Learnings

**Check:**
1. Are examples actually saved? Check `learning_data/learning_index.json`
2. Do logs show learning context being loaded? Check Render logs
3. Is ANTHROPIC_API_KEY set? AI needs this to use extended thinking

**Fix:**
- Verify files uploaded successfully
- Check browser console for errors
- Ensure notes field is filled out

### Inconsistent Results

**Possible causes:**
1. Too few examples (upload at least 3-5)
2. Conflicting instructions (review and consolidate)
3. Low-quality images (use high-res PDFs)

**Fix:**
- Add more training examples
- Remove contradictory instructions
- Upload clearer floor plans

### Learning Data Not Persisting

**Check Render deployment:**
```bash
# Render may have ephemeral filesystem
# Learning data should be in persistent storage
```

**Recommended:** Use external database or S3 for production

---

## 🎓 Example Learning Scenarios

### Scenario 1: Custom Symbol Set

**Goal:** Teach AI your company's electrical symbols

**Steps:**
1. Create a PDF with symbol legend
2. Upload with notes: "Symbol Standard - Use these icons"
3. Upload 2-3 example floor plans using these symbols
4. AI will now recognize and use your symbol set

### Scenario 2: Room-Specific Rules

**Goal:** Different automation standards per room type

**Instructions to add:**
```
Master Bedroom:
- 2 wall switches (entry, bedside)
- 4 downlights
- 1 thermostat
- 1 window shading controller
- Premium tier

Guest Bedrooms:
- 1 wall switch
- 2 downlights
- Basic tier

Living Room:
- 3-gang switch (entry, seating, accent)
- 6 downlights + accent lighting
- 2 shading controllers
- 4 speakers (corners)
- Deluxe tier
```

### Scenario 3: Fixing Common Mistakes

**Problem:** AI always misses bathroom humidity sensors

**Solution:**
1. Manually add sensors in AI Mapping tool
2. Rate analysis as 3 stars
3. Add feedback: "Missing humidity sensors - always include one per bathroom"
4. Save correction
5. Future analyses will include bathroom sensors

---

## 📞 Support

For issues with the learning system:
1. Check `/learning_data/learning_index.json` exists and has data
2. Review Render logs for "LEARNING DATABASE" context
3. Verify extended thinking is enabled (check `thinking` parameter in API calls)
4. Test with simple instruction first: "Count all lights"

---

## 🔮 Future Enhancements

Planned features:
- [ ] Visual symbol library with drag-and-drop
- [ ] Learning analytics dashboard
- [ ] Export/import learning database
- [ ] A/B testing different instruction sets
- [ ] Automated accuracy improvement tracking
- [ ] Learning from successful quotes

---

**Version:** 1.0
**Last Updated:** 2025-01-28
**Author:** Claude AI Assistant
