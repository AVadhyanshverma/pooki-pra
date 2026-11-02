/**
 * In-browser content-aware readability extractor.
 * Converts live DOM into a structured semantic representation for clean GFM markdown generation.
 */
(() => {
    function isVisible(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        if (el.getAttribute('aria-hidden') === 'true') return false;
        const rect = el.getBoundingClientRect();
        return (rect.width > 0 && rect.height > 0) || el.getClientRects().length > 0;
    }

    // Unwanted boilerplate containers
    const BOILERPLATE_SELECTORS = [
        'nav', 'footer', 'noscript', 'script', 'style',
        '#cookie-banner', '.cookie-banner', '#onetrust-banner-sdk',
        '[role="dialog"]', '[role="alertdialog"]', '.modal',
        '.ad', '.advertisement', '[class*="ad-container"]', '[id*="ad-container"]'
    ];

    const BOILERPLATE_QUERY = BOILERPLATE_SELECTORS.join(', ');

    function isBoilerplate(el) {
        try {
            return !!el.closest(BOILERPLATE_QUERY);
        } catch (e) {
            return false;
        }
    }

    function extractTable(tableEl) {
        const rows = [];
        const trs = tableEl.querySelectorAll('tr');
        trs.forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('th, td')).map(td => td.innerText.replace(/\|/g, '\\|').trim());
            if (cells.length > 0 && cells.some(c => c.length > 0)) {
                rows.push(cells);
            }
        });
        return rows;
    }

    function extractContent(mode = 'readability') {
        const title = document.title || document.querySelector('h1')?.innerText || 'Untitled Page';
        const url = window.location.href;

        // Target container
        let root = document.body;
        if (mode === 'readability') {
            const mainCandidate = document.querySelector('article') || document.querySelector('main') || document.querySelector('[role="main"]');
            if (mainCandidate && mainCandidate.innerText.trim().length > 100) {
                root = mainCandidate;
            }
        }

        const candidateNodes = root.querySelectorAll('h1, h2, h3, h4, h5, h6, p, pre, table, ul, ol, blockquote, dt, dd');
        const blocks = [];
        const processedNodes = new Set();

        candidateNodes.forEach(node => {
            if (!isVisible(node)) return;
            if (mode === 'readability' && isBoilerplate(node)) return;
            if (processedNodes.has(node)) return;

            const tag = node.tagName.toLowerCase();
            if (tag.startsWith('h')) {
                const level = parseInt(tag[1]);
                const text = node.innerText.trim();
                if (text) blocks.push({ type: 'heading', level, text });
            } else if (tag === 'p') {
                const text = node.innerText.trim();
                if (text) blocks.push({ type: 'paragraph', text });
            } else if (tag === 'pre') {
                const codeEl = node.querySelector('code');
                const langClass = (codeEl?.className || node.className || '').match(/language-([a-zA-Z0-9_\-]+)/);
                const lang = langClass ? langClass[1] : '';
                const code = (codeEl ? codeEl.innerText : node.innerText).trimEnd();
                if (code) blocks.push({ type: 'code', language: lang, text: code });
                node.querySelectorAll('*').forEach(c => processedNodes.add(c));
            } else if (tag === 'table') {
                const rows = extractTable(node);
                if (rows.length > 0) blocks.push({ type: 'table', rows });
                node.querySelectorAll('*').forEach(c => processedNodes.add(c));
            } else if (tag === 'ul' || tag === 'ol') {
                if (node.parentElement && (node.parentElement.tagName.toLowerCase() === 'li')) return;
                const items = Array.from(node.querySelectorAll(':scope > li')).map(li => li.innerText.trim()).filter(Boolean);
                if (items.length > 0) blocks.push({ type: 'list', ordered: tag === 'ol', items });
                node.querySelectorAll('*').forEach(c => processedNodes.add(c));
            } else if (tag === 'blockquote') {
                const text = node.innerText.trim();
                if (text) blocks.push({ type: 'quote', text });
                node.querySelectorAll('*').forEach(c => processedNodes.add(c));
            } else if (tag === 'dt' || tag === 'dd') {
                const text = node.innerText.trim();
                if (text) blocks.push({ type: 'paragraph', text });
            }
        });

        const totalWords = blocks.reduce((acc, b) => acc + (b.text ? b.text.split(/\s+/).length : 0), 0);

        return {
            title,
            url,
            scraped_at: new Date().toISOString(),
            mode,
            word_count: totalWords,
            blocks
        };
    }

    return JSON.stringify(extractContent(window.__scrape_mode || 'readability'));
})();
