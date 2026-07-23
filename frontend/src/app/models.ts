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

// A conversation is the messages and sent items sharing a conversationId.
// The summary is what the inbox row needs; the items are the thread.
export interface Conversation {
  id: string;
  subject: string;
  participant: EmailAddress;
  lastPreview: string;
  lastTimestamp: string;
  messageCount: number;
  lastIsInbound: boolean;
  isRead: boolean;
}

// One item in a thread. The backend tags both source shapes with
// direction and timestamp; the rest of each shape comes through as it is,
// so the inbound branch is still a Message.
export interface ConversationItem {
  id: string;
  direction: 'inbound' | 'outbound';
  timestamp: string;
  conversationId: string;
  subject: string;
  body: { contentType: string; content: string };
  from?: { emailAddress: EmailAddress };
  to?: { emailAddress: EmailAddress };
  bodyPreview?: string;
  receivedDateTime?: string;
  sentDateTime?: string;
  isRead?: boolean;
  isReplied?: boolean;
  inReplyTo?: string;
  template_id?: string | null;
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
