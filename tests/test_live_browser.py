from academic_workspace.live_browser import LiveBrowserTransport


class FakeResponse:
    ok = True
    status = 200

    def body(self):
        return b"archivo"


class FakeRequest:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeResponse()


def test_live_transport_downloads_blackboard_resource_through_browser_context():
    transport = LiveBrowserTransport("unused")
    request = FakeRequest()
    transport._request = request

    assert transport.fetch("/bbcswebdav/pid-file/xid-file") == b"archivo"
    assert request.urls == ["https://utecvirtual.blackboard.com/bbcswebdav/pid-file/xid-file"]
