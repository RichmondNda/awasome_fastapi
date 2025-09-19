"""
Terminal Documentation Server for Awasome FastAPI
Provides text-based access to API documentation in development environment.
"""

import json
import httpx
import asyncio
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich import print as rprint
import click

console = Console()

class TerminalDocs:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.openapi_url = f"{self.api_url}/openapi.json"
        self._schema_cache = None

    async def get_openapi_schema(self) -> Dict[str, Any]:
        """Fetch OpenAPI schema with caching."""
        if self._schema_cache is None:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(self.openapi_url)
                    response.raise_for_status()
                    self._schema_cache = response.json()
                except httpx.RequestError as e:
                    console.print(f"[red]❌ Error fetching schema: {e}[/red]")
                    return {}
        return self._schema_cache

    def show_api_info(self, schema: Dict[str, Any]):
        """Display API information."""
        info = schema.get('info', {})
        
        panel_content = f"""
[bold blue]Title:[/bold blue] {info.get('title', 'Unknown')}
[bold blue]Version:[/bold blue] {info.get('version', 'Unknown')}
[bold blue]Description:[/bold blue] {info.get('description', 'No description')}

[bold green]Contact:[/bold green]
  • Name: {info.get('contact', {}).get('name', 'N/A')}
  • Email: {info.get('contact', {}).get('email', 'N/A')}

[bold green]License:[/bold green]
  • Name: {info.get('license', {}).get('name', 'N/A')}
  • URL: {info.get('license', {}).get('url', 'N/A')}
"""
        
        console.print(Panel(panel_content, title="🚀 API Information", border_style="blue"))

    def show_endpoints(self, schema: Dict[str, Any]):
        """Display all endpoints in a formatted table."""
        paths = schema.get('paths', {})
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Method", style="cyan", width=8)
        table.add_column("Endpoint", style="blue", width=40)
        table.add_column("Summary", style="green")
        table.add_column("Tags", style="yellow", width=15)

        for path, methods in paths.items():
            for method, details in methods.items():
                if isinstance(details, dict):
                    summary = details.get('summary', 'No summary')
                    tags = ', '.join(details.get('tags', []))
                    table.add_row(
                        method.upper(),
                        path,
                        summary[:50] + "..." if len(summary) > 50 else summary,
                        tags
                    )

        console.print(table)

    def show_endpoint_details(self, schema: Dict[str, Any], endpoint: str, method: str = None):
        """Show detailed information about a specific endpoint."""
        paths = schema.get('paths', {})
        
        if endpoint not in paths:
            console.print(f"[red]❌ Endpoint '{endpoint}' not found[/red]")
            return

        endpoint_data = paths[endpoint]
        
        if method:
            method = method.lower()
            if method not in endpoint_data:
                console.print(f"[red]❌ Method '{method.upper()}' not found for endpoint '{endpoint}'[/red]")
                return
            methods = {method: endpoint_data[method]}
        else:
            methods = {k: v for k, v in endpoint_data.items() if isinstance(v, dict)}

        for method_name, details in methods.items():
            self._display_method_details(endpoint, method_name.upper(), details)

    def _display_method_details(self, endpoint: str, method: str, details: Dict[str, Any]):
        """Display details for a specific HTTP method."""
        
        # Method header
        console.print(f"\n[bold cyan]{method} {endpoint}[/bold cyan]")
        console.rule()
        
        # Summary and description
        console.print(f"[bold]Summary:[/bold] {details.get('summary', 'No summary')}")
        if desc := details.get('description'):
            console.print(f"[bold]Description:[/bold] {desc}")
        
        # Tags
        if tags := details.get('tags'):
            console.print(f"[bold]Tags:[/bold] {', '.join(tags)}")

        # Request body
        if request_body := details.get('requestBody'):
            console.print(f"\n[bold green]📤 Request Body:[/bold green]")
            if content := request_body.get('content'):
                for content_type, schema_info in content.items():
                    console.print(f"  • Content-Type: [cyan]{content_type}[/cyan]")
                    if schema_ref := schema_info.get('schema', {}).get('$ref'):
                        schema_name = schema_ref.split('/')[-1]
                        console.print(f"  • Schema: [yellow]{schema_name}[/yellow]")

        # Parameters
        if parameters := details.get('parameters'):
            console.print(f"\n[bold blue]📋 Parameters:[/bold blue]")
            param_table = Table(show_header=True)
            param_table.add_column("Name", style="cyan")
            param_table.add_column("In", style="blue")
            param_table.add_column("Type", style="green")
            param_table.add_column("Required", style="red")
            param_table.add_column("Description", style="white")
            
            for param in parameters:
                param_table.add_row(
                    param.get('name', ''),
                    param.get('in', ''),
                    param.get('schema', {}).get('type', 'unknown'),
                    "✓" if param.get('required') else "✗",
                    param.get('description', '')[:40]
                )
            console.print(param_table)

        # Responses
        if responses := details.get('responses'):
            console.print(f"\n[bold magenta]📨 Responses:[/bold magenta]")
            for status_code, response_data in responses.items():
                status_style = "green" if status_code.startswith('2') else "red" if status_code.startswith('4') or status_code.startswith('5') else "yellow"
                console.print(f"  • [{status_style}]{status_code}[/{status_style}]: {response_data.get('description', 'No description')}")

    def show_schemas(self, schema: Dict[str, Any]):
        """Display all available schemas."""
        components = schema.get('components', {})
        schemas = components.get('schemas', {})
        
        if not schemas:
            console.print("[yellow]No schemas found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Schema Name", style="cyan", width=20)
        table.add_column("Type", style="blue", width=15)
        table.add_column("Properties Count", style="green", width=15)
        table.add_column("Description", style="white")

        for name, schema_def in schemas.items():
            schema_type = schema_def.get('type', 'object')
            properties = schema_def.get('properties', {})
            prop_count = len(properties) if properties else 0
            description = schema_def.get('description', 'No description')[:50]
            
            table.add_row(name, schema_type, str(prop_count), description)

        console.print(table)

    def show_schema_details(self, schema: Dict[str, Any], schema_name: str):
        """Show detailed information about a specific schema."""
        components = schema.get('components', {})
        schemas = components.get('schemas', {})
        
        if schema_name not in schemas:
            console.print(f"[red]❌ Schema '{schema_name}' not found[/red]")
            return

        schema_def = schemas[schema_name]
        
        console.print(f"\n[bold cyan]📋 Schema: {schema_name}[/bold cyan]")
        console.rule()
        
        # Basic info
        console.print(f"[bold]Type:[/bold] {schema_def.get('type', 'unknown')}")
        if desc := schema_def.get('description'):
            console.print(f"[bold]Description:[/bold] {desc}")

        # Properties
        if properties := schema_def.get('properties'):
            console.print(f"\n[bold green]Properties:[/bold green]")
            
            prop_table = Table(show_header=True)
            prop_table.add_column("Property", style="cyan", width=20)
            prop_table.add_column("Type", style="blue", width=15)
            prop_table.add_column("Required", style="red", width=10)
            prop_table.add_column("Description", style="white")
            
            required_fields = schema_def.get('required', [])
            
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get('type', 'unknown')
                is_required = "✓" if prop_name in required_fields else "✗"
                prop_desc = prop_def.get('description', '')[:40]
                
                prop_table.add_row(prop_name, prop_type, is_required, prop_desc)
            
            console.print(prop_table)

        # Example
        if example := schema_def.get('example'):
            console.print(f"\n[bold yellow]Example:[/bold yellow]")
            syntax = Syntax(json.dumps(example, indent=2), "json", theme="monokai", line_numbers=True)
            console.print(syntax)

    async def show_live_examples(self):
        """Show live examples by making actual API calls."""
        console.print(Panel("🔴 Live API Examples", border_style="red"))
        
        async with httpx.AsyncClient() as client:
            # Health check example
            try:
                console.print("\n[bold blue]🏥 Health Check Example:[/bold blue]")
                console.print(f"[dim]GET {self.api_url}/system/health[/dim]")
                
                response = await client.get(f"{self.api_url}/system/health")
                if response.status_code == 200:
                    syntax = Syntax(json.dumps(response.json(), indent=2), "json", theme="monokai")
                    console.print(syntax)
                else:
                    console.print(f"[red]❌ Status: {response.status_code}[/red]")
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")

            # System info example
            try:
                console.print(f"\n[bold blue]ℹ️ System Info Example:[/bold blue]")
                console.print(f"[dim]GET {self.api_url}/system/info[/dim]")
                
                response = await client.get(f"{self.api_url}/system/info")
                if response.status_code == 200:
                    syntax = Syntax(json.dumps(response.json(), indent=2), "json", theme="monokai")
                    console.print(syntax)
                else:
                    console.print(f"[red]❌ Status: {response.status_code}[/red]")
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")


