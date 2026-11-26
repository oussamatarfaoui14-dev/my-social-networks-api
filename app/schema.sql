CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 first_name TEXT NOT NULL, last_name TEXT NOT NULL, password_hash TEXT NOT NULL,
 bio TEXT NOT NULL DEFAULT '', avatar_url TEXT,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS groups (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
 icon TEXT NOT NULL, cover_url TEXT NOT NULL, visibility TEXT NOT NULL CHECK(visibility IN ('public','private','secret')),
 members_can_post INTEGER NOT NULL DEFAULT 1, members_can_create_events INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS group_members (
 id INTEGER PRIMARY KEY, group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('admin','member')), UNIQUE(group_id,user_id)
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
 starts_at TEXT NOT NULL, ends_at TEXT NOT NULL CHECK(ends_at > starts_at),
 location TEXT NOT NULL, cover_url TEXT NOT NULL,
 visibility TEXT NOT NULL CHECK(visibility IN ('public','private')),
 group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published')),
 shopping_enabled INTEGER NOT NULL DEFAULT 0, carpool_enabled INTEGER NOT NULL DEFAULT 0,
 ticketing_enabled INTEGER NOT NULL DEFAULT 0,
 CHECK(ticketing_enabled=0 OR visibility='public')
);
CREATE TABLE IF NOT EXISTS event_members (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 role TEXT NOT NULL CHECK(role IN ('organizer','participant')),
 status TEXT NOT NULL CHECK(status IN ('invited','accepted')),
 CHECK(role!='organizer' OR status='accepted'), UNIQUE(event_id,user_id)
);
CREATE TABLE IF NOT EXISTS threads (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL,
 group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
 event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
 CHECK((group_id IS NOT NULL) + (event_id IS NOT NULL) = 1)
);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY, thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS message_comments (
 id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS albums (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS photos (
 id INTEGER PRIMARY KEY, album_id INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, url TEXT NOT NULL, caption TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS photo_comments (
 id INTEGER PRIMARY KEY, photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS polls (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 title TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS questions (
 id INTEGER PRIMARY KEY, poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS options (
 id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
 text TEXT NOT NULL, UNIQUE(question_id,text), UNIQUE(id,question_id)
);
CREATE TABLE IF NOT EXISTS answers (
 id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 option_id INTEGER NOT NULL, UNIQUE(question_id,user_id),
 FOREIGN KEY(option_id,question_id) REFERENCES options(id,question_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS ticket_types (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 name TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>=0),
 quantity INTEGER NOT NULL CHECK(quantity>=1), UNIQUE(event_id,name), UNIQUE(id,event_id)
);
CREATE TABLE IF NOT EXISTS tickets (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 ticket_type_id INTEGER NOT NULL, email TEXT NOT NULL COLLATE NOCASE,
 first_name TEXT NOT NULL, last_name TEXT NOT NULL, address_line TEXT NOT NULL,
 postal_code TEXT NOT NULL, city TEXT NOT NULL, country TEXT NOT NULL,
 identity_key TEXT NOT NULL, receipt_hash TEXT NOT NULL, amount_cents INTEGER NOT NULL,
 purchased_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(event_id,email), UNIQUE(event_id,identity_key),
 FOREIGN KEY(ticket_type_id,event_id) REFERENCES ticket_types(id,event_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS shopping_items (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 name TEXT NOT NULL, name_key TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
 arrival_at TEXT NOT NULL, UNIQUE(event_id,name_key)
);
CREATE TABLE IF NOT EXISTS carpools (
 id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 departure_location TEXT NOT NULL, departure_at TEXT NOT NULL,
 price_cents INTEGER NOT NULL CHECK(price_cents>=0), available_seats INTEGER NOT NULL CHECK(available_seats>=1),
 max_detour_minutes INTEGER NOT NULL CHECK(max_detour_minutes>=0)
);
CREATE INDEX IF NOT EXISTS idx_sessions_expiration ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_group_member_user ON group_members(user_id,group_id);
CREATE INDEX IF NOT EXISTS idx_event_member_user ON event_members(user_id,event_id);
CREATE INDEX IF NOT EXISTS idx_events_group ON events(group_id);
CREATE INDEX IF NOT EXISTS idx_events_visibility ON events(status,visibility);
CREATE INDEX IF NOT EXISTS idx_threads_event ON threads(event_id);
CREATE INDEX IF NOT EXISTS idx_threads_group ON threads(group_id);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_message_comments ON message_comments(message_id);
CREATE INDEX IF NOT EXISTS idx_albums_event ON albums(event_id);
CREATE INDEX IF NOT EXISTS idx_photos_album ON photos(album_id);
CREATE INDEX IF NOT EXISTS idx_photo_comments ON photo_comments(photo_id);
CREATE INDEX IF NOT EXISTS idx_polls_event ON polls(event_id);
CREATE INDEX IF NOT EXISTS idx_questions_poll ON questions(poll_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_tickets_type ON tickets(ticket_type_id);
CREATE INDEX IF NOT EXISTS idx_carpools_event ON carpools(event_id);
PRAGMA user_version = 1;
