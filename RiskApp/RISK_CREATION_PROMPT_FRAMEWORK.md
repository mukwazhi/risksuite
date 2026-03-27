# Risk Creation Prompt Framework
## Complete Multi-Stage Form Completion Guide

**Version**: 1.0  
**Date**: January 26, 2026  
**Purpose**: Comprehensive prompt template to collect all attributes required for complete risk creation through all workflow stages

---

## How to Use This Framework

This framework provides a structured approach to gather all necessary information for creating a comprehensive risk record in the RiskMate ERP system. Use this as a questionnaire, interview guide, or data collection template.

---

## 🎯 STAGE 1: RISK IDENTIFICATION & BASIC INFORMATION

### Section 1.1: Risk Overview
```
PROMPT: "Let's create a new risk record. Please provide the following information:"

1. RISK TITLE
   Question: "What is the name/title of this risk?"
   Format: Clear, concise description (max 200 characters)
   Example: "Data Breach Due to Inadequate Cybersecurity Controls"
   Response: _______________________________________________

2. RISK DESCRIPTION
   Question: "Describe this risk in detail. What is the risk event?"
   Format: Comprehensive paragraph explaining the risk
   Example: "Risk of unauthorized access to customer data due to weak 
            password policies, outdated security software, and lack of 
            multi-factor authentication systems."
   Response: _______________________________________________
   _______________________________________________
   _______________________________________________

3. RISK CAUSE
   Question: "What are the root causes or sources of this risk?"
   Format: Detailed explanation of what causes this risk
   Example: "Outdated IT infrastructure, insufficient security training, 
            lack of regular security audits, delayed patch management"
   Response: _______________________________________________
   _______________________________________________
   _______________________________________________

4. BUSINESS IMPACT DESCRIPTION
   Question: "What are the potential consequences if this risk materializes?"
   Format: Detailed impact description covering all affected areas
   Example: "Financial losses from regulatory fines, reputational damage, 
            loss of customer trust, operational disruption, legal liabilities"
   Response: _______________________________________________
   _______________________________________________
   _______________________________________________
```

### Section 1.2: Risk Classification
```
5. PRIMARY RISK CATEGORY
   Question: "Which category does this risk primarily belong to?"
   Options:
   [ ] Strategic Risk
   [ ] Operational Risk
   [ ] Financial Risk
   [ ] Compliance/Regulatory Risk
   [ ] Reputational Risk
   [ ] Technology/IT Risk
   [ ] Human Resources Risk
   [ ] Environmental Risk
   [ ] Market Risk
   [ ] Credit Risk
   [ ] Liquidity Risk
   [ ] Other: _______________
   
   Selected: _______________________________________________

6. CROSS-CATEGORY IMPACTS (if applicable)
   Question: "Does this risk impact other categories? If yes, specify:"
   
   Additional Category #1: _______________
   - Impact Level (1-5): ___
   - Likelihood Level (1-5): ___
   - Impact Notes: _______________________________________________
   
   Additional Category #2: _______________
   - Impact Level (1-5): ___
   - Likelihood Level (1-5): ___
   - Impact Notes: _______________________________________________
   
   Additional Category #3: _______________
   - Impact Level (1-5): ___
   - Likelihood Level (1-5): ___
   - Impact Notes: _______________________________________________
```

### Section 1.3: Ownership & Responsibility
```
7. DEPARTMENT/BUSINESS UNIT
   Question: "Which department or business unit does this risk affect?"
   Format: Select from organizational structure
   Example: "Information Technology", "Finance", "Operations"
   Response: _______________________________________________

8. RISK OWNER
   Question: "Who is responsible for managing this risk?"
   Format: Employee name or position
   Example: "Chief Information Security Officer (CISO)"
   Response: _______________________________________________
   Employee ID (if applicable): _______________
   Email: _______________________________________________

9. RISK COORDINATOR/DEPUTY
   Question: "Who is the secondary contact for this risk?"
   Format: Employee name or position
   Response: _______________________________________________
   Employee ID (if applicable): _______________
   Email: _______________________________________________
```

