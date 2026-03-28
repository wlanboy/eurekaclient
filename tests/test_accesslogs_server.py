import sys
import os
import threading
import socketserver
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "accesslogs"))

from server import EurekaHandler
from table import analyze_log_file, is_valid_ipv4


@pytest.fixture(scope="module")
def test_server():
    """Startet einen EurekaHandler auf einem zufälligen freien Port."""
    with socketserver.TCPServer(("127.0.0.1", 0), EurekaHandler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        yield port
        httpd.shutdown()


class TestEurekaHandler:
    def test_get_returns_200(self, test_server):
        url = f"http://127.0.0.1:{test_server}/"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200

    def test_get_returns_offline_message(self, test_server):
        url = f"http://127.0.0.1:{test_server}/"
        with urllib.request.urlopen(url) as resp:
            body = resp.read()
        assert body == b"Eureka ist offline"

    def test_get_content_type_html(self, test_server):
        url = f"http://127.0.0.1:{test_server}/"
        with urllib.request.urlopen(url) as resp:
            content_type = resp.headers.get("Content-type")
        assert "text/html" in content_type

    def test_any_path_returns_200(self, test_server):
        url = f"http://127.0.0.1:{test_server}/eureka/apps/SOMESERVICE"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200

    def test_last_sent_status_attribute(self):
        """EurekaHandler speichert den letzten HTTP-Status in _last_sent_status."""
        assert EurekaHandler._last_sent_status == 200


class TestIsValidIpv4:
    @pytest.mark.parametrize("ip", [
        "192.168.1.1",
        "0.0.0.0",
        "255.255.255.255",
        "10.0.0.1",
    ])
    def test_valid_ips(self, ip):
        assert is_valid_ipv4(ip) is True

    @pytest.mark.parametrize("ip", [
        "256.1.1.1",
        "192.168.1",
        "192.168.1.1.1",
        "abc.def.ghi.jkl",
        "",
        "192.168.-1.1",
    ])
    def test_invalid_ips(self, ip):
        assert is_valid_ipv4(ip) is False


LOG_LINE = '10.20.1.15 - [28/Mar/2026:10:00:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'


class TestAnalyzeLogFile:
    def test_groups_ips_by_class_b(self, tmp_path):
        log_file = tmp_path / "access_log"
        log_file.write_text(
            '10.20.1.15 - [28/Mar/2026:10:00:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
            '10.20.3.42 - [28/Mar/2026:10:01:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
            '192.168.1.1 - [28/Mar/2026:10:02:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
        )
        result = analyze_log_file(str(log_file))
        assert result is not None
        assert "10.20" in result
        assert "192.168" in result
        assert "10.20.1.15" in result["10.20"]
        assert "10.20.3.42" in result["10.20"]
        assert "192.168.1.1" in result["192.168"]

    def test_deduplicates_same_ip(self, tmp_path):
        log_file = tmp_path / "access_log"
        log_file.write_text(LOG_LINE * 3)
        result = analyze_log_file(str(log_file))
        assert result is not None
        assert len(result["10.20"]) == 1

    def test_file_not_found_returns_none(self):
        result = analyze_log_file("/nonexistent/path/access_log")
        assert result is None

    def test_empty_file_returns_empty_dict(self, tmp_path):
        log_file = tmp_path / "access_log"
        log_file.write_text("")
        result = analyze_log_file(str(log_file))
        assert result == {}

    def test_ignores_lines_without_ip(self, tmp_path):
        log_file = tmp_path / "access_log"
        log_file.write_text(
            "diese zeile hat kein IP-Format\n"
            + LOG_LINE
        )
        result = analyze_log_file(str(log_file))
        assert result is not None
        assert len(result) == 1
        assert "10.20" in result

    def test_multiple_ips_same_subnet(self, tmp_path):
        log_file = tmp_path / "access_log"
        log_file.write_text(
            '10.0.0.1 - [28/Mar/2026:10:00:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
            '10.0.0.2 - [28/Mar/2026:10:01:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
            '10.0.1.1 - [28/Mar/2026:10:02:00 +0000] - "GET / HTTP/1.1" - 200 "-" "-" "-" "-"\n'
        )
        result = analyze_log_file(str(log_file))
        assert result is not None
        assert len(result["10.0"]) == 3
