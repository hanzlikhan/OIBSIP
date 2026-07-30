/**
 * Nova Voice Assistant - Dashboard Controller (WebSocket client & UI effects)
 */

let ws = null;
let reconnectInterval = 3000;
let remindersSyncTimer = null;
let activeTimers = {}; // Local timer intervals dictionary
let handsFreeRecognition = null;
let isHandsFreeActive = false;
let _handsFreePaused = false;

// Waveform visualizer context
const canvas = document.getElementById("waveform-canvas");
const ctx = canvas.getContext("2d");
let animationFrameId = null;
let assistantState = "idle"; // idle, listening, processing, speaking
let wavePhase = 0;

// DOM Hooks
const micOrb = document.getElementById("assistant-mic-orb");
const micIcon = document.getElementById("mic-icon");
const connectionIndicator = document.getElementById("connection-indicator");
const connectionText = document.getElementById("connection-text");
const stateText = document.getElementById("assistant-state-text");
const promptText = document.getElementById("assistant-prompt-text");
const chatContainer = document.getElementById("chat-messages-container");
const textForm = document.getElementById("text-input-form");
const textInput = document.getElementById("query-text-input");
const btnClearChat = document.getElementById("btn-clear-chat");
const customCmdForm = document.getElementById("custom-command-form");
const customCmdList = document.getElementById("custom-commands-list");
const settingsForm = document.getElementById("system-settings-form");
const remindersList = document.getElementById("reminders-list");
const alarmModal = document.getElementById("alarm-modal");
const alarmMessage = document.getElementById("alarm-message-text");
const btnDismissAlarm = document.getElementById("btn-dismiss-alarm");
const btnToggleWeatherKey = document.getElementById("btn-toggle-weather-key");
const weatherKeyInput = document.getElementById("settings-weather-key");

// ==========================================================================
// 1. WebSocket Connectivity
// ==========================================================================
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("WebSocket connected.");
        connectionIndicator.className = "status-dot connected";
        connectionText.textContent = "Connected";
        showToast("Connected to Voice Assistant server");
        
        // Start polling for active reminders sync
        if (!remindersSyncTimer) {
            remindersSyncTimer = setInterval(() => {
                sendWsMessage("get_reminders", {});
            }, 5000);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket closed. Attempting reconnect...");
        connectionIndicator.className = "status-dot disconnected";
        connectionText.textContent = "Disconnected";
        
        if (remindersSyncTimer) {
            clearInterval(remindersSyncTimer);
            remindersSyncTimer = null;
        }
        
        // Clean up visual state
        setAssistantState("idle");
        
        setTimeout(connectWebSocket, reconnectInterval);
    };

    ws.onerror = (error) => {
        console.error("WebSocket error: ", error);
    };

    ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        const eventType = payload.event;
        const data = payload.data;

        switch (eventType) {
            case "status_change":
                setAssistantState(data.status, data.text);
                if (data.status === "processing") clearActivityFeed();
                break;
            case "assistant_response":
                appendAssistantMessage(data);
                break;
            case "settings_data":
                renderSettings(data);
                break;
            case "reminder_triggered":
                triggerAlarmAlert(data.message);
                break;
            case "notification":
                showToast(data.message);
                break;
            case "error":
                showToast(data.message, true);
                appendSystemErrorMessage(data.message);
                break;
            case "activity_feed":
                appendActivityStep(data.type, data.message);
                break;
            case "session_cleared":
                clearActivityFeed();
                showToast("Session memory cleared. Starting fresh conversation.");
                break;
            case "toggle_hud":
                toggleSpotlightHUD();
                break;
            default:
                console.log("Unhandled event: ", eventType, data);
        }
    };
}

function sendWsMessage(event, data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(jsonPayload(event, data));
    } else {
        showToast("Cannot communicate. WebSocket is disconnected.", true);
    }
}

function jsonPayload(event, data) {
    return JSON.stringify({ event, data });
}

