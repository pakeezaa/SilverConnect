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

// Skill checkbox highlight (register-volunteer form + volunteer profile edit)
document.querySelectorAll('.checkbox-group .checkbox-item input[type=checkbox]').forEach(cb => {
  cb.addEventListener('change', () => {
    cb.closest('.checkbox-item').classList.toggle('checked', cb.checked);
  });
});

// PROFILE VIEW/EDIT TOGGLE (user + volunteer profile pages)
function showEditForm() {
  document.getElementById('profileView').classList.add('hidden');
  document.getElementById('profileEdit').classList.remove('hidden');
}

function hideEditForm() {
  document.getElementById('profileEdit').classList.add('hidden');
  document.getElementById('profileView').classList.remove('hidden');
}

// Saves the profile edit form. `role` is 'user' or 'volunteer' — volunteers
// have an extra availability field and a skills checkbox group.
async function saveProfile(role) {
  const data = {
    name: document.getElementById('editName').value.trim(),
    phone: document.getElementById('editPhone').value.trim(),
    neighborhood: document.getElementById('editNeighborhood').value.trim(),
    bio: document.getElementById('editBio').value.trim()
  };
  if (role === 'volunteer') {
    data.availability = document.getElementById('editAvailability').value;
    data.skills = [...document.querySelectorAll('#skillCheckboxes input:checked')].map(i => i.value);
  }
  const json = await apiPost('/profile/edit', data);
  if (json.success) {
    showAlert('editAlert', 'Profile updated successfully!', 'success');
    setTimeout(() => location.reload(), 1000);
  }
}
