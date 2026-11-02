use std::path::PathBuf;
use anyhow::Result;
use regex::Regex;
use serde_json::Value;

pub const SCRAPER_SCRIPT: &str = include_str!("../../../src/browser/scraper_extractor.js");
pub const DOM_EXTRACTOR_SCRIPT: &str = include_str!("../../../src/browser/dom_extractor.js");

pub struct Scraper;

impl Scraper {
    pub fn format_markdown(data: &Value) -> String {
        let title = data.get("title").and_then(|t| t.as_str()).unwrap_or("Untitled Page");
        let url = data.get("url").and_then(|u| u.as_str()).unwrap_or("");
        let scraped_at = data.get("scraped_at").and_then(|s| s.as_str()).unwrap_or("");
        let empty_vec = vec![];
        let blocks = data.get("blocks").and_then(|b| b.as_array()).unwrap_or(&empty_vec);

        // Word count
        let mut total_words = 0;
        for b in blocks {
            if let Some(text) = b.get("text").and_then(|t| t.as_str()) {
                total_words += text.split_whitespace().count();
            }
        }
        let reading_time = std::cmp::max(1, total_words / 200);

        let mut lines = Vec::new();
        lines.push("---".to_string());
        lines.push(format!("title: \"{}\"", title.replace('\"', "\\\"")));
        lines.push(format!("url: \"{}\"", url));
        lines.push(format!("scraped_at: \"{}\"", scraped_at));
        lines.push(format!("word_count: {}", total_words));
        lines.push(format!("reading_time_min: {}", reading_time));
        lines.push("---".to_string());
        lines.push("".to_string());
        lines.push(format!("# {}", title));
        lines.push("".to_string());
        lines.push(format!("> Source: [{}]({}) | Scraped: {}", url, url, &scraped_at.chars().take(10).collect::<String>()));
        lines.push("".to_string());

        for b in blocks {
            let b_type = b.get("type").and_then(|t| t.as_str()).unwrap_or("");
            match b_type {
                "heading" => {
                    let level = b.get("level").and_then(|l| l.as_u64()).unwrap_or(2).min(6).max(1);
                    let prefix = "#".repeat(level as usize);
                    let text = b.get("text").and_then(|t| t.as_str()).unwrap_or("");
                    lines.push(format!("{} {}\n", prefix, text));
                }
                "paragraph" => {
                    let text = b.get("text").and_then(|t| t.as_str()).unwrap_or("");
                    lines.push(format!("{}\n", text));
                }
                "code" => {
                    let lang = b.get("language").and_then(|l| l.as_str()).unwrap_or("");
                    let code = b.get("text").and_then(|c| c.as_str()).unwrap_or("");
                    lines.push(format!("```{}\n{}\n```\n", lang, code));
                }
                "quote" => {
                    let text = b.get("text").and_then(|t| t.as_str()).unwrap_or("");
                    lines.push(format!("> {}\n", text));
                }
                "list" => {
                    let ordered = b.get("ordered").and_then(|o| o.as_bool()).unwrap_or(false);
                    if let Some(items) = b.get("items").and_then(|i| i.as_array()) {
                        for (idx, item) in items.iter().enumerate() {
                            let item_text = item.as_str().unwrap_or("");
                            if ordered {
                                lines.push(format!("{}. {}", idx + 1, item_text));
                            } else {
                                lines.push(format!("* {}", item_text));
                            }
                        }
                        lines.push("".to_string());
                    }
                }
                "table" => {
                    if let Some(rows) = b.get("rows").and_then(|r| r.as_array()) {
                        if !rows.is_empty() {
                            let mut table_rows: Vec<Vec<String>> = Vec::new();
                            let mut max_cols = 0;
                            for r in rows {
                                if let Some(cells) = r.as_array() {
                                    let row_cells: Vec<String> = cells.iter().map(|c| c.as_str().unwrap_or("").to_string()).collect();
                                    max_cols = max_cols.max(row_cells.len());
                                    table_rows.push(row_cells);
                                }
                            }
                            if let Some(header) = table_rows.first() {
                                lines.push(format!("| {} |", header.join(" | ")));
                                lines.push(format!("| {} |", vec!["---"; max_cols].join(" | ")));
                                for r in table_rows.iter().skip(1) {
                                    lines.push(format!("| {} |", r.join(" | ")));
                                }
                                lines.push("".to_string());
                            }
                        }
                    }
                }
                _ => {}
            }
        }

        lines.join("\n")
    }

    pub fn save_markdown(content: &str, title: &str, output_path: Option<&str>) -> Result<PathBuf> {
        let path = if let Some(p) = output_path {
            PathBuf::from(p)
        } else {
            let re = Regex::new(r"[^\w\s-]")?;
            let clean = re.replace_all(title, "").to_lowercase();
            let re_space = Regex::new(r"[-\s]+")?;
            let slug = re_space.replace_all(&clean, "-").trim_matches('-').to_string();
            let slug = if slug.is_empty() { "page".to_string() } else { slug.chars().take(60).collect() };

            let scrapes_dir = PathBuf::from("scrapes");
            std::fs::create_dir_all(&scrapes_dir)?;

            let mut target = scrapes_dir.join(format!("{}.md", slug));
            let mut counter = 1;
            while target.exists() {
                target = scrapes_dir.join(format!("{}-{}.md", slug, counter));
                counter += 1;
            }
            target
        };

        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(&path, content)?;
        Ok(path)
    }
}