// ==========================================================================
// 2. UI State Controller
// ==========================================================================
function setAssistantState(state, text = "") {
    assistantState = state;
    
    // Reset classes
    micOrb.className = "mic-orb";
    micIcon.className = "fa-solid mic-symbol";
    
    // Pause continuous recognition if speaking or processing
    if (isHandsFreeActive && handsFreeRecognition) {
        if (state === "speaking" || state === "processing") {
            if (!_handsFreePaused) {
                console.log("[Hands-Free] Pausing listener during speaking/processing");
                _handsFreePaused = true;
                try {
                    handsFreeRecognition.abort();
                } catch (err) {}
            }
        } else if (state === "idle" && _handsFreePaused) {
            console.log("[Hands-Free] Resuming listener");
            _handsFreePaused = false;
            try {
                handsFreeRecognition.start();
            } catch (err) {}
        }
    }
    
    if (state === "listening") {
        micOrb.classList.add("listening");
        micIcon.classList.add("fa-microphone-lines");
        stateText.textContent = "Listening";
        stateText.style.color = "var(--color-cyan)";
        promptText.textContent = "I'm listening to your voice...";
        promptText.style.color = "var(--color-cyan)";
    } 
    else if (state === "processing") {
        micOrb.classList.add("processing");
        micIcon.classList.add("fa-arrows-spin");
        stateText.textContent = "Processing";
        stateText.style.color = "var(--color-amber)";
        promptText.textContent = text || "Thinking...";
        promptText.style.color = "var(--color-amber)";
    } 
    else if (state === "speaking") {
        micOrb.classList.add("speaking");
        micIcon.classList.add("fa-volume-high");
        stateText.textContent = "Speaking";
        stateText.style.color = "var(--color-violet)";
        promptText.textContent = text || "Speaking response...";
        promptText.style.color = "var(--color-violet)";
    } 
    else {
        // IDLE fallback
        micOrb.classList.add("idle-breath");
        micIcon.classList.add("fa-microphone");
        stateText.textContent = "Idle";
        stateText.style.color = "var(--text-muted)";
        promptText.textContent = "Click the orb or press Spacebar to start speaking";
        promptText.style.color = "var(--text-dark)";
    }
}

// ==========================================================================
// 3. Activity Log & Chat Feed Rendering
// ==========================================================================
function appendAssistantMessage(data) {
    // 1. Add user spoken bubble
    appendChatBubble(data.query, "user", {
        intent: data.intent,
        confidence: data.confidence
    });
    
    // 2. Add assistant response bubble
    let responseHtml = `<p class="bubble-text">${data.speech}</p>`;
    
    // Add custom layout block depending on action output details
    if (data.ui_data && Object.keys(data.ui_data).length > 0) {
        const ui = data.ui_data;
        
        if (data.intent === "weather" && ui.status !== "error") {
            responseHtml += `
                <div class="custom-card-ui weather-card-ui">
                    <div class="ui-temp">${ui.temp}°C</div>
                    <div class="ui-details">
                        <span class="ui-loc"><i class="fa-solid fa-location-dot"></i> ${ui.location}</span>
                        <span class="ui-cond">${ui.condition}</span>
                        <span class="ui-humidity"><i class="fa-solid fa-droplet"></i> Humidity: ${ui.humidity}%</span>
                    </div>
                </div>
            `;
        }
        else if (data.intent === "search" && ui.opened_url) {
            responseHtml += `
                <div class="custom-card-ui action-card-ui">
                    <span><i class="fa-solid fa-globe"></i> Query: <strong>${ui.query}</strong></span>
                    <a href="${ui.opened_url}" target="_blank" class="ui-btn-link">Open Search <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>
            `;
        }
        else if (data.intent === "email" && ui.status === "simulated") {
            responseHtml += `
                <div class="custom-card-ui action-card-ui">
                    <span><i class="fa-solid fa-envelope-open-text"></i> Email Saved to Local Outbox:</span>
                    <small style="word-break: break-all; color: var(--text-muted); display: block; margin-top: 4px;">File: ${ui.file_path.split('\\').pop()}</small>
                </div>
            `;
        }
        else if (data.intent === "reminder" && ui.reminder_id) {
            responseHtml += `
                <div class="custom-card-ui action-card-ui">
                    <span><i class="fa-solid fa-bell"></i> Timer set for: <strong>${ui.message}</strong></span>
                </div>
            `;
        }
    }

    appendChatBubble(responseHtml, "assistant");
}

