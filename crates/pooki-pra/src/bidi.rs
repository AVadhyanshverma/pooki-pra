use std::sync::atomic::{AtomicU64, Ordering};
use anyhow::{Result, Context, anyhow};
use futures_util::{StreamExt, SinkExt};
use serde_json::{json, Value};
use tokio::net::TcpStream;
use tokio_tungstenite::{connect_async, MaybeTlsStream, WebSocketStream};
use tokio_tungstenite::tungstenite::Message;
use tracing::{info, debug};

pub struct BiDiClient {
    ws_stream: WebSocketStream<MaybeTlsStream<TcpStream>>,
    msg_id: AtomicU64,
    pub context_id: Option<String>,
}

impl BiDiClient {
    pub async fn connect(ws_url: &str) -> Result<Self> {
        info!("Connecting to WebDriver BiDi at {}", ws_url);
        let mut stream = None;
        let mut last_err = None;

        for _ in 0..15 {
            match connect_async(ws_url).await {
                Ok((s, _)) => {
                    stream = Some(s);
                    break;
                }
                Err(e) => {
                    last_err = Some(e);
                    tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                }
            }
        }

        let ws_stream = stream.ok_or_else(|| {
            anyhow!("Failed to connect to BiDi WebSocket after retries: {:?}", last_err)
        })?;
        
        let mut client = Self {
            ws_stream,
            msg_id: AtomicU64::new(1),
            context_id: None,
        };

        // Initialize session
        client.init_session().await?;
        Ok(client)
    }

    fn next_id(&self) -> u64 {
        self.msg_id.fetch_add(1, Ordering::SeqCst)
    }

    pub async fn send_cmd(&mut self, method: &str, params: Value) -> Result<Value> {
        let id = self.next_id();
        let payload = json!({
            "id": id,
            "method": method,
            "params": params
        });

        debug!("Sending BiDi message: {}", payload);
        self.ws_stream.send(Message::Text(payload.to_string().into())).await?;

        // Wait for response matching ID
        while let Some(msg_result) = self.ws_stream.next().await {
            let msg = msg_result?;
            if let Message::Text(text) = msg {
                debug!("Received BiDi response: {}", text);
                if let Ok(val) = serde_json::from_str::<Value>(&text) {
                    if val.get("id").and_then(|v| v.as_u64()) == Some(id) {
                        if let Some(err) = val.get("error") {
                            return Err(anyhow!("BiDi error {}: {}", err, val.get("message").unwrap_or(&json!(""))));
                        }
                        return Ok(val.get("result").cloned().unwrap_or(Value::Null));
                    }
                }
            }
        }

        Err(anyhow!("WebSocket closed unexpectedly while waiting for response id {}", id))
    }

    pub async fn init_session(&mut self) -> Result<()> {
        let res = self.send_cmd("session.new", json!({
            "capabilities": {}
        })).await?;
        debug!("Session initialized: {:?}", res);

        // Get context tree
        let tree_res = self.send_cmd("browsingContext.getTree", json!({})).await?;
        if let Some(contexts) = tree_res.get("contexts").and_then(|c| c.as_array()) {
            if let Some(first) = contexts.first() {
                if let Some(cid) = first.get("context").and_then(|c| c.as_str()) {
                    self.context_id = Some(cid.to_string());
                    info!("Active BiDi context ID: {}", cid);
                }
            }
        }
        
        if self.context_id.is_none() {
            // Create a new browsing context
            let new_ctx = self.send_cmd("browsingContext.create", json!({"type": "tab"})).await?;
            if let Some(cid) = new_ctx.get("context").and_then(|c| c.as_str()) {
                self.context_id = Some(cid.to_string());
                info!("Created new BiDi context ID: {}", cid);
            }
        }

        Ok(())
    }

    pub async fn navigate(&mut self, url: &str) -> Result<Value> {
        let ctx = self.context_id.as_ref().context("No active browsing context")?;
        let res = self.send_cmd("browsingContext.navigate", json!({
            "context": ctx,
            "url": url,
            "wait": "complete"
        })).await?;
        Ok(res)
    }

    pub async fn evaluate_script(&mut self, expression: &str) -> Result<Value> {
        let ctx = self.context_id.as_ref().context("No active browsing context")?;
        let res = self.send_cmd("script.evaluate", json!({
            "expression": expression,
            "target": {
                "context": ctx
            },
            "awaitPromise": true,
            "resultOwnership": "root"
        })).await?;

        if let Some(res_type) = res.get("type").and_then(|t| t.as_str()) {
            if res_type == "exception" {
                let err_text = res.get("exceptionDetails")
                    .and_then(|d| d.get("text"))
                    .and_then(|t| t.as_str())
                    .unwrap_or("Unknown JS exception");
                return Err(anyhow!("JavaScript execution error: {}", err_text));
            }
        }

        // Extract value from BiDi script result format
        if let Some(result_obj) = res.get("result") {
            if let Some(val) = result_obj.get("value") {
                return Ok(val.clone());
            }
        }
        Ok(res)
    }

    pub async fn capture_screenshot(&mut self) -> Result<Vec<u8>> {
        let ctx = self.context_id.as_ref().context("No active browsing context")?;
        let res = self.send_cmd("browsingContext.captureScreenshot", json!({
            "context": ctx
        })).await?;

        let b64 = res.get("data")
            .and_then(|d| d.as_str())
            .context("Missing screenshot base64 data")?;

        use base64::Engine;
        let bytes = base64::engine::general_purpose::STANDARD.decode(b64)?;
        Ok(bytes)
    }
}