### Section 1.4: Additional Context
```
10. RISK IDENTIFICATION DATE
    Question: "When was this risk first identified?"
    Format: DD/MM/YYYY
    Response: _____ / _____ / _________

11. RISK SOURCE
    Question: "How was this risk identified?"
    Options:
    [ ] Risk Assessment Workshop
    [ ] Internal Audit
    [ ] External Audit
    [ ] Incident/Near Miss
    [ ] Regulatory Change
    [ ] Strategic Planning
    [ ] Employee Report
    [ ] Management Review
    [ ] Other: _______________
    
    Selected: _______________________________________________

12. RELATED RISKS (if any)
    Question: "Are there any related or interconnected risks?"
    Format: List risk IDs or titles
    Response: _______________________________________________
    _______________________________________________
```

---

## 🔴 STAGE 2: INHERENT RISK ASSESSMENT

### Section 2.1: Inherent Likelihood (Before Controls)
```
PROMPT: "Now let's assess the INHERENT risk - the risk level WITHOUT 
         considering any existing controls or mitigations."

13. INHERENT LIKELIHOOD
    Question: "What is the likelihood of this risk occurring WITHOUT any controls?"
    
    Rating Scale:
    [ ] 1 - Rare (Less than 10% chance, once in 10+ years)
    [ ] 2 - Unlikely (10-30% chance, once in 5-10 years)
    [ ] 3 - Possible (30-50% chance, once in 2-5 years)
    [ ] 4 - Likely (50-80% chance, once per year)
    [ ] 5 - Almost Certain (80-100% chance, multiple times per year)
    
    Selected Rating: _____
    
    Justification: "Why did you choose this rating?"
    Response: _______________________________________________
    _______________________________________________
```

### Section 2.2: Inherent Impact (Before Controls)
```
14. INHERENT IMPACT
    Question: "What would be the impact if this risk occurred WITHOUT any controls?"
    
    Rating Scale:
    [ ] 1 - Insignificant (Minimal financial loss <$10K, no disruption)
    [ ] 2 - Minor (Low financial loss $10K-$100K, minor disruption)
    [ ] 3 - Moderate (Medium loss $100K-$1M, noticeable disruption)
    [ ] 4 - Major (High loss $1M-$10M, significant disruption)
    [ ] 5 - Catastrophic (Severe loss >$10M, critical disruption)
    
    Selected Rating: _____
    
    Justification: "Why did you choose this rating?"
    Response: _______________________________________________
    _______________________________________________

15. INHERENT RISK SCORE (Calculated)
    Formula: Inherent Likelihood × Inherent Impact
    Calculated Score: _____ × _____ = _____
    
    Risk Rating:
    [ ] 1-4: Low Risk (Green)
    [ ] 8-14: Medium Risk (Yellow)
    [ ] 15-19: High Risk (Red)
    [ ] 20-25: Critical Risk (Dark Red)
    
    Classification: _______________________________________________
```

---

## 🛡️ STAGE 3: INTERNAL CONTROLS DEFINITION

### Section 3.1: Control Inventory
```
PROMPT: "Now let's identify the internal controls that help mitigate this risk."

16. NUMBER OF CONTROLS
    Question: "How many internal controls exist for this risk?"
    Response: _____ controls
```

