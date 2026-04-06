"use client";

/**
 * Lightweight syntax-highlighted <pre> block.
 * Colors Python/JS/bash keywords without external dependencies.
 */
export function SyntaxPre({ code, className = "" }: { code: string; className?: string }) {
  const lines = code.split("\n");
  return (
    <pre className={className} style={{ background: "#0B0F14", color: "#e2e8f0", padding: "20px 24px", fontSize: "13px", fontFamily: "monospace", lineHeight: 1.6, overflowX: "auto", margin: 0, borderRadius: "8px" }}>
      {lines.map((line, i) => (
        <div key={i}>{colorize(line)}</div>
      ))}
    </pre>
  );
}

function colorize(line: string): React.ReactNode {
  // Comment lines
  if (/^\s*(#|\/\/)/.test(line)) return <span style={{ color: "#6b7280" }}>{line}</span>;
  // String-heavy lines
  if (/^\s*["']/.test(line.trim()) || /^\s*`/.test(line.trim())) return <span style={{ color: "#a5d6a7" }}>{line}</span>;

  // Tokenize keywords
  const parts: React.ReactNode[] = [];
  const keywords = /\b(import|from|def|async|await|return|if|elif|else|for|in|class|try|except|raise|with|as|not|and|or|True|False|None|const|let|var|function|export|new|throw|catch|print)\b/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = keywords.exec(line)) !== null) {
    if (match.index > last) parts.push(colorSegment(line.slice(last, match.index)));
    parts.push(<span key={match.index} style={{ color: "#c792ea" }}>{match[0]}</span>);
    last = match.index + match[0].length;
  }
  if (last < line.length) parts.push(colorSegment(line.slice(last)));
  if (parts.length === 0) return line;
  return <>{parts}</>;
}

function colorSegment(text: string): React.ReactNode {
  // Color strings within segment
  const parts: React.ReactNode[] = [];
  const strRe = /(["'`])(?:(?!\1).)*\1|f"(?:[^"\\]|\\.)*"/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = strRe.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    parts.push(<span key={`s${match.index}`} style={{ color: "#a5d6a7" }}>{match[0]}</span>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length > 0 ? <>{parts}</> : text;
}
