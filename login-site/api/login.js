const { USER, PASS, sign, safeEq } = require('./_auth');

module.exports = (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ ok: false });
  const { username = '', password = '' } = req.body || {};
  if (safeEq(username, USER) && safeEq(password, PASS)) {
    res.setHeader('Set-Cookie',
      `session=${sign(USER)}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=604800`);
    return res.json({ ok: true });
  }
  res.status(401).json({ ok: false });
};
