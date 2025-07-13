#!/usr/bin/env python3
"""
MCP PostgreSQL Server

A Model Context Protocol server that connects to PostgreSQL databases,
exposes table schemas as resources, provides read-only query tools,
and includes prompts for common data analysis tasks.
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create config from environment variables"""
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DATABASE", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )


@dataclass
class AppContext:
    """Application context with database connection"""
    db_config: DatabaseConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle"""
    db_config = DatabaseConfig.from_env()
    
    # Test database connection
    try:
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password
        )
        conn.close()
        logger.info(f"Successfully connected to PostgreSQL at {db_config.host}:{db_config.port}/{db_config.database}")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise
    
    try:
        yield AppContext(db_config=db_config)
    finally:
        logger.info("Shutting down PostgreSQL MCP server")


# Initialize FastMCP server
mcp = FastMCP(
    "PostgreSQL MCP Server",
    lifespan=app_lifespan
)


def get_db_connection(config: DatabaseConfig):
    """Create a database connection"""
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.user,
        password=config.password,
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def is_read_only_query(sql: str) -> bool:
    """Check if SQL query is read-only (SELECT only)"""
    # Remove comments and normalize whitespace
    sql_clean = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
    sql_clean = sql_clean.strip().upper()
    
    # Check if it starts with SELECT
    if not sql_clean.startswith('SELECT'):
        return False
    
    # Check for dangerous keywords
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'COPY', 'CALL', 'EXEC'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_clean:
            return False
    
    return True


# Resources - Expose table schemas
@mcp.resource("postgres://schema/{schema_name}")
def get_schema_info(schema_name: str) -> str:
    """Get detailed information about a database schema"""
    ctx = mcp.get_context()
    config = ctx.request_context.lifespan_context.db_config
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                # Get schema information
                cur.execute("""
                    SELECT 
                        t.table_name,
                        t.table_type,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length
                    FROM information_schema.tables t
                    LEFT JOIN information_schema.columns c 
                        ON t.table_name = c.table_name 
                        AND t.table_schema = c.table_schema
                    WHERE t.table_schema = %s
                    ORDER BY t.table_name, c.ordinal_position
                """, (schema_name,))
                
                rows = cur.fetchall()
                
                if not rows:
                    return f"Schema '{schema_name}' not found or contains no tables."
                
                # Group by table
                tables = {}
                for row in rows:
                    table_name = row['table_name']
                    if table_name not in tables:
                        tables[table_name] = {
                            'table_type': row['table_type'],
                            'columns': []
                        }
                    
                    if row['column_name']:
                        tables[table_name]['columns'].append({
                            'name': row['column_name'],
                            'type': row['data_type'],
                            'nullable': row['is_nullable'] == 'YES',
                            'default': row['column_default'],
                            'max_length': row['character_maximum_length']
                        })
                
                # Format as readable text
                result = f"Schema: {schema_name}\n\n"
                for table_name, table_info in tables.items():
                    result += f"Table: {table_name} ({table_info['table_type']})\n"
                    result += "Columns:\n"
                    for col in table_info['columns']:
                        nullable = "NULL" if col['nullable'] else "NOT NULL"
                        default = f" DEFAULT {col['default']}" if col['default'] else ""
                        max_len = f"({col['max_length']})" if col['max_length'] else ""
                        result += f"  - {col['name']}: {col['type']}{max_len} {nullable}{default}\n"
                    result += "\n"
                
                return result
                
    except Exception as e:
        return f"Error retrieving schema information: {str(e)}"


@mcp.resource("postgres://table/{schema_name}/{table_name}")
def get_table_info(schema_name: str, table_name: str) -> str:
    """Get detailed information about a specific table"""
    ctx = mcp.get_context()
    config = ctx.request_context.lifespan_context.db_config
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                # Get table and column information
                cur.execute("""
                    SELECT 
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.numeric_scale
                    FROM information_schema.columns c
                    WHERE c.table_schema = %s AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """, (schema_name, table_name))
                
                columns = cur.fetchall()
                
                if not columns:
                    return f"Table '{schema_name}.{table_name}' not found."
                
                # Get table size and row count
                cur.execute("""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size(quote_ident(%s)||'.'||quote_ident(%s))) as size,
                        (SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname = %s) as row_estimate
                """, (schema_name, table_name, table_name))
                
                size_info = cur.fetchone()
                
                # Format result
                result = f"Table: {schema_name}.{table_name}\n"
                if size_info:
                    result += f"Size: {size_info['size']}\n"
                    result += f"Estimated rows: {size_info['row_estimate'] or 'Unknown'}\n"
                result += "\nColumns:\n"
                
                for col in columns:
                    nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                    default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                    
                    # Format type with precision/scale
                    data_type = col['data_type']
                    if col['character_maximum_length']:
                        data_type += f"({col['character_maximum_length']})"
                    elif col['numeric_precision'] and col['numeric_scale'] is not None:
                        data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
                    
                    result += f"  - {col['column_name']}: {data_type} {nullable}{default}\n"
                
                return result
                
    except Exception as e:
        return f"Error retrieving table information: {str(e)}"


# Tools - SQL Query execution
@mcp.tool()
def execute_query(sql: str, limit: Optional[int] = 100) -> Dict[str, Any]:
    """
    Execute a read-only SQL query against the PostgreSQL database.
    
    Args:
        sql: The SQL SELECT query to execute
        limit: Maximum number of rows to return (default: 100, max: 1000)
    
    Returns:
        Dictionary with query results, row count, and execution info
    """
    ctx = mcp.get_context()
    config = ctx.request_context.lifespan_context.db_config
    
    # Validate query is read-only
    if not is_read_only_query(sql):
        return {
            "error": "Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, or DDL operations permitted.",
            "sql": sql
        }
    
    # Validate and enforce limit
    if limit is None or limit > 1000:
        limit = 1000
    if limit < 1:
        limit = 1
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                # Add LIMIT if not present
                sql_with_limit = sql.rstrip(';')
                if not re.search(r'\bLIMIT\s+\d+\b', sql_with_limit, re.IGNORECASE):
                    sql_with_limit += f" LIMIT {limit}"
                
                cur.execute(sql_with_limit)
                rows = cur.fetchall()
                
                # Convert to list of dictionaries for JSON serialization
                results = [dict(row) for row in rows]
                
                return {
                    "results": results,
                    "row_count": len(results),
                    "sql_executed": sql_with_limit,
                    "success": True
                }
                
    except Exception as e:
        return {
            "error": str(e),
            "sql": sql,
            "success": False
        }


@mcp.tool()
def list_schemas() -> Dict[str, Any]:
    """List all available schemas in the database"""
    ctx = mcp.get_context()
    config = ctx.request_context.lifespan_context.db_config
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY schema_name
                """)
                
                schemas = [row['schema_name'] for row in cur.fetchall()]
                
                return {
                    "schemas": schemas,
                    "count": len(schemas),
                    "success": True
                }
                
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


