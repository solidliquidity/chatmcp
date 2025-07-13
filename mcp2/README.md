# Email Manager MCP Server

A Model Context Protocol (MCP) server for automated email management and client follow-up. Supports both Gmail and Outlook/Microsoft Graph APIs for comprehensive email operations, client tracking, and follow-up automation.

## Features

### Resources
- **Email Folders**: Browse email folders/labels and their contents
  - `email://folders` - Get all email folders with message counts
  - `email://folder/{folder_name}` - Get detailed folder contents and recent messages

### Tools
- **search_emails**: Search emails with keywords, sender, subject filters
- **send_follow_up_email**: Send automated follow-up emails to clients with templates
- **track_client_status**: Track client interaction status for follow-up management
- **find_overdue_clients**: Identify clients who haven't responded within specified timeframes

### Prompts
- **follow-up-campaign**: Generate systematic follow-up campaigns for overdue clients
- **client-analysis**: Analyze client communication patterns and engagement
- **email-cleanup**: Organize and clean up email folders efficiently

## Supported Email Providers

### Gmail
- Uses Google API Client Library
- Supports OAuth 2.0 authentication
- Read, send, and organize Gmail messages
- Access to labels and threads

### Outlook (Microsoft Graph)
- Uses Microsoft Graph API
- Supports OAuth 2.0 authentication  
- Read, send, and organize Outlook messages
- Access to folders and conversations

## Installation

1. **Install dependencies**:
   ```bash
   cd mcp2
   pip install -e .
   ```

2. **Set up email provider credentials**:
   ```bash
   cp .env.example .env
   # Edit .env with your provider choice
   ```

3. **Configure OAuth credentials** (see setup sections below)

## Gmail Setup

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop Application)
5. Download credentials JSON file

### 2. Configure Gmail
```bash
# Set environment variables
export EMAIL_PROVIDER=gmail
export GMAIL_CREDENTIALS_PATH=/path/to/gmail_credentials.json
```

### 3. Gmail Credentials File
Save your OAuth credentials as `gmail_credentials.json`:
```json
{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "your-client-secret",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Outlook Setup

### 1. Register Azure App
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory > App registrations
3. Create new registration
4. Add permissions: Mail.Read, Mail.Send, Mail.ReadWrite
5. Generate client secret

### 2. Configure Outlook
```bash
# Set environment variables
export EMAIL_PROVIDER=outlook
export OUTLOOK_CREDENTIALS_PATH=/path/to/outlook_credentials.json
```

### 3. Outlook Credentials File
Save your OAuth credentials as `outlook_credentials.json`:
```json
{
  "client_id": "your-application-id",
  "client_secret": "your-client-secret",
  "tenant_id": "your-tenant-id",
  "access_token": "your-access-token"
}
```

## Usage

### Development Mode
Test the server with MCP Inspector:
```bash
uv run mcp dev mcp_email/server.py
```

### Production Deployment
Run the server directly:
```bash
python -m mcp_email.server
```

### Claude Desktop Integration
Install in Claude Desktop:
```bash
uv run mcp install mcp_email/server.py --name "Email Manager" \
  -v EMAIL_PROVIDER=gmail \
  -v GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
```

## Usage Examples

### Search and Analyze Emails
```python
# Search for emails from specific client
emails = await session.call_tool("search_emails", {
    "query": "from:client@example.com",
    "max_results": 50
})

# Find overdue clients
overdue = await session.call_tool("find_overdue_clients", {
    "days_threshold": 7
})
```

### Send Follow-up Emails
```python
# Send gentle follow-up
result = await session.call_tool("send_follow_up_email", {
    "to_email": "client@example.com",
    "client_name": "John Doe",
    "subject": "Project Update",
    "follow_up_type": "gentle"
})