### Section 3.2: Control Details (Repeat for Each Control)
```
==================== CONTROL #1 ====================

17.1 CONTROL NAME
     Question: "What is the name of this control?"
     Example: "Multi-Factor Authentication System"
     Response: _______________________________________________

17.2 CONTROL DESCRIPTION
     Question: "Describe this control in detail"
     Example: "All users must authenticate using password + SMS code 
               before accessing systems"
     Response: _______________________________________________
     _______________________________________________

17.3 CONTROL TYPE
     Question: "What type of control is this?"
     Options:
     [ ] Preventive - Stops risks before they occur (80% L, 20% I reduction)
     [ ] Detective - Identifies risks when they happen (30% L, 70% I reduction)
     [ ] Corrective - Fixes issues after occurrence (10% L, 90% I reduction)
     [ ] Directive - Guides behavior to reduce risk (50% L, 50% I reduction)
     
     Selected: _______________________________________________

17.4 CONTROL WEIGHT
     Question: "How important is this control relative to others? (1-10 scale)"
     Note: All control weights should sum to 10 for proper calculation
     Rating: _____ / 10
     
     Explanation: "Why this weight?"
     Response: _______________________________________________

17.5 CONTROL EFFECTIVENESS
     Question: "How effective is this control currently? (0-100%)"
     Rating: _____% 
     
     Effectiveness Guide:
     - 0-25%: Ineffective or rarely applied
     - 26-50%: Partially effective, inconsistent application
     - 51-75%: Generally effective, minor gaps
     - 76-100%: Highly effective, consistently applied
     
     Justification: _______________________________________________
     _______________________________________________

17.6 CONTROL OWNER
     Question: "Who is responsible for this control?"
     Response: _______________________________________________
     Department: _______________________________________________
     Email: _______________________________________________

17.7 CONTROL FREQUENCY
     Question: "How often is this control performed/reviewed?"
     Options:
     [ ] Continuous (Automated, always active)
     [ ] Daily
     [ ] Weekly
     [ ] Monthly
     [ ] Quarterly
     [ ] Semi-Annually
     [ ] Annually
     [ ] Event-Driven
     
     Selected: _______________________________________________

17.8 CONTROL STATUS
     Question: "Is this control currently active?"
     [ ] Active
     [ ] Inactive
     [ ] Planned
     [ ] Under Review
     
     Selected: _______________________________________________

17.9 CONTROL IMPLEMENTATION DATE
     Question: "When was this control implemented?"
     Format: DD/MM/YYYY
     Response: _____ / _____ / _________

17.10 LAST REVIEW DATE
      Question: "When was this control last reviewed/tested?"
      Format: DD/MM/YYYY
      Response: _____ / _____ / _________

17.11 NEXT REVIEW DATE
      Question: "When is the next control review scheduled?"
      Format: DD/MM/YYYY
      Response: _____ / _____ / _________

17.12 CONTROL DOCUMENTATION
      Question: "Are there documented procedures for this control?"
      [ ] Yes - Document Reference: _______________
      [ ] No
      [ ] In Development

17.13 CONTROL TESTING EVIDENCE
      Question: "Is there evidence of control testing?"
      [ ] Yes - Evidence Location: _______________
      [ ] No
      [ ] Testing Scheduled
      
17.14 CONTROL COST (Optional)
      Question: "What is the annual cost of maintaining this control?"
      Currency: _____
      Amount: _______________
      
17.15 CONTROL AUTOMATION LEVEL
      Question: "Is this control automated?"
      [ ] Fully Automated
      [ ] Partially Automated
      [ ] Manual
      
      Automation Details: _______________________________________________

==================== END CONTROL #1 ====================

[REPEAT Section 3.2 for each additional control]

==================== CONTROL #2 ====================
[Same questions 17.1 - 17.15]
...

==================== CONTROL #3 ====================
[Same questions 17.1 - 17.15]
...
```

### Section 3.3: Control Effectiveness Summary
```
18. TOTAL CONTROL EFFECTIVENESS
    Question: "What is the overall weighted effectiveness of all controls?"
    Calculation: Σ(Weight × Effectiveness) for all controls
    Formula: (W1×E1 + W2×E2 + ... + Wn×En) / Σ Weights
    
    Calculated: _____% 
    
    Interpretation:
    [ ] 0-40%: Poor control environment
    [ ] 41-60%: Adequate control environment
    [ ] 61-80%: Strong control environment
    [ ] 81-100%: Excellent control environment
    
    Assessment: _______________________________________________
```

---

## 📊 STAGE 4: RESIDUAL RISK CALCULATION

### Section 4.1: Post-Control Risk Assessment
```
PROMPT: "Based on the controls defined, let's calculate the residual risk 
         (risk remaining AFTER controls are applied)."

19. RESIDUAL LIKELIHOOD
    Calculation: Inherent Likelihood reduced by control effectiveness
    Formula: Based on control types and weighted effectiveness
    
    Calculated Residual Likelihood: _____
    
    Reduction: From _____ to _____ (___% reduction)

20. RESIDUAL IMPACT
    Calculation: Inherent Impact reduced by control effectiveness
    Formula: Based on control types and weighted effectiveness
    
    Calculated Residual Impact: _____
    
    Reduction: From _____ to _____ (___% reduction)

21. POST-CONTROL RESIDUAL RISK SCORE
    Formula: Residual Likelihood × Residual Impact
    Calculated: _____ × _____ = _____
    
    Risk Rating:
    [ ] 1-4: Low Risk (Green)
    [ ] 8-14: Medium Risk (Yellow)
    [ ] 15-19: High Risk (Red)
    [ ] 20-25: Critical Risk (Dark Red)
    
    Classification: _______________________________________________

22. RISK REDUCTION PERCENTAGE
    Formula: ((Inherent Score - Residual Score) / Inherent Score) × 100
    Calculated: (_____ - _____) / _____ × 100 = _____%
    
    Effectiveness Assessment:
    [ ] 0-20%: Controls have minimal impact
    [ ] 21-40%: Controls have moderate impact
    [ ] 41-60%: Controls have significant impact
    [ ] 61-80%: Controls have strong impact
    [ ] 81-100%: Controls are highly effective
```

