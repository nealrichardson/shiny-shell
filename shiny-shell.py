from shiny import App, reactive, render, ui
import subprocess
import os
import socket

app_ui = ui.page_fillable(
    ui.tags.head(
        ui.tags.style(
            """
            body {
                background-color: #000;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                margin: 0;
                padding: 0;
            }
            .terminal-container {
                background-color: #000;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                height: 100vh;
                overflow-y: auto;
                padding: 20px;
                box-sizing: border-box;
            }
            .terminal-output {
                white-space: pre-wrap;
                word-wrap: break-word;
                margin-bottom: 10px;
            }
            .prompt-line {
                color: #00ff00;
                display: flex;
                align-items: center;
                margin: 5px 0;
            }
            .prompt {
                margin-right: 5px;
                flex-shrink: 0;
            }
            .command-input {
                background: transparent;
                border: none;
                outline: none;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                flex-grow: 1;
                caret-color: #00ff00;
                padding: 0;
                margin: 0;
            }
            .command-input:focus {
                outline: none;
                box-shadow: none;
            }
            #command {
                background: transparent !important;
                border: none !important;
                outline: none !important;
                color: #00ff00 !important;
                font-family: 'Courier New', monospace !important;
                font-size: inherit !important;
                padding: 0 !important;
                margin: 0 !important;
                box-shadow: none !important;
                vertical-align: baseline !important;
                line-height: inherit !important;
                height: auto !important;
                min-height: 0 !important;
                width: 100% !important;
                flex: 1 !important;
            }
            .prompt-line {
                color: #00ff00;
                display: flex;
                align-items: baseline;
                margin: 5px 0;
                font-family: 'Courier New', monospace;
                font-size: 16px;
                line-height: 1.2;
                flex-wrap: nowrap;
            }
            .prompt-text {
                white-space: nowrap;
                flex-shrink: 0;
            }
            .error-output {
                color: #ff6666;
            }
            .success-output {
                color: #00ff00;
            }
            .timestamp {
                color: #888;
                font-size: 12px;
            }
        """
        )
    ),
    ui.div(ui.output_ui("terminal_display"), class_="terminal-container"),
    ui.tags.script(
        """
        $(document).ready(function() {
            var commandHistory = [];
            var historyIndex = -1;

            // Handle keydown events on the input (using event delegation)
            $(document).on('keydown', '#command', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    var cmd = $(this).val().trim();

                    if (cmd) {
                        // Add to local history
                        commandHistory.push(cmd);
                        historyIndex = -1;

                        // Send to server with priority flag to ensure it's processed
                        Shiny.setInputValue('execute_cmd', cmd + '_' + Date.now(), {priority: 'event'});
                    }
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (commandHistory.length > 0) {
                        if (historyIndex === -1) {
                            historyIndex = commandHistory.length - 1;
                        } else if (historyIndex > 0) {
                            historyIndex--;
                        }
                        $(this).val(commandHistory[historyIndex]);
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (historyIndex !== -1) {
                        historyIndex++;
                        if (historyIndex >= commandHistory.length) {
                            historyIndex = -1;
                            $(this).val('');
                        } else {
                            $(this).val(commandHistory[historyIndex]);
                        }
                    }
                }
            });

            // Keep input focused and auto-focus when page updates
            $(document).on('click', function(e) {
                if (!$(e.target).is('#command')) {
                    setTimeout(function() {
                        $('#command').focus();
                    }, 10);
                }
            });

            // Focus input when terminal updates
            $(document).on('DOMNodeInserted', function() {
                setTimeout(function() {
                    $('#command').focus();
                }, 10);
            });

            // Auto-scroll to bottom and focus input
            function scrollToBottomAndFocus() {
                var container = $('.terminal-container');
                container.scrollTop(container[0].scrollHeight);

                setTimeout(function() {
                    $('#command').focus();
                }, 10);
            }

            // Scroll to bottom when content changes
            var observer = new MutationObserver(scrollToBottomAndFocus);
            observer.observe(document.querySelector('.terminal-container'), {
                childList: true,
                subtree: true
            });

            // Initial focus and setup
            setTimeout(function() {
                scrollToBottomAndFocus();
                // Initialize the reactive input to ensure it's ready
                Shiny.setInputValue('execute_cmd', 'init_' + Date.now(), {priority: 'event'});
            }, 100);
        });
    """
    ),
)


