/**
 * Production Logger
 * Safe logging utility that respects production settings
 */

import { getConfig } from '../config/production';

export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

class Logger {
  private config = getConfig();
  private logLevels: Record<LogLevel, number> = {
    error: 0,
    warn: 1,
    info: 2,
    debug: 3
  };

  private shouldLog(level: LogLevel): boolean {
    return this.logLevels[level] <= this.logLevels[this.config.logging.level];
  }

  private formatMessage(level: LogLevel, context: string, message: string, data?: any): string {
    const timestamp = new Date().toISOString();
    const formattedMessage = `[${timestamp}] [${level.toUpperCase()}] [${context}] ${message}`;

    if (data) {
      return `${formattedMessage}\nData: ${JSON.stringify(data, null, 2)}`;
    }

    return formattedMessage;
  }

  private async sendToRemote(level: LogLevel, context: string, message: string, data?: any): Promise<void> {
    if (!this.config.logging.enableRemoteLogging || !this.config.logging.remoteEndpoint) {
      return;
    }

    try {
      await fetch(this.config.logging.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          level,
          context,
          message,
          data,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href
        })
      });
    } catch (error) {
      // Silently fail - don't break the app if logging fails
      if (this.config.logging.enableConsole) {
        console.warn('Failed to send log to remote endpoint:', error);
      }
    }
  }

  error(context: string, message: string, error?: any): void {
    if (!this.shouldLog('error')) return;

    const formattedMessage = this.formatMessage('error', context, message, error);

    if (this.config.logging.enableConsole) {
      console.error(formattedMessage);
    }

    this.sendToRemote('error', context, message, {
      error: error?.message || error,
      stack: error?.stack
    }).catch(() => {});
  }

  warn(context: string, message: string, data?: any): void {
    if (!this.shouldLog('warn')) return;

    const formattedMessage = this.formatMessage('warn', context, message, data);

    if (this.config.logging.enableConsole) {
      console.warn(formattedMessage);
    }

    this.sendToRemote('warn', context, message, data).catch(() => {});
  }

  info(context: string, message: string, data?: any): void {
    if (!this.shouldLog('info')) return;

    const formattedMessage = this.formatMessage('info', context, message, data);

    if (this.config.logging.enableConsole) {
      console.info(formattedMessage);
    }

    this.sendToRemote('info', context, message, data).catch(() => {});
  }

  debug(context: string, message: string, data?: any): void {
    if (!this.shouldLog('debug')) return;

    const formattedMessage = this.formatMessage('debug', context, message, data);

    if (this.config.logging.enableConsole) {
      console.debug(formattedMessage);
    }

    this.sendToRemote('debug', context, message, data).catch(() => {});
  }

  // Performance logging
  performance(context: string, operation: string, duration: number, metadata?: any): void {
    this.info(context, `Performance: ${operation} completed in ${duration}ms`, metadata);
  }

  // User action logging
  userAction(context: string, action: string, userId?: string, metadata?: any): void {
    this.info(context, `User action: ${action}`, {
      userId,
      ...metadata
    });
  }
}

export const logger = new Logger();