@mcp.tool()
def list_tables(schema_name: str = "public") -> Dict[str, Any]:
    """List all tables in a schema"""
    ctx = mcp.get_context()
    config = ctx.request_context.lifespan_context.db_config
    
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        table_name,
                        table_type,
                        (SELECT reltuples::BIGINT FROM pg_class WHERE relname = table_name) as row_estimate
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    ORDER BY table_name
                """, (schema_name,))
                
                tables = []
                for row in cur.fetchall():
                    tables.append({
                        "name": row['table_name'],
                        "type": row['table_type'],
                        "estimated_rows": row['row_estimate']
                    })
                
                return {
                    "schema": schema_name,
                    "tables": tables,
                    "count": len(tables),
                    "success": True
                }
                
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


# Prompts - Common data analysis tasks
@mcp.prompt("analyze-table")
def analyze_table_prompt(schema_name: str = "public", table_name: str = "") -> str:
    """Generate a prompt for analyzing a database table"""
    if not table_name:
        return f"""
I need to analyze a table in the {schema_name} schema. Please help me:

1. First, list all tables in the {schema_name} schema to see what's available
2. Choose a table to analyze
3. Get the table structure and basic information
4. Generate some analytical queries to understand the data:
   - Row count and basic statistics
   - Distribution of key columns
   - Data quality checks (nulls, duplicates)
   - Interesting patterns or insights

Use the available PostgreSQL tools to explore the data systematically.
"""
    else:
        return f"""
Please analyze the table {schema_name}.{table_name}:

1. Get the table structure and basic information
2. Run analytical queries to understand:
   - Total row count
   - Column data types and constraints
   - Distribution of key columns
   - Check for null values and data quality
   - Sample some representative data
   - Look for interesting patterns

Use the PostgreSQL tools to generate insights about this table.
"""


@mcp.prompt("data-quality-check")
def data_quality_prompt(schema_name: str = "public", table_name: str = "") -> str:
    """Generate a prompt for data quality analysis"""
    if not table_name:
        return f"""
I want to perform a comprehensive data quality check on tables in the {schema_name} schema.

Please help me:
1. List available tables in {schema_name}
2. For each table (or selected tables), check:
   - Missing values (NULL counts per column)
   - Duplicate records
   - Data type consistency
   - Referential integrity
   - Outliers and anomalies
   - Data freshness (if timestamp columns exist)

Generate SQL queries to assess data quality systematically.
"""
    else:
        return f"""
Perform a comprehensive data quality assessment for {schema_name}.{table_name}:

1. Get table structure and identify key columns
2. Check for data quality issues:
   - Count and percentage of NULL values per column
   - Duplicate records (full and partial)
   - Data type violations or unexpected formats
   - Value ranges and outliers
   - Referential integrity (if foreign keys exist)
   - Data consistency patterns

3. Generate a data quality report with findings and recommendations.

Use SQL queries to systematically evaluate data quality.
"""


@mcp.prompt("performance-analysis")
def performance_analysis_prompt(schema_name: str = "public") -> str:
    """Generate a prompt for database performance analysis"""
    return f"""
I need to analyze database performance for the {schema_name} schema.

Please help me examine:

1. Table sizes and growth patterns:
   - Disk space usage by table
   - Row counts and estimated sizes
   - Index usage and effectiveness

2. Query performance considerations:
   - Tables without primary keys
   - Large tables that might benefit from partitioning
   - Columns that might need indexing

3. Generate recommendations for:
   - Index optimization
   - Query performance improvements
   - Schema design suggestions

Use the available PostgreSQL tools to gather performance-related insights.
"""


def main():
    """Main entry point for the MCP server"""
    import asyncio
    
    # Check for required environment variables
    required_vars = ["POSTGRES_HOST", "POSTGRES_DATABASE", "POSTGRES_USER"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        logger.error("- POSTGRES_HOST (default: localhost)")
        logger.error("- POSTGRES_PORT (default: 5432)")
        logger.error("- POSTGRES_DATABASE (required)")
        logger.error("- POSTGRES_USER (required)")
        logger.error("- POSTGRES_PASSWORD (required)")
        exit(1)
    
    logger.info("Starting PostgreSQL MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()