# Send urgent follow-up with custom message
result = await session.call_tool("send_follow_up_email", {
    "to_email": "client@example.com", 
    "client_name": "Jane Smith",
    "subject": "Contract Approval Required",
    "follow_up_type": "urgent",
    "custom_message": "Hi Jane, we need your approval on the contract by EOD today..."
})
```

### Client Tracking
```python
# Update client status
result = await session.call_tool("track_client_status", {
    "client_email": "client@example.com",
    "status": "responded"
})

# Browse email folders
folders = await session.read_resource("email://folders")
inbox_details = await session.read_resource("email://folder/inbox")
```

### Automated Follow-up Campaigns
```python
# Generate follow-up campaign
campaign = await session.get_prompt("follow-up-campaign", {
    "client_type": "enterprise",
    "urgency": "high"
})

# Analyze client communication patterns
analysis = await session.get_prompt("client-analysis", {
    "time_period": "last_month"
})
```

## Follow-up Templates

The server includes built-in follow-up templates:

### Gentle Follow-up
- Used for 1-3 days overdue
- Friendly, understanding tone
- Offers assistance

### Standard Reminder
- Used for 4-7 days overdue
- Professional, direct approach
- Requests specific timeline

### Urgent Follow-up
- Used for 8+ days overdue
- Time-sensitive language
- Emphasizes importance

## Client Tracking Features

### Status Tracking
- **pending**: Awaiting client response
- **responded**: Client has replied
- **overdue**: Past due date threshold
- **closed**: Conversation completed

### Automated Detection
- Identifies clients who haven't responded
- Calculates days overdue
- Tracks response patterns
- Suggests follow-up actions

## Security and Privacy

### OAuth Authentication
- Secure OAuth 2.0 flows for both providers
- Token refresh handling
- Minimal required permissions

### Data Protection
- No email content stored permanently
- Client data processed in memory only
- Secure credential management
- API rate limiting compliance

### Email Safety
- Read-only operations by default
- Explicit send permissions required
- Email validation before sending
- Template-based safe messaging

## Troubleshooting

### Gmail Issues
```bash
# Test Gmail authentication
python -c "
from mcp_email.server import GmailService, EmailConfig
import asyncio
config = EmailConfig.from_env()
service = GmailService(config)
asyncio.run(service.authenticate())
print('Gmail authentication successful!')
"
```

### Outlook Issues
```bash
# Test Outlook authentication
python -c "
from mcp_email.server import OutlookService, EmailConfig
import asyncio
config = EmailConfig.from_env()
service = OutlookService(config)
asyncio.run(service.authenticate())
print('Outlook authentication successful!')
"
```

### Common Errors

1. **"Gmail dependencies not installed"**
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. **"Outlook dependencies not installed"**
   ```bash
   pip install msgraph-core requests
   ```

3. **"Credentials file not found"**
   - Ensure credential files exist at specified paths
   - Check file permissions
   - Verify JSON format

4. **"Authentication failed"**
   - Check OAuth credentials are valid
   - Verify API permissions are granted
   - Ensure tokens haven't expired

## Client Follow-up Workflows

### Daily Client Check
1. Run `find_overdue_clients` to identify overdue responses
2. Categorize by urgency level
3. Send appropriate follow-up templates
4. Update client tracking status

### Weekly Campaign
1. Analyze communication patterns with `client-analysis` prompt
2. Identify at-risk clients
3. Create targeted follow-up campaigns
4. Monitor response rates

### Monthly Cleanup
1. Use `email-cleanup` prompt for folder organization
2. Archive completed conversations
3. Update client status tracking
4. Review and optimize follow-up templates

## Architecture

The server uses:
- **FastMCP**: High-level MCP framework
- **Google API Client**: Gmail integration
- **Microsoft Graph**: Outlook integration
- **OAuth 2.0**: Secure authentication
- **Template system**: Consistent follow-up messaging
- **Client tracking**: Response monitoring

## Contributing

Contributions welcome! Please ensure:
- Secure OAuth implementation
- Proper error handling
- Email validation and safety
- Documentation updates
- Privacy and security compliance

## License

MIT License - see LICENSE file for details.