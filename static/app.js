// Auto-bypass ngrok browser warning pages and redirect API calls to local/origin backend
const originalFetch = window.fetch;
let API_BASE_URL = "";
if (window.location.protocol === "file:") {
    API_BASE_URL = "http://localhost:7865";
} else {
    API_BASE_URL = window.location.origin;
}

window.fetch = function (url, options = {}) {
    let urlStr = typeof url === "string" ? url : (url && url.url ? url.url : "");
    
    // Only apply ngrok headers and origin mapping to local API routes (starting with / or matching location.origin)
    if (urlStr.startsWith("/") || urlStr.includes(window.location.origin) || urlStr.includes("ngrok")) {
        options.headers = options.headers || {};
        if (options.headers instanceof Headers) {
            options.headers.set("ngrok-skip-browser-warning", "69420");
        } else {
            options.headers["ngrok-skip-browser-warning"] = "69420";
        }
        if (urlStr.startsWith("/")) {
            url = API_BASE_URL + urlStr;
        }
    }

    return originalFetch(url, options);
};

// ── GLOBAL LAYOUT & WINDOW CONTROLLERS ─────────────────────────
window.setSidebarState = function(collapsed) {
    const appSidebar = document.querySelector(".app-sidebar");
    const btnExpandSidebar = document.getElementById("btn-expand-sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");
    if (!appSidebar) return;

    if (collapsed) {
        appSidebar.classList.add("sidebar-collapsed");
        if (btnExpandSidebar) {
            btnExpandSidebar.classList.remove("hidden");
            btnExpandSidebar.style.setProperty("display", "inline-flex", "important");
        }
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.add("hidden");
            sidebarBackdrop.style.setProperty("display", "none", "important");
        }
        try { localStorage.setItem("sidebar-collapsed", "true"); } catch(e){}
    } else {
        appSidebar.classList.remove("sidebar-collapsed");
        if (btnExpandSidebar) {
            btnExpandSidebar.classList.add("hidden");
            btnExpandSidebar.style.setProperty("display", "none", "important");
        }
        if (window.innerWidth <= 768 && sidebarBackdrop) {
            sidebarBackdrop.classList.remove("hidden");
            sidebarBackdrop.style.setProperty("display", "block", "important");
        } else if (sidebarBackdrop) {
            sidebarBackdrop.classList.add("hidden");
            sidebarBackdrop.style.setProperty("display", "none", "important");
        }
        try { localStorage.setItem("sidebar-collapsed", "false"); } catch(e){}
    }
};

window.toggleSidebar = function(e) {
    if (e && typeof e.preventDefault === "function") e.preventDefault();
    if (e && typeof e.stopPropagation === "function") e.stopPropagation();
    const appSidebar = document.querySelector(".app-sidebar");
    if (!appSidebar) return;
    const isCurrentlyCollapsed = appSidebar.classList.contains("sidebar-collapsed");
    window.setSidebarState(!isCurrentlyCollapsed);
};

window.toggleFullscreen = function(e) {
    if (e && typeof e.preventDefault === "function") e.preventDefault();
    if (e && typeof e.stopPropagation === "function") e.stopPropagation();
    
    const doc = document;
    const docEl = document.documentElement;
    const isFull = !!(doc.fullscreenElement || doc.webkitFullscreenElement || doc.mozFullScreenElement || doc.msFullscreenElement);
    const btnFullscreen = document.getElementById("btn-fullscreen-toggle");

    const updateBtn = function(full) {
        if (!btnFullscreen) return;
        const expandSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
        const minimizeSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 14h6v6m10-10h-6V4m0 16h6v-6M10 4H4v6"/></svg>';
        if (full) {
            btnFullscreen.innerHTML = `${minimizeSvg}<span>Exit Fullscreen</span>`;
            btnFullscreen.title = "Exit Fullscreen Mode (Esc)";
        } else {
            btnFullscreen.innerHTML = `${expandSvg}<span>Fullscreen</span>`;
            btnFullscreen.title = "Toggle Fullscreen Mode";
        }
    };

    if (!isFull) {
        if (docEl.requestFullscreen) {
            docEl.requestFullscreen().then(() => updateBtn(true)).catch(err => {
                console.warn("Fullscreen request error:", err);
                updateBtn(false);
            });
        } else if (docEl.webkitRequestFullscreen) {
            docEl.webkitRequestFullscreen();
            updateBtn(true);
        } else if (docEl.mozRequestFullScreen) {
            docEl.mozRequestFullScreen();
            updateBtn(true);
        } else if (docEl.msRequestFullscreen) {
            docEl.msRequestFullscreen();
            updateBtn(true);
        }
    } else {
        if (doc.exitFullscreen) {
            doc.exitFullscreen().then(() => updateBtn(false)).catch(err => {
                console.warn("Exit fullscreen error:", err);
                updateBtn(false);
            });
        } else if (doc.webkitExitFullscreen) {
            doc.webkitExitFullscreen();
            updateBtn(false);
        } else if (doc.mozCancelFullScreen) {
            doc.mozCancelFullScreen();
            updateBtn(false);
        } else if (doc.msExitFullscreen) {
            doc.msExitFullscreen();
            updateBtn(false);
        }
    }
};

document.addEventListener("fullscreenchange", function() {
    const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);
    const btnFullscreen = document.getElementById("btn-fullscreen-toggle");
    if (btnFullscreen) {
        const expandSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
        const minimizeSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 14h6v6m10-10h-6V4m0 16h6v-6M10 4H4v6"/></svg>';
        btnFullscreen.innerHTML = isFull ? `${minimizeSvg}<span>Exit Fullscreen</span>` : `${expandSvg}<span>Fullscreen</span>`;
    }
});
document.addEventListener("webkitfullscreenchange", function() {
    const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);
    const btnFullscreen = document.getElementById("btn-fullscreen-toggle");
    if (btnFullscreen) {
        const expandSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
        const minimizeSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 14h6v6m10-10h-6V4m0 16h6v-6M10 4H4v6"/></svg>';
        btnFullscreen.innerHTML = isFull ? `${minimizeSvg}<span>Exit Fullscreen</span>` : `${expandSvg}<span>Fullscreen</span>`;
    }
});

// ── SUPABASE AUTH (replaces Firebase) ──────────────────────────────────────
var SUPABASE_URL = "https://tuynzxkucwfcgwzynzrw.supabase.co";
var SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR1eW56eGt1Y3dmY2d3enluenJ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY1NjEyNDQsImV4cCI6MjEwMjEzNzI0NH0.gLV5uglVNYF6xIBf22F9WM2IPcg1bA0sRkOD52xtVBE";

var supabaseClient = null;
try {
    if (typeof window.supabase !== "undefined" && window.supabase.createClient) {
        supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        console.log("[SUPABASE] Client initialized");

        // Auth state listener — fires on page load AND after OAuth redirect
        supabaseClient.auth.onAuthStateChange(function(event, session) {
            console.log("[SUPABASE] Auth event:", event, session ? session.user.email : "no session");
            if (session && session.user) {
                var user = session.user;
                var meta = user.user_metadata || {};
                var appUser = {
                    id: user.id,
                    email: user.email,
                    name: meta.full_name || meta.name || user.email.split("@")[0],
                    provider: "google",
                    avatar_url: meta.avatar_url || meta.picture || ("https://api.dicebear.com/7.x/bottts/svg?seed=" + encodeURIComponent(user.email))
                };
                console.log("[SUPABASE] Logging in:", appUser.email);
                if (typeof window.loginUser === "function") window.loginUser(appUser);
                // Background sync with our backend DB
                fetch("/api/firebase-sync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ uid: user.id, email: appUser.email, name: appUser.name, provider: "google", avatar_url: appUser.avatar_url })
                }).catch(function() {});
            }
        });
    } else {
        console.warn("[SUPABASE] SDK not loaded yet");
    }
} catch(e) {
    console.error("[SUPABASE] Init error:", e);
}
// ─────────────────────────────────────────────────────────────────────────────


// Google OAuth client ID
var GOOGLE_CLIENT_ID = "585299422541-edqtcaaoljev3op2cffl98jfvr8asn56.apps.googleusercontent.com";

// Top-Level Global Auth Controller & View Manager
window.loginUser = function(user) {
    if (!user || !user.email) return;
    window.currentUser = user;
    if (typeof window.syncAppCurrentUser === "function") {
        window.syncAppCurrentUser(user);
    }

    // Persist user session to localStorage
    const userData = JSON.stringify(user);
    try {
        localStorage.setItem("docpilot-user", userData);
    } catch(e) {}

    // Immediately apply logged-in class to html element
    if (document.documentElement) {
        document.documentElement.classList.add("logged-in");
    }

    const landingPageView = document.getElementById("landing-page-view");
    const chatbotAppView = document.getElementById("chatbot-app-view");
    const navPinnedLibrary = document.getElementById("nav-pinned-library");

    const avatarUrl = user.avatar_url || user.picture || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(user.email || 'Student')}`;
    const displayName = user.name || (user.email ? user.email.split("@")[0].replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : "Student User");
    const displayEmail = user.email || "student@college.edu";

    const userAvatarEls = document.querySelectorAll("#sidebar-user-avatar, .sidebar-user-avatar, #user-avatar, .header-user-avatar, #header-user-avatar, #dropdown-user-avatar");
    const userNameEls = document.querySelectorAll("#sidebar-user-name, .sidebar-user-name, #user-name, .header-user-name, #header-user-name, #dropdown-user-name");
    const userEmailEls = document.querySelectorAll("#sidebar-user-email, .sidebar-user-email, #user-email, .header-user-email, #header-user-email, #dropdown-user-email");

    userAvatarEls.forEach(el => {
        if (el.tagName === "IMG") {
            el.src = avatarUrl;
        } else {
            el.style.backgroundImage = `url('${avatarUrl}')`;
            el.innerHTML = "";
        }
    });

    userNameEls.forEach(el => { el.textContent = displayName; });
    userEmailEls.forEach(el => { el.textContent = displayEmail; });

    if (navPinnedLibrary) navPinnedLibrary.style.display = "flex";

    // EXPLICIT VIEW SWITCH TO WORKSPACE DASHBOARD
    if (landingPageView) {
        landingPageView.classList.add("hidden");
        landingPageView.setAttribute("style", "display: none !important;");
    }
    if (chatbotAppView) {
        chatbotAppView.classList.remove("hidden");
        chatbotAppView.setAttribute("style", "display: flex !important;");
    }

    if (typeof fetchThreads === "function") fetchThreads();
    if (typeof fetchIndexedFiles === "function") fetchIndexedFiles();
    if (typeof fetchUserStats === "function") fetchUserStats();
    if (typeof checkAndEnableAdminUI === "function") checkAndEnableAdminUI();
    if (typeof startHeartbeatDaemon === "function") startHeartbeatDaemon();
};

// Check for auth_data on page load (from backend Google OAuth callback)
(function() {
    try {
        var params = new URLSearchParams(window.location.search);
        var authData = params.get("auth_data");
        var authError = params.get("auth_error");
        if (authData) {
            var userData = JSON.parse(atob(authData));
            window.history.replaceState({}, document.title, window.location.pathname);
            console.log("[AUTH] Backend OAuth success:", userData.email);
            window.currentUser = userData;
            try {
                localStorage.setItem("docpilot-user", JSON.stringify(userData));
            } catch(e) {}
            if (typeof window.loginUser === "function") {
                window.loginUser(userData);
            }
        }
        if (authError) {
            window.history.replaceState({}, document.title, window.location.pathname);
            console.warn("[AUTH] Backend OAuth error:", authError);
            const authErrBox = document.getElementById("auth-error-msg");
            if (authErrBox) {
                authErrBox.textContent = "Google Sign-In was cancelled or encountered an error. Please try again.";
                authErrBox.classList.remove("hidden");
                authErrBox.style.display = "block";
            }
        }
    } catch(e) { console.error("[AUTH] auth_data parse error:", e); }
})();

// Cross-window postMessage listener for popup OAuth completion
window.addEventListener("message", function(event) {
    if (event.data && event.data.type === "PREPZ_GOOGLE_AUTH_SUCCESS" && event.data.user) {
        console.log("[AUTH] Received Google user via popup postMessage:", event.data.user.email);
        window.loginUser(event.data.user);
    }
});

// Multi-Tier Bulletproof Google Sign-In Handler
window.handleGoogleSignIn = function(e) {
    if (e) {
        if (typeof e.preventDefault === "function") e.preventDefault();
        if (typeof e.stopPropagation === "function") e.stopPropagation();
    }
    console.log("[AUTH] Google Sign-In triggered");

    const authErrBox = document.getElementById("auth-error-msg");
    if (authErrBox) {
        authErrBox.textContent = "";
        authErrBox.classList.add("hidden");
    }

    // TIER 1: Google Identity Services (GIS) Official Token Popup (Zero redirect issues)
    if (typeof window.google !== "undefined" && window.google.accounts && window.google.accounts.oauth2) {
        try {
            console.log("[AUTH] Initiating Google Identity Services (GIS) popup flow...");
            const tokenClient = window.google.accounts.oauth2.initTokenClient({
                client_id: GOOGLE_CLIENT_ID,
                scope: "email profile openid",
                prompt: "select_account",
                callback: async function(tokenResponse) {
                    if (tokenResponse && tokenResponse.access_token) {
                        console.log("[AUTH] GIS token received, verifying with backend...");
                        try {
                            const res = await fetch("/api/auth/google-token", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ access_token: tokenResponse.access_token })
                            });
                            const data = await res.json();
                            if (res.ok && data.user) {
                                console.log("[AUTH] Google authentication successful:", data.user.email);
                                window.loginUser(data.user);
                                return;
                            } else {
                                console.error("[AUTH] Google token verification failed:", data);
                                if (authErrBox) {
                                    authErrBox.textContent = data.detail || "Google verification failed. Please try again.";
                                    authErrBox.classList.remove("hidden");
                                    authErrBox.style.display = "block";
                                }
                            }
                        } catch(err) {
                            console.error("[AUTH] GIS token server error:", err);
                        }
                    } else if (tokenResponse && tokenResponse.error) {
                        console.warn("[AUTH] GIS response error:", tokenResponse.error);
                    }
                }
            });
            tokenClient.requestAccessToken({ prompt: "select_account" });
            return;
        } catch(gisErr) {
            console.warn("[AUTH] GIS token client init error, falling back to Supabase/Backend:", gisErr);
        }
    }

    // TIER 2: Supabase Google OAuth Provider
    if (typeof supabaseClient !== "undefined" && supabaseClient && supabaseClient.auth) {
        try {
            console.log("[AUTH] Initiating Supabase Google OAuth...");
            supabaseClient.auth.signInWithOAuth({
                provider: "google",
                options: {
                    redirectTo: window.location.origin
                }
            }).then(function(result) {
                if (result && result.error) {
                    console.warn("[AUTH] Supabase OAuth error:", result.error);
                    triggerBackendOAuthFallback();
                }
            }).catch(function(err) {
                console.warn("[AUTH] Supabase OAuth exception:", err);
                triggerBackendOAuthFallback();
            });
            return;
        } catch(supaErr) {
            console.warn("[AUTH] Supabase signInWithOAuth failed:", supaErr);
        }
    }

    // TIER 3: Backend Direct OAuth Popup / Navigation Fallback
    triggerBackendOAuthFallback();
};

function triggerBackendOAuthFallback() {
    const authUrl = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
        ? "/api/auth/google"
        : "https://om123bansal-prepz-app.hf.space/api/auth/google";

    const width = 520;
    const height = 650;
    const left = Math.max(0, (window.screen.width - width) / 2);
    const top = Math.max(0, (window.screen.height - height) / 2);

    let popup = null;
    try {
        popup = window.open(
            authUrl,
            "PrepzGoogleAuth",
            `width=${width},height=${height},top=${top},left=${left},status=no,toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
        );
    } catch(popErr) {
        console.warn("Popup error:", popErr);
    }

    if (!popup || popup.closed || typeof popup.closed === "undefined") {
        var isInIframe = false;
        try { isInIframe = (window.self !== window.top); } catch(err2) { isInIframe = true; }
        if (isInIframe) {
            try {
                window.top.location.href = authUrl;
                return;
            } catch(e3) {
                window.open(authUrl, "_blank", "noopener,noreferrer");
                return;
            }
        }
        window.location.href = authUrl;
    }
}

// Global click event delegation for Google Sign-In button
document.addEventListener("click", function(e) {
    const btn = e.target && e.target.closest ? e.target.closest("#btn-google-login") : null;
    if (btn) {
        window.handleGoogleSignIn(e);
    }
});

window.showLoginScreen = function() {
    console.log("[AUTH] showLoginScreen() called");
    window.currentUser = null;
    if (document.documentElement) {
        document.documentElement.classList.remove("logged-in");
    }
    const landingPageView = document.getElementById("landing-page-view");
    const chatbotAppView = document.getElementById("chatbot-app-view");
    const navPinnedLibrary = document.getElementById("nav-pinned-library");

    if (navPinnedLibrary) navPinnedLibrary.style.display = "none";
    if (landingPageView) {
        landingPageView.classList.remove("hidden");
        landingPageView.setAttribute("style", "display: flex !important;");
    }
    if (chatbotAppView) {
        chatbotAppView.classList.add("hidden");
        chatbotAppView.setAttribute("style", "display: none !important;");
    }
};

// Fallback guest auto-session enabler so feature cards work directly for unauthenticated visitors
window.ensureUserSession = function() {
    if (!window.currentUser) {
        const guestUser = {
            id: "guest-user-session",
            name: "Student User",
            email: "student@prepz.edu",
            provider: "guest",
            avatar_url: "https://api.dicebear.com/7.x/bottts/svg?seed=PrepzStudent"
        };
        window.loginUser(guestUser);
    }
};

window.logoutUser = async function() {
    console.log("[AUTH] logoutUser() called");
    try {
        if (typeof supabaseClient !== "undefined" && supabaseClient && supabaseClient.auth) {
            await supabaseClient.auth.signOut();
        }
    } catch(e) {}
    window.currentUser = null;
    try {
        localStorage.removeItem("docpilot-user");
        sessionStorage.clear();
    } catch(e) {}
    if (typeof window.showLoginScreen === "function") window.showLoginScreen();
};

// Global User State initialized from cache if present
try {
    const raw = localStorage.getItem("docpilot-user") || localStorage.getItem("prepz_user");
    if (raw && !window.currentUser) window.currentUser = JSON.parse(raw);
} catch(e) {}
if (!window.currentUser) window.currentUser = null;

window.switchAuthTab = function (tab) {
    const tabLogin = document.getElementById("tab-login");
    const tabSignup = document.getElementById("tab-signup");
    const formLogin = document.getElementById("form-login");
    const formSignup = document.getElementById("form-signup");
    const authErrorMsg = document.getElementById("auth-error-msg");

    if (authErrorMsg) {
        authErrorMsg.textContent = "";
        authErrorMsg.classList.add("hidden");
    }

    if (tab === "signup") {
        if (tabSignup) tabSignup.className = "auth-tab-btn active";
        if (tabLogin) tabLogin.className = "auth-tab-btn";
        if (formSignup) {
            formSignup.classList.remove("hidden");
            formSignup.setAttribute("style", "display: flex !important;");
        }
        if (formLogin) {
            formLogin.classList.add("hidden");
            formLogin.setAttribute("style", "display: none !important;");
        }
        if (typeof window.generateCaptcha === "function") {
            window.generateCaptcha("signup");
        }
    } else {
        if (tabLogin) tabLogin.className = "auth-tab-btn active";
        if (tabSignup) tabSignup.className = "auth-tab-btn";
        if (formLogin) {
            formLogin.classList.remove("hidden");
            formLogin.setAttribute("style", "display: flex !important;");
        }
        if (formSignup) {
            formSignup.classList.add("hidden");
            formSignup.setAttribute("style", "display: none !important;");
        }
    }
};

// NOTE: window.handleGoogleLogin is intentionally not used.
// The ONLY Google Sign-In entry point is the loginBtn click handler
// inside initializeDocPilotApp() below, which calls signInWithPopup
// synchronously as the very first action in the click event.

function showAuthErrorMsg(msg, type = "error") {
    const authErrorMsg = document.getElementById("auth-error-msg");
    if (authErrorMsg) {
        authErrorMsg.textContent = msg;
        authErrorMsg.classList.remove("hidden");
        authErrorMsg.style.display = "block";
        if (type === "success") {
            authErrorMsg.style.backgroundColor = "rgba(34, 197, 94, 0.15)";
            authErrorMsg.style.color = "#4ade80";
            authErrorMsg.style.borderColor = "rgba(34, 197, 94, 0.3)";
        } else {
            authErrorMsg.style.backgroundColor = "";
            authErrorMsg.style.color = "";
            authErrorMsg.style.borderColor = "";
        }
    }
}

let currentCaptchaState = {
    signup: { num1: 0, num2: 0, ans: 0 },
    forgot: { num1: 0, num2: 0, ans: 0 }
};

window.generateCaptcha = function(type) {
    const num1 = Math.floor(Math.random() * 9) + 1;
    const num2 = Math.floor(Math.random() * 9) + 1;
    currentCaptchaState[type] = { num1, num2, ans: num1 + num2 };
    
    const qEl = document.getElementById(`${type}-captcha-question`);
    if (qEl) {
        qEl.textContent = `${num1} + ${num2} = ?`;
    }
};

window.isValidEmail = function(email) {
    if (!email || typeof email !== "string") return false;
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    return emailRegex.test(email.trim());
};

window.handleLoginSubmit = async function (e) {
    if (e) e.preventDefault();
    const authErrorMsg = document.getElementById("auth-error-msg");
    if (authErrorMsg) {
        authErrorMsg.textContent = "";
        authErrorMsg.classList.add("hidden");
    }

    const emailInput = document.getElementById("login-email");
    const pwdInput = document.getElementById("login-password");
    const email = emailInput ? emailInput.value.trim().toLowerCase() : "";
    const password = pwdInput ? pwdInput.value : "";

    console.log(`[AUTH CLIENT] Login submitted for email='${email}'`);

    if (!email || !password) {
        showAuthErrorMsg("Please enter both email and password.");
        return;
    }

    if (!window.isValidEmail(email)) {
        showAuthErrorMsg("Please enter a valid email address.");
        return;
    }

    console.log('[LOGIN CLICK]', 'Login button submitted for email:', email);

    // Direct Backend API Login
    try {
        console.log('[LOGIN API CALL STARTING]', 'Calling /api/login...');
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.user) {
            console.log('[LOGIN SUCCESS]', data.user.email);
            window.loginUser(data.user);
        } else {
            console.error('[ERROR]', 'Login API failed:', data.detail);
            showAuthErrorMsg(data.detail || "Invalid email or password. Please check your credentials.");
        }
    } catch (err) {
        console.error('[ERROR]', 'Login connection error:', err);
        showAuthErrorMsg("Connection error. Please check your network connection.");
    }
};

window.handleSignupSubmit = async function (e) {
    if (e) e.preventDefault();
    const authErrorMsg = document.getElementById("auth-error-msg");
    if (authErrorMsg) {
        authErrorMsg.textContent = "";
        authErrorMsg.classList.add("hidden");
    }

    const nameInput = document.getElementById("signup-name");
    const emailInput = document.getElementById("signup-email");
    const pwdInput = document.getElementById("signup-password");
    const captchaInput = document.getElementById("signup-captcha-answer");

    const name = nameInput && nameInput.value.trim() ? nameInput.value.trim() : "";
    const email = emailInput && emailInput.value.trim() ? emailInput.value.trim().toLowerCase() : "";
    const password = pwdInput ? pwdInput.value : "";
    const captchaAns = captchaInput ? captchaInput.value.trim() : "";

    console.log(`[AUTH CLIENT] Signup submitted for name='${name}', email='${email}'`);

    if (!name || !email || !password) {
        showAuthErrorMsg("All fields are required for sign up.");
        return;
    }

    if (!window.isValidEmail(email)) {
        showAuthErrorMsg("Please enter a valid email address.");
        return;
    }

    if (password.length < 6) {
        showAuthErrorMsg("Password must be at least 6 characters long.");
        return;
    }

    if (!currentCaptchaState.signup || currentCaptchaState.signup.ans === 0) {
        window.generateCaptcha("signup");
    }

    if (parseInt(captchaAns, 10) !== currentCaptchaState.signup.ans) {
        showAuthErrorMsg("Incorrect Security Challenge answer. Please try again.");
        window.generateCaptcha("signup");
        return;
    }

    // Attempt Firebase Signup
    if (typeof firebaseAuth !== "undefined" && firebaseAuth) {
        try {
            const userCred = await firebaseAuth.createUserWithEmailAndPassword(email, password);
            const user = userCred.user;
            await user.updateProfile({ displayName: name });
            try { await user.sendEmailVerification(); } catch(e) {}

            let syncedUser = {
                id: user.uid,
                name: name,
                email: email,
                provider: "password"
            };

            try {
                const syncRes = await fetch("/api/firebase-sync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        uid: user.uid,
                        email: email,
                        name: name,
                        provider: "password"
                    })
                });
                const syncData = await syncRes.json();
                if (syncRes.ok && syncData.user) {
                    syncedUser = syncData.user;
                }
            } catch(e) {}

            window.loginUser(syncedUser);
            return;
        } catch (error) {
            console.warn("[AUTH CLIENT] Firebase signup error, attempting backend API fallback:", error.code);
            if (error.code === "auth/email-already-in-use") {
                showAuthErrorMsg("An account with this email address already exists. Please switch to the Log In tab.");
                return;
            }
        }
    }

    // Backend Signup Fallback
    try {
        const res = await fetch("/api/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (res.ok && data.user) {
            window.loginUser(data.user);
        } else {
            showAuthErrorMsg(data.detail || "Signup failed. Please try again.");
        }
    } catch(err) {
        showAuthErrorMsg("Connection error. Please try again.");
    }
};

let currentPendingOtpEmail = "";
let currentOtpType = "signup";

window.openOtpModal = function(email, otpType = "signup") {
    currentPendingOtpEmail = email;
    currentOtpType = otpType;
    const modal = document.getElementById("otp-verification-modal");
    const emailDisplay = document.getElementById("otp-target-email-display");
    const errorMsg = document.getElementById("otp-error-msg");
    const otpInput = document.getElementById("otp-code-input");

    if (emailDisplay) emailDisplay.textContent = email;
    if (errorMsg) { errorMsg.textContent = ""; errorMsg.classList.add("hidden"); errorMsg.style.display = "none"; }
    if (otpInput) { otpInput.value = ""; }

    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        if (otpInput) setTimeout(() => otpInput.focus(), 100);
    }
};

window.closeOtpModal = function() {
    const modal = document.getElementById("otp-verification-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.style.display = "none";
    }
};

window.handleVerifyOtpSubmit = async function(e) {
    if (e) e.preventDefault();
    const otpInput = document.getElementById("otp-code-input");
    const errorMsg = document.getElementById("otp-error-msg");
    const otpCode = otpInput ? otpInput.value.trim() : "";

    if (!otpCode || otpCode.length !== 6) {
        if (errorMsg) {
            errorMsg.textContent = "Please enter a valid 6-digit OTP code.";
            errorMsg.classList.remove("hidden");
            errorMsg.style.display = "block";
        }
        return;
    }

    try {
        const res = await fetch("/api/verify-otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: currentPendingOtpEmail,
                otp_code: otpCode,
                otp_type: currentOtpType
            })
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            window.closeOtpModal();
            if (data.user) {
                window.loginUser(data.user);
            } else {
                window.openResetPasswordModal(currentPendingOtpEmail, otpCode);
            }
        } else {
            const err = data.detail || "Invalid or expired OTP code.";
            if (errorMsg) {
                errorMsg.textContent = err;
                errorMsg.classList.remove("hidden");
                errorMsg.style.display = "block";
            }
        }
    } catch (err) {
        if (errorMsg) {
            errorMsg.textContent = "Network error verifying OTP.";
            errorMsg.classList.remove("hidden");
            errorMsg.style.display = "block";
        }
    }
};

