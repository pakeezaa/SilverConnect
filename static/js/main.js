// NAV TOGGLE
function toggleNav() {
  document.getElementById('navLinks').classList.toggle('open');
}

// API HELPERS
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

function showAlert(id, msg, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert alert-${type} show`;
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.className = 'alert';
}

// Role toggle visual feedback on login page
document.querySelectorAll('.role-toggle input[type=radio]').forEach(radio => {
  radio.addEventListener('change', () => {
    document.querySelectorAll('.role-option .role-btn').forEach(btn => {
      btn.style.background = '';
      btn.style.color = '';
    });
    if (radio.checked) {
      radio.nextElementSibling.style.background = '#0a4932';
      radio.nextElementSibling.style.color = '#fff';
    }
  });
});
