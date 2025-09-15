# Shiny Shell

A web-based terminal emulator that provides a browser-accessible command-line interface. Inspired by https://github.com/colearendt/shiny-shell, vibed with Claude.

## Features

- **Web-based Terminal**: Access a shell interface through your web browser
- **Tab Completion**: Press Tab to complete commands and file paths
  - Shows multiple completions when available
  - Press Tab again to accept the first completion
  - Supports both absolute and relative paths
- **Command History**: Navigate through previous commands using arrow keys (↑/↓)
- **Real-time Command Execution**: Execute shell commands with live output display
- **Terminal Styling**: Classic green-on-black terminal appearance with monospace font

## How it Works

The application creates a web interface that mimics a traditional terminal:

- The current working directory is tracked and displayed in the prompt
- Command output (both stdout and stderr) is displayed with appropriate styling
- Success/error states are visually distinguished with different colors
- Commands have a 30-second timeout limit for safety

## Usage

Run the application and navigate to the provided URL to access your web-based shell interface:

```bash
python shiny-shell.py
```

Type commands as you would in a regular terminal. The interface supports:
- Standard shell navigation and command execution
- Tab completion for commands and file paths:
  - `ls <tab>` - complete file names
  - `cd py<tab>` - complete directory names starting with "py"
  - `cd /us<tab>` - complete absolute paths
- Arrow key navigation through command history

## Technical Details

- Built with [Shiny](https://shiny.posit.co/py/)
- Uses jQuery for client-side interactions
- Commands are executed using Python's `subprocess` module
- Reactive state management for terminal session and command history

## Testing

Run the tab completion test suite:

```bash
python test_completions.py
```

This creates a temporary directory structure and tests various completion scenarios including:
- Command completion
- File and directory completion
- Absolute and relative path completion
- Common prefix handling
- Edge cases with spaces and special characters

## Known Limitations

Not an exhaustive list, just some things I've noticed so far:

- No multi-line command support
- `!$`, `!!`, and similar bash shortcuts don't work
- You can't open things like `vim` or `nano` that require a full terminal interface
- Any color you like, as long as it's green on black
