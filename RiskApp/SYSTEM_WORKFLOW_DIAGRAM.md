# RiskMate ERP - System Workflow Diagram

## Complete Application Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RISKMATE ERP SYSTEM WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                         PHASE 1: RISK IDENTIFICATION
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────┐
    │  User Login  │
    └──────┬───────┘
           │
           ▼
    ┌──────────────────┐
    │ Create New Risk  │──────────────┐
    └──────┬───────────┘              │
           │                           │
           ▼                           │
    ┌────────────────────────────┐    │
    │ STAGE 1: Basic Information │    │
    ├────────────────────────────┤    │
    │ • Risk Title               │    │
    │ • Description              │    │
    │ • Cause                    │    │
    │ • Business Impact          │    │
    │ • Category                 │    │
    │ • Department               │    │
    │ • Risk Owner               │    │
    │ • Cross-Category Impacts   │    │
    └────────┬───────────────────┘    │
             │                         │
             ▼                         │
      [Save as Draft]                  │
             │                         │
             │                         │
═════════════▼═════════════════════════════════════════════════════════════════
                    PHASE 2: INHERENT RISK & CONTROLS
═══════════════════════════════════════════════════════════════════════════════
             │
             ▼
    ┌────────────────────────────────┐
    │ STAGE 2: Inherent Assessment  │
    ├────────────────────────────────┤
    │ • Inherent Likelihood (1-5)    │
    │ • Inherent Impact (1-5)        │
    │ • Inherent Risk Score (L×I)    │
    └────────┬───────────────────────┘
             │
             ▼
    ┌────────────────────────────────┐
    │   Define Internal Controls     │
    ├────────────────────────────────┤
    │ • Control Name                 │
    │ • Control Type:                │
    │   - Preventive (80% L, 20% I)  │
    │   - Detective (30% L, 70% I)   │
    │   - Corrective (10% L, 90% I)  │
    │   - Directive (50% L, 50% I)   │
    │ • Weight (1-10)                │
    │ • Initial Effectiveness (0-100%)│
    │ • Control Owner                │
    │ • Frequency                    │
    └────────┬───────────────────────┘
             │
             ▼
    ┌────────────────────────────────┐
    │ Calculate Residual Risk        │
    ├────────────────────────────────┤
    │ Post-Control Residual Score    │
    │ = Inherent Score reduced by    │
    │   weighted control effectiveness│
    └────────┬───────────────────────┘
             │
             ▼
      [Risk Status: Parked]
             │
             │
═════════════▼═════════════════════════════════════════════════════════════════
                      PHASE 3: RISK WORKFLOW & APPROVAL
═══════════════════════════════════════════════════════════════════════════════
             │
             ▼
    ┌────────────────────┐
    │  Submit for Review │
    └────────┬───────────┘
             │
             ▼
      [Status: Pending]
             │
             ├──────────┐
             │          │
             ▼          ▼
    ┌─────────────┐  ┌─────────────┐
    │   Approve   │  │   Reject    │
    │  (Manager)  │  │  (Manager)  │
    └──────┬──────┘  └──────┬──────┘
           │                │
           │                ▼
           │         [Status: Rejected]
           │                │
           │                └──► [Edit & Resubmit]
           │
           ▼
    [Status: Approved]
           │
           │
═════════════▼═════════════════════════════════════════════════════════════════
              PHASE 4: KEY RISK INDICATORS (KRI) SETUP
═══════════════════════════════════════════════════════════════════════════════
           │
           ▼
    ┌──────────────────────────────┐
    │  Add Key Risk Indicators     │
    ├──────────────────────────────┤
    │ For Each Indicator:          │
    │ • Indicator Name (KPI)       │
    │ • Measurement Unit           │
    │ • Measurement Period         │
    │   (daily/weekly/monthly/etc) │
    │ • Appetite Level             │
    │ • Direction (increase/decrease)│
    │ • Trigger Threshold (Caution)│
    │ • Breach Threshold (Critical)│
    │ • Operators (>=, <=, >, <)   │
    │ • Tolerance % (±10%)         │
    └──────────┬───────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │ Generate Assessment Schedules│
    ├──────────────────────────────┤
    │ • Start Date                 │
    │ • Number of Periods          │
    │ • Auto-generate based on     │
    │   measurement period         │
    └──────────┬───────────────────┘
               │
               │