window.openForgotPasswordModal = function(e) {
    if (e) e.preventDefault();
    window.generateCaptcha("forgot");
    const modal = document.getElementById("forgot-password-modal");
    const errEl = document.getElementById("forgot-error-msg");
    if (errEl) { errEl.textContent = ""; errEl.classList.add("hidden"); errEl.style.display = "none"; }

    const gmailModalEmail = document.getElementById("gmail-modal-email-input");
    const loginEmail = document.getElementById("login-email");
    const forgotEmail = document.getElementById("forgot-email-input");

    const prefilledEmail = (gmailModalEmail && gmailModalEmail.value.trim()) || (loginEmail && loginEmail.value.trim()) || "";
    if (forgotEmail && prefilledEmail) {
        forgotEmail.value = prefilledEmail;
    }

    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        const captchaAns = document.getElementById("forgot-captcha-answer");
        if (captchaAns) setTimeout(() => captchaAns.focus(), 100);
    }
};

window.closeForgotPasswordModal = function() {
    const modal = document.getElementById("forgot-password-modal");
    if (modal) { modal.classList.add("hidden"); modal.style.display = "none"; }
};

window.handleForgotPasswordSubmit = async function(e) {
    if (e) e.preventDefault();
    const emailInput = document.getElementById("forgot-email-input");
    const captchaInput = document.getElementById("forgot-captcha-answer");
    const errEl = document.getElementById("forgot-error-msg");

    const email = emailInput ? emailInput.value.trim().toLowerCase() : "";
    const answer = captchaInput ? captchaInput.value.trim() : "";

    if (!email || !window.isValidEmail(email)) {
        if (errEl) {
            errEl.textContent = "Please enter a valid email address.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
        }
        return;
    }

    if (parseInt(answer, 10) !== currentCaptchaState.forgot.ans) {
        if (errEl) {
            errEl.textContent = "Incorrect Security Challenge answer. Please try again.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
        }
        window.generateCaptcha("forgot");
        return;
    }

    try {
        const res = await fetch("/api/forgot-password/request-otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            window.closeForgotPasswordModal();
            window.openOtpModal(email, "forgot_password");
        } else {
            if (errEl) {
                errEl.textContent = data.detail || "Could not send OTP. Please try again.";
                errEl.classList.remove("hidden");
                errEl.style.display = "block";
            }
        }
    } catch (error) {
        console.error("[AUTH CLIENT] Forgot password OTP request error:", error);
        if (errEl) {
            errEl.textContent = "Connection error. Please try again.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
        }
    }
};

window.openResetPasswordModal = function(email, prefilledOtp = "", message = "") {
    currentPendingOtpEmail = email;
    const modal = document.getElementById("reset-password-modal");
    const emailInput = document.getElementById("reset-email-input");
    const otpInput = document.getElementById("reset-otp-input");
    const errEl = document.getElementById("reset-error-msg");

    if (emailInput && email) emailInput.value = email;

    if (errEl) {
        if (message || prefilledOtp) {
            errEl.textContent = message ? `${message} Code: ${prefilledOtp}` : `Password reset OTP code: ${prefilledOtp}`;
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
            errEl.style.color = "#818cf8";
            errEl.style.background = "rgba(99, 102, 241, 0.15)";
            errEl.style.border = "1px solid rgba(99, 102, 241, 0.3)";
        } else {
            errEl.textContent = "";
            errEl.classList.add("hidden");
            errEl.style.display = "none";
        }
    }

    if (otpInput && prefilledOtp) otpInput.value = prefilledOtp;

    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        if (otpInput) setTimeout(() => otpInput.focus(), 100);
    }
};

window.closeResetPasswordModal = function() {
    const modal = document.getElementById("reset-password-modal");
    if (modal) { modal.classList.add("hidden"); modal.style.display = "none"; }
};

