
const $ = (id) => document.getElementById(id);

const state = {
    mode: "login",
    token: null,
    username: null,
    room: "general",
    socket: null,
    reconnectTimer: null,
    typingTimer: null,
    reconnectAttempts: 0,
    manuallyLoggedOut: false,
    activePrivateUser: null,
};

const authPanel = $("auth-panel");
const chatPanel = $("chat-panel");
const authForm = $("auth-form");
const authStatus = $("auth-status");
const authSubmit = $("auth-submit");
const messages = $("messages");
const messageForm = $("message-form");
const messageInput = $("message-input");
const connectionStatus = $("connection-status");
const onlineUsers = $("online-users");
const typingStatus = $("typing-status");
const toast = $("toast");
const privateRecipient = $("private-recipient");

let toastTimer;
let typingSentAt = 0;

function showToast(text) {
    toast.textContent = text;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 2800);
}

function setStatus(text, error = false) {
    authStatus.textContent = text;
    authStatus.style.color = error ? "#ff7185" : "#9eacc1";
}

function setConnection(text, connected = false) {
    connectionStatus.textContent = text;
    connectionStatus.classList.toggle("connected", connected);
}

function setMode(mode) {
    state.mode = mode;
    $("login-tab").classList.toggle("active", mode === "login");
    $("register-tab").classList.toggle("active", mode === "register");
    authSubmit.textContent = mode === "login" ? "Login" : "Create account";
    $("password").autocomplete =
        mode === "login" ? "current-password" : "new-password";
    setStatus("");
}

$("login-tab").addEventListener("click", () => setMode("login"));
$("register-tab").addEventListener("click", () => setMode("register"));

async function apiRequest(path, body) {
    const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(result.detail || "Request failed.");
    }

    return result;
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = $("username").value.trim();
    const password = $("password").value;

    if (!/^[A-Za-z0-9_]{3,24}$/.test(username)) {
        setStatus("Use 3–24 letters, numbers, or underscores.", true);
        return;
    }

    if (password.length < 8 || password.length > 128) {
        setStatus("Password must be between 8 and 128 characters.", true);
        return;
    }

    authSubmit.disabled = true;
    setStatus(state.mode === "login" ? "Logging in…" : "Creating account…");

    try {
        if (state.mode === "register") {
            const result = await apiRequest("/api/register", {
                username,
                password,
            });

            setMode("login");
            $("username").value = username;
            $("password").value = "";
            setStatus(result.message);
        } else {
            const result = await apiRequest("/api/login", {
                username,
                password,
            });

            state.token = result.token;
            state.username = result.username;
            state.manuallyLoggedOut = false;
            state.activePrivateUser = null;

            authPanel.classList.add("hidden");
            chatPanel.classList.remove("hidden");

            $("my-name").textContent = state.username;
            $("my-avatar").textContent =
                state.username.charAt(0).toUpperCase();
            $("room-select").value = state.room;

            connectSocket();
        }
    } catch (error) {
        setStatus(error.message || "Unable to sign in.", true);
    } finally {
        authSubmit.disabled = false;
    }
});

function scrollToLatest() {
    messages.scrollTop = messages.scrollHeight;
}

