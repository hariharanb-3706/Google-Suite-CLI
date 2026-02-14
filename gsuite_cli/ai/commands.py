"""
AI command implementations
"""

import click
import logging
from typing import Dict, Any, List

from ..auth.oauth import OAuthManager
from ..services.calendar import CalendarService
from ..services.gmail import GmailService
from ..utils.formatters import print_success, print_info, print_error, format_output, print_header
from .nlp import NaturalLanguageProcessor
from .summarizer import EmailSummarizer
from .analytics import AIAnalytics
from .chatbot import AIChatBot

logger = logging.getLogger(__name__)


@click.group()
def ai():
    """AI-powered commands and features"""
    pass


@ai.command('ask')
@click.argument('query', required=True)
@click.option('--execute', is_flag=True, help='Execute the suggested command')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def ai_ask(ctx, query, execute, format):
    """Ask AI in natural language and get command suggestions"""
    nlp = NaturalLanguageProcessor()
    
    print_header("🤖 AI Command Assistant")
    print(f"Query: {query}")
    print()
    
    # Parse the natural language query
    parsed = nlp.parse_command(query)
    
    print_section("Intent Analysis")
    print(f"Intent: {parsed['intent']}")
    print(f"Confidence: {parsed['confidence'] * 100}%")
    
    if parsed['entities']:
        print("Entities found:")
        for entity_type, value in parsed['entities'].items():
            if isinstance(value, list):
                print(f"  {entity_type}: {', '.join(str(v) for v in value)}")
            else:
                print(f"  {entity_type}: {value}")
    
    print()
    
    # Suggest command
    suggested_command = nlp.suggest_command(query)
    print_section("Suggested Command")
    print(f"$ {suggested_command}")
    
    # Execute if requested
    if execute and not suggested_command.startswith('#'):
        print()
        print_section("Executing Command")
        try:
            # This is a simplified execution - in production, you'd want proper command routing
            if 'calendar' in suggested_command:
                # Execute calendar command
                service = CalendarService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
                events = service.list_events()
                if events:
                    formatted_events = []
                    for event in events[:10]:  # Limit to 10 for demo
                        formatted_events.append({
                            'ID': event['id'][:15] + '...',
                            'Title': event['summary'][:30],
                            'Start': event['start'][:10],
                            'End': event['end'][:10]
                        })
                    output = format_output(formatted_events, format_type=format)
                    print(output)
                else:
                    print_info("No events found")
            
            elif 'gmail' in suggested_command:
                # Execute gmail command
                service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
                emails = service.list_messages(max_results=10)
                if emails:
                    formatted_emails = []
                    for email in emails:
                        formatted_emails.append({
                            'ID': email['id'][:15] + '...',
                            'From': email['from'][:30],
                            'Subject': email['subject'][:40],
                            'Date': email['date'][:10],
                            'Snippet': email['snippet'][:50] + '...'
                        })
                    output = format_output(formatted_emails, format_type=format)
                    print(output)
                else:
                    print_info("No emails found")
            
            print_success("Command executed successfully!")
            
        except Exception as e:
            print_error(f"Error executing command: {e}")


@ai.command('summarize')
@click.option('--period', default='recent', type=click.Choice(['today', 'week', 'recent']))
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def ai_summarize(ctx, period, format):
    """AI-powered summary of your emails and calendar"""
    summarizer = EmailSummarizer()
    
    print_header("📊 AI Summary")
    print(f"Period: {period}")
    print()
    
    try:
        # Get emails
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        emails = gmail_service.list_messages(max_results=20)
        
        if not emails:
            print_info("No emails found for summary")
            return
        
        # Generate summary
        summary = summarizer.summarize_multiple_emails(emails)
        
        print_section("Email Summary")
        print(f"📧 {summary['summary']}")
        
        if summary['themes']:
            print(f"🏷️  Themes: {', '.join(summary['themes'])}")
        
        if summary['urgent_emails'] > 0:
            print(f"⚠️  {summary['urgent_emails']} urgent emails")
        
        print()
        
        # Show insights
        if summary['insights']:
            print_section("AI Insights")
            for insight in summary['insights']:
                print(f"💡 {insight}")
            print()
        
        # Show top senders
        if summary['top_senders']:
            print_section("Top Communicators")
            for sender, count in summary['top_senders'][:5]:
                print(f"📨 {sender}: {count} emails")
            print()
        
        # Show sentiment breakdown
        if format == 'table':
            print_section("Sentiment Analysis")
            sentiment_data = []
            for sentiment_type, count in summary['sentiment_breakdown'].items():
                sentiment_data.append({
                    'Type': sentiment_type.capitalize(),
                    'Count': count,
                    'Percentage': round(count / summary['total_emails'] * 100, 1)
                })
            output = format_output(sentiment_data, format_type=format)
            print(output)
        
    except Exception as e:
        print_error(f"Error generating summary: {e}")


