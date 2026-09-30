"""Dedupe + decision state + listing snapshot in SQLite. The interface
(seen/record/mark/status/recent/get) is small so the backend can be swapped."""
import sqlite3

_COLS = ("source", "source_id", "verdict", "score", "status", "ts",
         "url", "title", "price_eur", "area", "housing_type")


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS seen ("
            " source TEXT, source_id TEXT, verdict TEXT, score INTEGER,"
            " status TEXT, ts TEXT, url TEXT, title TEXT, price_eur INTEGER,"
            " area TEXT, housing_type TEXT, PRIMARY KEY (source, source_id))"
        )
        self.conn.commit()

    def seen(self, source, source_id):
        cur = self.conn.execute(
            "SELECT 1 FROM seen WHERE source=? AND source_id=?", (source, str(source_id)))
        return cur.fetchone() is not None

    def record(self, decision, ts=""):
        l = decision.listing
        self.conn.execute(
            "INSERT OR IGNORE INTO seen"
            " (source, source_id, verdict, score, status, ts, url, title,"
            "  price_eur, area, housing_type)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (l.source, str(l.source_id), decision.verdict.value, decision.score,
             "new", ts, l.url, l.title, l.price_eur, l.area,
             getattr(l.housing_type, "value", l.housing_type)))
        self.conn.commit()

    def mark(self, source, source_id, status):
        self.conn.execute(
            "UPDATE seen SET status=? WHERE source=? AND source_id=?",
            (status, source, str(source_id)))
        self.conn.commit()

    def status(self, source, source_id):
        cur = self.conn.execute(
            "SELECT status FROM seen WHERE source=? AND source_id=?", (source, str(source_id)))
        row = cur.fetchone()
        return row[0] if row else None

    def get(self, source, source_id):
        cur = self.conn.execute(
            "SELECT * FROM seen WHERE source=? AND source_id=?", (source, str(source_id)))
        row = cur.fetchone()
        return dict(row) if row else None

    def recent(self, verdicts=None, exclude_status=(), limit=20):
        sql = "SELECT * FROM seen"
        where, params = [], []
        if not verdicts:                     # default (None or ()): only SHOW/FLAG, never DROP
            verdicts = ("show", "flag")
        where.append("verdict IN (%s)" % ",".join("?" * len(verdicts)))
        params += list(verdicts)
        if exclude_status:
            # keep NULL-status rows: `NULL NOT IN (...)` is NULL (not TRUE), which would
            # silently exclude them - guard explicitly.
            where.append("(status IS NULL OR status NOT IN (%s))"
                         % ",".join("?" * len(exclude_status)))
            params += list(exclude_status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts DESC, rowid DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]

    def close(self):
        self.conn.close()
