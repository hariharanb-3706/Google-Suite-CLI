"""
Main CLI entry point for GSuite CLI
"""

import logging
import sys
from pathlib import Path

import click
from colorama import init, Fore, Style

from .auth.oauth import OAuthManager
from .utils.formatters import setup_logging, print_success, print_error, print_info, format_output, print_header, print_section, print_key_value_pairs
from .services.calendar import CalendarService
from .services.gmail import GmailService
from .services.sheets import SheetsService
from .services.docs import DocsService
from .services.docs_advanced import AdvancedDocsService
from .services.calendar_advanced import AdvancedCalendarService
from .services.gmail_advanced import AdvancedGmailService
from .services.sheets_advanced import AdvancedSheetsService
from .config.manager import ConfigManager
from .utils.cache import CacheManager, get_global_cache, configure_cache
from .ai import ai as ai_commands
from .ui.interactive import start_interactive_mode

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Global OAuth manager instance
oauth_manager = OAuthManager()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-dir', type=click.Path(), help='Custom configuration directory')
@click.option('--no-cache', is_flag=True, help='Disable caching')
@click.pass_context
def cli(ctx, debug, config_dir, no_cache):
    """
    GSuite CLI - Advanced CLI tool for Google Workspace services
    
    Manage your Google Calendar, Gmail, Sheets, Drive, and Tasks from the command line.
    """
    # Setup logging
    setup_logging(debug)
    
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    ctx.obj['oauth_manager'] = OAuthManager(config_dir) if config_dir else oauth_manager
    ctx.obj['config_manager'] = ConfigManager(config_dir)
    
    # Configure cache based on settings
    config = ctx.obj['config_manager'].config
    if no_cache or not config.cache_enabled:
        configure_cache(enabled=False)
        ctx.obj['cache_manager'] = None
    else:
        cache_manager = CacheManager(
            cache_dir=config.cache_dir,
            default_ttl=config.cache_ttl
        )
        configure_cache(ttl=config.cache_ttl, cache_dir=config.cache_dir, enabled=True)
        ctx.obj['cache_manager'] = cache_manager
    
    # Update debug mode from config if not specified in command line
    if not debug and ctx.obj['config_manager'].get('debug_mode'):
        setup_logging(True)
    
    # Check authentication status
    if not ctx.obj['oauth_manager'].is_authenticated():
        print_info("Not authenticated. Run 'gs auth login' to get started.")


@cli.group()
def auth():
    """Authentication commands"""
    pass


