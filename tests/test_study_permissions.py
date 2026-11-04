import pytest

from academic_workspace.study_permissions import permission_for


def test_permission_policy_marks_external_publish_as_always_confirmed():
    permission = permission_for("publish_issue")

    assert permission["schema"] == "study-permission.v1"
    assert permission["requires_confirmation"] is True
    assert permission["external_side_effect"] is True


def test_permission_policy_allows_local_report_without_confirmation():
    permission = permission_for("create_incident_report")

    assert permission["requires_confirmation"] is False
    assert permission["external_side_effect"] is False


def test_unknown_permission_fails():
    with pytest.raises(ValueError):
        permission_for("unknown")
