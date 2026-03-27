"""
Assessment Aggregation Service
Aggregates indicator assessments into enterprise-level risk assessments
"""
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AssessmentAggregationService:
    """Service to aggregate indicator assessments into risk assessments"""
    
    @staticmethod
    def create_risk_assessment_from_indicators(risk, period_start, period_end, assessment_type='periodic', user=None):
        """
        Create risk assessment aggregating recent indicator assessments
        
        Args:
            risk: Risk instance
            period_start: Start date of assessment period
            period_end: End date of assessment period
            assessment_type: Type of assessment ('periodic', 'triggered', 'ad_hoc')
            user: User conducting the assessment
            
        Returns:
            RiskAssessment instance or None if insufficient data
        """
        from riskregister.models import RiskAssessment, IndicatorAssessment
        
        # Get all indicator assessments in period
        indicator_assessments = IndicatorAssessment.objects.filter(
            indicator__risk=risk,
            assessment_date__range=[period_start, period_end]
        )
        
        if not indicator_assessments.exists():
            logger.warning(f"No indicator assessments found for risk {risk.risk_id} in period {period_start} to {period_end}")
            return None
        
        logger.info(f"Aggregating {indicator_assessments.count()} indicator assessments for risk {risk.risk_id}")
        
        # Calculate aggregate metrics
        status_counts = {
            'on_target': indicator_assessments.filter(status='on_target').count(),
            'caution': indicator_assessments.filter(status='caution').count(),
            'breached': indicator_assessments.filter(status='breached').count(),
        }
        
        # Determine overall risk rating based on indicators
        likelihood, impact = AssessmentAggregationService._calculate_risk_rating(
            risk, indicator_assessments, status_counts
        )
        
        # Generate narrative
        narrative = AssessmentAggregationService._generate_narrative(
            risk, indicator_assessments, status_counts
        )
        
        # Get previous assessment for comparison
        previous_assessment = RiskAssessment.objects.filter(
            risk=risk,
            is_current=True
        ).first()
        
        # Mark previous assessments as not current
        RiskAssessment.objects.filter(risk=risk, is_current=True).update(is_current=False)
        
        # Create risk assessment
        risk_assessment = RiskAssessment.objects.create(
            risk=risk,
            assessment_date=period_end,
            assessment_type=assessment_type,
            likelihood=likelihood,
            impact=impact,
            assessor=user,
            previous_likelihood=previous_assessment.likelihood if previous_assessment else None,
            previous_impact=previous_assessment.impact if previous_assessment else None,
            executive_summary=narrative['summary'],
            rationale=narrative['detailed'],
            is_current=True,
        )
        
        # Aggregate indicator data
        risk_assessment.aggregate_from_indicators(period_start, period_end)
        
        # Mark all source assessments as having triggered this assessment
        indicator_assessments.update(triggered_risk_assessment=True)
        
        # Update risk's current likelihood and impact
        risk.likelihood = likelihood
        risk.impact = impact
        risk.save(update_fields=['likelihood', 'impact'])
        
        logger.info(f"Created risk assessment {risk_assessment.id} for risk {risk.risk_id}")
        
        return risk_assessment
    
    @staticmethod
    def _calculate_risk_rating(risk, indicator_assessments, status_counts):
        """
        Calculate likelihood and impact based on indicator statuses
        
        Uses a weighted scoring system:
        - Breached indicators have highest weight (0.6)
        - Caution indicators have medium weight (0.3)
        - On-target indicators have no negative weight
        """
        
        total_count = indicator_assessments.count()
        breached_count = status_counts['breached']
        caution_count = status_counts['caution']
        
        if total_count == 0:
            # Fallback to current risk rating
            return risk.likelihood or 3, risk.impact or 3
        
        # Weight-based calculation
        breach_weight = 0.6
        caution_weight = 0.3
        
        score = (breached_count * breach_weight + caution_count * caution_weight) / total_count
        
        # Get current risk rating
        current_likelihood = risk.likelihood or 3
        current_impact = risk.impact or 3
        
        # Adjust based on indicator performance
        if score > 0.5:  # More than 50% breached/caution
            likelihood = min(5, current_likelihood + 1)
            impact = min(5, current_impact + 1)
        elif score > 0.3:  # 30-50% breached/caution
            likelihood = current_likelihood
            impact = current_impact
        else:  # Less than 30% breached/caution
            likelihood = max(1, current_likelihood - 1) if score < 0.1 else current_likelihood
            impact = max(1, current_impact - 1) if score < 0.1 else current_impact
        
        logger.debug(f"Risk rating calculated: L={likelihood}, I={impact} (score={score:.2f})")
        
        return likelihood, impact
    
    @staticmethod
    def _generate_narrative(risk, indicator_assessments, status_counts):
        """Generate assessment narrative from indicator data"""
        
        total = indicator_assessments.count()
        breached = indicator_assessments.filter(status='breached')
        caution = indicator_assessments.filter(status='caution')
        on_target = indicator_assessments.filter(status='on_target')
        
        # Executive summary
        summary = f"Risk assessment for {risk.title} based on {total} indicator assessment(s). "
        
        if breached.exists():
            summary += f"{breached.count()} indicator(s) breached thresholds. "
        if caution.exists():
            summary += f"{caution.count()} indicator(s) in caution zone. "
        if on_target.exists():
            summary += f"{on_target.count()} indicator(s) on target. "
        
        # Detailed analysis
        detailed = f"Assessment Period Analysis:\n\n"
        detailed += f"Total Indicators Assessed: {total}\n\n"
        detailed += f"Performance Status:\n"
        detailed += f"  • On Target: {status_counts['on_target']}\n"
        detailed += f"  • Caution: {status_counts['caution']}\n"
        detailed += f"  • Breached: {status_counts['breached']}\n\n"
        
        if breached.exists():
            detailed += "Critical Issues (Breached Indicators):\n"
            for assessment in breached:
                detailed += f"  • {assessment.indicator.preferred_kpi_name}: "
                detailed += f"{assessment.formatted_value}"
                if assessment.indicator.breach_threshold:
                    detailed += f" (Threshold: {assessment.indicator.breach_operator} {assessment.indicator.breach_threshold})"
                detailed += "\n"
                if assessment.assessment_notes:
                    detailed += f"    Notes: {assessment.assessment_notes[:100]}...\n"
            detailed += "\n"
        
        if caution.exists():
            detailed += "Areas of Concern (Caution Zone):\n"
            for assessment in caution:
                detailed += f"  • {assessment.indicator.preferred_kpi_name}: "
                detailed += f"{assessment.formatted_value}"
                if assessment.indicator.trigger_threshold:
                    detailed += f" (Threshold: {assessment.indicator.trigger_operator} {assessment.indicator.trigger_threshold})"
                detailed += "\n"
            detailed += "\n"
        
        # Recommendations
        if breached.exists() or caution.exists():
            detailed += "Recommendations:\n"
            if breached.exists():
                detailed += "  • Immediate attention required for breached indicators\n"
                detailed += "  • Review and update mitigation strategies\n"
            if caution.exists():
                detailed += "  • Monitor caution-zone indicators closely\n"
                detailed += "  • Consider preventive actions to avoid breach\n"
        
        return {
            'summary': summary.strip(),
            'detailed': detailed.strip(),
        }
    
    @staticmethod
    def check_auto_trigger_conditions(risk):
        """
        Check if risk should have an auto-triggered assessment based on indicator breaches
        
        Returns:
            RiskAssessment instance if triggered, None otherwise
        """
        from datetime import date
        from riskregister.models import IndicatorAssessment
        
        # Check if risk has schedule config
        if not hasattr(risk, 'schedule_config') or not risk.schedule_config.is_active:
            return None
        
        config = risk.schedule_config
        
        # Get recent assessments (last 30 days)
        period_start = date.today() - timedelta(days=30)
        period_end = date.today()
        
        recent_assessments = IndicatorAssessment.objects.filter(
            indicator__risk=risk,
            assessment_date__gte=period_start,
            triggered_risk_assessment=False  # Not already processed
        )
        
        breached_count = recent_assessments.filter(status='breached').count()
        
        logger.debug(f"Risk {risk.risk_id}: {breached_count} breached indicators (threshold: {config.auto_trigger_on_breached})")
        
        if breached_count >= config.auto_trigger_on_breached:
            logger.info(f"Auto-triggering risk assessment for {risk.risk_id} due to {breached_count} breached indicators")
            
            return AssessmentAggregationService.create_risk_assessment_from_indicators(
                risk=risk,
                period_start=period_start,
                period_end=period_end,
                assessment_type='triggered'
            )
        
        return None
