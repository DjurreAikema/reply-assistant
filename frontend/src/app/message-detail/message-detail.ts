import { DatePipe } from '@angular/common';
import { Component, input, output } from '@angular/core';

import { ExtractedField, Message } from '../models';
import { ReviewPanel } from '../review-panel/review-panel';

@Component({
  selector: 'app-message-detail',
  imports: [DatePipe, ReviewPanel],
  templateUrl: './message-detail.html',
  styleUrl: './message-detail.scss',
})
export class MessageDetail {
  message = input<Message | null>(null);
  // Extraction state is owned by the inbox page; this component only
  // renders it below the body and passes edits back up.
  fields = input<ExtractedField[]>([]);
  requiredKeys = input<string[]>([]);
  fieldChange = output<{ key: string; value: string }>();
}