═════════════════════════════════════════════════════════════════════════════════
                  PHASE 5: INDICATOR ASSESSMENT WORKFLOW
═════════════════════════════════════════════════════════════════════════════════
               │
               ├─────────────────┬──────────────────┐
               │                 │                  │
               ▼                 ▼                  ▼
    ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐
    │   SCHEDULED    │  │   ADHOC      │  │  FROM INDICATOR  │
    │  ASSESSMENT    │  │ ASSESSMENT   │  │  HISTORY PAGE    │
    └────────┬───────┘  └──────┬───────┘  └────────┬─────────┘
             │                 │                    │
             │                 │                    │
             └─────────────────┴────────────────────┘
                               │
                               ▼
             ┌─────────────────────────────────┐
             │ Record Indicator Assessment #1  │
             ├─────────────────────────────────┤
             │ • Measured Value                │
             │ • Assessment Date               │
             │ • Assessment Notes              │
             │ • Analysis                      │
             │ • Corrective Actions            │
             │ • Evidence Documents            │
             │ • Assessment Type:              │
             │   - Scheduled (from schedule)   │
             │   - Adhoc (manual/on-demand)    │
             └─────────────┬───────────────────┘
                           │
                           ▼
             ┌─────────────────────────────────┐
             │  Automatic Evaluation           │
             ├─────────────────────────────────┤
             │ • Compare measured value with:  │
             │   - Trigger Threshold → Caution │
             │   - Breach Threshold → Breached │
             │   - Neither → On Target         │
             │ • Calculate variance from       │
             │   tolerance threshold           │
             │ • Calculate trend (vs previous):│
             │   - Improving ⬇                │
             │   - Deteriorating ⬆            │
             │   - Stable ➡                   │
             │   - New (first assessment)      │
             └─────────────┬───────────────────┘
                           │
                           ▼
             ┌─────────────────────────────────┐
             │  Check Remaining Indicators     │
             └─────────────┬───────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
          [More Indicators]  [All Done]
                    │             │
                    │             │
                    ▼             │
    ┌───────────────────────┐    │
    │ Redirect to Next      │    │
    │ Unassessed Indicator  │    │
    └───────┬───────────────┘    │
            │                    │
            └────► [LOOP] ───────┘
                                 │
                                 │
═════════════════════════════════▼═══════════════════════════════════════════
              PHASE 6: CONTROL EFFECTIVENESS ASSESSMENT
═════════════════════════════════════════════════════════════════════════════
                                 │
                                 ▼
              ┌──────────────────────────────┐
              │ Check Active Controls Exist? │
              └──────────┬───────────────────┘
                         │
                  ┌──────┴──────┐
                  │             │
                  ▼             ▼
            [Yes, Has       [No Controls]
             Controls]            │
                  │               │
                  ▼               │
    ┌────────────────────────┐   │
    │ Assess Control         │   │
    │ Effectiveness          │   │
    ├────────────────────────┤   │
    │ For Each Control:      │   │
    │ • Rate Effectiveness   │   │
    │   (0-100%)             │   │
    │ • Visual Progress Bar  │   │
    │ • Color Coded:         │   │
    │   - Green: ≥75%        │   │
    │   - Yellow: ≥50%       │   │
    │   - Red: <50%          │   │
    └────────┬───────────────┘   │
             │                   │
             └───────────────────┘
                       │
                       │
═════════════════════════▼═══════════════════════════════════════════════════
                PHASE 7: OVERALL RISK ASSESSMENT