@ai.command('analytics')
@click.argument('type_', default='overview', type=click.Choice(['overview', 'productivity', 'email', 'calendar']))
@click.option('--period', default='week', type=click.Choice(['day', 'week', 'month']))
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def ai_analytics(ctx, type_, period, format):
    """AI-powered productivity analytics"""
    analytics = AIAnalytics()
    
    print_header("📈 AI Analytics")
    print(f"Type: {type_}")
    print(f"Period: {period}")
    print()
    
    try:
        # Get data
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        calendar_service = CalendarService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        
        emails = gmail_service.list_messages(max_results=50)
        events = calendar_service.list_events(max_results=50)
        
        # Generate analysis
        analysis = analytics.analyze_productivity(emails, events, period)
        
        if 'message' in analysis:
            print_info(analysis['message'])
            return
        
        # Show productivity score
        print_section("Productivity Score")
        score = analysis['productivity_score']
        score_emoji = "🏆" if score >= 80 else "✅" if score >= 60 else "⚠️" if score >= 40 else "❌"
        print(f"{score_emoji} {score}/100")
        print()
        
        # Show insights
        if analysis['insights']:
            print_section("AI Insights")
            for insight in analysis['insights']:
                print(f"💡 {insight}")
            print()
        
        # Show recommendations
        if analysis['recommendations']:
            print_section("Recommendations")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"{i}. {rec}")
            print()
        
        # Show detailed analysis based on type
        if type_ == 'email' and analysis['email_analysis']:
            print_section("Email Analysis")
            email_data = analysis['email_analysis']
            print(f"📧 Total emails: {email_data['total']}")
            print(f"📊 Emails per day: {email_data['emails_per_day']}")
            print(f"📈 Recent emails: {email_data['recent_emails']}")
            print()
        
        elif type_ == 'calendar' and analysis['calendar_analysis']:
            print_section("Calendar Analysis")
            calendar_data = analysis['calendar_analysis']
            print(f"📅 Total events: {calendar_data['total']}")
            print(f"🤝 Meetings: {calendar_data['meetings']}")
            print(f"🏠 Personal events: {calendar_data['personal']}")
            print()
        
        elif type_ == 'productivity':
            print_section("Time Analysis")
            time_data = analysis['time_analysis']
            if time_data['peak_hours']:
                print(f"⏰ Peak hours: {', '.join(time_data['peak_hours'])}")
            print()
        
        # Format detailed data if requested
        if format == 'json':
            print_section("Full Analysis Data")
            print(format_output([analysis], format_type='json'))
        
    except Exception as e:
        print_error(f"Error generating analytics: {e}")


@ai.command('smart-reply')
@click.argument('email_id')
@click.option('--count', default=3, help='Number of smart replies to generate')
@click.pass_context
def ai_smart_reply(ctx, email_id, count):
    """Generate AI-powered smart replies for an email"""
    summarizer = EmailSummarizer()
    
    print_header("🤖 Smart Reply Generator")
    print(f"Email ID: {email_id}")
    print()
    
    try:
        # Get email
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        email = gmail_service.get_message(email_id)
        
        if not email:
            print_error("Email not found")
            return
        
        # Generate summary and smart replies
        summary = summarizer.summarize_email(email)
        
        print_section("Email Summary")
        print(f"📝 {summary['summary']}")
        print(f"😊 Sentiment: {summary['sentiment']}")
        print(f"⚡ Urgency: {summary['urgency']}")
        print()
        
        if summary['action_items']:
            print_section("Action Items")
            for i, action in enumerate(summary['action_items'], 1):
                print(f"{i}. {action}")
            print()
        
        print_section("Smart Replies")
        for i, reply in enumerate(summary['smart_replies'][:count], 1):
            print(f"{i}. {reply}")
        
        print()
        print_info("Choose a reply or compose your own response")
        
    except Exception as e:
        print_error(f"Error generating smart replies: {e}")


@ai.command('chat')
@click.argument('message', required=False)
@click.pass_context
def ai_chat(ctx, message):
    """Chat with AI to clarify doubts (Powered by Gemini)"""
    config = ctx.obj['config_manager'].config.ai
    chatbot = AIChatBot(gemini_key=config.gemini_api_key)
    
    if message:
        # Single message mode
        print_info("Thinking...")
        response = chatbot.chat(message)
        print(f"\n🤖 AI: {response}\n")
    else:
        # Interactive chat mode
        print_header("🤖 AI Chatbot (Gemini)")
        print_info("Type your questions below. Type 'exit' or 'quit' to stop.")
        
        while True:
            user_input = click.prompt("\n👤 You")
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print_info("Goodbye!")
                break
            
            print_info("Thinking...")
            response = chatbot.chat(user_input)
            print(f"\n🤖 AI: {response}")


@ai.command('insights')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']))
@click.pass_context
def ai_insights(ctx, format):
    """Generate AI-powered insights from your data"""
    analytics = AIAnalytics()
    summarizer = EmailSummarizer()
    
    print_header("🧠 AI Insights")
    print()
    
    try:
        # Get data
        gmail_service = GmailService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        calendar_service = CalendarService(ctx.obj['oauth_manager'], ctx.obj.get('cache_manager'))
        
        emails = gmail_service.list_messages(max_results=30)
        events = calendar_service.list_events(max_results=30)
        
        # Generate comprehensive insights
        productivity_analysis = analytics.analyze_productivity(emails, events, 'week')
        email_summary = summarizer.summarize_multiple_emails(emails)
        
        # Productivity insights
        print_section("📈 Productivity Insights")
        if 'insights' in productivity_analysis:
            for insight in productivity_analysis['insights']:
                print(f"💡 {insight}")
        print()
        
        # Communication insights
        print_section("💬 Communication Insights")
        if email_summary['top_senders']:
            top_sender = email_summary['top_senders'][0]
            print(f"👥 Most communication with: {top_sender[0]} ({top_sender[1]} emails)")
        
        if email_summary['themes']:
            print(f"🏷️  Common themes: {', '.join(email_summary['themes'][:3])}")
        
        if email_summary['urgent_emails'] > 0:
            print(f"⚠️  {email_summary['urgent_emails']} emails need immediate attention")
        print()
        
        # Recommendations
        if 'recommendations' in productivity_analysis:
            print_section("🎯 AI Recommendations")
            for i, rec in enumerate(productivity_analysis['recommendations'][:5], 1):
                print(f"{i}. {rec}")
        
    except Exception as e:
        print_error(f"Error generating insights: {e}")


def print_section(title: str):
    """Print section header"""
    print(f"\n▶ {title}")
    print("-" * (len(title) + 3))
