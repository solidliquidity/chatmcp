# PostgreSQL MCP Server

A Model Context Protocol (MCP) server that provides secure, read-only access to PostgreSQL databases. This server exposes database schemas as resources, provides tools for executing safe SQL queries, and includes prompts for common data analysis tasks.

## Features

### Resources
- **Schema Information**: Browse database schemas and their structure
  - `postgres://schema/{schema_name}` - Get detailed schema information
  - `postgres://table/{schema_name}/{table_name}` - Get specific table details

### Tools
- **execute_query**: Execute read-only SQL SELECT queries with safety validation
- **list_schemas**: Get all available database schemas
- **list_tables**: List tables in a specific schema

### Prompts
- **analyze-table**: Generate prompts for systematic table analysis
- **data-quality-check**: Create data quality assessment workflows
- **performance-analysis**: Database performance analysis guidance

## Security Features

- **Read-only Operations**: Only SELECT queries are permitted
- **SQL Injection Protection**: Query validation and parameterization
- **Query Limiting**: Automatic row limits to prevent resource exhaustion
- **Schema Restrictions**: Environment-based access control

## Installation

1. **Install dependencies**:
   ```bash
   cd mcp1
   pip install -e .
   ```

2. **Configure database connection**:
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL credentials
   ```

3. **Set environment variables**:
   ```bash
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export POSTGRES_DATABASE=your_database
   export POSTGRES_USER=your_username
   export POSTGRES_PASSWORD=your_password
   ```

## Usage

### Development Mode
Test the server with MCP Inspector:
```bash
uv run mcp dev mcp_postgres/server.py
```

### Production Deployment
Run the server directly:
```bash
python -m mcp_postgres.server
```

### Claude Desktop Integration
Install in Claude Desktop:
```bash
uv run mcp install mcp_postgres/server.py --name "PostgreSQL Server"
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POSTGRES_HOST` | PostgreSQL server hostname | localhost | Yes |
| `POSTGRES_PORT` | PostgreSQL server port | 5432 | No |
| `POSTGRES_DATABASE` | Database name | - | Yes |
| `POSTGRES_USER` | Database username | - | Yes |
| `POSTGRES_PASSWORD` | Database password | - | Yes |

### Example .env file
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=analytics
POSTGRES_USER=readonly_user
POSTGRES_PASSWORD=secure_password
```

## Usage Examples

### Exploring Database Structure
```python
# List all schemas
schemas = await session.call_tool("list_schemas")

# List tables in a schema
tables = await session.call_tool("list_tables", {"schema_name": "public"})

# Get schema information as resource
schema_info = await session.read_resource("postgres://schema/public")
```

### Executing Queries
```python
# Run a simple query
result = await session.call_tool("execute_query", {
    "sql": "SELECT * FROM users WHERE created_at > '2024-01-01'",
    "limit": 50
})

# Data analysis query
result = await session.call_tool("execute_query", {
    "sql": """
        SELECT 
            DATE_TRUNC('month', created_at) as month,
            COUNT(*) as user_count
        FROM users 
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month
    """
})
```

### Using Analysis Prompts
```python
# Get table analysis prompt
prompt = await session.get_prompt("analyze-table", {
    "schema_name": "public",
    "table_name": "orders"
})

# Get data quality check prompt
prompt = await session.get_prompt("data-quality-check", {
    "schema_name": "public"
})
```

## Security Considerations

### Query Safety
- Only `SELECT` statements are allowed
- Dangerous keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.) are blocked
- Automatic query limiting to prevent resource exhaustion
- SQL injection protection through parameterized queries

### Database Access
- Use dedicated read-only database users
- Implement network-level access controls
- Consider using connection pooling for production deployments
- Regular security audits of database permissions

### Recommended Database Setup
```sql
-- Create a read-only user
CREATE USER mcp_readonly WITH PASSWORD 'secure_password';

-- Grant minimal required permissions
GRANT CONNECT ON DATABASE your_database TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO mcp_readonly;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO mcp_readonly;
```

## Architecture

The server uses:
- **FastMCP**: High-level MCP framework for Python
- **psycopg2**: PostgreSQL adapter for database connectivity
- **Environment-based configuration**: Secure credential management
- **Resource-based schema exposure**: Browse database structure
- **Tool-based query execution**: Safe SQL query interface
- **Prompt templates**: Guided data analysis workflows

## Troubleshooting

### Connection Issues
```bash
# Test database connectivity
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='your_db',
    user='your_user',
    password='your_password'
)
print('Connection successful!')
conn.close()
"
```

### Common Errors

1. **"Missing required environment variables"**
   - Ensure all required environment variables are set
   - Check .env file exists and is properly formatted

2. **"Only SELECT queries are allowed"**
   - The server only permits read-only operations
   - Verify your query starts with SELECT

3. **"Failed to connect to PostgreSQL"**
   - Check database credentials and network connectivity
   - Verify PostgreSQL server is running and accessible

## Contributing

Contributions are welcome! Please ensure:
- All queries remain read-only for security
- Proper error handling and logging
- Documentation updates for new features
- Security validation for any new functionality

## License

MIT License - see LICENSE file for details.