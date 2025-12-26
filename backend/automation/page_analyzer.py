import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


KEEP_ATTRIBUTES = {
    'id', 'name', 'type', 'value', 'for', 'href', 'action', 'method',
    'role', 'aria-label', 'data-automation-id', 'data-testid',
    'required', 'checked', 'selected', 'disabled', 'readonly', 'multiple',
    'min', 'max', 'maxlength', 'pattern', 'accept', 'autocomplete',
}

REMOVE_TAGS = {
    'script', 'style', 'noscript', 'svg', 'path', 'meta', 'link',
    'head', 'iframe', 'object', 'embed', 'canvas', 'video', 'audio',
    'source', 'track', 'map', 'area', 'picture', 'template',
}

SELF_CLOSING_TAGS = {
    'input', 'img', 'br', 'hr', 'meta', 'link', 'base', 'col',
    'embed', 'source', 'track', 'wbr', 'area',
}


class HTMLFilter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip_depth = 0
        self.current_tag_stack = []
    
    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        
        if tag_lower in REMOVE_TAGS:
            self.skip_depth += 1
            return
        
        if self.skip_depth > 0:
            return
        
        filtered_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if name_lower in KEEP_ATTRIBUTES:
                if value:
                    filtered_attrs.append(f'{name_lower}="{value}"')
                else:
                    filtered_attrs.append(name_lower)
        
        if filtered_attrs:
            self.result.append(f'<{tag_lower} {" ".join(filtered_attrs)}>')
        else:
            self.result.append(f'<{tag_lower}>')
        
        if tag_lower not in SELF_CLOSING_TAGS:
            self.current_tag_stack.append(tag_lower)
    
    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        
        if tag_lower in REMOVE_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        
        if self.skip_depth > 0:
            return
        
        if tag_lower not in SELF_CLOSING_TAGS:
            if self.current_tag_stack and self.current_tag_stack[-1] == tag_lower:
                self.current_tag_stack.pop()
            self.result.append(f'</{tag_lower}>')
    
    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        
        text = data.strip()
        if text:
            text = re.sub(r'\s+', ' ', text)
            self.result.append(text)
    
    def handle_startendtag(self, tag, attrs):
        tag_lower = tag.lower()
        
        if tag_lower in REMOVE_TAGS or self.skip_depth > 0:
            return
        
        filtered_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if name_lower in KEEP_ATTRIBUTES:
                if value:
                    filtered_attrs.append(f'{name_lower}="{value}"')
                else:
                    filtered_attrs.append(name_lower)
        
        if filtered_attrs:
            self.result.append(f'<{tag_lower} {" ".join(filtered_attrs)}/>')
        else:
            self.result.append(f'<{tag_lower}/>')
    
    def get_filtered_html(self) -> str:
        return ''.join(self.result)


def filter_html(html_content: str) -> str:
    if not html_content:
        return ""
    
    try:
        parser = HTMLFilter()
        parser.feed(html_content)
        filtered = parser.get_filtered_html()
        filtered = re.sub(r'\s+', ' ', filtered)
        filtered = re.sub(r'>\s+<', '><', filtered)
        return filtered.strip()
    except Exception as e:
        logger.error(f"Error filtering HTML: {e}")
        return ""


@dataclass
class PageContent:
    url: str = ""
    title: str = ""
    filtered_html: str = ""
    forms: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "filtered_html": self.filtered_html[:50000] if self.filtered_html else "",
            "forms": self.forms[:10],
            "inputs": self.inputs[:100],
            "buttons": self.buttons[:50],
        }


