async function loadClients() {
  const res = await fetch('/clients');
  const clients = await res.json();
  const list = document.getElementById('client-list');
  list.innerHTML = '';

  clients.forEach(client => {
    const li = document.createElement('li');
    li.innerHTML = `
      <strong>${client.serviceName}</strong> - ${client.running ? '🟢 läuft' : '🔴 gestoppt'}
      <div>
        <button onclick="start('${client.serviceName}')">Start</button>
        <button class="stop" onclick="stop('${client.serviceName}')">Stop</button>
        <button onclick="del('${client.serviceName}')">Löschen</button>
        <button onclick="toggleLogs('${client.serviceName}')">Show Logs</button>
      </div>
    `;
    list.appendChild(li);

    const logViewer = createLogViewer(client.serviceName);
    list.appendChild(logViewer);
  });
}

async function start(name) {
  try {
    const res = await fetch(`/clients/${name}/start`, { method: 'POST' });
    if (!res.ok) {
      const data = await res.json();
      alert(`⚠️ ${data.detail || 'Fehler beim Starten von ' + name}`);
    }
  } catch (err) {
    alert(`❌ Netzwerkfehler beim Starten von ${name}`);
  } finally {
    loadClients();
  }
}

async function stop(name) {
  try {
    const res = await fetch(`/clients/${name}/stop`, { method: 'POST' });
    if (!res.ok) {
      const data = await res.json();
      alert(`⚠️ ${data.detail || 'Fehler beim Stoppen von ' + name}`);
    }
  } catch (err) {
    alert(`❌ Netzwerkfehler beim Stoppen von ${name}`);
  } finally {
    loadClients();
  }
}

async function del(name) {
  try {
    const res = await fetch(`/clients/${name}`, { method: 'DELETE' });
    if (!res.ok) {
      const data = await res.json();
      alert(`⚠️ ${data.detail || 'Fehler beim Löschen von ' + name}`);
    }
  } catch (err) {
    alert(`❌ Netzwerkfehler beim Löschen von ${name}`);
  } finally {
    loadClients();
  }
}

function createLogViewer(name) {
  const logDiv = document.createElement('div');
  logDiv.id = `log-${name}`;
  logDiv.className = 'log-viewer';
  logDiv.style.display = 'none'; 
  logDiv.innerHTML = `<pre><code id="log-content-${name}">Logs werden geladen...</code></pre>`;
  return logDiv;
}


async function showLogs(name) {
  const logContainer = document.getElementById(`log-${name}`);
  if (!logContainer) return;

  const res = await fetch(`/clients/${name}/logs`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const logContent = document.getElementById(`log-content-${name}`);
  logContent.textContent = "";

  function read() {
    reader.read().then(({ done, value }) => {
      if (done) return;
      logContent.textContent += decoder.decode(value);
      logContent.scrollTop = logContent.scrollHeight;
      read();
    });
  }

  read();
}

function toggleLogs(name) {
  const logDiv = document.getElementById(`log-${name}`);
  if (!logDiv) {
    alert(`⚠️ Log-Container für ${name} nicht gefunden.`);
    return;
  }

  if (logDiv.style.display === 'block') {
    logDiv.style.display = 'none';
  } else {
    logDiv.style.display = 'block';
    showLogs(name);
  }
}

document.getElementById('add-form').onsubmit = async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.httpPort = parseInt(data.httpPort);
  data.securePort = parseInt(data.securePort);
  data.leaseInfo = {
    renewalIntervalInSecs: 30,
    durationInSecs: 90
  };
  await fetch('/clients', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  e.target.reset();
  loadClients();
};

document.getElementById('theme-switch').addEventListener('change', (e) => {
  document.body.classList.toggle('dark', e.target.checked);
});

loadClients();
