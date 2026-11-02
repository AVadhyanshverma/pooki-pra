use std::path::PathBuf;
use rusqlite::{Connection, params};
use anyhow::Result;
use chrono::Utc;

pub struct Database {
    pub path: PathBuf,
}

impl Database {
    pub fn default_path() -> Result<PathBuf> {
        let home = std::env::var("HOME")?;
        let p = PathBuf::from(home).join(".local/share/agent-browser/agent_browser.db");
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent)?;
        }
        Ok(p)
    }

    pub fn new() -> Result<Self> {
        let path = Self::default_path()?;
        let conn = Connection::open(&path)?;
        conn.execute_batch("
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                is_temp INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_uuid TEXT UNIQUE NOT NULL,
                profile_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                initial_url TEXT,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS session_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_uuid TEXT NOT NULL,
                step_idx INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                operation TEXT NOT NULL,
                target_element TEXT,
                confidence REAL,
                latency_ms REAL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scrapes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                word_count INTEGER,
                profile_name TEXT,
                scraped_at TEXT NOT NULL
            );
        ")?;
        Ok(Self { path })
    }

    pub fn get_conn(&self) -> Result<Connection> {
        Ok(Connection::open(&self.path)?)
    }

    pub fn record_scrape(&self, url: &str, title: &str, file_path: &str, word_count: usize, profile_name: &str) -> Result<()> {
        let conn = self.get_conn()?;
        let now = Utc::now().to_rfc3339();
        conn.execute(
            "INSERT INTO scrapes (url, title, file_path, word_count, profile_name, scraped_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![url, title, file_path, word_count as i64, profile_name, now],
        )?;
        Ok(())
    }

    pub fn record_action(&self, session_uuid: &str, step_idx: usize, url: &str, title: &str, operation: &str) -> Result<()> {
        let conn = self.get_conn()?;
        let now = Utc::now().to_rfc3339();
        conn.execute(
            "INSERT INTO session_actions (session_uuid, step_idx, url, title, operation, target_element, confidence, latency_ms, timestamp) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![session_uuid, step_idx as i64, url, title, operation, url, 1.0, 0.0, now],
        )?;
        Ok(())
    }
}
