import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ExtractedField } from '../models';

@Component({
  selector: 'app-review-panel',
  imports: [FormsModule, MatFormFieldModule, MatInputModule, MatTooltipModule],
  templateUrl: './review-panel.html',
  styleUrl: './review-panel.scss',
})
export class ReviewPanel {
  fields = input.required<ExtractedField[]>();
  requiredKeys = input<string[]>([]);
  fieldChange = output<{ key: string; value: string }>();

  expandedKey = signal<string | null>(null);
  showUnused = signal(false);

  // Foreground what the agent actually has to look at: extracted values
  // and anything the candidate templates need. Empty fields no template
  // asks for stay behind a toggle instead of shouting "Needs input" ten
  // times on every email.
  primary = computed(() => {
    const required = new Set(this.requiredKeys());
    return this.fields().filter((f) => f.value.trim() || required.has(f.key));
  });

  unused = computed(() => {
    const primaryKeys = new Set(this.primary().map((f) => f.key));
    return this.fields().filter((f) => !primaryKeys.has(f.key));
  });

  label(key: string): string {
    return key.replace(/_/g, ' ');
  }

  confidencePercent(field: ExtractedField): number {
    return Math.round(field.confidence * 100);
  }

  band(field: ExtractedField): string {
    if (!field.value.trim()) return 'lo';
    if (field.confidence >= 0.8) return 'hi';
    if (field.confidence >= 0.5) return 'mid';
    return 'lo';
  }

  toggleSpan(key: string): void {
    this.expandedKey.update((current) => (current === key ? null : key));
  }
}