def server(input, output, session):
    # Store command history and terminal session
    terminal_session = reactive.value([])
    command_history_list = reactive.value([])  # For up/down arrow navigation
    history_index = reactive.value(-1)

    # Get user and hostname for prompt
    username = os.environ.get("USER", "user")
    hostname = socket.gethostname()
    current_dir = reactive.value(os.getcwd())

    def get_prompt():
        cwd = current_dir.get()
        home = os.environ.get("HOME", "")
        if cwd.startswith(home):
            cwd = cwd.replace(home, "~", 1)
        return f"{username}@{hostname}:{cwd}$ "

    def execute_command(cmd):
        try:
            # Handle cd command specially to update working directory
            if cmd.strip().startswith("cd "):
                path = cmd.strip()[3:].strip()
                if not path:
                    path = os.environ.get("HOME", os.getcwd())
                elif path == "~":
                    path = os.environ.get("HOME", os.getcwd())
                elif path.startswith("~/"):
                    path = os.path.join(os.environ.get("HOME", os.getcwd()), path[2:])

                try:
                    os.chdir(path)
                    current_dir.set(os.getcwd())
                    return {
                        "command": cmd,
                        "output": "",
                        "return_code": 0,
                        "success": True,
                    }
                except OSError as e:
                    return {
                        "command": cmd,
                        "output": f"cd: {e}",
                        "return_code": 1,
                        "success": False,
                    }

            # Execute other commands
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=current_dir.get(),
            )

            output_text = ""
            if result.stdout:
                output_text += result.stdout
            if result.stderr:
                output_text += result.stderr

            return {
                "command": cmd,
                "output": output_text,
                "return_code": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "command": cmd,
                "output": "Command timed out (30s limit)",
                "return_code": -1,
                "success": False,
            }
        except Exception as e:
            return {
                "command": cmd,
                "output": f"Error: {str(e)}",
                "return_code": -1,
                "success": False,
            }

    def add_to_session(prompt, cmd, output, success):
        session_data = list(terminal_session.get())
        session_data.append(
            {"prompt": prompt, "command": cmd, "output": output, "success": success}
        )
        terminal_session.set(session_data)

        # Add to command history for navigation (only non-empty commands)
        if cmd.strip():
            history = list(command_history_list.get())
            history.append(cmd.strip())
            command_history_list.set(history)
            history_index.set(-1)  # Reset history navigation

    @reactive.effect
    @reactive.event(input.execute_cmd, ignore_init=True)
    def handle_command():
        cmd_with_timestamp = input.execute_cmd()
        if cmd_with_timestamp:
            # Remove timestamp suffix to get actual command
            cmd = cmd_with_timestamp.rsplit("_", 1)[0]

            # Ignore initialization command
            if cmd == "init":
                return

            if cmd.strip():
                prompt = get_prompt()
                result = execute_command(cmd.strip())
                add_to_session(prompt, cmd.strip(), result["output"], result["success"])

            # Clear input
            ui.update_text("command", value="")

    @render.ui
    def terminal_display():
        session_data = terminal_session.get()
        elements = []

        # Display all previous commands and outputs
        for entry in session_data:
            # Show prompt + command
            elements.append(
                ui.div(f"{entry['prompt']}{entry['command']}", class_="terminal-output")
            )

            # Show output if any
            if entry["output"]:
                output_class = "success-output" if entry["success"] else "error-output"
                elements.append(
                    ui.div(entry["output"], class_=f"terminal-output {output_class}")
                )

        # Add current prompt line with input
        current_prompt = get_prompt()
        elements.append(
            ui.div(
                ui.span(current_prompt, class_="prompt-text", style="margin-right: 0.5em;"),
                ui.input_text("command", "", placeholder="", width="100%"),
                class_="prompt-line",
            )
        )

        return ui.div(*elements)


app = App(app_ui, server)
