import { DataService } from '@ghostfolio/ui/services';

import { CommonModule } from '@angular/common';
import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  ViewChild
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

interface ChatMessage {
  role: 'user' | 'agent';
  content: string;
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
    MatProgressSpinnerModule
  ],
  selector: 'gf-chat-page',
  styleUrls: ['./chat-page.scss'],
  templateUrl: './chat-page.html'
})
export class GfChatPageComponent implements AfterViewChecked {
  @ViewChild('messagesContainer') private messagesContainer: ElementRef;

  public isLoading = false;
  public messageInput = '';
  public messages: ChatMessage[] = [];

  private shouldScrollToBottom = false;

  public constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private dataService: DataService
  ) {}

  public ngAfterViewChecked() {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
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

    const history = this.messages.slice(0, -1).map(({ content: c, role }) => ({
      content: c,
      role
    }));

    this.dataService.sendChatMessage({ history, message: content }).subscribe({
      next: (response) => {
        this.messages.push({
          content: response.content,
          role: 'agent',
          timestamp: new Date()
        });

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

  public onSuggestionClick(suggestion: string) {
    this.messageInput = suggestion;
    this.onSendMessage();
  }

  private scrollToBottom() {
    const container = this.messagesContainer?.nativeElement;

    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }
}
