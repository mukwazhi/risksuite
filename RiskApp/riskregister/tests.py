from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import (
	Risk,
	RiskIndicator,
	IndicatorAssessment,
	IndicatorMeasurement,
	RiskAssessment,
	Department,
	RiskCategory,
	RiskOwner,
	Mitigation,
	MitigationProgressLog,
)
from datetime import date


class ManualAssessmentFlowTest(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='tester', password='pass')
		self.client = Client()
		self.client.login(username='tester', password='pass')

		# Create required department and category, then a risk
		dept = Department.objects.create(name='Test Dept', abbreviation='TD')
		category = RiskCategory.objects.create(name='General')
		self.risk = Risk.objects.create(
			department=dept,
			category=category,
			title='Test Risk',
			description='desc',
			cause='cause',
			impact_description='impact',
			likelihood=3,
			impact=3,
			created_by=self.user,
			status='parked'
		)

		# Create two indicators (use preferred_kpi_name since `name` is a property)
		self.ind1 = RiskIndicator.objects.create(risk=self.risk, preferred_kpi_name='KRI 1')
		self.ind2 = RiskIndicator.objects.create(risk=self.risk, preferred_kpi_name='KRI 2')

	def test_indicator_assessments_lead_to_manual_assessment(self):
		# Post assessment for indicator 1
		url1 = reverse('record_indicator_assessment_for_indicator', args=[self.ind1.pk])
		resp = self.client.get(url1)
		self.assertEqual(resp.status_code, 200)

		post1 = {
			'measured_value': 10,
			'assessment_date': date.today().isoformat(),
			'assessment_notes': 'ok',
		}
		resp = self.client.post(url1, post1, follow=True)
		self.assertEqual(resp.status_code, 200)

		# Now post assessment for indicator 2
		url2 = reverse('record_indicator_assessment_for_indicator', args=[self.ind2.pk])
		resp = self.client.post(url2, {
			'measured_value': 99,
			'assessment_date': date.today().isoformat(),
			'assessment_notes': 'breach',
		}, follow=True)

		# After the second indicator, we should be redirected to the manual assessment page
		# which is served by add_assessment with show_indicator_results flag.
		final_urls = [u for (u, status) in resp.redirect_chain] if resp.redirect_chain else []
		self.assertTrue(any('/add-assessment/' in u or '/add-assessment' in u for u in final_urls) or resp.request.get('PATH_INFO','').startswith('/risks/'))

		# Now load the manual assessment page
		add_url = reverse('add_assessment', args=[self.risk.pk]) + '?show_indicator_results=1'
		resp = self.client.get(add_url)
		self.assertEqual(resp.status_code, 200)
		# Submit a manual assessment
		resp = self.client.post(add_url, {
			'assessment_type': 'periodic',
			'assessment_date': date.today().isoformat(),
			'likelihood': 4,
			'impact': 4,
			'rationale': 'Manual set',
		}, follow=True)

		self.assertEqual(resp.status_code, 200)

		# Verify a RiskAssessment was created and risk updated
		ra = RiskAssessment.objects.filter(risk=self.risk).order_by('-created_at').first()
		self.assertIsNotNone(ra)
		self.assertEqual(ra.likelihood, 4)
		self.assertEqual(ra.impact, 4)

		self.risk.refresh_from_db()
		self.assertEqual(self.risk.likelihood, 4)
		self.assertEqual(self.risk.impact, 4)


class MitigationProgressTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.user = User.objects.create_user(username='mittester', password='pass')
		self.client = Client()
		self.client.login(username='mittester', password='pass')

		dept = Department.objects.create(name='Mit Dept', abbreviation='MD')
		category = RiskCategory.objects.create(name='Mit Category')
		self.risk = Risk.objects.create(
			department=dept,
			category=category,
			title='Mit Risk',
			description='desc',
			cause='cause',
			impact_description='impact',
			likelihood=2,
			impact=2,
			created_by=self.user,
			status='parked'
		)

		# Create an owner and mitigation
		self.owner = RiskOwner.objects.create(name='Owner One', department=dept)
		self.mitigation = Mitigation.objects.create(
			risk=self.risk,
			strategy='reduce',
			action='Take action',
			responsible_person=self.owner,
			due_date=None,
			status='pending',
			completion_percentage=0
		)

	def test_record_progress_update_creates_log(self):
		from .models import MitigationProgressLog

		# Call helper directly
		log = self.mitigation.record_progress_update(
			user=self.user,
			action_type='progress_update',
			notes='Worked on mitigation',
			previous_status='pending',
			previous_completion_percentage=0,
			completion_percentage=25,
		)

		self.assertIsNotNone(log)
		self.assertEqual(MitigationProgressLog.objects.filter(mitigation=self.mitigation).count(), 1)
		self.assertEqual(log.action_type, 'progress_update')
		self.assertEqual(log.completion_percentage, 25)

	def test_update_mitigation_view_logs_progress(self):
		from django.urls import reverse
		from .models import MitigationProgressLog

		url = reverse('update_mitigation', args=[self.mitigation.pk])

		post_data = {
			'status': 'in_progress',
			'completion_percentage': 30,
			'due_date': '',
			'responsible_person': str(self.owner.pk),
			'progress_notes': 'Update via view',
			'postponement_reason': '',
			'failure_reason': '',
			'lessons_learned': '',
			'trigger_reassessment': ''
		}

		resp = self.client.post(url, post_data, follow=True)
		self.assertIn(resp.status_code, (200, 302))

		# A progress log should have been created
		logs = MitigationProgressLog.objects.filter(mitigation=self.mitigation)
		self.assertGreaterEqual(logs.count(), 1)