function formatTime(value) {
    if (!value) return "";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";

    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function addSystemMessage(text) {
    const item = document.createElement("div");
    item.className = "system-message";
    item.textContent = text;
    messages.appendChild(item);
    scrollToLatest();
}

function addMessage(data, isPrivate = false) {
    const item = document.createElement("article");
    item.className = "message";

    const sender = data.username || data.from || "User";

    if (sender === state.username) {
        item.classList.add("mine");
    }

    const meta = document.createElement("div");
    meta.className = "message-meta";

    const name = document.createElement("strong");
    name.textContent = sender;

    const time = document.createElement("span");
    time.textContent = formatTime(data.timestamp);

    meta.append(name, time);

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = data.message || "";

    item.append(meta, bubble);

    if (isPrivate) {
        const tag = document.createElement("div");
        tag.className = "private-message-tag";
        tag.textContent = "🔒 Private message";
        item.appendChild(tag);
    }

    messages.appendChild(item);
    scrollToLatest();

    if (sender !== state.username && document.hidden) {
        showNotification(
            isPrivate ? `Private message from ${sender}` : `${sender} sent a message`,
            data.message || ""
        );
    }
}

function showNotification(title, body) {
    if (!("Notification" in window) || Notification.permission !== "granted") {
        return;
    }

    try {
        new Notification(title, {
            body: body.slice(0, 120),
            tag: "connect-chat-message",
        });
    } catch {
        // Notifications may not be supported.
    }
}

function renderOnlineUsers(users) {
    onlineUsers.replaceChildren();

    [...new Set(users)].forEach((username) => {
        const item = document.createElement("li");
        item.textContent = username;
        onlineUsers.appendChild(item);
    });

    updatePrivateRecipients(users);
}

function updatePrivateRecipients(users) {
    if (!privateRecipient) return;

    const previous = state.activePrivateUser;
    privateRecipient.replaceChildren();

    const groupOption = document.createElement("option");
    groupOption.value = "";
    groupOption.textContent = "Group chat";
    privateRecipient.appendChild(groupOption);

    [...new Set(users)]
        .filter((username) => username !== state.username)
        .sort((a, b) => a.localeCompare(b))
        .forEach((username) => {
            const option = document.createElement("option");
            option.value = username;
            option.textContent = username;
            privateRecipient.appendChild(option);
        });

    if (
        previous &&
        [...privateRecipient.options].some((option) => option.value === previous)
    ) {
        privateRecipient.value = previous;
    }
}

function sendSocket(data) {
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
        state.socket.send(JSON.stringify(data));
        return true;
    }

    return false;
}

function connectSocket() {
    if (!state.token || state.manuallyLoggedOut) return;

    clearTimeout(state.reconnectTimer);
    setConnection("Connecting…");

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const url =
        `${protocol}//${location.host}/ws/${encodeURIComponent(state.room)}` +
        `?token=${encodeURIComponent(state.token)}`;

    const socket = new WebSocket(url);
    state.socket = socket;

    socket.addEventListener("open", () => {
        if (state.socket !== socket) return;

        state.reconnectAttempts = 0;
        setConnection("Connected", true);
        $("room-title").textContent = `# ${state.room}`;
        $("room-description").textContent =
            "You're connected to the conversation.";
        messageInput.disabled = false;

        showToast(`Connected to #${state.room}`);
    });

    socket.addEventListener("message", (event) => {
        let data;

        try {
            data = JSON.parse(event.data);
        } catch {
            return;
        }

        switch (data.type) {
            case "history":
                state.activePrivateUser = null;
                if (privateRecipient) privateRecipient.value = "";
                messages.replaceChildren();
                (data.messages || []).forEach((message) => addMessage(message));

                if (!(data.messages || []).length) {
                    showEmptyState("No messages yet. Start the conversation!");
                }
                break;

            case "message":
                if (!state.activePrivateUser) {
                    messages.querySelector(".empty-state")?.remove();
                    addMessage(data);
                }
                break;

            case "private_history":
                if (data.with !== state.activePrivateUser) break;

                messages.replaceChildren();
                (data.messages || []).forEach((message) => {
                    addMessage({
                        username: message.from,
                        from: message.from,
                        to: message.to,
                        message: message.message,
                        timestamp: message.timestamp,
                    }, true);
                });

                if (!(data.messages || []).length) {
                    showEmptyState("No private messages yet. Say hello!");
                }
                break;

            case "private":
                if (
                    data.from === state.username &&
                    data.to === state.activePrivateUser
                ) {
                    messages.querySelector(".empty-state")?.remove();
                    addMessage(data, true);
                } else if (
                    data.to === state.username &&
                    data.from === state.activePrivateUser
                ) {
                    messages.querySelector(".empty-state")?.remove();
                    addMessage(data, true);
                } else if (
                    data.to === state.username &&
                    document.hidden
                ) {
                    showNotification(`Private message from ${data.from}`, data.message || "");
                }
                break;

            case "system":
                if (!state.activePrivateUser) {
                    addSystemMessage(data.message || "");
                }
                break;

            case "presence":
                renderOnlineUsers(data.users || []);
                break;

            case "typing":
                if (
                    !state.activePrivateUser &&
                    data.username !== state.username
                ) {
                    typingStatus.textContent = `${data.username} is typing…`;
                    clearTimeout(state.typingTimer);
                    state.typingTimer = setTimeout(() => {
                        typingStatus.textContent = "";
                    }, 1800);
                }
                break;

            case "error":
                showToast(data.message || "An error occurred.");
                break;
        }
    });

    socket.addEventListener("error", () => {
        if (state.socket === socket) setConnection("Connection issue");
    });

    socket.addEventListener("close", () => {
        if (state.socket !== socket) return;

        state.socket = null;
        messageInput.disabled = true;
        setConnection("Disconnected");

        if (!state.manuallyLoggedOut && state.token) {
            const delay = Math.min(
                1000 * (2 ** state.reconnectAttempts),
                10000
            );
            state.reconnectAttempts += 1;
            state.reconnectTimer = setTimeout(connectSocket, delay);
        }
    });
}

