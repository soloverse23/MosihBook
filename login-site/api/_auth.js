const crypto = require('crypto');
const USER = process.env.APP_USER || 'admin';
const PASS = process.env.APP_PASSWORD || 'kweh4G3PwDxJ';
const SECRET = process.env.SESSION_SECRET || '55f28d0af6ed5fe705126948fad45199ddaae93d6e48a61b';

const sign = (u) => crypto.createHmac('sha256', SECRET).update(u).digest('hex');
const safeEq = (a, b) => {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
};
const isAuthed = (req) => {
  const m = /(?:^|;\s*)session=([a-f0-9]+)/.exec(req.headers.cookie || '');
  return !!m && safeEq(m[1], sign(USER));
};
module.exports = { USER, PASS, sign, safeEq, isAuthed };
