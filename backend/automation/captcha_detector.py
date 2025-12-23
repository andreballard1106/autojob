import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


CAPTCHA_INDICATORS = [
    "g-recaptcha",
    "recaptcha",
    "h-captcha",
    "hcaptcha",
    "cf-turnstile",
    "captcha",
    "challenge-form",
    "challenge-running",
    "cf-challenge",
    "arkose",
    "funcaptcha",
]

CAPTCHA_IFRAME_PATTERNS = [
    r"recaptcha.*iframe",
    r"hcaptcha.*iframe",
    r"challenges\.cloudflare",
    r"captcha.*frame",
]

CAPTCHA_TEXT_PATTERNS = [
    r"verify.*human",
    r"verify.*robot",
    r"prove.*human",
    r"not.*robot",
    r"security.*check",
    r"complete.*captcha",
    r"solve.*puzzle",
    r"i.?m not a robot",
    r"confirm.*human",
]

CAPTCHA_ELEMENT_SELECTORS = [
    "[class*='recaptcha']",
    "[class*='g-recaptcha']",
    "[class*='h-captcha']",
    "[class*='captcha']",
    "[id*='captcha']",
    "[data-sitekey]",
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='challenges.cloudflare']",
    ".cf-turnstile",
    "#cf-challenge-running",
    "[class*='challenge']",
]


@dataclass
class CaptchaDetectionResult:
    detected: bool
    captcha_type: str = "unknown"
    confidence: float = 0.0
    selectors_found: List[str] = None
    message: str = ""
    
    def __post_init__(self):
        self.selectors_found = self.selectors_found or []


class CaptchaDetector:
    def __init__(self):
        self._text_patterns = [re.compile(p, re.IGNORECASE) for p in CAPTCHA_TEXT_PATTERNS]
        self._iframe_patterns = [re.compile(p, re.IGNORECASE) for p in CAPTCHA_IFRAME_PATTERNS]
    
    def detect_from_html(self, html_content: str) -> CaptchaDetectionResult:
        if not html_content:
            return CaptchaDetectionResult(detected=False)
        
        html_lower = html_content.lower()
        
        indicators_found = []
        for indicator in CAPTCHA_INDICATORS:
            if indicator in html_lower:
                indicators_found.append(indicator)
        
        text_matches = []
        for pattern in self._text_patterns:
            if pattern.search(html_content):
                text_matches.append(pattern.pattern)
        
        iframe_matches = []
        for pattern in self._iframe_patterns:
            if pattern.search(html_content):
                iframe_matches.append(pattern.pattern)
        
        total_signals = len(indicators_found) + len(text_matches) + len(iframe_matches)
        
        if total_signals == 0:
            return CaptchaDetectionResult(detected=False)
        
        captcha_type = self._determine_type(indicators_found, iframe_matches)
        confidence = min(1.0, total_signals * 0.25)
        
        if any(x in indicators_found for x in ["g-recaptcha", "recaptcha"]):
            confidence = max(confidence, 0.9)
        elif any(x in indicators_found for x in ["h-captcha", "hcaptcha"]):
            confidence = max(confidence, 0.9)
        elif any(x in indicators_found for x in ["cf-turnstile", "cf-challenge"]):
            confidence = max(confidence, 0.85)
        
        return CaptchaDetectionResult(
            detected=confidence >= 0.5,
            captcha_type=captcha_type,
            confidence=confidence,
            selectors_found=indicators_found,
            message=f"CAPTCHA detected: {captcha_type}",
        )
    
    def detect_from_page(self, page) -> CaptchaDetectionResult:
        try:
            detection_js = """
            () => {
                const result = {
                    found: false,
                    type: 'unknown',
                    selectors: [],
                    iframes: [],
                    visible: false
                };
                
                // Check for reCAPTCHA
                const recaptcha = document.querySelector('.g-recaptcha, [data-sitekey], iframe[src*="recaptcha"]');
                if (recaptcha) {
                    result.found = true;
                    result.type = 'recaptcha';
                    result.selectors.push('recaptcha');
                    result.visible = recaptcha.offsetParent !== null;
                }
                
                // Check for hCaptcha
                const hcaptcha = document.querySelector('.h-captcha, iframe[src*="hcaptcha"]');
                if (hcaptcha) {
                    result.found = true;
                    result.type = 'hcaptcha';
                    result.selectors.push('hcaptcha');
                    result.visible = hcaptcha.offsetParent !== null;
                }
                
                // Check for Cloudflare Turnstile
                const turnstile = document.querySelector('.cf-turnstile, #cf-challenge-running, iframe[src*="challenges.cloudflare"]');
                if (turnstile) {
                    result.found = true;
                    result.type = 'cloudflare';
                    result.selectors.push('cloudflare');
                    result.visible = turnstile.offsetParent !== null;
                }
                
                // Check for generic captcha elements
                const generic = document.querySelector('[class*="captcha"], [id*="captcha"]');
                if (generic && !result.found) {
                    result.found = true;
                    result.type = 'generic';
                    result.selectors.push('captcha');
                    result.visible = generic.offsetParent !== null;
                }
                
                // Check for challenge iframes
                const iframes = document.querySelectorAll('iframe');
                iframes.forEach(iframe => {
                    const src = iframe.src || '';
                    if (src.includes('captcha') || src.includes('challenge') || 
                        src.includes('recaptcha') || src.includes('hcaptcha')) {
                        result.iframes.push(src);
                        result.found = true;
                    }
                });
                
                // Check for "I'm not a robot" text
                const bodyText = document.body ? document.body.innerText : '';
                if (/i.?m not a robot|verify.*human|prove.*human/i.test(bodyText)) {
                    result.found = true;
                    if (result.type === 'unknown') {
                        result.type = 'text-based';
                    }
                }
                
                return result;
            }
            """
            
            data = page.evaluate(detection_js)
            
            if data.get("found"):
                return CaptchaDetectionResult(
                    detected=True,
                    captcha_type=data.get("type", "unknown"),
                    confidence=0.95 if data.get("visible") else 0.7,
                    selectors_found=data.get("selectors", []),
                    message=f"CAPTCHA detected via page analysis: {data.get('type')}",
                )
            
            return CaptchaDetectionResult(detected=False)
            
        except Exception as e:
            logger.warning(f"Error during CAPTCHA detection: {e}")
            return CaptchaDetectionResult(detected=False)
    
    def _determine_type(self, indicators: List[str], iframe_patterns: List[str]) -> str:
        indicators_lower = [x.lower() for x in indicators]
        
        if any("recaptcha" in x or "g-recaptcha" in x for x in indicators_lower):
            return "recaptcha"
        if any("hcaptcha" in x or "h-captcha" in x for x in indicators_lower):
            return "hcaptcha"
        if any("cloudflare" in x or "cf-" in x or "turnstile" in x for x in indicators_lower):
            return "cloudflare"
        if any("arkose" in x or "funcaptcha" in x for x in indicators_lower):
            return "arkose"
        if any("recaptcha" in p.lower() for p in iframe_patterns):
            return "recaptcha"
        if any("hcaptcha" in p.lower() for p in iframe_patterns):
            return "hcaptcha"
        return "generic"


captcha_detector = CaptchaDetector()

