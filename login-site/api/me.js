const { USER, isAuthed } = require('./_auth');

module.exports = (req, res) => res.json({ ok: isAuthed(req), user: USER });
