// Decide which edits look like AI-generated or pasted code. VS Code gives extensions no direct
// signal that a suggestion was accepted, so we use the size of a single insertion as a proxy:
// typing adds one character at a time, an accepted suggestion or a paste adds a block at once.

export interface Change {
  text: string;
  rangeLength: number; // characters replaced
}

export const MIN_CHARS = 60;
export const MIN_LINES = 3;

export function looksLikeBlockInsertion(change: Change): boolean {
  const lines = change.text.split(/\r?\n/).length;
  return change.text.length >= MIN_CHARS && (lines >= MIN_LINES || change.text.length >= 200);
}

export function insertedLineRange(startLine: number, text: string): [number, number] {
  const count = text.split(/\r?\n/).length;
  return [startLine, startLine + count - 1];
}
