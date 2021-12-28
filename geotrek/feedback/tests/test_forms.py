import uuid
from hashlib import md5
from unittest import mock

from django.core import mail
from django.forms.widgets import EmailInput, HiddenInput, Select
from django.test.utils import override_settings
from mapentity.tests.factories import SuperUserFactory, UserFactory
from mapentity.widgets import MapWidget
from tinymce.widgets import TinyMCE

from geotrek.authent.tests.factories import UserProfileFactory
from geotrek.feedback.forms import ReportForm
from geotrek.feedback.helpers import SuricateMessenger
from geotrek.feedback.models import TimerEvent
from geotrek.feedback.tests.factories import ReportFactory
from geotrek.feedback.tests.test_suricate_sync import (
    SuricateWorkflowTests, test_for_management_mode,
    test_for_report_and_basic_modes)
from geotrek.maintenance.forms import InterventionForm
from geotrek.maintenance.tests.factories import InterventionStatusFactory


class TestSuricateForms(SuricateWorkflowTests):
    def setUp(cls):
        super().setUp()
        cls.filed_report = ReportFactory(status=cls.filed_status, uid=uuid.uuid4())
        cls.waiting_report = ReportFactory(status=cls.waiting_status, uid=uuid.uuid4())
        cls.user = UserFactory(password="drowssap")
        UserProfileFactory.create(user=cls.user)

    @test_for_report_and_basic_modes
    def test_creation_form_common(self):
        data = {
            'email': 'test@test.fr',
            'geom': 'POINT(5.1 6.6)',
        }
        form = ReportForm(data)
        keys = form.fields.keys()
        self.assertIsInstance(form.fields["geom"].widget, MapWidget)
        self.assertIsInstance(form.fields["email"].widget, EmailInput)
        self.assertIsInstance(form.fields["comment"].widget, TinyMCE)
        self.assertIsInstance(form.fields["activity"].widget, Select)
        self.assertIsInstance(form.fields["category"].widget, Select)
        self.assertIsInstance(form.fields["status"].widget, Select)
        self.assertIsInstance(form.fields["problem_magnitude"].widget, Select)
        self.assertIsInstance(form.fields["related_trek"].widget, Select)
        self.assertNotIn('message', keys)
        self.assertIsInstance(form.fields["assigned_user"].widget, HiddenInput)
        self.assertFalse(form.errors)

    @test_for_report_and_basic_modes
    def test_update_form_common(self):
        form = ReportForm(instance=self.filed_report)
        keys = form.fields.keys()
        self.assertIsInstance(form.fields["geom"].widget, MapWidget)
        self.assertIsInstance(form.fields["email"].widget, EmailInput)
        self.assertIsInstance(form.fields["comment"].widget, TinyMCE)
        self.assertIsInstance(form.fields["activity"].widget, Select)
        self.assertIsInstance(form.fields["category"].widget, Select)
        self.assertIsInstance(form.fields["status"].widget, Select)
        self.assertIsInstance(form.fields["problem_magnitude"].widget, Select)
        self.assertIsInstance(form.fields["related_trek"].widget, Select)
        self.assertNotIn('message', keys)
        self.assertIsInstance(form.fields["assigned_user"].widget, HiddenInput)
        self.assertFalse(form.errors)  # assert form is valid

    @test_for_management_mode
    def test_creation_form_specifics_2(self):
        data = {
            'email': 'test@test.fr',
            'geom': 'POINT(5.1 6.6)',
        }
        form = ReportForm(data)
        keys = form.fields.keys()

        self.assertIsInstance(form.fields["geom"].widget, MapWidget)
        self.assertIsInstance(form.fields["email"].widget, EmailInput)
        self.assertIsInstance(form.fields["comment"].widget, TinyMCE)
        self.assertIsInstance(form.fields["activity"].widget, Select)
        self.assertIsInstance(form.fields["category"].widget, Select)
        self.assertIsInstance(form.fields["status"].widget, HiddenInput)
        self.assertIsInstance(form.fields["problem_magnitude"].widget, Select)
        self.assertIsInstance(form.fields["related_trek"].widget, Select)
        self.assertNotIn('message', keys)
        self.assertIsInstance(form.fields["assigned_user"].widget, HiddenInput)

    @test_for_management_mode
    def test_update_form_specifics_2(self):
        form = ReportForm(instance=self.filed_report)
        keys = form.fields.keys()
        self.assertIsInstance(form.fields["geom"].widget, HiddenInput)
        self.assertIsInstance(form.fields["email"].widget, HiddenInput)
        self.assertIsInstance(form.fields["comment"].widget, HiddenInput)
        self.assertIsInstance(form.fields["activity"].widget, HiddenInput)
        self.assertIsInstance(form.fields["category"].widget, HiddenInput)
        self.assertIsInstance(form.fields["status"].widget, Select)
        self.assertIsInstance(form.fields["problem_magnitude"].widget, HiddenInput)
        self.assertIsInstance(form.fields["related_trek"].widget, Select)
        self.assertIn('message', keys)
        self.assertIsInstance(form.fields["assigned_user"].widget, Select)
        # Todo ajouter les contraintes de contenu de status selon old_status / pas de contrainte si autres modes

    @test_for_management_mode
    @mock.patch("geotrek.feedback.helpers.requests.get")
    @mock.patch("geotrek.feedback.helpers.requests.post")
    def test_workflow_assign_step(self, mocked_post, mocked_get):
        self.build_get_request_patch(mocked_get)
        self.build_post_request_patch(mocked_post)
        # When assigning a user to a report
        data = {
            'assigned_user': str(self.user.pk),
            'email': 'test@test.fr',
            'geom': 'POINT(5.1 6.6)',
        }
        form = ReportForm(instance=self.filed_report, data=data)
        form.save()
        # Assert report status changes
        self.assertEquals(self.filed_report.status.suricate_id, "waiting")
        # Asser timer is created
        self.assertEquals(TimerEvent.objects.filter(report=self.filed_report).count(), 1)
        # Assert data forwarded to Suricate
        check = md5(
            (SuricateMessenger().gestion_manager.PRIVATE_KEY_CLIENT_SERVER + SuricateMessenger().gestion_manager.ID_ORIGIN + str(self.filed_report.uid)).encode()
        ).hexdigest()
        call1 = mock.call(
            'http://suricate.example.com/wsSendMessageSentinelle',
            {'id_origin': 'geotrek', 'uid_alerte': self.filed_report.uid, 'message': '', 'check': check},
            auth=('', '')
        )
        call2 = mock.call(
            'http://suricate.example.com/wsUpdateStatus',
            {'id_origin': 'geotrek', 'uid_alerte': self.filed_report.uid, 'statut': 'waiting', 'txt_changestatut': '', 'check': check},
            auth=('', '')
        )
        mocked_post.assert_has_calls([call1, call2], any_order=True)
        # Assert user is notified
        self.assertEqual(mail.outbox[-1].subject, "Geotrek - Nouveau Signalement à traiter")
        self.assertEqual(mail.outbox[-1].to, [self.filed_report.assigned_user.email])

    @test_for_management_mode
    @override_settings()
    def test_workflow_program_step(self):
        # When creating an intervention for a report
        status = InterventionStatusFactory()
        user = SuperUserFactory(username="admin", password="dadadad")
        data = {
            'name': "test_interv",
            'date': "2025-12-12",
            'status': status.pk,
            'structure': user.profile.structure.pk
        }
        form = InterventionForm(user=user, target_type=self.waiting_report.get_content_type_id(), target_id=self.waiting_report.pk, data=data)
        form.is_valid()
        form.save()
        # Assert timer is created
        self.assertEquals(TimerEvent.objects.filter(report=self.waiting_report).count(), 1)
        # Assert report status changed
        self.waiting_report.refresh_from_db()
        self.assertEquals(self.waiting_report.status.suricate_id, "programmed")
