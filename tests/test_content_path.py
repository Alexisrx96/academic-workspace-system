from academic_workspace.browser_source import BrowserApiCollector


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses

    def get_json(self, path):
        return self.responses[path]


def test_collector_records_observed_folder_lineage_for_content_paths():
    query = "%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0"
    root = f"/learn/api/v1/courses/c1/contents/ROOT/children?{query}"
    child = f"/learn/api/v1/courses/c1/contents/folder-1/children?{query}"
    responses = {
        "/learn/api/v1/users/me": {"id": "u1"},
        "/learn/api/v1/users/u1/memberships?expand=course.effectiveAvailability,course.permissions,courseRole&includeCount=true&limit=10000": {
            "results": [{"course": {"id": "c1", "courseId": "ELE1", "name": "Electrónica", "effectiveAvailability": True}}]
        },
        "/learn/api/v1/courses/c1/announcements?limit=100&offset=0&sort=startDateRestriction%28desc%29": {"results": [], "paging": {"nextPage": ""}},
        root: {"results": [{"id": "folder-1", "contentHandler": "resource/x-bb-folder", "title": "Semana 1"}], "paging": {"nextPage": ""}},
        child: {"results": [{"id": "file-1", "contentHandler": "resource/x-bb-file", "title": "Guía"}], "paging": {"nextPage": ""}},
        "/learn/api/v1/courses/c1/gradebook/columns?isExcludedFromCourseUserActivity=true&expand=associatedRubrics%2CcollectExternalSubmissions&includeInvisible=false": {"results": []},
        "/learn/api/v1/courses/c1/gradebook/grades?isExcludedFromCourseUserActivity=true&limit=100&userId=u1": {"results": []},
    }

    snapshot = BrowserApiCollector(FakeTransport(responses)).collect()
    activity = next(item for item in snapshot.activities if item.id == "file-1")

    assert activity.content_path == ("Semana 1--folder-1",)