@auth.command()
@click.pass_context
def login(ctx):
    """Authenticate with Google Workspace"""
    print_info("Starting authentication process...")
    
    # Check if credentials file exists
    credentials_file = Path.home() / '.config' / 'gsuite-cli' / 'credentials.json'
    if not credentials_file.exists():
        print_error("Credentials file not found!")
        print_info("Please follow these steps:")
        print_info("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print_info("2. Create a new project or select existing one")
        print_info("3. Enable APIs: Calendar, Gmail, Sheets, Drive, Tasks")
        print_info("4. Create OAuth 2.0 Client ID credentials")
        print_info("5. Download the JSON file and save it as:")
        print_info(f"   {credentials_file}")
        return
    
    # Attempt authentication
    creds = ctx.obj['oauth_manager'].get_credentials()
    if creds:
        print_success("Authentication successful!")
        print_info(f"Token expires: {creds.expiry}")
    else:
        print_error("Authentication failed!")


@auth.command()
@click.pass_context
def logout(ctx):
    """Revoke authentication"""
    if ctx.obj['oauth_manager'].revoke_credentials():
        print_success("Successfully logged out")
    else:
        print_error("No active authentication found")


@auth.command()
@click.pass_context
def status(ctx):
    """Check authentication status"""
    auth_info = ctx.obj['oauth_manager'].get_auth_info()
    
    if auth_info.get('authenticated'):
        print_success("✓ Authenticated")
        print_info(f"Valid: {auth_info.get('valid', 'Unknown')}")
        print_info(f"Expired: {auth_info.get('expired', 'Unknown')}")
        if auth_info.get('token_expiry'):
            print_info(f"Expires: {auth_info['token_expiry']}")
        print_info(f"Has refresh token: {auth_info.get('refresh_token', False)}")
    else:
        print_error("✗ Not authenticated")
        if 'error' in auth_info:
            print_error(f"Error: {auth_info['error']}")


@cli.group()
def calendar():
    """Google Calendar commands"""
    pass


@calendar.command('list')
@click.option('--calendar-id', default='primary', help='Calendar ID')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def calendar_list(ctx, calendar_id, format):
    """List calendar events"""
    cache_manager = ctx.obj.get('cache_manager')
    service = CalendarService(ctx.obj['oauth_manager'], cache_manager)
    events = service.list_events(calendar_id=calendar_id)
    
    if not events:
        print_info("No events found")
        return
    
    # Format events for display
    formatted_events = []
    for event in events:
        formatted_events.append({
            'ID': event['id'][:15] + '...',
            'Title': event['summary'][:30] + ('...' if len(event['summary']) > 30 else ''),
            'Start': event['start'][:10],
            'End': event['end'][:10],
            'Location': event['location'][:20] + ('...' if len(event['location']) > 20 else ''),
        })
    
    output = format_output(formatted_events, format_type=format)
    print(output)


@calendar.command('get')
@click.argument('event_id')
@click.option('--calendar-id', default='primary', help='Calendar ID (default: primary)')
@click.pass_context
def calendar_get(ctx, event_id, calendar_id):
    """Get a specific event"""
    service = CalendarService(ctx.obj['oauth_manager'])
    event = service.get_event(event_id, calendar_id=calendar_id)
    
    if not event:
        print_error("Event not found")
        return
    
    print(f"ID: {event['id']}")
    print(f"Title: {event['summary']}")
    print(f"Description: {event['description']}")
    print(f"Location: {event['location']}")
    print(f"Start: {event['start']}")
    print(f"End: {event['end']}")
    print(f"Status: {event['status']}")


@calendar.command('create')
@click.option('--title', help='Event title')
@click.option('--start', help='Start time (YYYY-MM-DD HH:MM)')
@click.option('--end', help='End time (YYYY-MM-DD HH:MM)')
@click.option('--description', default='', help='Event description')
@click.option('--location', default='', help='Event location')
@click.option('--calendar-id', default='primary', help='Calendar ID (default: primary)')
@click.pass_context
def calendar_create(ctx, title, start, end, description, location, calendar_id):
    """Create a new event"""
    from datetime import datetime, timedelta
    
    # Interactive prompts if required arguments are missing
    if not title:
        title = click.prompt("Event Title")
    
    if not start:
        start = click.prompt("Start time (YYYY-MM-DD HH:MM)")
        
    if not end:
        # Suggest 1 hour duration by default
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M')
            default_end = (start_dt + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
            end = click.prompt("End time (YYYY-MM-DD HH:MM)", default=default_end)
        except ValueError:
            end = click.prompt("End time (YYYY-MM-DD HH:MM)")
    
    if not description and click.confirm("Add description?", default=False):
        description = click.prompt("Description")
        
    if not location and click.confirm("Add location?", default=False):
        location = click.prompt("Location")
    
    try:
        start_time = datetime.strptime(start, '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(end, '%Y-%m-%d %H:%M')
    except ValueError:
        print_error("Invalid datetime format. Use: YYYY-MM-DD HH:MM")
        return
    
    service = CalendarService(ctx.obj['oauth_manager'])
    event_id = service.create_event(
        calendar_id=calendar_id,
        summary=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location
    )
    
    if event_id:
        # Get the full event to display details
        event = service.get_event(event_id, calendar_id=calendar_id)
        if event:
            print_success(f"Event created: {event.get('id')}")
            print(f"Title: {event.get('summary')}")
            print(f"Start: {event.get('start')}")
            print(f"End: {event.get('end')}")
        else:
            print_success(f"Event created successfully (ID: {event_id})")
    else:
        print_error("Failed to create event")


@calendar.command('delete')
@click.argument('event_id')
@click.option('--calendar-id', default='primary', help='Calendar ID (default: primary')
@click.pass_context
def calendar_delete(ctx, event_id, calendar_id):
    """Delete an event"""
    service = CalendarService(ctx.obj['oauth_manager'])
    success = service.delete_event(event_id, calendar_id)
    
    if success:
        print_success(f"Event deleted: {event_id}")
    else:
        print_error("Failed to delete event")


@calendar.command('search')
@click.argument('query')
@click.option('--calendar-id', default='primary', help='Calendar ID (default: primary')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def calendar_search(ctx, query, calendar_id, format):
    """Search events"""
    cache_manager = ctx.obj.get('cache_manager')
    service = CalendarService(ctx.obj['oauth_manager'], cache_manager)
    events = service.search_events(query, calendar_id)
    
    if not events:
        print_info(f"No events found for: {query}")
        return
    
    # Format events for display
    formatted_events = []
    for event in events:
        formatted_events.append({
            'ID': event['id'][:15] + '...',
            'Title': event['summary'][:30] + ('...' if len(event['summary']) > 30 else ''),
            'Start': event['start'][:16],
            'End': event['end'][:16]
        })
    
    output = format_output(formatted_events, format_type=format)
    print(output)


@calendar.command('insights')
@click.option('--days', default=7, help='Number of days to analyze')
@click.pass_context
def calendar_insights(ctx, days):
    """Get AI-powered calendar insights"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedCalendarService(ctx.obj['oauth_manager'], cache_manager)
    
    insights = service.get_smart_schedule_insights(days)
    
    if not insights:
        print_info("No calendar insights available")
        return
    
    print_header("🧠 AI Calendar Insights")
    print_key_value_pairs({
        'Total Events': str(insights.get('total_events', 0)),
        'Busiest Day': insights.get('busiest_day', 'N/A'),
        'Peak Hour': f"{insights.get('peak_hour', 'N/A')}:00" if insights.get('peak_hour') else 'N/A',
        'Meeting Density': f"{insights.get('meeting_density', 0)} events/day",
        'Focus Time Available': f"{insights.get('focus_time_available', 0)} hours",
        'Total Meeting Hours': f"{insights.get('total_meeting_hours', 0)} hours"
    })
    
    if insights.get('recommendations'):
        print_section("AI Recommendations")
        for i, rec in enumerate(insights['recommendations'], 1):
            print(f"{i}. {rec}")


@calendar.command('smart-create')
@click.argument('title')
@click.option('--description', default='', help='Event description')
@click.option('--duration', default=60, help='Duration in minutes')
@click.option('--attendees', help='Comma-separated list of attendee emails')
@click.option('--no-optimal', is_flag=True, help='Skip optimal time finding')
@click.pass_context
def calendar_smart_create(ctx, title, description, duration, attendees, no_optimal):
    """Create event with AI-powered time suggestions"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedCalendarService(ctx.obj['oauth_manager'], cache_manager)
    
    attendee_list = [email.strip() for email in attendees.split(',')] if attendees else None
    
    event_id = service.create_smart_event(
        title=title,
        description=description,
        duration_minutes=duration,
        attendees=attendee_list,
        find_optimal_time=not no_optimal
    )
    
    if event_id:
        print_success(f"Smart event created successfully")
        print_info(f"Event ID: {event_id}")
    else:
        print_error("Failed to create smart event")


@calendar.command('analytics')
@click.option('--days', default=30, help='Number of days to analyze')
@click.pass_context
def calendar_analytics(ctx, days):
    """Get comprehensive calendar analytics"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedCalendarService(ctx.obj['oauth_manager'], cache_manager)
    
    analytics = service.get_calendar_analytics(days)
    
    if not analytics:
        print_info("No calendar analytics available")
        return
    
    print_header("📊 Calendar Analytics")
    print_key_value_pairs({
        'Total Events': str(analytics.get('total_events', 0)),
        'Period Days': str(analytics.get('period_days', 0)),
        'Total Hours': f"{analytics.get('total_hours', 0)} hours",
        'Avg Events/Day': f"{analytics.get('avg_events_per_day', 0)}",
        'Avg Hours/Day': f"{analytics.get('avg_hours_per_day', 0)}",
        'Recurring Events': str(analytics.get('recurring_events', 0)),
        'Events with Attendees': str(analytics.get('events_with_attendees', 0)),
        'Productivity Score': f"{analytics.get('productivity_score', 0)}/100"
    })
    
    if analytics.get('insights'):
        print_section("AI Insights")
        for insight in analytics['insights']:
            print(f"💡 {insight}")


@calendar.command('create-calendar')
@click.option('--summary', help='Calendar summary/title')
@click.option('--description', default='', help='Calendar description')
@click.option('--timezone', default='UTC', help='Timezone (default: UTC)')
@click.pass_context
def calendar_create_calendar(ctx, summary, description, timezone):
    """Create a new secondary calendar"""
    if not summary:
        summary = click.prompt("Calendar Name")
        
    if not description and click.confirm("Add description?", default=False):
        description = click.prompt("Description")

    service = CalendarService(ctx.obj['oauth_manager'])
    calendar = service.create_calendar(summary, description, timezone)
    
    if calendar:
        print_success(f"Created calendar: {calendar.get('id')}")
        print(f"Summary: {calendar.get('summary')}")
        print(f"Description: {calendar.get('description')}")
        print(f"Timezone: {calendar.get('timeZone')}")
    else:
        print_error("Failed to create calendar")


@calendar.command('list-calendars')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def calendar_list_calendars(ctx, format):
    """List all calendars"""
    cache_manager = ctx.obj.get('cache_manager')
    service = CalendarService(ctx.obj['oauth_manager'], cache_manager)
    calendars = service.list_calendars()
    
    if not calendars:
        print_info("No calendars found")
        return
    
    formatted_calendars = []
    for cal in calendars:
        formatted_calendars.append({
            'ID': cal['id'],
            'Summary': cal['summary'],
            'Description': cal['description'],
            'Primary': cal['primary'],
            'Role': cal['access_role']
        })
    
    output = format_output(formatted_calendars, format_type=format)
    print(output)


@cli.group()
def gmail():
    """Gmail commands"""
    pass


@gmail.command('list')
@click.option('--query', default='', help='Search query (Gmail search syntax)')
@click.option('--max-results', default=50, help='Maximum number of messages')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def gmail_list(ctx, query, max_results, format):
    """List email messages"""
    service = GmailService(ctx.obj['oauth_manager'])
    messages = service.list_messages(query=query, max_results=max_results)
    
    if not messages:
        print_info("No messages found")
        return
    
    # Format messages for display
    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            'ID': message['id'],
            'From': message['from'][:25] + ('...' if len(message['from']) > 25 else ''),
            'Subject': message['subject'][:40] + ('...' if len(message['subject']) > 40 else ''),
            'Date': message['date'][:16],
            'Snippet': message['snippet'][:50] + ('...' if len(message['snippet']) > 50 else ''),
        })
    
    output = format_output(formatted_messages, format_type=format)
    print(output)


@gmail.command('get')
@click.argument('message_id')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def gmail_get(ctx, message_id, format):
    """Get a specific email message"""
    service = GmailService(ctx.obj['oauth_manager'])
    message = service.get_message(message_id)
    
    if not message:
        print_error("Message not found")
        return
    
    if format == 'json':
        print(format_output([message], format_type='json'))
    else:
        print(f"From: {message['from']}")
        print(f"To: {message['to']}")
        print(f"Subject: {message['subject']}")
        print(f"Date: {message['date']}")
        print(f"Labels: {', '.join(message['label_ids'])}")
        print("-" * 50)
        print(message['body'])


@gmail.command('send')
@click.option('--to', required=True, help='Recipient email address')
@click.option('--subject', required=True, help='Email subject')
@click.option('--body', required=True, help='Email body (plain text)')
@click.option('--cc', help='CC recipient')
@click.option('--bcc', help='BCC recipient')
@click.option('--html', help='HTML body (optional)')
@click.option('--attach', multiple=True, help='File attachments (can be used multiple times)')
@click.pass_context
def gmail_send(ctx, to, subject, body, cc, bcc, html, attach):
    """Send an email"""
    service = GmailService(ctx.obj['oauth_manager'])
    
    attachments = list(attach) if attach else None
    message_id = service.send_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html_body=html,
        attachments=attachments
    )
    
    if message_id:
        print_success(f"Message sent: {message_id}")
    else:
        print_error("Failed to send message")


@gmail.command('search')
@click.argument('query')
@click.option('--max-results', default=50, help='Maximum number of messages')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def gmail_search(ctx, query, max_results, format):
    """Search messages using Gmail search syntax"""
    service = GmailService(ctx.obj['oauth_manager'])
    messages = service.search_messages(query, max_results=max_results)
    
    if not messages:
        print_info("No messages found")
        return
    
    # Format messages for display
    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            'ID': message['id'],
            'From': message['from'][:25] + ('...' if len(message['from']) > 25 else ''),
            'Subject': message['subject'][:40] + ('...' if len(message['subject']) > 40 else ''),
            'Date': message['date'][:16],
            'Snippet': message['snippet'][:50] + ('...' if len(message['snippet']) > 50 else ''),
        })
    
    output = format_output(formatted_messages, format_type=format)
    print(output)


@gmail.command('delete')
@click.argument('message_id')
@click.pass_context
def gmail_delete(ctx, message_id):
    """Delete a message"""
    service = GmailService(ctx.obj['oauth_manager'])
    success = service.delete_message(message_id)
    
    if success:
        print_success(f"Message deleted: {message_id}")
    else:
        print_error("Failed to delete message")


@gmail.command('read')
@click.argument('message_id')
@click.pass_context
def gmail_read(ctx, message_id):
    """Mark message as read"""
    service = GmailService(ctx.obj['oauth_manager'])
    success = service.mark_as_read(message_id)
    
    if success:
        print_success(f"Message marked as read: {message_id}")
    else:
        print_error("Failed to mark message as read")


@gmail.command('unread')
@click.argument('message_id')
@click.pass_context
def gmail_unread(ctx, message_id):
    """Mark message as unread"""
    service = GmailService(ctx.obj['oauth_manager'])
    success = service.mark_as_unread(message_id)
    
    if success:
        print_success(f"Message marked as unread: {message_id}")
    else:
        print_error("Failed to mark message as unread")


@gmail.command('labels')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def gmail_labels(ctx, format):
    """List Gmail labels"""
    service = GmailService(ctx.obj['oauth_manager'])
    labels = service.get_labels()
    
    if not labels:
        print_info("No labels found")
        return
    
    # Format labels for display
    formatted_labels = []
    for label in labels:
        formatted_labels.append({
            'Name': label['name'],
            'Type': label['type'],
            'Total': label['messages_total'],
            'Unread': label['messages_unread'],
        })
    
    output = format_output(formatted_labels, format_type=format)
    print(output)


@gmail.command('thread')
@click.argument('thread_id')
@click.pass_context
def gmail_thread(ctx, thread_id):
    """Get email thread"""
    service = GmailService(ctx.obj['oauth_manager'])
    thread = service.get_thread(thread_id)
    
    if not thread:
        print_error("Thread not found")
        return
    
    print(f"Thread ID: {thread['id']}")
    print(f"Messages: {len(thread['messages'])}")
    print("=" * 60)
    
    for i, message in enumerate(thread['messages'], 1):
        print(f"\n--- Message {i} ---")
        print(f"From: {message['from']}")
        print(f"To: {message['to']}")
        print(f"Subject: {message['subject']}")
        print(f"Date: {message['date']}")
        print("-" * 40)
        print(message['body'][:500] + ('...' if len(message['body']) > 500 else ''))


@cli.group()
def sheets():
    """Google Sheets commands"""
    pass


@sheets.command('list')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def sheets_list(ctx, format):
    """List all spreadsheets"""
    service = SheetsService(ctx.obj['oauth_manager'])
    spreadsheets = service.list_spreadsheets()
    
    if not spreadsheets:
        print_info("No spreadsheets found")
        return
    
    # Format spreadsheets for display
    formatted_spreadsheets = []
    for spreadsheet in spreadsheets:
        formatted_spreadsheets.append({
            'ID': spreadsheet['id'][:15] + '...',
            'Name': spreadsheet['name'][:40] + ('...' if len(spreadsheet['name']) > 40 else ''),
            'Created': spreadsheet['created_time'][:10] if spreadsheet['created_time'] else '',
            'Modified': spreadsheet['modified_time'][:10] if spreadsheet['modified_time'] else '',
        })
    
    output = format_output(formatted_spreadsheets, format_type=format)
    print(output)


@sheets.command('get')
@click.argument('spreadsheet_id')
@click.option('--range', default='A1:Z100', help='Range to read (default: A1:Z100)')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def sheets_get(ctx, spreadsheet_id, range, format):
    """Read data from a spreadsheet"""
    service = SheetsService(ctx.obj['oauth_manager'])
    values = service.read_range(spreadsheet_id, range)
    
    if not values:
        print_info("No data found in specified range")
        return
    
    if format == 'json':
        print(format_output([{'data': values}], format_type='json'))
    else:
        # Display as table
        output = format_output(values, format_type=format)
        print(output)


@sheets.command('read')
@click.argument('spreadsheet_id')
@click.argument('sheet_name')
@click.option('--header-row', default=1, help='Header row number (default: 1)')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']), help='Output format')
@click.pass_context
def sheets_read(ctx, spreadsheet_id, sheet_name, header_row, format):
    """Read sheet data as structured data with headers"""
    service = SheetsService(ctx.obj['oauth_manager'])
    data = service.get_sheet_data(spreadsheet_id, sheet_name, header_row)
    
    if not data:
        print_info("No data found")
        return
    
    output = format_output(data, format_type=format)
    print(output)


@sheets.command('write')
@click.argument('spreadsheet_id')
@click.argument('range')
@click.argument('data_file')
@click.option('--input-format', default='csv', type=click.Choice(['csv', 'json']), help='Input file format')
@click.pass_context
def sheets_write(ctx, spreadsheet_id, range, data_file, input_format):
    """Write data to a spreadsheet range"""
    import csv
    import json
    
    service = SheetsService(ctx.obj['oauth_manager'])
    
    try:
        # Read data from file
        values = []
        if input_format == 'csv':
            with open(data_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                values = list(reader)
        elif input_format == 'json':
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    # Convert list of dicts to list of lists
                    headers = list(data[0].keys())
                    values = [headers]
                    for row in data:
                        values.append([row.get(h, '') for h in headers])
                else:
                    values = data
        
        success = service.write_range(spreadsheet_id, range, values)
        
        if success:
            print_success(f"Written {len(values)} rows to {range}")
        else:
            print_error("Failed to write data")
            
    except FileNotFoundError:
        print_error(f"File not found: {data_file}")
    except Exception as e:
        print_error(f"Error reading file: {e}")


@sheets.command('append')
@click.argument('spreadsheet_id')
@click.argument('range')
@click.argument('data_file')
@click.option('--input-format', default='csv', type=click.Choice(['csv', 'json']), help='Input file format')
@click.pass_context
def sheets_append(ctx, spreadsheet_id, range, data_file, input_format):
    """Append rows to a spreadsheet"""
    import csv
    import json
    
    service = SheetsService(ctx.obj['oauth_manager'])
    
    try:
        # Read data from file
        values = []
        if input_format == 'csv':
            with open(data_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                values = list(reader)
        elif input_format == 'json':
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    # Convert list of dicts to list of lists
                    headers = list(data[0].keys())
                    values = [headers]
                    for row in data:
                        values.append([row.get(h, '') for h in headers])
                else:
                    values = data
        
        success = service.append_rows(spreadsheet_id, range, values)
        
        if success:
            print_success(f"Appended {len(values)} rows to {range}")
        else:
            print_error("Failed to append data")
            
    except FileNotFoundError:
        print_error(f"File not found: {data_file}")
    except Exception as e:
        print_error(f"Error reading file: {e}")


@sheets.command('create')
@click.argument('title')
@click.pass_context
def sheets_create(ctx, title):
    """Create a new spreadsheet"""
    service = SheetsService(ctx.obj['oauth_manager'])
    spreadsheet_id = service.create_spreadsheet(title)
    
    if spreadsheet_id:
        print_success(f"Created spreadsheet: {spreadsheet_id}")
        print(f"Title: {title}")
        print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    else:
        print_error("Failed to create spreadsheet")


@sheets.command('add-sheet')
@click.argument('spreadsheet_id')
@click.argument('sheet_title')
@click.pass_context
def sheets_add_sheet(ctx, spreadsheet_id, sheet_title):
    """Add a new sheet to a spreadsheet"""
    service = SheetsService(ctx.obj['oauth_manager'])
    sheet_id = service.add_sheet(spreadsheet_id, sheet_title)
    
    if sheet_id is not None:
        print_success(f"Added sheet '{sheet_title}' with ID: {sheet_id}")
    else:
        print_error("Failed to add sheet")


@sheets.command('clear')
@click.argument('spreadsheet_id')
@click.argument('range')
@click.pass_context
def sheets_clear(ctx, spreadsheet_id, range):
    """Clear a range of cells"""
    service = SheetsService(ctx.obj['oauth_manager'])
    success = service.clear_range(spreadsheet_id, range)
    
    if success:
        print_success(f"Cleared range: {range}")
    else:
        print_error("Failed to clear range")


@sheets.command('info')
@click.argument('spreadsheet_id')
@click.pass_context
def sheets_info(ctx, spreadsheet_id):
    """Get spreadsheet information"""
    service = SheetsService(ctx.obj['oauth_manager'])
    spreadsheet = service.get_spreadsheet(spreadsheet_id)
    
    if not spreadsheet:
        print_error("Spreadsheet not found")
        return
    
    print(f"Spreadsheet ID: {spreadsheet['spreadsheet_id']}")
    print(f"Title: {spreadsheet['properties'].get('title', 'Unknown')}")
    print(f"URL: {spreadsheet['spreadsheet_url']}")
    print(f"Sheets: {len(spreadsheet['sheets'])}")
    
    for sheet in spreadsheet['sheets']:
        print(f"\n  Sheet: {sheet['title']}")
        print(f"    ID: {sheet['sheet_id']}")
        print(f"    Index: {sheet['index']}")
        print(f"    Type: {sheet['sheet_type']}")
        grid_props = sheet.get('grid_properties', {})
        print(f"    Size: {grid_props.get('rowCount', '?')} x {grid_props.get('columnCount', '?')}")


@cli.group()
def drive():
    """Google Drive commands"""
    pass


@cli.group()
def tasks():
    """Google Tasks commands"""
    pass


@cli.command('interactive')
@click.option('--no-welcome', is_flag=True, help='Skip welcome screen')
def interactive(no_welcome):
    """Start interactive mode with beautiful UI"""
    if not no_welcome:
        print_info("🚀 Starting GSuite CLI Interactive Mode...")
    
    try:
        start_interactive_mode()
    except KeyboardInterrupt:
        print_info("\n👋 Goodbye!")
    except Exception as e:
        print_error(f"Error starting interactive mode: {e}")


@cli.command()
@click.pass_context
def welcome(ctx):
    """Show welcome screen and start interactive mode"""
    interactive.callback(no_welcome=False)


@cli.group()
def docs():
    """Google Docs commands"""
    pass


@docs.command('list')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def docs_list(ctx, format):
    """List all Google Docs"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    documents = service.list_documents()
    
    if not documents:
        print_info("No documents found")
        return
    
    # Format documents for display
    formatted_docs = []
    for doc in documents:
        formatted_docs.append({
            'ID': doc['id'][:15] + '...',
            'Name': doc['name'][:30] + ('...' if len(doc['name']) > 30 else ''),
            'Created': doc['created'],
            'Modified': doc['modified'],
            'Shared': 'Yes' if doc['shared'] else 'No'
        })
    
    output = format_output(formatted_docs, format_type=format)
    print(output)


@docs.command('get')
@click.argument('document_id')
@click.option('--format', default='text', type=click.Choice(['text', 'json', 'csv']))
@click.pass_context
def docs_get(ctx, document_id, format):
    """Get document content"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    document = service.get_document(document_id)
    
    if not document:
        print_error("Document not found")
        return
    
    if format == 'text':
        print_header(f"📄 {document['name']}")
        print(f"Created: {document['created']}")
        print(f"Modified: {document['modified']}")
        print(f"Words: {document['word_count']}")
        print(f"Characters: {document['char_count']}")
        print()
        print_section("Content")
        print(document['content'][:1000] + ('...' if len(document['content']) > 1000 else ''))
    else:
        # Format as JSON/CSV
        formatted_data = [{
            'ID': document['id'],
            'Name': document['name'],
            'Created': document['created'],
            'Modified': document['modified'],
            'Word Count': document['word_count'],
            'Character Count': document['char_count'],
            'Content': document['content'][:500] + ('...' if len(document['content']) > 500 else '')
        }]
        output = format_output(formatted_data, format_type=format)
        print(output)


@docs.command('create')
@click.argument('title')
@click.option('--content', default='', help='Initial content for the document')
@click.pass_context
def docs_create(ctx, title, content):
    """Create a new document"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    document_id = service.create_document(title, content)
    
    if document_id:
        print_success(f"Document created: {title}")
        print_info(f"Document ID: {document_id}")
    else:
        print_error("Failed to create document")


@docs.command('update')
@click.argument('document_id')
@click.option('--content', required=True, help='Content to update the document with')
@click.option('--append', is_flag=True, help='Append content instead of replacing')
@click.pass_context
def docs_update(ctx, document_id, content, append):
    """Update document content"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    
    if append:
        success = service.append_to_document(document_id, content)
        action = "appended to"
    else:
        success = service.update_document(document_id, content)
        action = "updated"
    
    if success:
        print_success(f"Content {action} document")
    else:
        print_error(f"Failed to {action.rstrip('d')} document")


@docs.command('search')
@click.argument('query')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def docs_search(ctx, query, format):
    """Search documents"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    documents = service.search_documents(query)
    
    if not documents:
        print_info(f"No documents found for: {query}")
        return
    
    # Format documents for display
    formatted_docs = []
    for doc in documents:
        formatted_docs.append({
            'ID': doc['id'][:15] + '...',
            'Name': doc['name'][:40] + ('...' if len(doc['name']) > 40 else ''),
            'Created': doc['created'],
            'Modified': doc['modified'],
            'Owner': doc['owners'][0] if doc['owners'] else 'Unknown'
        })
    
    output = format_output(formatted_docs, format_type=format)
    print(output)


@docs.command('info')
@click.argument('document_id')
@click.pass_context
def docs_info(ctx, document_id):
    """Get document information"""
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    info = service.get_document_info(document_id)
    
    if not info:
        print_error("Document not found")
        return
    
    print_header(f"📄 Document Information")
    print_key_value_pairs({
        'Name': info['name'],
        'ID': info['id'],
        'Created': info['created'],
        'Modified': info['modified'],
        'Size': info['size'],
        'Shared': 'Yes' if info['shared'] else 'No',
        'Permissions': str(info['permission_count']),
        'Web Link': info.get('web_view_link', 'N/A')
    })


@docs.command('template')
@click.argument('template_type')
@click.option('--title', help='Custom title for the document')
@click.option('--project-name', help='Project name (for project template)')
@click.pass_context
def docs_template(ctx, template_type, title, project_name):
    """Create document from template"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    kwargs = {}
    if project_name:
        kwargs['project_name'] = project_name
    
    document_id = service.create_from_template(template_type, title, **kwargs)
    
    if not document_id:
        print_error("Failed to create document from template")


@docs.command('templates')
@click.pass_context
def docs_templates(ctx):
    """List available templates"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    templates = service.list_templates()
    
    print_header("📋 Available Templates")
    for name, info in templates.items():
        print(f"\n{Fore.CYAN}{name}:")
        print(f"  {Fore.WHITE}Title: {info['title']}")
        print(f"  {Fore.WHITE}Description: {info['description']}")


@docs.command('read')
@click.argument('document_id')
@click.option('--format', default='text', type=click.Choice(['text', 'json', 'metadata']))
@click.pass_context
def docs_read(ctx, document_id, format):
    """Read document with advanced metadata"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    if format == 'metadata':
        document = service.get_document_with_metadata(document_id)
    else:
        # Use basic service for simple text view
        basic_service = DocsService(ctx.obj['oauth_manager'], cache_manager)
        document = basic_service.get_document(document_id)
    
    if not document:
        print_error("Document not found")
        return
    
    if format == 'metadata':
        print_header(f"📄 {document['name']}")
        print_key_value_pairs({
            'ID': document['id'],
            'Created': document['created'],
            'Modified': document['modified'],
            'Size': document['size'],
            'Shared': 'Yes' if document['shared'] else 'No',
            'Web Link': document.get('web_view_link', 'N/A'),
            'Revisions': str(document.get('revisions_count', 0)),
            'Collaborators': str(len(document.get('collaborators', [])))
        })
        
        if 'analytics' in document:
            analytics = document['analytics']
            print_section("Document Analytics")
            print_key_value_pairs({
                'Words': str(analytics.get('word_count', 0)),
                'Characters': str(analytics.get('char_count', 0)),
                'Reading Time': f"{analytics.get('estimated_reading_time_minutes', 0)} min",
                'Complexity Score': f"{analytics.get('complexity_score', 0)}/100",
                'Content Type': analytics.get('content_type', 'Unknown')
            })
        
        if document.get('collaborators'):
            print_section("Collaborators")
            for collaborator in document['collaborators']:
                print(f"  👤 {collaborator['name']} ({collaborator['role']})")
        
    else:
        # Simple text view
        print_header(f"📄 {document['name']}")
        print(f"Words: {document.get('word_count', 0)} | Characters: {document.get('char_count', 0)}")
        print()
        print_section("Content")
        content = document.get('content', '')
        print(content[:1000] + ('...' if len(content) > 1000 else ''))


@docs.command('share')
@click.argument('document_id')
@click.argument('email')
@click.option('--role', default='reader', type=click.Choice(['reader', 'writer', 'commenter']))
@click.pass_context
def docs_share(ctx, document_id, email, role):
    """Share document with another user"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    if service.share_document(document_id, email, role):
        print_success(f"Document shared with {email} as {role}")
    else:
        print_error("Failed to share document")


@docs.command('versions')
@click.argument('document_id')
@click.pass_context
def docs_versions(ctx, document_id):
    """Show document version history"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    versions = service.get_document_versions(document_id)
    
    if not versions:
        print_info("No version history available")
        return
    
    print_header(f"📜 Version History")
    for version in versions:
        print(f"📅 {version['modified_time'][:19]}")
        print(f"   👤 {version['modifier']}")
        print(f"   📊 Size: {version['size']} bytes")
        print()


@docs.command('export')
@click.argument('document_id')
@click.option('--format', default='pdf', type=click.Choice(['pdf', 'docx', 'txt', 'html', 'rtf', 'odt']))
@click.option('--output', help='Output file path')
@click.pass_context
def docs_export(ctx, document_id, format, output):
    """Export document in various formats"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    content = service.export_document_advanced(document_id, format)
    
    if not content:
        print_error("Failed to export document")
        return
    
    # Determine output path
    if not output:
        output = f"document_{document_id[:8]}.{format}"
    
    try:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f"Document exported to {output}")
    except Exception as e:
        print_error(f"Failed to save file: {e}")


@docs.command('duplicate')
@click.argument('document_id')
@click.option('--title', help='Title for the duplicated document')
@click.pass_context
def docs_duplicate(ctx, document_id, title):
    """Duplicate a document"""
    cache_manager = ctx.obj.get('cache_manager')
    service = AdvancedDocsService(ctx.obj['oauth_manager'], cache_manager)
    
    new_id = service.duplicate_document(document_id, title)
    
    if new_id:
        print_success(f"Document duplicated successfully")
        print_info(f"New document ID: {new_id}")
    else:
        print_error("Failed to duplicate document")


@docs.command('delete')
@click.argument('document_id')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def docs_delete(ctx, document_id, confirm):
    """Delete a document"""
    if not confirm:
        click.confirm(f"Are you sure you want to delete document {document_id}?", abort=True)
    
    cache_manager = ctx.obj.get('cache_manager')
    service = DocsService(ctx.obj['oauth_manager'], cache_manager)
    
    if service.delete_document(document_id):
        print_success("Document deleted successfully")
    else:
        print_error("Failed to delete document")


@cli.group()
def ai():
    """AI-powered commands and features"""
    pass


@ai.command('ask')
@click.argument('query', required=True)
@click.option('--execute', is_flag=True, help='Execute the suggested command')
@click.pass_context
def ai_ask(ctx, query, execute):
    """Ask AI in natural language and get command suggestions"""
    from .ai.nlp import NaturalLanguageProcessor
    
    print_header("🤖 AI Command Assistant")
    print(f"Query: {query}")
    print()
    
    nlp = NaturalLanguageProcessor()
    parsed = nlp.parse_command(query)
    suggested_command = nlp.suggest_command(query)
    
    print_section("Suggested Command")
    print(f"$ {suggested_command}")
    
    if execute and not suggested_command.startswith('#'):
        print_info(f"Would execute: {suggested_command}")


@ai.command('summarize')
@click.option('--period', default='recent', type=click.Choice(['today', 'week', 'recent']))
@click.pass_context
def ai_summarize(ctx, period):
    """AI-powered summary of your emails and calendar"""
    from .ai.summarizer import EmailSummarizer
    
    print_header("📊 AI Summary")
    print(f"Period: {period}")
    print()
    
    try:
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        emails = gmail_service.list_messages(max_results=10)
        
        if not emails:
            print_info("No emails found for summary")
            return
        
        summarizer = EmailSummarizer()
        summary = summarizer.summarize_multiple_emails(emails)
        
        print_section("Email Summary")
        print(f"📧 {summary['summary']}")
        
        if summary['urgent_emails'] > 0:
            print(f"⚠️  {summary['urgent_emails']} urgent emails")
        
    except Exception as e:
        print_error(f"Error generating summary: {e}")


@ai.command('analytics')
@click.option('--period', default='week', type=click.Choice(['day', 'week', 'month']))
@click.pass_context
def ai_analytics(ctx, period):
    """AI-powered productivity analytics"""
    from .ai.analytics import AIAnalytics
    
    print_header("📈 AI Analytics")
    print(f"Period: {period}")
    print()
    
    try:
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        calendar_service = CalendarService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        
        emails = gmail_service.list_messages(max_results=20)
        events = calendar_service.list_events(max_results=20)
        
        analytics = AIAnalytics()
        analysis = analytics.analyze_productivity(emails, events, period)
        
        if 'message' in analysis:
            print_info(analysis['message'])
            return
        
        print_section("Productivity Score")
        score = analysis['productivity_score']
        score_emoji = "🏆" if score >= 80 else "✅" if score >= 60 else "⚠️"
        print(f"{score_emoji} {score}/100")
        
        if analysis['insights']:
            print_section("AI Insights")
            for insight in analysis['insights']:
                print(f"💡 {insight}")
        
    except Exception as e:
        print_error(f"Error generating analytics: {e}")


@cli.group()
def cache():
    """Cache management commands"""
    pass


@cache.command('status')
@click.pass_context
def cache_status(ctx):
    """Show cache status and statistics"""
    cache_manager = ctx.obj.get('cache_manager')
    
    if not cache_manager:
        print_info("Caching is disabled")
        return
    
    stats = cache_manager.get_stats()
    
    print_header("Cache Statistics")
    print(f"Total items: {stats['total_items']}")
    print(f"Cache size: {stats['cache_size_mb']} MB")
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate_percent']}%")
    print(f"Cache directory: {stats['cache_dir']}")


@cache.command('clear')
@click.option('--service', help='Clear cache for specific service only')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def cache_clear(ctx, service, confirm):
    """Clear cache"""
    cache_manager = ctx.obj.get('cache_manager')
    
    if not cache_manager:
        print_info("Caching is disabled")
        return
    
    if not confirm:
        if service:
            click.confirm(f"Clear cache for '{service}' service?", abort=True)
        else:
            click.confirm("Clear all cache?", abort=True)
    
    if service:
        count = cache_manager.expire(service)
        print_success(f"Cleared {count} cache entries for '{service}'")
    else:
        cache_manager.clear()
        print_success("Cache cleared successfully")


@cache.command('stats')
@click.option('--service', help='Show stats for specific service')
@click.pass_context
def cache_stats(ctx, service):
    """Show detailed cache statistics"""
    cache_manager = ctx.obj.get('cache_manager')
    
    if not cache_manager:
        print_info("Caching is disabled")
        return
    
    stats = cache_manager.get_stats()
    
    if service:
        print_section(f"{service.upper()} Cache Stats")
    else:
        print_section("Global Cache Stats")
    
    print_key_value_pairs({
        'Total Items': stats['total_items'],
        'Cache Size (MB)': stats['cache_size_mb'],
        'Cache Hits': stats['hits'],
        'Cache Misses': stats['misses'],
        'Hit Rate (%)': stats['hit_rate_percent'],
        'Cache Sets': stats['sets'],
        'Cache Directory': stats['cache_dir']
    })


@cache.command('vacuum')
@click.pass_context
def cache_vacuum(ctx):
    """Vacuum cache to reclaim space"""
    cache_manager = ctx.obj.get('cache_manager')
    
    if not cache_manager:
        print_info("Caching is disabled")
        return
    
    if cache_manager.vacuum():
        print_success("Cache vacuumed successfully")
    else:
        print_error("Failed to vacuum cache")


@cache.command('configure')
@click.option('--ttl', type=int, help='Default TTL in seconds')
@click.option('--enable/--disable', default=None, help='Enable or disable cache')
@click.pass_context
def cache_configure(ctx, ttl, enable):
    """Configure cache settings"""
    config_manager = ctx.obj['config_manager']
    
    if ttl is not None:
        config_manager.set('cache_ttl', ttl)
        print_success(f"Cache TTL set to {ttl} seconds")
    
    if enable is not None:
        config_manager.set('cache_enabled', enable)
        status = "enabled" if enable else "disabled"
        print_success(f"Caching {status}")
    
    config_manager.save_config()
    
    # Show current settings
    print_section("Current Cache Settings")
    print(f"Enabled: {config_manager.get('cache_enabled')}")
    print(f"TTL: {config_manager.get('cache_ttl')} seconds")
    print(f"Cache Dir: {config_manager.get('cache_dir') or 'Default'}")


@cli.group()
def config():
    """Configuration management"""
    pass


@config.command('get')
@click.argument('key')
@click.pass_context
def config_get(ctx, key):
    """Get a configuration value"""
    config_manager = ctx.obj['config_manager']
    value = config_manager.get(key)
    
    if value is not None:
        print(f"{key}: {value}")
    else:
        print_error(f"Configuration key '{key}' not found")


@config.command('set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key, value):
    """Set a configuration value"""
    config_manager = ctx.obj['config_manager']
    
    # Try to parse as JSON for complex values
    try:
        import json
        if value.lower() in ['true', 'false']:
            parsed_value = value.lower() == 'true'
        elif value.isdigit():
            parsed_value = int(value)
        elif value.replace('.', '').isdigit():
            parsed_value = float(value)
        else:
            try:
                parsed_value = json.loads(value)
            except:
                parsed_value = value
    except:
        parsed_value = value
    
    if config_manager.set(key, parsed_value):
        config_manager.save_config()
        print_success(f"Set {key} = {parsed_value}")
    else:
        print_error(f"Failed to set {key}")


@config.command('list')
@click.option('--section', help='Show specific configuration section')
@click.pass_context
def config_list(ctx, section):
    """List configuration values"""
    config_manager = ctx.obj['config_manager']
    
    if section:
        config_data = config_manager.get_section(section)
        if config_data:
            print(f"\n{section.upper()} Configuration:")
            print("-" * 40)
            for key, value in config_data.items():
                print(f"  {key}: {value}")
        else:
            print_error(f"Section '{section}' not found")
    else:
        config_data = config_manager.get_all()
        print("\nGlobal Configuration:")
        print("-" * 40)
        
        for section_name, section_data in config_data.items():
            if isinstance(section_data, dict):
                print(f"\n{section_name.upper()}:")
                for key, value in section_data.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {section_name}: {section_data}")


@config.command('reset')
@click.confirmation_option(prompt='Are you sure you want to reset all configuration to defaults?')
@click.pass_context
def config_reset(ctx):
    """Reset configuration to defaults"""
    config_manager = ctx.obj['config_manager']
    
    if config_manager.reset_to_defaults():
        config_manager.save_config()
        print_success("Configuration reset to defaults")


@config.command('save')
@click.option('--format', default='yaml', type=click.Choice(['yaml', 'json']), help='File format')
@click.pass_context
def config_save(ctx, format):
    """Save current configuration"""
    config_manager = ctx.obj['config_manager']
    config_manager.save_config(format)


@config.command('export')
@click.argument('file_path')
@click.option('--format', default='yaml', type=click.Choice(['yaml', 'json']), help='File format')
@click.pass_context
def config_export(ctx, file_path, format):
    """Export configuration to file"""
    config_manager = ctx.obj['config_manager']
    config_manager.export_config(file_path, format)


@config.command('import')
@click.argument('file_path')
@click.pass_context
def config_import(ctx, file_path):
    """Import configuration from file"""
    config_manager = ctx.obj['config_manager']
    
    if config_manager.import_config(file_path):
        config_manager.save_config()


@config.command('validate')
@click.pass_context
def config_validate(ctx):
    """Validate configuration"""
    config_manager = ctx.obj['config_manager']
    issues = config_manager.validate_config()
    
    if not issues:
        print_success("Configuration is valid")
    else:
        print_error("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")


@config.command('edit')
@click.pass_context
def config_edit(ctx):
    """Open configuration file in default editor"""
    import os
    import subprocess
    
    config_manager = ctx.obj['config_manager']
    config_file = config_manager.config_file
    
    if not config_file.exists():
        config_manager.save_config()
    
    editor = os.environ.get('EDITOR', 'nano')
    try:
        subprocess.call([editor, str(config_file)])
        print_info(f"Configuration file opened in {editor}")
        print_info("Run 'gs config validate' after editing to check for issues")
    except Exception as e:
        print_error(f"Failed to open editor: {e}")
        print_info(f"You can manually edit: {config_file}")

cli.add_command(ai_commands)


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        print_info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        if '--debug' in sys.argv:
            logging.exception("Unexpected error")
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
