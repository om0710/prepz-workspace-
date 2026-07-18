// Auto-bypass ngrok browser warning pages and redirect API calls to local ngrok backend
const originalFetch = window.fetch;
const API_BASE_URL = "https://credible-fleshed-refinish.ngrok-free.dev";

window.fetch = function (url, options = {}) {
    options.headers = options.headers || {};
    if (options.headers instanceof Headers) {
        options.headers.set("ngrok-skip-browser-warning", "69420");
    } else {
        options.headers["ngrok-skip-browser-warning"] = "69420";
    }
    
    // Direct API route mapping to skip proxy issues
    if (typeof url === "string" && url.startsWith("/")) {
        url = API_BASE_URL + url;
    }
    
    return originalFetch(url, options);
};

function initializeDocPilotApp() {
    // Primary View Containers
    const chatbotAppView = document.getElementById("chatbot-app-view");
    const contentWrapper = document.querySelector(".content-wrapper");
    const landingPageView = document.getElementById("landing-page-view");
    
    // Gmail Auth Elements
    const loginBtn = document.getElementById("btn-google-login");
    const userAvatar = document.querySelector(".sidebar-user-avatar");
    const userName = document.querySelector(".sidebar-user-name");
    const userEmail = document.querySelector(".sidebar-user-email");
    const logoutBtn = document.querySelector(".sidebar-user");

    // Core Chat Elements
    const chatMessages = document.getElementById("chat-messages");
    const chatMessagesContainer = document.getElementById("chat-messages-container");
    const landingContainer = document.getElementById("landing-container");
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const threadsList = document.getElementById("threads-list");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");
    const indexedFilesList = document.getElementById("indexed-files-list");
    
    // Navbar Elements & Interactive Triggers
    const navNewChat = document.getElementById("nav-new-chat");
    const navNewChatBtn = document.getElementById("nav-new-chat-btn");
    const headerNewChatBtn = document.getElementById("btn-header-new-chat");
    const uploadZone = document.getElementById("upload-zone");
    const librarySearchInput = document.getElementById("library-search-input");
    
    const btnInputPlus = document.getElementById("btn-input-plus");
    const btnToggleSearch = document.getElementById("btn-toggle-search");
    const btnInputVoice = document.getElementById("btn-input-voice");
    const btnSubmit = document.getElementById("btn-submit");

    // Settings Dropdown Elements
    const btnHeaderSettings = document.getElementById("btn-header-settings");
    const btnHeaderBack = document.getElementById("btn-header-back");
    const settingsDropdown = document.getElementById("settings-dropdown");
    const btnSettingsPin = document.getElementById("btn-settings-pin");
    const labelSettingsPin = document.getElementById("label-settings-pin");
    const btnSettingsArchive = document.getElementById("btn-settings-archive");
    const btnSettingsDelete = document.getElementById("btn-settings-delete");

    // Local State Variables
    let currentThreadId = localStorage.getItem("currentThreadId") || null;
    let isWebSearchEnabled = false;
    let isRecording = false;
    let speechRecognition = null;

    let isCurrentPinned = false;
    let isCurrentArchived = false;

    // ----------------------------------------------------
    // Authentication Manager
    // ----------------------------------------------------
    function initAuth() {
        if (loginBtn) {
            loginBtn.addEventListener("click", () => {
                const width = 500;
                const height = 600;
                const left = (screen.width / 2) - (width / 2);
                const top = (screen.height / 2) - (height / 2);
                window.open('/static/login_popup.html', 'Google Sign-In', `width=${width},height=${height},left=${left},top=${top}`);
            });
        }

        window.addEventListener("message", (e) => {
            if (e.data && e.data.type === "google-login-success") {
                loginUser(e.data.user);
            }
        });

        window.addEventListener("storage", (e) => {
            if (e.key === "google-login-success-event" && e.newValue) {
                try {
                    const data = JSON.parse(e.newValue);
                    if (data && data.user) {
                        loginUser(data.user);
                        localStorage.removeItem("google-login-success-event");
                    }
                } catch(err) {}
            }
        });

        if (logoutBtn) {
            logoutBtn.addEventListener("click", () => {
                logoutUser();
            });
        }

        // Check if session user details are already saved
        const savedUser = localStorage.getItem("docpilot-user");
        if (savedUser) {
            try {
                loginUser(JSON.parse(savedUser));
            } catch(e) {
                showLoginScreen();
            }
        } else {
            showLoginScreen();
        }
    }

    function showLoginScreen() {
        if (landingPageView) landingPageView.style.display = "flex";
        if (chatbotAppView) chatbotAppView.style.display = "none";
    }

    function loginUser(user) {
        localStorage.setItem("docpilot-user", JSON.stringify(user));
        if (userAvatar) userAvatar.src = user.picture || "https://api.dicebear.com/7.x/bottts/svg?seed=Om";
        if (userName) userName.textContent = user.name || "Om Bansal";
        if (userEmail) userEmail.textContent = user.email || "ombansal221@gmail.com";

        if (landingPageView) landingPageView.style.display = "none";
        if (chatbotAppView) chatbotAppView.style.display = "flex";

        // Fetch folders and threads
        fetchThreads();
        fetchIndexedFiles();

        if (currentThreadId) {
            loadThreadHistory(currentThreadId);
        } else {
            showLandingState();
        }
    }

    function logoutUser() {
        localStorage.removeItem("docpilot-user");
        localStorage.removeItem("currentThreadId");
        currentThreadId = null;
        chatMessages.innerHTML = "";
        showLoginScreen();
    }

    // ----------------------------------------------------
    // Search Filtering
    // ----------------------------------------------------
    function initSearchFilter() {
        if (librarySearchInput) {
            librarySearchInput.addEventListener("input", () => {
                const query = librarySearchInput.value.toLowerCase().trim();
                const items = threadsList.querySelectorAll(".thread-item");
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(query) ? "flex" : "none";
                });
            });
        }
    }

    // ----------------------------------------------------
    // Suggestions Flow
    // ----------------------------------------------------
    function initSuggestions() {
        document.querySelectorAll(".suggestion-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                const text = pill.dataset.prompt;
                userInput.value = text;
                userInput.focus();
                userInput.dispatchEvent(new Event("input"));
                chatForm.dispatchEvent(new Event("submit"));
            });
        });
    }

    // ----------------------------------------------------
    // Input Box Autoresize
    // ----------------------------------------------------
    function initInputAutoresize() {
        if (userInput) {
            userInput.addEventListener("input", () => {
                userInput.style.height = "auto";
                userInput.style.height = (userInput.scrollHeight) + "px";
            });

            userInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    chatForm.dispatchEvent(new Event("submit"));
                }
            });
        }
    }

    // ----------------------------------------------------
    // Web Search Toggle
    // ----------------------------------------------------
    if (btnToggleSearch) {
        btnToggleSearch.addEventListener("click", () => {
            isWebSearchEnabled = !isWebSearchEnabled;
            btnToggleSearch.classList.toggle("active", isWebSearchEnabled);
        });
    }

    // ----------------------------------------------------
    // Speech Recognition (Voice Input)
    // ----------------------------------------------------
    function initVoiceRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition || !btnInputVoice) return;

        speechRecognition = new SpeechRecognition();
        speechRecognition.continuous = false;
        speechRecognition.interimResults = false;
        speechRecognition.lang = 'en-US';

        speechRecognition.onstart = () => {
            isRecording = true;
            btnInputVoice.classList.add("recording");
            const label = btnInputVoice.querySelector("span");
            if (label) label.textContent = "Listening...";
        };

        speechRecognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript) {
                const currentVal = userInput.value;
                userInput.value = currentVal + (currentVal ? " " : "") + transcript;
                userInput.dispatchEvent(new Event("input"));
            }
        };

        speechRecognition.onerror = () => stopRecording();
        speechRecognition.onend = () => stopRecording();

        btnInputVoice.addEventListener("click", () => {
            if (isRecording) {
                speechRecognition.stop();
            } else {
                speechRecognition.start();
            }
        });
    }

    function stopRecording() {
        isRecording = false;
        if (btnInputVoice) {
            btnInputVoice.classList.remove("recording");
            const label = btnInputVoice.querySelector("span");
            if (label) label.textContent = "Voice";
        }
    }

    // ----------------------------------------------------
    // Settings Dropdown Operations
    // ----------------------------------------------------
    function initSettingsMenu() {
        if (btnHeaderSettings && settingsDropdown) {
            btnHeaderSettings.addEventListener("click", (e) => {
                e.stopPropagation();
                settingsDropdown.classList.toggle("hidden");
            });
        }

        document.addEventListener("click", (e) => {
            if (settingsDropdown && !settingsDropdown.classList.contains("hidden")) {
                const container = document.querySelector(".settings-container");
                if (container && !container.contains(e.target)) {
                    settingsDropdown.classList.add("hidden");
                }
            }
        });

        if (btnSettingsPin) {
            btnSettingsPin.addEventListener("click", async () => {
                if (!currentThreadId) return;
                settingsDropdown.classList.add("hidden");
                const nextState = !isCurrentPinned;
                try {
                    const res = await fetch(`/thread/${currentThreadId}/pin`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ is_pinned: nextState })
                    });
                    if (res.ok) {
                        isCurrentPinned = nextState;
                        if (labelSettingsPin) {
                            labelSettingsPin.textContent = isCurrentPinned ? "Unpin Chat" : "Pin Chat";
                        }
                        fetchThreads();
                    }
                } catch (err) {
                    console.error("Error setting pin:", err);
                }
            });
        }

        if (btnSettingsArchive) {
            btnSettingsArchive.addEventListener("click", async () => {
                if (!currentThreadId) return;
                settingsDropdown.classList.add("hidden");
                try {
                    const res = await fetch(`/thread/${currentThreadId}/archive`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ is_archived: true })
                    });
                    if (res.ok) {
                        showLandingState();
                        fetchThreads();
                    }
                } catch (err) {
                    console.error("Error archiving:", err);
                }
            });
        }

        if (btnSettingsDelete) {
            btnSettingsDelete.addEventListener("click", async () => {
                if (!currentThreadId) return;
                settingsDropdown.classList.add("hidden");
                if (confirm("Are you sure you want to delete this conversation completely?")) {
                    try {
                        const res = await fetch(`/thread/${currentThreadId}`, {
                            method: "DELETE"
                        });
                        if (res.ok) {
                            showLandingState();
                            fetchThreads();
                        }
                    } catch (err) {
                        console.error("Error deleting:", err);
                    }
                }
            });
        }
    }

    // ----------------------------------------------------
    // UI Layout States & Scrolling
    // ----------------------------------------------------
    function showLandingState() {
        currentThreadId = null;
        localStorage.removeItem("currentThreadId");
        
        chatMessagesContainer.classList.add("hidden");
        landingContainer.classList.remove("hidden");
        
        if (contentWrapper) {
            contentWrapper.classList.add("landing-mode");
            contentWrapper.classList.remove("chat-mode");
        }

        if (btnHeaderSettings) {
            btnHeaderSettings.style.display = "none";
        }
        if (btnHeaderBack) {
            btnHeaderBack.style.display = "none";
        }
        
        chatMessages.innerHTML = "";
        userInput.value = "";
        userInput.style.height = "auto";
    }

    function showChatState() {
        landingContainer.classList.add("hidden");
        chatMessagesContainer.classList.remove("hidden");
        
        if (contentWrapper) {
            contentWrapper.classList.remove("landing-mode");
            contentWrapper.classList.add("chat-mode");
        }

        if (btnHeaderSettings) {
            btnHeaderSettings.style.display = "flex";
        }
        if (btnHeaderBack) {
            btnHeaderBack.style.display = "flex";
        }
        scrollToBottom();
    }

    function scrollToBottom() {
        setTimeout(() => {
            if (chatMessagesContainer) {
                chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
            }
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }, 50);
    }

    // New Chat Bindings
    if (navNewChat) {
        navNewChat.addEventListener("click", (e) => {
            e.preventDefault();
            showLandingState();
        });
    }
    if (navNewChatBtn) {
        navNewChatBtn.addEventListener("click", (e) => {
            e.preventDefault();
            showLandingState();
        });
    }
    if (headerNewChatBtn) {
        headerNewChatBtn.addEventListener("click", () => {
            showLandingState();
        });
    }

    // ----------------------------------------------------
    // Chat Backend API Communications
    // ----------------------------------------------------
    async function fetchThreads() {
        try {
            const res = await fetch("/threads");
            const data = await res.json();
            threadsList.innerHTML = "";
            
            const threads = data.threads || [];
            if (threads.length === 0) {
                threadsList.innerHTML = `<li class="file-item-empty">No active chats</li>`;
                return;
            }

            threads.forEach(thread => {
                const li = document.createElement("li");
                li.className = `thread-item ${thread.thread_id === currentThreadId ? "active" : ""}`;
                
                li.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    <span>${thread.title}</span>
                    ${thread.is_pinned ? `<span class="pin-badge" style="margin-left:auto; font-size:10px;">📌</span>` : ""}
                `;
                
                li.addEventListener("click", () => {
                    selectThread(thread.thread_id);
                });
                
                threadsList.appendChild(li);
            });
        } catch (e) {
            console.error("Error loading chat threads:", e);
        }
    }

    function selectThread(threadId) {
        currentThreadId = threadId;
        localStorage.setItem("currentThreadId", currentThreadId);
        showChatState();
        
        document.querySelectorAll(".thread-item").forEach(item => {
            item.classList.remove("active");
        });
        fetchThreads();
        loadThreadHistory(currentThreadId);
    }

    async function loadThreadHistory(threadId) {
        try {
            const res = await fetch(`/thread/${threadId}/history`);
            const data = await res.json();
            
            chatMessages.innerHTML = "";
            if (!data.messages || data.messages.length === 0) {
                showLandingState();
                return;
            }

            showChatState();
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });

            // Fetch thread metadata pin status
            try {
                const metaRes = await fetch(`/thread/${threadId}/metadata`);
                if (metaRes.ok) {
                    const meta = await metaRes.json();
                    isCurrentPinned = meta.is_pinned;
                    isCurrentArchived = meta.is_archived;
                    if (labelSettingsPin) {
                        labelSettingsPin.textContent = isCurrentPinned ? "Unpin Chat" : "Pin Chat";
                    }
                }
            } catch(e) {
                console.error("Error loading metadata:", e);
            }

            scrollToBottom();
        } catch (e) {
            console.error("Error loading history:", e);
            showLandingState();
        }
    }

    function appendMessage(role, content) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}`;
        
        if (role === "assistant" && !content) {
            msgDiv.innerHTML = `
                <div class="qubi-typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
        } else {
            let formatted = content
                .replace(/&/g, "&amp;")
                .replace(/&lt;/g, "<")
                .replace(/&gt;/g, ">");

            formatted = formatted.replace(/```([\s\S]+?)```/g, (match, p1) => `<pre><code>${p1}</code></pre>`);
            formatted = formatted.replace(/`([^`\n]+?)`/g, "<code>$1</code>");
            formatted = formatted.replace(/\n/g, "<br>");
                
            msgDiv.innerHTML = formatted;
        }
        
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        
        return msgDiv;
    }

    // Submit handler (Stream-friendly buffering)
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        let queryText = userInput.value.trim();
        if (!queryText) return;

        if (!currentThreadId) {
            currentThreadId = uuidv4();
            localStorage.setItem("currentThreadId", currentThreadId);
        }

        if (isWebSearchEnabled) {
            queryText = "[Search Wikipedia]: " + queryText;
        }

        userInput.value = "";
        userInput.style.height = "auto";
        
        showChatState();
        appendMessage("user", queryText);

        const assistantBubble = appendMessage("assistant", "");
        let fullResponse = "";

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: queryText, thread_id: currentThreadId })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let sseBuffer = "";
            
            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                sseBuffer += decoder.decode(value, { stream: true });
                const lines = sseBuffer.split("\n");
                
                // Retain incomplete last line in chunk buffer
                sseBuffer = lines.pop();
                
                for (const line of lines) {
                    const cleanLine = line.trim();
                    if (!cleanLine) continue;
                    
                    if (cleanLine.startsWith("data: ")) {
                        try {
                            const dataText = cleanLine.substring(6).trim();
                            if (dataText === "[DONE]") continue;
                                
                            const parsed = JSON.parse(dataText);
                            if (parsed.text) {
                                fullResponse += parsed.text;
                                
                                let streamingHtml = fullResponse
                                    .replace(/&/g, "&amp;")
                                    .replace(/&lt;/g, "<")
                                    .replace(/&gt;/g, ">");

                                streamingHtml = streamingHtml.replace(/```([\s\S]+?)```/g, (m, p) => `<pre><code>${p}</code></pre>`);
                                streamingHtml = streamingHtml.replace(/`([^`\n]+?)`/g, "<code>$1</code>");
                                streamingHtml = streamingHtml.replace(/\n/g, "<br>") + "▌";

                                assistantBubble.innerHTML = streamingHtml;
                                scrollToBottom();
                            } else if (parsed.error) {
                                assistantBubble.innerHTML = `<span style="color:#ef4444;">Error: ${parsed.error}</span>`;
                            }
                        } catch (e) {}
                    }
                }
            }
            
            let completedHtml = fullResponse
                .replace(/&/g, "&amp;")
                .replace(/&lt;/g, "<")
                .replace(/&gt;/g, ">");
            completedHtml = completedHtml.replace(/```([\s\S]+?)```/g, (m, p) => `<pre><code>${p}</code></pre>`);
            completedHtml = completedHtml.replace(/`([^`\n]+?)`/g, "<code>$1</code>");
            completedHtml = completedHtml.replace(/\n/g, "<br>");
            
            assistantBubble.innerHTML = completedHtml;
            scrollToBottom();
            fetchThreads();
        } catch (err) {
            assistantBubble.innerHTML = `<span style="color:#ef4444;">Error connecting to DocPilot.</span>`;
            console.error(err);
        }
    });

    function uuidv4() {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    // ----------------------------------------------------
    // PDF Uploads Manager
    // ----------------------------------------------------
    if (uploadZone) {
        uploadZone.addEventListener("click", () => {
            fileInput.click();
        });
    }

    if (btnInputPlus) {
        btnInputPlus.addEventListener("click", () => {
            fileInput.click();
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", () => {
            if (fileInput.files.length > 0) {
                uploadFile(fileInput.files[0]);
            }
        });
    }

    async function uploadFile(file) {
        if (!file.name.endsWith(".pdf")) {
            alert("Only PDF files are supported.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        if (uploadStatus) {
            uploadStatus.style.display = "block";
            uploadStatus.textContent = "⏳ Uploading...";
            uploadStatus.style.color = "#a855f7";
        }

        try {
            const res = await fetch("/upload", {
                method: "POST",
                body: formData
            });

            if (res.ok) {
                if (uploadStatus) {
                    uploadStatus.textContent = "✅ Uploaded!";
                    uploadStatus.style.color = "#10b981";
                    setTimeout(() => { uploadStatus.style.display = "none"; }, 2000);
                }
                fileInput.value = "";
                fetchIndexedFiles();
            } else {
                const data = await res.json();
                if (uploadStatus) {
                    uploadStatus.textContent = `❌ ${data.detail || "Upload failed."}`;
                    uploadStatus.style.color = "#ef4444";
                }
            }
        } catch (e) {
            if (uploadStatus) {
                uploadStatus.textContent = "❌ Network error.";
                uploadStatus.style.color = "#ef4444";
            }
        }
    }

    async function fetchIndexedFiles() {
        try {
            const res = await fetch("/files");
            if (!res.ok) return;
            const data = await res.json();
            
            indexedFilesList.innerHTML = "";
            const files = data.files || [];
            
            if (files.length === 0) {
                indexedFilesList.innerHTML = `<li class="file-item-empty">No folders pinned</li>`;
                return;
            }

            files.forEach(file => {
                const li = document.createElement("li");
                li.className = "file-item";
                li.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <span title="${file}">${file}</span>
                    <button class="btn-delete-file" data-filename="${file}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                `;
                
                const btnDelete = li.querySelector(".btn-delete-file");
                if (btnDelete) {
                    btnDelete.addEventListener("click", (e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete ${file}?`)) {
                            deleteUploadedFile(file);
                        }
                    });
                }
                
                indexedFilesList.appendChild(li);
            });
        } catch (e) {
            console.error("Error loading files:", e);
        }
    }

    async function deleteUploadedFile(filename) {
        try {
            const res = await fetch(`/files/${encodeURIComponent(filename)}`, {
                method: "DELETE"
            });
            if (res.ok) {
                fetchIndexedFiles();
            } else {
                const data = await res.json();
                alert(`Error deleting file: ${data.detail || "Request failed."}`);
            }
        } catch(err) {
            console.error("Error deleting file:", err);
            alert("Network error deleting file.");
        }
    }

    function initSidebarToggle() {
        const btnCollapseSidebar = document.querySelector(".sidebar-collapse-btn");
        const btnExpandSidebar = document.getElementById("btn-expand-sidebar");
        const appSidebar = document.querySelector(".app-sidebar");

        if (btnCollapseSidebar && btnExpandSidebar && appSidebar) {
            btnCollapseSidebar.addEventListener("click", () => {
                appSidebar.classList.add("sidebar-collapsed");
                btnExpandSidebar.classList.remove("hidden");
                localStorage.setItem("sidebar-collapsed", "true");
            });

            btnExpandSidebar.addEventListener("click", () => {
                appSidebar.classList.remove("sidebar-collapsed");
                btnExpandSidebar.classList.add("hidden");
                localStorage.setItem("sidebar-collapsed", "false");
            });

            const isCollapsed = localStorage.getItem("sidebar-collapsed") === "true";
            if (isCollapsed) {
                appSidebar.classList.add("sidebar-collapsed");
                btnExpandSidebar.classList.remove("hidden");
            } else {
                appSidebar.classList.remove("sidebar-collapsed");
                btnExpandSidebar.classList.add("hidden");
            }
        }
        if (btnHeaderBack) {
            btnHeaderBack.addEventListener("click", () => {
                showLandingState();
            });
        }
    }

    // Start flows
    initSearchFilter();
    initSuggestions();
    initInputAutoresize();
    initVoiceRecognition();
    initSettingsMenu();
    initSidebarToggle();
    initAuth();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeDocPilotApp);
} else {
    initializeDocPilotApp();
}
