// Auto-bypass ngrok browser warning pages and redirect API calls to local/origin backend
const originalFetch = window.fetch;
let API_BASE_URL = "";
if (window.location.protocol === "file:") {
    API_BASE_URL = "http://localhost:7865";
} else {
    API_BASE_URL = window.location.origin;
}

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

// Global Fail-Proof Auth Handlers
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

window.loginUser = function (user) {
    if (!user) user = { name: "Student User", email: "student@college.edu", provider: "local" };
    localStorage.setItem("docpilot-user", JSON.stringify(user));

    if (user.email && typeof saveGoogleAccountToHistory === "function") {
        saveGoogleAccountToHistory({
            name: user.name || "Student User",
            email: user.email,
            avatar_url: user.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user.email}`
        });
    }

    const landingPageView = document.getElementById("landing-page-view");
    const chatbotAppView = document.getElementById("chatbot-app-view");

    if (landingPageView) {
        landingPageView.classList.add("hidden");
        landingPageView.style.setProperty("display", "none", "important");
    }
    if (chatbotAppView) {
        chatbotAppView.classList.remove("hidden");
        chatbotAppView.style.setProperty("display", "flex", "important");
    }

    const userAvatar = document.querySelector(".sidebar-user-avatar");
    const userName = document.querySelector(".sidebar-user-name");
    const userEmail = document.querySelector(".sidebar-user-email");

    if (userName) userName.textContent = user.name || "Student User";
    if (userEmail) userEmail.textContent = user.email || "student@college.edu";
    if (userAvatar) {
        const avatarUrl = user.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user.email || 'user'}`;
        userAvatar.style.backgroundImage = `url('${avatarUrl}')`;
        userAvatar.innerHTML = "";
    }
};

// Google Accounts History Store (Device local only)
function getGoogleAccountsHistory() {
    try {
        const stored = localStorage.getItem("prepz_google_accounts");
        if (stored) return JSON.parse(stored);
    } catch(e) {}
    return [];
}

function saveGoogleAccountToHistory(acc) {
    let accounts = getGoogleAccountsHistory();
    accounts = accounts.filter(a => a.email.toLowerCase() !== acc.email.toLowerCase());
    accounts.unshift(acc);
    try {
        localStorage.setItem("prepz_google_accounts", JSON.stringify(accounts));
    } catch(e) {}
}

window.closeGoogleAccountModal = function() {
    const modal = document.getElementById("google-account-modal");
    if (modal) {
        modal.classList.add("hidden");
        modal.style.display = "none";
    }
};

window.selectGoogleAccount = async function(name, email, avatar_url) {
    window.closeGoogleAccountModal();
    if (!email || !window.isValidEmail(email)) {
        showAuthErrorMsg("Please enter a valid Gmail address (e.g. user@gmail.com).");
        return;
    }

    const accObj = {
        name: name,
        email: email.trim().toLowerCase(),
        picture: avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(email)}`
    };

    try {
        const res = await fetch("/api/google-login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(accObj)
        });
        const data = await res.json();
        if (res.ok && data.user) {
            saveGoogleAccountToHistory({ name: data.user.name, email: data.user.email, avatar_url: data.user.avatar_url });
            window.loginUser(data.user);
        } else {
            const errDetail = data && data.detail ? data.detail : "Google Sign-In failed. Please enter a valid Gmail address.";
            showAuthErrorMsg(errDetail);
        }
    } catch (err) {
        showAuthErrorMsg("Unable to connect to server for Google Sign-In. Please check your connection.");
    }
};

window.handleGoogleLogin = function () {
    let accounts = getGoogleAccountsHistory();

    const modal = document.getElementById("google-account-modal");
    const accountsListContainer = document.getElementById("google-accounts-list");

    // If no previous Google accounts saved on this device, prompt directly for user's own email
    if (!accounts || accounts.length === 0) {
        const inputEmail = prompt("Enter your Gmail address to Continue with Google:", "");
        if (inputEmail && inputEmail.trim()) {
            const rawEmail = inputEmail.trim().toLowerCase();
            if (!window.isValidEmail(rawEmail)) {
                showAuthErrorMsg("Please enter a valid Gmail address (e.g. user@gmail.com).");
                return;
            }
            const rawName = rawEmail.split("@")[0].replace(/[._-]/g, " ");
            const formattedName = rawName.charAt(0).toUpperCase() + rawName.slice(1);
            window.selectGoogleAccount(formattedName, rawEmail, `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(rawEmail)}`);
        }
        return;
    }

    accountsListContainer.innerHTML = "";
    accounts.forEach(acc => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-google-account-item";
        btn.onclick = function() {
            window.selectGoogleAccount(acc.name, acc.email, acc.avatar_url);
        };

        const avatarSrc = acc.avatar_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${acc.email}`;
        btn.innerHTML = `
            <div class="account-avatar-img" style="background-image: url('${avatarSrc}');"></div>
            <div class="account-text-info">
                <span class="account-name">${acc.name}</span>
                <span class="account-email">${acc.email}</span>
            </div>
            <span class="account-select-badge">Log in →</span>
        `;
        accountsListContainer.appendChild(btn);
    });

    const addBtn = document.getElementById("btn-use-another-account");
    if (addBtn) {
        addBtn.onclick = function() {
            window.closeGoogleAccountModal();
            const inputEmail = prompt("Enter another Gmail address:", "");
            if (inputEmail && inputEmail.trim()) {
                const rawEmail = inputEmail.trim().toLowerCase();
                if (!window.isValidEmail(rawEmail)) {
                    showAuthErrorMsg("Please enter a valid Gmail address (e.g. user@gmail.com).");
                    return;
                }
                const rawName = rawEmail.split("@")[0].replace(/[._-]/g, " ");
                const formattedName = rawName.charAt(0).toUpperCase() + rawName.slice(1);
                window.selectGoogleAccount(formattedName, rawEmail, `https://api.dicebear.com/7.x/bottts/svg?seed=${rawEmail}`);
            }
        };
    }

    modal.classList.remove("hidden");
    modal.style.display = "flex";
};

