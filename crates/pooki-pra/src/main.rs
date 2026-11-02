mod launcher;
mod bidi;
mod db;
mod scraper;

use anyhow::Result;
use clap::{Parser, Subcommand};
use serde_json::json;

use launcher::CamoufoxProcess;
use bidi::BiDiClient;
use db::Database;
use scraper::Scraper;

#[derive(Parser)]
#[command(name = "pooki-pra")]
#[command(about = "Pooki-Pra: High-performance native Rust stealth browser engine", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Navigates to a URL and displays page info
    Navigate {
        url: String,
        #[arg(long, default_value = "true")]
        headless: bool,
    },
    /// Scrapes a web page to clean Markdown (.md)
    Scrape {
        url: String,
        #[arg(short, long)]
        output: Option<String>,
        #[arg(long, default_value = "readability")]
        mode: String,
    },
    /// Takes a screenshot of a webpage
    Screenshot {
        url: String,
        output: String,
    },
    /// Runs as an MCP (Model Context Protocol) stdio JSON-RPC server
    Mcp,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Navigate { url, headless } => {
            println!("🚀 Launching Camoufox BiDi engine...");
            let proc = CamoufoxProcess::spawn(headless, None).await?;
            let mut client = BiDiClient::connect(&proc.ws_url).await?;

            println!("🌐 Navigating to {} ...", url);
            client.navigate(&url).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

            let title_val = client.evaluate_script("document.title").await?;
            let title = title_val.as_str().unwrap_or("Unknown");
            println!("✅ Successfully landed on: {}", title);

            let db = Database::new()?;
            db.record_action("cli_session", 1, &url, title, "NAVIGATE")?;
        }

        Commands::Scrape { url, output, mode } => {
            println!("🚀 Launching Camoufox BiDi engine...");
            let proc = CamoufoxProcess::spawn(true, None).await?;
            let mut client = BiDiClient::connect(&proc.ws_url).await?;

            println!("🌐 Navigating to {} ...", url);
            client.navigate(&url).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;

            println!("📄 Extracting semantic DOM blocks (mode: {})...", mode);
            let script = format!(
                "window.__scrape_mode = '{}';\n{}",
                mode,
                scraper::SCRAPER_SCRIPT
            );
            let extracted_raw = client.evaluate_script(&script).await?;
            let extracted: serde_json::Value = if let Some(s) = extracted_raw.as_str() {
                serde_json::from_str(s)?
            } else {
                extracted_raw
            };
            let markdown = Scraper::format_markdown(&extracted);

            let title = extracted.get("title").and_then(|t| t.as_str()).unwrap_or("page");
            let saved_path = Scraper::save_markdown(&markdown, title, output.as_deref())?;

            let word_count = markdown.split_whitespace().count();
            println!("✅ Scraped and saved to: {:?}", saved_path);
            println!("📊 Word count: {}", word_count);

            let db = Database::new()?;
            db.record_scrape(&url, title, saved_path.to_str().unwrap_or(""), word_count, "default")?;
        }

        Commands::Screenshot { url, output } => {
            println!("🚀 Launching Camoufox BiDi engine...");
            let proc = CamoufoxProcess::spawn(true, None).await?;
            let mut client = BiDiClient::connect(&proc.ws_url).await?;

            println!("🌐 Navigating to {} ...", url);
            client.navigate(&url).await?;

            println!("📸 Capturing screenshot...");
            let png_bytes = client.capture_screenshot().await?;
            std::fs::write(&output, png_bytes)?;
            println!("✅ Screenshot saved to: {}", output);
        }

        Commands::Mcp => {
            run_mcp_server().await?;
        }
    }

    Ok(())
}

async fn run_mcp_server() -> Result<()> {
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    let stdin = tokio::io::stdin();
    let mut stdout = tokio::io::stdout();
    let mut reader = BufReader::new(stdin);
    let mut line = String::new();

    let mut browser_proc: Option<CamoufoxProcess> = None;
    let mut bidi_client: Option<BiDiClient> = None;

    while reader.read_line(&mut line).await? > 0 {
        let req_text = line.trim();
        if req_text.is_empty() {
            line.clear();
            continue;
        }

        if let Ok(req) = serde_json::from_str::<serde_json::Value>(req_text) {
            let id = req.get("id").cloned();
            let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");

            match method {
                "initialize" => {
                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": { "tools": { "listChanged": false } },
                            "serverInfo": { "name": "pooki-pra", "version": "0.1.0" }
                        }
                    });
                    stdout.write_all(format!("{}\n", resp).as_bytes()).await?;
                    stdout.flush().await?;
                }

                "tools/list" => {
                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "tools": [
                                {
                                    "name": "browser_navigate",
                                    "description": "Navigates native Camoufox BiDi engine to a URL",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": { "url": { "type": "string" } },
                                        "required": ["url"]
                                    }
                                },
                                {
                                    "name": "browser_scrape",
                                    "description": "Converts web page into clean Markdown (.md)",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "url": { "type": "string" },
                                            "output_path": { "type": "string" }
                                        }
                                    }
                                }
                            ]
                        }
                    });
                    stdout.write_all(format!("{}\n", resp).as_bytes()).await?;
                    stdout.flush().await?;
                }

                "tools/call" => {
                    let params = req.get("params").cloned().unwrap_or(json!({}));
                    let name = params.get("name").and_then(|n| n.as_str()).unwrap_or("");
                    let args = params.get("arguments").cloned().unwrap_or(json!({}));

                    // Ensure browser is running
                    if browser_proc.is_none() {
                        let proc = CamoufoxProcess::spawn(true, None).await?;
                        let client = BiDiClient::connect(&proc.ws_url).await?;
                        browser_proc = Some(proc);
                        bidi_client = Some(client);
                    }

                    let client = bidi_client.as_mut().unwrap();

                    let tool_result = match name {
                        "browser_navigate" => {
                            let url = args.get("url").and_then(|u| u.as_str()).unwrap_or("");
                            client.navigate(url).await?;
                            let title = client.evaluate_script("document.title").await?;
                            json!({ "url": url, "title": title })
                        }
                        "browser_scrape" => {
                            let url = args.get("url").and_then(|u| u.as_str()).unwrap_or("");
                            let out_path = args.get("output_path").and_then(|p| p.as_str());
                            if !url.is_empty() {
                                client.navigate(url).await?;
                                tokio::time::sleep(tokio::time::Duration::from_millis(1500)).await;
                            }
                            let script = format!("window.__scrape_mode = 'readability';\n{}", scraper::SCRAPER_SCRIPT);
                            let extracted_raw = client.evaluate_script(&script).await?;
                            let extracted: serde_json::Value = if let Some(s) = extracted_raw.as_str() {
                                serde_json::from_str(s).unwrap_or(extracted_raw)
                            } else {
                                extracted_raw
                            };
                            let markdown = Scraper::format_markdown(&extracted);
                            let title = extracted.get("title").and_then(|t| t.as_str()).unwrap_or("page");
                            let saved_path = Scraper::save_markdown(&markdown, title, out_path)?;
                            json!({
                                "status": "scraped",
                                "title": title,
                                "file_path": saved_path.to_str().unwrap_or(""),
                                "word_count": markdown.split_whitespace().count()
                            })
                        }
                        _ => json!({ "error": format!("Unknown tool: {}", name) })
                    };

                    let resp = json!({
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{ "type": "text", "text": tool_result.to_string() }]
                        }
                    });
                    stdout.write_all(format!("{}\n", resp).as_bytes()).await?;
                    stdout.flush().await?;
                }

                _ => {}
            }
        }
        line.clear();
    }

    Ok(())
}
