import { Component, inject, signal } from '@angular/core';

import { AiPanel } from '../ai-panel/ai-panel';
import { ApiService } from '../api.service';
import { MessageDetail } from '../message-detail/message-detail';
import { MessageList } from '../message-list/message-list';
import { ExtractedField, Message } from '../models';

@Component({
  selector: 'app-inbox',
  imports: [MessageList, MessageDetail, AiPanel],
  templateUrl: './inbox.html',
  styleUrl: './inbox.scss',
})
export class Inbox {
  private api = inject(ApiService);

  messages = signal<Message[] | null>(null);
  selected = signal<Message | null>(null);

  // Extracted fields live here because two panes need them: the review
  // panel in the centre edits them, the AI panel on the right consumes
  // them for draft substitution and send gating.
  fields = signal<ExtractedField[]>([]);
  requiredKeys = signal<string[]>([]);

  constructor() {
    this.refresh();
  }

  onSelect(message: Message): void {
    this.selected.set(message);
  }

  onFields(fields: ExtractedField[]): void {
    this.fields.set(fields);
  }

  onRequiredKeys(keys: string[]): void {
    this.requiredKeys.set(keys);
  }

  onFieldEdit(edit: { key: string; value: string }): void {
    this.fields.update((list) =>
      list.map((f) => (f.key === edit.key ? { ...f, value: edit.value } : f)),
    );
  }

  onReplied(messageId: string): void {
    // Refetch instead of patching local state, so the list always shows
    // exactly what is on disk. Cheap at this scale, honest at any scale.
    this.refresh(messageId);
  }

  private refresh(keepSelectedId?: string): void {
    this.api.getMessages().subscribe((list) => {
      this.messages.set(list);
      const targetId = keepSelectedId ?? this.selected()?.id;
      if (targetId) {
        this.selected.set(list.find((m) => m.id === targetId) ?? null);
      }
    });
  }
}
