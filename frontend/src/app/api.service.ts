import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Candidate, Message, SentItem, Template } from './models';

// All URLs are relative. In dev the Angular proxy forwards /api to Flask
// on port 5000 (see proxy.conf.json), which also avoids CORS entirely.
@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  getMessages(): Observable<Message[]> {
    return this.http.get<Message[]>('/api/messages');
  }

  getMessage(id: string): Observable<Message> {
    return this.http.get<Message>(`/api/messages/${id}`);
  }

  getTemplates(): Observable<Template[]> {
    return this.http.get<Template[]>('/api/templates');
  }

  suggest(messageId: string): Observable<{ candidates: Candidate[] }> {
    return this.http.post<{ candidates: Candidate[] }>(`/api/messages/${messageId}/suggest`, {});
  }

  draft(messageId: string, templateId: string): Observable<{ body: string }> {
    return this.http.post<{ body: string }>(`/api/messages/${messageId}/draft`, {
      template_id: templateId,
    });
  }

  send(messageId: string, body: string): Observable<SentItem> {
    return this.http.post<SentItem>(`/api/messages/${messageId}/send`, { body });
  }
}
