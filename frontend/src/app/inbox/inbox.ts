import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatSidenavModule } from '@angular/material/sidenav';
import { map } from 'rxjs';

import { ApiService } from '../api.service';
import { ConversationList } from '../conversation-list/conversation-list';
import { ConversationThread } from '../conversation-thread/conversation-thread';
import { Conversation, ConversationItem, Message, SentItem } from '../models';
import { ReplyWorkspace } from '../reply-workspace/reply-workspace';

// Below this the inbox stops being a column and becomes a drawer, rather
// than squeezing three columns into a phone.
const DRAWER_QUERY = '(max-width: 1000px)';

@Component({
  selector: 'app-inbox',
  imports: [
    ConversationList,
    ConversationThread,
    ReplyWorkspace,
    MatSidenavModule,
    MatButtonModule,
  ],
  templateUrl: './inbox.html',
  styleUrl: './inbox.scss',
})
export class Inbox {
  private api = inject(ApiService);

  conversations = signal<Conversation[] | null>(null);
  selectedId = signal<string | null>(null);
  thread = signal<ConversationItem[]>([]);
  // The most recent inbound message in the selected thread. Suggestion,
  // drafting and sending all still work on a single message id, so this
  // is what the reply workspace is driven by.
  selected = signal<Message | null>(null);
  justSentId = signal<string | null>(null);

  private narrow = toSignal(
    inject(BreakpointObserver)
      .observe(DRAWER_QUERY)
      .pipe(map((state) => state.matches)),
    { initialValue: false },
  );

  drawerMode = computed<'over' | 'side'>(() => (this.narrow() ? 'over' : 'side'));
  drawerOpen = signal(true);

  constructor() {
    // The drawer is permanent while it is a column and closed while it
    // overlays, so crossing the breakpoint sets it either way.
    effect(() => this.drawerOpen.set(!this.narrow()));
    this.refresh();
  }

  onSelect(conversation: Conversation): void {
    if (this.narrow()) this.drawerOpen.set(false);
    if (conversation.id === this.selectedId()) return;
    this.selectedId.set(conversation.id);
    this.justSentId.set(null);
    this.loadThread(conversation.id);
  }

  onReplied(sent: SentItem): void {
    // Refetch instead of patching local state, so the list always shows
    // exactly what is on disk. Cheap at this scale, honest at any scale.
    this.justSentId.set(sent.id);
    this.refresh();
    const id = this.selectedId();
    if (id) this.loadThread(id);
  }

  private loadThread(conversationId: string): void {
    this.api.getConversation(conversationId).subscribe((items) => {
      if (this.selectedId() !== conversationId) return;
      this.thread.set(items);
      const latest = this.lastInbound(items);
      // Replacing this with an equal message would restart suggestion,
      // and reloading after a send must not cost another model call.
      if (latest?.id !== this.selected()?.id) this.selected.set(latest);
    });
  }

  private lastInbound(items: ConversationItem[]): Message | null {
    for (let i = items.length - 1; i >= 0; i--) {
      // Inbound items come through with the full message shape intact.
      if (items[i].direction === 'inbound') return items[i] as unknown as Message;
    }
    return null;
  }

  private refresh(): void {
    this.api.getConversations().subscribe((list) => this.conversations.set(list));
  }
}
