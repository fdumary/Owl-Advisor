document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const floatingOwl = document.getElementById('floating-owl');
    const chatContainer = document.getElementById('chat-container');
    const hero = document.getElementById('hero');

    // Handle floating owl click
    floatingOwl.addEventListener('click', () => {
        floatingOwl.classList.add('fade-out');
        
        setTimeout(() => {
            floatingOwl.classList.add('hidden');
            chatContainer.classList.remove('hidden');
            // Optional: hide or shrink hero for more space
            if (hero) {
                hero.style.height = '0';
                hero.style.opacity = '0';
                hero.style.margin = '0';
                hero.style.overflow = 'hidden';
            }
            userInput.focus();
        }, 500); // Matches CSS transition duration
    });
    
    // Handle back button click
    const closeChatBtn = document.getElementById('close-chat-btn');
    if (closeChatBtn) {
        closeChatBtn.addEventListener('click', () => {
            chatContainer.classList.add('hidden');
            floatingOwl.classList.remove('hidden');
            
            // Short delay to let browser process display block before opacity transition
            setTimeout(() => {
                floatingOwl.classList.remove('fade-out');
                if (hero) {
                    hero.style.height = 'auto';
                    hero.style.opacity = '1';
                    hero.style.margin = '0 0 20px 0';
                }
            }, 50);
        });
    }

    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar';
        avatarDiv.innerHTML = isUser ? '👤' : '🦉';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'text';
        
        // Simple markdown parsing for bold text
        const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        textDiv.innerHTML = formattedText;
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(textDiv);
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;
        
        // Add user message
        addMessage(text, true);
        userInput.value = '';
        
        // Add typing indicator
        const typingId = 'typing-' + Date.now();
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message';
        typingDiv.id = typingId;
        typingDiv.innerHTML = `
            <div class="avatar">🦉</div>
            <div class="text">
                <span class="typing-dot">.</span>
                <span class="typing-dot">.</span>
                <span class="typing-dot">.</span>
            </div>
        `;
        chatBox.appendChild(typingDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
        
        // Attempt to get user location
        let lat = null;
        let lon = null;
        
        const getLocation = () => new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve();
            } else {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        lat = position.coords.latitude;
                        lon = position.coords.longitude;
                        resolve();
                    },
                    (error) => {
                        console.warn('Geolocation error:', error);
                        resolve();
                    },
                    { timeout: 3000 } // only wait 3 seconds for location so chat doesn't lag
                );
            }
        });
        
        await getLocation();
        
        // Call backend API
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text, lat: lat, lon: lon })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            document.getElementById(typingId).remove();
            
            // Add AI response
            addMessage(data.response);
        } catch (error) {
            console.error('Error:', error);
            document.getElementById(typingId).remove();
            addMessage("Sorry, I'm having trouble connecting to the server right now.");
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
