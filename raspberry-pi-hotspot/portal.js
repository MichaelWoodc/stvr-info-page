(() => {
  const uuid = () => crypto.randomUUID ? crypto.randomUUID() : '10000000-1000-4000-8000-100000000000'.replace(/[018]/g,c => (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16));
  function stored(storageName, key) {
    try { const storage = window[storageName]; let value = storage.getItem(key); if (!value) { value = uuid(); storage.setItem(key, value); } return value; }
    catch { return uuid(); }
  }
  const visitor = stored('localStorage', 'portal-visitor');
  const session = stored('sessionStorage', 'portal-session');
  const footer = document.querySelector('footer') || document.body;
  const panel = document.createElement('div');
  panel.className = 'portal-guestbook';
  panel.innerHTML = `<p class="portal-stats" aria-live="polite">Visitor count: loading…</p><details><summary>Sign the guestbook</summary><form><label>Your name or nickname<input name="name" maxlength="80" required autocomplete="nickname"></label><label>Your message<textarea name="message" maxlength="2000" rows="4" required></textarea></label><button type="submit">Sign the guestbook</button><p class="portal-message" role="status"></p></form></details>`;
  footer.prepend(panel);
  const style = document.createElement('link'); style.rel = 'stylesheet'; style.href = '/portal.css'; document.head.append(style);
  async function post(path, data) {
    const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const result = await response.json().catch(() => ({error:response.status===429?'Please wait a moment and try again.':'Could not save right now. Please try again.'})); if (!response.ok) throw Error(result.error || 'Please try again.'); return result;
  }
  post('/api/visit', {visitor_id:visitor,session_id:session,page:location.pathname})
    .then(data => panel.querySelector('.portal-stats').textContent = `Visitors: ${data.visitors} · Visits: ${data.visits}`)
    .catch(() => panel.querySelector('.portal-stats').textContent = 'Visitor count is temporarily unavailable.');
  let submission = uuid();
  panel.querySelector('form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget;
    const button = form.querySelector('button'); const status = form.querySelector('.portal-message');
    button.disabled = true; status.textContent = 'Saving your message…';
    try {
      await post('/api/guestbook', {visitor_id:visitor,submission_id:submission,name:form.elements.name.value,message:form.elements.message.value});
      form.reset(); submission = uuid(); status.textContent = 'Thank you for signing the guestbook! Your message has been saved.';
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });
})();
