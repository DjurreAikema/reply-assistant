import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { MatRippleModule } from '@angular/material/core';

import { Conversation } from '../models';

@Component({
  selector: 'app-conversation-list',
  imports: [DatePipe, MatRippleModule],
  templateUrl: './conversation-list.html',
  styleUrl: './conversation-list.scss',
})
export class ConversationList {
  conversations = input.required<Conversation[] | null>();
  selectedId = input<string | null>(null);
  select = output<Conversation>();
}