// ==========================================================================
// Activity Feed — Live thought process display
// ==========================================================================
function appendActivityStep(type, message) {
    const feed = document.getElementById("activity-feed");
    const spotlightFeed = document.getElementById("spotlight-activity-feed");
    
    // Step creation
    const step = document.createElement("div");
    step.className = `activity-step activity-${type}`;
    
    const typeIcons = {
        thinking: "fa-brain",
        tool_call: "fa-gear",
        tool_result: "fa-circle-check",
        response: "fa-message",
        response_ready: "fa-message"
    };
    const icon = typeIcons[type] || "fa-circle";
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    step.innerHTML = `
        <i class="fa-solid ${icon} activity-icon"></i>
        <span class="activity-text">${escapeHtml(message)}</span>
        <span class="activity-time">${timeStr}</span>
    `;

    // 1. Update main Dashboard tab feed
    if (feed) {
        const idle = feed.querySelector(".activity-idle");
        if (idle) idle.remove();
        
        const agentTab = document.getElementById("tab-content-activity");
        if (agentTab && !agentTab.classList.contains("active-tab") && document.getElementById("spotlight-hud").classList.contains("hidden")) {
            switchTab("activity");
        }
        
        feed.appendChild(step.cloneNode(true));
        feed.scrollTop = feed.scrollHeight;
    }

    // 2. Update Spotlight HUD feed if visible
    if (spotlightFeed) {
        const pl = spotlightFeed.querySelector(".spotlight-placeholder");
        if (pl) pl.remove();
        
        spotlightFeed.appendChild(step);
        spotlightFeed.scrollTop = spotlightFeed.scrollHeight;
    }
}

function clearActivityFeed() {
    const feed = document.getElementById("activity-feed");
    const spotlightFeed = document.getElementById("spotlight-activity-feed");
    
    if (feed) {
        feed.innerHTML = `
            <div class="activity-idle">
                <i class="fa-solid fa-satellite-dish"></i>
                <p>Agent is ready. Awaiting your command.</p>
            </div>
        `;
    }
    
    if (spotlightFeed) {
        spotlightFeed.innerHTML = `
            <div class="spotlight-placeholder">
                <i class="fa-solid fa-satellite"></i>
                <p>Nova is listening. Ask anything or type commands.</p>
            </div>
        `;
    }
}

window.clearSession = function() {
    sendWsMessage("clear_session", {});
};