EXTRACT_JS = """
() => {
    const result = {
        url: window.location.href,
        title: document.title,
        forms: [],
        inputs: [],
        buttons: []
    };
    
    // Extract forms
    document.querySelectorAll('form').forEach((form, i) => {
        if (i >= 10) return;
        result.forms.push({
            index: i,
            id: form.id || '',
            name: form.name || '',
            action: form.action || '',
            method: form.method || 'get'
        });
    });
    
    // Helper to check visibility
    const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && 
               style.visibility !== 'hidden' && 
               style.opacity !== '0' &&
               el.offsetWidth > 0 && 
               el.offsetHeight > 0;
    };
    
    // Helper to find label (enhanced for Workday)
    const findLabel = (el) => {
        // 1. Standard label[for="id"]
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return label.textContent.trim().slice(0, 200);
        }
        
        // 2. Parent label element
        const parentLabel = el.closest('label');
        if (parentLabel) return parentLabel.textContent.trim().slice(0, 200);
        
        // 3. aria-label attribute
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').slice(0, 200);
        
        // 4. aria-labelledby
        const labelledBy = el.getAttribute('aria-labelledby');
        if (labelledBy) {
            const labelEl = document.getElementById(labelledBy);
            if (labelEl) return labelEl.textContent.trim().slice(0, 200);
        }
        
        // 5. Workday-specific: Look for label in parent container
        const container = el.closest('[data-automation-id]') || el.closest('div') || el.parentElement;
        if (container) {
            // Look for label element in container
            const labelInContainer = container.querySelector('label');
            if (labelInContainer && labelInContainer !== el) {
                return labelInContainer.textContent.trim().slice(0, 200);
            }
            
            // Look for Workday formLabel
            const formLabel = container.querySelector('[data-automation-id*="formLabel"], [data-automation-id*="Label"]');
            if (formLabel) return formLabel.textContent.trim().slice(0, 200);
            
            // Look for span/div with label-like class
            const labelSpan = container.querySelector('.label, .form-label, span:first-child');
            if (labelSpan && labelSpan.textContent.trim().length < 100) {
                return labelSpan.textContent.trim().slice(0, 200);
            }
        }
        
        // 6. Previous sibling that might be a label
        const prevSibling = el.previousElementSibling;
        if (prevSibling) {
            const text = prevSibling.textContent.trim();
            // Only use short text as label (avoids paragraphs)
            if (text && text.length > 0 && text.length < 80) {
                return text.slice(0, 200);
            }
        }
        
        // 7. Placeholder as fallback
        if (el.getAttribute('placeholder')) return el.getAttribute('placeholder').slice(0, 200);
        
        return '';
    };
    
    // Extract inputs, textareas, selects
    ['input', 'textarea', 'select'].forEach(tag => {
        document.querySelectorAll(tag).forEach(el => {
            if (result.inputs.length >= 100) return;
            
            const type = el.type || '';
            if (['hidden', 'submit', 'button', 'image', 'reset'].includes(type)) return;
            
            // File inputs are often hidden for styling but still important for automation
            const isFileInput = type === 'file';
            if (!isFileInput && !isVisible(el)) return;
            
            const inputData = {
                tag: tag,
                id: el.id || '',
                name: el.name || '',
                type: type || (tag === 'textarea' ? 'textarea' : tag === 'select' ? 'select' : 'text'),
                label: findLabel(el),
                placeholder: el.getAttribute('placeholder') || '',
                'aria-label': el.getAttribute('aria-label') || '',
                'data-automation-id': el.getAttribute('data-automation-id') || '',
                'data-testid': el.getAttribute('data-testid') || '',
                required: el.required || false,
                value: el.value || '',
                autocomplete: el.getAttribute('autocomplete') || ''
            };
            
            if (tag === 'select') {
                inputData.options = [];
                Array.from(el.options).slice(0, 30).forEach(opt => {
                    if (opt.text.trim()) {
                        inputData.options.push({
                            value: opt.value || '',
                            text: opt.text.trim()
                        });
                    }
                });
            }
            
            result.inputs.push(inputData);
        });
    });
    
    // Extract radio groups (Workday uses custom role="radiogroup" elements)
    document.querySelectorAll('[role="radiogroup"], fieldset:has(input[type="radio"])').forEach(group => {
        if (result.inputs.length >= 100) return;
        if (!isVisible(group)) return;
        
        // Find the question/label for this radio group
        let groupLabel = '';
        const legend = group.querySelector('legend');
        if (legend) {
            groupLabel = legend.textContent.trim();
        } else {
            // Try to find label from aria-label or nearby text
            groupLabel = group.getAttribute('aria-label') || 
                         group.getAttribute('aria-labelledby') || '';
            if (!groupLabel) {
                // Look for preceding label or heading
                const prevEl = group.previousElementSibling;
                if (prevEl && (prevEl.tagName === 'LABEL' || prevEl.tagName === 'P' || prevEl.tagName === 'DIV')) {
                    groupLabel = prevEl.textContent.trim().slice(0, 200);
                }
            }
        }
        
        // Get all radio options
        const options = [];
        group.querySelectorAll('[role="radio"], input[type="radio"], label').forEach(opt => {
            const optText = opt.textContent || opt.getAttribute('aria-label') || opt.value || '';
            if (optText.trim() && !options.includes(optText.trim())) {
                options.push(optText.trim().slice(0, 50));
            }
        });
        
        if (groupLabel || options.length > 0) {
            result.inputs.push({
                tag: 'radiogroup',
                type: 'radiogroup',
                label: groupLabel.slice(0, 200),
                id: group.id || '',
                'data-automation-id': group.getAttribute('data-automation-id') || '',
                options: options.slice(0, 10),
                required: group.hasAttribute('aria-required') || groupLabel.includes('*')
            });
        }
    });
    
    // Also extract individual radio buttons that might not be in a radiogroup
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        if (result.inputs.length >= 100) return;
        if (!isVisible(radio)) return;
        
        const label = findLabel(radio);
        const name = radio.name || '';
        
        // Check if already captured in a radiogroup
        const existingGroup = result.inputs.find(inp => inp.type === 'radiogroup' && inp.label.includes(label));
        if (!existingGroup) {
            result.inputs.push({
                tag: 'input',
                type: 'radio',
                label: label,
                id: radio.id || '',
                name: name,
                value: radio.value || '',
                'data-automation-id': radio.getAttribute('data-automation-id') || '',
                checked: radio.checked
            });
        }
    });
    
    // Extract checkboxes with their labels
    document.querySelectorAll('input[type="checkbox"], [role="checkbox"]').forEach(cb => {
        if (result.inputs.length >= 100) return;
        if (!isVisible(cb)) return;
        
        const label = cb.tagName === 'INPUT' ? findLabel(cb) : (cb.textContent || cb.getAttribute('aria-label') || '');
        
        result.inputs.push({
            tag: 'checkbox',
            type: 'checkbox',
            label: label.slice(0, 200),
            id: cb.id || '',
            'data-automation-id': cb.getAttribute('data-automation-id') || '',
            checked: cb.checked || cb.getAttribute('aria-checked') === 'true',
            required: cb.hasAttribute('required') || cb.hasAttribute('aria-required')
        });
    });
    
    // Extract Workday custom dropdowns (combobox, listbox, custom selects)
    // These are NOT standard <select> elements but custom components
    const workdayDropdownSelectors = [
        '[role="combobox"]',
        '[role="listbox"]',
        '[data-automation-id*="selectInputContainer"]',
        '[data-automation-id*="dropdown"]',
        '[data-automation-id*="Select"]',
        '[data-automation-id*="countryRegion"]',
        '[data-automation-id*="addressSection"]',
        'button[aria-haspopup="listbox"]',
        '[data-automation-id*="formField"] button[aria-expanded]'
    ];
    
    workdayDropdownSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (result.inputs.length >= 100) return;
            if (!isVisible(el)) return;
            
            // Skip if already captured as standard select
            const automationId = el.getAttribute('data-automation-id') || '';
            const existingInput = result.inputs.find(inp => 
                inp['data-automation-id'] === automationId && automationId !== ''
            );
            if (existingInput) return;
            
            // Find label for this dropdown
            let label = '';
            const container = el.closest('[data-automation-id]') || el.parentElement;
            if (container) {
                const labelEl = container.querySelector('label, [data-automation-id*="Label"], [data-automation-id*="formLabel"]');
                if (labelEl) label = labelEl.textContent.trim();
            }
            if (!label) {
                label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || '';
            }
            if (!label) {
                const prevEl = el.previousElementSibling;
                if (prevEl) label = prevEl.textContent.trim();
            }
            
            // Get current value if displayed
            const currentValue = el.textContent.trim() || el.getAttribute('value') || '';
            
            // Check if required (look for asterisk in label or aria-required)
            const isRequired = el.hasAttribute('aria-required') || 
                               el.hasAttribute('required') ||
                               label.includes('*') ||
                               (container && container.textContent.includes('*'));
            
            result.inputs.push({
                tag: 'workday_dropdown',
                type: 'workday_dropdown',
                label: label.slice(0, 200),
                id: el.id || '',
                'data-automation-id': automationId,
                'aria-label': el.getAttribute('aria-label') || '',
                currentValue: currentValue.slice(0, 100),
                required: isRequired,
                // Note: options not available - loaded dynamically via API
                options: []
            });
        });
    });
    
    // Extract buttons with full attributes for AI analysis
    document.querySelectorAll('button, input[type="submit"], input[type="button"], a[role="button"], [role="button"]').forEach(el => {
        if (result.buttons.length >= 50) return;
        if (!isVisible(el)) return;
        
        const text = el.textContent || el.value || el.getAttribute('aria-label') || '';
        const btnData = {
            tag: el.tagName.toLowerCase(),
            id: el.id || '',
            name: el.name || '',
            type: el.type || 'button',
            text: text.trim().slice(0, 100),
            'aria-label': el.getAttribute('aria-label') || '',
            'data-automation-id': el.getAttribute('data-automation-id') || '',
            'data-testid': el.getAttribute('data-testid') || '',
            'class': el.className || ''
        };
        
        // Determine button purpose
        const lowerText = text.toLowerCase().trim();
        if (lowerText.includes('next') || lowerText.includes('continue') || 
            lowerText.includes('save and continue') || lowerText.includes('proceed')) {
            btnData.purpose = 'next';
        } else if (lowerText.includes('submit') || lowerText.includes('apply') || 
                   lowerText.includes('send application') || lowerText.includes('finish')) {
            btnData.purpose = 'submit';
        } else if (lowerText.includes('back') || lowerText.includes('previous')) {
            btnData.purpose = 'back';
        } else if (lowerText.includes('cancel')) {
            btnData.purpose = 'cancel';
        }
        
        result.buttons.push(btnData);
    });
    
    return result;
}
"""


