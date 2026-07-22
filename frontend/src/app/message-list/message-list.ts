import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
import { MatRippleModule } from '@angular/material/core';

import { Message } from '../models';

@Component({
  selector: 'app-message-list',
  imports: [DatePipe, MatRippleModule],
  templateUrl: './message-list.html',
  styleUrl: './message-list.scss',
})
export class MessageList {
  messages = input.required<Message[] | null>();
  selectedId = input<string | null>(null);
  select = output<Message>();
}