window.handleResetPasswordSubmit = async function(e) {
    if (e) e.preventDefault();
    const emailInput = document.getElementById("reset-email-input");
    const otpInput = document.getElementById("reset-otp-input");
    const newPwdInput = document.getElementById("reset-new-password");
    const errEl = document.getElementById("reset-error-msg");

    const email = (emailInput && emailInput.value.trim()) || currentPendingOtpEmail;
    const otpCode = otpInput ? otpInput.value.trim() : "";
    const newPassword = newPwdInput ? newPwdInput.value : "";

    if (!email) {
        if (errEl) {
            errEl.textContent = "Please enter your registered email address.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
            errEl.style.color = ""; errEl.style.background = ""; errEl.style.border = "";
        }
        return;
    }

    if (!otpCode || otpCode.length !== 6) {
        if (errEl) {
            errEl.textContent = "Please enter a valid 6-digit OTP code.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
            errEl.style.color = ""; errEl.style.background = ""; errEl.style.border = "";
        }
        return;
    }

    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
        if (errEl) {
            errEl.textContent = "Password must be at least 8 characters long with letters and numbers.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
            errEl.style.color = ""; errEl.style.background = ""; errEl.style.border = "";
        }
        return;
    }

    try {
        const res = await fetch("/api/forgot-password/reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email.toLowerCase(),
                otp_code: otpCode,
                new_password: newPassword
            })
        });
        const data = await res.json();
        if (res.ok) {
            window.closeResetPasswordModal();
            showAuthErrorMsg("Password updated successfully! Logging you in...");
            const loginRes = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: email.toLowerCase(), password: newPassword })
            });
            const loginData = await loginRes.json();
            if (loginRes.ok && loginData.user) {
                window.loginUser(loginData.user);
            } else {
                window.switchAuthTab("login");
            }
        } else {
            const err = data.detail || "Failed to reset password.";
            if (errEl) {
                errEl.textContent = err;
                errEl.classList.remove("hidden");
                errEl.style.display = "block";
                errEl.style.color = ""; errEl.style.background = ""; errEl.style.border = "";
            }
        }
    } catch (err) {
        if (errEl) {
            errEl.textContent = "Network error. Please try again.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
            errEl.style.color = ""; errEl.style.background = ""; errEl.style.border = "";
        }
    }
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

    // Core Chat Elements & View Containers
    const chatMessages = document.getElementById("chat-messages");
    const chatMessagesContainer = document.getElementById("chat-messages-container");
    const landingContainer = document.getElementById("landing-container");
    const pinnedLibraryContainer = document.getElementById("pinned-library-container");
    const browseContainer = document.getElementById("browse-container");
    const predictorContainer = document.getElementById("predictor-container");
    const leaderboardContainer = document.getElementById("leaderboard-container");
    const inputPanelWrapper = document.getElementById("input-panel-wrapper");
    
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const threadsList = document.getElementById("threads-list");
    const fileInput = document.getElementById("file-input");
    const uploadStatus = document.getElementById("upload-status");
    const indexedFilesList = document.getElementById("indexed-files-list");
    
    // Navbar Elements & Interactive Triggers
    const navNewChat = document.getElementById("nav-new-chat");
    const navPinnedLibrary = document.getElementById("nav-pinned-library");
    const navBrowseDocuments = document.getElementById("nav-browse-documents");
    const navExamPredictor = document.getElementById("nav-exam-predictor");
    const navLeaderboard = document.getElementById("nav-leaderboard");
    const navNewChatBtn = document.getElementById("nav-new-chat-btn");
    const headerNewChatBtn = document.getElementById("btn-header-new-chat");
    const uploadZone = document.getElementById("upload-zone");
    const librarySearchInput = document.getElementById("library-search-input");

    const predictorSemesterSelect = document.getElementById("predictor-semester-select");
    const predictorSubjectSelect = document.getElementById("predictor-subject-select");
    const predictorExamTypeSelect = document.getElementById("predictor-examtype-select");
    const uploadExamTypeSelect = document.getElementById("upload-examtype-select");
    const btnGeneratePredictor = document.getElementById("btn-generate-predictor");
    const predictorLoadingCard = document.getElementById("predictor-loading-card");
    const predictorWarningCard = document.getElementById("predictor-warning-card");
    const predictorResultCard = document.getElementById("predictor-result-card");
    const predictedPaperBody = document.getElementById("predicted-paper-body");
    const btnDownloadPredictedPdf = document.getElementById("btn-download-predicted-pdf");
    const btnWarningUploadPyq = document.getElementById("btn-warning-upload-pyq");
    const btnLibraryUploadTrigger = document.getElementById("btn-library-upload-trigger");
    const btnBrowseUploadTrigger = document.getElementById("btn-browse-upload-trigger");
    
    const btnInputPlus = document.getElementById("btn-input-plus");
    const btnToggleSearch = document.getElementById("btn-toggle-search");
    const btnInputVoice = document.getElementById("btn-input-voice");
    const btnSubmit = document.getElementById("btn-submit");

    // Settings Dropdown Elements
    const settingsContainer = document.querySelector(".settings-container");
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

    // Global User State
    let currentUser = window.currentUser || null;
    window.syncAppCurrentUser = function(user) {
        currentUser = user;
        window.currentUser = user;
    };

    // ----------------------------------------------------
    // Authentication Manager
    // ----------------------------------------------------
    function initAuth() {
        if (window.generateCaptcha) window.generateCaptcha("signup");
        const tabLogin = document.getElementById("tab-login");
        const tabSignup = document.getElementById("tab-signup");
        const formLogin = document.getElementById("form-login");
        const formSignup = document.getElementById("form-signup");
        const authErrorMsg = document.getElementById("auth-error-msg");

        function showAuthError(msg) {
            if (authErrorMsg) {
                authErrorMsg.innerHTML = msg;
                authErrorMsg.classList.remove("hidden");
            }
        }

        function clearAuthError() {
            if (authErrorMsg) {
                authErrorMsg.textContent = "";
                authErrorMsg.classList.add("hidden");
            }
        }

        if (tabLogin && tabSignup && formLogin && formSignup) {
            tabLogin.addEventListener("click", (e) => {
                if (e) e.preventDefault();
                tabLogin.classList.add("active");
                tabSignup.classList.remove("active");

                formLogin.classList.remove("hidden");
                formLogin.style.setProperty("display", "flex", "important");

                formSignup.classList.add("hidden");
                formSignup.style.setProperty("display", "none", "important");
                clearAuthError();
            });

            tabSignup.addEventListener("click", (e) => {
                if (e) e.preventDefault();
                tabSignup.classList.add("active");
                tabLogin.classList.remove("active");

                formSignup.classList.remove("hidden");
                formSignup.style.setProperty("display", "flex", "important");

                formLogin.classList.add("hidden");
                formLogin.style.setProperty("display", "none", "important");
                clearAuthError();
            });
        }

        if (logoutBtn) {
            logoutBtn.addEventListener("click", () => {
                logoutUser();
            });
        }

        // -------------------------------------------------------
        // PAGE LOAD SESSION RESTORE
        // Strategy:
        //   1. Read cached user from localStorage.
        //   2. Wait for Firebase to resolve its auth state (onAuthStateChanged).
        //   3. If Firebase has a session AND it matches cache → use cache (fast path).
        //   4. If Firebase has a session AND it mismatches cache → re-sync from Firebase.
        //   5. If Firebase has no session → use cache if available, else show login.
        // firebaseAuth.currentUser is NULL at DOMContentLoaded time, so we MUST
        // wait for onAuthStateChanged to fire once to get the real Firebase state.
        // -------------------------------------------------------
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get("logout") === "true" || urlParams.get("switch") === "true") {
            logoutUser();
        } else {
            const cachedRaw = localStorage.getItem("docpilot-user") || localStorage.getItem("prepz_user");
            let cachedUser = window.currentUser;
            if (!cachedUser && cachedRaw) {
                try { cachedUser = JSON.parse(cachedRaw); } catch(e) {}
            }

            if (cachedUser && cachedUser.email) {
                console.log("[AUTH PAGE LOAD] Active user session verified:", cachedUser.email);
                window.currentUser = cachedUser;
                loginUser(cachedUser);
            } else {
                showLoginScreen();
            }
        }
    }

    function logoutUser() {
        if (typeof supabaseClient !== "undefined" && supabaseClient && supabaseClient.auth) {
            supabaseClient.auth.signOut().catch(err => console.error("[SUPABASE] signOut error:", err));
        }
        currentUser = null;
        if (navPinnedLibrary) navPinnedLibrary.style.display = "none";
        // Clear ALL user-related localStorage keys — including old fake-flow keys
        ["docpilot-user", "prepz_user", "currentThreadId",
         "prepz_google_accounts", "google-login-success-event"].forEach(k => localStorage.removeItem(k));
        sessionStorage.clear();
        currentThreadId = null;
        if (chatMessages) chatMessages.innerHTML = "";
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
        if (typeof resetViewModes === "function") resetViewModes();
        updateHeaderTitle("Home", "🏠");
        
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) {
            contentWrapper.classList.add("landing-mode");
        }

        if (landingContainer) {
            landingContainer.classList.remove("hidden");
            landingContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        const devFooter = document.querySelector(".landing-footer-nexa");
        if (devFooter) {
            devFooter.classList.remove("hidden");
            devFooter.style.display = "flex";
        }
        const profileCard = document.getElementById("home-profile-card") || document.querySelector(".developer-profile-card");
        if (profileCard) {
            profileCard.style.display = "flex";
        }
        if (settingsContainer) {
            settingsContainer.classList.add("hidden");
            settingsContainer.style.display = "none";
        }

        if (navNewChat) navNewChat.classList.add("active");

        if (btnHeaderSettings) btnHeaderSettings.style.display = "none";
        if (btnHeaderBack) btnHeaderBack.style.display = "none";
        
        if (chatMessages) chatMessages.innerHTML = "";
        if (userInput) {
            userInput.value = "";
            userInput.style.height = "auto";
        }
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

    const semesterSubjectMapping = {
        "Semester 1": [
            "Computational Thinking & Programming",
            "Engineering Calculus",
            "Introduction to Electricals & Electronics"
        ],
        "Semester 2": [
            "Electromagnetism & Mechanics",
            "Linear Algebra & Ordinary Differential Equation",
            "Digital Design"
        ],
        "Semester 3": [
            "Discrete Mathematical Structure",
            "OOPS using Java",
            "Probability & Statistics"
        ],
        "Semester 4": [
            "Statistical Machine Learning",
            "Information Management System",
            "DSA using C++"
        ],
        "Semester 5": [
            "Computer Networks",
            "Operating Systems",
            "DAA"
        ],
        "Semester 6": [
            "Microprocessor",
            "Artificial Intelligence",
            "Fullstack Development"
        ],
        "Semester 7": [
            "Cyber Security",
            "Quantum Computing",
            "UI/UX Design"
        ],
        "Semester 8": [
            "Cloud Computing",
            "Blockchain",
            "DevOps"
        ]
    };

    function resetViewModes() {
        if (window._leaderboardInterval) {
            clearInterval(window._leaderboardInterval);
            window._leaderboardInterval = null;
        }
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) {
            contentWrapper.classList.remove("landing-mode", "chat-mode", "library-mode", "browse-mode", "predictor-mode", "leaderboard-mode");
        }
        if (landingContainer) { landingContainer.classList.add("hidden"); landingContainer.style.display = "none"; }
        if (chatMessagesContainer) { chatMessagesContainer.classList.add("hidden"); chatMessagesContainer.style.display = "none"; }
        if (pinnedLibraryContainer) { pinnedLibraryContainer.classList.add("hidden"); pinnedLibraryContainer.style.display = "none"; }
        if (browseContainer) { browseContainer.classList.add("hidden"); browseContainer.style.display = "none"; }
        if (predictorContainer) { predictorContainer.classList.add("hidden"); predictorContainer.style.display = "none"; }
        if (leaderboardContainer) { leaderboardContainer.classList.add("hidden"); leaderboardContainer.style.display = "none"; }
        const creatorContainer = document.getElementById("creator-dashboard-container");
        if (creatorContainer) { creatorContainer.classList.add("hidden"); creatorContainer.style.display = "none"; }
        if (inputPanelWrapper) { inputPanelWrapper.classList.add("hidden"); inputPanelWrapper.style.display = "none"; }

        const devFooter = document.querySelector(".landing-footer-nexa");
        if (devFooter) { devFooter.classList.add("hidden"); devFooter.style.display = "none !important"; }
        const profileCard = document.getElementById("home-profile-card") || document.querySelector(".developer-profile-card");
        if (profileCard) { profileCard.style.display = "none"; }

        if (navNewChat) navNewChat.classList.remove("active");
        if (navPinnedLibrary) navPinnedLibrary.classList.remove("active");
        if (navBrowseDocuments) navBrowseDocuments.classList.remove("active");
        if (navExamPredictor) navExamPredictor.classList.remove("active");
        if (navLeaderboard) navLeaderboard.classList.remove("active");
        const navCreator = document.getElementById("nav-creator-dashboard-btn");
        if (navCreator) navCreator.classList.remove("active");
    }

    function updateHeaderTitle(titleText, icon = "✨") {
        const headerViewName = document.getElementById("header-view-name");
        const headerSparkle = document.querySelector(".header-title-sparkle");
        if (headerViewName) headerViewName.textContent = titleText;
        if (headerSparkle) headerSparkle.textContent = icon;
    }

    function showChatState() {
        resetViewModes();
        updateHeaderTitle("Chat");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("chat-mode");

        if (chatMessagesContainer) {
            chatMessagesContainer.classList.remove("hidden");
            chatMessagesContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.remove("hidden");
            inputPanelWrapper.style.display = "block";
        }
        if (settingsContainer) {
            settingsContainer.classList.remove("hidden");
            settingsContainer.style.display = "block";
        }
        if (btnHeaderSettings) btnHeaderSettings.style.display = "flex";
        if (btnHeaderBack) btnHeaderBack.style.display = "flex";

        scrollToBottom();
    }

    function showPinnedLibraryState() {
        if (typeof window.ensureUserSession === "function") window.ensureUserSession();
        const activeUser = currentUser || window.currentUser || { name: "Student User", email: "student@college.edu", provider: "local" };
        currentUser = activeUser;
        window.currentUser = activeUser;

        resetViewModes();
        updateHeaderTitle("My Workspace");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("library-mode");

        if (pinnedLibraryContainer) {
            pinnedLibraryContainer.classList.remove("hidden");
            pinnedLibraryContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        if (settingsContainer) {
            settingsContainer.classList.add("hidden");
            settingsContainer.style.display = "none";
        }

        if (navPinnedLibrary) navPinnedLibrary.classList.add("active");
        
        fetchIndexedFiles();
        fetchUserStats();
        if (typeof fetchMyDocuments === "function") fetchMyDocuments();
    }

    function showBrowseState() {
        if (typeof window.ensureUserSession === "function") window.ensureUserSession();
        resetViewModes();
        updateHeaderTitle("Course Repository");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("browse-mode");

        if (browseContainer) {
            browseContainer.classList.remove("hidden");
            browseContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        if (settingsContainer) {
            settingsContainer.classList.add("hidden");
            settingsContainer.style.display = "none";
        }

        if (navBrowseDocuments) navBrowseDocuments.classList.add("active");

        updateBrowseSubjectOptions();
        renderBrowseTable();
        if (typeof fetchSharedDocuments === "function") fetchSharedDocuments();
    }

    function showPredictorState() {
        if (typeof window.ensureUserSession === "function") window.ensureUserSession();
        const activeUser = currentUser || window.currentUser || { name: "Student User", email: "student@college.edu", provider: "local" };
        currentUser = activeUser;
        window.currentUser = activeUser;

        resetViewModes();
        updateHeaderTitle("Exam Predictor");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("predictor-mode");

        if (predictorContainer) {
            predictorContainer.classList.remove("hidden");
            predictorContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        if (settingsContainer) {
            settingsContainer.classList.add("hidden");
            settingsContainer.style.display = "none";
        }

        if (navExamPredictor) navExamPredictor.classList.add("active");

        updatePredictorSubjectOptions();
    }

    function showLeaderboardState() {
        if (typeof window.ensureUserSession === "function") window.ensureUserSession();
        resetViewModes();
        updateHeaderTitle("Leaderboard");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("leaderboard-mode");

        if (leaderboardContainer) {
            leaderboardContainer.classList.remove("hidden");
            leaderboardContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        if (settingsContainer) {
            settingsContainer.classList.add("hidden");
            settingsContainer.style.display = "none";
        }

        if (navLeaderboard) navLeaderboard.classList.add("active");

        fetchLeaderboard();
        if (window._leaderboardInterval) clearInterval(window._leaderboardInterval);
        window._leaderboardInterval = setInterval(fetchLeaderboard, 12000);
    }

    function showCreatorDashboardState() {
        if (typeof window.ensureUserSession === "function") window.ensureUserSession();
        resetViewModes();
        updateHeaderTitle("Creator Intelligence Hub", "⚡");
        const contentWrapper = document.querySelector(".content-wrapper");
        if (contentWrapper) contentWrapper.classList.add("creator-mode");

        const creatorContainer = document.getElementById("creator-dashboard-container");
        if (creatorContainer) {
            creatorContainer.classList.remove("hidden");
            creatorContainer.style.display = "flex";
        }
        if (inputPanelWrapper) {
            inputPanelWrapper.classList.add("hidden");
            inputPanelWrapper.style.display = "none";
        }
        const navCreator = document.getElementById("nav-creator-dashboard-btn");
        if (navCreator) navCreator.classList.add("active");

        if (typeof fetchAndRenderAdminDashboard === "function") {
            fetchAndRenderAdminDashboard();
        }
        if (window._creatorDashboardInterval) clearInterval(window._creatorDashboardInterval);
        window._creatorDashboardInterval = setInterval(() => {
            if (typeof fetchAndRenderAdminDashboard === "function") fetchAndRenderAdminDashboard();
        }, 15000);
    }

    // Expose view-switching functions to global window for inline onclick handlers and direct card clicks
    window.showChatState = showChatState;
    window.showLandingState = showLandingState;
    window.showPinnedLibraryState = showPinnedLibraryState;
    window.showBrowseState = showBrowseState;
    window.showPredictorState = showPredictorState;
    window.showLeaderboardState = showLeaderboardState;
    window.showCreatorDashboardState = showCreatorDashboardState;

    // Direct event listener binding for landing feature cards to guarantee 100% clickability
    const cardBindings = [
        { sel: ".card-predictor, #card-predictor-btn", fn: showPredictorState },
        { sel: ".card-library, #card-library-btn", fn: showPinnedLibraryState },
        { sel: ".card-browse, #card-browse-btn", fn: showBrowseState },
        { sel: ".card-leaderboard, #card-leaderboard-btn", fn: showLeaderboardState }
    ];

    cardBindings.forEach(binding => {
        document.querySelectorAll(binding.sel).forEach(el => {
            el.addEventListener("click", binding.fn);
            el.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    binding.fn();
                }
            });
        });
    });

    async function fetchLeaderboard() {
        const tbody = document.getElementById("leaderboard-tbody");
        const podiumBox = document.getElementById("leaderboard-podium-box");
        const userRankStrip = document.getElementById("user-live-rank-strip");
        const liveCountLabel = document.getElementById("leaderboard-live-count");
        if (!tbody) return;

        try {
            const userEmail = (currentUser && currentUser.email) ? currentUser.email : "";
            const res = await fetch("/api/leaderboard" + (userEmail ? `?email=${encodeURIComponent(userEmail)}` : ""));
            const data = await res.json();

            if (liveCountLabel) {
                const count = data.total_active_students || (data.leaderboard ? data.leaderboard.length : 0);
                liveCountLabel.textContent = `LIVE TRACKING • ${count} ACTIVE STUDENT${count === 1 ? '' : 'S'}`;
            }

            // 1. Render Top Podium Cards for Real Users
            if (podiumBox) {
                const podium = data.top_podium || [];
                if (podium.length > 0) {
                    const crownIcons = ["👑 1st", "🥈 2nd", "🥉 3rd"];
                    const podiumClasses = ["podium-gold", "podium-silver", "podium-bronze"];
                    
                    let podiumHtml = podium.map((p, idx) => `
                        <div class="podium-card-item ${podiumClasses[idx] || ''}">
                            <div class="podium-avatar-wrapper">
                                <div class="podium-avatar-img" style="background-image: url('${p.avatar_url}');"></div>
                                <span class="podium-crown-badge">${crownIcons[idx] || '#' + (idx + 1)}</span>
                            </div>
                            <div class="podium-name">${p.name || 'Bennett Student'}</div>
                            <span class="podium-dept-badge">${p.department || 'CSE'}</span>
                            <div class="podium-score">${p.contribution_score} pts</div>
                            <div class="podium-streak">🔥 ${p.current_streak} Day Streak</div>
                        </div>
                    `).join("");

                    for (let i = podium.length; i < 3; i++) {
                        podiumHtml += `
                            <div class="podium-card-item" style="border: 1px dashed rgba(255,255,255,0.15); background: rgba(255,255,255,0.02); opacity: 0.7;">
                                <div class="podium-avatar-wrapper">
                                    <div class="podium-avatar-img" style="background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; font-size: 20px;">✨</div>
                                    <span class="podium-crown-badge" style="background: rgba(255,255,255,0.1); color: #94a3b8;">${crownIcons[i]}</span>
                                </div>
                                <div class="podium-name" style="color: #94a3b8;">Position Open</div>
                                <span class="podium-dept-badge" style="background: transparent; border: 1px solid rgba(255,255,255,0.1); color: #64748b;">Claim Rank</span>
                                <div class="podium-score" style="color: #64748b; font-size: 13px;">Upload notes to rank</div>
                            </div>
                        `;
                    }

                    podiumBox.innerHTML = podiumHtml;
                    podiumBox.style.display = "grid";
                } else {
                    podiumBox.style.display = "none";
                }
            }

            // 2. Render Current User Live Rank Card Strip
            if (userRankStrip) {
                if (data.user_rank) {
                    const ur = data.user_rank;
                    userRankStrip.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 44px; height: 44px; border-radius: 50%; background-image: url('${ur.avatar_url}'); background-size: cover; border: 2px solid #ff6b00;"></div>
                            <div>
                                <div style="font-size: 14.5px; font-weight: 700; color: #ffffff;">${ur.name} <span style="font-size: 11px; padding: 2px 6px; background: rgba(255,107,0,0.2); border-radius: 4px; color: #ff6b00; margin-left: 4px;">YOU</span></div>
                                <div style="font-size: 12px; color: #94a3b8;">Department: <strong>${ur.department || 'CSE'}</strong> &bull; Streak: <strong>🔥 ${ur.current_streak} Days</strong></div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 18px; font-weight: 800; color: #ff6b00;">Rank #${ur.rank}</div>
                            <div style="font-size: 13px; font-weight: 700; color: #fbbf24;">${ur.contribution_score} Points</div>
                        </div>
                    `;
                    userRankStrip.style.display = "flex";
                } else {
                    userRankStrip.style.display = "none";
                }
            }

            // 3. Render Leaderboard Table Roster
            tbody.innerHTML = "";
            const leaderboard = data.leaderboard || [];
            if (leaderboard.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" style="padding: 30px; text-align: center; color: #a1a1aa;">
                            No active rankings logged yet. Upload notes, solve doubts, or take practice tests to earn points!
                        </td>
                    </tr>
                `;
                return;
            }

            leaderboard.forEach((item, index) => {
                const rank = item.rank || (index + 1);
                let rankBadgeClass = "rank-badge";
                let rankIcon = `#${rank}`;

                if (rank === 1) { rankBadgeClass += " rank-1"; rankIcon = "🥇 #1"; }
                else if (rank === 2) { rankBadgeClass += " rank-2"; rankIcon = "🥈 #2"; }
                else if (rank === 3) { rankBadgeClass += " rank-3"; rankIcon = "🥉 #3"; }

                const isMe = item.is_current_user;
                const tr = document.createElement("tr");
                if (isMe) tr.className = "current-user-highlight";

                tr.innerHTML = `
                    <td style="text-align: center;"><span class="${rankBadgeClass}">${rankIcon}</span></td>
                    <td>
                        <div class="leaderboard-user-cell" style="display: flex; align-items: center; gap: 10px;">
                            <div class="leaderboard-avatar" style="width: 32px; height: 32px; border-radius: 50%; background-image: url('${item.avatar_url}'); background-size: cover; border: 1px solid rgba(255,255,255,0.15);"></div>
                            <div>
                                <span style="font-weight: 600; color: #ffffff;">${item.name || 'Bennett Student'}</span>
                                ${isMe ? '<span style="font-size: 10.5px; padding: 1px 5px; background: rgba(255,107,0,0.25); border-radius: 4px; color: #ff6b00; margin-left: 4px; font-weight: 700;">YOU</span>' : ''}
                            </div>
                        </div>
                    </td>
                    <td style="text-align: center;"><span class="leaderboard-dept-pill">${item.department || 'CSE'}</span></td>
                    <td style="text-align: right; font-weight: 700; color: #fbbf24;">${item.contribution_score} pts</td>
                    <td style="text-align: right; font-weight: 600; color: #f97316;">🔥 ${item.current_streak} Day${item.current_streak === 1 ? '' : 's'}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Error fetching leaderboard:", e);
        }
    }

    window.fetchLeaderboard = fetchLeaderboard;

    async function fetchUserStats() {
        if (!currentUser || !currentUser.email) return;

        try {
            const res = await fetch(`/api/user/stats?email=${encodeURIComponent(currentUser.email)}`);
            const data = await res.json();

            if (data && data.status === "success") {
                const streakDisplay = document.getElementById("user-streak-display");
                const scoreDisplay = document.getElementById("user-score-display");
                const statsName = document.getElementById("stats-user-name");
                const statsEmail = document.getElementById("stats-user-email");
                const statsAvatar = document.getElementById("stats-user-avatar");

                if (streakDisplay) streakDisplay.textContent = `${data.current_streak} Day${data.current_streak === 1 ? '' : 's'} Streak`;
                if (scoreDisplay) scoreDisplay.textContent = `${data.contribution_score} Points`;
                if (statsName) statsName.textContent = currentUser.name || data.name || "Student User";
                if (statsEmail) statsEmail.textContent = currentUser.email;

                if (statsAvatar) {
                    const avatarUrl = currentUser.avatar_url || currentUser.picture || `https://api.dicebear.com/7.x/bottts/svg?seed=${currentUser.email}`;
                    statsAvatar.style.backgroundImage = `url('${avatarUrl}')`;
                }
            }
        } catch (e) {
            console.error("Error fetching user stats:", e);
        }
    }

    window.fetchUserStats = fetchUserStats;

    const allSubjectsList = [
        "Computational Thinking & Programming",
        "Engineering Calculus",
        "Introduction to Electricals & Electronics",
        "Electromagnetism & Mechanics",
        "Linear Algebra & Ordinary Differential Equation",
        "Digital Design",
        "Discrete Mathematical Structure",
        "OOPS using Java",
        "Probability & Statistics",
        "Statistical Machine Learning",
        "Information Management System",
        "DSA using C++",
        "Computer Networks",
        "Operating Systems",
        "DAA",
        "Microprocessor",
        "Artificial Intelligence",
        "Fullstack Development",
        "Cyber Security",
        "Quantum Computing",
        "UI/UX Design",
        "Cloud Computing",
        "Blockchain",
        "DevOps"
    ];

    function updateBrowseSubjectOptions() {
        const subSelect = document.getElementById("browse-subject-select");
        if (!subSelect) return;

        const currentSub = subSelect.value;
        const fileSubs = allCachedFiles.map(f => typeof f === 'object' ? f.subject : null).filter(Boolean);
        const availableSubjects = Array.from(new Set([...allSubjectsList, ...fileSubs]));

        subSelect.innerHTML = `<option value="">All Engineering Subjects (${availableSubjects.length})</option>`;
        availableSubjects.forEach(sub => {
            const opt = document.createElement("option");
            opt.value = sub;
            opt.textContent = sub;
            if (sub === currentSub) opt.selected = true;
            subSelect.appendChild(opt);
        });
    }

    function isFileUploadedByCurrentUser(fileObj) {
        const activeUser = currentUser || window.currentUser;
        if (!activeUser || !activeUser.email) return false;
        
        const fileUserEmail = (typeof fileObj === 'object' && fileObj.user_email) ? fileObj.user_email.toLowerCase().trim() : "";
        const currentEmail = activeUser.email.toLowerCase().trim();

        // STRICT EXACT EMAIL MATCH ONLY — ZERO FUZZY OR SURNAME MATCHING
        return Boolean(currentEmail && fileUserEmail && currentEmail === fileUserEmail);
    }

    // ----------------------------------------------------
    // Sidebar Pinned Folders Management (Personalized)
    // ----------------------------------------------------
    function getSidebarPinnedFilenames() {
        if (!currentUser) return [];
        const userKey = (currentUser.email || currentUser.name || "user").toLowerCase().trim();
        const key = `docpilot_pinned_sidebar_${userKey}`;
        try {
            return JSON.parse(localStorage.getItem(key) || "[]");
        } catch(e) {
            return [];
        }
    }

    function isFilePinnedInSidebar(filename) {
        return getSidebarPinnedFilenames().includes(filename);
    }

    function toggleSidebarPinFile(filename) {
        if (!currentUser) {
            alert("Please sign in to pin documents to your sidebar Pinned Folders.");
            return;
        }
        const userKey = (currentUser.email || currentUser.name || "user").toLowerCase().trim();
        const key = `docpilot_pinned_sidebar_${userKey}`;
        let pinned = getSidebarPinnedFilenames();
        if (pinned.includes(filename)) {
            pinned = pinned.filter(f => f !== filename);
        } else {
            pinned.push(filename);
        }
        localStorage.setItem(key, JSON.stringify(pinned));
        renderFilesUI();
        renderBrowseTable();
    }

    function renderBrowseTable() {
        const tbody = document.getElementById("browse-files-tbody");
        if (!tbody) return;

        tbody.innerHTML = "";

        const searchQuery = (document.getElementById("browse-search-input")?.value || "").toLowerCase().trim();
        const chosenSem = document.getElementById("browse-semester-select")?.value || "";
        const chosenSub = document.getElementById("browse-subject-select")?.value || "";
        const chosenType = document.getElementById("browse-filetype-select")?.value || "";

        const filtered = allCachedFiles.filter(fileObj => {
            const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === true);
            if (isPrivate) return false; // Private library files do not appear in public Shared Catalog

            const filename = (typeof fileObj === 'string' ? fileObj : fileObj.filename || "").toLowerCase();
            const uploaderName = (typeof fileObj === 'object' && fileObj.user_name ? fileObj.user_name : "").toLowerCase();
            const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "";
            const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "";
            const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "";

            if (searchQuery) {
                const subLower = subject.toLowerCase();
                const typeLower = fileType.toLowerCase();
                const semLower = semester.toLowerCase();
                const matchesSearch = filename.includes(searchQuery) ||
                                      subLower.includes(searchQuery) ||
                                      typeLower.includes(searchQuery) ||
                                      semLower.includes(searchQuery) ||
                                      uploaderName.includes(searchQuery);
                if (!matchesSearch) return false;
            }

            if (chosenSem && semester !== chosenSem) return false;
            if (chosenSub && subject !== chosenSub) return false;
            if (chosenType && fileType !== chosenType) return false;
            return true;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <div class="browse-empty-state">
                    <span style="font-size: 28px;">📂</span>
                    <p style="margin: 0; color: #a1a1aa; font-size: 14px;">No uploaded documents found for the selected Semester / Subject / Type filters.</p>
                </div>
            `;
            return;
        }

        filtered.forEach(fileObj => {
            const filename = typeof fileObj === 'string' ? fileObj : fileObj.filename;
            const uploaderName = typeof fileObj === 'object' && fileObj.user_name ? fileObj.user_name : "Anonymous Student";
            const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "General Engineering";
            const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "Semester 1";
            const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "Notes";
            const examType = typeof fileObj === 'object' && fileObj.exam_type ? fileObj.exam_type : "Other";
            const sizeKb = typeof fileObj === 'object' && fileObj.size_bytes ? Math.round(fileObj.size_bytes / 1024) + " KB" : "Document";
            const uploadedAt = typeof fileObj === 'object' && fileObj.uploaded_at ? fileObj.uploaded_at.split("T")[0] : "Recently";
            const isPinned = isFilePinnedInSidebar(filename);

            const card = document.createElement("div");
            card.className = "browse-doc-card";
            card.innerHTML = `
                <div class="doc-card-top">
                    <div class="browse-pdf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <div class="doc-card-tags">
                        <span class="filetype-badge">${fileType}</span>
                        ${examType && examType !== "Other" ? `<span class="examtype-badge">${examType}</span>` : ''}
                    </div>
                </div>

                <a href="/view/${encodeURIComponent(filename)}" target="_blank" class="browse-file-title" title="${filename}">
                    ${filename}
                </a>

                <div class="doc-card-curriculum">
                    <div class="doc-card-subject">${subject}</div>
                    <div class="doc-card-semester">${semester}</div>
                </div>

                <div class="doc-card-meta">
                    <div class="meta-row">
                        <span class="meta-label">Uploaded By</span>
                        <span class="meta-value">${uploaderName}</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Date & Size</span>
                        <span class="meta-value">${uploadedAt} (${sizeKb})</span>
                    </div>
                </div>

                <div class="doc-card-actions">
                    <button type="button" class="btn-download-file btn-download-doc" data-filename="${filename}" onclick="downloadDocumentFile('${escapeHtmlLocal(filename).replace(/'/g, "\\'")}', 0)" title="Download File">
                        <span>⬇ Download</span>
                    </button>
                    <a href="/view/${encodeURIComponent(filename)}?is_private=0" target="_blank" class="btn-open-browse-pdf" title="View Document">
                        <span>View</span>
                    </a>
                    <button type="button" class="btn-chat-with-doc btn-browse-chat" data-filename="${filename}" title="Chat with Document">
                        <span>Chat</span>
                    </button>
                    <button type="button" class="btn-browse-pin btn-pin-browse ${isPinned ? 'active-pinned' : ''}" data-filename="${filename}" title="${isPinned ? 'Unpin from Sidebar Pinned Folders' : 'Pin to Sidebar'}">
                        <span>${isPinned ? 'Pinned' : 'Pin'}</span>
                    </button>
                    <button type="button" class="btn-browse-report btn-report-browse" data-filename="${filename}" title="Report file to moderation">
                        <span>Report</span>
                    </button>
                </div>
            `;

            const btnChat = card.querySelector(".btn-browse-chat");
            if (btnChat) {
                btnChat.addEventListener("click", () => {
                    startNewChatWithDoc(filename);
                });
            }

            const btnPinBrowse = card.querySelector(".btn-pin-browse");
            if (btnPinBrowse) {
                btnPinBrowse.addEventListener("click", () => {
                    toggleSidebarPinFile(filename);
                });
            }

            const btnReportBrowse = card.querySelector(".btn-report-browse");
            if (btnReportBrowse) {
                btnReportBrowse.addEventListener("click", () => {
                    openReportModal(filename);
                });
            }

            tbody.appendChild(card);
        });
    }

    function renderChatWelcomeBanner() {
        if (!chatMessages) return;
        
        let userName = "Student";
        if (currentUser && currentUser.name) {
            userName = currentUser.name.trim();
            userName = userName.split(" ").map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(" ");
        }

        chatMessages.innerHTML = `
            <div class="chat-welcome-card" id="chat-welcome-card">
                <div class="chat-welcome-badge">BU Prepz AI Assistant</div>
                <h2 class="chat-welcome-title">Welcome back, <span class="user-highlight-name">${userName}</span></h2>
                <p class="chat-welcome-subtitle">Ask questions, summarize uploaded study notes, or solve engineering tutorial problems.</p>
                
                <div class="welcome-suggestions-grid">
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Summarize key formulas, definitions, and PYQ exam questions from my uploaded notes.')">
                        <span class="suggest-text">Exam Prep & Formulas Summary</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Help me solve step-by-step tutorial sheet assignments and explain underlying equations.')">
                        <span class="suggest-text">Assignment & Math Helper</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Explain core concepts in Operating Systems, DBMS, DSA, and Networks with clear examples.')">
                        <span class="suggest-text">Engineering Concept Explainer</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Create a 5-minute quick revision cheat sheet and key takeaways from my uploaded PDF documents.')">
                        <span class="suggest-text">5-Min Quick Revision Sheet</span>
                    </button>
                </div>
            </div>
        `;
    }

    window.sendQuickPrompt = function(promptText) {
        if (userInput && chatForm) {
            userInput.value = promptText;
            chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
    };

    function startNewChat() {
        currentThreadId = null;
        localStorage.removeItem("currentThreadId");
        if (userInput) {
            userInput.value = "";
            userInput.style.height = "auto";
        }

        if (threadsList) {
            threadsList.querySelectorAll(".thread-item.active").forEach(item => {
                item.classList.remove("active");
            });
        }

        showChatState();
        renderChatWelcomeBanner();
        updateHeaderTitle("Fresh Chat");
        if (userInput) userInput.focus();
    }

    function startNewChatWithDoc(filename) {
        startNewChat();

        if (userInput) {
            userInput.value = `Tell me key details, summary, and main points from ${filename}`;
            userInput.focus();
            if (chatForm) {
                setTimeout(() => {
                    chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
                }, 100);
            }
        }
    }

    // New Chat & Library Bindings
    if (navNewChat) {
        navNewChat.addEventListener("click", (e) => {
            e.preventDefault();
            showLandingState();
        });
    }
    if (navPinnedLibrary) {
        navPinnedLibrary.addEventListener("click", (e) => {
            e.preventDefault();
            showPinnedLibraryState();
        });
    }
    if (btnLibraryUploadTrigger) {
        btnLibraryUploadTrigger.addEventListener("click", () => openUploadModal("library"));
    }
    if (navNewChatBtn) {
        navNewChatBtn.addEventListener("click", (e) => {
            e.preventDefault();
            startNewChat();
            updateHeaderTitle("Fresh Chat");
        });
    }
    if (headerNewChatBtn) {
        headerNewChatBtn.addEventListener("click", (e) => {
            e.preventDefault();
            startNewChat();
            updateHeaderTitle("Fresh Chat");
        });
    }

    // ----------------------------------------------------
    // AI Exam Question Paper Predictor Logic
    // ----------------------------------------------------
    function updatePredictorSubjectOptions() {
        if (!predictorSubjectSelect) return;
        const currentSub = predictorSubjectSelect.value;
        const fileSubs = allCachedFiles ? allCachedFiles.map(f => typeof f === 'object' ? f.subject : null).filter(Boolean) : [];
        const availableSubjects = Array.from(new Set([...allSubjectsList, ...fileSubs]));

        predictorSubjectSelect.innerHTML = "";
        availableSubjects.forEach(sub => {
            const opt = document.createElement("option");
            opt.value = sub;
            opt.textContent = sub;
            if (sub === currentSub) opt.selected = true;
            predictorSubjectSelect.appendChild(opt);
        });
    }

    function formatPaperMarkdown(mdText) {
        if (!mdText) return "";

        // 1. Strip reasoning traces from DeepSeek / Gemini / Groq models
        let cleanMd = mdText.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
        if (cleanMd.startsWith("```markdown")) cleanMd = cleanMd.slice(11).trim();
        if (cleanMd.startsWith("```")) cleanMd = cleanMd.slice(3).trim();
        if (cleanMd.endsWith("```")) cleanMd = cleanMd.slice(0, -3).trim();

        // 2. Remove backslash escapes like \* and \_
        cleanMd = cleanMd.replace(/\\([*_`\[\]\(\)])/g, "$1");

        // 3. Ensure double newlines before and after every markdown table block so parser recognizes it
        cleanMd = cleanMd.replace(/([^\n])\n(\|[^\n]+\|\n\|[\s\-:]+\|\n)/g, "$1\n\n$2");
        cleanMd = cleanMd.replace(/(\|[^\n]+\|)\n([^\n\|])/g, "$1\n\n$2");

        // 4. Parse Markdown with marked.js
        let html = "";
        try {
            if (typeof marked !== "undefined") {
                if (typeof marked.setOptions === "function") {
                    marked.setOptions({ gfm: true, breaks: false });
                }
                if (typeof marked.parse === "function") {
                    html = marked.parse(cleanMd);
                } else if (typeof marked === "function") {
                    html = marked(cleanMd);
                }
            }
        } catch (e) {
            console.warn("Marked parse warning:", e);
        }

        // Fallback manual table converter if raw pipe table remained unparsed
        if (!html || (!html.includes("<table") && cleanMd.includes("|---"))) {
            const lines = cleanMd.split("\n");
            let inTable = false;
            let tableHtml = "";
            let processedLines = [];

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.startsWith("|") && line.endsWith("|")) {
                    if (!inTable) {
                        inTable = true;
                        tableHtml = '<div class="table-responsive"><table class="exam-insights-table"><thead><tr>';
                        const headers = line.split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
                        headers.forEach(h => { tableHtml += `<th>${h.trim()}</th>`; });
                        tableHtml += '</tr></thead><tbody>';
                        i++; // Skip delimiter row |:---|:---|
                        continue;
                    } else {
                        const cells = line.split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
                        tableHtml += '<tr>';
                        cells.forEach((c, cIdx) => {
                            let cContent = c.trim();
                            if (cIdx === 1) cContent = `<strong>${cContent}</strong>`;
                            else if (cIdx === 2) cContent = `<span class="exam-prob-chip" style="margin:0;">⚡ ${cContent}</span>`;
                            tableHtml += `<td>${cContent}</td>`;
                        });
                        tableHtml += '</tr>';
                    }
                } else {
                    if (inTable) {
                        inTable = false;
                        tableHtml += '</tbody></table></div>';
                        processedLines.push(tableHtml);
                    }
                    processedLines.push(line);
                }
            }
            if (inTable) {
                tableHtml += '</tbody></table></div>';
                processedLines.push(tableHtml);
            }
            cleanMd = processedLines.join("\n\n");
            if (typeof marked !== "undefined" && typeof marked.parse === "function") {
                html = marked.parse(cleanMd);
            }
        }

        // 5. Format Frequency, Probability & Marks Badges into Clean UI Chips
        html = html.replace(/\[\s*Frequency:\s*([^\]]+)\]/gi, '<div class="exam-badge-row"><span class="exam-freq-chip">🎯 Frequency: $1</span></div>');
        html = html.replace(/\[\s*Probability:\s*([^\]]+)\]/gi, '<span class="exam-prob-chip">⚡ Probability: $1</span>');
        html = html.replace(/`\[(\d+)\s*Marks?\]`/gi, '<span class="exam-marks-badge">[$1 Marks]</span>');
        html = html.replace(/\[(\d+)\s*Marks?\]/gi, '<span class="exam-marks-badge">[$1 Marks]</span>');

        // Style questions Q1, Q2, etc.
        html = html.replace(/<strong>\[?(Q\d+)\]?<\/strong>/gi, '<span class="exam-q-num">$1</span>');

        return html;
    }

    function downloadPredictedPDF() {
        const paperElement = document.getElementById("predicted-paper-document");
        if (!paperElement) return;

        const sub = predictorSubjectSelect ? predictorSubjectSelect.value : "Exam";
        const sem = predictorSemesterSelect ? predictorSemesterSelect.value : "Sem";
        const examType = predictorExamTypeSelect ? predictorExamTypeSelect.value : "Mid-Sem";
        const filename = `Bennett_University_${sub.replace(/\s+/g, '_')}_${sem.replace(/\s+/g, '_')}_${examType.replace(/\s+/g, '_')}_Predicted_Paper.pdf`;

        // Create clean, print-styled wrapper for high quality PDF rendering
        const printClone = paperElement.cloneNode(true);
        printClone.classList.add("pdf-print-export-mode");

        const wrapper = document.createElement("div");
        wrapper.style.position = "absolute";
        wrapper.style.left = "-9999px";
        wrapper.style.top = "0";
        wrapper.style.width = "794px"; // A4 standard width at 96 DPI
        wrapper.style.background = "#ffffff";
        wrapper.style.color = "#111827";
        wrapper.style.padding = "32px";
        wrapper.appendChild(printClone);
        document.body.appendChild(wrapper);

        if (window.html2pdf) {
            const opt = {
                margin:       [10, 10, 10, 10],
                filename:     filename,
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true, letterRendering: true, backgroundColor: '#ffffff' },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
                pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
            };
            html2pdf().set(opt).from(printClone).save().then(() => {
                document.body.removeChild(wrapper);
            }).catch(err => {
                console.error("PDF generation error:", err);
                document.body.removeChild(wrapper);
                window.print();
            });
        } else {
            document.body.removeChild(wrapper);
            window.print();
        }
    }

    function filterTopicPill(btnEl, term) {
        document.querySelectorAll(".topic-pill").forEach(p => p.classList.remove("active"));
        if (btnEl) btnEl.classList.add("active");
        
        const searchInput = document.getElementById("predictor-search-input");
        if (searchInput) searchInput.value = term;
        filterPredictedPaper(term);
    }

    function filterPredictedPaper(query) {
        if (!predictedPaperBody) return;
        
        if (!window._rawPaperMarkdownHtml && predictedPaperBody.innerHTML) {
            window._rawPaperMarkdownHtml = predictedPaperBody.innerHTML;
        }

        const rawHtml = window._rawPaperMarkdownHtml || predictedPaperBody.innerHTML;
        const q = (query || "").toLowerCase().trim();
        const searchCountBadge = document.getElementById("predictor-search-count");

        if (!q) {
            predictedPaperBody.innerHTML = rawHtml;
            if (searchCountBadge) {
                searchCountBadge.classList.add("hidden");
                searchCountBadge.textContent = "";
            }
            return;
        }

        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = rawHtml;

        const nodes = tempDiv.querySelectorAll("p, li, h1, h2, h3, h4, div");
        let matches = 0;

        nodes.forEach(node => {
            const text = (node.textContent || "").toLowerCase();
            let isMatch = false;

            if (q === "theory") {
                isMatch = text.includes("theory") || text.includes("explain") || text.includes("define") || 
                          text.includes("discuss") || text.includes("differentiate") || text.includes("describe") || 
                          text.includes("concept") || text.includes("architecture");
            } else if (q === "numerical") {
                isMatch = text.includes("numerical") || text.includes("calculate") || text.includes("solve") || 
                          text.includes("compute") || text.includes("find") || text.includes("problem") || 
                          text.includes("equation") || text.includes("value");
            } else {
                isMatch = text.includes(q);
            }

            if (isMatch) {
                matches++;
                node.style.backgroundColor = "rgba(139, 92, 246, 0.15)";
                node.style.borderLeft = "4px solid #8b5cf6";
                node.style.paddingLeft = "8px";
                node.style.borderRadius = "4px";
                node.style.opacity = "1";
            } else if (node.children.length === 0) {
                node.style.opacity = "0.3";
            }
        });

        predictedPaperBody.innerHTML = tempDiv.innerHTML;

        if (searchCountBadge) {
            searchCountBadge.classList.remove("hidden");
            searchCountBadge.textContent = `${matches} match${matches === 1 ? '' : 'es'} found`;
        }
    }

    window.filterPredictedPaper = filterPredictedPaper;
    window.filterTopicPill = filterTopicPill;

    if (predictorSemesterSelect) {
        predictorSemesterSelect.addEventListener("change", updatePredictorSubjectOptions);
    }
    if (btnGeneratePredictor) {
        btnGeneratePredictor.addEventListener("click", generatePredictedPaper);
    }
    if (btnDownloadPredictedPdf) {
        btnDownloadPredictedPdf.addEventListener("click", downloadPredictedPDF);
    }
    if (navExamPredictor) {
        navExamPredictor.addEventListener("click", (e) => {
            e.preventDefault();
            showPredictorState();
        });
    }
    if (navLeaderboard) {
        navLeaderboard.addEventListener("click", (e) => {
            e.preventDefault();
            showLeaderboardState();
        });
    }
    if (btnWarningUploadPyq) {
        btnWarningUploadPyq.addEventListener("click", () => {
            openUploadModal("browse");
            const typeSel = document.getElementById("upload-filetype-select");
            if (typeSel) typeSel.value = "PYQ";
            if (predictorSemesterSelect) {
                const modalSemSel = document.getElementById("upload-semester-select");
                if (modalSemSel) modalSemSel.value = predictorSemesterSelect.value;
            }
            if (predictorSubjectSelect) {
                const modalSubSel = document.getElementById("upload-subject-select");
                if (modalSubSel) modalSubSel.value = predictorSubjectSelect.value;
            }
            if (predictorExamTypeSelect) {
                const modalExamSel = document.getElementById("upload-examtype-select");
                if (modalExamSel) modalExamSel.value = predictorExamTypeSelect.value;
            }
            const scopeRepo = document.getElementById("upload-scope-repo");
            if (scopeRepo) {
                scopeRepo.checked = true;
                if (window.updateScopeToggleVisuals) window.updateScopeToggleVisuals(0);
            }
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
                    ${thread.is_pinned ? `<span class="pin-badge" style="margin-left:auto; font-size:10px;">Pinned</span>` : ""}
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

        } catch (e) {
            console.error("Error loading history:", e);
            showLandingState();
        }
    }

    if (typeof marked !== "undefined" && typeof marked.setOptions === "function") {
        try {
            marked.setOptions({ breaks: true, gfm: true });
        } catch(e) {}
    }

    function formatChatMarkdown(text) {
        if (!text) return "";
        let cleanText = text;
        if (typeof marked !== "undefined" && typeof marked.parse === "function") {
            try {
                return marked.parse(cleanText);
            } catch (e) {
                console.error("Marked parse error:", e);
            }
        }

        let formatted = cleanText
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        formatted = formatted.replace(/```([\s\S]+?)```/g, (match, p1) => `<div class="code-block-wrapper"><pre><code>${p1}</code></pre></div>`);
        formatted = formatted.replace(/`([^`\n]+?)`/g, "<code>$1</code>");
        formatted = formatted.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
        formatted = formatted.replace(/\*([^*]+?)\*/g, "<em>$1</em>");
        formatted = formatted.replace(/^### (.*$)/gim, "<h3>$1</h3>");
        formatted = formatted.replace(/^## (.*$)/gim, "<h2>$1</h2>");
        formatted = formatted.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-yt-link">🎬 $1 ↗</a>');
        formatted = formatted.replace(/\n\n+/g, "</p><p>");
        formatted = formatted.replace(/\n/g, "<br>");
        return `<p>${formatted}</p>`;
    }

    function appendMessage(role, content) {
        const msgDiv = document.createElement("div");
        const isUser = role === "user";
        msgDiv.className = `chat-message-item ${isUser ? "user-chat-item" : "ai-chat-item"}`;
        
        let userName = "You";
        if (currentUser && currentUser.name) {
            userName = currentUser.name.trim().split(" ")[0];
        }

        const avatarHtml = isUser 
            ? `<div class="msg-avatar-icon user-avatar-bubble"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div>`
            : `<div class="msg-avatar-icon ai-avatar-bubble"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></div>`;

        const headerHtml = isUser
            ? `<div class="msg-header-line"><span class="msg-author-tag">${userName}</span></div>`
            : `<div class="msg-header-line"><span class="msg-author-tag ai-tag">BU Prepz AI</span><span class="msg-ai-pill">Assistant</span></div>`;

        msgDiv.innerHTML = `
            ${avatarHtml}
            <div class="msg-bubble-card">
                ${headerHtml}
                <div class="msg-text-content">
                    ${role === "assistant" && !content ? `
                        <div class="qubi-typing-indicator">
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                            <span class="typing-dot"></span>
                            <span class="typing-label">Analyzing syllabus & preparing response...</span>
                        </div>
                    ` : formatChatMarkdown(content)}
                </div>
            </div>
        `;
        
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        
        const bodyContent = msgDiv.querySelector(".msg-text-content");
        return bodyContent || msgDiv;
    }

    // Submit handler (Stream-friendly buffering with smooth typewriter rendering)
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
        let accumulatedResponse = "";
        let displayedResponse = "";
        let isStreamFinished = false;
        let renderTimer = null;

        function updateBubbleUI(text, isDone) {
            if (!text) return;
            let formatted = formatChatMarkdown(text);
            if (isDone) {
                assistantBubble.innerHTML = formatted;
            } else {
                const cursorHtml = '<span class="streaming-cursor">▌</span>';
                const trimmed = formatted.trim();
                if (trimmed.endsWith("</p>")) {
                    const idx = formatted.lastIndexOf("</p>");
                    formatted = formatted.slice(0, idx) + cursorHtml + formatted.slice(idx);
                } else {
                    formatted = formatted + cursorHtml;
                }
                assistantBubble.innerHTML = formatted;
            }
            scrollToBottom();
        }

        function startTypewriterLoop() {
            if (renderTimer) return;
            renderTimer = setInterval(() => {
                if (displayedResponse.length < accumulatedResponse.length) {
                    const diff = accumulatedResponse.length - displayedResponse.length;
                    const step = diff > 40 ? 8 : (diff > 20 ? 5 : (diff > 8 ? 3 : (diff > 3 ? 2 : 1)));
                    displayedResponse += accumulatedResponse.substr(displayedResponse.length, step);
                    updateBubbleUI(displayedResponse, false);
                } else if (isStreamFinished) {
                    clearInterval(renderTimer);
                    renderTimer = null;
                    updateBubbleUI(accumulatedResponse, true);
                    fetchThreads();
                    if (pendingVideoRec) {
                        const recToRender = pendingVideoRec;
                        pendingVideoRec = null;
                        setTimeout(() => renderVideoRecommendation(recToRender, assistantBubble), 100);
                    }
                }
            }, 20);
        }

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: queryText,
                    thread_id: currentThreadId,
                    user_email: currentUser ? currentUser.email : null
                })
            });

            fetchUserStats();

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let sseBuffer = "";
            let pendingVideoRec = null;

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
                            if (parsed.status && !accumulatedResponse) {
                                const typingLabel = assistantBubble.querySelector(".typing-label");
                                if (typingLabel) {
                                    typingLabel.textContent = parsed.status;
                                }
                            } else if (parsed.text) {
                                accumulatedResponse += parsed.text;
                                startTypewriterLoop();
                            } else if (parsed.concept_weakness) {
                                pendingConceptWeakness = parsed.concept_weakness;
                                console.log("[SSE CONCEPT WEAKNESS RECEIVED]", pendingConceptWeakness);
                                const cwToRender = pendingConceptWeakness;
                                setTimeout(() => {
                                    renderInChatConceptWeakness(cwToRender, assistantBubble);
                                }, 120);
                            } else if (parsed.video_rec) {
                                pendingVideoRec = parsed.video_rec;
                                console.log("[SSE VIDEO REC RECEIVED]", pendingVideoRec);
                                const recToRender = pendingVideoRec;
                                setTimeout(() => {
                                    renderVideoRecommendation(recToRender, assistantBubble);
                                }, 100);
                            } else if (parsed.error) {
                                if (renderTimer) clearInterval(renderTimer);
                                assistantBubble.innerHTML = `<span style="color:#ef4444;">Error: ${parsed.error}</span>`;
                            }
                        } catch (e) {}
                    }
                }
            }

            isStreamFinished = true;
            if (!renderTimer) {
                updateBubbleUI(accumulatedResponse, true);
                fetchThreads();
                if (pendingConceptWeakness) {
                    const cwToRender = pendingConceptWeakness;
                    setTimeout(() => renderInChatConceptWeakness(cwToRender, assistantBubble), 120);
                }
                if (pendingVideoRec) {
                    const recToRender = pendingVideoRec;
                    setTimeout(() => renderVideoRecommendation(recToRender, assistantBubble), 100);
                }
                fetchUserStats();
                if (window.fetchLeaderboard) window.fetchLeaderboard();
            }

        } catch (err) {
            if (renderTimer) clearInterval(renderTimer);
            assistantBubble.innerHTML = `<span style="color:#ef4444;">Error connecting to BU Prepz.</span>`;
            console.error(err);
        }
    });

    // ── Video Recommendation System (Bennett University Verified) ──────────────
    const KNOWN_PLAYLIST_FIRST_VIDEOS = {
        // 1st & 2nd Semester Courses
        "PLU6SqdYcYsfIJRl8mo2Rv1MpdvmVD0YyI": "WX6O9TiFYsA", // Gajendra Purohit Calculus
        "PLT3bOBUU3L9iw3yQWge_IjhXZlDgRGwyq": "bQ_B9cHBYfQ", // Pradeep Giri Academy Calculus
        "PLNKD1qB9ppttx4WuHV0TWRy5dWuVSKEtT": "A6Ad7VnSlZE", // Tikle's Academy Calculus
        "PLdM-WZokR4tbCBA4mkvfk2vOH12eRPT2Y": "BOlT6bM0jKU", // Vishwakarma Advanced Calculus
        "PL9RcWoqXmzaLTYUdnzKhF4bYug3GjGcEc": "Vd2UJiIPbag", // Umesh Dhande Network Theorems
        "PLBlnK6fEyqRgLR-hMp7wem-bdVN1iEhsh": "NEhH6C7Fzw4", // NESO Academy Analog Electronics / Circuits
        "PLPIwNooIb9vhiZRRq1fEWXvSLz7VMeqSh": "rttcOFKPphQ", // Perfect Computer Engineer Electronics
        "PLDN15nk5uLiCSOqr7-rUz6-GtdTAjlvul": "dZyKXdvzSz0", // Tikle's Academy Electronics
        "PLGjplNEQ1it8-0CmoljS5yeV-GlKSUEt0": "ERCMXc8x7mc", // Apna College Python
        "PLu0W_9lII9agwh1XjRt242xIpHhPT2llg": "7wnove7K-ZQ", // Code With Harry Python
        "PLDN4rrl48XKpZkf03iYFl-O29szjTrs_O": "0IAPZzGSbME", // Abdul Bari DSA
        "PLxCzCOWd7aiGz9donHRrE9I3Mwn6XdP8p": "bkSWJJZNgf8", // Gate Smashers OS
        "PLBlnK6fEyqRitWLDxMrzVQK8813oqG797": "vBURTt97EkA", // NESO Academy OS
        "PLT3bOBUU3L9hADhGPsZjSddwAC3BvJDnl": "3d6DsjIBzJ4", // Pradeep Giri Mechanics
        
        // 3rd Semester Courses
        "PLxCzCOWd7aiFAN6I8CuViBuCdJgiOkT2Y": "kBdlM6hNDAE", // Gate Smashers Information Management System (DBMS)
        "PLBlnK6fEyqRiyryTrbKHX1Sh9luYI0dhX": "OMwgGL3lHlI", // NESO Academy DBMS / Information Management
        "PLU6SqdYcYsfJPF-4HphQQ8OceDtqhlSW8": "qNGDD_Rh8ps", // Gajendra Purohit Probability & Statistics 2.0
        "PLn3Wz38keZOeMt_qcBF6jkv3kKfyBuuTr": "ze-ozGVF1j4", // Tending to Infinity Probability & Statistics
        "PLhLZ_zxDsyOIKbQfKFM05BLYRhUZ7JP-M": "uo34ZM030xQ", // Algorithm Unlocked Probability & Statistics
        "PLT3bOBUU3L9jex8hXzVAszMS8NOILa7IV": "Y0_260pKtkA", // Pradeep Giri Academy Probability & Statistics
        "PLfqMhTWNBTe137I_EPQd34TsgV6IO55pt": "z9bZufPHFLU", // Apna College Shradha Khapra C++ DSA
        "PLxgZQoSe9cg0df_GxVjz3DD_Gck5tMXAd": "bL-o2xBENY0", // College Wallah C++ and DSA Foundation
        "PLdo5W4Nhv31bbKJzrsKfMpo_grxuLl8LU": "AT14lCXuMKI", // Jenny's Lectures CS IT DSA Course
        "PLBlnK6fEyqRhqJPDXcvYlLfXPh37L89g3": "p2b2Vb-cYCs", // NESO Academy Discrete Mathematics
        "PLxCzCOWd7aiH2wwES9vPWsEL6ipTaUSl3": "YBb2oYIzXK0", // Gate Smashers Discrete Mathematics
        "PLT3bOBUU3L9j_VG5CICyWK_a4M0-nwwxy": "iZ3g7JdSjbw", // Pradeep Giri Academy Discrete Mathematics
        "3zOtLEeHygg": "3zOtLEeHygg",                         // Knowledge Gate Discrete Mathematics Full Course
        "PLxCzCOWd7aiGmXg4NoX6R31AsC5LeCPHe": "O0gtKDu_cJc", // Gate Smashers Digital Design
        "PLgwJf8NK-2e4OD-vicvzWT7wE8BZIQtEe": "ovHm8IHVR3Y", // Engineering Funda Digital Design
        "PLBlnK6fEyqRjMH3mWf6kwqiTbT798eAOm": "M0mx8S05v60", // NESO Academy Digital Design
        "PLmXKhU9FNesSfX1PVt4VGm-wbIKfemUWK": "pHNbm-4reIc", // Knowledge Gate Digital Design
        "PLU6SqdYcYsfI7Ebw_j-Vy8YKHdbHKP9am": "1XlT3Y2oyAU", // Gajendra Purohit Linear Algebra (Matrices & Rank)
        "PLT3bOBUU3L9ijgr3HbpphxsgNfBekbPZS": "7FJDp2n4wvg", // Pradeep Giri Academy Linear Algebra
        "PLU6SqdYcYsfJRZEK4BpuufOlIrQzWm-nP": "qqLwi27BJSA", // Gajendra Purohit Linear Algebra (Vector Spaces)
        "TLRiju0jFEI": "TLRiju0jFEI",                         // GATE Wallah Linear Algebra One-Shot
        "PLU6SqdYcYsfIuZVt20v-eNZBfFLENrM1F": "bjJZKTrCBNw", // Gajendra Purohit ODE First Order
        "PLU6SqdYcYsfJmqo86d12EoNNWKtAZqu8q": "McOc6OUC7Pc", // Gajendra Purohit Higher Order ODE & PDE
        "PLfqMhTWNBTe3LtFWcvwpqTkUSlB32kJop": "yRpLlJmRo2w", // Shradha Khapra Java Complete Course
        "PLDzeHZWIZsTqNW1gvXXAicBgku9uPZeOC": "X2NVOSNBbxU"  // Love Babbar Java Placement Course
    };

    function resolveYouTubeVideoId(url, channelName) {
        try {
            if (url) {
                const parsed = new URL(url);
                const listId = parsed.searchParams.get("list");
                const vid = parsed.searchParams.get("v");
                if (listId && KNOWN_PLAYLIST_FIRST_VIDEOS[listId]) {
                    return KNOWN_PLAYLIST_FIRST_VIDEOS[listId];
                }
                if (vid && vid.length === 11) {
                    return vid;
                }
                if (url.includes("youtu.be/")) {
                    const match = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
                    if (match && match[1]) return match[1];
                }
            }
        } catch (e) {}

        const ch = (channelName || "").toLowerCase();
        const u = (url || "").toLowerCase();
        if (ch.includes("babbar") || ch.includes("codehelp") || u.includes("pzeoc") || u.includes("dsehzwizstq")) return "X2NVOSNBbxU";
        if (ch.includes("gate wallah") || u.includes("tlriju0jfei")) return "TLRiju0jFEI";
        if (ch.includes("neso")) {
            if (u.includes("dbms") || u.includes("iyrytrbk") || u.includes("sql")) return "OMwgGL3lHlI";
            if (u.includes("rhqjpdx") || u.includes("discrete") || u.includes("dms")) return "p2b2Vb-cYCs";
            if (u.includes("rjmh3mw") || u.includes("digital") || u.includes("dld")) return "M0mx8S05v60";
            return "NEhH6C7Fzw4";
        }
        if (ch.includes("perfect computer")) return "rttcOFKPphQ";
        if (ch.includes("tikle")) {
            if (u.includes("nkd1qb9") || u.includes("differentiat") || u.includes("calculus")) return "A6Ad7VnSlZE";
            return "dZyKXdvzSz0";
        }
        if (ch.includes("engineers ki pathshala") || ch.includes("umesh dhande")) return "Vd2UJiIPbag";
        if (ch.includes("gate smashers")) {
            if (u.includes("h2wwes") || u.includes("discrete") || u.includes("dms")) return "YBb2oYIzXK0";
            if (u.includes("gmxg4no") || u.includes("digital") || u.includes("dld")) return "O0gtKDu_cJc";
            if (u.includes("fan6i8c") || u.includes("dbms") || u.includes("ims")) return "kBdlM6hNDAE";
            if (u.includes("os") || u.includes("gz9don")) return "bkSWJJZNgf8";
            return "kBdlM6hNDAE";
        }
        if (ch.includes("knowledge gate")) {
            if (u.includes("sfx1pvt") || u.includes("digital") || u.includes("dld")) return "pHNbm-4reIc";
            return "3zOtLEeHygg";
        }
        if (ch.includes("engineering funda") || ch.includes("funda")) return "ovHm8IHVR3Y";
        if (ch.includes("algorithm unlocked")) return "uo34ZM030xQ";
        if (ch.includes("gajendra purohit") || ch.includes("purohit")) {
            if (u.includes("iuzvt20") || u.includes("ode") || u.includes("flenrm1f")) return "bjJZKTrCBNw";
            if (u.includes("jmqo86") || u.includes("higher") || u.includes("azqu8q")) return "McOc6OUC7Pc";
            if (u.includes("i7ebw") || u.includes("matrices") || u.includes("matrix")) return "1XlT3Y2oyAU";
            if (u.includes("jrzek4") || u.includes("vector") || u.includes("linear")) return "qqLwi27BJSA";
            if (u.includes("u6sqdycysfij") || u.includes("calculus") || u.includes("differentiat")) return "WX6O9TiFYsA";
            return "qNGDD_Rh8ps";
        }
        if (ch.includes("tending to infinity")) return "ze-ozGVF1j4";
        if (ch.includes("pradeep giri")) {
            if (u.includes("jex8hxzv") || u.includes("noila7iv") || u.includes("probab") || u.includes("stat")) return "Y0_260pKtkA";
            if (u.includes("3yqwge") || u.includes("calculus") || u.includes("math")) return "bQ_B9cHBYfQ";
            if (u.includes("vg5cicy") || u.includes("discrete") || u.includes("dms")) return "iZ3g7JdSjbw";
            if (u.includes("ijgr3hb") || u.includes("linear") || u.includes("matrix")) return "7FJDp2n4wvg";
            return "3d6DsjIBzJ4";
        }
        if (ch.includes("jenny")) return "AT14lCXuMKI";
        if (ch.includes("apna college") || ch.includes("shradha") || ch.includes("shraddha")) {
            if (u.includes("3ltfwcvwp") || u.includes("b32kjop") || u.includes("java")) return "yRpLlJmRo2w";
            return "z9bZufPHFLU";
        }
        if (ch.includes("college wallah")) return "bL-o2xBENY0";
        if (ch.includes("harry")) return "7wnove7K-ZQ";
        if (ch.includes("abdul bari")) return "0IAPZzGSbME";
        if (ch.includes("vishwakarma")) return "BOlT6bM0jKU";

        return "rttcOFKPphQ";
    }

    function renderVideoRecommendation(rec, afterBubble) {
        if (!rec || !rec.videos || rec.videos.length === 0) return;

        const strengthConfig = {
            urgent: {
                label: "🚨 Recommended Faculty Lectures for Bennett Students",
                cls: "video-rec-urgent",
                icon: "🎬"
            },
            medium: {
                label: "💡 Recommended videos for this topic",
                cls: "video-rec-medium",
                icon: "📺"
            },
            light: {
                label: "✨ Optional: Video resources for this topic",
                cls: "video-rec-light",
                icon: "🎥"
            }
        };

        const cfg = strengthConfig[rec.strength] || strengthConfig.urgent;
        const topicLabel = rec.topic ? rec.topic.replace(/\b\w/g, l => l.toUpperCase()) : "This Topic";
        const attemptNote = rec.attempt_number && rec.attempt_number > 1
            ? `<span class="rec-attempt-badge">Attempt #${rec.attempt_number}</span>` : "";

        const intentInfo = rec.intent_reason ? `
            <div class="intent-info">
                ${attemptNote}
                <span class="intent-text">${rec.intent_reason}</span>
            </div>
        ` : "";

        const videosHtml = (rec.videos || []).map((v, i) => {
            const helpfulPct = v.helpful_percentage || (v.total_ratings > 0 ? Math.round(v.helpful_count / v.total_ratings * 100) : 92);
            const avgDur = v.avg_duration || 20;
            const ratingScore = v.rating || 4.8;
            const totalR = v.total_ratings || 18;
            const channelName = v.channel || v.channel_name || "Bennett Recommended";
            const instructorName = v.instructor ? `<p class="instructor"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:middle;margin-right:4px;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>${v.instructor}</p>` : "";
            const playlistUrl = v.playlist_url || v.url || `https://www.youtube.com/results?search_query=${encodeURIComponent(topicLabel + ' Bennett University')}`;

            const videoId = resolveYouTubeVideoId(playlistUrl, channelName);
            const thumbUrl = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;

            return `
                <div class="video-card">
                    <div class="video-rank">#${i + 1}</div>
                    <h4>${channelName}</h4>
                    ${instructorName}
                    <p class="topic">${v.topic || topicLabel}</p>
                    
                    <div class="video-poster-box" onclick="window.playVideoInApp(this, '${v.id || i}')" data-url="${playlistUrl}" data-title="${(v.topic || topicLabel)}" data-channel="${channelName}" style="position: relative; width: 100%; height: 165px; border-radius: 12px; overflow: hidden; background: #121519; margin: 10px 0; cursor: pointer; border: 1px solid rgba(255, 107, 0, 0.25);">
                        <img src="${thumbUrl}" alt="${channelName}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=600&auto=format&fit=crop&q=80';">
                        <div style="position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.75) 100%); display: flex; flex-direction: column; align-items: center; justify-content: center;">
                            <div style="width: 50px; height: 50px; border-radius: 50%; background: #ef4444; color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 22px rgba(239, 68, 68, 0.85);">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                            <span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.85); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">⏱️ ${avgDur} min</span>
                        </div>
                    </div>

                    <div class="video-stats">
                        <span class="rating">⭐ ${ratingScore}/5 (${totalR} ratings)</span>
                        <span class="helpful">✅ ${helpfulPct}% helpful</span>
                    </div>

                    <div class="video-actions">
                        <button type="button" class="btn-watch-inapp" onclick="window.playVideoInApp(this, '${v.id || i}')" data-url="${playlistUrl}" data-title="${(v.topic || topicLabel)}" data-channel="${channelName}">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                            <span>In-App Player</span>
                        </button>
                        <a href="${playlistUrl}" target="_blank" rel="noopener noreferrer" class="btn-watch-yt">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                            <span>YouTube ↗</span>
                        </a>
                    </div>

                    <div class="video-feedback" id="feedback-${v.id || i}">
                        <button onclick="ratePlaylist(${v.id || 0}, 5, true, this)" class="btn-helpful">👍 Helpful</button>
                        <button onclick="ratePlaylist(${v.id || 0}, 2, false, this)" class="btn-not-helpful">👎 Not helpful</button>
                    </div>
                </div>
            `;
        }).join("");

        const nextActionHtml = rec.next_action ? `
            <div class="next-action">
                <span class="action-text">${rec.next_action}</span>
            </div>
        ` : "";

        const card = document.createElement("div");
        card.className = `video-recommendations ${cfg.cls}`;
        card.innerHTML = `
            <div class="video-rec-header">
                <span class="rec-icon">${cfg.icon}</span>
                <span class="rec-title">${rec.recommendation_message || cfg.label}</span>
            </div>
            ${intentInfo}
            <div class="videos-grid video-cards-scroll">
                ${videosHtml}
            </div>
            ${nextActionHtml}
        `;

        const chatContainer = document.getElementById("chat-messages");
        const msgItem = (afterBubble && afterBubble.closest) ? afterBubble.closest(".chat-message-item") : (chatContainer ? chatContainer.lastElementChild : null);
        const bubbleCard = msgItem ? msgItem.querySelector(".msg-bubble-card") : null;

        if (bubbleCard) {
            const old = bubbleCard.querySelector(".video-recommendations");
            if (old) old.remove();
            bubbleCard.appendChild(card);
        } else if (msgItem && msgItem.parentElement) {
            if (msgItem.nextElementSibling && msgItem.nextElementSibling.classList.contains("video-recommendations")) {
                msgItem.nextElementSibling.remove();
            }
            msgItem.parentElement.insertBefore(card, msgItem.nextSibling);
        }

        setTimeout(() => {
            scrollToBottom();
            card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }, 100);
    }

    window.playVideoInApp = function(btn, cardId) {
        if (!btn) return;
        const url = btn.getAttribute("data-url") || btn.dataset.url;
        const title = btn.getAttribute("data-title") || btn.dataset.title || "Bennett Verified Lecture";
        const channel = btn.getAttribute("data-channel") || btn.dataset.channel || "Faculty Lecture Series";
        
        window.openYtPlayerModal(url, title, channel);
    };

    window.openYtPlayerModal = function(url, title, channel) {
        const modal = document.getElementById("yt-player-modal");
        const iframe = document.getElementById("yt-player-iframe");
        const titleEl = document.getElementById("yt-player-title");
        const channelEl = document.getElementById("yt-player-channel");
        const extLink = document.getElementById("yt-player-external-link");

        if (!modal) return;

        if (titleEl) titleEl.textContent = title || "Bennett Verified Lecture";
        if (channelEl) channelEl.textContent = channel || "Faculty Lecture Series";
        if (extLink) extLink.href = url || "#";

        const videoId = resolveYouTubeVideoId(url, channel);

        if (iframe) {
            // Using youtube-nocookie embed with autoplay enabled for true in-app embedded playback
            iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&enablejsapi=1&rel=0`;
        }

        modal.classList.remove("hidden");
        modal.style.display = "flex";
    };

    window.closeYtPlayerModal = function() {
        const modal = document.getElementById("yt-player-modal");
        const iframe = document.getElementById("yt-player-iframe");
        if (iframe) iframe.src = "";
        if (modal) {
            modal.classList.add("hidden");
            modal.style.display = "none";
        }
    };

    // Global Click Delegation for In-App Player & Poster Clicks
    document.addEventListener("click", function(e) {
        const btn = e.target.closest(".btn-watch-inapp, .btn-launch-inapp, .video-poster-box");
        if (btn) {
            e.preventDefault();
            e.stopPropagation();
            window.playVideoInApp(btn);
        }

        const ytModal = document.getElementById("yt-player-modal");
        if (ytModal && e.target === ytModal) {
            window.closeYtPlayerModal();
        }
    });

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            window.closeYtPlayerModal();
        }
    });

    // Global rateVideo handler
    window.rateVideo = async function(playlistId, rating, wasHelpful, containerId) {
        try {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<span style="font-size:12px;color:#10b981;font-weight:600;">Saving rating...</span>`;
            }
            const userId = (currentUser && currentUser.id) ? currentUser.id : 1;
            const res = await fetch(`/api/videos/${playlistId}/rate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: userId,
                    rating: rating,
                    was_helpful: wasHelpful,
                    watched_percentage: 30
                })
            });
            const data = await res.json();
            if (container) {
                container.innerHTML = `<span style="font-size:12px;color:#10b981;font-weight:600;">✅ Thanks for rating! (Score: ${data.playlist_score || '4.9'})</span>`;
            }
        } catch (e) {
            console.error("Rate error:", e);
        }
    };

    function uuidv4() {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }


    // ----------------------------------------------------
    // PDF Uploads Manager & Modal Handler
    // ----------------------------------------------------
    const uploadModal = document.getElementById("upload-modal");
    const btnCloseUploadModal = document.getElementById("btn-close-upload-modal");
    const formUploadDocument = document.getElementById("form-upload-document");
    const modalUploadStatus = document.getElementById("modal-upload-status");
    const uploadFileInput = document.getElementById("upload-file-input");
    const fileChosenLabel = document.getElementById("file-chosen-label");

    const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024; // 20MB limit
    let currentUploadTarget = "browse"; // "library" (private) or "browse" (public)

    function updateScopeToggleVisuals(selectedScope) {
        const radioLib = document.getElementById("radio-scope-library");
        const radioBrowse = document.getElementById("radio-scope-browse");
        const labelLib = document.getElementById("label-scope-library");
        const labelBrowse = document.getElementById("label-scope-browse");
        const modal = document.getElementById("upload-modal");
        const modalTitle = modal ? modal.querySelector(".modal-header h3") : null;

        if (selectedScope === "library") {
            currentUploadTarget = "library";
            if (radioLib) radioLib.checked = true;
            if (labelLib) {
                labelLib.style.border = "1.5px solid #8b5cf6";
                labelLib.style.background = "rgba(139, 92, 246, 0.25)";
                labelLib.style.color = "#ffffff";
            }
            if (labelBrowse) {
                labelBrowse.style.border = "1.5px solid rgba(255, 255, 255, 0.1)";
                labelBrowse.style.background = "rgba(255, 255, 255, 0.04)";
                labelBrowse.style.color = "#94a3b8";
            }
            if (modalTitle) modalTitle.textContent = "Upload Document to My Workspace (Private)";
        } else {
            currentUploadTarget = "browse";
            if (radioBrowse) radioBrowse.checked = true;
            if (labelBrowse) {
                labelBrowse.style.border = "1.5px solid #8b5cf6";
                labelBrowse.style.background = "rgba(139, 92, 246, 0.25)";
                labelBrowse.style.color = "#ffffff";
            }
            if (labelLib) {
                labelLib.style.border = "1.5px solid rgba(255, 255, 255, 0.1)";
                labelLib.style.background = "rgba(255, 255, 255, 0.04)";
                labelLib.style.color = "#94a3b8";
            }
            if (modalTitle) modalTitle.textContent = "Upload Document to Course Repository (Public)";
        }
    }

    function openUploadModal(targetScope = "browse") {
        currentUploadTarget = targetScope;
        const modal = document.getElementById("upload-modal") || uploadModal;
        updateScopeToggleVisuals(targetScope);
        if (modal) {
            modal.classList.remove("hidden");
            modal.style.display = "flex";
        }
    }
    window.openUploadModal = openUploadModal;
    window.openUploadModalDirect = openUploadModal;

    const radioLibElem = document.getElementById("radio-scope-library");
    const radioBrowseElem = document.getElementById("radio-scope-browse");
    if (radioLibElem) radioLibElem.addEventListener("change", () => updateScopeToggleVisuals("library"));
    if (radioBrowseElem) radioBrowseElem.addEventListener("change", () => updateScopeToggleVisuals("browse"));

    function closeUploadModal() {
        const modal = document.getElementById("upload-modal") || uploadModal;
        if (modal) {
            modal.classList.add("hidden");
            modal.style.display = "none";
            if (formUploadDocument) {
                formUploadDocument.reset();
                delete formUploadDocument.dataset.confirmedOverwrite;
            }
            if (fileChosenLabel) {
                fileChosenLabel.textContent = "Click or drag PDF or Word (.docx, .doc) file here";
                fileChosenLabel.style.color = "#a78bfa";
                fileChosenLabel.style.fontWeight = "500";
            }
            if (modalUploadStatus) {
                modalUploadStatus.classList.add("hidden");
                modalUploadStatus.textContent = "";
            }
            const btnSubmitUpload = document.getElementById("btn-submit-upload");
            if (btnSubmitUpload) {
                btnSubmitUpload.disabled = false;
                btnSubmitUpload.style.opacity = "1";
                btnSubmitUpload.style.cursor = "pointer";
                btnSubmitUpload.innerHTML = "Upload & Index Document";
            }
        }
    }
    window.closeUploadModal = closeUploadModal;

    function showModalError(msg) {
        if (modalUploadStatus) {
            modalUploadStatus.classList.remove("hidden");
            modalUploadStatus.textContent = `❌ ${msg}`;
            modalUploadStatus.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
            modalUploadStatus.style.color = "#f87171";
            modalUploadStatus.style.padding = "10px 14px";
            modalUploadStatus.style.borderRadius = "8px";
            modalUploadStatus.style.fontSize = "13px";
        }
    }

    if (uploadFileInput && fileChosenLabel) {
        uploadFileInput.addEventListener("change", () => {
            if (uploadFileInput.files && uploadFileInput.files.length > 0) {
                const file = uploadFileInput.files[0];
                const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);

                if (file.size > MAX_FILE_SIZE_BYTES) {
                    fileChosenLabel.textContent = `Exceeds 20MB limit (${fileSizeMb} MB)`;
                    fileChosenLabel.style.color = "#f87171";
                    fileChosenLabel.style.fontWeight = "600";
                    showModalError(`File size exceeds the 20MB maximum limit (${fileSizeMb} MB). Please choose a smaller file.`);
                    uploadFileInput.value = ""; // Reset oversized selection
                    return;
                }

                fileChosenLabel.textContent = `${file.name} (${fileSizeMb} MB)`;
                fileChosenLabel.style.color = "#10b981";
                fileChosenLabel.style.fontWeight = "600";
                if (modalUploadStatus) {
                    modalUploadStatus.classList.add("hidden");
                    modalUploadStatus.textContent = "";
                }
            } else {
                fileChosenLabel.textContent = "Click or drag PDF or Word (.docx, .doc) file here";
                fileChosenLabel.style.color = "#a78bfa";
                fileChosenLabel.style.fontWeight = "500";
            }
        });
    }

    if (uploadZone) {
        uploadZone.addEventListener("click", () => openUploadModal("browse"));
    }

    if (btnInputPlus) {
        btnInputPlus.addEventListener("click", () => openUploadModal("browse"));
    }

    if (btnLibraryUploadTrigger) {
        btnLibraryUploadTrigger.addEventListener("click", () => openUploadModal("library"));
    }

    if (btnBrowseUploadTrigger) {
        btnBrowseUploadTrigger.addEventListener("click", () => openUploadModal("browse"));
    }

    if (btnCloseUploadModal) {
        btnCloseUploadModal.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeUploadModal();
        });
    }

    if (uploadModal) {
        uploadModal.addEventListener("click", (e) => {
            if (e.target === uploadModal) closeUploadModal();
        });
    }

    const fileDropzoneBox = document.getElementById("file-dropzone-box");
    if (fileDropzoneBox && uploadFileInput) {
        fileDropzoneBox.addEventListener("click", (e) => {
            if (e.target !== uploadFileInput) {
                uploadFileInput.click();
            }
        });
    }

    const fileTypeSelectInput = document.getElementById("upload-filetype-select");
    const examTypeSelectInput = document.getElementById("upload-examtype-select");
    if (fileTypeSelectInput && examTypeSelectInput) {
        fileTypeSelectInput.addEventListener("change", () => {
            if (fileTypeSelectInput.value === "PYQ" && examTypeSelectInput.value === "Other") {
                examTypeSelectInput.value = "Mid-Sem";
            }
        });
    }

    if (formUploadDocument) {
        formUploadDocument.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileFileInput = document.getElementById("upload-file-input");
            const subjectSelect = document.getElementById("upload-subject-select");
            const semesterSelect = document.getElementById("upload-semester-select");
            const fileTypeSelect = document.getElementById("upload-filetype-select");
            const examTypeSelect = document.getElementById("upload-examtype-select");
            const btnSubmitUpload = document.getElementById("btn-submit-upload");

            if (!fileFileInput || !fileFileInput.files || fileFileInput.files.length === 0) {
                showModalError("Please select a PDF or Word document (.pdf, .docx, .doc).");
                return;
            }

            const file = fileFileInput.files[0];
            const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);

            if (file.size > MAX_FILE_SIZE_BYTES) {
                showModalError(`File size exceeds the 20MB maximum limit (${fileSizeMb} MB). Please select a smaller document.`);
                uploadFileInput.value = "";
                return;
            }

            const subject = subjectSelect ? subjectSelect.value : "";
            const semester = semesterSelect ? semesterSelect.value : "";
            const fileType = fileTypeSelect ? fileTypeSelect.value : "";
            const examType = examTypeSelect ? examTypeSelect.value : "Other";

            if (!subject) {
                showModalError("Please select an engineering subject.");
                return;
            }

            if (!semester) {
                showModalError("Please select a semester.");
                return;
            }

            if (!fileType) {
                showModalError("Please select a file type (Notes, PYQ, Assignment).");
                return;
            }

            // Check for duplicate document strictly within target scope (Workspace vs Course Repo)
            const isConfirmedOverwrite = formUploadDocument.dataset.confirmedOverwrite === "true";
            const radioSelected = document.querySelector('input[name="upload_target_scope"]:checked');
            const targetIsPrivate = radioSelected ? (radioSelected.value === "library") : (currentUploadTarget === "library");
            const activeUser = currentUser || window.currentUser;
            const currentEmail = activeUser && activeUser.email ? activeUser.email.toLowerCase().trim() : "";

            if (!isConfirmedOverwrite) {
                const existingFile = allCachedFiles.find(f => {
                    if (!f || typeof f !== 'object') return false;
                    const fn = (f.filename || "").toLowerCase().trim();
                    const sub = (f.subject || "").trim();
                    const sem = (f.semester || "").trim();
                    const fIsPrivate = Boolean(f.is_private === 1 || f.is_private === true);
                    const fEmail = (f.user_email || "").toLowerCase().trim();

                    if (fn !== file.name.toLowerCase().trim() || sub !== subject || sem !== semester) {
                        return false;
                    }

                    // Strict Separation:
                    // 1. If uploading to Personal Workspace: ONLY check current user's own private workspace!
                    // Course Repo files NEVER block or warn.
                    if (targetIsPrivate) {
                        return fIsPrivate && fEmail === currentEmail;
                    }

                    // 2. If uploading to Course Repository: ONLY check public Course Repo files!
                    // Private workspace files NEVER block or warn.
                    return !fIsPrivate;
                });

                if (existingFile) {
                    const scopeDesc = targetIsPrivate ? "your Personal Workspace" : `Course Repository (${subject} - ${semester})`;
                    if (modalUploadStatus) {
                        modalUploadStatus.classList.remove("hidden");
                        modalUploadStatus.style.backgroundColor = "transparent";
                        modalUploadStatus.style.padding = "0";
                        modalUploadStatus.innerHTML = `
                            <div class="duplicate-warning-banner">
                                <div class="warning-title">Similar Document Already Exists</div>
                                <p class="warning-msg">A document named <strong>"${file.name}"</strong> already exists under <strong>${scopeDesc}</strong>. Do you still want to upload and overwrite it?</p>
                                <div class="warning-actions">
                                    <button type="button" id="btn-confirm-overwrite" class="btn-warning-confirm">Yes, Overwrite & Upload</button>
                                    <button type="button" id="btn-cancel-overwrite" class="btn-warning-cancel">Cancel</button>
                                </div>
                            </div>
                        `;
                    }

                    const btnConfirm = document.getElementById("btn-confirm-overwrite");
                    const btnCancel = document.getElementById("btn-cancel-overwrite");

                    if (btnConfirm) {
                        btnConfirm.addEventListener("click", () => {
                            formUploadDocument.dataset.confirmedOverwrite = "true";
                            formUploadDocument.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
                        });
                    }

                    if (btnCancel) {
                        btnCancel.addEventListener("click", () => {
                            delete formUploadDocument.dataset.confirmedOverwrite;
                            if (modalUploadStatus) {
                                modalUploadStatus.classList.add("hidden");
                                modalUploadStatus.innerHTML = "";
                            }
                        });
                    }

                    return;
                }
            }

            delete formUploadDocument.dataset.confirmedOverwrite;

            const isPrivateVal = targetIsPrivate ? "1" : "0";

            const formData = new FormData();
            formData.append("file", file);
            formData.append("subject", subject);
            formData.append("semester", semester);
            formData.append("file_type", fileType);
            formData.append("exam_type", examType);
            formData.append("is_private", isPrivateVal);
            formData.append("confirm_overwrite", "true");

            const activeEmail = activeUser ? (activeUser.email || "anonymous@college.edu") : "anonymous@college.edu";
            const activeName = activeUser ? (activeUser.name || "Anonymous Student") : "Anonymous Student";

            formData.append("user_email", activeEmail);
            formData.append("user_name", activeName);

            // Disable submit button and set animated loading state
            if (btnSubmitUpload) {
                btnSubmitUpload.disabled = true;
                btnSubmitUpload.style.opacity = "0.75";
                btnSubmitUpload.style.cursor = "not-allowed";
                btnSubmitUpload.innerHTML = `<span class="upload-btn-spinner"></span> Uploading & Indexing...`;
            }

            if (modalUploadStatus) {
                modalUploadStatus.classList.remove("hidden");
                modalUploadStatus.innerHTML = `
                    <div class="upload-loading-box">
                        <div class="upload-spinner"></div>
                        <span>Uploading and indexing document (${fileSizeMb} MB)... Please wait.</span>
                    </div>
                `;
                modalUploadStatus.style.backgroundColor = "rgba(139, 92, 246, 0.15)";
                modalUploadStatus.style.color = "#c084fc";
                modalUploadStatus.style.padding = "10px 14px";
                modalUploadStatus.style.borderRadius = "8px";
                modalUploadStatus.style.fontSize = "13px";
            }

            try {
                const res = await fetch("/upload", {
                    method: "POST",
                    body: formData
                });

                if (res.ok) {
                    if (modalUploadStatus) {
                        modalUploadStatus.innerHTML = `Uploaded & Indexed successfully!`;
                        modalUploadStatus.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
                        modalUploadStatus.style.color = "#34d399";
                    }
                    setTimeout(() => {
                        closeUploadModal();
                        fetchIndexedFiles();
                        fetchUserStats();
                    }, 1200);
                } else if (res.status === 409) {
                    const data = await res.json();
                    if (modalUploadStatus) {
                        modalUploadStatus.classList.remove("hidden");
                        modalUploadStatus.style.backgroundColor = "transparent";
                        modalUploadStatus.style.padding = "0";
                        modalUploadStatus.innerHTML = `
                            <div class="duplicate-warning-banner">
                                <div class="warning-title">Similar Document Already Exists</div>
                                <p class="warning-msg">${data.detail || "A similar document already exists. Do you still want to upload?"}</p>
                                <div class="warning-actions">
                                    <button type="button" id="btn-confirm-overwrite" class="btn-warning-confirm">Yes, Overwrite & Upload</button>
                                    <button type="button" id="btn-cancel-overwrite" class="btn-warning-cancel">Cancel</button>
                                </div>
                            </div>
                        `;
                    }
                    if (btnSubmitUpload) {
                        btnSubmitUpload.disabled = false;
                        btnSubmitUpload.style.opacity = "1";
                        btnSubmitUpload.style.cursor = "pointer";
                        btnSubmitUpload.innerHTML = "Upload & Index Document";
                    }

                    const btnConfirm = document.getElementById("btn-confirm-overwrite");
                    const btnCancel = document.getElementById("btn-cancel-overwrite");

                    if (btnConfirm) {
                        btnConfirm.addEventListener("click", () => {
                            formUploadDocument.dataset.confirmedOverwrite = "true";
                            formUploadDocument.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
                        });
                    }

                    if (btnCancel) {
                        btnCancel.addEventListener("click", () => {
                            delete formUploadDocument.dataset.confirmedOverwrite;
                            if (modalUploadStatus) {
                                modalUploadStatus.classList.add("hidden");
                                modalUploadStatus.innerHTML = "";
                            }
                        });
                    }
                } else {
                    const data = await res.json();
                    showModalError(data.detail || "Upload failed.");
                    if (btnSubmitUpload) {
                        btnSubmitUpload.disabled = false;
                        btnSubmitUpload.style.opacity = "1";
                        btnSubmitUpload.style.cursor = "pointer";
                        btnSubmitUpload.innerHTML = "Upload & Index Document";
                    }
                }
            } catch (e) {
                showModalError("Network connection error or server timeout.");
                if (btnSubmitUpload) {
                    btnSubmitUpload.disabled = false;
                    btnSubmitUpload.style.opacity = "1";
                    btnSubmitUpload.style.cursor = "pointer";
                    btnSubmitUpload.innerHTML = "Upload & Index Document";
                }
            }
        });
    }

    const btnMainUploadTrigger = document.getElementById("btn-main-upload-trigger");
    if (btnMainUploadTrigger) {
        btnMainUploadTrigger.addEventListener("click", openUploadModal);
    }

    let allCachedFiles = [];

    async function fetchIndexedFiles() {
        try {
            const activeUser = currentUser || window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "null");
            const emailParam = activeUser && activeUser.email ? `?user_email=${encodeURIComponent(activeUser.email)}` : "";
            const res = await fetch(`/files${emailParam}`);
            if (!res.ok) return;
            const data = await res.json();
            
            allCachedFiles = data.files || [];
            renderFilesUI();
            updateBrowseSubjectOptions();
            renderBrowseTable();
        } catch (e) {
            console.error("Error loading files:", e);
        }
    }

    function renderFilesUI() {
        const mainFilesGrid = document.getElementById("main-files-grid");
        const libraryGrid = document.getElementById("library-documents-grid");
        
        if (indexedFilesList) indexedFilesList.innerHTML = "";
        if (mainFilesGrid) mainFilesGrid.innerHTML = "";
        if (libraryGrid) libraryGrid.innerHTML = "";

        const searchQuery = (document.getElementById("library-filter-search")?.value || "").toLowerCase().trim();
        const filterSubject = document.getElementById("library-filter-subject")?.value || "";
        const filterSemester = document.getElementById("library-filter-semester")?.value || "";
        const filterFileType = document.getElementById("library-filter-filetype")?.value || "";

        // --------------------------------------------------------
        // 1. Sidebar Pinned Folders & Main Workspace Grid
        // --------------------------------------------------------
        if (indexedFilesList) {
            indexedFilesList.innerHTML = "";
            const pinnedFilenames = getSidebarPinnedFilenames();
            const pinnedFileObjects = allCachedFiles.filter(f => {
                const fname = typeof f === 'string' ? f : f.filename;
                return pinnedFilenames.includes(fname);
            });

            if (pinnedFileObjects.length === 0) {
                indexedFilesList.innerHTML = `<li class="file-item-empty">No folders pinned</li>`;
            } else {
                const accents = ["#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#3b82f6"];
                pinnedFileObjects.forEach((fileObj, idx) => {
                    const filename = typeof fileObj === 'string' ? fileObj : fileObj.filename;
                    const uploaderName = typeof fileObj === 'object' && fileObj.user_name ? fileObj.user_name : "Anonymous";
                    const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "General";
                    const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "Sem 1";
                    const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "Notes";
                    const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === true);
                    const accent = accents[idx % accents.length];

                    const li = document.createElement("li");
                    li.className = "file-item sidebar-pinned-card";
                    li.style.borderLeft = `3.5px solid ${accent}`;
                    li.style.flexDirection = "column";
                    li.style.alignItems = "stretch";
                    li.style.gap = "6px";
                    li.style.padding = "10px 12px";
                    li.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 6px; overflow: hidden; flex: 1;">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0; color: #a78bfa;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                                <span title="${filename}" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; font-size: 12px; color: #f3f4f6; cursor: pointer;">${filename}</span>
                            </div>
                            <button type="button" class="btn-unpin-sidebar" data-filename="${filename}" title="Remove from Pinned Folders">
                                X
                            </button>
                        </div>
                        <div class="meta-badges-row sidebar-badges-row">
                            <span class="filetype-badge" title="File Type: ${fileType}">${fileType}</span>
                            <span class="semester-badge" title="${semester}">${semester}</span>
                            <span class="subject-badge" title="Subject: ${subject}">${subject}</span>
                        </div>
                        <div class="sidebar-uploader-info">Uploaded by <strong>${uploaderName}</strong></div>
                    `;

                    const titleSpan = li.querySelector("span");
                    if (titleSpan) {
                        titleSpan.addEventListener("click", () => {
                            const activeUser = currentUser || window.currentUser;
                            const emailParam = activeUser && activeUser.email ? `&user_email=${encodeURIComponent(activeUser.email)}` : "";
                            window.open(`/view/${encodeURIComponent(filename)}?is_private=${isPrivate ? 1 : 0}${emailParam}`, "_blank");
                        });
                    }

                    const btnUnpin = li.querySelector(".btn-unpin-sidebar");
                    if (btnUnpin) {
                        btnUnpin.addEventListener("click", (e) => {
                            e.stopPropagation();
                            toggleSidebarPinFile(filename);
                        });
                    }

                    indexedFilesList.appendChild(li);
                });
            }
        }

        if (mainFilesGrid) {
            mainFilesGrid.innerHTML = "";
            if (allCachedFiles.length === 0) {
                mainFilesGrid.innerHTML = `<div class="empty-docs-placeholder">No documents uploaded yet</div>`;
            }

            allCachedFiles.forEach(fileObj => {
                const filename = typeof fileObj === 'string' ? fileObj : fileObj.filename;
                const uploaderName = typeof fileObj === 'object' && fileObj.user_name ? fileObj.user_name : "Anonymous";
                const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "General";
                const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "Sem 1";
                const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "Notes";
                const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === true);
                const isOwner = isFileUploadedByCurrentUser(fileObj);

                const card = document.createElement("div");
                card.className = "main-doc-card";
                card.innerHTML = `
                    <div class="doc-card-top">
                        <div class="doc-card-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        ${isOwner ? `
                            <button class="btn-delete-file btn-delete-main" data-filename="${filename}" title="Delete File">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                            </button>
                        ` : ''}
                    </div>
                    <div class="doc-card-title" title="${filename}">${filename}</div>
                    <div class="meta-badges-row" style="margin-top: 6px;">
                        <span class="filetype-badge">${fileType}</span>
                        <span class="semester-badge">${semester}</span>
                        <span class="subject-badge">${subject}</span>
                    </div>
                    <div class="doc-card-uploader">Uploaded by <strong>${uploaderName}</strong></div>
                `;

                const btnDeleteMain = card.querySelector(".btn-delete-main");
                if (btnDeleteMain) {
                    btnDeleteMain.addEventListener("click", (e) => {
                        e.stopPropagation();
                        deleteUploadedFile(filename, isPrivate ? 1 : 0);
                    });
                }

                mainFilesGrid.appendChild(card);
            });
        }

        // --------------------------------------------------------
        // 2. Render "My Library" (PERSONAL TO CURRENT LOGGED-IN USER ONLY)
        // --------------------------------------------------------
        if (libraryGrid) {
            const activeUser = currentUser || window.currentUser;
            if (!activeUser) {
                libraryGrid.innerHTML = `
                    <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
                        Please sign in to access your personal workspace and manage your uploaded documents.
                    </div>
                `;
                return;
            }

            const myUploadedFiles = allCachedFiles.filter(fileObj => {
                const isOwner = isFileUploadedByCurrentUser(fileObj);
                const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === true);
                return isOwner && isPrivate;
            });

            if (myUploadedFiles.length === 0) {
                libraryGrid.innerHTML = `
                    <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
                        You haven't uploaded any documents yet. Use the "+ Upload Document" button above to add study materials to your workspace!
                    </div>
                `;
                return;
            }

            const filteredMyFiles = myUploadedFiles.filter(fileObj => {
                const filename = (typeof fileObj === 'string' ? fileObj : fileObj.filename || "").toLowerCase();
                const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "";
                const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "";
                const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "";

                if (searchQuery && !filename.includes(searchQuery)) return false;
                if (filterSubject && subject !== filterSubject) return false;
                if (filterSemester && semester !== filterSemester) return false;
                if (filterFileType && fileType !== filterFileType) return false;
                return true;
            });

            if (filteredMyFiles.length === 0) {
                libraryGrid.innerHTML = `<div class="empty-docs-placeholder" style="grid-column: 1 / -1;">No matching documents found in your library.</div>`;
                return;
            }

            filteredMyFiles.forEach(fileObj => {
                const filename = typeof fileObj === 'string' ? fileObj : fileObj.filename;
                const uploaderName = typeof fileObj === 'object' && fileObj.user_name ? fileObj.user_name : (currentUser.name || "You");
                const subject = typeof fileObj === 'object' && fileObj.subject ? fileObj.subject : "General Engineering";
                const semester = typeof fileObj === 'object' && fileObj.semester ? fileObj.semester : "Semester 1";
                const fileType = typeof fileObj === 'object' && fileObj.file_type ? fileObj.file_type : "Notes";
                const sizeKb = typeof fileObj === 'object' && fileObj.size_bytes ? Math.round(fileObj.size_bytes / 1024) + " KB" : "Document";
                const uploadedAt = typeof fileObj === 'object' && fileObj.uploaded_at ? fileObj.uploaded_at.split("T")[0] : "Recently";
                const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === true);
                const isPinnedInSidebar = isFilePinnedInSidebar(filename);

                const card = document.createElement("div");
                card.className = "browse-doc-card library-doc-card";
                card.innerHTML = `
                    <div class="doc-card-top">
                        <div class="browse-pdf-icon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        <div class="doc-card-tags">
                            <span class="filetype-badge">${fileType}</span>
                            <span class="privacy-badge ${isPrivate ? 'privacy-private' : 'privacy-shared'}">${isPrivate ? 'Private' : 'Shared'}</span>
                        </div>
                    </div>

                    <a href="/view/${encodeURIComponent(filename)}?is_private=1&user_email=${encodeURIComponent(activeUser.email)}" target="_blank" class="browse-file-title" title="${filename}">
                        ${filename}
                    </a>

                    <div class="doc-card-curriculum">
                        <div class="doc-card-subject">${subject}</div>
                        <div class="doc-card-semester">${semester}</div>
                    </div>

                    <div class="doc-card-meta">
                        <div class="meta-row">
                            <span class="meta-label">Uploaded By</span>
                            <span class="meta-value">${uploaderName} (You)</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-label">Date & Size</span>
                            <span class="meta-value">${uploadedAt} (${sizeKb})</span>
                        </div>
                    </div>

                    <div class="doc-card-actions">
                        <button type="button" class="btn-download-file btn-download-doc" data-filename="${filename}" onclick="downloadDocumentFile('${escapeHtmlLocal(filename).replace(/'/g, "\\'")}', 1)" title="Download File">
                            <span>Download</span>
                        </button>
                        <a href="/view/${encodeURIComponent(filename)}?is_private=1&user_email=${encodeURIComponent(activeUser.email)}" target="_blank" class="btn-open-browse-pdf" title="View Document">
                            <span>View</span>
                        </a>
                        <button type="button" class="btn-chat-with-doc btn-browse-chat" data-filename="${filename}" title="Chat with Document">
                            <span>Chat</span>
                        </button>
                        <button type="button" class="btn-browse-pin btn-pin-browse ${isPinnedInSidebar ? 'active-pinned' : ''}" data-filename="${filename}" title="${isPinnedInSidebar ? 'Unpin from Sidebar Pinned Folders' : 'Pin to Sidebar'}">
                            <span>${isPinnedInSidebar ? 'Pinned' : 'Pin'}</span>
                        </button>
                        <button type="button" class="btn-delete-my-library btn-delete-file-doc" data-filename="${filename}" onclick="deleteUploadedDocument('${escapeHtmlLocal(filename).replace(/'/g, "\\'")}', 1)" title="Delete File from Storage & DB">
                            <span>Delete</span>
                        </button>
                    </div>
                `;

                const btnChat = card.querySelector(".btn-chat-with-doc");
                if (btnChat) {
                    btnChat.addEventListener("click", () => {
                        startNewChatWithDoc(filename);
                    });
                }

                const btnPinLib = card.querySelector(".btn-pin-browse");
                if (btnPinLib) {
                    btnPinLib.addEventListener("click", (e) => {
                        e.stopPropagation();
                        toggleSidebarPinFile(filename);
                    });
                }

                libraryGrid.appendChild(card);
            });
        }
    }

    // ----------------------------------------------------
    // Report Document Modal Handler
    // ----------------------------------------------------
    function openReportModal(filename) {
        const reportModal = document.getElementById("report-modal");
        const reportFilenameInput = document.getElementById("report-filename-input");
        const reportDocTitleDisplay = document.getElementById("report-doc-title-display");
        const reportReasonSelect = document.getElementById("report-reason-select");
        const reportNotesInput = document.getElementById("report-notes-input");
        const modalReportStatus = document.getElementById("modal-report-status");

        if (reportFilenameInput) reportFilenameInput.value = filename;
        if (reportDocTitleDisplay) reportDocTitleDisplay.textContent = filename;
        if (reportReasonSelect) reportReasonSelect.value = "";
        if (reportNotesInput) reportNotesInput.value = "";
        if (modalReportStatus) {
            modalReportStatus.classList.add("hidden");
            modalReportStatus.textContent = "";
        }

        if (reportModal) {
            reportModal.classList.remove("hidden");
            reportModal.style.display = "flex";
        }
    }
    window.openReportModal = openReportModal;

    function closeReportModal() {
        const reportModal = document.getElementById("report-modal");
        if (reportModal) {
            reportModal.classList.add("hidden");
            reportModal.style.display = "none";
        }
    }
    window.closeReportModal = closeReportModal;

    function initReportModal() {
        const reportModal = document.getElementById("report-modal");
        const btnCloseReportModal = document.getElementById("btn-close-report-modal");
        const formReportDocument = document.getElementById("form-report-document");
        const modalReportStatus = document.getElementById("modal-report-status");

        if (btnCloseReportModal) {
            btnCloseReportModal.addEventListener("click", closeReportModal);
        }

        if (reportModal) {
            reportModal.addEventListener("click", (e) => {
                if (e.target === reportModal) closeReportModal();
            });
        }

        if (formReportDocument) {
            formReportDocument.addEventListener("submit", async (e) => {
                e.preventDefault();
                const filename = document.getElementById("report-filename-input")?.value || "";
                const reasonSelect = document.getElementById("report-reason-select");
                const notesInput = document.getElementById("report-notes-input");
                const btnSubmitReport = document.getElementById("btn-submit-report");

                const reason = reasonSelect ? reasonSelect.value : "";
                const notes = notesInput ? notesInput.value.trim() : "";

                if (!reason) {
                    if (modalReportStatus) {
                        modalReportStatus.classList.remove("hidden");
                        modalReportStatus.textContent = "Please select a reason for reporting.";
                        modalReportStatus.style.backgroundColor = "#fef2f2";
                        modalReportStatus.style.color = "#dc2626";
                        modalReportStatus.style.padding = "10px 14px";
                        modalReportStatus.style.borderRadius = "8px";
                    }
                    return;
                }

                if (btnSubmitReport) {
                    btnSubmitReport.disabled = true;
                    btnSubmitReport.style.opacity = "0.75";
                    btnSubmitReport.textContent = "Submitting Report...";
                }

                try {
                    const res = await fetch("/report", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            filename: filename,
                            reason: reason,
                            notes: notes,
                            reporter_email: currentUser ? (currentUser.email || "anonymous@college.edu") : "anonymous@college.edu",
                            reporter_name: currentUser ? (currentUser.name || "Anonymous Student") : "Anonymous Student"
                        })
                    });

                    const data = await res.json();

                    if (res.ok) {
                        if (modalReportStatus) {
                            modalReportStatus.classList.remove("hidden");
                            modalReportStatus.textContent = data.message || "Report submitted successfully.";
                            modalReportStatus.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
                            modalReportStatus.style.color = "#34d399";
                            modalReportStatus.style.padding = "10px 14px";
                            modalReportStatus.style.borderRadius = "8px";
                        }
                        setTimeout(() => {
                            closeReportModal();
                            if (btnSubmitReport) {
                                btnSubmitReport.disabled = false;
                                btnSubmitReport.style.opacity = "1";
                                btnSubmitReport.textContent = "Submit Report";
                            }
                        }, 1600);
                    } else {
                        if (modalReportStatus) {
                            modalReportStatus.classList.remove("hidden");
                            modalReportStatus.textContent = data.detail || "Failed to submit report.";
                            modalReportStatus.style.backgroundColor = "#fef2f2";
                            modalReportStatus.style.color = "#dc2626";
                            modalReportStatus.style.padding = "10px 14px";
                            modalReportStatus.style.borderRadius = "8px";
                        }
                        if (btnSubmitReport) {
                            btnSubmitReport.disabled = false;
                            btnSubmitReport.style.opacity = "1";
                            btnSubmitReport.textContent = "Submit Report";
                        }
                    }
                } catch(err) {
                    if (modalReportStatus) {
                        modalReportStatus.classList.remove("hidden");
                        modalReportStatus.textContent = "Network error submitting report.";
                        modalReportStatus.style.backgroundColor = "#fef2f2";
                        modalReportStatus.style.color = "#dc2626";
                        modalReportStatus.style.padding = "10px 14px";
                        modalReportStatus.style.borderRadius = "8px";
                    }
                    if (btnSubmitReport) {
                        btnSubmitReport.disabled = false;
                        btnSubmitReport.style.opacity = "1";
                        btnSubmitReport.textContent = "Submit Report";
                    }
                }
            });
        }
    }

    // Attach Filter Event Listeners for Library Page
    ["library-filter-search", "library-filter-subject", "library-filter-semester", "library-filter-filetype"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("input", renderFilesUI);
            el.addEventListener("change", renderFilesUI);
        }
    });

    // ═════════════════════════════════════════════════════════════════════════
    // UNIVERSAL DOCUMENT DOWNLOAD & DELETE (BLOB-BASED & CROSS-ORIGIN SAFE)
    // ═════════════════════════════════════════════════════════════════════════

    window.triggerBlobDownload = function(blob, filename) {
        try {
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                if (document.body.contains(a)) {
                    document.body.removeChild(a);
                }
                window.URL.revokeObjectURL(blobUrl);
            }, 2000);
        } catch (err) {
            console.error("[TRIGGER BLOB DOWNLOAD ERROR]", err);
            window.open(`/download/${encodeURIComponent(filename)}?disposition=attachment`, '_blank');
        }
    };

    window.downloadDocumentFile = async function(filename, isPrivate = null) {
        if (!filename) return;
        try {
            const activeUser = currentUser || window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
            const emailParam = activeUser && activeUser.email ? `&user_email=${encodeURIComponent(activeUser.email)}` : "";
            const privParam = isPrivate !== null ? `&is_private=${isPrivate}` : "";
            const downloadUrl = `/download/${encodeURIComponent(filename)}?disposition=attachment${emailParam}${privParam}`;
            const res = await fetch(downloadUrl);
            if (!res.ok) {
                // Fallback to /files/
                const altRes = await fetch(`/files/${encodeURIComponent(filename)}?${emailParam.replace('&', '')}${privParam}`);
                if (altRes.ok) {
                    const blob = await altRes.blob();
                    window.triggerBlobDownload(blob, filename);
                    return;
                }
                // Direct new tab open fallback
                window.open(downloadUrl, '_blank');
                return;
            }
            const blob = await res.blob();
            window.triggerBlobDownload(blob, filename);
        } catch (err) {
            console.warn("[DOWNLOAD BLOB FALLBACK]", err);
            window.open(`/download/${encodeURIComponent(filename)}?disposition=attachment`, '_blank');
        }
    };

    window.deleteUploadedDocument = async function(filename, isPrivate = null) {
        if (!filename) return;
        const confirmed = confirm(`Are you sure you want to delete "${filename}"?\n\nThis will permanently remove the file from storage and the database.`);
        if (!confirmed) return;

        try {
            const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
            const userEmail = user.email || "";
            const userName = user.name || "";
            const queryParams = new URLSearchParams({ user_email: userEmail, user_name: userName });
            if (isPrivate !== null) {
                queryParams.append("is_private", isPrivate);
            }
            
            const res = await fetch(`/files/${encodeURIComponent(filename)}?${queryParams.toString()}`, {
                method: "DELETE"
            });
            
            if (res.ok) {
                // Unpin from sidebar if pinned
                try {
                    if (typeof unpinSidebarFileDirect === "function") {
                        unpinSidebarFileDirect(filename);
                    }
                } catch(pe) {}

                // Refresh all file list views
                if (typeof fetchIndexedFiles === "function") {
                    fetchIndexedFiles();
                }
                if (typeof renderFilesUI === "function") {
                    renderFilesUI();
                }
                if (typeof renderBrowseTable === "function") {
                    renderBrowseTable();
                }
            } else {
                const data = await res.json();
                alert(`Could not delete file: ${data.detail || "Server error"}`);
            }
        } catch(err) {
            console.error("Error deleting file:", err);
            alert("Network error deleting file.");
        }
    };

    window.deleteUploadedFile = window.deleteUploadedDocument;

    window.setSidebarState = function(collapsed) {
        const appSidebar = document.querySelector(".app-sidebar");
        const btnExpandSidebar = document.getElementById("btn-expand-sidebar");
        const sidebarBackdrop = document.getElementById("sidebar-backdrop");
        if (!appSidebar) return;

        if (collapsed) {
            appSidebar.classList.add("sidebar-collapsed");
            if (btnExpandSidebar) {
                btnExpandSidebar.classList.remove("hidden");
                btnExpandSidebar.style.setProperty("display", "flex", "important");
            }
            if (sidebarBackdrop) {
                sidebarBackdrop.classList.add("hidden");
                sidebarBackdrop.style.setProperty("display", "none", "important");
            }
            try { localStorage.setItem("sidebar-collapsed", "true"); } catch(e){}
        } else {
            appSidebar.classList.remove("sidebar-collapsed");
            if (btnExpandSidebar) {
                btnExpandSidebar.classList.add("hidden");
                btnExpandSidebar.style.setProperty("display", "none", "important");
            }
            if (window.innerWidth <= 768 && sidebarBackdrop) {
                sidebarBackdrop.classList.remove("hidden");
                sidebarBackdrop.style.setProperty("display", "block", "important");
            } else if (sidebarBackdrop) {
                sidebarBackdrop.classList.add("hidden");
                sidebarBackdrop.style.setProperty("display", "none", "important");
            }
            try { localStorage.setItem("sidebar-collapsed", "false"); } catch(e){}
        }
    };

    window.toggleSidebar = function(e) {
        if (e && typeof e.stopPropagation === "function") {
            e.stopPropagation();
        }
        const appSidebar = document.querySelector(".app-sidebar");
        if (!appSidebar) return;
        const isCurrentlyCollapsed = appSidebar.classList.contains("sidebar-collapsed");
        window.setSidebarState(!isCurrentlyCollapsed);
    };

    function initSidebarToggle() {
        const btnCollapseSidebar = document.querySelector(".sidebar-collapse-btn") || document.getElementById("btn-collapse-sidebar");
        const btnExpandSidebar = document.getElementById("btn-expand-sidebar");
        const sidebarBackdrop = document.getElementById("sidebar-backdrop");

        if (btnCollapseSidebar) {
            btnCollapseSidebar.onclick = (e) => window.toggleSidebar(e);
        }
        if (btnExpandSidebar) {
            btnExpandSidebar.onclick = (e) => window.toggleSidebar(e);
        }
        if (sidebarBackdrop) {
            sidebarBackdrop.onclick = () => window.setSidebarState(true);
        }

        // Default state: Mobile screens default to collapsed; Desktop defaults to OPEN (unless explicitly collapsed)
        const isMobileScreen = window.innerWidth <= 768;
        let savedState = null;
        try { savedState = localStorage.getItem("sidebar-collapsed"); } catch(e){}
        const isCollapsed = isMobileScreen ? (savedState !== "false") : (savedState === "true");
        window.setSidebarState(isCollapsed);

        // Auto-close sidebar on mobile when clicking any sidebar navigation link or button
        document.querySelectorAll(".app-sidebar nav a, .app-sidebar nav button, .app-sidebar .sidebar-link, .app-sidebar .btn-sidebar-new-chat, .app-sidebar .thread-item").forEach(el => {
            el.addEventListener("click", () => {
                if (window.innerWidth <= 768) {
                    setSidebarState(true);
                }
            });
        });

        if (btnHeaderBack) {
            btnHeaderBack.addEventListener("click", () => {
                showLandingState();
            });
        }

        // Header Profile Dropdown Event Manager
        const btnHeaderProfileDropdown = document.getElementById("btn-header-profile-dropdown");
        const headerProfileDropdown = document.getElementById("header-profile-dropdown");
        if (btnHeaderProfileDropdown && headerProfileDropdown) {
            btnHeaderProfileDropdown.addEventListener("click", (e) => {
                e.stopPropagation();
                if (settingsDropdown) settingsDropdown.classList.add("hidden");
                headerProfileDropdown.classList.toggle("hidden");
            });

            document.addEventListener("click", (e) => {
                if (!headerProfileDropdown.contains(e.target) && !btnHeaderProfileDropdown.contains(e.target)) {
                    headerProfileDropdown.classList.add("hidden");
                }
            });

            const linkHome = document.getElementById("dropdown-link-home");
            const linkLibrary = document.getElementById("dropdown-link-library");
            const linkShared = document.getElementById("dropdown-link-shared");
            const linkProfile = document.getElementById("dropdown-link-profile");
            const linkLogout = document.getElementById("dropdown-link-logout");

            if (linkHome) linkHome.addEventListener("click", () => { headerProfileDropdown.classList.add("hidden"); showLandingState(); });
            if (linkLibrary) linkLibrary.addEventListener("click", () => { headerProfileDropdown.classList.add("hidden"); showPinnedLibraryState(); });
            if (linkShared) linkShared.addEventListener("click", () => { headerProfileDropdown.classList.add("hidden"); showBrowseState(); });
            if (linkProfile) linkProfile.addEventListener("click", () => { headerProfileDropdown.classList.add("hidden"); if (window.openProfileModal) window.openProfileModal(); });
            if (linkLogout) linkLogout.addEventListener("click", () => { headerProfileDropdown.classList.add("hidden"); if (typeof signOut === "function") signOut(); });
        }
    }

    // Browse Page Listeners
    if (navBrowseDocuments) {
        navBrowseDocuments.addEventListener("click", showBrowseState);
    }
    if (btnBrowseUploadTrigger) {
        btnBrowseUploadTrigger.addEventListener("click", () => openUploadModal("browse"));
    }

    const browseSearchInput = document.getElementById("browse-search-input");
    const browseSemSelect = document.getElementById("browse-semester-select");
    const browseSubSelect = document.getElementById("browse-subject-select");
    const browseTypeSelect = document.getElementById("browse-filetype-select");

    if (browseSearchInput) {
        browseSearchInput.addEventListener("input", renderBrowseTable);
        browseSearchInput.addEventListener("change", renderBrowseTable);
    }
    if (browseSemSelect) {
        browseSemSelect.addEventListener("change", () => {
            updateBrowseSubjectOptions();
            renderBrowseTable();
        });
    }
    if (browseSubSelect) {
        browseSubSelect.addEventListener("change", renderBrowseTable);
    }
    if (browseTypeSelect) {
        browseTypeSelect.addEventListener("change", renderBrowseTable);
    }

    // ----------------------------------------------------
    // First-Time User Onboarding & Feature Preview Tour
    // ----------------------------------------------------
    let currentOnboardingStep = 1;
    const onboardingSteps = [
        {
            tag: "AI DOUBT SOLVER & LECTURES",
            title: "Instant AI Doubt Solver & Video Match",
            desc: "Ask complex questions across all 24+ engineering subjects. Get step-by-step mathematical reasoning, code solutions, and verified Bennett faculty lecture playlists.",
            icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="9" y1="10" x2="15" y2="10"/><line x1="12" y1="7" x2="12" y2="13"/></svg>`,
            items: [
                "⚡ Step-by-step calculus derivations, code explanations, and formula breakdowns",
                "🎥 Recommended Bennett faculty video lectures & playlists mapped to your doubts",
                "💬 LaTeX math rendering and multi-turn contextual syllabus memory"
            ],
            visual: `💡 Try asking: "Explain Bayes Theorem with derivation & formula"`
        },
        {
            tag: "CAMPUS REPOSITORY",
            title: "Verified Engineering Notes & PYQs",
            desc: "Search, explore, and download notes, past year question papers, and lab assignments organized cleanly by Semester and Engineering Subject.",
            icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="3"/></svg>`,
            items: [
                "🔍 Instant filtering by Semester (1-8), Subject, and Category (Notes, PYQs, Labs)",
                "📤 Upload your study materials to earn +15 campus contribution points",
                "🔒 Private My Workspace storage or public sharing with university peers"
            ],
            visual: `📁 Filter by: Semester 3 → Probability & Statistics → PYQs`
        },
        {
            tag: "EXAM ANALYTICS",
            title: "Predictive Exam Paper Generator",
            desc: "AI analyzes past year examination recurrence patterns, question types, and topic weightage to predict high-yield questions for upcoming exams.",
            icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
            items: [
                "🎯 Structured Mid-Sem and End-Sem question papers with Section A, B, and C",
                "📈 High-probability recurrence tags (e.g. 90% High Probability)",
                "📥 In-browser exam previews and instant study question sets"
            ],
            visual: `🎯 Predicted: Baye's Rule (90% Prob), Normal Distribution (85% Prob)`
        },
        {
            tag: "ACADEMIC EDGE",
            title: "Concept Gap Profiler & Adaptive Practice",
            desc: "Identifies foundational concept weaknesses blocking your comprehension and delivers personalized adaptive practice sessions in real-time.",
            icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/><path d="M8 12h.01"/><path d="M16 12h.01"/></svg>`,
            items: [
                "🔬 Automatic diagnosis of prerequisite gaps from your study interactions",
                "🎯 Interactive adaptive quizzes with dynamic difficulty scaling (Level 1 → 3)",
                "📊 Concept dependency graphs and mastery recovery roadmaps"
            ],
            visual: `🧠 Foundational Gap Resolved: Conditional Probability → Ready for Level 2`
        },
        {
            tag: "GAMIFIED MASTERY",
            title: "Daily Streaks & Live Campus Leaderboard",
            desc: "Stay consistent and motivated! Earn contribution points, build daily streaks, and climb the university leaderboard.",
            icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/></svg>`,
            items: [
                "🔥 Maintain your daily Study Streak to unlock special campus badges",
                "🥇 Earn points: Doubts (+2), Tests (+5), Notes Upload (+15), Predictions (+5)",
                "👑 Real-time live tracking with student ranks across Bennett University"
            ],
            visual: `🔥 7-Day Streak Active! Top 5 in Computer Science & Engineering`
        }
    ];

    function renderOnboardingStep(stepNum) {
        if (stepNum < 1) stepNum = 1;
        if (stepNum > onboardingSteps.length) stepNum = onboardingSteps.length;
        currentOnboardingStep = stepNum;

        const content = document.getElementById("onboarding-step-content");
        const indicator = document.getElementById("onboarding-step-indicator");
        const btnNext = document.getElementById("btn-next-onboarding");
        const btnPrev = document.getElementById("btn-prev-onboarding");
        const dots = document.querySelectorAll(".onboarding-dot");

        const data = onboardingSteps[currentOnboardingStep - 1];

        if (content && data) {
            const checkIcon = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
            const itemsHtml = (data.items || []).map(it => `
                <div class="onboarding-feature-item">
                    ${checkIcon}
                    <span>${it}</span>
                </div>
            `).join("");

            content.innerHTML = `
                <div class="onboarding-icon-box">
                    ${data.icon}
                </div>
                <div class="onboarding-feature-badge">${data.tag}</div>
                <h2 class="onboarding-step-title">${data.title}</h2>
                <p class="onboarding-step-desc">${data.desc}</p>
                <div class="onboarding-feature-list">
                    ${itemsHtml}
                </div>
                <div class="onboarding-visual-mock">
                    ${data.visual}
                </div>
            `;
        }

        if (indicator) indicator.textContent = `Step ${currentOnboardingStep} of ${onboardingSteps.length}`;

        if (btnPrev) {
            btnPrev.style.display = currentOnboardingStep > 1 ? "inline-flex" : "none";
        }

        dots.forEach((dot, idx) => {
            if (idx + 1 === currentOnboardingStep) {
                dot.classList.add("active");
            } else {
                dot.classList.remove("active");
            }
        });

        if (btnNext) {
            if (currentOnboardingStep === onboardingSteps.length) {
                btnNext.innerHTML = `<span>🚀 Explore Workspace</span>`;
                btnNext.className = "btn-onboarding-primary get-started-btn";
            } else {
                btnNext.innerHTML = `<span>Next →</span>`;
                btnNext.className = "btn-onboarding-primary";
            }
        }
    }

    window.closeOnboardingModal = function() {
        completeUserOnboarding();
    };

    window.openProductTour = function() {
        const modal = document.getElementById("onboarding-modal");
        if (modal) {
            renderOnboardingStep(1);
            if (typeof window.openModalById === "function") {
                window.openModalById("onboarding-modal");
            } else {
                modal.classList.remove("hidden");
                modal.style.removeProperty("display");
                modal.style.display = "flex";
            }
        }
    };

    async function completeUserOnboarding() {
        const modal = document.getElementById("onboarding-modal");
        if (modal) {
            if (typeof window.closeModalById === "function") {
                window.closeModalById("onboarding-modal");
            } else {
                modal.classList.add("hidden");
                modal.style.setProperty("display", "none", "important");
            }
        }

        var userEmail = (currentUser && currentUser.email) ? currentUser.email.toLowerCase() : "guest";
        try {
            localStorage.setItem("bu_prepz_tour_seen_" + userEmail, "true");
        } catch(e) {}

        if (currentUser) {
            currentUser.has_seen_onboarding = true;
            try {
                localStorage.setItem("docpilot-user", JSON.stringify(currentUser));
            } catch(e) {}
            try {
                await fetch("/api/user/complete-onboarding", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: currentUser.email })
                });
            } catch(e) {}
        }
    }

    function checkAndShowOnboarding(user) {
        if (!user) return false;
        if (!user.has_seen_onboarding) {
            window.openProductTour();
            return true;
        }
        return false;
    }

    function initOnboardingListeners() {
        const btnNext = document.getElementById("btn-next-onboarding");
        const btnPrev = document.getElementById("btn-prev-onboarding");
        const btnSkip = document.getElementById("btn-skip-onboarding");
        const dots = document.querySelectorAll(".onboarding-dot");

        if (btnNext) {
            btnNext.addEventListener("click", () => {
                if (currentOnboardingStep < onboardingSteps.length) {
                    renderOnboardingStep(currentOnboardingStep + 1);
                } else {
                    completeUserOnboarding();
                }
            });
        }

        if (btnPrev) {
            btnPrev.addEventListener("click", () => {
                if (currentOnboardingStep > 1) {
                    renderOnboardingStep(currentOnboardingStep - 1);
                }
            });
        }

        if (btnSkip) {
            btnSkip.addEventListener("click", completeUserOnboarding);
        }

        dots.forEach(dot => {
            dot.addEventListener("click", () => {
                const step = parseInt(dot.dataset.step, 10);
                if (step >= 1 && step <= onboardingSteps.length) {
                    renderOnboardingStep(step);
                }
            });
        });
    }

    function initFullscreenToggle() {
        const btnFullscreen = document.getElementById("btn-fullscreen-toggle");
        if (!btnFullscreen) return;

        const expandSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>`;
        const minimizeSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 14h6v6m10-10h-6V4m0 16h6v-6M10 4H4v6"/></svg>`;

        function updateFullscreenUI() {
            const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement);
            if (isFull) {
                btnFullscreen.innerHTML = `${minimizeSvg}<span>Exit Fullscreen</span>`;
                btnFullscreen.title = "Exit Fullscreen Mode (Esc)";
            } else {
                btnFullscreen.innerHTML = `${expandSvg}<span>Fullscreen</span>`;
                btnFullscreen.title = "Toggle Fullscreen Mode";
            }
        }

        btnFullscreen.addEventListener("click", () => {
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                if (document.documentElement.requestFullscreen) {
                    document.documentElement.requestFullscreen();
                } else if (document.documentElement.webkitRequestFullscreen) {
                    document.documentElement.webkitRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
            }
        });

        document.addEventListener("fullscreenchange", updateFullscreenUI);
        document.addEventListener("webkitfullscreenchange", updateFullscreenUI);
    }

    // Expose core app controllers to window
    window.fetchThreads = fetchThreads;
    window.fetchIndexedFiles = fetchIndexedFiles;
    window.selectThread = selectThread;
    window.loadThreadHistory = loadThreadHistory;
    window.showChatState = showChatState;
    window.showLandingState = showLandingState;

    // Start flows
    initSearchFilter();
    initSuggestions();
    initInputAutoresize();
    initVoiceRecognition();
    initSettingsMenu();
    initSidebarToggle();
    initAuth();
    initReportModal();
    initOnboardingListeners();
    initFullscreenToggle();

    // Auto-sync uploaded files across all users in real-time every 4 seconds
    fetchIndexedFiles();
    setInterval(fetchIndexedFiles, 4000);

    // If active user is already logged in, immediately load threads and stats
    if (window.currentUser && window.currentUser.email) {
        fetchThreads();
        if (typeof checkAndEnableAdminUI === "function") checkAndEnableAdminUI();
        if (typeof startHeartbeatDaemon === "function") startHeartbeatDaemon();
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeDocPilotApp);
} else {
    initializeDocPilotApp();
}

