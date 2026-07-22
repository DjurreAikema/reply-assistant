import { Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatRippleModule } from '@angular/material/core';

import { ApiService } from '../api.service';
import { Candidate, ExtractedField, Message } from '../models';

type Phase = 'idle' | 'suggesting' | 'suggested' | 'drafting' | 'drafted' | 'sending' | 'sent';

const TOKEN_RE = /\{\{\s*(\w+)\s*\}\}/g;

@Component({
  selector: 'app-ai-panel',
  imports: [FormsModule, MatButtonModule, MatProgressBarModule, MatRippleModule],
  templateUrl: './ai-panel.html',
  styleUrl: './ai-panel.scss',
})
export class AiPanel {
  private api = inject(ApiService);

  message = input<Message | null>(null);
  // Owned by the inbox page and edited in the review panel; consumed
  // here for draft substitution and send gating.
  fields = input<ExtractedField[]>([]);
  fieldsChange = output<ExtractedField[]>();
  // Which field keys matter right now: the union of the candidates'
  // placeholders until a template is picked, then just the chosen one's.
  // The review panel uses this to foreground what actually needs review.
  requiredKeysChange = output<string[]>();
  replied = output<string>();

  phase = signal<Phase>('idle');
  candidates = signal<Candidate[]>([]);
  selectedTemplateId = signal<string | null>(null);
  lowConfidence = signal(false);
  // rawDraft is the model output with its {{tokens}} intact. The visible
  // draft is recomputed from rawDraft plus the current field values on
  // every field edit, never patched in place, so stale or short values
  // can never corrupt it. Once the agent types in the textarea the
  // substitution stops and their text is left alone.
  rawDraft = signal('');
  draft = signal('');
  manualEdit = signal(false);
  error = signal<string | null>(null);

  selectedCandidate = computed(
    () => this.candidates().find((c) => c.template_id === this.selectedTemplateId()) ?? null,
  );

  // Primary send gate: the chosen template's declared placeholders must
  // all have a non-empty field value. The draft text is not trusted for
  // this, the model may have dropped a token entirely while rewriting.
  missingFields = computed(() => {
    const candidate = this.selectedCandidate();
    if (!candidate) return [];
    const values = new Map(this.fields().map((f) => [f.key, f.value]));
    return candidate.placeholders.filter((p) => !(values.get(p) ?? '').trim());
  });

  // Secondary backstop: whatever the data says, a literal {{token}} in
  // the outgoing text never gets sent.
  leftoverTokens = computed(() => {
    const found = new Set<string>();
    for (const match of this.draft().matchAll(TOKEN_RE)) {
      found.add(match[1]);
    }
    return [...found];
  });

  sendBlockReason = computed(() => {
    const missing = this.missingFields();
    if (missing.length) {
      return `Fill in ${missing.map((k) => this.label(k)).join(', ')} before sending`;
    }
    const leftover = this.leftoverTokens();
    if (leftover.length) {
      return `The draft still contains the unfilled placeholder ${leftover
        .map((k) => this.label(k))
        .join(', ')}`;
    }
    return null;
  });

  constructor() {
    // Selecting a message is the trigger for suggestions, no extra click.
    // The message id is captured so a slow response for a previous email
    // cannot land in the panel after switching to another one.
    effect(() => {
      const msg = this.message();
      this.reset();
      if (!msg || msg.isReplied) {
        if (msg?.isReplied) this.phase.set('sent');
        return;
      }
      this.phase.set('suggesting');
      const requestedId = msg.id;
      this.api.suggest(requestedId).subscribe({
        next: (res) => {
          if (this.message()?.id !== requestedId) return;
          this.candidates.set(res.candidates);
          this.lowConfidence.set(res.low_confidence);
          this.fieldsChange.emit(res.fields);
          this.requiredKeysChange.emit([...new Set(res.candidates.flatMap((c) => c.placeholders))]);
          this.phase.set('suggested');
          // Top candidate is expanded by default; the draft itself still
          // waits for an explicit choice so the flow stays two clicks.
        },
        error: (err) => this.fail(requestedId, err),
      });
    });

    // Displayed draft is a pure function of rawDraft plus field values,
    // until the agent edits by hand.
    effect(() => {
      const raw = this.rawDraft();
      const fields = this.fields();
      if (this.manualEdit()) return;
      this.draft.set(this.substitute(raw, fields));
    });
  }

  pick(candidate: Candidate): void {
    const msg = this.message();
    if (!msg || this.phase() === 'drafting' || this.phase() === 'sending') return;
    this.selectedTemplateId.set(candidate.template_id);
    this.requiredKeysChange.emit([...candidate.placeholders]);
    this.phase.set('drafting');
    this.error.set(null);
    const requestedId = msg.id;
    this.api.draft(requestedId, candidate.template_id).subscribe({
      next: (res) => {
        if (this.message()?.id !== requestedId) return;
        this.manualEdit.set(false);
        this.rawDraft.set(res.body);
        this.phase.set('drafted');
      },
      error: (err) => this.fail(requestedId, err),
    });
  }

  onDraftEdited(value: string): void {
    this.manualEdit.set(true);
    this.draft.set(value);
  }

  send(): void {
    const msg = this.message();
    if (!msg || !this.draft().trim() || this.sendBlockReason()) return;
    this.phase.set('sending');
    this.error.set(null);
    this.api.send(msg.id, this.draft(), this.selectedTemplateId()).subscribe({
      next: () => {
        this.phase.set('sent');
        this.replied.emit(msg.id);
      },
      error: (err) => this.fail(msg.id, err),
    });
  }

  confidencePercent(candidate: Candidate): number {
    return Math.round(candidate.confidence * 100);
  }

  label(key: string): string {
    return key.replace(/_/g, ' ');
  }

  private substitute(raw: string, fields: ExtractedField[]): string {
    return raw.replace(TOKEN_RE, (token, key: string) => {
      const value = fields.find((f) => f.key === key)?.value.trim();
      return value ? value : token;
    });
  }

  private reset(): void {
    this.phase.set('idle');
    this.candidates.set([]);
    this.selectedTemplateId.set(null);
    this.lowConfidence.set(false);
    this.rawDraft.set('');
    this.draft.set('');
    this.manualEdit.set(false);
    this.error.set(null);
    this.fieldsChange.emit([]);
    this.requiredKeysChange.emit([]);
  }

  private fail(requestedId: string, err: { error?: { error?: string } }): void {
    if (this.message()?.id !== requestedId) return;
    this.error.set(err.error?.error ?? 'The request failed. Check that the backend is running.');
    this.phase.set(this.candidates().length ? 'suggested' : 'idle');
  }
}
