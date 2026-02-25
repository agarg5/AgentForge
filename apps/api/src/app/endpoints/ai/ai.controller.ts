import { HasPermission } from '@ghostfolio/api/decorators/has-permission.decorator';
import { HasPermissionGuard } from '@ghostfolio/api/guards/has-permission.guard';
import { ApiService } from '@ghostfolio/api/services/api/api.service';
import {
  AiAdminOverviewResponse,
  AiFeedbackRequest,
  AiPromptResponse
} from '@ghostfolio/common/interfaces';
import { permissions } from '@ghostfolio/common/permissions';
import type { AiPromptMode, RequestWithUser } from '@ghostfolio/common/types';

import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpException,
  HttpStatus,
  Inject,
  Param,
  Post,
  Query,
  UseGuards
} from '@nestjs/common';
import { REQUEST } from '@nestjs/core';
import { AuthGuard } from '@nestjs/passport';

import { AiService } from './ai.service';

@Controller('ai')
export class AiController {
  public constructor(
    private readonly aiService: AiService,
    private readonly apiService: ApiService,
    @Inject(REQUEST) private readonly request: RequestWithUser
  ) {}

  @Post('chat')
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async chat(
    @Body()
    body: { message: string; history?: { role: string; content: string }[] },
    @Headers('authorization') authorization: string
  ) {
    try {
      return await this.aiService.forwardToAgent({
        message: body.message,
        history: body.history,
        authToken: authorization
      });
    } catch (error) {
      throw new HttpException(
        error.message ?? 'Agent unavailable',
        error.status ?? HttpStatus.BAD_GATEWAY
      );
    }
  }

  @Get('chat/history')
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async getChatHistory(@Headers('authorization') authorization: string) {
    try {
      return await this.aiService.getChatHistory({
        authToken: authorization
      });
    } catch (error) {
      throw new HttpException(
        error.message ?? 'Agent unavailable',
        error.status ?? HttpStatus.BAD_GATEWAY
      );
    }
  }

  @Delete('chat/history')
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async clearChatHistory(
    @Headers('authorization') authorization: string
  ) {
    try {
      return await this.aiService.clearChatHistory({
        authToken: authorization
      });
    } catch (error) {
      throw new HttpException(
        error.message ?? 'Agent unavailable',
        error.status ?? HttpStatus.BAD_GATEWAY
      );
    }
  }

  @Get('admin/overview')
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async getAdminOverview(): Promise<AiAdminOverviewResponse> {
    try {
      return await this.aiService.getAdminOverview();
    } catch (error) {
      throw new HttpException(
        error.message ?? 'Agent unavailable',
        error.status ?? HttpStatus.BAD_GATEWAY
      );
    }
  }

  @Post('feedback')
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async submitFeedback(
    @Body() body: AiFeedbackRequest,
    @Headers('authorization') authorization: string
  ) {
    try {
      return await this.aiService.submitFeedback({
        authToken: authorization,
        feedback: body
      });
    } catch (error) {
      throw new HttpException(
        error.message ?? 'Agent unavailable',
        error.status ?? HttpStatus.BAD_GATEWAY
      );
    }
  }

  @Get('prompt/:mode')
  @HasPermission(permissions.readAiPrompt)
  @UseGuards(AuthGuard('jwt'), HasPermissionGuard)
  public async getPrompt(
    @Param('mode') mode: AiPromptMode,
    @Query('accounts') filterByAccounts?: string,
    @Query('assetClasses') filterByAssetClasses?: string,
    @Query('dataSource') filterByDataSource?: string,
    @Query('symbol') filterBySymbol?: string,
    @Query('tags') filterByTags?: string
  ): Promise<AiPromptResponse> {
    const filters = this.apiService.buildFiltersFromQueryParams({
      filterByAccounts,
      filterByAssetClasses,
      filterByDataSource,
      filterBySymbol,
      filterByTags
    });

    const prompt = await this.aiService.getPrompt({
      filters,
      mode,
      impersonationId: undefined,
      languageCode: this.request.user.settings.settings.language,
      userCurrency: this.request.user.settings.settings.baseCurrency,
      userId: this.request.user.id
    });

    return { prompt };
  }
}
