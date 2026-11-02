use std::path::PathBuf;
use std::net::TcpListener;
use tokio::process::{Child, Command};
use anyhow::{Result, Context, anyhow};
use tracing::info;

#[allow(dead_code)]
pub struct CamoufoxProcess {
    pub child: Child,
    pub port: u16,
    pub ws_url: String,
    pub profile_dir: Option<PathBuf>,
}

impl CamoufoxProcess {
    pub fn find_camoufox_binary() -> Result<PathBuf> {
        let home = std::env::var("HOME").context("HOME env not set")?;
        let official_dir = PathBuf::from(home).join(".cache/camoufox/browsers/official");
        
        if official_dir.exists() {
            for entry in std::fs::read_dir(&official_dir)? {
                let entry = entry?;
                let bin = entry.path().join("camoufox-bin");
                if bin.exists() {
                    return Ok(bin);
                }
            }
        }
        Err(anyhow!("Camoufox binary not found in ~/.cache/camoufox/browsers/official/"))
    }

    pub fn get_available_port() -> Result<u16> {
        let listener = TcpListener::bind("127.0.0.1:0")?;
        let port = listener.local_addr()?.port();
        drop(listener);
        Ok(port)
    }

    pub async fn spawn(headless: bool, profile_dir: Option<PathBuf>) -> Result<Self> {
        let bin = Self::find_camoufox_binary()?;
        let port = Self::get_available_port()?;
        let ws_url = format!("ws://127.0.0.1:{}/session", port);

        info!("Spawning Camoufox from {:?} on port {}", bin, port);

        let mut cmd = Command::new(&bin);
        cmd.arg("--remote-debugging-port").arg(port.to_string());
        cmd.arg("--no-remote");

        if headless {
            cmd.arg("--headless");
        }

        if let Some(ref p) = profile_dir {
            cmd.arg("-profile").arg(p);
        }

        // Configure stealth environment
        let camou_config = serde_json::json!({
            "navigator.hardwareConcurrency": 16,
            "screen.width": 1920,
            "screen.height": 1080
        });
        cmd.env("CAMOU_CONFIG_1", camou_config.to_string());
        cmd.env("MOZ_REMOTE_SETTINGS_DEVTOOLS", "1");

        // Detach stdio or redirect
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());

        let child = cmd.spawn().context("Failed to spawn Camoufox binary")?;

        // Give Firefox 1 second to bind its WebSocket port
        tokio::time::sleep(tokio::time::Duration::from_millis(1200)).await;

        Ok(Self {
            child,
            port,
            ws_url,
            profile_dir,
        })
    }
}

impl Drop for CamoufoxProcess {
    fn drop(&mut self) {
        let _ = self.child.start_kill();
    }
}