function appendChatBubble(content, sender, metadata = null) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender}-bubble`;
    
    let bubbleContent = "";
    if (sender === "user") {
        bubbleContent = `<p class="bubble-text">${escapeHtml(content)}</p>`;
        if (metadata && metadata.intent !== "unknown") {
            bubbleContent += `
                <div class="bubble-meta">
                    <span>Intent: <span class="intent-tag">${metadata.intent}</span></span>
                    <span>Confidence: <strong>${metadata.confidence}</strong></span>
                </div>
            `;
        }
    } else {
        // Assistant bubbles may contain structured HTML cards
        bubbleContent = content;
    }
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    bubbleContent += `<span class="bubble-time">${timeStr}</span>`;
    
    bubble.innerHTML = bubbleContent;
    chatContainer.appendChild(bubble);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendSystemErrorMessage(message) {
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble assistant-bubble";
    errorBubble.style.borderLeft = "4px solid var(--color-rose)";
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    errorBubble.innerHTML = `
        <p class="bubble-text" style="color: var(--color-rose);"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(message)}</p>
        <span class="bubble-time">${timeStr}</span>
    `;
    
    chatContainer.appendChild(errorBubble);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ==========================================================================
// 4. Tab Navigation
// ==========================================================================
window.switchTab = function(tabName) {
    // Reset active buttons and tabs
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active-tab"));
    
    // Activate clicked tab
    document.getElementById(`tab-btn-${tabName}`).classList.add("active");
    document.getElementById(`tab-content-${tabName}`).classList.add("active-tab");
};

// ==========================================================================
// 5. Settings, Custom Commands & Timer Render
// ==========================================================================
function renderSettings(data) {
    // Fill settings forms
    document.getElementById("settings-weather-key").value = data.weather_key;
    document.getElementById("settings-smtp-server").value = data.smtp_server;
    document.getElementById("settings-smtp-port").value = data.smtp_port;
    document.getElementById("settings-smtp-user").value = data.smtp_user;
    document.getElementById("settings-smtp-from").value = data.smtp_from;
    document.getElementById("settings-debug-mode").checked = data.debug_mode;
    document.getElementById("settings-voice-rate").value = data.voice_rate;
    document.getElementById("settings-voice-gender").value = data.voice_gender;

    // Toggle Live/Debug input view
    toggleSmtpFieldsVisibility(data.debug_mode);

    // Render Custom Commands Registry
    renderCustomCommandsList(data.custom_commands);

    // Render Reminders List
    renderRemindersList(data.active_reminders);

    // Update memory stats bar
    if (data.memory_stats) {
        const ms = data.memory_stats;
        const convEl = document.getElementById("stat-conversations");
        const factsEl = document.getElementById("stat-facts");
        const modelEl = document.getElementById("stat-model");
        if (convEl) convEl.innerHTML = `<i class="fa-solid fa-comments"></i> ${ms.total_conversations} conversations`;
        if (factsEl) factsEl.innerHTML = `<i class="fa-solid fa-lightbulb"></i> ${ms.known_facts} facts`;
        if (data.groq_model && modelEl) modelEl.innerHTML = `<i class="fa-solid fa-robot"></i> ${data.groq_model.split('-').slice(0,3).join('-')}`;
    }

    // Show Groq status
    if (data.groq_key_set !== undefined) {
        const stateCard = document.getElementById("assistant-state-card");
        if (stateCard && data.groq_key_set) {
            stateCard.title = "Groq AI Brain: Connected";
        }
    }
}

function toggleSmtpFieldsVisibility(debugMode) {
    const fields = document.getElementById("smtp-configurations-fields");
    if (debugMode) {
        fields.style.opacity = "0.5";
        fields.querySelectorAll("input").forEach(inp => inp.disabled = true);
    } else {
        fields.style.opacity = "1";
        fields.querySelectorAll("input").forEach(inp => inp.disabled = false);
    }
}

function renderCustomCommandsList(commands) {
    customCmdList.innerHTML = "";
    
    const keys = Object.keys(commands);
    if (keys.length === 0) {
        customCmdList.innerHTML = `<p class="empty-state" style="padding: 1.5rem; font-size: 0.8rem;">No custom voice commands registered yet.</p>`;
        return;
    }

    keys.forEach(trigger => {
        const val = commands[trigger];
        const responseText = typeof val === "string" ? val : `Action: ${val.action}`;
        
        const item = document.createElement("div");
        item.className = "custom-command-item";
        item.innerHTML = `
            <div class="command-details">
                <span class="command-trigger">"${trigger}"</span>
                <span class="command-response" title="${responseText}">${escapeHtml(responseText)}</span>
            </div>
            <button class="btn-delete-command" onclick="deleteCustomCommand('${escapeJsString(trigger)}')">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;
        customCmdList.appendChild(item);
    });
}

window.deleteCustomCommand = function(trigger) {
    if (confirm(`Are you sure you want to delete the custom command: "${trigger}"?`)) {
        sendWsMessage("delete_command", { trigger });
    }
};

