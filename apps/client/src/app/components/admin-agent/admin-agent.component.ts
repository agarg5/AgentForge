import type { AiAdminOverviewResponse } from '@ghostfolio/common/interfaces';
import { DataService } from '@ghostfolio/ui/services';

import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit
} from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatTooltipModule
  ],
  selector: 'gf-admin-agent',
  styleUrls: ['./admin-agent.component.scss'],
  templateUrl: './admin-agent.component.html'
})
export class GfAdminAgentComponent implements OnInit, OnDestroy {
  public data: AiAdminOverviewResponse;
  public isLoading = true;
  public loadError = false;

  public toolColumns = ['name', 'type', 'description'];
  public verificationColumns = ['name', 'description'];
  public evalCategoryEntries: { category: string; count: number }[] = [];

  private unsubscribeSubject = new Subject<void>();

  public constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private dataService: DataService
  ) {}

  public ngOnInit() {
    this.dataService
      .getAgentAdminOverview()
      .pipe(takeUntil(this.unsubscribeSubject))
      .subscribe({
        next: (data) => {
          this.data = data;
          this.evalCategoryEntries = Object.entries(data.evals.categories).map(
            ([category, count]) => ({ category, count })
          );
          this.isLoading = false;
          this.changeDetectorRef.markForCheck();
        },
        error: () => {
          this.isLoading = false;
          this.loadError = true;
          this.changeDetectorRef.markForCheck();
        }
      });
  }

  public ngOnDestroy() {
    this.unsubscribeSubject.next();
    this.unsubscribeSubject.complete();
  }
}
