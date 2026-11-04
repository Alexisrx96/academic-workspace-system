from academic_workspace.browser_source import BrowserApiCollector


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, path):
        self.calls.append(path)
        return self.responses[path]


def test_browser_collector_uses_observed_utec_shapes_and_excludes_grades():
    responses = {
        "/learn/api/v1/users/me": {"id": "_user_"},
        "/learn/api/v1/users/_user_/memberships?expand=course.effectiveAvailability,course.permissions,courseRole&includeCount=true&limit=10000": {
            "results": [{"course": {"id": "_course_", "courseId": "SINF-V02-022026", "name": "Sistemas", "description": "Curso", "effectiveAvailability": True}}]
        },
        "/learn/api/v1/courses/_course_/announcements?limit=100&offset=0&sort=startDateRestriction%28desc%29": {
            "results": [{"id": "ann-1", "subject": "Aviso", "body": {"displayText": "Clase mañana"}, "creationDate": "2026-08-10T12:00:00Z"}],
            "paging": {"nextPage": ""},
        },
        "/learn/api/v1/courses/_course_/contents/ROOT/children?%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0": {
            "results": [{"id": "folder-1", "contentHandler": "resource/x-bb-folder", "title": "Semana 1", "description": "Material", "modifiedDate": 1786487449722}],
            "paging": {"nextPage": ""},
        },
        "/learn/api/v1/courses/_course_/contents/folder-1/children?%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0": {
            "results": [{"id": "task-1", "contentHandler": "resource/x-bb-assignment", "title": "Tarea", "dueDate": "2026-08-20T23:59:00Z", "body": {"displayText": "Indicaciones"}}],
            "paging": {"nextPage": ""},
        },
        "/learn/api/v1/courses/_course_/gradebook/columns?isExcludedFromCourseUserActivity=true&expand=associatedRubrics%2CcollectExternalSubmissions&includeInvisible=false": {
            "results": [{"id": "col-1", "columnName": "Tarea"}]
        },
        "/learn/api/v1/courses/_course_/gradebook/grades?isExcludedFromCourseUserActivity=true&limit=100&userId=_user_": {
            "results": [{"id": "grade-1", "columnId": "col-1", "manualScore": 9, "pointsPossible": 10, "instructorFeedback": "Revisar conclusión"}]
        },
    }

    snapshot = BrowserApiCollector(FakeTransport(responses)).collect()

    assert [(c.id, c.course_id) for c in snapshot.courses] == [("_course_", "SINF-V02-022026")]
    assert [(a.kind, a.id) for a in snapshot.activities] == [
        ("announcement", "ann-1"),
        ("assignment", "task-1"),
        ("content", "folder-1"),
        ("feedback", "grade-1"),
    ]
    feedback = next(a for a in snapshot.activities if a.kind == "feedback")
    assert feedback.body == "Revisar conclusión"
    assert "9" not in feedback.body