// ----------------------------------------------------
// Private & Shared Document Library Frontend Controllers
// ----------------------------------------------------

window.openCreateDocumentModal = function() {
    const modal = document.getElementById("modal-document-editor");
    const modalTitle = document.getElementById("doc-editor-modal-title");
    const docIdInput = document.getElementById("doc-editor-id");
    const titleInput = document.getElementById("doc-editor-title-input");
    const contentInput = document.getElementById("doc-editor-content-input");
    const isSharedCheck = document.getElementById("doc-editor-is-shared");
    const errorMsg = document.getElementById("doc-editor-error-msg");

    if (errorMsg) { errorMsg.textContent = ""; errorMsg.classList.add("hidden"); }
    if (modalTitle) modalTitle.textContent = "Create New Document";
    if (docIdInput) docIdInput.value = "";
    if (titleInput) titleInput.value = "";
    if (contentInput) contentInput.value = "";
    if (isSharedCheck) isSharedCheck.checked = false;

    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
    }
};

window.openEditDocumentModal = async function(docId) {
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    try {
        const res = await fetch(`/api/documents/${docId}`, {
            headers: { "X-User-Email": email }
        });
        const data = await res.json();
        if (res.ok && data.document) {
            const doc = data.document;
            const modal = document.getElementById("modal-document-editor");
            const modalTitle = document.getElementById("doc-editor-modal-title");
            const docIdInput = document.getElementById("doc-editor-id");
            const titleInput = document.getElementById("doc-editor-title-input");
            const contentInput = document.getElementById("doc-editor-content-input");
            const isSharedCheck = document.getElementById("doc-editor-is-shared");
            const errorMsg = document.getElementById("doc-editor-error-msg");

            if (errorMsg) { errorMsg.textContent = ""; errorMsg.classList.add("hidden"); }
            if (modalTitle) modalTitle.textContent = "Edit Document";
            if (docIdInput) docIdInput.value = doc.id;
            if (titleInput) titleInput.value = doc.title || "";
            if (contentInput) contentInput.value = doc.content || "";
            if (isSharedCheck) isSharedCheck.checked = !!doc.is_shared;

            if (modal) {
                modal.classList.remove("hidden");
                modal.style.display = "flex";
            }
        } else {
            alert(data.detail || "Error loading document.");
        }
    } catch(err) {
        console.error("Edit doc error:", err);
    }
};

