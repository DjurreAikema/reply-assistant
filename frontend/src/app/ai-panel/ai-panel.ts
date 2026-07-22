import { Component, effect, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatRippleModule } from '@angular/material/core';

import { ApiService } from '../api.service';
import { Candidate, Message } from '../models';

type Phase = 'idle' | 'suggesting' | 'suggested' | 'drafting' | 'drafted' | 'sending' | 'sent';

@Component({
  selector: 'app-ai-panel',
  imports: [FormsModule, MatButtonModule, MatProgressBarModule, MatRippleModule],
  templateUrl: './ai-panel.html',
  styleUrl: './ai-panel.scss',
})
export class AiPanel {
  private api = inject(ApiService);

  message = input<Message | null>(null);
  replied = output<string>();

  phase = signal<Phase>('idle');
  candidates = signal<Candidate[]>([]);
  selectedTemplateId = signal<string | null>(null);
  draft = signal('');
  error = signal<string | null>(null);

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
          this.phase.set('suggested');
          // Top candidate is expanded by default; the draft itself still
          // waits for an explicit choice so the flow stays two clicks.
        },
        error: (err) => this.fail(requestedId, err),
      });
    });
  }

  pick(candidate: Candidate): void {
    const msg = this.message();
    if (!msg || this.phase() === 'drafting' || this.phase() === 'sending') return;
    this.selectedTemplateId.set(candidate.template_id);
    this.phase.set('drafting');
    this.error.set(null);
    const requestedId = msg.id;
    this.api.draft(requestedId, candidate.template_id).subscribe({
      next: (res) => {
        if (this.message()?.id !== requestedId) return;
        this.draft.set(res.body);
        this.phase.set('drafted');
      },
      error: (err) => this.fail(requestedId, err),
    });
  }

  send(): void {
    const msg = this.message();
    if (!msg || !this.draft().trim()) return;
    this.phase.set('sending');
    this.error.set(null);
    this.api.send(msg.id, this.draft()).subscribe({
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

  private reset(): void {
    this.phase.set('idle');
    this.candidates.set([]);
    this.selectedTemplateId.set(null);
    this.draft.set('');
    this.error.set(null);
  }

  private fail(requestedId: string, err: { error?: { error?: string } }): void {
    if (this.message()?.id !== requestedId) return;
    this.error.set(err.error?.error ?? 'The request failed. Check that the backend is running.');
    this.phase.set(this.candidates().length ? 'suggested' : 'idle');
  }
}
