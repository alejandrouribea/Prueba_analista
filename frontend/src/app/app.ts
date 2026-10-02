import { ChangeDetectionStrategy, Component } from '@angular/core';

import { ConciliadorPage } from './features/conciliador/conciliador-page/conciliador-page';

@Component({
  selector: 'app-root',
  template: '<app-conciliador-page />',
  imports: [ConciliadorPage],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {}
