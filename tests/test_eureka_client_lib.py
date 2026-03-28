import threading
from unittest.mock import patch, MagicMock

import requests

from eureka_client_lib import (
    MetricsStore,
    get_ip_address,
    register_instance,
    send_heartbeat,
    deregister_instance,
)

SERVICE_DATA = {
    "serviceName": "testservice",
    "hostName": "localhost",
    "httpPort": 8080,
    "infoEndpointPath": "/actuator/info",
    "healthEndpointPath": "/actuator/health",
}


class TestMetricsStore:
    def test_initial_state(self):
        store = MetricsStore()
        data = store.get_metrics_data()
        assert data["successful_registrations_total"] == 0
        assert data["registration_errors_total"] == 0
        assert data["service_registered_status"] == {}

    def test_increment_successful_registrations(self):
        store = MetricsStore()
        store.increment_successful_registrations()
        store.increment_successful_registrations()
        assert store.get_metrics_data()["successful_registrations_total"] == 2

    def test_increment_registration_errors(self):
        store = MetricsStore()
        store.increment_registration_errors()
        assert store.get_metrics_data()["registration_errors_total"] == 1

    def test_set_service_registered_status(self):
        store = MetricsStore()
        store.set_service_registered_status("FOO", 1)
        assert store.get_metrics_data()["service_registered_status"]["FOO"] == 1

    def test_get_metrics_data_returns_copy(self):
        """Externe Änderungen am zurückgegebenen Dict dürfen den Store nicht verändern."""
        store = MetricsStore()
        store.set_service_registered_status("FOO", 1)
        data = store.get_metrics_data()
        data["service_registered_status"]["FOO"] = 99
        assert store.get_metrics_data()["service_registered_status"]["FOO"] == 1

    def test_thread_safety(self):
        store = MetricsStore()
        threads = [
            threading.Thread(target=store.increment_successful_registrations)
            for _ in range(100)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert store.get_metrics_data()["successful_registrations_total"] == 100


class TestGetIpAddress:
    def test_valid_hostname(self):
        assert get_ip_address("localhost") == "127.0.0.1"

    def test_invalid_hostname_falls_back(self):
        ip = get_ip_address("this.host.does.not.exist.invalid")
        assert ip == "127.0.0.1"


class TestRegisterInstance:
    def test_success_204(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=204)
        with patch("eureka_client_lib.requests.post", return_value=mock_resp):
            result = register_instance(SERVICE_DATA, store)
        assert result is True
        data = store.get_metrics_data()
        assert data["successful_registrations_total"] == 1
        assert data["service_registered_status"]["TESTSERVICE"] == 1

    def test_failure_non_204(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=500, text="Internal Error")
        with patch("eureka_client_lib.requests.post", return_value=mock_resp):
            result = register_instance(SERVICE_DATA, store)
        assert result is False
        data = store.get_metrics_data()
        assert data["registration_errors_total"] == 1
        assert data["service_registered_status"]["TESTSERVICE"] == 0

    def test_connection_error(self):
        store = MetricsStore()
        with patch("eureka_client_lib.requests.post", side_effect=requests.exceptions.ConnectionError):
            result = register_instance(SERVICE_DATA, store)
        assert result is False
        assert store.get_metrics_data()["registration_errors_total"] == 1

    def test_ssl_preferred_uses_https_urls(self):
        store = MetricsStore()
        ssl_data = {**SERVICE_DATA, "sslPreferred": True, "securePort": 8443}
        mock_resp = MagicMock(status_code=204)
        with patch("eureka_client_lib.requests.post", return_value=mock_resp) as mock_post:
            register_instance(ssl_data, store)
        xml_payload = mock_post.call_args[1]["data"]
        assert "https://" in xml_payload

    def test_no_ssl_uses_http_urls(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=204)
        with patch("eureka_client_lib.requests.post", return_value=mock_resp) as mock_post:
            register_instance(SERVICE_DATA, store)
        xml_payload = mock_post.call_args[1]["data"]
        assert "http://" in xml_payload

    def test_instance_id_format(self):
        """instanceId muss das Format hostname:SERVICENAME:port haben."""
        store = MetricsStore()
        mock_resp = MagicMock(status_code=204)
        with patch("eureka_client_lib.requests.post", return_value=mock_resp) as mock_post:
            register_instance(SERVICE_DATA, store)
        xml_payload = mock_post.call_args[1]["data"]
        assert "localhost:TESTSERVICE:8080" in xml_payload


class TestSendHeartbeat:
    def test_success_200(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=200)
        with patch("eureka_client_lib.requests.put", return_value=mock_resp):
            result = send_heartbeat(SERVICE_DATA, store)
        assert result is True

    def test_404_triggers_reregister_then_succeeds(self):
        store = MetricsStore()
        not_found = MagicMock(status_code=404)
        ok = MagicMock(status_code=200)
        reg_ok = MagicMock(status_code=204)
        with patch("eureka_client_lib.requests.put", side_effect=[not_found, ok]), \
             patch("eureka_client_lib.requests.post", return_value=reg_ok):
            result = send_heartbeat(SERVICE_DATA, store, max_retries=3)
        assert result is True

    def test_connection_error_exhausts_retries(self):
        store = MetricsStore()
        with patch("eureka_client_lib.requests.put", side_effect=requests.exceptions.ConnectionError), \
             patch("eureka_client_lib.time.sleep"):
            result = send_heartbeat(SERVICE_DATA, store, max_retries=2)
        assert result is False

    def test_non_200_non_404_exhausts_retries(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=503, text="Service Unavailable")
        with patch("eureka_client_lib.requests.put", return_value=mock_resp), \
             patch("eureka_client_lib.time.sleep"):
            result = send_heartbeat(SERVICE_DATA, store, max_retries=2)
        assert result is False


class TestDeregisterInstance:
    def test_success_200_clears_status(self):
        store = MetricsStore()
        store.set_service_registered_status("TESTSERVICE", 1)
        mock_resp = MagicMock(status_code=200)
        with patch("eureka_client_lib.requests.delete", return_value=mock_resp):
            deregister_instance(SERVICE_DATA, store)
        assert store.get_metrics_data()["service_registered_status"]["TESTSERVICE"] == 0

    def test_connection_error_does_not_raise(self):
        store = MetricsStore()
        with patch("eureka_client_lib.requests.delete", side_effect=requests.exceptions.ConnectionError):
            deregister_instance(SERVICE_DATA, store)  # darf keine Exception werfen

    def test_non_200_does_not_raise(self):
        store = MetricsStore()
        mock_resp = MagicMock(status_code=404, text="Not Found")
        with patch("eureka_client_lib.requests.delete", return_value=mock_resp):
            deregister_instance(SERVICE_DATA, store)  # darf keine Exception werfen
