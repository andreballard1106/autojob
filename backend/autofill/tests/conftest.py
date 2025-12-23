import pytest
from unittest.mock import Mock, MagicMock, PropertyMock
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


@pytest.fixture
def mock_element():
    element = Mock(spec=WebElement)
    element.tag_name = "input"
    element.text = ""
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    element.is_selected.return_value = False
    element.get_attribute.return_value = None
    element.find_element.return_value = None
    element.find_elements.return_value = []
    element.click.return_value = None
    element.clear.return_value = None
    element.send_keys.return_value = None
    return element


@pytest.fixture
def mock_select_element(mock_element):
    mock_element.tag_name = "select"
    
    option1 = Mock(spec=WebElement)
    option1.get_attribute.side_effect = lambda attr: "us" if attr == "value" else None
    option1.text = "United States"
    
    option2 = Mock(spec=WebElement)
    option2.get_attribute.side_effect = lambda attr: "uk" if attr == "value" else None
    option2.text = "United Kingdom"
    
    mock_element.find_elements.return_value = [option1, option2]
    
    return mock_element


@pytest.fixture
def mock_checkbox_element(mock_element):
    mock_element.tag_name = "input"
    mock_element.get_attribute.side_effect = lambda attr: "checkbox" if attr == "type" else None
    return mock_element


@pytest.fixture
def mock_radio_element(mock_element):
    mock_element.tag_name = "input"
    mock_element.get_attribute.side_effect = lambda attr: {
        "type": "radio",
        "name": "gender",
        "value": "male",
    }.get(attr)
    return mock_element


@pytest.fixture
def mock_file_element(mock_element):
    mock_element.tag_name = "input"
    mock_element.get_attribute.side_effect = lambda attr: "file" if attr == "type" else None
    return mock_element


@pytest.fixture
def mock_driver(mock_element):
    driver = Mock(spec=WebDriver)
    driver.find_element.return_value = mock_element
    driver.find_elements.return_value = [mock_element]
    driver.execute_script.return_value = None
    driver.switch_to = Mock()
    driver.switch_to.frame.return_value = None
    driver.switch_to.default_content.return_value = None
    driver.switch_to.active_element = mock_element
    return driver


@pytest.fixture
def mock_driver_with_wait(mock_driver, mock_element):
    from selenium.webdriver.support.ui import WebDriverWait
    
    def mock_until(condition):
        return mock_element
    
    return mock_driver


class MockWebDriverWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout
        self._element = None
    
    def until(self, condition):
        if self._element:
            return self._element
        elements = self.driver.find_elements("css", "test")
        if elements:
            return elements[0]
        raise Exception("Element not found")
    
    def set_element(self, element):
        self._element = element


@pytest.fixture
def sample_commands():
    return {
        "type_text": {
            "action": "type_text",
            "selector": "#email",
            "value": "test@example.com",
        },
        "type_number": {
            "action": "type_number",
            "selector": "#age",
            "value": 25,
        },
        "select_option": {
            "action": "select_option",
            "selector": "#country",
            "value": "US",
            "select_by": "value",
        },
        "check": {
            "action": "check",
            "selector": "#agree",
            "checked": True,
        },
        "select_radio": {
            "action": "select_radio",
            "name": "gender",
            "value": "male",
        },
        "upload_file": {
            "action": "upload_file",
            "selector": "#resume",
            "file_path": "/tmp/test.pdf",
        },
        "enter_date": {
            "action": "enter_date",
            "selector": "#start_date",
            "value": "2024-01-15",
        },
        "click": {
            "action": "click",
            "selector": "#submit",
        },
        "wait": {
            "action": "wait",
            "time_ms": 1000,
        },
        "press_key": {
            "action": "press_key",
            "key": "enter",
        },
    }