function renderRemindersList(reminders) {
    // Clear existing countdown intervals
    Object.values(activeTimers).forEach(intervalId => clearInterval(intervalId));
    activeTimers = {};

    remindersList.innerHTML = "";
    
    if (reminders.length === 0) {
        remindersList.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-bell-slash"></i>
                <p>No active reminders running.</p>
            </div>
        `;
        return;
    }

    reminders.forEach(r => {
        const card = document.createElement("div");
        card.className = "reminder-card";
        card.id = `card-${r.id}`;
        
        const minPart = r.duration >= 60 ? `${Math.floor(r.duration / 60)}m ` : "";
        const secPart = `${r.duration % 60}s`;

        card.innerHTML = `
            <div class="reminder-info">
                <p class="reminder-message">${escapeHtml(r.message)}</p>
                <span class="reminder-duration">Duration: ${minPart}${secPart}</span>
            </div>
            <div class="reminder-timer">
                <span id="countdown-${r.id}" class="time-countdown">${formatTimeRemaining(r.time_left)}</span>
                <span class="time-end">Alert: ${r.end_time}</span>
            </div>
        `;
        remindersList.appendChild(card);

        // Start local client ticking interval for accurate real-time values
        let timeLeft = r.time_left;
        const intervalId = setInterval(() => {
            timeLeft--;
            if (timeLeft <= 0) {
                document.getElementById(`countdown-${r.id}`).textContent = "00:00";
                clearInterval(intervalId);
            } else {
                document.getElementById(`countdown-${r.id}`).textContent = formatTimeRemaining(timeLeft);
            }
        }, 1000);
        
        activeTimers[r.id] = intervalId;
    });
}

function formatTimeRemaining(seconds) {
    if (seconds <= 0) return "00:00";
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    const pMins = mins.toString().padStart(2, "0");
    const pSecs = secs.toString().padStart(2, "0");
    
    if (hours > 0) {
        return `${hours.toString().padStart(2, "0")}:${pMins}:${pSecs}`;
    }
    return `${pMins}:${pSecs}`;
}

// ==========================================================================
// 6. Audio Alerts & Modals (Web Audio API Synthesizer)
// ==========================================================================
function triggerAlarmAlert(message) {
    alarmMessage.textContent = message;
    alarmModal.classList.remove("hidden");
    
    // Play electronic warning beeps in the browser using Web Audio API
    playSynthesizerBeep();
}

function playSynthesizerBeep() {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    // Create oscillator and gain control nodes
    let count = 0;
    const interval = setInterval(() => {
        if (count >= 3 || alarmModal.classList.contains("hidden")) {
            clearInterval(interval);
            return;
        }
        
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        
        osc.type = "sine";
        osc.frequency.value = 880; // A5 tone
        
        // Attack/decay envelope
        gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.8, audioCtx.currentTime + 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.8);
        
        osc.start();
        osc.stop(audioCtx.currentTime + 0.8);
        
        count++;
    }, 1000);
}

btnDismissAlarm.onclick = () => {
    alarmModal.classList.add("hidden");
};

// ==========================================================================
// 7. Dynamic Canvas Waveform Animation
// ==========================================================================
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 250;
}

window.addEventListener("resize", resizeCanvas);

function animateWaveform() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (assistantState === "listening") {
        // Draw active rapid blue lines representing microphone capture
        drawSineWave(3, "rgba(6, 182, 212, 0.45)", 40, 0.02, wavePhase);
        drawSineWave(2.2, "rgba(6, 182, 212, 0.25)", 20, 0.035, -wavePhase * 1.5);
        drawSineWave(4.5, "rgba(6, 182, 212, 0.15)", 60, 0.012, wavePhase * 0.8);
        wavePhase += 0.15;
    } 
    else if (assistantState === "speaking") {
        // Draw flowing purple lines for verbal vocal responses
        drawSineWave(2, "rgba(139, 92, 246, 0.45)", 35, 0.015, wavePhase);
        drawSineWave(1.5, "rgba(139, 92, 246, 0.25)", 18, 0.025, -wavePhase * 1.2);
        drawSineWave(3, "rgba(139, 92, 246, 0.15)", 50, 0.01, wavePhase * 0.5);
        wavePhase += 0.08;
    } 
    else if (assistantState === "processing") {
        // Draw slow amber loading pattern
        drawSineWave(1.2, "rgba(245, 158, 11, 0.35)", 15, 0.01, wavePhase);
        drawSineWave(1.8, "rgba(245, 158, 11, 0.15)", 8, 0.02, -wavePhase);
        wavePhase += 0.04;
    } 
    else {
        // Calm flat indicator when idle
        drawSineWave(0.8, "rgba(148, 163, 184, 0.08)", 3, 0.005, wavePhase);
        wavePhase += 0.01;
    }
    
    animationFrameId = requestAnimationFrame(animateWaveform);
}

function drawSineWave(frequencyMultiplier, color, amplitude, scale, phase) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    
    const centerY = canvas.height / 2;
    const width = canvas.width;
    
    for (let x = 0; x < width; x++) {
        // Apply envelope padding so wave pinches down to 0 at the edges
        const edgeEnvelope = Math.sin((x / width) * Math.PI);
        const y = centerY + Math.sin(x * scale + phase) * amplitude * frequencyMultiplier * edgeEnvelope;
        
        if (x === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
}

// ==========================================================================
// 8. Action Event Listeners & Initializations
// ==========================================================================

// Click orb to record speech
micOrb.onclick = () => {
    if (assistantState === "idle") {
        sendWsMessage("start_listening", {});
    }
};

// Press Spacebar (when focus is not on input fields) to trigger mic
window.onkeydown = (e) => {
    if (e.code === "Space" && document.activeElement !== textInput && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
        e.preventDefault();
        if (assistantState === "idle") {
            sendWsMessage("start_listening", {});
        }
    }
};

// Text commands submission
textForm.onsubmit = (e) => {
    e.preventDefault();
    const val = textInput.value.trim();
    if (val) {
        appendChatBubble(val, "user");
        sendWsMessage("user_input", { text: val });
        textInput.value = "";
    }
};

// Custom commands submission
customCmdForm.onsubmit = (e) => {
    e.preventDefault();
    const trigger = document.getElementById("cmd-trigger-input").value.trim();
    const response = document.getElementById("cmd-response-input").value.trim();
    if (trigger && response) {
        sendWsMessage("save_command", { trigger, response });
        document.getElementById("cmd-trigger-input").value = "";
        document.getElementById("cmd-response-input").value = "";
    }
};

// Config Settings Form submission
settingsForm.onsubmit = (e) => {
    e.preventDefault();
    const data = {
        weather_key: document.getElementById("settings-weather-key").value.trim(),
        smtp_server: document.getElementById("settings-smtp-server").value.trim(),
        smtp_port: parseInt(document.getElementById("settings-smtp-port").value.trim()) || 587,
        smtp_user: document.getElementById("settings-smtp-user").value.trim(),
        smtp_from: document.getElementById("settings-smtp-from").value.trim(),
        debug_mode: document.getElementById("settings-debug-mode").checked,
        voice_rate: parseInt(document.getElementById("settings-voice-rate").value.trim()) || 175,
        voice_gender: parseInt(document.getElementById("settings-voice-gender").value) || 0
    };
    sendWsMessage("save_settings", data);
};

// Listen to checkbox changes to toggle disabled classes instantly
document.getElementById("settings-debug-mode").onchange = (e) => {
    toggleSmtpFieldsVisibility(e.target.checked);
};

// Clear Chat button trigger
btnClearChat.onclick = () => {
    if (confirm("Clear the activity log?")) {
        chatContainer.innerHTML = `
            <div class="chat-bubble assistant-bubble">
                <p class="bubble-text">Logs cleared. Ready for new commands.</p>
                <span class="bubble-time">Status refreshed</span>
            </div>
        `;
    }
};

// Toggle API Key visibility
btnToggleWeatherKey.onclick = () => {
    const isPass = weatherKeyInput.type === "password";
    weatherKeyInput.type = isPass ? "text" : "password";
    btnToggleWeatherKey.innerHTML = isPass ? `<i class="fa-solid fa-eye-slash"></i>` : `<i class="fa-solid fa-eye"></i>`;
};

// Toast Notifications helper
function showToast(message, isError = false) {
    const container = document.getElementById("toast-notification-container");
    const toast = document.createElement("div");
    toast.className = `toast ${isError ? 'toast-error' : ''}`;
    
    const icon = isError ? "fa-solid fa-circle-exclamation" : "fa-solid fa-circle-check";
    const color = isError ? "var(--color-rose)" : "var(--color-emerald)";
    
    toast.innerHTML = `
        <i class="${icon}" style="color: ${color}"></i>
        <span>${escapeHtml(message)}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto dismiss after 3.5s
    setTimeout(() => {
        toast.style.animation = "bubbleSlideIn 0.3s ease-in reverse forwards";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Helpers
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

function escapeJsString(str) {
    return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Kickstart Layout
resizeCanvas();
animateWaveform();
connectWebSocket();

// ==========================================================================
// Spotlight HUD Controls (Nova 2.1)
// ==========================================================================
const spotlightOverlay = document.getElementById("spotlight-hud");
const spotlightInput = document.getElementById("spotlight-input");

function toggleSpotlightHUD() {
    if (!spotlightOverlay) return;
    
    const isHidden = spotlightOverlay.classList.contains("hidden");
    if (isHidden) {
        // Clear previous input
        spotlightInput.value = "";
        clearActivityFeed();
        
        // Show
        spotlightOverlay.classList.remove("hidden");
        setTimeout(() => spotlightInput.focus(), 50);
    } else {
        // Hide
        spotlightOverlay.classList.add("hidden");
        spotlightInput.blur();
    }
}

// Handle Spotlight input commands
if (spotlightInput) {
    spotlightInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const query = spotlightInput.value.trim();
            if (query) {
                // Add to standard UI chat container too so history matches
                appendChatBubble(query, "user");
                
                // Submit to backend
                sendWsMessage("user_input", { text: query });
                
                // Reset spotlight input state
                spotlightInput.value = "";
            }
        }
    });
}

// Handle escape key to dismiss overlay
window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (spotlightOverlay && !spotlightOverlay.classList.contains("hidden")) {
            toggleSpotlightHUD();
        }
    }
});

