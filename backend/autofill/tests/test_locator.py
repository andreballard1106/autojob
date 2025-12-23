import pytest
from unittest.mock import Mock, patch, MagicMock
from autofill.locator import ElementLocator
from autofill.models import SelectorType
from autofill.exceptions import ElementNotFoundError


class TestElementLocator:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    def test_init(self, mock_driver):
        locator = ElementLocator(mock_driver)
        assert locator.driver == mock_driver
        assert locator._iframe_stack == []
    
    def test_get_by_css(self, locator):
        from selenium.webdriver.common.by import By
        assert locator._get_by(SelectorType.CSS) == By.CSS_SELECTOR
    
    def test_get_by_xpath(self, locator):
        from selenium.webdriver.common.by import By
        assert locator._get_by(SelectorType.XPATH) == By.XPATH
    
    def test_get_by_id(self, locator):
        from selenium.webdriver.common.by import By
        assert locator._get_by(SelectorType.ID) == By.ID
    
    def test_get_by_name(self, locator):
        from selenium.webdriver.common.by import By
        assert locator._get_by(SelectorType.NAME) == By.NAME


class TestElementLocatorFind:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_find_success(self, mock_wait_class, locator, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = locator.find("#email")
        
        assert result == mock_element
        mock_wait_class.assert_called_once()
    
    @patch('autofill.locator.WebDriverWait')
    def test_find_not_found_raises(self, mock_wait_class, locator):
        mock_wait = Mock()
        mock_wait.until.side_effect = Exception("Not found")
        mock_wait_class.return_value = mock_wait
        
        with pytest.raises(ElementNotFoundError):
            locator.find("#nonexistent")
    
    @patch('autofill.locator.WebDriverWait')
    def test_find_not_found_no_raise(self, mock_wait_class, locator):
        mock_wait = Mock()
        mock_wait.until.side_effect = Exception("Not found")
        mock_wait_class.return_value = mock_wait
        
        result = locator.find("#nonexistent", raise_on_not_found=False)
        
        assert result is None


class TestElementLocatorFindClickable:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_find_clickable_success(self, mock_wait_class, locator, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = locator.find_clickable("#button")
        
        assert result == mock_element


class TestElementLocatorFindVisible:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_find_visible_success(self, mock_wait_class, locator, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = locator.find_visible("#input")
        
        assert result == mock_element


class TestElementLocatorFindAll:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    def test_find_all(self, locator, mock_driver, mock_element):
        mock_driver.find_elements.return_value = [mock_element, mock_element]
        
        result = locator.find_all(".item")
        
        assert len(result) == 2


class TestElementLocatorWaitMethods:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_wait_for_visible_true(self, mock_wait_class, locator, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = locator.wait_for_visible("#element")
        
        assert result == True
    
    @patch('autofill.locator.WebDriverWait')
    def test_wait_for_visible_false(self, mock_wait_class, locator):
        mock_wait = Mock()
        mock_wait.until.side_effect = Exception("Timeout")
        mock_wait_class.return_value = mock_wait
        
        result = locator.wait_for_visible("#element")
        
        assert result == False
    
    @patch('autofill.locator.WebDriverWait')
    def test_wait_for_hidden(self, mock_wait_class, locator):
        mock_wait = Mock()
        mock_wait.until.return_value = True
        mock_wait_class.return_value = mock_wait
        
        result = locator.wait_for_hidden("#loading")
        
        assert result == True
    
    @patch('autofill.locator.WebDriverWait')
    def test_wait_for_clickable(self, mock_wait_class, locator, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = locator.wait_for_clickable("#button")
        
        assert result == True


class TestElementLocatorScrollMethods:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    def test_scroll_into_view(self, locator, mock_driver, mock_element):
        locator.scroll_into_view(mock_element)
        
        mock_driver.execute_script.assert_called()
    
    def test_scroll_to_top(self, locator, mock_driver):
        locator.scroll_to_top()
        
        mock_driver.execute_script.assert_called_with("window.scrollTo(0, 0);")
    
    def test_scroll_to_bottom(self, locator, mock_driver):
        locator.scroll_to_bottom()
        
        mock_driver.execute_script.assert_called()


class TestElementLocatorHelpers:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    def test_is_visible_true(self, locator, mock_element):
        mock_element.is_displayed.return_value = True
        
        assert locator.is_visible(mock_element) == True
    
    def test_is_visible_false(self, locator, mock_element):
        mock_element.is_displayed.return_value = False
        
        assert locator.is_visible(mock_element) == False
    
    def test_is_enabled_true(self, locator, mock_element):
        mock_element.is_enabled.return_value = True
        
        assert locator.is_enabled(mock_element) == True
    
    def test_is_enabled_false(self, locator, mock_element):
        mock_element.is_enabled.return_value = False
        
        assert locator.is_enabled(mock_element) == False
    
    def test_get_element_info(self, locator, mock_element):
        mock_element.tag_name = "input"
        mock_element.get_attribute.side_effect = lambda attr: {
            "id": "email",
            "name": "user_email",
            "type": "email",
            "value": "test@example.com",
        }.get(attr)
        mock_element.text = ""
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        mock_element.is_selected.return_value = False
        
        info = locator.get_element_info(mock_element)
        
        assert info["tag"] == "input"
        assert info["id"] == "email"
        assert info["visible"] == True


class TestElementLocatorIframe:
    @pytest.fixture
    def locator(self, mock_driver):
        return ElementLocator(mock_driver)
    
    def test_exit_iframe(self, locator, mock_driver):
        locator._iframe_stack = [Mock()]
        
        locator.exit_iframe()
        
        assert len(locator._iframe_stack) == 0
        mock_driver.switch_to.default_content.assert_called()
    
    def test_exit_all_iframes(self, locator, mock_driver):
        locator._iframe_stack = [Mock(), Mock()]
        
        locator.exit_all_iframes()
        
        assert len(locator._iframe_stack) == 0
        mock_driver.switch_to.default_content.assert_called()

