//! Runs the adapter the way Folio does and plays Folio's side.

use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

use serde_json::{Value, json};

struct Adapter {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

impl Adapter {
    fn start() -> Self {
        let mut child = Command::new(env!("CARGO_BIN_EXE_rich-content"))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        let stdin = child.stdin.take().unwrap();
        let stdout = BufReader::new(child.stdout.take().unwrap());
        let mut a = Self { child, stdin, stdout };
        a.send(json!({ "method": "initialize", "params": { "folio": "1.0.2", "protocol": 5 } }));
        a
    }

    fn send(&mut self, v: Value) {
        writeln!(self.stdin, "{v}").unwrap();
    }

    fn recv(&mut self) -> Value {
        let mut line = String::new();
        self.stdout.read_line(&mut line).unwrap();
        serde_json::from_str(&line).unwrap()
    }

    fn command(&mut self, id: &str) {
        self.send(json!({ "method": "command", "params": { "command": id } }));
    }

    /// Expects a request and answers it.
    fn answer(&mut self, method: &str, result: Value) -> Value {
        let req = self.recv();
        assert_eq!(req["method"], method, "{req}");
        self.send(json!({ "id": req["id"], "result": result }));
        req["params"].clone()
    }
}

impl Drop for Adapter {
    fn drop(&mut self) {
        self.send(json!({ "method": "shutdown" }));
        let _ = self.child.wait();
    }
}

fn doc(paragraphs: Value, selection: Value) -> Value {
    json!({ "folio": 1, "paragraphs": paragraphs, "cursor": { "para": 0, "ch": 0 },
            "anchor": { "para": 0, "ch": 0 }, "selection": selection })
}

#[test]
fn lists_turn_on_and_off() {
    let mut a = Adapter::start();
    let plain = json!([{ "style": "body", "runs": [{ "text": "One" }] }, { "style": "body", "runs": [{ "text": "Two" }] }]);
    let both = json!({ "start": { "para": 0, "ch": 0 }, "end": { "para": 1, "ch": 2 } });

    a.command("bullets");
    a.answer("doc.get", doc(plain, both.clone()));
    let set = a.answer("doc.set_list", Value::Null);
    assert_eq!(set, json!({ "list": { "kind": "bullet", "level": 0 }, "from": 0, "to": 1 }));

    // Already bullets: the same command turns them off.
    let bullets = json!([{ "style": "body", "list": { "kind": "bullet", "level": 0 }, "runs": [] },
                         { "style": "body", "list": { "kind": "bullet", "level": 0 }, "runs": [] }]);
    a.command("bullets");
    a.answer("doc.get", doc(bullets.clone(), both.clone()));
    assert_eq!(a.answer("doc.set_list", Value::Null)["list"], Value::Null);

    // Switching to numbers keeps the level.
    let nested = json!([{ "style": "body", "list": { "kind": "bullet", "level": 2 }, "runs": [] }]);
    a.command("numbers");
    a.answer("doc.get", doc(nested, Value::Null));
    let set = a.answer("doc.set_list", Value::Null);
    assert_eq!(set["list"], json!({ "kind": "numbered", "level": 2 }));
}

#[test]
fn links_ask_for_a_url() {
    let mut a = Adapter::start();
    let text = json!([{ "style": "body", "runs": [{ "text": "See the site" }] }]);
    let sel = json!({ "start": { "para": 0, "ch": 4 }, "end": { "para": 0, "ch": 12 } });

    a.command("link");
    a.answer("doc.get", doc(text.clone(), sel.clone()));
    let prompt = a.answer("ui.prompt", json!("example.com"));
    assert_eq!(prompt["default"], "https://");
    assert_eq!(a.answer("doc.set_link", Value::Null), json!({ "url": "https://example.com" }));

    // Cancelling does nothing; with no selection it explains instead.
    a.command("link");
    a.answer("doc.get", doc(text.clone(), sel));
    a.answer("ui.prompt", Value::Null);
    a.command("link");
    a.answer("doc.get", doc(text, Value::Null));
    let note = a.answer("notify", Value::Null);
    assert!(note["text"].as_str().unwrap().contains("Select"));

    a.command("unlink");
    assert_eq!(a.answer("doc.set_link", Value::Null), json!({ "url": null }));
}