// ==========================================================================
// 9. Hands-Free Mode (Continuous Recognition)
// ==========================================================================
const toggleHandsFree = document.getElementById("toggle-hands-free");

function startHandsFreeMode() {
    if (isHandsFreeActive) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("Web Speech API is not supported in this browser. Please use Chrome/Edge.", true);
        if (toggleHandsFree) toggleHandsFree.checked = false;
        return;
    }
    
    handsFreeRecognition = new SpeechRecognition();
    handsFreeRecognition.continuous = true;
    handsFreeRecognition.interimResults = false;
    handsFreeRecognition.lang = 'en-US';
    
    handsFreeRecognition.onstart = () => {
        isHandsFreeActive = true;
        _handsFreePaused = false;
        showToast("Hands-Free Mode enabled. Listening...");
        setHandsFreeUIState(true);
    };
    
    handsFreeRecognition.onresult = (event) => {
        const resultIndex = event.resultIndex;
        const transcript = event.results[resultIndex][0].transcript.trim();
        
        if (transcript) {
            console.log(`[Hands-Free] Spoken: "${transcript}"`);
            
            // Append spoken user bubble to the chat logs
            appendChatBubble(transcript, "user");
            
            // Dispatch to server WebSocket
            sendWsMessage("user_input", { text: transcript });
        }
    };
    
    handsFreeRecognition.onerror = (event) => {
        console.error("[Hands-Free] error: ", event.error);
        if (event.error === 'not-allowed') {
            showToast("Microphone access blocked. Please allow mic permissions.", true);
            stopHandsFreeMode();
        }
    };
    
    handsFreeRecognition.onend = () => {
        if (isHandsFreeActive && !_handsFreePaused) {
            console.log("[Hands-Free] Restarting recognition...");
            try {
                handsFreeRecognition.start();
            } catch (err) {
                console.error("[Hands-Free] Restart failed: ", err);
            }
        }
    };
    
    try {
        handsFreeRecognition.start();
    } catch (err) {
        console.error("[Hands-Free] Start failed: ", err);
    }
}

function stopHandsFreeMode() {
    isHandsFreeActive = false;
    _handsFreePaused = false;
    if (handsFreeRecognition) {
        try {
            handsFreeRecognition.stop();
        } catch (err) {}
        handsFreeRecognition = null;
    }
    showToast("Hands-Free Mode disabled.");
    setHandsFreeUIState(false);
    if (toggleHandsFree) toggleHandsFree.checked = false;
}

function setHandsFreeUIState(active) {
    const label = document.querySelector(".toggle-label-text");
    if (label) {
        label.style.color = active ? "var(--color-cyan)" : "var(--text-dark)";
        label.textContent = active ? "Hands-Free Active" : "Hands-Free (Auto-Listen)";
    }
}

if (toggleHandsFree) {
    toggleHandsFree.onchange = (e) => {
        if (e.target.checked) {
            startHandsFreeMode();
        } else {
            stopHandsFreeMode();
        }
    };
}

