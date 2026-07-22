import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';

import { Message } from '../models';

@Component({
  selector: 'app-message-detail',
  imports: [DatePipe],
  templateUrl: './message-detail.html',
  styleUrl: './message-detail.scss',
})
export class MessageDetail {
  message = input<Message | null>(null);
}
