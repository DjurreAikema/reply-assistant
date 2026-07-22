import { Routes } from '@angular/router';

import { Inbox } from './inbox/inbox';
import { TemplatesPage } from './templates-page/templates-page';

export const routes: Routes = [
  { path: '', component: Inbox },
  { path: 'templates', component: TemplatesPage },
  { path: '**', redirectTo: '' },
];
