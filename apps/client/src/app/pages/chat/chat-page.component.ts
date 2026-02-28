import { AiVerificationCheck } from '@ghostfolio/common/interfaces';
import { DataService } from '@ghostfolio/ui/services';

import { CommonModule } from '@angular/common';
import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnInit,
  ViewChild
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

interface Politician {
  name: string;
  chamber: string;
  party: string;
  initials: string;
  image: string;
}

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
  contentHtml?: SafeHtml;
  toolsUsed?: string[];
  toolsExpanded?: boolean;
  runId?: string;
  latencySeconds?: number;
  verification?: AiVerificationCheck[];
  verificationExpanded?: boolean;
  verificationAnimatedCount?: number;
  feedbackScore?: number;
  timestamp: Date;
}

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'page' },
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  selector: 'gf-chat-page',
  styleUrls: ['./chat-page.scss'],
  templateUrl: './chat-page.html'
})
export class GfChatPageComponent implements AfterViewChecked, OnInit {
  @ViewChild('messagesContainer') private messagesContainer: ElementRef;

  public isLoading = false;
  public isLoadingHistory = true;
  public messageInput = '';
  public messages: ChatMessage[] = [];
  public politicians: Politician[] = [];

  private shouldScrollToBottom = false;

  public constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private dataService: DataService,
    private sanitizer: DomSanitizer
  ) {
    marked.setOptions({ breaks: true });
  }

  public ngOnInit() {
    this.dataService.getPoliticians().subscribe({
      next: (politicians) => {
        this.politicians = politicians;
        this.changeDetectorRef.markForCheck();
      }
    });

    this.dataService.getChatHistory().subscribe({
      next: (response) => {
        this.messages = response.history.map((msg) => ({
          content: msg.content,
          contentHtml:
            msg.role === 'agent'
              ? this.sanitizer.bypassSecurityTrustHtml(
                  marked.parse(msg.content) as string
                )
              : undefined,
          role: msg.role as 'user' | 'agent',
          timestamp: new Date()
        }));

        this.isLoadingHistory = false;
        this.shouldScrollToBottom = true;
        this.changeDetectorRef.markForCheck();
      },
      error: () => {
        this.isLoadingHistory = false;
        this.changeDetectorRef.markForCheck();
      }
    });
  }

  public ngAfterViewChecked() {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  public onClearChat() {
    this.dataService.clearChatHistory().subscribe({
      next: () => {
        this.messages = [];
        this.changeDetectorRef.markForCheck();
      }
    });
  }

  public onSendMessage() {
    const content = this.messageInput.trim();

    if (!content || this.isLoading) {
      return;
    }

    this.messages.push({
      content,
      role: 'user',
      timestamp: new Date()
    });

    this.messageInput = '';
    this.isLoading = true;
    this.shouldScrollToBottom = true;
    this.changeDetectorRef.markForCheck();

    this.dataService.sendChatMessage({ message: content }).subscribe({
      next: (response) => {
        const verification = response.metrics?.verification?.length
          ? response.metrics.verification
          : undefined;

        const agentMessage: ChatMessage = {
          content: response.content,
          contentHtml: this.sanitizer.bypassSecurityTrustHtml(
            marked.parse(response.content) as string
          ),
          role: 'agent',
          toolsUsed: response.tools_used?.length
            ? response.tools_used
            : undefined,
          toolsExpanded: false,
          runId: response.run_id,
          latencySeconds: response.metrics?.latency_seconds,
          verification,
          verificationExpanded: false,
          verificationAnimatedCount: 0,
          timestamp: new Date()
        };

        this.messages.push(agentMessage);

        this.isLoading = false;
        this.shouldScrollToBottom = true;
        this.changeDetectorRef.markForCheck();
      },
      error: () => {
        this.messages.push({
          content: 'Sorry, something went wrong. Please try again.',
          role: 'agent',
          timestamp: new Date()
        });

        this.isLoading = false;
        this.shouldScrollToBottom = true;
        this.changeDetectorRef.markForCheck();
      }
    });
  }

  public toggleToolsExpanded(message: ChatMessage) {
    message.toolsExpanded = !message.toolsExpanded;
    this.changeDetectorRef.markForCheck();
  }

  public onSuggestionClick(suggestion: string) {
    this.messageInput = suggestion;
    this.onSendMessage();
  }

  public onPoliticianClick(politician: Politician) {
    this.messageInput = `Show me ${politician.name}'s recent stock trades`;
    this.onSendMessage();
  }

  public toggleVerificationExpanded(message: ChatMessage) {
    message.verificationExpanded = !message.verificationExpanded;

    if (message.verificationExpanded) {
      this.animateVerificationChecks(message);
    }

    this.changeDetectorRef.markForCheck();
  }

  public onFeedback(message: ChatMessage, score: number) {
    if (!message.runId || message.feedbackScore === score) {
      return;
    }

    const previousScore = message.feedbackScore;
    message.feedbackScore = score;
    this.changeDetectorRef.markForCheck();

    this.dataService.sendFeedback({ run_id: message.runId, score }).subscribe({
      error: () => {
        message.feedbackScore = previousScore;
        this.changeDetectorRef.markForCheck();
      }
    });
  }

  private animateVerificationChecks(message: ChatMessage) {
    message.verificationAnimatedCount = 0;

    const total = message.verification?.length ?? 0;

    if (total === 0) {
      return;
    }

    const interval = setInterval(() => {
      message.verificationAnimatedCount =
        (message.verificationAnimatedCount ?? 0) + 1;

      this.changeDetectorRef.markForCheck();

      if ((message.verificationAnimatedCount ?? 0) >= total) {
        clearInterval(interval);
      }
    }, 150);
  }

  private scrollToBottom() {
    const container = this.messagesContainer?.nativeElement;

    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }
}
