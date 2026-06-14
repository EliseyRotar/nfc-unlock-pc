// NFC Unlock PC - setup wizard frontend.
// Talks to the Flask backend in setup_server.py (localhost only).

let selectedReaderIndex = null;
let scanTimer = null;
let detectedIdentifier = null;

const steps = ["step-driver", "step-reader", "step-tap", "step-confirm", "step-credentials", "step-done"];

function showStep(id) {
  for (const s of steps) {
    document.getElementById(s).classList.toggle("active", s === id);
  }
}

async function checkDriver() {
  try {
    const res = await fetch("/api/driver_status");
    const data = await res.json();
    if (data.readers_found > 0 || data.system !== "Windows") {
      showStep("step-reader");
      loadReaders();
      return;
    }
    if (data.candidates && data.candidates.length > 0) {
      document.getElementById("driver-checking").classList.add("hidden");
      document.getElementById("driver-problem").classList.remove("hidden");
      document.getElementById("driver-device-name").textContent =
        data.candidates.map((d) => `${d.FriendlyName} (${d.Status})`).join(", ");
      return;
    }
    // No reader visible and nothing obviously wrong - just go to the
    // reader-select step, which will show "no readers found".
    showStep("step-reader");
    loadReaders();
  } catch (e) {
    showStep("step-reader");
    loadReaders();
  }
}

document.getElementById("btn-install-driver").addEventListener("click", async () => {
  const status = document.getElementById("driver-install-status");
  status.textContent = "Asking Windows to search for a driver (approve the permission prompt)...";
  try {
    await fetch("/api/install_driver", { method: "POST" });
    status.textContent = "Done. Checking again...";
    setTimeout(checkDriver, 4000);
  } catch (e) {
    status.textContent = "Error: " + e;
  }
});

document.getElementById("btn-skip-driver").addEventListener("click", () => {
  showStep("step-reader");
  loadReaders();
});

async function loadReaders() {
  const list = document.getElementById("reader-list");
  list.innerHTML = '<p class="muted">Looking for readers...</p>';
  try {
    const res = await fetch("/api/readers");
    const data = await res.json();
    const readers = data.readers || [];
    if (readers.length === 0) {
      list.innerHTML = '<p class="muted">No PC/SC readers found. Plug one in, install ' +
        'its driver, and click Refresh.</p>';
      return;
    }
    list.innerHTML = "";
    readers.forEach((name, idx) => {
      const item = document.createElement("div");
      item.className = "reader-item";
      item.textContent = name;
      item.addEventListener("click", () => selectReader(idx, name));
      list.appendChild(item);
    });
  } catch (e) {
    list.innerHTML = '<p class="muted">Error contacting the setup server: ' + e + "</p>";
  }
}

function selectReader(idx, name) {
  selectedReaderIndex = idx;
  document.querySelectorAll(".reader-item").forEach((el, i) => {
    el.classList.toggle("selected", i === idx);
  });
  document.getElementById("selected-reader-name").textContent = name;
  setTimeout(() => {
    showStep("step-tap");
    startScanning();
  }, 250);
}

function startScanning() {
  if (scanTimer) clearInterval(scanTimer);
  scanTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/scan?reader=${selectedReaderIndex}`);
      const data = await res.json();
      if (data.identifier) {
        clearInterval(scanTimer);
        scanTimer = null;
        detectedIdentifier = data.identifier;
        document.getElementById("detected-identifier").textContent = detectedIdentifier;
        showStep("step-confirm");
      }
    } catch (e) {
      // transient errors are fine - keep polling
    }
  }, 400);
}

function rescan() {
  detectedIdentifier = null;
  showStep("step-tap");
  startScanning();
}

async function saveEnrollment() {
  const username = document.getElementById("input-username").value;
  const password = document.getElementById("input-password").value;

  const res = await fetch("/api/enroll", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier: detectedIdentifier, username, password }),
  });
  const data = await res.json();
  if (data.error) {
    alert("Error: " + data.error);
    return;
  }
  renderNextSteps(data.next_steps);
  showStep("step-done");
}

function renderNextSteps(next) {
  document.getElementById("done-title").textContent = next.title || "";
  const container = document.getElementById("done-commands");
  container.innerHTML = "";

  function addBlock(label, commands) {
    if (label) {
      const h = document.createElement("h3");
      h.textContent = label;
      container.appendChild(h);
    }
    const pre = document.createElement("pre");
    pre.textContent = (commands || []).join("\n");
    container.appendChild(pre);
  }

  if (next.tier1 || next.tier2) {
    if (next.tier1) addBlock(next.tier1.label, next.tier1.commands);
    if (next.tier2) addBlock(next.tier2.label, next.tier2.commands);
  } else {
    addBlock(null, next.commands);
  }

  document.getElementById("done-note").textContent = next.note || "";

  const actionRow = document.getElementById("done-action");
  const actionBtn = document.getElementById("btn-done-action");
  const actionStatus = document.getElementById("done-action-status");
  actionStatus.textContent = "";

  if (next.action === "install_task_windows") {
    actionRow.classList.remove("hidden");
    actionBtn.textContent = "Install the background unlock task";
    actionBtn.onclick = async () => {
      actionStatus.textContent = "Asking Windows to install the task (approve the permission prompt)...";
      try {
        const res = await fetch("/api/install_unlock_task", { method: "POST" });
        const data = await res.json();
        if (data.error) {
          actionStatus.textContent = "Error: " + data.error;
        } else {
          actionStatus.textContent = "Done. The 'NFCUnlockPC' task is installed and will " +
            "run at boot. Tap your phone at the lock screen to try it.";
        }
      } catch (e) {
        actionStatus.textContent = "Error: " + e;
      }
    };
  } else {
    actionRow.classList.add("hidden");
  }
}

document.getElementById("btn-refresh-readers").addEventListener("click", loadReaders);
document.getElementById("btn-confirm-yes").addEventListener("click", () => showStep("step-credentials"));
document.getElementById("btn-confirm-no").addEventListener("click", rescan);
document.getElementById("btn-save").addEventListener("click", saveEnrollment);

checkDriver();