function showAuthErrorMsg(msg) {
    const authErrorMsg = document.getElementById("auth-error-msg");
    if (authErrorMsg) {
        authErrorMsg.textContent = msg;
        authErrorMsg.classList.remove("hidden");
        authErrorMsg.style.display = "block";
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
    const email = emailInput ? emailInput.value.trim() : "";
    const password = pwdInput ? pwdInput.value : "";

    if (!email || !password) {
        showAuthErrorMsg("Please enter both email and password.");
        return;
    }

    if (!window.isValidEmail(email)) {
        showAuthErrorMsg("Please enter a valid email address.");
        return;
    }

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.user) {
            window.loginUser(data.user);
        } else if (data.status === "otp_required") {
            window.openOtpModal(data.email, "signup");
        } else {
            const errorText = data && data.detail ? data.detail : "Invalid email or password.";
            showAuthErrorMsg(errorText);
        }
    } catch (err) {
        showAuthErrorMsg("Unable to connect to server. Please check your connection.");
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
    const email = emailInput && emailInput.value.trim() ? emailInput.value.trim() : "";
    const password = pwdInput ? pwdInput.value : "";
    const captchaAns = captchaInput ? captchaInput.value.trim() : "";

    if (!name || !email || !password) {
        showAuthErrorMsg("All fields are required for sign up.");
        return;
    }

    if (!window.isValidEmail(email)) {
        showAuthErrorMsg("Please enter a valid email address.");
        return;
    }

    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
        showAuthErrorMsg("Password must be at least 8 characters long and contain both letters and numbers.");
        return;
    }

    if (parseInt(captchaAns, 10) !== currentCaptchaState.signup.ans) {
        showAuthErrorMsg("Incorrect Security Challenge answer. Please try again.");
        window.generateCaptcha("signup");
        return;
    }

    try {
        const res = await fetch("/api/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name,
                email,
                password,
                captcha_answer: captchaAns,
                captcha_expected: currentCaptchaState.signup.ans.toString()
            })
        });
        const data = await res.json();
        if (res.ok && data.status === "otp_required") {
            window.openOtpModal(data.email, "signup");
        } else if (res.ok && data.user) {
            window.loginUser(data.user);
        } else {
            const errorText = data && data.detail ? data.detail : "Sign up failed. Please try again.";
            showAuthErrorMsg(errorText);
            window.generateCaptcha("signup");
            
            if (errorText.toLowerCase().includes("already exists")) {
                setTimeout(() => {
                    window.switchAuthTab("login");
                    const loginEmail = document.getElementById("login-email");
                    if (loginEmail) loginEmail.value = email;
                    showAuthErrorMsg("Account already exists! Switched to Log In tab. Please enter your password.");
                }, 1000);
            }
        }
    } catch (err) {
        showAuthErrorMsg("Unable to connect to server. Please check your connection.");
        window.generateCaptcha("signup");
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
    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
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

    const email = emailInput ? emailInput.value.trim() : "";
    const answer = captchaInput ? captchaInput.value.trim() : "";

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
            body: JSON.stringify({
                email,
                captcha_answer: answer,
                captcha_expected: currentCaptchaState.forgot.ans.toString()
            })
        });
        const data = await res.json();
        if (res.ok) {
            window.closeForgotPasswordModal();
            window.openResetPasswordModal(email);
        } else {
            const err = data.detail || "Failed to send reset OTP.";
            if (errEl) {
                errEl.textContent = err;
                errEl.classList.remove("hidden");
                errEl.style.display = "block";
            }
        }
    } catch (err) {
        if (errEl) {
            errEl.textContent = "Network error. Please try again.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
        }
    }
};

window.openResetPasswordModal = function(email, prefilledOtp = "") {
    currentPendingOtpEmail = email;
    const modal = document.getElementById("reset-password-modal");
    const otpInput = document.getElementById("reset-otp-input");
    const errEl = document.getElementById("reset-error-msg");

    if (errEl) { errEl.textContent = ""; errEl.classList.add("hidden"); errEl.style.display = "none"; }
    if (otpInput && prefilledOtp) otpInput.value = prefilledOtp;

    if (modal) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
    }
};

window.closeResetPasswordModal = function() {
    const modal = document.getElementById("reset-password-modal");
    if (modal) { modal.classList.add("hidden"); modal.style.display = "none"; }
};

