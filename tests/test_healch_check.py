from unittest.mock import MagicMock

import pytest
import requests

from healthcheck import health_check


@pytest.fixture
def set_port_env_var(monkeypatch):
    monkeypatch.setenv('PORT', '8000')


# Test for a successful response
def test_check_api_health_success(mocker, set_port_env_var):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_get = mocker.patch('healthcheck.health_check.requests.get',
                            return_value=mock_response)

    result = health_check.check_api_health()
    assert result is True
    mock_get.assert_called_once_with('http://localhost:8000/dota2-gsi/health')


# Test for a failed response
def test_check_api_health_failure(mocker, set_port_env_var):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
    mock_get = mocker.patch('healthcheck.health_check.requests.get',
                            return_value=mock_response)

    result = health_check.check_api_health()
    assert result is False
    mock_get.assert_called_once_with('http://localhost:8000/dota2-gsi/health')


# Test for a request exception
def test_check_api_health_request_exception(mocker, set_port_env_var):
    mock_get = mocker.patch('healthcheck.health_check.requests.get',
                            side_effect=requests.exceptions.RequestException)

    result = health_check.check_api_health()
    assert result is False
    mock_get.assert_called_once_with('http://localhost:8000/dota2-gsi/health')
