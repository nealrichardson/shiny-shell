# Shiny Shell

A web-based terminal emulator that provides a browser-accessible command-line interface. Inspired by https://github.com/colearendt/shiny-shell, vibed with Claude.

## Features

- **Web-based Terminal**: Access a shell interface through your web browser
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

Run the application and navigate to the provided URL to access your web-based shell interface. Type commands as you would in a regular terminal - the interface supports standard shell navigation and command execution.

## Technical Details

- Built with [Shiny](https://shiny.posit.co/py/)
- Uses jQuery for client-side interactions
- Commands are executed using Python's `subprocess` module
- Reactive state management for terminal session and command history

## Known Limitations

Not an exhausive list, just some things I've noticed so far:

- No tab completion
- No multi-line command support
- You can't open things like `vim` or `nano` that require a full terminal interface
- Any color you like, as long as it's green on black