---

## 🎯 STAGE 5: KEY RISK INDICATORS (KRI) SETUP

### Section 5.1: KRI Strategy
```
PROMPT: "Now let's define Key Risk Indicators (KRIs) to monitor this risk."

23. NUMBER OF INDICATORS
    Question: "How many KRIs will you monitor for this risk?"
    Response: _____ indicators
    
    Recommendation: 2-5 indicators per risk for effective monitoring
```

### Section 5.2: Indicator Details (Repeat for Each KRI)
```
==================== INDICATOR #1 ====================

24.1 INDICATOR NAME
     Question: "What is the name of this indicator?"
     Example: "Number of Failed Login Attempts"
     Response: _______________________________________________

24.2 PREFERRED KPI NAME (Optional)
     Question: "Is there an alternative/preferred name?"
     Example: "Failed Authentication Events"
     Response: _______________________________________________

24.3 INDICATOR DESCRIPTION
     Question: "Describe what this indicator measures"
     Response: _______________________________________________
     _______________________________________________

24.4 MEASUREMENT UNIT
     Question: "What unit is used to measure this indicator?"
     Examples: "Count", "Percentage (%)", "Days", "USD", "Hours"
     Response: _______________________________________________

24.5 MEASUREMENT PERIOD
     Question: "How often should this indicator be measured?"
     Options:
     [ ] Daily
     [ ] Weekly
     [ ] Bi-Weekly
     [ ] Monthly
     [ ] Quarterly
     [ ] Semi-Annually
     [ ] Annually
     
     Selected: _______________________________________________

24.6 APPETITE LEVEL (Target Value)
     Question: "What is the desired/target value for this indicator?"
     Example: "Maximum 5 failed attempts per day"
     Target Value: _______________________________________________
     
     Explanation: "Why this target?"
     Response: _______________________________________________

24.7 INDICATOR DIRECTION
     Question: "For better risk management, should this indicator:"
     [ ] Increase (higher values are better)
     [ ] Decrease (lower values are better)
     
     Selected: _______________________________________________

24.8 TRIGGER THRESHOLD (Caution Level)
     Question: "At what value does this indicator signal caution?"
     Example: "15 failed attempts (triggers warning)"
     Threshold Value: _______________________________________________
     Operator: [ ] >= [ ] <= [ ] > [ ] < [ ] = [ ] ≠
     Selected: _____  Value: _______________

24.9 BREACH THRESHOLD (Critical Level)
     Question: "At what value is this indicator breached/critical?"
     Example: "30 failed attempts (critical breach)"
     Threshold Value: _______________________________________________
     Operator: [ ] >= [ ] <= [ ] > [ ] < [ ] = [ ] ≠
     Selected: _____  Value: _______________

24.10 TOLERANCE PERCENTAGE
      Question: "What is the acceptable variance from appetite? (±%)"
      Example: "±10% tolerance"
      Tolerance: ± _____% 
      
      Calculated Range:
      - Lower Bound: _____
      - Upper Bound: _____

24.11 DATA SOURCE
      Question: "Where is the data for this indicator collected?"
      Example: "Security logs from authentication server"
      Response: _______________________________________________

24.12 MEASUREMENT RESPONSIBILITY
      Question: "Who is responsible for measuring this indicator?"
      Response: _______________________________________________
      Department: _______________________________________________

24.13 REPORTING FREQUENCY
      Question: "How often should results be reported?"
      [ ] Real-time
      [ ] Daily
      [ ] Weekly
      [ ] Monthly
      [ ] Quarterly
      
      Selected: _______________________________________________

24.14 BASELINE VALUE (if known)
      Question: "What is the current/baseline value?"
      Current Value: _______________________________________________
      Baseline Date: _____ / _____ / _________

24.15 INDICATOR CATEGORY
      Question: "What category does this indicator belong to?"
      [ ] Leading Indicator (Predictive)
      [ ] Lagging Indicator (Historical)
      [ ] Concurrent Indicator (Real-time)
      
      Selected: _______________________________________________

==================== END INDICATOR #1 ====================

[REPEAT Section 5.2 for each additional indicator]

==================== INDICATOR #2 ====================
[Same questions 24.1 - 24.15]
...

==================== INDICATOR #3 ====================
[Same questions 24.1 - 24.15]
...
```

