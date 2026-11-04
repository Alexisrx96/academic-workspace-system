from academic_workspace.browser_source import BrowserApiCollector


class FakeTransport:
    def __init__(self, responses):
        self.responses = responses

    def get_json(self, path):
        return self.responses[path]


def test_collector_preserves_file_and_embedded_blackboard_resources():
    root = "/learn/api/v1/courses/_course_/contents/ROOT/children?%40view=Summary&expand=assignedGroups%2CselfEnrollmentGroups.group%2CgradebookCategory&includeInActivityTracking=true&limit=100&offset=0"
    responses = {
        "/learn/api/v1/users/me": {"id": "_user_"},
        "/learn/api/v1/users/_user_/memberships?expand=course.effectiveAvailability,course.permissions,courseRole&includeCount=true&limit=10000": {
            "results": [{"course": {"id": "_course_", "courseId": "ELE1", "name": "Electrónica", "effectiveAvailability": True}}]
        },
        "/learn/api/v1/courses/_course_/announcements?limit=100&offset=0&sort=startDateRestriction%28desc%29": {"results": [], "paging": {"nextPage": ""}},
        root: {
            "results": [
                {
                    "id": "file-1", "contentHandler": "resource/x-bb-file", "title": "Guía",
                    "parentId": "ROOT",
                    "body": {"displayText": "Guía", "rawText": "Guía"},
                    "contentDetail": {"resource/x-bb-file": {"file": {
                        "fileName": "Guía.pdf", "mimeType": "application/pdf", "fileSize": 42,
                        "permanentUrl": "/bbcswebdav/pid-file/xid-file"
                    }}},
                },
                {
                    "id": "doc-1", "contentHandler": "resource/x-bb-document", "title": "Lectura",
                    "parentId": "ROOT",
                    "body": {"rawText": '<p>Leer <a href="https://utecvirtual.blackboard.com/bbcswebdav/pid-doc/xid-doc">lectura.docx</a></p>'},
                },
            ],
            "paging": {"nextPage": ""},
        },
        "/learn/api/v1/courses/_course_/gradebook/columns?isExcludedFromCourseUserActivity=true&expand=associatedRubrics%2CcollectExternalSubmissions&includeInvisible=false": {"results": []},
        "/learn/api/v1/courses/_course_/gradebook/grades?isExcludedFromCourseUserActivity=true&limit=100&userId=_user_": {"results": []},
    }

    snapshot = BrowserApiCollector(FakeTransport(responses)).collect()
    resources = {activity.id: activity.attachments for activity in snapshot.activities}

    assert resources["file-1"] == ({
        "id": "file-1",
        "name": "Guía.pdf",
        "mime_type": "application/pdf",
        "size": 42,
        "source_url": "/bbcswebdav/pid-file/xid-file",
    },)
    assert resources["doc-1"] == ({
        "id": "doc-1-embedded-1",
        "name": "lectura.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": None,
        "source_url": "/bbcswebdav/pid-doc/xid-doc",
    },)
