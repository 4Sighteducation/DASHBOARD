# VESPA Action Plan System - Overview

## 📋 What You Now Have

### 1. **ACTION_PLAN_SIMPLE_TEMPLATE.html**
- Clean, punchy template with placeholders
- 3 tiers: Quick Wins, Medium Term, Long Term
- Each tier has: Findings, Actions, Activities, Behaviors, Questions
- Ready for AI to populate or manual customization

### 2. **AI_PROMPT_ACTION_PLAN_GENERATOR.txt**
- Complete prompt for GPT-4/Claude
- Takes school baseline data + knowledge bases
- Generates contextual, specific content
- Outputs structured JSON to fill template
- Includes all constraints (concise, realistic, middle-band focus, pattern-aware)

### 3. **EXAMPLE_AI_Generated_Content_Crest_Academy.json**
- Shows what AI would generate for Crest Academy
- Structured JSON matching template placeholders
- Based on real Crest baseline data

### 4. **EXAMPLE_Crest_Academy_Action_Plan_RENDERED.html**
- Complete example showing final output
- Demonstrates how template looks when filled
- Can append to Crest report for testing

---

## 🎯 The Complete Flow

```
SCHOOL BASELINE DATA
    ↓
AI PROMPT (with knowledge bases)
    ↓
AI GENERATES JSON CONTENT
    ↓
PYTHON FILLS TEMPLATE PLACEHOLDERS
    ↓
APPEND TO SCHOOL REPORT
```

---

## 🔧 Implementation Options

### **Option A: Manual (Test First)**
1. Take `ACTION_PLAN_SIMPLE_TEMPLATE.html`
2. Use `EXAMPLE_AI_Generated_Content_Crest_Academy.json` as guide
3. Manually fill placeholders for one school
4. Append to their report
5. Get feedback
6. Then automate

### **Option B: AI-Generated (Flexible)**
```python
import openai

def generate_action_plan_content(school_data, knowledge_bases):
    """
    Call AI to generate contextual action plan
    """
    prompt = build_prompt_from_template(
        school_data=school_data,
        activities_kb=knowledge_bases['activities'],
        insights_kb=knowledge_bases['coaching_insights'],
        statements=knowledge_bases['100_statements']
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=2000
    )
    
    return json.loads(response.choices[0].message.content)
```

### **Option C: Rule-Based Python (Predictable)**
```python
def generate_action_plan_content(school_data, knowledge_bases):
    """
    Use logic to select activities and generate content
    """
    # Identify priorities
    lowest_dimension = min(school_data['vespa_scores'], 
                          key=school_data['vespa_scores'].get)
    
    # Select activities
    quick_wins = select_activities(
        dimension=lowest_dimension,
        tier='quick_wins',
        activities_kb=knowledge_bases['activities']
    )
    
    # Select coaching questions
    questions = select_coaching_questions(
        dimension=lowest_dimension,
        insights_kb=knowledge_bases['coaching_insights']
    )
    
    # Select behaviors
    behaviors = select_100_statements(
        dimension=lowest_dimension,
        statements=knowledge_bases['100_statements']
    )
    
    # Build content dict
    return {
        "quick_wins": {
            "findings": build_findings(school_data, 'quick'),
            "actions": build_actions(quick_wins, school_data),
            "activities": format_activities(quick_wins),
            "behaviors": format_behaviors(behaviors),
            "questions": format_questions(questions)
        },
        # ... etc
    }
```

---

## 🎨 Content Principles (Built Into AI Prompt)

✅ **Concise:** Findings <15 words, Actions <20 words
✅ **Pattern-aware:** References data patterns, not rigid scores
✅ **Middle-band focused:** Explicitly prioritizes 40-50% cohort
✅ **Realistic:** 5-7 min coaching, 45 min meetings, achievable timelines
✅ **Non-patronizing:** No VESPA explanations, assumes training
✅ **Specific:** Names actual activities with IDs (SY26, PR18)
✅ **Behavioral:** Quotes exact 100 Statements
✅ **Evidence-linked:** Brief research references

---

## 📊 What The Final Report Looks Like

```
SCHOOL REPORT.html
├─ Executive Summary
├─ Cycle 1 Baseline Overview
├─ Exam Readiness Index
├─ Questionnaire Insights
├─ Year Group Analysis
├─ Group Analysis
├─ Score Distributions
├─ Statement Level Analysis
├─ [EXISTING RECOMMENDATIONS REMOVED]
└─ ACTION PLAN (NEW)
    ├─ Quick Wins (5 sections, concise)
    ├─ Medium Term (5 sections, concise)
    └─ Long Term (4 sections, concise)
```

---

## ⚡ Quick Start

### **To Test Right Now:**
1. Open `EXAMPLE_Crest_Academy_Action_Plan_RENDERED.html`
2. Copy the content
3. Append to end of `EACT_Crest_Academy_Cycle1_Baseline_20251112_195303.html`
4. Open in browser to see how it looks
5. Share with Crest Academy for feedback

### **To Build Python Automation:**
I can create `action_plan_generator.py` that:
- Reads school baseline data
- Loads knowledge bases
- Either calls AI API OR uses rule-based logic
- Fills template placeholders
- Returns ready-to-append HTML

---

## 💭 Key Differences From Previous Version

| Before | After |
|--------|-------|
| 500+ lines per tier | ~50 lines per tier |
| Explains concepts | Assumes knowledge |
| Rigid score boundaries | Pattern-based guidance |
| Universal approach | Targeted to middle band |
| Long explanations | Punchy bullets |
| 20 min coaching | 5-7 min coaching |
| Multiple examples | One clear path |

---

## 🚀 What Would You Like To Do Next?

1. **Test the rendered example** - Append to Crest report and review?
2. **Customize for another school** - Pick one and I'll generate their version?
3. **Build Python automation** - Create the generator module?
4. **Refine template further** - Still too much content?
5. **Commit and push** - Save all these files to GitHub?

The template is now lean and mean! 🎯