### Section 5.3: Assessment Schedule Generation
```
25. SCHEDULE START DATE
    Question: "When should the first indicator assessment occur?"
    Format: DD/MM/YYYY
    Response: _____ / _____ / _________

26. NUMBER OF ASSESSMENT PERIODS
    Question: "How many assessment periods should be generated?"
    Example: "12 (for monthly assessments over one year)"
    Response: _____ periods
    
    Schedule End Date (Calculated): _____ / _____ / _________

27. SCHEDULE GENERATION PREFERENCE
    Question: "How should the schedule be generated?"
    [ ] Automatic (based on measurement period)
    [ ] Manual (custom dates)
    
    Selected: _______________________________________________
```

---

## 📋 STAGE 6: MITIGATION & TREATMENT PLAN

### Section 6.1: Risk Treatment Strategy
```
28. RISK TREATMENT OPTION
    Question: "What is the primary treatment strategy for this risk?"
    Options:
    [ ] Accept - Accept the risk as-is (risk appetite aligned)
    [ ] Mitigate - Reduce likelihood/impact through additional controls
    [ ] Transfer - Share or transfer risk (insurance, outsourcing)
    [ ] Avoid - Eliminate risk by stopping the activity
    [ ] Exploit - Take advantage of opportunity (for positive risks)
    
    Selected: _______________________________________________
    
    Rationale: _______________________________________________
    _______________________________________________

29. MITIGATION ACTIONS REQUIRED
    Question: "Are additional mitigation actions needed?"
    [ ] Yes - How many? _____ actions
    [ ] No - Current controls are sufficient
```

### Section 6.2: Mitigation Action Details (If Applicable)
```
==================== MITIGATION ACTION #1 ====================

30.1 ACTION TITLE
     Question: "What is the mitigation action?"
     Example: "Implement Security Awareness Training Program"
     Response: _______________________________________________

30.2 ACTION DESCRIPTION
     Question: "Describe this action in detail"
     Response: _______________________________________________
     _______________________________________________

30.3 RESPONSIBLE PERSON
     Question: "Who will implement this action?"
     Response: _______________________________________________
     Department: _______________________________________________

30.4 TARGET COMPLETION DATE
     Question: "When should this action be completed?"
     Format: DD/MM/YYYY
     Response: _____ / _____ / _________

30.5 ACTION STATUS
     Question: "What is the current status?"
     [ ] Not Started
     [ ] In Progress
     [ ] Completed
     [ ] On Hold
     [ ] Cancelled
     
     Selected: _______________________________________________

30.6 COMPLETION PERCENTAGE
     Question: "What percentage of this action is complete?"
     Response: _____%

30.7 ESTIMATED COST
     Question: "What is the estimated cost?"
     Currency: _____
     Amount: _______________

30.8 PRIORITY
     Question: "What is the priority level?"
     [ ] Critical
     [ ] High
     [ ] Medium
     [ ] Low
     
     Selected: _______________________________________________

==================== END MITIGATION ACTION #1 ====================

[REPEAT for additional mitigation actions]
```

---

## ✅ STAGE 7: RISK APPROVAL & WORKFLOW

### Section 7.1: Review & Submission
```
31. RISK STATUS
    Question: "What is the initial status of this risk?"
    [ ] Draft - Still being developed
    [ ] Parked - Complete but not submitted
    [ ] Pending - Submitted for approval
    
    Selected: _______________________________________________

32. SUBMIT FOR APPROVAL?
    Question: "Ready to submit this risk for management approval?"
    [ ] Yes - Submit now
    [ ] No - Save as draft
    
    If Yes:
    - Approver Name: _______________________________________________
    - Approver Role: _______________________________________________
    - Submission Date: _____ / _____ / _________

33. REVIEW CYCLE
    Question: "How often should this risk be reviewed?"
    [ ] Monthly
    [ ] Quarterly
    [ ] Semi-Annually
    [ ] Annually
    [ ] Event-Driven
    
    Selected: _______________________________________________
    Next Review Date: _____ / _____ / _________
```