window.handleResetPasswordSubmit = async function(e) {
    if (e) e.preventDefault();
    const otpInput = document.getElementById("reset-otp-input");
    const newPwdInput = document.getElementById("reset-new-password");
    const errEl = document.getElementById("reset-error-msg");

    const otpCode = otpInput ? otpInput.value.trim() : "";
    const newPassword = newPwdInput ? newPwdInput.value : "";

    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
        if (errEl) {
            errEl.textContent = "Password must be at least 8 characters long with letters and numbers.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
        }
        return;
    }

    try {
        const res = await fetch("/api/forgot-password/reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: currentPendingOtpEmail,
                otp_code: otpCode,
                new_password: newPassword
            })
        });
        const data = await res.json();
        if (res.ok) {
            window.closeResetPasswordModal();
            showAuthErrorMsg("Password reset successful! Logging you in...");
            const loginRes = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: currentPendingOtpEmail, password: newPassword })
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
            }
        }
    } catch (err) {
        if (errEl) {
            errEl.textContent = "Network error resetting password.";
            errEl.classList.remove("hidden");
            errEl.style.display = "block";
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
    let currentUser = null;

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
                authErrorMsg.textContent = msg;
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

        // Login Form Submission
        if (formLogin) {
            formLogin.addEventListener("submit", async (e) => {
                e.preventDefault();
                clearAuthError();
                const emailInput = document.getElementById("login-email");
                const pwdInput = document.getElementById("login-password");
                const email = emailInput ? emailInput.value.trim() : "";
                const password = pwdInput ? pwdInput.value : "";

                if (!email || !password) {
                    showAuthError("Please enter both email and password.");
                    return;
                }

                try {
                    const res = await fetch("/api/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, password })
                    });
                    const data = await res.json();
                    if (res.ok && data.user) {
                        loginUser(data.user);
                    } else {
                        showAuthError(data.detail || "Login failed.");
                    }
                } catch(err) {
                    showAuthError("Connection error. Please try again.");
                }
            });
        }

        // Signup Form Submission
        if (formSignup) {
            formSignup.addEventListener("submit", async (e) => {
                e.preventDefault();
                clearAuthError();
                const nameInput = document.getElementById("signup-name");
                const emailInput = document.getElementById("signup-email");
                const pwdInput = document.getElementById("signup-password");
                
                const name = nameInput ? nameInput.value.trim() : "";
                const email = emailInput ? emailInput.value.trim() : "";
                const password = pwdInput ? pwdInput.value : "";

                if (!name || !email || !password) {
                    showAuthError("All fields (Name, Email, Password) are required.");
                    return;
                }

                try {
                    const res = await fetch("/api/signup", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ name, email, password })
                    });
                    const data = await res.json();
                    if (res.ok && data.user) {
                        loginUser(data.user);
                    } else {
                        showAuthError(data.detail || "Signup failed.");
                    }
                } catch(err) {
                    showAuthError("Connection error. Please try again.");
                }
            });
        }

        if (loginBtn) {
            loginBtn.addEventListener("click", (e) => {
                if (e) e.preventDefault();
                clearAuthError();
                window.handleGoogleLogin();
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

        // Check URL parameters for explicit logout request
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get("logout") === "true" || urlParams.get("switch") === "true") {
            logoutUser();
        } else {
            // Check if session user details are already saved
            const savedUser = localStorage.getItem("docpilot-user") || localStorage.getItem("prepz_user");
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
    }

    function showLoginScreen() {
        currentUser = null;
        localStorage.removeItem("docpilot-user");
        localStorage.removeItem("prepz_user");
        if (navPinnedLibrary) navPinnedLibrary.style.display = "none";
        if (landingPageView) {
            landingPageView.classList.remove("hidden");
            landingPageView.style.display = "flex";
        }
        if (chatbotAppView) {
            chatbotAppView.classList.add("hidden");
            chatbotAppView.style.display = "none";
        }
    }

    function logoutUser() {
        localStorage.removeItem("docpilot-user");
        localStorage.removeItem("prepz_user");
        sessionStorage.clear();
        currentUser = null;
        showLoginScreen();
    }

    function loginUser(user) {
        currentUser = user;
        localStorage.setItem("docpilot-user", JSON.stringify(user));
        if (userAvatar) {
            const avatarUrl = user.avatar_url || user.picture || `https://api.dicebear.com/7.x/bottts/svg?seed=${user.email || 'Om'}`;
            userAvatar.style.backgroundImage = `url('${avatarUrl}')`;
            userAvatar.innerHTML = "";
        }
        if (userName) userName.textContent = user.name || "Student User";
        if (userEmail) userEmail.textContent = user.email || "student@college.edu";

        if (navPinnedLibrary) navPinnedLibrary.style.display = "flex";
        if (landingPageView) {
            landingPageView.classList.add("hidden");
            landingPageView.style.display = "none";
        }
        if (chatbotAppView) {
            chatbotAppView.classList.remove("hidden");
            chatbotAppView.style.display = "flex";
        }

        // Fetch folders, threads, and user stats
        fetchThreads();
        fetchIndexedFiles();
        fetchUserStats();

        // Check if first-time user onboarding tour needs to be shown
        if (user && !user.has_seen_onboarding) {
            const showingOnboarding = checkAndShowOnboarding(user);
            if (showingOnboarding) return;
        }

        if (currentThreadId) {
            loadThreadHistory(currentThreadId);
        } else {
            showLandingState();
        }
    }

    window.loginUser = loginUser;

    function logoutUser() {
        currentUser = null;
        if (navPinnedLibrary) navPinnedLibrary.style.display = "none";
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

        if (navNewChat) navNewChat.classList.remove("active");
        if (navPinnedLibrary) navPinnedLibrary.classList.remove("active");
        if (navBrowseDocuments) navBrowseDocuments.classList.remove("active");
        if (navExamPredictor) navExamPredictor.classList.remove("active");
        if (navLeaderboard) navLeaderboard.classList.remove("active");
    }

    function updateHeaderTitle(titleText, icon = "✨") {
        const headerViewName = document.getElementById("header-view-name");
        const headerSparkle = document.querySelector(".header-title-sparkle");
        if (headerViewName) headerViewName.textContent = titleText;
        if (headerSparkle) headerSparkle.textContent = icon;
    }

    function showChatState() {
        resetViewModes();
        updateHeaderTitle("Chat", "💬");
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
        if (!currentUser) {
            alert("Please sign in to view your personal 'My Library'.");
            showLandingState();
            return;
        }

        resetViewModes();
        updateHeaderTitle("Personal Collection", "📚");
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
    }

    function showBrowseState() {
        resetViewModes();
        updateHeaderTitle("Shared Resources", "📁");
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
    }

    function showPredictorState() {
        if (!currentUser) {
            alert("Please sign in to access the AI Exam Question Paper Predictor.");
            showLandingState();
            return;
        }

        resetViewModes();
        updateHeaderTitle("Exam Predictor", "🎯");
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
        resetViewModes();
        updateHeaderTitle("Leaderboard", "🏆");
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
    }

    async function fetchLeaderboard() {
        const tbody = document.getElementById("leaderboard-tbody");
        if (!tbody) return;

        try {
            const res = await fetch("/api/leaderboard");
            const data = await res.json();
            tbody.innerHTML = "";

            const leaderboard = data.leaderboard || [];
            if (leaderboard.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" style="padding: 30px; text-align: center; color: #a1a1aa;">
                            🏆 No activity logged yet. Upload notes, ask AI questions, or download files to earn points!
                        </td>
                    </tr>
                `;
                return;
            }

            leaderboard.forEach((item, index) => {
                const rank = index + 1;
                let rankBadgeClass = "rank-badge";
                let rankIcon = `#${rank}`;

                if (rank === 1) { rankBadgeClass += " rank-1"; rankIcon = "🥇 #1"; }
                else if (rank === 2) { rankBadgeClass += " rank-2"; rankIcon = "🥈 #2"; }
                else if (rank === 3) { rankBadgeClass += " rank-3"; rankIcon = "🥉 #3"; }

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td style="text-align: center;"><span class="${rankBadgeClass}">${rankIcon}</span></td>
                    <td>
                        <div class="leaderboard-user-cell">
                            <div class="leaderboard-avatar" style="background-image: url('${item.avatar_url}');"></div>
                            <span style="font-weight: 600; color: #ffffff;">${item.name || 'Anonymous Student'}</span>
                        </div>
                    </td>
                    <td style="text-align: right; font-weight: 700; color: #eab308;">⭐ ${item.contribution_score} pts</td>
                    <td style="text-align: right; font-weight: 600; color: #f97316;">🔥 ${item.current_streak} Day${item.current_streak === 1 ? '' : 's'}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Error fetching leaderboard:", e);
        }
    }

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

                if (streakDisplay) streakDisplay.textContent = `${data.current_streak} Day${data.current_streak === 1 ? '' : 's'} Streak 🔥`;
                if (scoreDisplay) scoreDisplay.textContent = `${data.contribution_score} Points ⭐`;
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
        if (!currentUser || !currentUser.email) return false;
        const fileUserEmail = (typeof fileObj === 'object' && fileObj.user_email) ? fileObj.user_email.toLowerCase().trim() : "";
        const currentEmail = currentUser.email.toLowerCase().trim();

        if (currentEmail && fileUserEmail && currentEmail === fileUserEmail) return true;
        return false;
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
                <tr>
                    <td colspan="6" style="padding: 40px 20px; text-align: center; color: #6b7280; font-size: 13.5px;">
                        📂 No uploaded documents found for the selected Semester / Subject / Type filters.
                    </td>
                </tr>
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

            const tr = document.createElement("tr");
            tr.className = "browse-row";
            tr.innerHTML = `
                <td class="col-filename">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="browse-pdf-icon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        <a href="/view/${encodeURIComponent(filename)}" target="_blank" class="browse-file-title" title="${filename}">
                            ${filename}
                        </a>
                    </div>
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                        <span class="filetype-badge">${fileType}</span>
                        ${examType && examType !== "Other" ? `<span class="examtype-badge">${examType}</span>` : ''}
                    </div>
                </td>
                <td>
                    <div style="display: flex; flex-direction: column; gap: 3px;">
                        <span style="font-weight: 700; font-size: 13.5px; color: #60a5fa !important;">${subject}</span>
                        <span style="font-size: 12px; color: #f4f4f5 !important; font-weight: 500;">${semester}</span>
                    </div>
                </td>
                <td><span style="font-weight: 600; font-size: 13.5px; color: #ffffff !important;">${uploaderName}</span></td>
                <td><span style="font-size: 12.5px; color: #e4e4e7 !important; font-weight: 500;">${uploadedAt} (${sizeKb})</span></td>
                <td class="col-action">
                    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                        <a href="/view/${encodeURIComponent(filename)}" target="_blank" class="btn-open-browse-pdf" title="View or Download Document">
                            👁️ View Document
                        </a>
                        <a href="/download/${encodeURIComponent(filename)}?disposition=attachment" download="${filename}" class="btn-download-file" title="Download File from Storage">
                            ⬇️ Download
                        </a>
                        <button type="button" class="btn-chat-with-doc btn-browse-chat" data-filename="${filename}" title="Chat with Document" style="width: auto; padding: 7px 12px;">
                            💬 Chat
                        </button>
                        <button type="button" class="btn-pin-browse ${isPinned ? 'active-pinned' : ''}" data-filename="${filename}" title="${isPinned ? 'Unpin from Sidebar Pinned Folders' : 'Pin to Sidebar Pinned Folders'}">
                            ${isPinned ? '📌 Pinned' : '📌 Pin'}
                        </button>
                        <button type="button" class="btn-report-browse" data-filename="${filename}" title="Report file to moderation">
                            🚩 Report
                        </button>
                    </div>
                </td>
            `;

            const btnChat = tr.querySelector(".btn-browse-chat");
            if (btnChat) {
                btnChat.addEventListener("click", () => {
                    startNewChatWithDoc(filename);
                });
            }

            const btnPinBrowse = tr.querySelector(".btn-pin-browse");
            if (btnPinBrowse) {
                btnPinBrowse.addEventListener("click", () => {
                    toggleSidebarPinFile(filename);
                });
            }

            const btnReportBrowse = tr.querySelector(".btn-report-browse");
            if (btnReportBrowse) {
                btnReportBrowse.addEventListener("click", () => {
                    openReportModal(filename);
                });
            }

            tbody.appendChild(tr);
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
                <div class="chat-welcome-badge">⚡ Prepz AI Assistant</div>
                <h2 class="chat-welcome-title">Welcome back, <span class="user-highlight-name">${userName}</span>! 👋</h2>
                <p class="chat-welcome-subtitle">Ask questions, summarize uploaded study notes, or solve engineering tutorial problems.</p>
                
                <div class="welcome-suggestions-grid">
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Summarize key formulas, definitions, and PYQ exam questions from my uploaded notes.')">
                        <span class="suggest-icon">📝</span>
                        <span class="suggest-text">Exam Prep & Formulas Summary</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Help me solve step-by-step tutorial sheet assignments and explain underlying equations.')">
                        <span class="suggest-icon">🧮</span>
                        <span class="suggest-text">Assignment & Math Helper</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Explain core concepts in Operating Systems, DBMS, DSA, and Networks with clear examples.')">
                        <span class="suggest-icon">💡</span>
                        <span class="suggest-text">Engineering Concept Explainer</span>
                    </button>
                    <button type="button" class="welcome-suggest-btn" onclick="sendQuickPrompt('Create a 5-minute quick revision cheat sheet and key takeaways from my uploaded PDF documents.')">
                        <span class="suggest-icon">⚡</span>
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
        updateHeaderTitle("Fresh Chat", "💬");
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
            updateHeaderTitle("Fresh Chat", "💬");
        });
    }
    if (headerNewChatBtn) {
        headerNewChatBtn.addEventListener("click", (e) => {
            e.preventDefault();
            startNewChat();
            updateHeaderTitle("Fresh Chat", "💬");
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

        let html = mdText
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Horizontal Rules
        html = html.replace(/^---$/gim, '<hr>');

        // Bold & Italic
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Lists
        html = html.replace(/^\s*[\-\*]\s+(.*$)/gim, '<ul><li>$1</li></ul>');
        html = html.replace(/<\/ul>\s*<ul>/g, '');

        // Paragraphs & Line breaks
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');

        return `<p>${html}</p>`;
    }

    async function generatePredictedPaper() {
        if (!currentUser) {
            alert("Please sign in to generate AI predicted question papers.");
            return;
        }

        const sem = predictorSemesterSelect ? predictorSemesterSelect.value : "Semester 1";
        const sub = predictorSubjectSelect ? predictorSubjectSelect.value : "";
        const examType = predictorExamTypeSelect ? predictorExamTypeSelect.value : "Mid-Sem";

        if (!sub) {
            alert("Please select a subject.");
            return;
        }

        // Reset state
        if (predictorResultCard) predictorResultCard.classList.add("hidden");
        if (predictorWarningCard) predictorWarningCard.classList.add("hidden");
        if (predictorLoadingCard) predictorLoadingCard.classList.remove("hidden");

        try {
            const res = await fetch("/api/predict-paper", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ semester: sem, subject: sub, exam_type: examType })
            });

            const data = await res.json();
            if (predictorLoadingCard) predictorLoadingCard.classList.add("hidden");

            if (!res.ok || data.success === false) {
                if (predictorWarningCard) {
                    predictorWarningCard.classList.remove("hidden");
                    const msgEl = document.getElementById("predictor-warning-message");
                    if (msgEl) msgEl.textContent = data.message || `Not enough ${examType} PYQs uploaded yet for accurate prediction.`;
                }
                return;
            }

            // Render Result Card
            if (predictorResultCard) predictorResultCard.classList.remove("hidden");

            const badgePyq = document.getElementById("badge-pyq-count");
            if (badgePyq) badgePyq.textContent = `📊 Based on ${data.pyq_count} ${data.exam_type || examType} PYQs (${data.pyq_filenames ? data.pyq_filenames.join(', ') : ''})`;

            const badgeSub = document.getElementById("badge-predicted-subject");
            if (badgeSub) badgeSub.textContent = `${data.subject} (${data.semester} • ${data.exam_type || examType})`;

            if (predictedPaperBody) {
                const formattedHtml = formatPaperMarkdown(data.paper_markdown);
                window._rawPaperMarkdownHtml = formattedHtml;
                predictedPaperBody.innerHTML = formattedHtml;
            }
        } catch (err) {
            if (predictorLoadingCard) predictorLoadingCard.classList.add("hidden");
            alert(`Error generating predicted paper: ${err.message || err}`);
        }
    }

    function downloadPredictedPDF() {
        const paperElement = document.getElementById("predicted-paper-document");
        if (!paperElement) return;

        const sub = predictorSubjectSelect ? predictorSubjectSelect.value : "Exam";
        const sem = predictorSemesterSelect ? predictorSemesterSelect.value : "Sem";
        const filename = `Prepz_Predicted_Paper_${sub.replace(/\s+/g, '_')}_${sem.replace(/\s+/g, '_')}.pdf`;

        if (window.html2pdf) {
            const opt = {
                margin:       12,
                filename:     filename,
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };
            html2pdf().set(opt).from(paperElement).save();
        } else {
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
            openUploadModal();
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
            assistantBubble.innerHTML = `<span style="color:#ef4444;">Error connecting to Prepz.</span>`;
            console.error(err);
        }
    });

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

    function openUploadModal(targetScope = "browse") {
        currentUploadTarget = targetScope;
        if (uploadModal) uploadModal.classList.remove("hidden");
    }

    function closeUploadModal() {
        if (uploadModal) {
            uploadModal.classList.add("hidden");
            if (formUploadDocument) formUploadDocument.reset();
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
                    fileChosenLabel.textContent = `⚠️ Exceeds 20MB limit (${fileSizeMb} MB)`;
                    fileChosenLabel.style.color = "#f87171";
                    fileChosenLabel.style.fontWeight = "600";
                    showModalError(`File size exceeds the 20MB maximum limit (${fileSizeMb} MB). Please choose a smaller file.`);
                    uploadFileInput.value = ""; // Reset oversized selection
                    return;
                }

                fileChosenLabel.textContent = `📄 ${file.name} (${fileSizeMb} MB)`;
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

            // Check for duplicate document (same filename + same subject + same semester)
            const isConfirmedOverwrite = formUploadDocument.dataset.confirmedOverwrite === "true";

            if (!isConfirmedOverwrite) {
                const existingFile = allCachedFiles.find(f => {
                    const fn = (typeof f === 'string' ? f : f.filename || "").toLowerCase();
                    const sub = typeof f === 'object' ? f.subject : "";
                    const sem = typeof f === 'object' ? f.semester : "";
                    return fn === file.name.toLowerCase() && sub === subject && sem === semester;
                });

                if (existingFile) {
                    if (modalUploadStatus) {
                        modalUploadStatus.classList.remove("hidden");
                        modalUploadStatus.style.backgroundColor = "transparent";
                        modalUploadStatus.style.padding = "0";
                        modalUploadStatus.innerHTML = `
                            <div class="duplicate-warning-banner">
                                <div class="warning-title">⚠️ Similar Document Already Exists</div>
                                <p class="warning-msg">A document named <strong>"${file.name}"</strong> already exists under <strong>${subject}</strong> (<strong>${semester}</strong>). Do you still want to upload and overwrite it?</p>
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

            const isPrivateVal = currentUploadTarget === "library" ? "1" : "0";

            const formData = new FormData();
            formData.append("file", file);
            formData.append("subject", subject);
            formData.append("semester", semester);
            formData.append("file_type", fileType);
            formData.append("exam_type", examType);
            formData.append("is_private", isPrivateVal);
            formData.append("confirm_overwrite", "true");

            if (currentUser) {
                formData.append("user_email", currentUser.email || "anonymous@college.edu");
                formData.append("user_name", currentUser.name || "Anonymous Student");
            }

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
                        modalUploadStatus.innerHTML = `✅ Uploaded & Indexed successfully!`;
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
                                <div class="warning-title">⚠️ Similar Document Already Exists</div>
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
            const res = await fetch("/files");
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
                                ✕
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
                            window.open(`/view/${encodeURIComponent(filename)}`, "_blank");
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
                        if (confirm(`Are you sure you want to delete "${filename}"?\n\nThis will permanently remove the file from both storage and the database.`)) {
                            deleteUploadedFile(filename);
                        }
                    });
                }

                mainFilesGrid.appendChild(card);
            });
        }

        // --------------------------------------------------------
        // 2. Render "My Library" (PERSONAL TO CURRENT LOGGED-IN USER ONLY)
        // --------------------------------------------------------
        if (libraryGrid) {
            if (!currentUser) {
                libraryGrid.innerHTML = `
                    <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
                        🔒 Please sign in to access your personal "My Library" and manage your uploaded documents.
                    </div>
                `;
                return;
            }

            const myUploadedFiles = allCachedFiles.filter(fileObj => {
                const isPrivate = typeof fileObj === 'object' && (fileObj.is_private === 1 || fileObj.is_private === "1" || fileObj.is_private === true);
                return isPrivate;
            });

            if (myUploadedFiles.length === 0) {
                libraryGrid.innerHTML = `
                    <div class="empty-docs-placeholder" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
                        📂 You haven't uploaded any documents yet. Use the "+ Upload Document" button above to add your study materials to your personal library!
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
                card.className = "library-doc-card";
                card.innerHTML = `
                    <div class="lib-card-top">
                        <div class="lib-card-badge-group">
                            <span class="filetype-badge">${fileType}</span>
                            <span class="semester-badge">${semester}</span>
                            ${isPrivate ? '<span style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">🔒 Private</span>' : '<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600;">🌐 Shared</span>'}
                        </div>
                    </div>
                    
                    <div class="lib-card-icon-row">
                        <div class="lib-doc-icon">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        <div class="lib-doc-title-wrapper">
                            <h4 class="lib-doc-title" title="${filename}">${filename}</h4>
                            <span class="subject-badge" style="max-width: 100%;">${subject}</span>
                        </div>
                    </div>

                    <div class="lib-card-meta-list">
                        <div class="meta-item">
                            <span class="meta-label">Uploaded By:</span>
                            <span class="meta-value">${uploaderName} (You)</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Date & Size:</span>
                            <span class="meta-value">${uploadedAt} (${sizeKb})</span>
                        </div>
                    </div>

                    <div class="lib-card-actions" style="display: flex; gap: 6px; margin-top: 4px;">
                        <a href="/view/${encodeURIComponent(filename)}" target="_blank" class="btn-open-pdf" title="View or Download Document" style="flex: 1; text-align: center; text-decoration: none;">
                            👁️ View Document
                        </a>
                        <button type="button" class="btn-chat-with-doc" data-filename="${filename}" style="flex: 1;">
                            💬 Chat
                        </button>
                        <button type="button" class="btn-pin-browse ${isPinnedInSidebar ? 'active-pinned' : ''}" data-filename="${filename}" title="${isPinnedInSidebar ? 'Unpin from Sidebar Pinned Folders' : 'Pin to Sidebar Pinned Folders'}" style="padding: 7px 10px;">
                            ${isPinnedInSidebar ? '📌 Pinned' : '📌 Pin'}
                        </button>
                        <button type="button" class="btn-delete-my-library" data-filename="${filename}" title="Delete File from Storage & DB">
                            🗑️ Delete
                        </button>
                    </div>
                `;

                const titleElem = card.querySelector(".lib-doc-title");
                if (titleElem) {
                    titleElem.style.cursor = "pointer";
                    titleElem.addEventListener("click", () => {
                        window.open(`/view/${encodeURIComponent(filename)}`, "_blank");
                    });
                }

                const iconElem = card.querySelector(".lib-doc-icon");
                if (iconElem) {
                    iconElem.style.cursor = "pointer";
                    iconElem.addEventListener("click", () => {
                        window.open(`/view/${encodeURIComponent(filename)}`, "_blank");
                    });
                }

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

                const btnDelete = card.querySelector(".btn-delete-my-library");
                if (btnDelete) {
                    btnDelete.addEventListener("click", (e) => {
                        e.stopPropagation();
                        if (confirm(`Are you sure you want to delete "${filename}"?\n\nThis will permanently remove the file from both storage and the database.`)) {
                            deleteUploadedFile(filename);
                        }
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

        if (reportModal) reportModal.classList.remove("hidden");
    }

    function closeReportModal() {
        const reportModal = document.getElementById("report-modal");
        if (reportModal) reportModal.classList.add("hidden");
    }

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
                            modalReportStatus.textContent = `✅ ${data.message || "Report submitted successfully."}`;
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

    async function deleteUploadedFile(filename) {
        try {
            const userEmail = currentUser ? (currentUser.email || "") : "";
            const userName = currentUser ? (currentUser.name || "") : "";
            const queryParams = new URLSearchParams({ user_email: userEmail, user_name: userName });
            const res = await fetch(`/files/${encodeURIComponent(filename)}?${queryParams.toString()}`, {
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
        const sidebarBackdrop = document.getElementById("sidebar-backdrop");

        function setSidebarState(collapsed) {
            if (!appSidebar) return;
            if (collapsed) {
                appSidebar.classList.add("sidebar-collapsed");
                if (btnExpandSidebar) btnExpandSidebar.classList.remove("hidden");
                if (sidebarBackdrop) {
                    sidebarBackdrop.classList.add("hidden");
                    sidebarBackdrop.style.display = "none";
                }
                localStorage.setItem("sidebar-collapsed", "true");
            } else {
                appSidebar.classList.remove("sidebar-collapsed");
                if (btnExpandSidebar) btnExpandSidebar.classList.add("hidden");
                // ONLY show backdrop overlay on mobile screens (<= 768px)
                if (window.innerWidth <= 768 && sidebarBackdrop) {
                    sidebarBackdrop.classList.remove("hidden");
                    sidebarBackdrop.style.display = "block";
                } else if (sidebarBackdrop) {
                    sidebarBackdrop.classList.add("hidden");
                    sidebarBackdrop.style.display = "none";
                }
                localStorage.setItem("sidebar-collapsed", "false");
            }
        }

        if (btnCollapseSidebar) {
            btnCollapseSidebar.addEventListener("click", () => setSidebarState(true));
        }
        if (btnExpandSidebar) {
            btnExpandSidebar.addEventListener("click", () => setSidebarState(false));
        }
        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener("click", () => setSidebarState(true));
        }

        // DEFAULT TO OFF / COLLAPSED unless user explicitly opened it
        const savedState = localStorage.getItem("sidebar-collapsed");
        const isCollapsed = savedState !== "false";
        setSidebarState(isCollapsed);

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
    // First-Time User Onboarding Manager
    // ----------------------------------------------------
    let currentOnboardingStep = 1;
    const onboardingSteps = [
        {
            title: "Browse Documents",
            desc: "Find notes, PYQs, and assignments filtered by subject and semester. Chat directly with any document to ask questions!",
            icon: `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`
        },
        {
            title: "My Library",
            desc: "Your personal workspace where your own uploaded notes and study materials live. Kept safe and private to you.",
            icon: `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`
        },
        {
            title: "AI Exam Predictor",
            desc: "Generate high-yield predicted question papers based on past year questions, pattern frequency, and topic weightage analysis.",
            icon: `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`
        },
        {
            title: "Leaderboard & Streaks",
            desc: "Earn points for uploading notes and active studying! Build up your daily Study Streak and climb the college leaderboard.",
            icon: `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/></svg>`
        }
    ];

    function renderOnboardingStep(stepNum) {
        currentOnboardingStep = stepNum;
        const content = document.getElementById("onboarding-step-content");
        const indicator = document.getElementById("onboarding-step-indicator");
        const btnNext = document.getElementById("btn-next-onboarding");
        const dots = document.querySelectorAll(".onboarding-dot");

        if (stepNum < 1) currentOnboardingStep = 1;
        if (stepNum > 4) currentOnboardingStep = 4;

        const data = onboardingSteps[currentOnboardingStep - 1];

        if (content) {
            content.innerHTML = `
                <div class="onboarding-icon-box">
                    ${data.icon}
                </div>
                <h2 class="onboarding-step-title">${data.title}</h2>
                <p class="onboarding-step-desc">${data.desc}</p>
            `;
        }

        if (indicator) indicator.textContent = `Step ${currentOnboardingStep} of 4`;

        dots.forEach((dot, idx) => {
            if (idx + 1 === currentOnboardingStep) {
                dot.classList.add("active");
            } else {
                dot.classList.remove("active");
            }
        });

        if (btnNext) {
            if (currentOnboardingStep === 4) {
                btnNext.textContent = "Get Started 🎉";
                btnNext.className = "btn-onboarding-primary get-started-btn";
            } else {
                btnNext.textContent = "Next →";
                btnNext.className = "btn-onboarding-primary";
            }
        }
    }

    async function completeUserOnboarding() {
        const modal = document.getElementById("onboarding-modal");
        if (modal) {
            modal.classList.add("hidden");
            modal.style.display = "none";
        }

        if (currentUser) {
            currentUser.has_seen_onboarding = true;
            localStorage.setItem("docpilot-user", JSON.stringify(currentUser));
            try {
                await fetch("/api/user/complete-onboarding", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: currentUser.email })
                });
            } catch(e) {}
        }
        showLandingState();
    }

    function checkAndShowOnboarding(user) {
        if (!user) return false;
        if (!user.has_seen_onboarding) {
            const modal = document.getElementById("onboarding-modal");
            if (modal) {
                renderOnboardingStep(1);
                modal.classList.remove("hidden");
                modal.style.display = "flex";
                return true;
            }
        }
        return false;
    }

    function initOnboardingListeners() {
        const btnNext = document.getElementById("btn-next-onboarding");
        const btnSkip = document.getElementById("btn-skip-onboarding");
        const dots = document.querySelectorAll(".onboarding-dot");

        if (btnNext) {
            btnNext.addEventListener("click", () => {
                if (currentOnboardingStep < 4) {
                    renderOnboardingStep(currentOnboardingStep + 1);
                } else {
                    completeUserOnboarding();
                }
            });
        }

        if (btnSkip) {
            btnSkip.addEventListener("click", completeUserOnboarding);
        }

        dots.forEach(dot => {
                    dot.addEventListener("click", () => {
                const step = parseInt(dot.dataset.step, 10);
                if (step >= 1 && step <= 4) {
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
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeDocPilotApp);
} else {
    initializeDocPilotApp();
}
