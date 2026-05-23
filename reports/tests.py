from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SmartAnalysisViewTests(TestCase):
	def test_smart_analysis_requires_login_and_renders(self):
		User = get_user_model()
		user = User.objects.create_user(username='analyst', password='pass12345')
		self.client.force_login(user)

		response = self.client.get(reverse('reports:smart_analysis'))

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'reports/smart_analysis.html')