---

## 📎 STAGE 8: SUPPORTING DOCUMENTATION

### Section 8.1: Attachments & References
```
34. SUPPORTING DOCUMENTS
    Question: "Are there any supporting documents?"
    [ ] Yes
    [ ] No
    
    If Yes, list documents:
    1. Document Name: _______________________________________________
       Document Type: _______________________________________________
       Location/Link: _______________________________________________
    
    2. Document Name: _______________________________________________
       Document Type: _______________________________________________
       Location/Link: _______________________________________________

35. RELATED POLICIES/PROCEDURES
    Question: "Which policies or procedures relate to this risk?"
    Response: _______________________________________________
    _______________________________________________

36. REGULATORY REQUIREMENTS
    Question: "Are there regulatory requirements related to this risk?"
    [ ] Yes - Specify: _______________________________________________
    [ ] No

37. INDUSTRY STANDARDS
    Question: "Which industry standards apply?"
    Examples: ISO 31000, COSO ERM, Basel III, SOX, GDPR
    Response: _______________________________________________
```

---

## 💬 STAGE 9: ADDITIONAL INFORMATION

### Section 9.1: Notes & Comments
```
38. RISK INTERCONNECTIONS
    Question: "How does this risk relate to other risks in the register?"
    Response: _______________________________________________
    _______________________________________________

39. RISK VELOCITY
    Question: "How quickly could this risk materialize?"
    [ ] Immediate (within days)
    [ ] Short-term (within weeks)
    [ ] Medium-term (within months)
    [ ] Long-term (within years)
    
    Selected: _______________________________________________

40. RISK PERSISTENCE
    Question: "How long would the impact last if this risk occurred?"
    [ ] Temporary (days to weeks)
    [ ] Short-duration (weeks to months)
    [ ] Long-duration (months to years)
    [ ] Permanent
    
    Selected: _______________________________________________

41. ADDITIONAL NOTES
    Question: "Any other information relevant to this risk?"
    Response: _______________________________________________
    _______________________________________________
    _______________________________________________

42. ESCALATION CRITERIA
    Question: "Under what circumstances should this risk be escalated?"
    Response: _______________________________________________
    _______________________________________________
```

---

## ✨ COMPLETION CHECKLIST

### Final Review Before Submission
```
☐ All mandatory fields completed
☐ Risk title is clear and descriptive
☐ Inherent risk assessment completed
☐ At least one control defined
☐ Control weights sum to 10
☐ Residual risk calculated
☐ At least one KRI defined
☐ KRI thresholds are realistic
☐ Assessment schedule generated
☐ Risk owner assigned
☐ Supporting documentation attached
☐ Risk reviewed by owner
☐ Ready for approval submission
```

---

## 📊 DATA SUMMARY OUTPUT

### Quick Reference Sheet
```
=================================================================
RISK SUMMARY SHEET
=================================================================

Risk ID: [Auto-generated]
Risk Title: _______________________________________________
Status: _______________________________________________
Created By: _______________________________________________
Created Date: _____ / _____ / _________

INHERENT RISK
- Likelihood: _____ / 5
- Impact: _____ / 5
- Score: _____ / 25
- Rating: _______________________________________________

CONTROLS
- Number of Controls: _____
- Total Effectiveness: _____%

RESIDUAL RISK
- Likelihood: _____ / 5
- Impact: _____ / 5
- Score: _____ / 25
- Rating: _______________________________________________
- Risk Reduction: _____%

KEY RISK INDICATORS
- Number of KRIs: _____
- Measurement Periods: _______________________________________________
- Next Assessment: _____ / _____ / _________

OWNERSHIP
- Risk Owner: _______________________________________________
- Department: _______________________________________________
- Approver: _______________________________________________

=================================================================
```

---

## 🔄 NEXT STEPS AFTER SUBMISSION

1. **Approval Stage**
   - Risk routed to approver
   - Awaiting approval decision
   - May require revisions

2. **Post-Approval**
   - Risk status: Approved
   - Indicator assessments can begin
   - Monitoring and reporting active

3. **Continuous Monitoring**
   - Scheduled KRI assessments
   - Adhoc assessments as needed
   - Regular risk reviews
   - Control effectiveness updates

---

**End of Risk Creation Prompt Framework**

*This framework ensures comprehensive risk data collection across all stages of the RiskMate ERP workflow.*
