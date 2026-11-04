const chatWindow = document.getElementById("chatWindow");
const chatForm   = document.getElementById("chatForm");
const chatInput  = document.getElementById("chatInput");
const badge      = document.getElementById("sentimentBadge");
const clearChatButton = document.getElementById("clearChatButton");
const micButton = document.getElementById("micButton");
const voiceStatus = document.getElementById("voiceStatus");
const speakReplies = document.getElementById("speakReplies");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const speechAvailable = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
let recognition = null;
let isListening = false;

function scrollBottom(){ chatWindow.scrollTop = chatWindow.scrollHeight; }

function speak(text, userRequested = false) {
  if ((!speakReplies.checked && !userRequested) || !speechAvailable) {
    if (!speechAvailable) voiceStatus.textContent = "Spoken replies aren’t supported in this browser.";
    return;
  }
  try {
    voiceStatus.textContent = "Starting spoken reply…";
    const synthesis = window.speechSynthesis;
    synthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(
      text.replace(/https?:\/\/\S+/g, " ").replace(/[*_#]/g, "")
    );
    utterance.lang = document.documentElement.lang || navigator.language || "en";
    utterance.rate = 0.96;
    utterance.onstart = () => { voiceStatus.textContent = "Reading the reply aloud…"; };
    utterance.onend = () => { voiceStatus.textContent = "Finished reading the reply"; };
    utterance.onerror = (event) => {
      if (event.error !== "canceled" && event.error !== "interrupted") {
        voiceStatus.textContent = "Tap a speaker button to hear the reply.";
      }
    };
    synthesis.speak(utterance);
    synthesis.resume();
  } catch (error) {
    voiceStatus.textContent = "Tap a speaker button to hear the reply.";
  }
}

function setListening(listening) {
  isListening = listening;
  micButton.classList.toggle("is-listening", listening);
  micButton.setAttribute("aria-label", listening ? "Stop speaking" : "Start speaking");
  micButton.innerHTML = listening
    ? '<i class="bi bi-stop-fill"></i><span>Listening</span>'
    : '<i class="bi bi-mic"></i><span>Speak</span>';
}

function addMsg(text, who, sentiment){
  const div = document.createElement("div");
  div.className = "msg " + (who === "user" ? "user" : "bot");
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  if (sentiment) bubble.classList.add("sent-" + sentiment);
  div.appendChild(bubble);
  if (who !== "user" && text !== "...") {
    const replayButton = document.createElement("button");
    replayButton.className = "reply-speak-button";
    replayButton.type = "button";
    replayButton.setAttribute("aria-label", "Read this reply aloud");
    replayButton.title = "Read this reply aloud";
    replayButton.innerHTML = '<i class="bi bi-volume-up"></i><span>Listen</span>';
    replayButton.addEventListener("click", () => speak(text, true));
    div.appendChild(replayButton);
  }
  chatWindow.appendChild(div);
  scrollBottom();
  return div;
}

async function loadHistory(){
  const r = await fetch("/api/history");
  if (!r.ok) throw new Error("Unable to load your chat history.");
  const msgs = await r.json();
  if (!Array.isArray(msgs)) throw new Error("The chat history response was invalid.");
  if (msgs.length) chatWindow.replaceChildren();
  msgs.forEach(m => addMsg(m.text, m.sender, m.sender === "user" ? m.sentiment : null));
}

clearChatButton.addEventListener("click", async () => {
  if (!window.confirm("Clear all of your chat messages? This cannot be undone.")) return;

  clearChatButton.disabled = true;
  try {
    const response = await fetch("/api/history/clear", {
      method: "POST",
      headers: {
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      }
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to clear your chats.");

    chatWindow.replaceChildren();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    addMsg("Your chat history has been cleared. I'm here whenever you'd like to start again.", "bot");
    badge.textContent = "Ready when you are";
    badge.className = "badge sentiment-badge";
    voiceStatus.textContent = "Your chat history was cleared";
  } catch (error) {
    addMsg(error.message || "Unable to clear your chats. Please try again.", "bot");
  } finally {
    clearChatButton.disabled = false;
  }
});

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.onstart = () => {
    setListening(true);
    voiceStatus.textContent = "Listening… speak naturally";
  };
  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      transcript += event.results[i][0].transcript;
    }
    chatInput.value = transcript.trim();
    voiceStatus.textContent = event.results[event.results.length - 1].isFinal
      ? "Message ready — send it when you’re ready"
      : "Listening…";
  };
  recognition.onerror = (event) => {
    const messages = {
      "not-allowed": "Microphone permission is blocked. Allow access in your browser settings.",
      "no-speech": "No speech detected. Tap the microphone to try again.",
      "audio-capture": "No microphone was found. You can type your message instead."
    };
    voiceStatus.textContent = messages[event.error] || "Voice input stopped. You can type instead.";
  };
  recognition.onend = () => setListening(false);
} else {
  micButton.disabled = true;
  micButton.title = "Voice input is not supported in this browser.";
  voiceStatus.textContent = "Voice input isn’t available in this browser. You can type instead.";
}

if (!speechAvailable) {
  speakReplies.checked = false;
  speakReplies.disabled = true;
  voiceStatus.textContent = "Spoken replies aren’t supported in this browser.";
}

micButton.addEventListener("click", () => {
  if (!recognition) return;
  if (isListening) recognition.stop();
  else {
    try {
      recognition.start();
    } catch (error) {
      voiceStatus.textContent = "Voice input couldn’t start. Please try again.";
    }
  }
});

speakReplies.addEventListener("change", () => {
  if (!speakReplies.checked && speechAvailable) {
    window.speechSynthesis.cancel();
    voiceStatus.textContent = "Automatic speech is off — use Listen on a reply.";
  }
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  addMsg(text, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  const typingIndicator = addMsg("...", "bot");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    typingIndicator.remove();
    if (!res.ok) throw new Error(data.error || "Unable to send your message.");
    addMsg(data.reply, "bot", data.sentiment);
    badge.textContent = `${data.sentiment.toUpperCase()} • ${data.confidence}%`;
    badge.className = "badge " + (
      data.sentiment === "positive" ? "bg-success" :
      data.sentiment === "negative" ? "bg-danger"  : "bg-secondary"
    );
    speak(data.reply);
    if (!speakReplies.checked) voiceStatus.textContent = "Reply received — tap Listen to hear it";
  } catch (err) {
    typingIndicator.remove();
    addMsg(err.message || "Sorry, something went wrong. Please try again.", "bot");
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
  }
});

chatInput.disabled = true;
loadHistory()
  .catch((error) => addMsg(error.message, "bot"))
  .finally(() => { chatInput.disabled = false; });