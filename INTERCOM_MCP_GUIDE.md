# Building with the Official Intercom MCP Server: A Developer's Guide

## The Discovery Journey

When I first tried to use the official Intercom MCP server in Claude Code, I hit a wall. The tools simply weren't available, despite the server showing as "connected." This led me down a rabbit hole of debugging that revealed important insights about how MCP servers actually work.

## The Real Problem

The issue wasn't with Intercom's MCP server—it was with how Claude Code registers MCP tools at startup. While Claude Desktop can dynamically load MCP tools, Claude Code cannot. This is a known limitation affecting many users.

## How Intercom MCP Actually Works

The Intercom MCP server uses **Streamable HTTP transport** with session management:

1. **Initialize without a session** → Server returns session ID in headers
2. **Use that session ID** for all subsequent requests
3. **Maintain the session** throughout your application lifecycle

Here's the critical discovery: The session ID comes in the `mcp-session-id` response header, not in the JSON body.

```javascript
// ❌ Wrong: Generating your own session
const sessionId = crypto.randomUUID();

// ✅ Right: Using the server's session
const response = await fetch(url, { method: 'POST', ... });
const sessionId = response.headers.get('mcp-session-id');
```

## Building Your Own Integration

### Quick Start

```javascript
const INTERCOM_MCP_URL = 'https://mcp.intercom.com/mcp';
const AUTH_TOKEN = 'your_intercom_api_token_here';

class IntercomMCPClient {
  async request(method, params = {}) {
    const headers = {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream, application/json'
    };

    // Add session for non-init requests
    if (this.sessionId && method !== 'initialize') {
      headers['Mcp-Session-Id'] = this.sessionId;
    }

    // Make request and parse SSE response
    const response = await fetch(this.url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ jsonrpc: '2.0', method, params, id: 1 })
    });

    // Capture session on init
    if (method === 'initialize') {
      this.sessionId = response.headers.get('mcp-session-id');
    }

    // Parse SSE format: "event: message\ndata: {...}"
    const text = await response.text();
    const match = text.match(/data: ({.*})/);
    return match ? JSON.parse(match[1]) : JSON.parse(text);
  }
}
```

## Available Tools

The server provides 6 powerful tools:

- **`search_conversations`** - Filter by state, source, author, response times
- **`get_conversation`** - Full details including message history
- **`search_contacts`** - Find by email, name, custom attributes
- **`get_contact`** - Complete contact profile
- **`search`** - Unified DSL for complex queries
- **`fetch`** - Get any resource by ID

## The Search DSL

The most powerful feature is the unified search with its query language:

```javascript
// Find open conversations from email
await client.callTool('search', {
  query: 'object_type:conversations state:open source_type:email'
});

// Find contacts from specific domain
await client.callTool('search', {
  query: 'object_type:contacts email_domain:"example.com"'
});

// Complex queries with operators
await client.callTool('search', {
  query: 'object_type:conversations statistics_time_to_admin_reply:gt:3600'
});
```

## Key Lessons Learned

1. **MCP != REST API** - It uses stateful sessions over HTTP with SSE responses
2. **Authentication is simple** - Just Bearer token in headers
3. **Session management is critical** - Must use server-provided session ID
4. **Response format is SSE** - Parse `data:` fields from event streams
5. **Error messages matter** - "At least one search parameter" means empty queries need filters

## Practical Applications

You can build:
- **Support dashboards** showing open conversations with slow response times
- **Customer insight tools** aggregating conversation patterns
- **Automation workflows** that trigger on specific conversation states
- **Analytics engines** processing conversation metrics

## The Bottom Line

The official Intercom MCP server is production-ready and fully functional. While it doesn't work directly in Claude Code due to tool registration limitations, you can absolutely build applications with it using any HTTP client. The session-based architecture and comprehensive tool set make it a powerful foundation for integrating Intercom data into your workflows.

The irony? Intercom uses Claude to power their AI, and now we can use their MCP server to build AI applications. Full circle.