═════════════════════════════════════════════════════════════════════════════
                       │
                       ▼
        ┌──────────────────────────────┐
        │  Manual Risk Assessment Form │
        ├──────────────────────────────┤
        │ View Indicator Results:      │
        │ • All indicator statuses     │
        │ • On Target / Caution / Breach│
        │ • Measured values            │
        │                              │
        │ View Assessment History:     │
        │ • Previous assessments       │
        │ • KRI details per assessment │
        │ • Trend analysis             │
        │                              │
        │ Enter Overall Assessment:    │
        │ • Assessment Date            │
        │ • Assessment Type            │
        │   - Periodic / Ad-hoc        │
        │ • Likelihood (1-5)           │
        │ • Impact (1-5)               │
        │ • Rationale                  │
        │ • Changes Since Last         │
        │ • Evidence                   │
        │ • Recommendations            │
        └────────┬─────────────────────┘
                 │
                 ▼
        ┌─────────────────────────┐
        │ Save Risk Assessment    │
        ├─────────────────────────┤
        │ • Mark as Current       │
        │ • Mark previous as old  │
        │ • Link to indicator     │
        │   assessments           │
        │ • Update risk L & I     │
        │ • Calculate trend       │
        │ • Generate risk score   │
        └────────┬────────────────┘
                 │
                 │
═════════════════▼═══════════════════════════════════════════════════════════
              PHASE 8: MONITORING & REPORTING
═════════════════════════════════════════════════════════════════════════════
                 │
                 ▼
        ┌──────────────────────────┐
        │   Risk Detail View       │
        ├──────────────────────────┤
        │ OVERVIEW TAB:            │
        │ • Risk Summary Cards:    │
        │   - Inherent Risk        │
        │   - Active Controls      │
        │   - Post-Control Residual│
        │   - Assessed/Current     │
        │ • Risk Description       │
        │ • Cross-Category Impact  │
        │ • Controls Table         │
        │                          │
        │ ASSESSMENTS TAB:         │
        │ • Assessment History     │
        │ • Expandable rows show:  │
        │   - Date & Type          │
        │   - Score & Rating       │
        │   - KRI Status Summary   │
        │   - Trend indicator      │
        │   - Full KRI details     │
        └────────┬─────────────────┘
                 │
                 ├──────────────────────┐
                 │                      │
                 ▼                      ▼
    ┌────────────────────┐  ┌───────────────────────┐
    │ Dashboard Views    │  │ Reports & Analytics   │
    ├────────────────────┤  ├───────────────────────┤
    │ • Risk Matrix      │  │ • PDF Risk Reports    │
    │ • All Risks List   │  │ • Assessment Dashboard│
    │ • Workflow Status: │  │ • Indicator History:  │
    │   - Parked         │  │   - All assessments   │
    │   - Pending        │  │   - Scheduled/Adhoc   │
    │   - Approved       │  │   - Variance tracking │
    │   - Rejected       │  │   - Trend analysis    │
    │ • Actions Required │  │ • Audit Trail         │
    │ • Notifications    │  │ • Traceability Matrix │
    └────────────────────┘  └───────────────────────┘


═════════════════════════════════════════════════════════════════════════════
                          CONTINUOUS CYCLES
═════════════════════════════════════════════════════════════════════════════

┌────────────────────────────────────────────────────────────────────────┐
│                    SCHEDULED ASSESSMENT CYCLE                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Schedule Due → Notification → Record Assessment → Evaluate →          │
│  Next Indicator → ... → Controls → Risk Assessment →                   │
│  Dashboard Updates → Generate Next Schedule → [REPEAT]                 │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│                     ADHOC ASSESSMENT WORKFLOW                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Trigger (from any page) → Assess All Indicators Sequentially →  │
│  Assess Control Effectiveness → Complete Risk Assessment →             │
│  Updated Risk Profile → [Can trigger anytime]                          │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘


═════════════════════════════════════════════════════════════════════════
                      KEY DECISION POINTS
═════════════════════════════════════════════════════════════════════════

◆ Risk Approval/Rejection
   → Approved: Move to KRI setup and monitoring
   → Rejected: Return to creator for revision

