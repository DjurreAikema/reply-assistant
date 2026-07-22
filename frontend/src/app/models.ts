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
}

export interface SentItem {
  id: string;
  inReplyTo: string;
  subject: string;
  sentDateTime: string;
}
