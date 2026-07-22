// Shapes mirror the backend JSON one to one. The message follows the
// Microsoft Graph message resource so a real Outlook integration later
// does not touch the frontend types.

export interface EmailAddress {
  name: string;
  address: string;
}

export interface Message {
  id: string;
  conversationId: string;
  from: { emailAddress: EmailAddress };
  subject: string;
  bodyPreview: string;
  body: { contentType: string; content: string };
  receivedDateTime: string;
  isRead: boolean;
  isReplied: boolean;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  body: string;
  placeholders: string[];
}

export interface Candidate {
  template_id: string;
  template_name: string;
  confidence: number;
  reason: string;
  // Declared placeholders of the template, minus agent_name which the
  // backend fills from config. These drive send gating.
  placeholders: string[];
}

export interface ExtractedField {
  key: string;
  value: string;
  confidence: number;
  source_span: string;
}

export interface SuggestResponse {
  candidates: Candidate[];
  fields: ExtractedField[];
  low_confidence: boolean;
}

export interface TemplateInput {
  name: string;
  description: string;
  body: string;
}

export interface SentItem {
  id: string;
  inReplyTo: string;
  template_id: string | null;
  subject: string;
  sentDateTime: string;
}