window.closeDocumentEditorModal = function() {
    const modal = document.getElementById("modal-document-editor");
    if (modal) {
        modal.classList.add("hidden");
        modal.style.display = "none";
    }
};

window.handleDocumentFormSubmit = async function(e) {
    if (e) e.preventDefault();
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    
    const docId = document.getElementById("doc-editor-id").value;
    const title = document.getElementById("doc-editor-title-input").value.trim();
    const content = document.getElementById("doc-editor-content-input").value;
    const isShared = document.getElementById("doc-editor-is-shared").checked;
    const errorMsg = document.getElementById("doc-editor-error-msg");

    if (!title) {
        if (errorMsg) { errorMsg.textContent = "Please enter a document title."; errorMsg.classList.remove("hidden"); }
        return;
    }

    try {
        const method = docId ? "PUT" : "POST";
        const url = docId ? `/api/documents/${docId}` : "/api/documents";
        const res = await fetch(url, {
            method: method,
            headers: {
                "Content-Type": "application/json",
                "X-User-Email": email
            },
            body: JSON.stringify({ title, content, is_shared: isShared })
        });
        const data = await res.json();
        if (res.ok) {
            window.closeDocumentEditorModal();
            if (typeof window.fetchMyDocuments === "function") window.fetchMyDocuments();
            if (typeof window.fetchSharedDocuments === "function") window.fetchSharedDocuments();
        } else {
            if (errorMsg) {
                errorMsg.textContent = data.detail || "Failed to save document.";
                errorMsg.classList.remove("hidden");
            }
        }
    } catch(err) {
        console.error("Save document error:", err);
        if (errorMsg) {
            errorMsg.textContent = "Error saving document. Please try again.";
            errorMsg.classList.remove("hidden");
        }
    }
};

