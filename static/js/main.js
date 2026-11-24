/**
 * ANNADATA AI — Platform Client Scripts
 * Handles Lucide icons, AI Assistant Chat, Dynamic Map Interactivity, and UI Enhancements.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // 2. Initialize Floating AI Assistant
    initAssistant();

    // 3. Confirm Delete / Logout Dialogs
    initConfirmations();

    // 4. Auto-dismiss flash alerts after 5 seconds
    initAutoDismissAlerts();
});

function initAssistant() {
    const trigger = document.getElementById('assistantTrigger');
    const panel = document.getElementById('assistantPanel');
    const closeBtn = document.getElementById('assistantClose');
    const sendBtn = document.getElementById('assistantSend');
    const input = document.getElementById('assistantInput');
    const messages = document.getElementById('assistantMessages');

    if (!trigger || !panel) return;

    trigger.addEventListener('click', () => {
        const isVisible = panel.style.display === 'flex';
        panel.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible && input) {
            input.focus();
            if (window.lucide) window.lucide.createIcons();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            panel.style.display = 'none';
        });
    }

    function appendMessage(text, isUser = false, meta = null) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${isUser ? 'user' : 'assistant'}`;
        
        // Simple markdown parsing for bold / bullet points
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/• (.*?)(?=\n|$)/g, '<li>$1</li>');
        
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*?<\/li>)/g, '<ul class="ps-3 mb-1">$1</ul>');
        }

        bubble.innerHTML = formatted;
        
        if (meta && !isUser) {
            const src = document.createElement('div');
            src.className = 'mt-1 text-muted';
            src.style.fontSize = '0.7rem';
            src.textContent = `⚡ ${meta}`;
            bubble.appendChild(src);
        }

        messages.appendChild(bubble);
        messages.scrollTop = messages.scrollHeight;
    }

    async function handleSend() {
        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, true);
        input.value = '';

        // Show typing indicator
        const typing = document.createElement('div');
        typing.className = 'chat-bubble assistant text-muted';
        typing.id = 'assistantTyping';
        typing.textContent = 'Thinking...';
        messages.appendChild(typing);
        messages.scrollTop = messages.scrollHeight;

        try {
            const resp = await fetch('/api/assistant/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await resp.json();
            const typingElem = document.getElementById('assistantTyping');
            if (typingElem) typingElem.remove();

            if (data.answer) {
                appendMessage(data.answer, false, data.source);
            } else {
                appendMessage('I was unable to retrieve an answer at this time. Please try again.', false);
            }
        } catch (err) {
            const typingElem = document.getElementById('assistantTyping');
            if (typingElem) typingElem.remove();
            appendMessage('Connection error. Operating in offline mode.', false);
        }
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', handleSend);
    }

    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSend();
            }
        });
    }

    // Quick prompt buttons
    document.querySelectorAll('.prompt-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            if (input) {
                input.value = pill.textContent.trim();
                handleSend();
            }
        });
    });
}

function initConfirmations() {
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            const msg = el.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            if (!confirm(msg)) {
                e.preventDefault();
            }
        });
    });
}

function initAutoDismissAlerts() {
    setTimeout(() => {
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {}
        });
    }, 6000);
}
