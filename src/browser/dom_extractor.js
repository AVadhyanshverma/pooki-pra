(() => {
    const actions = [];
    let idCounter = 1;
    
    function isVisible(el) {
        if (!el.getBoundingClientRect) return false;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0') return false;
        return true;
    }

    function getLabel(el) {
        return el.getAttribute('aria-label') ||
               el.getAttribute('placeholder') ||
               el.getAttribute('title') ||
               el.getAttribute('alt') ||
               (el.innerText ? el.innerText.trim() : '') ||
               (el.value ? el.value.trim() : '') ||
               '';
    }

    const elements = document.querySelectorAll(
        'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="menuitem"], [role="tab"], [role="searchbox"], [contenteditable="true"]'
    );

    elements.forEach(el => {
        if (!isVisible(el)) return;
        
        const tagName = el.tagName.toLowerCase();
        const type = (el.getAttribute('type') || '').toLowerCase();
        let kind = 'click';
        let role = el.getAttribute('role') || tagName;
        
        if (tagName === 'input') {
            if (['text', 'search', 'email', 'password', 'url', 'tel', 'number'].includes(type) || !type) {
                kind = 'fill';
                role = role || 'textbox';
            } else if (['checkbox', 'radio'].includes(type)) {
                kind = 'click';
                role = type;
            }
        } else if (tagName === 'textarea') {
            kind = 'fill';
            role = 'textbox';
        } else if (tagName === 'select') {
            kind = 'select';
            role = 'combobox';
        }

        const agentId = 'e' + (idCounter++);
        el.setAttribute('data-agent-id', agentId);
        
        const actionItem = {
            id: agentId,
            kind: kind,
            node: agentId,
            label: (getLabel(el) || tagName).slice(0, 80),
            role: role
        };

        if (kind === 'fill' || kind === 'select') {
            actionItem.value = el.value || '';
        }
        if (el.hasAttribute('checked') || el.checked) {
            actionItem.checked = Boolean(el.checked);
        }
        if (el.hasAttribute('aria-expanded')) {
            actionItem.expanded = el.getAttribute('aria-expanded') === 'true';
        }

        actions.push(actionItem);
    });

    actions.push({ id: "scroll_down", kind: "scroll", label: "Scroll down" });
    actions.push({ id: "scroll_up", kind: "scroll", label: "Scroll up" });

    const pageText = (document.body ? document.body.innerText : '')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 1200);

    return {
        url: window.location.href,
        title: document.title || '',
        text: pageText,
        actions: actions
    };
})();
