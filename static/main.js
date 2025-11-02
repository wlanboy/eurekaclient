async function loadClients() {
  const res = await fetch('/clients');
  const clients = await res.json();
  const list = document.getElementById('client-list');
  list.innerHTML = '';
  clients.forEach(c => {
    const li = document.createElement('li');
    li.innerHTML = `
      <strong>${c.serviceName}</strong> - ${c.running ? '🟢 läuft' : '🔴 gestoppt'}
      <div>
        <button onclick="start('${c.serviceName}')">Start</button>
        <button class="stop" onclick="stop('${c.serviceName}')">Stop</button>
        <button onclick="del('${c.serviceName}')">Löschen</button>
      </div>
    `;
    list.appendChild(li);
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