@click.group()
def cli():
    """Awasome FastAPI Terminal Documentation"""
    pass

@cli.command()
@click.option('--url', default='http://localhost:8000', help='API base URL')
def info(url):
    """Show API information"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if schema:
            docs.show_api_info(schema)
    
    asyncio.run(run())

@cli.command()
@click.option('--url', default='http://localhost:8000', help='API base URL')
def endpoints(url):
    """List all endpoints"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if schema:
            docs.show_endpoints(schema)
    
    asyncio.run(run())

@cli.command()
@click.argument('endpoint')
@click.option('--method', help='Specific HTTP method')
@click.option('--url', default='http://localhost:8000', help='API base URL')
def endpoint(endpoint, method, url):
    """Show details for a specific endpoint"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if schema:
            docs.show_endpoint_details(schema, endpoint, method)
    
    asyncio.run(run())

@cli.command()
@click.option('--url', default='http://localhost:8000', help='API base URL')
def schemas(url):
    """List all schemas"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if schema:
            docs.show_schemas(schema)
    
    asyncio.run(run())

@cli.command()
@click.argument('schema_name')
@click.option('--url', default='http://localhost:8000', help='API base URL')
def schema(schema_name, url):
    """Show details for a specific schema"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if schema:
            docs.show_schema_details(schema, schema_name)
    
    asyncio.run(run())

@cli.command()
@click.option('--url', default='http://localhost:8000', help='API base URL')
def examples(url):
    """Show live examples"""
    docs = TerminalDocs(url)
    asyncio.run(docs.show_live_examples())

@cli.command()
@click.option('--url', default='http://localhost:8000', help='API base URL')
def interactive(url):
    """Interactive documentation browser"""
    docs = TerminalDocs(url)
    
    async def run():
        schema = await docs.get_openapi_schema()
        if not schema:
            return
            
        while True:
            console.print("\n[bold cyan]🚀 Interactive API Documentation[/bold cyan]")
            console.print("1. API Info")
            console.print("2. List Endpoints") 
            console.print("3. Endpoint Details")
            console.print("4. List Schemas")
            console.print("5. Schema Details")
            console.print("6. Live Examples")
            console.print("7. Exit")
            
            choice = console.input("\n[bold yellow]Choose option (1-7): [/bold yellow]")
            
            if choice == '1':
                docs.show_api_info(schema)
            elif choice == '2':
                docs.show_endpoints(schema)
            elif choice == '3':
                endpoint_path = console.input("Enter endpoint path: ")
                method = console.input("Enter method (optional): ") or None
                docs.show_endpoint_details(schema, endpoint_path, method)
            elif choice == '4':
                docs.show_schemas(schema)
            elif choice == '5':
                schema_name = console.input("Enter schema name: ")
                docs.show_schema_details(schema, schema_name)
            elif choice == '6':
                await docs.show_live_examples()
            elif choice == '7':
                console.print("[green]👋 Goodbye![/green]")
                break
            else:
                console.print("[red]❌ Invalid choice[/red]")
    
    asyncio.run(run())

if __name__ == '__main__':
    cli()