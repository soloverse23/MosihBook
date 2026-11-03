// Local dev server (no Vercel account needed): node dev.js
const http = require('http'), fs = require('fs'), path = require('path');
const routes = { '/': 'dashboard', '/dashboard': 'dashboard', '/settings': 'settings' };

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  res.status = (c) => (res.statusCode = c, res);
  res.json = (o) => (res.setHeader('Content-Type', 'application/json'), res.end(JSON.stringify(o)));
  res.send = (b) => res.end(b);
  res.redirect = (c, l) => (res.writeHead(c, { Location: l }), res.end());
  req.query = Object.fromEntries(url.searchParams);

  const run = (file) => {
    let raw = '';
    req.on('data', (d) => (raw += d));
    req.on('end', () => {
      try { req.body = raw ? JSON.parse(raw) : {}; } catch { req.body = {}; }
      require('./api/' + file)(req, res);
    });
  };

  if (routes[url.pathname]) { req.query.name = routes[url.pathname]; return run('page'); }
  if (/^\/api\/(login|logout|me)$/.test(url.pathname)) return run(url.pathname.slice(5));
  if (url.pathname === '/login') return res.end(fs.readFileSync(path.join(__dirname, 'login.html')));
  res.redirect(302, '/dashboard');
}).listen(3000, () => console.log('http://localhost:3000'));