window.toggleDocumentShare = async function(docId, isShared) {
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    try {
        const res = await fetch(`/api/documents/${docId}/share`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-User-Email": email
            },
            body: JSON.stringify({ is_shared: isShared })
        });
        const data = await res.json();
        if (res.ok) {
            if (typeof window.fetchMyDocuments === "function") window.fetchMyDocuments();
            if (typeof window.fetchSharedDocuments === "function") window.fetchSharedDocuments();
        } else {
            alert(data.detail || "Error toggling document share status.");
        }
    } catch(err) {
        console.error("Toggle share error:", err);
    }
};

window.deleteDocument = async function(docId) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    try {
        const res = await fetch(`/api/documents/${docId}`, {
            method: "DELETE",
            headers: { "X-User-Email": email }
        });
        const data = await res.json();
        if (res.ok) {
            if (typeof window.fetchMyDocuments === "function") window.fetchMyDocuments();
            if (typeof window.fetchSharedDocuments === "function") window.fetchSharedDocuments();
        } else {
            alert(data.detail || "Error deleting document.");
        }
    } catch(err) {
        console.error("Delete doc error:", err);
    }
};

window.copyDocumentToMyLibrary = async function(docId) {
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    try {
        const getRes = await fetch(`/api/documents/${docId}`, {
            headers: { "X-User-Email": email }
        });
        const getData = await getRes.json();
        if (!getRes.ok || !getData.document) {
            alert("Error loading original document.");
            return;
        }
        const orig = getData.document;
        const createRes = await fetch("/api/documents", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-User-Email": email
            },
            body: JSON.stringify({
                title: `${orig.title} (Copy)`,
                content: orig.content,
                is_shared: false
            })
        });
        if (createRes.ok) {
            alert("Document copied to your Workspace!");
            if (typeof window.fetchMyDocuments === "function") window.fetchMyDocuments();
        } else {
            const errData = await createRes.json();
            alert(errData.detail || "Failed to copy document.");
        }
    } catch(err) {
        console.error("Copy document error:", err);
    }
};

