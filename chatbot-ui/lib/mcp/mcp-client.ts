import { spawn, ChildProcess } from 'child_process';

export class FirecrawlMCPClient {
  private process: ChildProcess | null = null;
  private isConnected = false;
  private requestId = 1;
  private pendingRequests = new Map<number, { resolve: Function; reject: Function }>();

  async connect(): Promise<void> {
    if (this.isConnected) return;

    return new Promise((resolve, reject) => {
      this.process = spawn('npx', ['firecrawl-mcp'], {
        stdio: 'pipe',
        cwd: process.cwd() + '/../firecrawl-mcp',
        env: {
          ...process.env,
          FIRECRAWL_API_KEY: process.env.FIRECRAWL_API_KEY || ''
        }
      });

      let initialized = false;

      // Handle stderr for initialization messages
      this.process.stderr?.on('data', (data) => {
        const output = data.toString();
        console.log('MCP Server:', output);
        
        if (output.includes('Firecrawl MCP Server initialized successfully') && !initialized) {
          initialized = true;
          this.setupMessageHandling();
          this.isConnected = true;
          resolve();
        }
      });

      // Handle process errors
      this.process.on('error', (error) => {
        console.error('MCP process error:', error);
        if (!initialized) reject(error);
      });

      this.process.on('close', (code) => {
        console.log(`MCP process closed with code ${code}`);
        this.isConnected = false;
        this.process = null;
      });

      // Timeout if server doesn't start
      setTimeout(() => {
        if (!initialized) {
          reject(new Error('MCP server failed to initialize within timeout'));
        }
      }, 10000);
    });
  }

  private setupMessageHandling(): void {
    if (!this.process?.stdout) return;

    let buffer = '';

    this.process.stdout.on('data', (data) => {
      buffer += data.toString();
      
      // Process complete JSON messages
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        
        if (line) {
          try {
            const message = JSON.parse(line);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse MCP message:', line, error);
          }
        }
      }
    });
  }

  private handleMessage(message: any): void {
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject } = this.pendingRequests.get(message.id)!;
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message || 'MCP request failed'));
      } else {
        resolve(message.result);
      }
    }
  }

  private async sendRequest(method: string, params?: any): Promise<any> {
    if (!this.process?.stdin) {
      throw new Error('MCP client not connected');
    }

    const id = this.requestId++;
    const request = {
      jsonrpc: '2.0',
      id,
      method,
      ...(params && { params })
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });

      this.process!.stdin!.write(JSON.stringify(request) + '\n');

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error('MCP request timeout'));
        }
      }, 30000);
    });
  }

  async disconnect(): Promise<void> {
    if (!this.isConnected) return;

    this.process?.kill();
    this.process = null;
    this.isConnected = false;
    this.pendingRequests.clear();
  }

  async listTools(): Promise<any[]> {
    const response = await this.sendRequest('tools/list');
    return response.tools || [];
  }

  async callTool(name: string, args: any): Promise<any> {
    const response = await this.sendRequest('tools/call', {
      name,
      arguments: args
    });
    return response;
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

// Singleton instance
export const firecrawlMCPClient = new FirecrawlMCPClient();