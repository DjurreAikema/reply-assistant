import { Component, inject, signal } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';

import { AiPanel } from './ai-panel/ai-panel';
import { ApiService } from './api.service';
import { MessageDetail } from './message-detail/message-detail';
import { MessageList } from './message-list/message-list';
import { Message } from './models';

@Component({
  selector: 'app-root',
  imports: [MatToolbarModule, MessageList, MessageDetail, AiPanel],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  private api = inject(ApiService);

  messages = signal<Message[] | null>(null);
  selected = signal<Message | null>(null);

  constructor() {
    this.refresh();
  }

  onSelect(message: Message): void {
    this.selected.set(message);
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
