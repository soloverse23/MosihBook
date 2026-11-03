const { USER, isAuthed } = require('./_auth');
const pages = require('./_pages');

module.exports = (req, res) => {
  const name = req.query.name;
  const path = '/' + name;
  if (!pages[name]) return res.redirect(302, '/dashboard');
  if (!isAuthed(req)) return res.redirect(302, '/login?next=' + encodeURIComponent(path));
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.send(pages[name](USER));
};