function showEmptyState(text) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = text;
    messages.appendChild(empty);
}

if (privateRecipient) {
    privateRecipient.addEventListener("change", () => {
        const recipient = privateRecipient.value;
        state.activePrivateUser = recipient || null;
        messages.replaceChildren();
        typingStatus.textContent = "";

        if (recipient) {
            $("room-title").textContent = `Private chat with ${recipient}`;
            $("room-description").textContent =
                "Only you and the selected recipient should receive these messages.";

            if (!sendSocket({
                action: "private_history",
                to: recipient,
            })) {
                showToast("Not connected. Please wait.");
            }
        } else {
            $("room-title").textContent = `# ${state.room}`;
            $("room-description").textContent =
                "You're connected to the conversation.";

            if (!sendSocket({ action: "load_history" })) {
                showToast("Not connected. Please wait.");
            }
        }
    });
}

$("room-select").addEventListener("change", (event) => {
    const nextRoom = event.target.value;
    if (nextRoom === state.room) return;

    state.room = nextRoom;
    state.activePrivateUser = null;

    if (privateRecipient) privateRecipient.value = "";

    messages.replaceChildren();
    typingStatus.textContent = "";

    if (state.socket) {
        state.socket.close();
    } else {
        connectSocket();
    }
});

messageForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    const recipient = state.activePrivateUser;
    const sent = recipient
        ? sendSocket({
            action: "private",
            to: recipient,
            message,
        })
        : sendSocket({
            action: "message",
            message,
        });

    if (sent) {
        messageInput.value = "";
        typingStatus.textContent = "";
    } else {
        showToast("Not connected. Please wait for reconnection.");
    }

    messageInput.focus();
});

messageInput.addEventListener("input", () => {
    const now = Date.now();

    if (
        !state.activePrivateUser &&
        messageInput.value.trim() &&
        now - typingSentAt > 1200
    ) {
        sendSocket({ action: "typing" });
        typingSentAt = now;
    }
});

$("emoji-btn").addEventListener("click", () => {
    const emoji = " 😊";
    const start = messageInput.selectionStart;
    const end = messageInput.selectionEnd;
    const value = messageInput.value;

    messageInput.value = value.slice(0, start) + emoji + value.slice(end);

    messageInput.focus();
    const position = start + emoji.length;
    messageInput.setSelectionRange(position, position);
});

$("logout-btn").addEventListener("click", logout);

function logout() {
    state.manuallyLoggedOut = true;
    clearTimeout(state.reconnectTimer);
    clearTimeout(state.typingTimer);

    if (state.socket) {
        const socket = state.socket;
        state.socket = null;
        socket.close();
    }

    state.token = null;
    state.username = null;
    state.room = "general";
    state.activePrivateUser = null;
    state.reconnectAttempts = 0;

    chatPanel.classList.add("hidden");
    authPanel.classList.remove("hidden");

    messages.replaceChildren();
    onlineUsers.replaceChildren();
    typingStatus.textContent = "";

    if (privateRecipient) privateRecipient.value = "";

    messageInput.disabled = false;
    $("room-select").value = "general";
    authForm.reset();

    setStatus("");
    setConnection("Disconnected");
    showToast("You have logged out.");
}

if ("Notification" in window && Notification.permission === "default") {
    document.addEventListener("click", function requestNotification() {
        Notification.requestPermission().catch(() => {});
    }, { once: true });
}