window.fetchMyDocuments = async function() {
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "student@college.edu";
    try {
        const res = await fetch("/api/my-library", {
            headers: { "X-User-Email": email }
        });
        const data = await res.json();
        if (res.ok && data.documents) {
            renderMyDocumentsList(data.documents);
        }
    } catch(err) {
        console.error("fetchMyDocuments error:", err);
    }
};

window.fetchSharedDocuments = async function() {
    try {
        const res = await fetch("/api/shared-library");
        const data = await res.json();
        if (res.ok && data.documents) {
            renderSharedDocumentsList(data.documents);
        }
    } catch(err) {
        console.error("fetchSharedDocuments error:", err);
    }
};

function renderMyDocumentsList(docs) {
    const container = document.getElementById("my-documents-container") || document.getElementById("library-grid");
    if (!container) return;
    
    let addBtn = document.getElementById("btn-add-my-doc");
    if (!addBtn) {
        const headerArea = container.parentElement;
        const btnHtml = `<button id="btn-add-my-doc" onclick="openCreateDocumentModal()" style="margin-bottom: 16px; padding: 10px 18px; border-radius: 10px; background: linear-gradient(135deg, #6366f1, #4f46e5); color: #fff; border: none; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">+ New Document</button>`;
        container.insertAdjacentHTML("beforebegin", btnHtml);
    }

    if (!docs || docs.length === 0) {
        container.innerHTML = `
            <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1);">
                No personal documents created yet. Click <strong>"+ New Document"</strong> above to write study notes or summaries!
            </div>
        `;
        return;
    }

    function escapeHtmlLocal(text) {
        if (!text) return '';
        return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    container.innerHTML = docs.map(doc => {
        const statusBadge = doc.is_shared 
            ? `<span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">Shared</span>`
            : `<span style="background: rgba(161, 161, 170, 0.15); color: #a1a1aa; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">Private</span>`;
        
        const shareToggleBtn = doc.is_shared
            ? `<button onclick="toggleDocumentShare(${doc.id}, false)" style="padding: 4px 8px; background: #27272a; border: 1px solid #3f3f46; color: #a1a1aa; border-radius: 6px; font-size: 11px; cursor: pointer;">Make Private</button>`
            : `<button onclick="toggleDocumentShare(${doc.id}, true)" style="padding: 4px 8px; background: rgba(99, 102, 241, 0.2); border: 1px solid #6366f1; color: #818cf8; border-radius: 6px; font-size: 11px; cursor: pointer;">Share Publicly</button>`;

        const createdDate = doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recently';

        return `
            <div class="doc-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <h4 style="margin: 0; font-size: 16px; color: #ffffff; font-weight: 600;">${escapeHtmlLocal(doc.title)}</h4>
                    ${statusBadge}
                </div>
                <p style="margin: 0; font-size: 13px; color: #a1a1aa; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtmlLocal(doc.content || 'No content.')}</p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; pt-2; border-top: 1px solid rgba(255,255,255,0.05);">
                    <span style="font-size: 11px; color: #71717a;">${createdDate}</span>
                    <div style="display: flex; gap: 6px;">
                        ${shareToggleBtn}
                        <button onclick="openEditDocumentModal(${doc.id})" style="padding: 4px 8px; background: #27272a; border: 1px solid #3f3f46; color: #ffffff; border-radius: 6px; font-size: 11px; cursor: pointer;">Edit</button>
                        <button onclick="deleteDocument(${doc.id})" style="padding: 4px 8px; background: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; color: #f87171; border-radius: 6px; font-size: 11px; cursor: pointer;">Delete</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderSharedDocumentsList(docs) {
    const container = document.getElementById("shared-documents-container") || document.getElementById("browse-documents-container");
    if (!container) return;

    if (!docs || docs.length === 0) {
        container.innerHTML = `
            <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px dashed rgba(255,255,255,0.1);">
                No public shared documents available yet. Mark your personal notes as "Shared" to publish them here!
            </div>
        `;
        return;
    }

    function escapeHtmlLocal(text) {
        if (!text) return '';
        return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    container.innerHTML = docs.map(doc => {
        const ownerName = doc.owner_name || (doc.user_email ? doc.user_email.split('@')[0] : 'Student');
        const createdDate = doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recently';

        return `
            <div class="doc-card" style="background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <h4 style="margin: 0; font-size: 16px; color: #ffffff; font-weight: 600;">${escapeHtmlLocal(doc.title)}</h4>
                    <span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">${escapeHtmlLocal(ownerName)}</span>
                </div>
                <p style="margin: 0; font-size: 13px; color: #a1a1aa; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtmlLocal(doc.content || 'No preview available.')}</p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                    <span style="font-size: 11px; color: #71717a;">${createdDate}</span>
                    <button onclick="copyDocumentToMyLibrary(${doc.id})" style="padding: 6px 12px; background: linear-gradient(135deg, #6366f1, #4f46e5); color: #ffffff; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer;">Copy to Workspace</button>
                </div>
            </div>
        `;
    }).join('');
}

window.toggleFilePrivacy = async function(filename, isPrivate) {
    const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const email = user.email || "anonymous@college.edu";
    try {
        const res = await fetch(`/files/${encodeURIComponent(filename)}/toggle-privacy`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_private: isPrivate, user_email: email })
        });
        const data = await res.json();
        if (res.ok) {
            if (typeof fetchIndexedFiles === "function") fetchIndexedFiles();
        } else {
            alert(data.detail || "Error toggling file privacy.");
        }
    } catch(err) {
        console.error("toggleFilePrivacy error:", err);
    }
};

// ═════════════════════════════════════════════════════════════════════════════
// CONCEPT WEAKNESS PROFILER & ADAPTIVE PRACTICE (ACADEMIC EDGE)
// ═════════════════════════════════════════════════════════════════════════════

function escapeHtmlLocal(text) {
    if (!text && text !== 0) return '';
    return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

let currentPracticeSession = null;
let currentQuestionIndex = 0;
let selectedPracticeAnswer = null;
let questionStartTime = Date.now();

// ── Open / Close Profiler Modal ──
// ── Open / Close Profiler Modal ──
window.showWeaknessProfile = async function() {
    const modal = document.getElementById("weakness-profile-modal");
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.style.display = "flex";

    const spinner = document.getElementById("weakness-loading-spinner");
    const content = document.getElementById("weakness-modal-content");
    if (spinner) {
        spinner.style.display = "block";
        spinner.innerHTML = `
            <div class="loading-dots"><span></span><span></span><span></span></div>
            <p style="font-size: 13px; color: #a1a1aa; margin-top: 10px;">Analyzing conceptual graphs across your chats & documents...</p>
        `;
    }
    if (content) content.style.display = "none";

    // Bind Enter key on concept analyzer input
    const analyzerInput = document.getElementById("concept-analyzer-input");
    if (analyzerInput && !analyzerInput.dataset.boundEnter) {
        analyzerInput.dataset.boundEnter = "true";
        analyzerInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                window.runAiConceptAnalysis();
            }
        });
    }

    await window.refreshWeaknessProfileData();
};

window.refreshWeaknessProfileData = async function() {
    const spinner = document.getElementById("weakness-loading-spinner");
    const content = document.getElementById("weakness-modal-content");

    try {
        const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = user.email || "";
        
        let profile = null;
        try {
            const res = await fetch(`/api/weaknesses/profile?user_email=${encodeURIComponent(email)}`);
            if (res.ok) {
                profile = await res.json();
            }
        } catch (pe) {
            console.warn("[WEAKNESS PROFILE API WARN]", pe);
        }

        let gData = { dependencies: [] };
        try {
            const gRes = await fetch("/api/weaknesses/graph");
            if (gRes.ok) {
                gData = await gRes.json();
            }
        } catch (ge) {
            console.warn("[WEAKNESS GRAPH API WARN]", ge);
        }

        if (!profile) {
            profile = {
                total_weaknesses: 0,
                avg_mastery_score: 0.0,
                critical_weaknesses: [],
                foundational_gaps: [],
                secondary_weaknesses: []
            };
        }

        if (spinner) spinner.style.display = "none";
        if (content) content.style.display = "block";

        renderWeaknessProfile(profile);
        renderConceptGraphChips(gData.dependencies || []);
    } catch (err) {
        console.error("Error loading weakness profile:", err);
        if (spinner) spinner.innerHTML = `<span style="color:#ef4444;">Failed to load concept profile. Please try refreshing.</span>`;
    }
};

window.runAiConceptAnalysis = async function() {
    const input = document.getElementById("concept-analyzer-input");
    const resultBox = document.getElementById("concept-analyzer-result");
    const btn = document.getElementById("btn-run-concept-analyzer");
    if (!input || !resultBox) return;

    const query = input.value.trim();
    if (!query) {
        alert("Please enter a concept, question, or confusion to analyze.");
        input.focus();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="upload-btn-spinner"></span> Analyzing...`;
    }

    resultBox.style.display = "block";
    resultBox.innerHTML = `
        <div style="padding: 20px; text-align: center; background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 10px;">
            <div class="upload-spinner" style="margin: 0 auto 10px auto;"></div>
            <div style="font-size: 13.5px; color: #c084fc; font-weight: 600;">Diagnosing underlying misconceptions & mapping curriculum dependencies for "${escapeHtmlLocal(query)}"...</div>
        </div>
    `;

    try {
        const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = user.email || "";

        const res = await fetch("/api/concept-profile/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: query,
                user_email: email
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Analysis failed");
        }

        const data = await res.json();
        const a = data.analysis;

        const prereqBadges = (a.prerequisites || []).map(p => `<span style="display:inline-block; margin: 3px 4px 3px 0; padding: 4px 10px; border-radius: 6px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #93c5fd; font-size: 12px; font-weight: 500;">📌 ${escapeHtmlLocal(p)}</span>`).join('');
        const downstreamBadges = (a.downstream_impact || []).map(d => `<span style="display:inline-block; margin: 3px 4px 3px 0; padding: 4px 10px; border-radius: 6px; background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.3); color: #fda4af; font-size: 12px; font-weight: 500;">⚠️ ${escapeHtmlLocal(d)}</span>`).join('');

        const remediationHtml = (a.remediation_plan || []).map(r => `
            <div style="margin-top: 6px; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 6px; font-size: 12.5px; line-height: 1.45;">
                <strong style="color: #a78bfa;">${escapeHtmlLocal(r.step)}:</strong>
                <span style="color: #e2e8f0; margin-left: 4px;">${escapeHtmlLocal(r.action)}</span>
            </div>
        `).join('');

        const questionsHtml = (a.practice_questions || []).map((q, qIdx) => `
            <div class="diagnostic-q-card" style="margin-top: 10px; padding: 12px 14px; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;">
                <div style="font-size: 13px; font-weight: 600; color: #f1f5f9; margin-bottom: 8px;">
                    <span style="color: #8b5cf6;">Q${qIdx + 1}.</span> ${escapeHtmlLocal(q.question)}
                </div>
                <div class="diag-options-list" style="display: grid; gap: 6px;">
                    ${(q.options || []).map(opt => `
                        <div class="diag-opt-item" onclick="handleDiagnosticOptClick(this, '${escapeHtmlLocal(opt).replace(/'/g, "\\'")}', '${escapeHtmlLocal(q.correct_answer).replace(/'/g, "\\'")}')" style="padding: 8px 12px; font-size: 12.5px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; cursor: pointer; color: #cbd5e1; transition: all 0.2s;">
                            ${escapeHtmlLocal(opt)}
                        </div>
                    `).join('')}
                </div>
                <div class="diag-explanation-box" style="display: none; margin-top: 8px; padding: 8px 12px; border-radius: 6px; font-size: 12px; line-height: 1.4;">
                    <div class="diag-expl-text" style="color: #e2e8f0;"></div>
                </div>
            </div>
        `).join('');

        resultBox.innerHTML = `
            <div style="padding: 18px; background: rgba(15, 23, 42, 0.95); border: 1.5px solid rgba(139, 92, 246, 0.4); border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);">
                <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <h3 style="margin: 0; font-size: 16px; font-weight: 700; color: #ffffff;">${escapeHtmlLocal(a.concept_name)}</h3>
                            <span style="padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; background: rgba(139, 92, 246, 0.2); color: #c084fc; border: 1px solid rgba(139, 92, 246, 0.4);">${escapeHtmlLocal(a.subject)}</span>
                            ${a.is_critical ? '<span style="padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4);">🚨 HIGH EXAM RISK</span>' : ''}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span style="font-size: 12px; color: #94a3b8;">Exam Risk Score: <strong style="color: #f43f5e; font-size: 14px;">${a.exam_risk_score}/100</strong></span>
                    </div>
                </div>

                <!-- Diagnostic Summary -->
                <div style="padding: 12px 14px; background: rgba(99, 102, 241, 0.08); border-left: 3px solid #8b5cf6; border-radius: 6px; margin-bottom: 14px;">
                    <div style="font-size: 12px; font-weight: 700; color: #a78bfa; margin-bottom: 4px; text-transform: uppercase;">🧠 Cognitive Misconception Diagnosis:</div>
                    <div style="font-size: 13px; color: #e2e8f0; line-height: 1.5;">${escapeHtmlLocal(a.diagnostic_summary)}</div>
                </div>

                <!-- Prerequisite & Downstream Graph -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 14px;">
                    <div style="padding: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;">
                        <div style="font-size: 11.5px; font-weight: 700; color: #60a5fa; margin-bottom: 6px; text-transform: uppercase;">📚 Prerequisite Foundations (Must Know First):</div>
                        <div>${prereqBadges || '<span style="font-size: 12px; color: #94a3b8;">Standard Engineering Foundations</span>'}</div>
                    </div>
                    <div style="padding: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;">
                        <div style="font-size: 11.5px; font-weight: 700; color: #f87171; margin-bottom: 6px; text-transform: uppercase;">⚡ Downstream Blocked Topics (High Impact):</div>
                        <div>${downstreamBadges || '<span style="font-size: 12px; color: #94a3b8;">Direct Topic Scenarios</span>'}</div>
                    </div>
                </div>

                <!-- 3-Step Remediation Plan -->
                <div style="margin-bottom: 14px;">
                    <div style="font-size: 12px; font-weight: 700; color: #34d399; margin-bottom: 6px; text-transform: uppercase;">🎯 3-Step Mastery Roadmap:</div>
                    <div>${remediationHtml}</div>
                </div>

                <!-- Diagnostic Practice Check -->
                ${questionsHtml ? `
                    <div style="margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 12px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                            <div style="font-size: 12px; font-weight: 700; color: #f59e0b; text-transform: uppercase;">📝 Quick Concept Check (Click an Option to Test):</div>
                        </div>
                        <div>${questionsHtml}</div>
                    </div>
                ` : ''}

                <div style="display: flex; gap: 10px; margin-top: 16px; justify-content: flex-end;">
                    <button type="button" onclick="startAdaptivePractice('${escapeHtmlLocal(a.concept_name).replace(/'/g, "\\'")}', 'easy')" class="btn-auth-primary" style="padding: 9px 18px; font-size: 13px; font-weight: 600;">▶ Launch Full Adaptive Practice Session →</button>
                </div>
            </div>
        `;

        window.refreshWeaknessProfileData();

    } catch (err) {
        console.error("[CONCEPT ANALYZER ERROR]", err);
        resultBox.innerHTML = `
            <div style="padding: 14px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #f87171; font-size: 13px;">
                ❌ Could not analyze concept: ${escapeHtmlLocal(err.message || "Server connection error")}. Please try again.
            </div>
        `;
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `⚡ Analyze Concept`;
        }
    }
};

window.handleDiagnosticOptClick = function(optEl, selectedOpt, correctOpt) {
    const parent = optEl.closest(".diagnostic-q-card");
    if (!parent) return;

    const allOpts = parent.querySelectorAll(".diag-opt-item");
    allOpts.forEach(o => {
        o.style.pointerEvents = "none";
        o.style.opacity = "0.7";
    });

    const isCorrect = selectedOpt.trim().startsWith(correctOpt.trim().charAt(0)) || selectedOpt.trim() === correctOpt.trim();
    if (isCorrect) {
        optEl.style.background = "rgba(16, 185, 129, 0.25)";
        optEl.style.border = "1.5px solid #10b981";
        optEl.style.color = "#34d399";
        optEl.style.fontWeight = "700";
        optEl.style.opacity = "1";
    } else {
        optEl.style.background = "rgba(239, 68, 68, 0.25)";
        optEl.style.border = "1.5px solid #ef4444";
        optEl.style.color = "#f87171";
        optEl.style.fontWeight = "700";
        optEl.style.opacity = "1";

        allOpts.forEach(o => {
            if (o.textContent.trim().startsWith(correctOpt.trim().charAt(0))) {
                o.style.background = "rgba(16, 185, 129, 0.2)";
                o.style.border = "1.5px solid #10b981";
                o.style.color = "#34d399";
                o.style.opacity = "1";
            }
        });
    }

    const explBox = parent.querySelector(".diag-explanation-box");
    if (explBox) {
        explBox.style.display = "block";
        explBox.style.background = isCorrect ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)";
        explBox.style.borderLeft = isCorrect ? "3px solid #10b981" : "3px solid #ef4444";
        const explText = explBox.querySelector(".diag-expl-text");
        if (explText) {
            explText.innerHTML = `<strong>${isCorrect ? '✅ Correct!' : '❌ Incorrect.'} Correct Answer: ${escapeHtmlLocal(correctOpt)}</strong>`;
        }
    }
};

window.closeWeaknessModal = function() {
    const modal = document.getElementById("weakness-profile-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.style.display = "none";
    }
};

function renderWeaknessProfile(profile) {
    if (!profile) return;

    try {
        // KPI Metrics
        const critCount = document.getElementById("kpi-critical-count");
        const foundCount = document.getElementById("kpi-foundational-count");
        const avgMastery = document.getElementById("kpi-avg-mastery");
        const totWeak = document.getElementById("kpi-total-weaknesses");

        const criticalList = profile.critical_weaknesses || [];
        const foundationalList = profile.foundational_gaps || [];
        const secondaryList = profile.secondary_weaknesses || [];

        if (critCount) critCount.textContent = criticalList.length;
        if (foundCount) foundCount.textContent = foundationalList.length;
        if (avgMastery) avgMastery.textContent = `${Math.round(profile.avg_mastery_score || 0)}%`;
        if (totWeak) totWeak.textContent = profile.total_weaknesses || (criticalList.length + foundationalList.length + secondaryList.length);

        // Section 1: Critical Weaknesses
        const critContainer = document.getElementById("weakness-critical-list");
        if (critContainer) {
            if (criticalList.length === 0) {
                critContainer.innerHTML = `<div style="padding: 12px; font-size: 13px; color: #94a3b8; background: rgba(255,255,255,0.02); border-radius: 8px;">✨ No critical weaknesses detected right now! Keep maintaining high mastery.</div>`;
            } else {
                critContainer.innerHTML = criticalList.map(item => createWeaknessCardHtml(item, 'critical')).join('');
            }
        }

        // Section 2: Foundational Gaps
        const foundContainer = document.getElementById("weakness-foundational-list");
        if (foundContainer) {
            if (foundationalList.length === 0) {
                foundContainer.innerHTML = `<div style="padding: 12px; font-size: 13px; color: #94a3b8; background: rgba(255,255,255,0.02); border-radius: 8px;">✨ All foundational engineering prerequisites are currently verified solid.</div>`;
            } else {
                foundContainer.innerHTML = foundationalList.map(item => createWeaknessCardHtml(item, 'foundational')).join('');
            }
        }

        // Section 3: Secondary Weaknesses
        const secSection = document.getElementById("weakness-secondary-section");
        const secContainer = document.getElementById("weakness-secondary-list");
        if (secContainer && secondaryList.length > 0) {
            if (secSection) secSection.style.display = "block";
            secContainer.innerHTML = secondaryList.map(item => createWeaknessCardHtml(item, 'secondary')).join('');
        } else if (secSection) {
            secSection.style.display = "none";
        }
    } catch (renderErr) {
        console.error("[RENDER WEAKNESS PROFILE ERROR]", renderErr);
    }
}

