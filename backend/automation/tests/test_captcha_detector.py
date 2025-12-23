import pytest
from unittest.mock import Mock, patch

from automation.captcha_detector import (
    CaptchaDetector,
    CaptchaDetectionResult,
    CAPTCHA_INDICATORS,
)


class TestCaptchaDetectionResult:
    def test_default_values(self):
        result = CaptchaDetectionResult(detected=False)
        
        assert result.detected == False
        assert result.captcha_type == "unknown"
        assert result.confidence == 0.0
        assert result.selectors_found == []
    
    def test_with_values(self):
        result = CaptchaDetectionResult(
            detected=True,
            captcha_type="recaptcha",
            confidence=0.95,
            selectors_found=["g-recaptcha"],
            message="CAPTCHA detected",
        )
        
        assert result.detected == True
        assert result.captcha_type == "recaptcha"
        assert result.confidence == 0.95


class TestCaptchaDetectorFromHtml:
    @pytest.fixture
    def detector(self):
        return CaptchaDetector()
    
    def test_no_captcha(self, detector):
        html = "<form><input type='text' name='email'><button>Submit</button></form>"
        
        result = detector.detect_from_html(html)
        
        assert result.detected == False
    
    def test_detect_recaptcha_class(self, detector):
        html = """
        <form>
            <div class="g-recaptcha" data-sitekey="xyz"></div>
            <button>Submit</button>
        </form>
        """
        
        result = detector.detect_from_html(html)
        
        assert result.detected == True
        assert result.captcha_type == "recaptcha"
        assert result.confidence >= 0.9
    
    def test_detect_hcaptcha(self, detector):
        html = """
        <form>
            <div class="h-captcha" data-sitekey="xyz"></div>
        </form>
        """
        
        result = detector.detect_from_html(html)
        
        assert result.detected == True
        assert result.captcha_type == "hcaptcha"
    
    def test_detect_cloudflare(self, detector):
        html = """
        <div id="cf-challenge-running">
            <div class="cf-turnstile"></div>
        </div>
        """
        
        result = detector.detect_from_html(html)
        
        assert result.detected == True
        assert result.captcha_type == "cloudflare"
    
    def test_detect_by_text(self, detector):
        html = """
        <div>
            <p>Please verify you're not a robot</p>
            <div class="challenge-form"></div>
        </div>
        """
        
        result = detector.detect_from_html(html)
        
        assert result.detected == True
    
    def test_detect_recaptcha_iframe(self, detector):
        html = """
        <iframe src="https://www.google.com/recaptcha/api2/anchor"></iframe>
        """
        
        result = detector.detect_from_html(html)
        
        assert result.detected == True
        assert result.captcha_type == "recaptcha"
    
    def test_empty_html(self, detector):
        result = detector.detect_from_html("")
        
        assert result.detected == False
    
    def test_none_html(self, detector):
        result = detector.detect_from_html(None)
        
        assert result.detected == False


class TestCaptchaDetectorFromPage:
    @pytest.fixture
    def detector(self):
        return CaptchaDetector()
    
    def test_detect_recaptcha_from_page(self, detector):
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "found": True,
            "type": "recaptcha",
            "selectors": ["recaptcha"],
            "iframes": [],
            "visible": True,
        }
        
        result = detector.detect_from_page(mock_page)
        
        assert result.detected == True
        assert result.captcha_type == "recaptcha"
        assert result.confidence >= 0.9
    
    def test_no_captcha_from_page(self, detector):
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "found": False,
            "type": "unknown",
            "selectors": [],
            "iframes": [],
            "visible": False,
        }
        
        result = detector.detect_from_page(mock_page)
        
        assert result.detected == False
    
    def test_detect_hidden_captcha(self, detector):
        mock_page = Mock()
        mock_page.evaluate.return_value = {
            "found": True,
            "type": "recaptcha",
            "selectors": ["recaptcha"],
            "iframes": [],
            "visible": False,
        }
        
        result = detector.detect_from_page(mock_page)
        
        assert result.detected == True
        assert result.confidence < 0.9
    
    def test_page_evaluate_error(self, detector):
        mock_page = Mock()
        mock_page.evaluate.side_effect = Exception("Page error")
        
        result = detector.detect_from_page(mock_page)
        
        assert result.detected == False


class TestCaptchaTypeDetection:
    @pytest.fixture
    def detector(self):
        return CaptchaDetector()
    
    def test_determine_recaptcha(self, detector):
        captcha_type = detector._determine_type(["g-recaptcha", "captcha"], [])
        assert captcha_type == "recaptcha"
    
    def test_determine_hcaptcha(self, detector):
        captcha_type = detector._determine_type(["h-captcha"], [])
        assert captcha_type == "hcaptcha"
    
    def test_determine_cloudflare(self, detector):
        captcha_type = detector._determine_type(["cf-turnstile"], [])
        assert captcha_type == "cloudflare"
    
    def test_determine_arkose(self, detector):
        captcha_type = detector._determine_type(["arkose"], [])
        assert captcha_type == "arkose"
    
    def test_determine_generic(self, detector):
        captcha_type = detector._determine_type(["captcha"], [])
        assert captcha_type == "generic"

