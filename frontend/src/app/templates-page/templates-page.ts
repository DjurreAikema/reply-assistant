import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

import { ApiService } from '../api.service';
import { Template } from '../models';

const TOKEN_RE = /\{\{\s*(\w+)\s*\}\}/g;

@Component({
  selector: 'app-templates-page',
  imports: [FormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  templateUrl: './templates-page.html',
  styleUrl: './templates-page.scss',
})
export class TemplatesPage {
  private api = inject(ApiService);

  templates = signal<Template[] | null>(null);
  error = signal<string | null>(null);
  saving = signal(false);

  // null means the form is closed, '' means creating, otherwise the id
  // of the template being edited.
  editingId = signal<string | null>(null);
  name = signal('');
  description = signal('');
  body = signal('');

  // Two-step delete: first click arms, second click within the same
  // template confirms. Anything else disarms.
  pendingDeleteId = signal<string | null>(null);

  // Parsed live from the body as the user types, and parsed again server
  // side on save. Never entered by hand.
  parsedPlaceholders = computed(() => {
    const seen = new Set<string>();
    for (const match of this.body().matchAll(TOKEN_RE)) {
      seen.add(match[1]);
    }
    return [...seen];
  });

  constructor() {
    this.load();
  }

  startCreate(): void {
    this.editingId.set('');
    this.name.set('');
    this.description.set('');
    this.body.set('');
    this.pendingDeleteId.set(null);
    this.error.set(null);
  }

  startEdit(template: Template): void {
    this.editingId.set(template.id);
    this.name.set(template.name);
    this.description.set(template.description);
    this.body.set(template.body);
    this.pendingDeleteId.set(null);
    this.error.set(null);
  }

  cancel(): void {
    this.editingId.set(null);
    this.error.set(null);
  }

  canSave(): boolean {
    return !this.saving() && !!this.name().trim() && !!this.body().trim();
  }

  save(): void {
    if (!this.canSave()) return;
    const input = {
      name: this.name().trim(),
      description: this.description().trim(),
      body: this.body().trim(),
    };
    const id = this.editingId();
    const call = id ? this.api.updateTemplate(id, input) : this.api.createTemplate(input);
    this.saving.set(true);
    this.error.set(null);
    call.subscribe({
      next: () => {
        this.saving.set(false);
        this.editingId.set(null);
        this.load();
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err.error?.error ?? 'Saving failed. Check that the backend is running.');
      },
    });
  }

  remove(template: Template): void {
    if (this.pendingDeleteId() !== template.id) {
      this.pendingDeleteId.set(template.id);
      return;
    }
    this.pendingDeleteId.set(null);
    this.error.set(null);
    this.api.deleteTemplate(template.id).subscribe({
      next: () => this.load(),
      error: (err) => {
        this.error.set(err.error?.error ?? 'Deleting failed. Check that the backend is running.');
      },
    });
  }

  private load(): void {
    this.api.getTemplates().subscribe({
      next: (list) => this.templates.set(list),
      error: () => this.error.set('Could not load templates. Check that the backend is running.'),
    });
  }
}