function createWeaknessCardHtml(item, type) {
    const concept = item.concept || item.concept_name || "Core Principle";
    const subject = item.subject || "Engineering";
    const mastery = Math.round(item.mastery || 0);
    const affected = (item.affected_topics || item.dependent_topics || []).slice(0, 3);
    const times = item.times_confused || 0;

    let affectedHtml = "";
    if (affected && affected.length > 0) {
        affectedHtml = `<div class="weakness-blocked-text">⚠️ Blocks understanding of: <strong>${escapeHtmlLocal(affected.join(', '))}</strong></div>`;
    }

    const safeConcept = escapeHtmlLocal(concept).replace(/'/g, "\\'");

    return `
        <div class="weakness-card">
            <div class="weakness-card-info">
                <div class="weakness-card-title-row">
                    <span class="weakness-concept-name">${escapeHtmlLocal(concept)}</span>
                    <span class="weakness-subject-tag">${escapeHtmlLocal(subject)}</span>
                    ${times >= 2 ? `<span style="font-size: 10.5px; background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: 700;">Confused ${times}x</span>` : ''}
                </div>
                ${affectedHtml}
                <div class="weakness-progress-row">
                    <div class="weakness-progress-bar-bg">
                        <div class="weakness-progress-fill" style="width: ${Math.max(5, mastery)}%;"></div>
                    </div>
                    <span class="weakness-progress-pct">${mastery}%</span>
                </div>
            </div>
            <button type="button" class="btn-start-practice" onclick="closeWeaknessModal(); startAdaptivePractice('${safeConcept}', 'easy');">
                <span>▶ Practice & Fix</span>
            </button>
        </div>
    `;
}

function renderConceptGraphChips(dependencies) {
    const container = document.getElementById("concept-dependency-chips");
    if (!container || !dependencies) return;

    try {
        container.innerHTML = dependencies.slice(0, 12).map(dep => {
            const safePrereq = escapeHtmlLocal(dep.prerequisite_concept).replace(/'/g, "\\'");
            return `
                <div style="padding: 6px 10px; border-radius: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); font-size: 11.5px; color: #cbd5e1; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; transition: all 0.2s ease;" onclick="closeWeaknessModal(); startAdaptivePractice('${safePrereq}', 'easy');" title="Click to practice prerequisite ${escapeHtmlLocal(dep.prerequisite_concept)}">
                    <span style="color: #f43f5e; font-weight: 700;">${escapeHtmlLocal(dep.prerequisite_concept)}</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #94a3b8;">${escapeHtmlLocal(dep.dependent_concept)}</span>
                </div>
            `;
        }).join('');
    } catch (graphErr) {
        console.error("[RENDER GRAPH CHIPS ERROR]", graphErr);
    }
}

// ── In-Chat Weakness Notification Card ──
window.renderInChatConceptWeakness = function(payload, container) {
    if (!payload || !container) return;

    // Check if already rendered in container
    if (container.querySelector(".in-chat-weakness-alert")) return;

    const concept = payload.concept || "Key Principle";
    const affected = (payload.related_topics || []).slice(0, 2);
    const affectedMsg = affected.length > 0 ? `Affects downstream mastery of <strong>${escapeHtmlLocal(affected.join(', '))}</strong>.` : "";
    const safeConcept = escapeHtmlLocal(concept).replace(/'/g, "\\'");

    const alertDiv = document.createElement("div");
    alertDiv.className = "in-chat-weakness-alert";
    alertDiv.innerHTML = `
        <div class="in-chat-weakness-header">
            <span class="in-chat-weakness-badge">🎯 ACADEMIC EDGE WEAKNESS DETECTED</span>
            <span style="font-size: 11px; color: #94a3b8;">Root Concept Blocker</span>
        </div>
        <div style="font-size: 13.5px; color: #f1f5f9; line-height: 1.4;">
            I noticed you're encountering repeated friction with <strong>${escapeHtmlLocal(concept)}</strong>. ${affectedMsg}
        </div>
        <div style="display: flex; gap: 10px; margin-top: 4px;">
            <button type="button" class="btn-start-practice" style="padding: 7px 14px; font-size: 12px;" onclick="startAdaptivePractice('${safeConcept}', 'easy')">
                <span>⚡ Fix with 3-Min Adaptive Practice</span>
            </button>
            <button type="button" style="padding: 7px 12px; font-size: 12px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); color: #cbd5e1; border-radius: 8px; cursor: pointer;" onclick="showWeaknessProfile()">
                View Full Concept Profile
            </button>
        </div>
    `;

    container.appendChild(alertDiv);
    if (typeof scrollToBottom === "function") scrollToBottom();
};

// ── Interactive Adaptive Practice Engine ──
window.startAdaptivePractice = async function(concept, difficulty = "easy") {
    const modal = document.getElementById("adaptive-practice-modal");
    if (!modal) return;

    modal.classList.remove("hidden");
    modal.style.display = "flex";

    const qContainer = document.getElementById("practice-question-container");
    const sContainer = document.getElementById("practice-summary-container");
    if (qContainer) qContainer.style.display = "block";
    if (sContainer) sContainer.style.display = "none";

    const conceptTitle = document.getElementById("practice-concept-title");
    if (conceptTitle) conceptTitle.textContent = `Practice: ${concept}`;

    const qPrompt = document.getElementById("practice-question-text");
    if (qPrompt) qPrompt.textContent = `Generating personalized adaptive questions for "${concept}"...`;

    try {
        const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = user.email || "";
        const res = await fetch(`/api/practice/generate?concept=${encodeURIComponent(concept)}&difficulty=${difficulty}&user_email=${encodeURIComponent(email)}`);
        
        if (!res.ok) {
            throw new Error(`API error ${res.status}`);
        }

        const sessionData = await res.json();
        currentPracticeSession = sessionData;
        currentQuestionIndex = 0;
        selectedPracticeAnswer = null;

        renderPracticeCurrentQuestion();
    } catch (err) {
        console.error("Error generating adaptive practice:", err);
        // Fallback default question if offline or API error
        currentPracticeSession = {
            session_id: 999,
            concept: concept,
            difficulty: difficulty,
            questions: [
                {
                    id: 999,
                    question: `Which fundamental principle is most critical to understanding "${concept}" in engineering?`,
                    type: "mcq",
                    options: [
                        "Application of first principles and boundary laws",
                        "Ignoring physical system constraints",
                        "Assuming zero system entropy",
                        "Only memorizing formula results without derivation"
                    ],
                    hint: `Focus on the foundational mathematical or physical boundary conditions for ${concept}.`
                }
            ]
        };
        currentQuestionIndex = 0;
        selectedPracticeAnswer = null;
        renderPracticeCurrentQuestion();
    }
};

window.closePracticeModal = function() {
    const modal = document.getElementById("adaptive-practice-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.style.setProperty("display", "none", "important");
    }
    currentPracticeSession = null;
};

function renderPracticeCurrentQuestion() {
    if (!currentPracticeSession || !currentPracticeSession.questions) return;
    const questions = currentPracticeSession.questions;
    if (currentQuestionIndex >= questions.length) {
        finishPracticeSession();
        return;
    }

    const q = questions[currentQuestionIndex];
    selectedPracticeAnswer = null;
    questionStartTime = Date.now();

    // Reset controls & feedback
    const diffBadge = document.getElementById("practice-difficulty-badge");
    const progressText = document.getElementById("practice-progress-text");
    const qPrompt = document.getElementById("practice-question-text");
    const optsContainer = document.getElementById("practice-options-container");
    const feedbackCard = document.getElementById("practice-feedback-card");
    const hintBox = document.getElementById("practice-hint-box");
    const submitBtn = document.getElementById("btn-submit-practice-answer");
    const nextBtn = document.getElementById("btn-next-practice-question");

    const currentDiff = (currentPracticeSession.difficulty || "easy").toUpperCase();
    if (diffBadge) {
        diffBadge.textContent = currentDiff;
        diffBadge.className = `practice-diff-badge diff-${currentDiff.toLowerCase()}`;
    }

    if (progressText) {
        progressText.textContent = `Question ${currentQuestionIndex + 1} of ${questions.length} | Adaptive Engine Active`;
    }

    if (qPrompt) qPrompt.textContent = q.question;

    if (feedbackCard) feedbackCard.style.display = "none";
    if (hintBox) {
        hintBox.style.display = "none";
        hintBox.textContent = q.hint || "Focus on the fundamental physical equation or definition.";
    }
    if (submitBtn) {
        submitBtn.style.display = "block";
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Answer";
    }
    if (nextBtn) nextBtn.style.display = "none";

    // Render Options
    if (optsContainer) {
        const letters = ["A", "B", "C", "D"];
        const options = q.options || [];
        optsContainer.innerHTML = options.map((opt, idx) => {
            const letter = letters[idx] || (idx + 1);
            const safeOpt = escapeHtmlLocal(opt).replace(/'/g, "\\'");
            return `
                <button type="button" class="practice-option-btn" id="practice-opt-${idx}" onclick="selectPracticeOption(${idx}, '${safeOpt}')">
                    <span class="practice-opt-letter">${letter}</span>
                    <span>${escapeHtmlLocal(opt)}</span>
                </button>
            `;
        }).join('');
    }
}

window.selectPracticeOption = function(idx, optText) {
    selectedPracticeAnswer = optText;
    const allBtns = document.querySelectorAll(".practice-option-btn");
    allBtns.forEach((btn, i) => {
        if (i === idx) btn.classList.add("selected");
        else btn.classList.remove("selected");
    });
};

window.togglePracticeHint = function() {
    const hintBox = document.getElementById("practice-hint-box");
    if (!hintBox) return;
    hintBox.style.display = (hintBox.style.display === "none" || !hintBox.style.display) ? "block" : "none";
};

window.submitPracticeCurrentAnswer = async function() {
    if (!selectedPracticeAnswer) {
        alert("Please select an answer option before submitting.");
        return;
    }

    if (!currentPracticeSession || !currentPracticeSession.questions) return;
    const q = currentPracticeSession.questions[currentQuestionIndex];
    const timeTaken = Math.max(3, Math.round((Date.now() - questionStartTime) / 1000));

    const submitBtn = document.getElementById("btn-submit-practice-answer");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Evaluating...";
    }

    try {
        const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = user.email || "";

        const res = await fetch(`/api/practice/${currentPracticeSession.session_id}/answer`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question_id: q.id,
                user_answer: selectedPracticeAnswer,
                time_taken: timeTaken,
                user_id: 1,
                user_email: email
            })
        });

        let evalResult = null;
        if (res.ok) {
            evalResult = await res.json();
        } else {
            evalResult = {
                is_correct: true,
                explanation: "Great attempt! Fundamental concept validated.",
                concept_note: "Core engineering principles established.",
                adapted: false
            };
        }

        // Update UI
        const feedbackCard = document.getElementById("practice-feedback-card");
        const banner = document.getElementById("practice-feedback-banner");
        const adaptBanner = document.getElementById("practice-adaptation-banner");
        const explText = document.getElementById("practice-explanation-text");
        const conceptNote = document.getElementById("practice-concept-note-text");
        const nextBtn = document.getElementById("btn-next-practice-question");

        if (feedbackCard) {
            feedbackCard.style.display = "block";
            if (evalResult.is_correct) {
                feedbackCard.style.background = "rgba(16, 185, 129, 0.12)";
                feedbackCard.style.border = "1px solid rgba(16, 185, 129, 0.35)";
                if (banner) {
                    banner.innerHTML = `<span style="color: #10b981;">✅ Correct! Outstanding conceptual reasoning.</span>`;
                }
            } else {
                feedbackCard.style.background = "rgba(239, 68, 68, 0.12)";
                feedbackCard.style.border = "1px solid rgba(239, 68, 68, 0.35)";
                if (banner) {
                    banner.innerHTML = `<span style="color: #ef4444;">❌ Incorrect. Let's understand why:</span>`;
                }
            }
        }

        if (evalResult.adapted && adaptBanner) {
            adaptBanner.style.display = "block";
            adaptBanner.textContent = evalResult.adaptation_message || `🔥 Difficulty adapted to ${evalResult.next_difficulty.toUpperCase()}!`;
            currentPracticeSession.difficulty = evalResult.next_difficulty;
        } else if (adaptBanner) {
            adaptBanner.style.display = "none";
        }

        if (explText) explText.textContent = evalResult.explanation || "";
        if (conceptNote) conceptNote.innerHTML = `<strong>Theoretical Principle:</strong> ${escapeHtmlLocal(evalResult.concept_note || '')}`;

        if (submitBtn) submitBtn.style.display = "none";
        if (nextBtn) nextBtn.style.display = "block";

    } catch (err) {
        console.error("Error submitting answer:", err);
        const feedbackCard = document.getElementById("practice-feedback-card");
        const banner = document.getElementById("practice-feedback-banner");
        const nextBtn = document.getElementById("btn-next-practice-question");
        if (feedbackCard) {
            feedbackCard.style.display = "block";
            feedbackCard.style.background = "rgba(16, 185, 129, 0.12)";
            if (banner) banner.innerHTML = `<span style="color: #10b981;">Answer recorded.</span>`;
        }
        if (submitBtn) submitBtn.style.display = "none";
        if (nextBtn) nextBtn.style.display = "block";
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
};

window.nextPracticeQuestion = function() {
    currentQuestionIndex += 1;
    renderPracticeCurrentQuestion();
};

async function finishPracticeSession() {
    if (!currentPracticeSession) return;

    const qContainer = document.getElementById("practice-question-container");
    const sContainer = document.getElementById("practice-summary-container");
    if (qContainer) qContainer.style.display = "none";
    if (sContainer) sContainer.style.display = "block";

    try {
        const user = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = user.email || "";

        const res = await fetch(`/api/practice/${currentPracticeSession.session_id}/complete?user_email=${encodeURIComponent(email)}`, {
            method: "POST"
        });
        const summary = await res.json();

        const scoreVal = document.getElementById("summary-score-val");
        const masteryVal = document.getElementById("summary-mastery-val");
        const timeVal = document.getElementById("summary-time-val");
        const badge = document.getElementById("summary-mastery-badge");

        if (scoreVal) scoreVal.textContent = `${summary.correct_answers || 1}/${summary.total_questions || 1}`;
        if (masteryVal) masteryVal.textContent = `${Math.round(summary.mastery_percentage || 25)}%`;
        if (timeVal) timeVal.textContent = `${summary.time_spent_seconds || 15}s`;

        if (badge) {
            const lvl = (summary.mastery_level || "intermediate").toUpperCase();
            badge.textContent = `Mastery: ${lvl}`;
            if (lvl === "EXPERT") {
                badge.style.background = "rgba(16, 185, 129, 0.2)";
                badge.style.color = "#34d399";
                badge.style.border = "1px solid #10b981";
            } else if (lvl === "INTERMEDIATE") {
                badge.style.background = "rgba(99, 102, 241, 0.2)";
                badge.style.color = "#818cf8";
                badge.style.border = "1px solid #6366f1";
            } else {
                badge.style.background = "rgba(245, 158, 11, 0.2)";
                badge.style.color = "#fbbf24";
                badge.style.border = "1px solid #f59e0b";
            }
        }
        fetchUserStats();
        if (window.fetchLeaderboard) window.fetchLeaderboard();
    } catch (err) {
        console.error("Error completing practice session:", err);
    }
}

// ==========================================================================
// 7. Creator & Super-Admin Intelligence Dashboard + Live Heartbeat Telemetry
// ==========================================================================

const CREATOR_ADMIN_EMAILS = [
    "ombansal221@gmail.com",
    "s24cseu1694@bennett.edu.in",
    "om0710@gmail.com",
    "om.bansal@bennett.edu.in",
    "admin@prepz.ai"
];

let adminDashboardCache = null;
let adminTableFilter = 'all';
let heartbeatIntervalId = null;

// Unique session ID per browser tab lifetime
const prepzSessionId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

function isCurrentCreatorAdmin() {
    try {
        const u = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
        const email = (u.email || "").toLowerCase().trim();
        return CREATOR_ADMIN_EMAILS.includes(email);
    } catch (e) {
        return false;
    }
}

function checkAndEnableAdminUI() {
    const navCreator = document.getElementById("nav-creator-dashboard-btn");
    if (!navCreator) return;
    if (isCurrentCreatorAdmin()) {
        navCreator.classList.remove("hidden");
        navCreator.style.removeProperty("display");
        navCreator.style.display = "flex";
    } else {
        navCreator.classList.add("hidden");
        navCreator.style.display = "none";
    }
}
window.checkAndEnableAdminUI = checkAndEnableAdminUI;

// Heartbeat Daemon (Sends ping every 30s when tab is active and visible)
function startHeartbeatDaemon() {
    if (heartbeatIntervalId) clearInterval(heartbeatIntervalId);

    async function sendHeartbeat() {
        if (document.visibilityState === 'hidden') return;
        try {
            const u = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
            const email = u.email || "";
            if (!email || email === "anonymous@college.edu") return;
            const name = u.name || "";

            await fetch("/api/analytics/heartbeat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: prepzSessionId,
                    user_email: email,
                    user_name: name
                })
            });
        } catch (e) {
            // Background telemetry notice
        }
    }

    // Immediate ping on start
    sendHeartbeat();
    heartbeatIntervalId = setInterval(sendHeartbeat, 30000);

    // Send ping immediately when switching back to tab
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            sendHeartbeat();
        }
    });
}
window.startHeartbeatDaemon = startHeartbeatDaemon;

function formatDwellTime(seconds) {
    const s = parseInt(seconds || 0, 10);
    if (s < 60) return `${s}s`;
    const mins = Math.floor(s / 60);
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hrs}h ${remMins}m`;
}

function formatRelativeTime(isoStr) {
    if (!isoStr) return "Never";
    try {
        const d = new Date(isoStr.endsWith("Z") ? isoStr : isoStr + "Z");
        const diffMs = Date.now() - d.getTime();
        const diffSec = Math.max(0, Math.floor(diffMs / 1000));
        if (diffSec < 45) return "Just now";
        if (diffSec < 90) return "1 min ago";
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr}h ago`;
        const diffDay = Math.floor(diffHr / 24);
        return `${diffDay}d ago`;
    } catch (e) {
        return isoStr.split("T")[0] || isoStr;
    }
}

// Generic Modal Management Helpers
window.openModalById = function(modalId) {
    const el = document.getElementById(modalId);
    if (!el) {
        console.warn("[MODAL] Element not found:", modalId);
        return;
    }
    el.classList.remove("hidden");
    el.style.removeProperty("display");
    el.style.display = "flex";
    document.body.style.overflow = "hidden";
};

window.closeModalById = function(modalId) {
    const el = document.getElementById(modalId);
    if (!el) return;
    el.classList.add("hidden");
    el.style.display = "none";
    document.body.style.overflow = "";
};

// Global ESC key listener to dismiss open modals
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        const openModals = document.querySelectorAll(".modal-overlay:not(.hidden)");
        openModals.forEach(m => {
            m.classList.add("hidden");
            m.style.display = "none";
        });
        document.body.style.overflow = "";
    }
});

// Fetch and render creator admin dashboard
async function fetchAndRenderAdminDashboard(isManualClick = false) {
    const u = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const adminEmail = (u.email || "").toLowerCase().trim();

    if (!isCurrentCreatorAdmin()) {
        console.warn("Creator Dashboard is restricted to authorized creators.");
        return;
    }

    const refreshBtn = document.getElementById("btn-creator-refresh");
    const refreshIcon = document.getElementById("creator-refresh-icon");
    const refreshText = document.getElementById("creator-refresh-text");

    if (isManualClick && refreshBtn) {
        refreshBtn.disabled = true;
        if (refreshIcon) refreshIcon.style.animation = "spin 0.7s linear infinite";
        if (refreshText) refreshText.textContent = "Refreshing...";
    }

    try {
        const res = await fetch(`/api/admin/dashboard?admin_email=${encodeURIComponent(adminEmail)}`);
        if (!res.ok) {
            throw new Error(`Admin dashboard error: ${res.statusText}`);
        }
        const data = await res.json();
        adminDashboardCache = data;

        // 1. Render KPIs
        const kpis = data.kpis || {};
        const kpiOnline = document.getElementById("kpi-online-now");
        const kpiActiveToday = document.getElementById("kpi-active-today");
        const kpiDwellTime = document.getElementById("kpi-dwell-time");
        const kpiUploads = document.getElementById("kpi-total-uploads");

        if (kpiOnline) kpiOnline.textContent = kpis.online_now || 0;
        if (kpiActiveToday) kpiActiveToday.textContent = kpis.active_today || 0;
        if (kpiDwellTime) kpiDwellTime.textContent = formatDwellTime(kpis.total_platform_dwell_time_seconds);
        if (kpiUploads) kpiUploads.textContent = kpis.total_uploads || 0;

        const subReg = document.getElementById("kpi-total-registered-sub");
        if (subReg) subReg.textContent = `Total: ${kpis.total_registered_users || 0} registered`;

        const subTodayDwell = document.getElementById("kpi-today-dwell-sub");
        if (subTodayDwell) subTodayDwell.textContent = `Today: ${formatDwellTime(kpis.today_platform_dwell_time_seconds)} engagement`;

        const subActions = document.getElementById("kpi-total-actions-sub");
        if (subActions) subActions.textContent = `${kpis.total_actions || 0} total platform actions`;

        // 2. Render Users Table
        filterAdminUserTable();

        // 3. Render Recent Activity Stream
        renderAdminActivityStream(data.recent_activity || []);

    } catch (err) {
        console.error("Error fetching creator dashboard:", err);
    } finally {
        if (isManualClick && refreshBtn) {
            setTimeout(() => {
                refreshBtn.disabled = false;
                if (refreshIcon) refreshIcon.style.animation = "";
                if (refreshText) refreshText.textContent = "Live Refresh";
            }, 400);
        }
    }
}
window.fetchAndRenderAdminDashboard = fetchAndRenderAdminDashboard;

function renderAdminUserTable(users) {
    const tbody = document.getElementById("creator-users-tbody");
    const countBadge = document.getElementById("creator-users-count-badge");
    if (countBadge) countBadge.textContent = `${users.length} Students`;
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #8a8f98; padding: 28px; font-size: 13px;">No students match criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = users.map(user => {
        const isOnline = user.is_online;
        let statusBadge = `<span class="status-chip offline">⚪ Offline</span>`;
        if (isOnline) {
            statusBadge = `<span class="status-chip online"><span class="live-dot-pulse" style="width:6px;height:6px;"></span> Online Now</span>`;
        } else if (user.today_duration_seconds > 0) {
            statusBadge = `<span class="status-chip recent">⚡ Active Today</span>`;
        }

        const avatar = user.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(user.email)}`;
        const safeEmail = encodeURIComponent(user.email);

        return `
            <tr style="cursor: pointer;" onclick="if (!event.target.closest('.btn-inspect-user')) openAdminUserDrilldown('${safeEmail}')">
                <td>
                    <div class="student-meta-cell">
                        <img src="${avatar}" class="student-table-avatar" alt="Avatar" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed=BU'">
                        <div class="student-name-stack">
                            <span class="student-table-name">${user.name || "Student"}</span>
                            <span class="student-table-email">${user.email}</span>
                        </div>
                    </div>
                </td>
                <td style="text-align: center;">${statusBadge}</td>
                <td style="text-align: right; font-family: var(--font-mono); font-weight: 700; color: #ff8a65;">${formatDwellTime(user.today_duration_seconds)}</td>
                <td style="text-align: right; font-family: var(--font-mono); color: #94a3b8;">${formatDwellTime(user.total_duration_seconds)}</td>
                <td style="text-align: center;">
                    <span style="display: inline-block; background: rgba(255, 255, 255, 0.06); padding: 2px 8px; border-radius: 6px; font-weight: 700;">${user.uploads_count || 0}</span>
                </td>
                <td style="text-align: right; font-family: var(--font-mono); color: #cbd5e1;">${user.actions_count || 0}</td>
                <td style="text-align: center;">
                    <button type="button" class="btn-inspect-user" onclick="event.stopPropagation(); openAdminUserDrilldown('${safeEmail}', this)">Inspect ↗</button>
                </td>
            </tr>
        `;
    }).join("");
}

function filterAdminUserTable() {
    if (!adminDashboardCache) return;
    const searchVal = (document.getElementById("admin-user-search-input")?.value || "").toLowerCase().trim();
    let filtered = adminDashboardCache.users || [];

    if (searchVal) {
        filtered = filtered.filter(u => 
            (u.name || "").toLowerCase().includes(searchVal) || 
            (u.email || "").toLowerCase().includes(searchVal)
        );
    }

    if (adminTableFilter === 'online') {
        filtered = filtered.filter(u => u.is_online);
    } else if (adminTableFilter === 'uploads') {
        filtered = filtered.filter(u => u.uploads_count > 0);
    }

    renderAdminUserTable(filtered);
}
window.filterAdminUserTable = filterAdminUserTable;

function setAdminUserFilter(filterType, btnEl) {
    adminTableFilter = filterType;
    document.querySelectorAll(".filter-pills-row .filter-pill").forEach(p => p.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    filterAdminUserTable();
}
window.setAdminUserFilter = setAdminUserFilter;

function renderAdminActivityStream(activities) {
    const list = document.getElementById("creator-activity-stream-list");
    if (!list) return;

    if (!activities || activities.length === 0) {
        list.innerHTML = `<div style="text-align:center;color:#64748b;padding:24px;font-size:12px;">No activity logged yet today.</div>`;
        return;
    }

    list.innerHTML = activities.map(act => {
        let badgeClass = "badge-login";
        const t = (act.action_type || "").toUpperCase();
        if (t.includes("UPLOAD")) badgeClass = "badge-upload";
        else if (t.includes("PREDICT")) badgeClass = "badge-predict";
        else if (t.includes("CONCEPT") || t.includes("WEAKNESS")) badgeClass = "badge-concept";

        return `
            <div class="stream-item">
                <div class="stream-item-top">
                    <span class="stream-action-badge ${badgeClass}">${act.action_type}</span>
                    <span class="stream-time">${formatRelativeTime(act.timestamp)}</span>
                </div>
                <div class="stream-user">${act.user_name || act.user_email}</div>
                <div class="stream-details">${act.action_details || "Action recorded"}</div>
            </div>
        `;
    }).join("");
}

// Deep User Drilldown Modal Handler
async function openAdminUserDrilldown(encodedEmail, btnElement = null) {
    const targetEmail = decodeURIComponent(encodedEmail);
    const u = window.currentUser || JSON.parse(localStorage.getItem("docpilot-user") || "{}");
    const adminEmail = (u.email || "").toLowerCase().trim();

    const originalBtnHtml = btnElement ? btnElement.innerHTML : null;
    if (btnElement) {
        btnElement.disabled = true;
        btnElement.innerHTML = `<span style="font-size: 11px;">Loading...</span>`;
    }

    try {
        const res = await fetch(`/api/admin/user-drilldown?admin_email=${encodeURIComponent(adminEmail)}&user_email=${encodeURIComponent(targetEmail)}`);
        if (!res.ok) throw new Error("Failed to load user details");
        const data = await res.json();

        // Populate drawer
        const prof = data.profile || {};
        const drawerAvatar = document.getElementById("drawer-user-avatar");
        const drawerName = document.getElementById("drawer-user-name");
        const drawerEmail = document.getElementById("drawer-user-email");

        if (drawerAvatar) drawerAvatar.src = prof.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(prof.email || targetEmail)}`;
        if (drawerName) drawerName.textContent = prof.name || targetEmail.split("@")[0].replace(".", " ").replace("_", " ").title();
        if (drawerEmail) drawerEmail.textContent = prof.email || targetEmail;

        const statTime = document.getElementById("drawer-stat-total-time");
        const statUploads = document.getElementById("drawer-stat-uploads");
        const statStreak = document.getElementById("drawer-stat-streak");
        const statPoints = document.getElementById("drawer-stat-points");

        if (statTime) statTime.textContent = formatDwellTime(data.total_duration_seconds);
        if (statUploads) statUploads.textContent = (data.uploads || []).length;
        if (statStreak) statStreak.textContent = `${prof.current_streak || 1} Days`;
        if (statPoints) statPoints.textContent = prof.contribution_score || 0;

        // Render Uploads
        const uploadsCount = document.getElementById("drawer-uploads-count");
        if (uploadsCount) uploadsCount.textContent = (data.uploads || []).length;
        const uploadsList = document.getElementById("drawer-uploads-list");
        if (uploadsList) {
            if (!data.uploads || data.uploads.length === 0) {
                uploadsList.innerHTML = `<div style="text-align: center; color: #8a8f98; padding: 24px; font-size: 13px;">No files uploaded yet by this user.</div>`;
            } else {
                uploadsList.innerHTML = data.uploads.map(up => `
                    <div class="drawer-item-card">
                        <div style="flex: 1; overflow: hidden;">
                            <div style="font-weight: 700; color: #ffffff; font-size: 13px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${up.filename}</div>
                            <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">${up.subject} &bull; ${up.semester} &bull; ${up.file_type} (${Math.round((up.size_bytes || 0) / 1024)} KB)</div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <a href="/view/${encodeURIComponent(up.filename)}?is_private=${up.is_private ? 1 : 0}&user_email=${encodeURIComponent(prof.email || '')}" target="_blank" class="btn-inspect-user" style="text-decoration:none;">View ↗</a>
                            <a href="/download/${encodeURIComponent(up.filename)}?disposition=attachment&is_private=${up.is_private ? 1 : 0}&user_email=${encodeURIComponent(prof.email || '')}" target="_blank" class="btn-inspect-user" style="text-decoration:none; background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.15);">⤓</a>
                        </div>
                    </div>
                `).join("");
            }
        }

        // Render Timeline
        const actCount = document.getElementById("drawer-activity-count");
        if (actCount) actCount.textContent = (data.activity_logs || []).length;
        const timelineList = document.getElementById("drawer-timeline-list");
        if (timelineList) {
            if (!data.activity_logs || data.activity_logs.length === 0) {
                timelineList.innerHTML = `<div style="color: #8a8f98; padding: 24px; text-align: center; font-size: 13px;">No recorded events for this user yet.</div>`;
            } else {
                timelineList.innerHTML = data.activity_logs.map(log => `
                    <div class="drawer-timeline-item">
                        <div style="display:flex; justify-content:space-between; font-size: 11.5px; font-weight:700; color:#ff8a65;">
                            <span>${log.action_type}</span>
                            <span style="color:#64748b; font-family:var(--font-mono); font-weight: 500;">${formatRelativeTime(log.timestamp)}</span>
                        </div>
                        <div style="font-size: 12px; color: #cbd5e1; margin-top: 3px;">${log.action_details || "Recorded action"}</div>
                    </div>
                `).join("");
            }
        }

        // Render Weaknesses
        const weaknessesList = document.getElementById("drawer-weaknesses-list");
        if (weaknessesList) {
            if (!data.concept_weaknesses || data.concept_weaknesses.length === 0) {
                weaknessesList.innerHTML = `<div style="text-align: center; color: #8a8f98; padding: 24px; font-size: 13px;">No concept weaknesses flagged yet.</div>`;
            } else {
                weaknessesList.innerHTML = data.concept_weaknesses.map(w => `
                    <div class="drawer-item-card">
                        <div>
                            <div style="font-weight: 700; color: #ffffff; font-size: 13px;">${w.concept}</div>
                            <div style="font-size: 11.5px; color: #f43f5e; margin-top: 2px;">Subject: ${w.subject} &bull; Mastery: ${Math.round(w.mastery_percentage || 0)}%</div>
                        </div>
                        <span style="font-size: 11px; color: #8a8f98; font-family: var(--font-mono);">${formatRelativeTime(w.recorded_at)}</span>
                    </div>
                `).join("");
            }
        }

        // Open modal
        switchDrawerTab('uploads');
        window.openModalById("admin-user-drawer-modal");

    } catch (err) {
        console.error("Error loading user drilldown:", err);
    } finally {
        if (btnElement && originalBtnHtml) {
            btnElement.disabled = false;
            btnElement.innerHTML = originalBtnHtml;
        }
    }
}
window.openAdminUserDrilldown = openAdminUserDrilldown;

function switchDrawerTab(tabName) {
    document.querySelectorAll(".drawer-tabs-row .drawer-tab-btn").forEach(b => b.classList.remove("active"));
    const activeBtn = document.getElementById(`tab-drawer-${tabName}`);
    if (activeBtn) activeBtn.classList.add("active");

    const vUploads = document.getElementById("drawer-view-uploads");
    const vTimeline = document.getElementById("drawer-view-timeline");
    const vWeaknesses = document.getElementById("drawer-view-weaknesses");

    if (vUploads) { vUploads.classList.add("hidden"); vUploads.style.display = "none"; }
    if (vTimeline) { vTimeline.classList.add("hidden"); vTimeline.style.display = "none"; }
    if (vWeaknesses) { vWeaknesses.classList.add("hidden"); vWeaknesses.style.display = "none"; }

    const targetView = document.getElementById(`drawer-view-${tabName}`);
    if (targetView) {
        targetView.classList.remove("hidden");
        targetView.style.display = "block";
    }
}
window.switchDrawerTab = switchDrawerTab;

// Auto-run admin check and heartbeat on initialization
document.addEventListener("DOMContentLoaded", () => {
    checkAndEnableAdminUI();
    startHeartbeatDaemon();
});

// Also trigger admin check whenever user session is updated
window.addEventListener("storage", () => {
    checkAndEnableAdminUI();
});

