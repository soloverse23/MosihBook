const layout = (title, active, body) => `<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f4f5f7;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#1a1a1a}
nav{background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.08);display:flex;align-items:center;gap:6px;padding:0 20px;height:56px}
nav a{padding:8px 14px;border-radius:8px;color:#444;text-decoration:none}
nav a.on{background:#eef0ff;color:#4f46e5;font-weight:bold}
nav .sp{flex:1}
nav button{border:1px solid #4f46e5;background:none;color:#4f46e5;padding:7px 14px;border-radius:8px;cursor:pointer;font:inherit}
main{max-width:860px;margin:28px auto;padding:0 16px}
.card{background:#fff;border-radius:14px;padding:24px;box-shadow:0 6px 24px rgba(0,0,0,.06);margin-bottom:16px}
h1{margin:0 0 12px;font-size:22px}
</style></head><body>
<nav>
  <a href="/dashboard" class="${active === 'dashboard' ? 'on' : ''}">Dashboard</a>
  <a href="/settings" class="${active === 'settings' ? 'on' : ''}">Settings</a>
  <span class="sp"></span>
  <button id="out">Sign out</button>
</nav>
<main>${body}</main>
<script>
document.getElementById('out').onclick = async () => {
  await fetch('/api/logout', {method:'POST'});
  location.href = '/login';
};
</script></body></html>`;

module.exports = {
  dashboard: (user) => layout('Dashboard', 'dashboard',
    `<div class="card"><h1>Dashboard</h1><p>Hello <b>${user}</b>, welcome 👋</p></div>`),
  settings: (user) => layout('Settings', 'settings',
    `<div class="card"><h1>Settings</h1><p>Username: <b>${user}</b></p></div>`),
};
