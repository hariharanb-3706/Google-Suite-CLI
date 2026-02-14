"""
Interactive CLI UI and menu system
"""

import os
import time
import sys
import shutil
from typing import Dict, List, Any, Optional
import click
from colorama import init, Fore, Style, Back

init(autoreset=True)


class InteractiveMenu:
    """Interactive CLI menu system with beautiful UI"""
    
    def __init__(self):
        self.options = {
            '1': {
                'name': '📅 Calendar',
                'description': 'Manage events and schedules',
                'color': Fore.BLACK,
                'commands': ['list', 'create', 'update', 'delete', 'search', 'create-calendar', 'list-calendars']
            },
            '2': {
                'name': '📧 Gmail', 
                'description': 'Read and send emails',
                'color': Fore.BLACK,
                'commands': ['list', 'send', 'search', 'get']
            },
            '3': {
                'name': '📊 Sheets',
                'description': 'Manage spreadsheets',
                'color': Fore.GREEN,
                'commands': ['list', 'read', 'write', 'create']
            },
            '4': {
                'name': '📄 Docs',
                'description': 'Manage documents',
                'color': Fore.BLACK,
                'commands': ['list', 'create', 'read', 'update', 'search']
            },
            '5': {
                'name': '🤖 AI Assistant',
                'description': 'AI-powered features',
                'color': Fore.BLACK,
                'commands': ['chat', 'ask', 'summarize', 'analytics', 'insights']
            },
            '6': {
                'name': '⚙️  Settings',
                'description': 'Configure and manage',
                'color': Fore.BLACK,
                'commands': ['config', 'cache', 'auth']
            },
            '7': {
                'name': '📈 Analytics',
                'description': 'View productivity insights',
                'color': Fore.RED,
                'commands': ['productivity', 'usage', 'performance']
            },
            '8': {
                'name': '❓ Help',
                'description': 'Get help and tutorials',
                'color': Fore.BLACK,
                'commands': ['commands', 'examples', 'tutorial']
            }
        }
    
    def get_width(self) -> int:
        """Get current terminal width"""
        return shutil.get_terminal_size((80, 20)).columns

    def get_display_width(self, text: str) -> int:
        """Estimate display width of text, accounting for double-width emojis"""
        # A very simple heuristic: count characters, adding 1 for common emojis in this app
        emojis = ["📅", "📧", "📊", "📄", "🤖", "⚙️", "📈", "❓", "🎯", "🚀", "👋", "⚡", "💚", "✅", "❌", "💡"]
        width = len(text)
        for emoji in emojis:
            width += text.count(emoji)
        return width

    def draw_box(self, content: List[str], color=Fore.BLACK, padding: int = 2):
        """Draw a centered box with content"""
        term_width = self.get_width()
        
        # Calculate max width needed for content
        max_content_width = 0
        for line in content:
            max_content_width = max(max_content_width, self.get_display_width(line))
        
        box_width = min(term_width - 4, max_content_width + (padding * 2) + 2)
        if box_width < 10: box_width = 10 # Minimum width
        
        # Center the box
        offset = (term_width - box_width) // 2
        margin = " " * offset
        
        print(margin + color + Style.BRIGHT + "╔" + "═" * (box_width - 2) + "╗")
        for line in content:
            display_width = self.get_display_width(line)
            
            # Handle potential overflow
            if display_width > box_width - 2:
                # Truncate if too long (simple char truncation for now)
                line = line[:box_width - 5] + "..."
                display_width = self.get_display_width(line)
            
            inner_padding = (box_width - 2 - display_width) // 2
            right_padding = box_width - 2 - display_width - inner_padding
            
            print(margin + color + Style.BRIGHT + "║" + " " * inner_padding + line + " " * right_padding + "║")
        print(margin + color + Style.BRIGHT + "╚" + "═" * (box_width - 2) + "╝")

    def show_welcome(self):
        """Show dynamic welcome screen"""
        self.clear_screen()
        width = self.get_width()
        
        logo_lines = [
            "████████╗███████╗██████╗ ███╗   ███╗██╗███╗   ██╗ █████╗ ██╗",
            "╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║████╗  ██║██╔══██╗██║",
            "   ██║   █████╗  ██████╔╝██╔████╔██║██║██╔██╗ ██║███████║██║",
            "   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██║╚██╗██║██╔══██║██║",
            "   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║ ╚████║██║  ██║███████╗",
            "   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝",
            "",
            "🚀 WORKSPACE CLI 🚀"
        ]
        
        for line in logo_lines:
            display_width = self.get_display_width(line)
            offset = max(0, (width - display_width) // 2)
            print(Fore.BLACK + Style.BRIGHT + " " * offset + line)
        
        print()
        tagline = "🤖 AI-Powered • ⚡ Lightning Fast • 📊 Productivity Focused"
        print(Fore.GREEN + Style.BRIGHT + tagline.center(width))
        print()
        
        self.show_quick_stats()
        print()
        self.loading_animation("Loading your workspace".center(width), 1)

    def show_quick_stats(self):
        """Show quick statistics in a centered box"""
        stats = [
            "📊 Productivity Score: 85/100",
            "📧 Unread Emails: 5",
            "📅 Today's Events: 3",
            "🤖 AI Insights Available"
        ]
        self.draw_box(stats, color=Fore.BLACK)

    def show_main_menu(self):
        """Show main interactive menu with dynamic centering"""
        self.clear_screen()
        width = self.get_width()
        
        self.draw_box(["🎯 MAIN MENU"], padding=10)
        print()
        
        # Center the options block
        max_opt_len = 0
        for key, option in self.options.items():
            # Calculate effective length, accounting for color codes if necessary, or just content
            # For simplicity, let's estimate based on visible characters
            line_len = len(f"[{key}] {option['name']}  {option['description']}")
            max_opt_len = max(max_opt_len, line_len)
        
        # Adjust max_opt_len for the formatted options
        max_opt_len_formatted = 0
        for key, option in self.options.items():
            # The display width is: [K] (4) + display_width(name) + spaces + display_width(description)
            # name is padded to 15 chars, but we need to know how many cells that takes.
            name_display_width = self.get_display_width(option['name'])
            padding_needed = max(0, 15 - len(option['name']))
            total_name_width = name_display_width + padding_needed
            
            current_len = 4 + total_name_width + self.get_display_width(option['description'])
            max_opt_len_formatted = max(max_opt_len_formatted, current_len)

        offset = (width - max_opt_len_formatted) // 2
        margin = " " * offset
        
        for key, option in self.options.items():
            option_num = f"{Fore.BLACK + Style.BRIGHT}[{key}]{Style.RESET_ALL} "
            option_name = option['color'] + Style.BRIGHT + f"{option['name']:<15}"
            option_desc = Fore.BLACK + option['description']
            print(margin + option_num + option_name + option_desc)
        
        print()
        print(margin + Fore.RED + Style.BRIGHT + "  [0] Exit")
        print()
        print(margin + Fore.BLACK + "  Choose an option [1-8, 0]: ", end="")
    
    def show_service_menu(self, service_key: str):
        """Show service-specific menu with dynamic layout"""
        if service_key not in self.options:
            return
        
        service = self.options[service_key]
        self.clear_screen()
        width = self.get_width()
        
        # Header
        self.draw_box([f"{service['name']} MENU"], color=service['color'], padding=10)
        print()
        
        # Center description and commands
        content_width = max(len(service['description']), 30)
        offset = (width - content_width) // 2
        margin = " " * offset
        
        print(margin + Fore.BLACK + Style.BRIGHT + service['description'])
        print()
        
        # Show available commands
        for i, command in enumerate(service['commands'], 1):
            print(margin + f"  {Fore.BLACK + Style.BRIGHT}[{i}]{Style.RESET_ALL} {service['color']}{command.capitalize()}")
        
        print()
        print(margin + Fore.BLACK + "  [b] Back to Main Menu")
        print(margin + Fore.RED + "  [0] Exit")
        print()
        print(margin + Fore.BLACK + "  Choose an option: ", end="")
    
    def get_user_choice(self) -> str:
        """Get user input with validation"""
        try:
            choice = input().strip().lower()
            return choice
        except (KeyboardInterrupt, EOFError):
            return '0'
    
    def handle_service_choice(self, service_key: str, command_num: str):
        """Handle service-specific command choice"""
        if service_key not in self.options:
            return
        
        service = self.options[service_key]
        commands = service['commands']
        
        try:
            cmd_index = int(command_num) - 1
            if 0 <= cmd_index < len(commands):
                command = commands[cmd_index]
                self.execute_command(service_key, command)
            else:
                self.show_error("Invalid command number")
        except ValueError:
            self.show_error("Please enter a valid number")
    
    def execute_command(self, service_key: str, command: str):
        """Execute the selected command"""
        self.clear_screen()
        
        # Command header
        service = self.options[service_key]
        print(Fore.BLACK + Style.BRIGHT + f"🚀 Executing: {service['name']} - {command.capitalize()}")
        print("=" * 60)
        print()
        
        # Map to actual CLI commands
        python_exe = f'"{sys.executable}"'
        command_map = {
            '1': {  # Calendar
                'list': f'{python_exe} -m gsuite_cli.cli calendar list',
                'create': f'{python_exe} -m gsuite_cli.cli calendar create',
                'update': f'{python_exe} -m gsuite_cli.cli calendar update',
                'delete': f'{python_exe} -m gsuite_cli.cli calendar delete',
                'search': f'{python_exe} -m gsuite_cli.cli calendar search',
                'create-calendar': f'{python_exe} -m gsuite_cli.cli calendar create-calendar',
                'list-calendars': f'{python_exe} -m gsuite_cli.cli calendar list-calendars'
            },
            '2': {  # Gmail
                'list': f'{python_exe} -m gsuite_cli.cli gmail list',
                'send': f'{python_exe} -m gsuite_cli.cli gmail send --help',
                'search': f'{python_exe} -m gsuite_cli.cli gmail search --help',
                'get': f'{python_exe} -m gsuite_cli.cli gmail get'
            },
            '3': {  # Sheets
                'list': f'{python_exe} -m gsuite_cli.cli sheets list',
                'read': f'{python_exe} -m gsuite_cli.cli sheets read',
                'write': f'{python_exe} -m gsuite_cli.cli sheets write',
                'create': f'{python_exe} -m gsuite_cli.cli sheets create'
            },
            '4': {  # Docs
                'list': f'{python_exe} -m gsuite_cli.cli docs list',
                'create': f'{python_exe} -m gsuite_cli.cli docs create --help',
                'read': f'{python_exe} -m gsuite_cli.cli docs get --help',
                'update': f'{python_exe} -m gsuite_cli.cli docs update --help',
                'search': f'{python_exe} -m gsuite_cli.cli docs search --help'
            },
            '5': {  # AI
                'chat': f'{python_exe} -m gsuite_cli.cli ai chat',
                'ask': f'{python_exe} -m gsuite_cli.cli ai ask --help',
                'summarize': f'{python_exe} -m gsuite_cli.cli ai summarize',
                'analytics': f'{python_exe} -m gsuite_cli.cli ai analytics',
                'insights': f'{python_exe} -m gsuite_cli.cli ai insights'
            },
            '6': {  # Settings
                'config': f'{python_exe} -m gsuite_cli.cli config list',
                'cache': f'{python_exe} -m gsuite_cli.cli cache status',
                'auth': f'{python_exe} -m gsuite_cli.cli auth status'
            },
            '7': {  # Analytics
                'productivity': f'{python_exe} -m gsuite_cli.cli ai analytics',
                'usage': f'{python_exe} -m gsuite_cli.cli cache stats',
                'performance': f'{python_exe} -m gsuite_cli.cli cache status'
            },
            '8': {  # Help
                'commands': f'{python_exe} -m gsuite_cli.cli --help',
                'examples': f'{python_exe} -m gsuite_cli.cli ai ask "show examples"',
                'tutorial': 'echo "🎯 Welcome to GSuite CLI! Use natural language like: gs ai ask show my calendar"'
            }
        }
        
        if service_key in command_map and command in command_map[service_key]:
            cli_command = command_map[service_key][command]
            
            # If command is 'get', prompt for ID before running
            if command == 'get':
                print(Fore.BLACK + "Enter ID: ", end="")
                item_id = input().strip()
                if item_id:
                    cli_command = f"{cli_command} {item_id}"
                else:
                    self.show_error("ID is required")
                    return

            print(Fore.BLACK + f"💡 Running: {cli_command}")
            print()
            
            # Execute the command
            try:
                os.system(cli_command)
            except Exception as e:
                print(Fore.RED + f"❌ Error: {e}")
        else:
            print(Fore.RED + "❌ Command not implemented yet")
        
        print()
        print(Fore.BLACK + "Press Enter to continue...", end="")
        input()
    
    def show_error(self, message: str):
        """Show error message"""
        print()
        print(Fore.RED + Style.BRIGHT + f"❌ {message}")
        time.sleep(2)
    
    def show_success(self, message: str):
        """Show success message"""
        print()
        print(Fore.GREEN + Style.BRIGHT + f"✅ {message}")
        time.sleep(2)
    
    def loading_animation(self, text: str, duration: int):
        """Show loading animation"""
        print(Fore.BLACK + Style.BRIGHT + f"{text}", end="")
        
        for i in range(duration * 2):
            time.sleep(0.5)
            print(".", end="", flush=True)
        
        print(" " + Fore.GREEN + Style.BRIGHT + "✓")
        time.sleep(0.5)
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def run(self):
        """Run the interactive menu system"""
        try:
            self.show_welcome()
            time.sleep(2)
            
            while True:
                self.show_main_menu()
                choice = self.get_user_choice()
                
                if choice == '0':
                    self.show_goodbye()
                    break
                elif choice in self.options:
                    self.handle_service_menu(choice)
                else:
                    self.show_error("Invalid choice. Please select 1-8 or 0.")
        
        except KeyboardInterrupt:
            self.show_goodbye()
    
    def handle_service_menu(self, service_key: str):
        """Handle service-specific menu"""
        while True:
            self.show_service_menu(service_key)
            choice = self.get_user_choice()
            
            if choice == '0':
                self.show_goodbye()
                sys.exit(0)
            elif choice == 'b':
                break
            else:
                self.handle_service_choice(service_key, choice)
    
    def show_goodbye(self):
        """Show goodbye message with dynamic box"""
        self.clear_screen()
        width = self.get_width()
        
        goodbye_content = [
            "👋 Thank you for using GSuite CLI!",
            "",
            "🚀 Your AI-Powered Productivity Assistant",
            "",
            "📊 Productivity Score: 85/100",
            "⚡ Cache Hit Rate: 92%",
            "🤖 AI Commands Used: 47",
            "",
            "💚 Stay productive!"
        ]
        
        print()
        self.draw_box(goodbye_content, color=Fore.GREEN, padding=5)
        print()


def start_interactive_mode():
    """Start the interactive CLI mode"""
    menu = InteractiveMenu()
    menu.run()


if __name__ == "__main__":
    start_interactive_mode()