◆ Indicator Status Evaluation
   → Breached: Triggers alerts, requires corrective action
   → Caution: Warning state, monitor closely
   → On Target: Normal operation

◆ Assessment Workflow Routing
   → All indicators done + Has controls: → Control Assessment
   → All indicators done + No controls: → Risk Assessment
   → Indicators remaining: → Next Indicator

◆ Assessment Triggers
   → Scheduled: Auto-generated from measurement periods
   → Adhoc: Manual trigger from "Assess Risk" button
   → From History: Direct assessment from indicator history page


═════════════════════════════════════════════════════════════════════════
                         DATA FLOW SUMMARY
═════════════════════════════════════════════════════════════════════════

Risk Creation → Inherent Assessment → Controls Definition →
Approval Workflow → KRI Setup → Schedule Generation →
Indicator Assessments (Scheduled + Adhoc) → Status Evaluation →
Control Effectiveness Assessment → Overall Risk Assessment →
Risk Score Update → Dashboard & Reports → Continuous Monitoring


═════════════════════════════════════════════════════════════════════════
                      USER INTERACTION POINTS
═════════════════════════════════════════════════════════════════════════

1. Login → Dashboard
2. Create/Edit Risk → Multi-stage form
3. Submit for Approval → Workflow action
4. Approve/Reject Risk → Manager action
5. Add Indicators → Configuration
6. Generate Schedules → Setup automation
7. Record Assessment → From schedule or adhoc
8. Assess Controls → Effectiveness rating
9. Complete Risk Assessment → Final evaluation
10. View Reports → Download PDFs
11. Monitor Dashboard → Real-time status
12. Check Indicator History → Detailed analytics


═════════════════════════════════════════════════════════════════════════
                    NOTIFICATION TRIGGERS
═════════════════════════════════════════════════════════════════════════

• Risk Status Changes (Submitted, Approved, Rejected)
• Scheduled Assessments Due
• Overdue Assessments
• Indicator Breaches
• High/Critical Risk Ratings
• Mitigation Due Dates
• Control Effectiveness Below Threshold


═════════════════════════════════════════════════════════════════════════
                     ROLE-BASED ACCESS
═════════════════════════════════════════════════════════════════════════

┌──────────────┬─────────────┬──────────────┬─────────────────┐
│    Role      │   Create    │   Approve    │   Assess        │
├──────────────┼─────────────┼──────────────┼─────────────────┤
│ Risk Owner   │     ✓       │      ✗       │       ✓         │
│ Manager      │     ✓       │      ✓       │       ✓         │
│ Assessor     │     ✗       │      ✗       │       ✓         │
│ Viewer       │     ✗       │      ✗       │       ✗         │
└──────────────┴─────────────┴──────────────┴─────────────────┘

```

## Key Features Summary

### 1. **Comprehensive Risk Management**
   - Multi-stage risk creation
   - Inherent vs residual risk tracking
   - Cross-category impact analysis

### 2. **Control Framework**
   - Multiple control types with different impact profiles
   - Weighted effectiveness calculations
   - Automatic residual risk computation

### 3. **KRI-Based Assessment**
   - Flexible indicator configuration
   - Automated schedule generation
   - Real-time threshold monitoring
   - Variance tracking against tolerance

### 4. **Dual Assessment Pathways**
   - **Scheduled**: Automated periodic assessments
   - **Adhoc**: On-demand assessments triggered by users

### 5. **Integrated Workflow**
   - Sequential indicator assessment
   - Automatic control effectiveness evaluation
   - Comprehensive risk assessment completion

### 6. **Rich Analytics**
   - Assessment history with KRI details
   - Trend analysis (improving/deteriorating/stable)
   - Variance tracking from tolerance thresholds
   - Type indicators (scheduled vs adhoc)

### 7. **Reporting & Visibility**
   - Real-time dashboards
   - PDF report generation
   - Audit trail
   - Assessment traceability matrix

---
**Document Version**: 1.0  
**Last Updated**: January 26, 2026  
**System**: RiskMate ERP - Enterprise Risk Management System
