"use client";

let nextId = 0;
export function newId(): string {
  nextId += 1;
  return `row-${nextId}-${Date.now()}`;
}

export type ContentEntry = { id: string; component: string; content: string };
export type OutcomeEntry = { id: string; group: string; outcome: "approved" | "denied" };
export type ReviewEntry = { id: string; decision: "approved" | "denied"; seconds: string };

export function buildLogsPayload(
  contentEntries: ContentEntry[],
  outcomeEntries: OutcomeEntry[],
  reviewEntries: ReviewEntry[]
): Record<string, unknown>[] {
  const logs: Record<string, unknown>[] = [];

  for (const c of contentEntries) {
    if (c.content.trim()) {
      logs.push({ component: c.component.trim() || "unknown", content: c.content.trim() });
    }
  }
  for (const o of outcomeEntries) {
    if (o.group.trim()) {
      logs.push({ demographic_group: o.group.trim(), outcome: o.outcome });
    }
  }
  for (const r of reviewEntries) {
    const seconds = Number(r.seconds);
    if (!Number.isNaN(seconds)) {
      logs.push({ event: "human_review", decision: r.decision, time_to_approve_seconds: seconds });
    }
  }

  return logs;
}

const inputClass =
  "w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm placeholder:text-slate-600";
const selectClass = "rounded-md bg-slate-900 border border-slate-700 px-2 py-2 text-sm";
const removeButtonClass =
  "shrink-0 rounded-md border border-slate-700 px-2 py-2 text-xs text-slate-400 hover:text-red-300 hover:border-red-500/40";
const addButtonClass =
  "rounded-md border border-dashed border-slate-700 px-3 py-2 text-xs text-slate-400 hover:text-slate-200 hover:border-slate-500";

export function ContentLogSection({
  entries,
  onChange,
}: {
  entries: ContentEntry[];
  onChange: (entries: ContentEntry[]) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-200">Messages &amp; user input</h3>
      <p className="mt-1 text-xs text-slate-500">
        Anything a user typed or the system logged as text — chat messages, form fields, API
        payloads. Checked for PII exposure and prompt-injection / jailbreak attempts.
      </p>
      <div className="mt-3 space-y-2">
        {entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-start">
            <input
              className={`${inputClass} w-40 shrink-0`}
              placeholder="source (e.g. chat_widget)"
              value={entry.component}
              onChange={(e) =>
                onChange(entries.map((x) => (x.id === entry.id ? { ...x, component: e.target.value } : x)))
              }
            />
            <textarea
              className={`${inputClass} h-16`}
              placeholder="What was said or submitted…"
              value={entry.content}
              onChange={(e) =>
                onChange(entries.map((x) => (x.id === entry.id ? { ...x, content: e.target.value } : x)))
              }
            />
            <button
              type="button"
              className={removeButtonClass}
              onClick={() => onChange(entries.filter((x) => x.id !== entry.id))}
              aria-label="Remove entry"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        className={`${addButtonClass} mt-2`}
        onClick={() => onChange([...entries, { id: newId(), component: "", content: "" }])}
      >
        + Add message
      </button>
    </div>
  );
}

export function OutcomeLogSection({
  entries,
  onChange,
}: {
  entries: OutcomeEntry[];
  onChange: (entries: OutcomeEntry[]) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-200">Decision outcomes</h3>
      <p className="mt-1 text-xs text-slate-500">
        One row per decision the AI made about a person, with the group they belong to. Checked for
        demographic skew in outcomes.
      </p>
      <div className="mt-3 space-y-2">
        {entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <input
              className={`${inputClass} w-48`}
              placeholder="group (e.g. Region A)"
              value={entry.group}
              onChange={(e) =>
                onChange(entries.map((x) => (x.id === entry.id ? { ...x, group: e.target.value } : x)))
              }
            />
            <select
              className={selectClass}
              value={entry.outcome}
              onChange={(e) =>
                onChange(
                  entries.map((x) =>
                    x.id === entry.id ? { ...x, outcome: e.target.value as OutcomeEntry["outcome"] } : x
                  )
                )
              }
            >
              <option value="approved">approved</option>
              <option value="denied">denied</option>
            </select>
            <button
              type="button"
              className={removeButtonClass}
              onClick={() => onChange(entries.filter((x) => x.id !== entry.id))}
              aria-label="Remove entry"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        className={`${addButtonClass} mt-2`}
        onClick={() => onChange([...entries, { id: newId(), group: "", outcome: "denied" }])}
      >
        + Add decision
      </button>
    </div>
  );
}

export function ReviewLogSection({
  entries,
  onChange,
}: {
  entries: ReviewEntry[];
  onChange: (entries: ReviewEntry[]) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-200">Human review events</h3>
      <p className="mt-1 text-xs text-slate-500">
        One row per time a human reviewed and approved/rejected an AI action, and how long it took
        them. Checked for automation bias / rubber-stamping.
      </p>
      <div className="mt-3 space-y-2">
        {entries.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <select
              className={selectClass}
              value={entry.decision}
              onChange={(e) =>
                onChange(
                  entries.map((x) =>
                    x.id === entry.id ? { ...x, decision: e.target.value as ReviewEntry["decision"] } : x
                  )
                )
              }
            >
              <option value="approved">approved</option>
              <option value="denied">denied</option>
            </select>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.1"
                min="0"
                className={`${inputClass} w-28`}
                placeholder="seconds"
                value={entry.seconds}
                onChange={(e) =>
                  onChange(entries.map((x) => (x.id === entry.id ? { ...x, seconds: e.target.value } : x)))
                }
              />
              <span className="text-xs text-slate-500 shrink-0">seconds to review</span>
            </div>
            <button
              type="button"
              className={removeButtonClass}
              onClick={() => onChange(entries.filter((x) => x.id !== entry.id))}
              aria-label="Remove entry"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        className={`${addButtonClass} mt-2`}
        onClick={() => onChange([...entries, { id: newId(), decision: "approved", seconds: "" }])}
      >
        + Add review event
      </button>
    </div>
  );
}
