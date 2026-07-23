import { Component, computed, input, signal } from '@angular/core';
import { DatePipe } from '@angular/common';

import { ConversationItem } from '../models';

// Bodies longer than this get a show more control rather than pushing the
// rest of the thread off screen.
const CLAMP_CHARS = 420;

interface Turn {
  item: ConversationItem;
  sender: string;
  open: boolean;
  clampable: boolean;
  full: boolean;
}

@Component({
  selector: 'app-conversation-thread',
  imports: [DatePipe],
  templateUrl: './conversation-thread.html',
  styleUrl: './conversation-thread.scss',
})
export class ConversationThread {
  items = input.required<ConversationItem[]>();
  // The reply just sent from this screen, confirmed on the item itself
  // rather than on a screen that replaces the workspace.
  justSentId = input<string | null>(null);

  // Manual open/closed overrides keyed by item id. Anything not in here
  // falls back to the default rule below.
  private overrides = signal<Record<string, boolean>>({});
  private full = signal<Record<string, boolean>>({});

  subject = computed(() => this.items()[0]?.subject ?? '');

  turns = computed<Turn[]>(() => {
    const items = this.items();
    const overrides = this.overrides();
    const full = this.full();
    const lastId = items[items.length - 1]?.id;
    const lastInboundId = [...items].reverse().find((i) => i.direction === 'inbound')?.id;
    return items.map((item) => ({
      item,
      sender: item.direction === 'inbound' ? (item.from?.emailAddress.name ?? 'Customer') : 'You',
      // The newest turn and the newest inbound message are what the agent
      // is working from, so those stay open. Earlier turns fold away.
      open: overrides[item.id] ?? (item.id === lastId || item.id === lastInboundId),
      clampable: item.body.content.length > CLAMP_CHARS,
      full: full[item.id] ?? false,
    }));
  });

  toggle(turn: Turn): void {
    this.overrides.update((current) => ({ ...current, [turn.item.id]: !turn.open }));
  }

  toggleFull(turn: Turn, event: Event): void {
    event.stopPropagation();
    this.full.update((current) => ({ ...current, [turn.item.id]: !turn.full }));
  }

  preview(item: ConversationItem): string {
    return item.bodyPreview ?? item.body.content;
  }
}