class PageAnalyzer:
    def __init__(self):
        self.page = None
    
    def analyze(self, page) -> PageContent:
        self.page = page
        content = PageContent()
        
        try:
            print(f"  [EXTRACT] Getting page data...")
            
            data = page.evaluate(EXTRACT_JS)
            
            content.url = data.get('url', '')
            content.title = data.get('title', '')
            content.forms = data.get('forms', [])
            content.inputs = data.get('inputs', [])
            content.buttons = data.get('buttons', [])
            
            print(f"  [EXTRACT] URL: {content.url[:60]}...")
            print(f"  [EXTRACT] Title: {content.title[:50]}...")
            print(f"  [EXTRACT] Forms: {len(content.forms)}, Inputs: {len(content.inputs)}, Buttons: {len(content.buttons)}")
            
            # Log some button info to help with debugging
            if content.buttons:
                print(f"  [EXTRACT] Buttons found:")
                for btn in content.buttons[:5]:  # First 5 buttons
                    btn_text = btn.get('text', '')[:30]
                    btn_purpose = btn.get('purpose', 'unknown')
                    print(f"           - '{btn_text}' (purpose: {btn_purpose})")
            
            # Log some input info
            if content.inputs:
                print(f"  [EXTRACT] Input fields found:")
                for inp in content.inputs[:5]:  # First 5 inputs
                    inp_label = inp.get('label', inp.get('name', inp.get('id', 'unknown')))[:30]
                    inp_type = inp.get('type', 'text')
                    print(f"           - '{inp_label}' (type: {inp_type})")
            
            raw_html = page.content()
            print(f"  [EXTRACT] HTML size: {len(raw_html)} chars, filtering...")
            
            content.filtered_html = filter_html(raw_html)
            print(f"  [EXTRACT] Filtered: {len(content.filtered_html)} chars")
            
        except Exception as e:
            print(f"  [EXTRACT ERROR] {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error analyzing page: {e}")
        
        return content
