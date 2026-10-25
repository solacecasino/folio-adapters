//! Rich Content: lists and links for Folio.
//!
//! Folio already draws, edits and prints list items and links (Tab indents a
//! list item, Enter continues the list, Cmd/Ctrl-click opens a link). This
//! adapter adds the commands that make them, using the adapter protocol
//! (docs/adapters.md in the Folio repo): `doc.get` for the selection,
//! `doc.set_list`, `doc.set_link` and `ui.prompt`.

use std::collections::VecDeque;
use std::io::{BufRead, Write};

use serde_json::{Value, json};

/// Talks to Folio over stdin and stdout, one JSON message per line.
struct Folio<R> {
    input: R,
    next_id: u64,
    /// Messages that arrived while waiting for a reply.
    backlog: VecDeque<Value>,
}

impl<R: BufRead> Folio<R> {
    fn send(&self, message: Value) {
        let mut out = std::io::stdout().lock();
        let _ = writeln!(out, "{message}");
        let _ = out.flush();
    }

    fn read(&mut self) -> Option<Value> {
        let mut line = String::new();
        loop {
            line.clear();
            if self.input.read_line(&mut line).ok()? == 0 {
                return None;
            }
            if let Ok(v) = serde_json::from_str(line.trim()) {
                return Some(v);
            }
        }
    }

    /// Sends a request and waits for its answer.
    fn request(&mut self, method: &str, params: Value) -> Result<Value, String> {
        self.next_id += 1;
        let id = self.next_id;
        self.send(json!({ "id": id, "method": method, "params": params }));
        loop {
            let message = self.read().ok_or("Folio closed the connection")?;
            if message["id"] == id && message.get("method").is_none() {
                return match message.get("error") {
                    Some(e) => Err(e.as_str().unwrap_or("error").to_owned()),
                    None => Ok(message["result"].clone()),
                };
            }
            self.backlog.push_back(message);
        }
    }

    fn notify(&mut self, text: &str) {
        let _ = self.request("notify", json!({ "text": text }));
    }

    fn next(&mut self) -> Option<Value> {
        self.backlog.pop_front().or_else(|| self.read())
    }
}

/// The paragraphs the selection (or the caret) is in.
fn selected_paragraphs(doc: &Value) -> (u64, u64) {
    let para = |v: &Value| v["para"].as_u64().unwrap_or(0);
    match doc["selection"].as_object() {
        Some(s) => (para(&s["start"]), para(&s["end"])),
        None => (para(&doc["cursor"]), para(&doc["cursor"])),
    }
}

/// Bulleted or numbered list on, or off if every selected paragraph
/// already is one. Levels are kept when switching kinds.
fn toggle_list<R: BufRead>(folio: &mut Folio<R>, kind: &str) -> Result<(), String> {
    let doc = folio.request("doc.get", json!({}))?;
    let (from, to) = selected_paragraphs(&doc);
    let paragraphs = doc["paragraphs"].as_array().cloned().unwrap_or_default();
    let selected: Vec<&Value> = paragraphs.iter().skip(from as usize).take((to - from + 1) as usize).collect();
    let all_this_kind = !selected.is_empty() && selected.iter().all(|p| p["list"]["kind"] == kind);
    if all_this_kind {
        folio.request("doc.set_list", json!({ "list": null, "from": from, "to": to }))?;
        return Ok(());
    }
    // One request per paragraph keeps each one's level, as one undo step each.
    let levels: Vec<u64> = selected.iter().map(|p| p["list"]["level"].as_u64().unwrap_or(0)).collect();
    if levels.iter().all(|l| *l == levels[0]) {
        folio.request("doc.set_list", json!({ "list": { "kind": kind, "level": levels[0] }, "from": from, "to": to }))?;
    } else {
        for (i, level) in levels.iter().enumerate() {
            let p = from + i as u64;
            folio.request("doc.set_list", json!({ "list": { "kind": kind, "level": level }, "from": p, "to": p }))?;
        }
    }
    Ok(())
}

/// The URL already on the selection's first character, if any.
fn link_at(doc: &Value, para: usize, ch: usize) -> Option<String> {
    let mut at = 0;
    for run in doc["paragraphs"][para]["runs"].as_array()? {
        let len = run["text"].as_str()?.chars().count();
        if ch < at + len {
            return run["link"].as_str().map(str::to_owned);
        }
        at += len;
    }
    None
}

/// What people type, as a link: adds https:// or mailto: when it's left off.
pub fn normalize(url: &str) -> String {
    let url = url.trim();
    let has_scheme = url.split_once(':').is_some_and(|(s, _)| !s.is_empty() && s.chars().all(|c| c.is_ascii_alphabetic()));
    if has_scheme {
        url.to_owned()
    } else if url.contains('@') && !url.contains('/') {
        format!("mailto:{url}")
    } else {
        format!("https://{url}")
    }
}

fn add_link<R: BufRead>(folio: &mut Folio<R>) -> Result<(), String> {
    let doc = folio.request("doc.get", json!({}))?;
    let Some(start) = doc["selection"]["start"].as_object() else {
        folio.notify("Select the text you want to link first.");
        return Ok(());
    };
    let (para, ch) = (start["para"].as_u64().unwrap_or(0) as usize, start["ch"].as_u64().unwrap_or(0) as usize);
    let current = link_at(&doc, para, ch);
    let answer = folio.request(
        "ui.prompt",
        json!({
            "title": "Link",
            "message": "Link the selected text to (leave empty to remove the link):",
            "default": current.unwrap_or_else(|| "https://".into()),
        }),
    )?;
    let Some(url) = answer.as_str() else { return Ok(()) }; // cancelled
    let url = url.trim();
    let url = if url.is_empty() || url == "https://" { Value::Null } else { json!(normalize(url)) };
    folio.request("doc.set_link", json!({ "url": url }))?;
    Ok(())
}

fn main() {
    let stdin = std::io::stdin();
    let mut folio = Folio {
        input: stdin.lock(),
        next_id: 0,
        backlog: VecDeque::new(),
    };
    while let Some(message) = folio.next() {
        let result = match message["method"].as_str() {
            Some("command") => match message["params"]["command"].as_str() {
                Some("bullets") => toggle_list(&mut folio, "bullet"),
                Some("numbers") => toggle_list(&mut folio, "numbered"),
                Some("link") => add_link(&mut folio),
                Some("unlink") => folio.request("doc.set_link", json!({ "url": null })).map(|_| ()),
                _ => Ok(()),
            },
            Some("shutdown") => break,
            _ => Ok(()),
        };
        if let Err(e) = result {
            folio.notify(&format!("Rich Content: {e}"));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn links_get_a_scheme() {
        assert_eq!(normalize("example.com"), "https://example.com");
        assert_eq!(normalize(" https://a.b/c "), "https://a.b/c");
        assert_eq!(normalize("me@example.com"), "mailto:me@example.com");
        assert_eq!(normalize("mailto:me@example.com"), "mailto:me@example.com");
    }

    #[test]
    fn finds_the_link_under_the_selection() {
        let doc = json!({ "paragraphs": [{ "style": "body", "runs": [
            { "text": "See " }, { "text": "the site", "link": "https://x.y" }] }] });
        assert_eq!(link_at(&doc, 0, 5).as_deref(), Some("https://x.y"));
        assert_eq!(link_at(&doc, 0, 1), None);
    }
}
