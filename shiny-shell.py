from shiny import App, reactive, render, ui
import subprocess
import os
import socket
import glob
import shlex
import json

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
    ui.div(
        ui.output_ui("terminal_display"),
        ui.output_ui("completions_display"),
        class_="terminal-container"
    ),
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

                    // Clear completions when executing command
                    lastCompletionResult = null;
                    completionIndex = -1;

                    if (cmd) {
                        // Add to local history
                        commandHistory.push(cmd);
                        historyIndex = -1;

                        // Send to server with priority flag to ensure it's processed
                        Shiny.setInputValue('execute_cmd', cmd + '_' + Date.now(), {priority: 'event'});
                    }
                } else if (e.key === 'Tab') {
                    e.preventDefault();
                    var cmd = $(this).val();
                    var cursorPos = this.selectionStart;

                    // Check if we can accept the first completion
                    if (lastCompletionResult && lastCompletionResult.completions.length > 1) {
                        // Accept the first completion
                        var completion = lastCompletionResult.completions[0];

                        // Apply the completion
                        var newCmd = cmd.substring(0, lastCompletionResult.start_pos) + completion + cmd.substring(lastCompletionResult.end_pos);
                        $(this).val(newCmd);

                        var newCursorPos = lastCompletionResult.start_pos + completion.length;
                        this.setSelectionRange(newCursorPos, newCursorPos);

                        console.log('Accepted first completion:', completion);

                        // Clear completions on backend
                        Shiny.setInputValue('clear_completions', Date.now(), {priority: 'event'});

                        // Clear frontend state
                        lastCompletionResult = null;
                        completionIndex = -1;
                        return;
                    }

                    // Clear previous completions state
                    completionIndex = -1;

                    // Add timestamp to ensure uniqueness and force processing
                    var timestamp = Date.now();
                    console.log('Sending tab completion request:', cmd, cursorPos, timestamp);

                    // Send tab completion request as encoded string
                    var requestData = JSON.stringify({
                        command: cmd,
                        cursor_pos: cursorPos,
                        timestamp: timestamp
                    });
                    Shiny.setInputValue('tab_complete', requestData, {priority: 'event'});
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

            // Handle tab completion response
            Shiny.addCustomMessageHandler('completion_result', function(result) {
                console.log('Received completion result:', result);

                if (result && result.completions && result.completions.length > 0) {
                    // Store result for cycling
                    lastCompletionResult = result;

                    var input = $('#command');
                    var cmd = input.val();

                    console.log('Processing completions for command:', cmd);

                    if (result.completions.length === 1) {
                        // Single completion - auto-complete
                        var completion = result.completions[0];
                        var newCmd = cmd.substring(0, result.start_pos) + completion + cmd.substring(result.end_pos);
                        console.log('Auto-completing:', cmd, '->', newCmd);
                        input.val(newCmd);

                        // Set cursor position after completion
                        var newCursorPos = result.start_pos + completion.length;
                        input[0].setSelectionRange(newCursorPos, newCursorPos);
                        input.focus();

                        // Clear stored result since we auto-completed
                        lastCompletionResult = null;
                    } else {
                        // Multiple completions - show common prefix if any
                        var commonPrefix = result.common_prefix;
                        console.log('Multiple completions:', result.completions, 'Common prefix:', commonPrefix);

                        if (commonPrefix && commonPrefix.length > (result.end_pos - result.start_pos)) {
                            var newCmd = cmd.substring(0, result.start_pos) + commonPrefix + cmd.substring(result.end_pos);
                            console.log('Using common prefix:', cmd, '->', newCmd);
                            input.val(newCmd);

                            var newCursorPos = result.start_pos + commonPrefix.length;
                            input[0].setSelectionRange(newCursorPos, newCursorPos);
                            input.focus();
                        }

                        // Completions will be shown by the backend in the completions_display
                    }
                } else {
                    lastCompletionResult = null;
                }
            });

            // Track completions for cycling
            var currentCompletions = [];
            var completionIndex = -1;
            var completionCommand = '';
            var completionCursorPos = 0;

            // Handle completion result and store for cycling
            var lastCompletionResult = null;

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
    current_completions = reactive.value([])  # Store current tab completions

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

    def get_tab_completions(command, cursor_pos):
        try:
            # Parse the command to find the word being completed
            words = shlex.split(command[:cursor_pos])
            if not words:
                # Empty command, complete commands
                return get_command_completions("")

            # Check if cursor is at the end of a word or in whitespace
            if cursor_pos > 0 and command[cursor_pos - 1].isspace():
                # Completing a new word
                if len(words) == 1:
                    # Second word - likely a file/directory
                    return get_file_completions("", current_dir.get())
                else:
                    # Subsequent words - file/directory completion
                    return get_file_completions("", current_dir.get())
            else:
                # Completing current word
                current_word = words[-1] if words else ""

                if len(words) == 1:
                    # First word - command completion
                    return get_command_completions(current_word)
                else:
                    # File/directory completion
                    return get_file_completions(current_word, current_dir.get())
        except:
            # If parsing fails, try file completion
            return get_file_completions("", current_dir.get())

    def get_command_completions(prefix):
        # Get commands from PATH
        commands = set()
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)

        for path_dir in path_dirs:
            if os.path.isdir(path_dir):
                try:
                    for cmd in os.listdir(path_dir):
                        cmd_path = os.path.join(path_dir, cmd)
                        if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
                            if cmd.startswith(prefix):
                                commands.add(cmd)
                except (PermissionError, OSError):
                    continue

        # Add some common built-in commands
        builtins = ["cd", "pwd", "echo", "export", "set", "unset", "history", "exit"]
        for builtin in builtins:
            if builtin.startswith(prefix):
                commands.add(builtin)

        return sorted(list(commands))

    def get_file_completions(prefix, directory):
        completions = []

        print(f"get_file_completions: prefix='{prefix}', directory='{directory}'")  # Debug

        # Handle paths with directory separators
        if "/" in prefix:
            dir_part = os.path.dirname(prefix)
            file_part = os.path.basename(prefix)

            print(f"Path with '/': dir_part='{dir_part}', file_part='{file_part}'")  # Debug

            # Handle absolute vs relative paths
            if prefix.startswith("/"):
                search_dir = dir_part if dir_part else "/"
                is_absolute = True
            else:
                search_dir = os.path.join(directory, dir_part) if dir_part else directory
                is_absolute = False
        else:
            search_dir = directory
            file_part = prefix
            is_absolute = False
            dir_part = ""

        print(f"Searching in: '{search_dir}' for files starting with '{file_part}'")  # Debug

        try:
            if os.path.isdir(search_dir):
                for item in os.listdir(search_dir):
                    if item.startswith(file_part):
                        item_path = os.path.join(search_dir, item)

                        # Build the completion with proper path prefix
                        if dir_part:
                            if is_absolute:
                                completion = os.path.join(dir_part, item)
                            else:
                                completion = os.path.join(dir_part, item)
                        else:
                            completion = item

                        if os.path.isdir(item_path):
                            completion += "/"

                        completions.append(completion)
                        print(f"Added completion: '{completion}'")  # Debug
        except (PermissionError, OSError) as e:
            print(f"Error accessing directory: {e}")  # Debug

        return sorted(completions)

    def find_completion_bounds(command, cursor_pos):
        # Find the start and end of the word being completed
        start = cursor_pos
        while start > 0 and not command[start - 1].isspace():
            start -= 1

        end = cursor_pos
        while end < len(command) and not command[end].isspace():
            end += 1

        print(f"Completion bounds for '{command}' at pos {cursor_pos}: start={start}, end={end}")
        print(f"Word being completed: '{command[start:end]}'")
        return start, end

    def find_common_prefix(completions):
        if not completions:
            return ""

        if len(completions) == 1:
            return completions[0]

        common = completions[0]
        for completion in completions[1:]:
            while common and not completion.startswith(common):
                common = common[:-1]

        return common

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

            # Clear completions and input
            current_completions.set([])
            ui.update_text("command", value="")

    @reactive.effect
    @reactive.event(input.tab_complete)
    async def handle_tab_completion():
        tab_request = input.tab_complete()
        print(f"Tab completion received: {tab_request}")  # Debug print

        if tab_request:
            try:
                # Parse the JSON string
                tab_data = json.loads(tab_request)
                command = tab_data.get("command", "")
                cursor_pos = tab_data.get("cursor_pos", 0)
                timestamp = tab_data.get("timestamp", 0)

                print(f"Processing completion for: '{command}' at pos {cursor_pos}")  # Debug print

                # Get completions
                completions = get_tab_completions(command, cursor_pos)
                print(f"Found completions: {completions}")  # Debug print

                if completions:
                    # Find the bounds of the word being completed
                    start_pos, end_pos = find_completion_bounds(command, cursor_pos)

                    # Calculate common prefix
                    common_prefix = find_common_prefix(completions)

                    result = {
                        "completions": completions,
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "common_prefix": common_prefix,
                        "timestamp": timestamp
                    }

                    print(f"Sending result: {result}")  # Debug print
                    # Send completion result to frontend
                    await session.send_custom_message("completion_result", result)

                    # If multiple completions, store them for display
                    if len(completions) > 1:
                        current_completions.set(completions)
                        print(f"Stored {len(completions)} completions for display")  # Debug print
                else:
                    print("No completions found")  # Debug print
            except json.JSONDecodeError as e:
                print(f"Failed to parse tab completion request: {e}")  # Debug print

    @reactive.effect
    @reactive.event(input.clear_completions)
    def handle_clear_completions():
        current_completions.set([])
        print("Cleared completions")  # Debug print

    @reactive.effect
    @reactive.event(input.show_completions)
    def handle_show_completions():
        completions_text = input.show_completions()
        print(f"Show completions received: {completions_text}")  # Debug print

        if completions_text:
            # Remove timestamp suffix
            completions = completions_text.rsplit("_", 1)[0]
            print(f"Displaying completions: {completions}")  # Debug print

            # Add completions to terminal output
            session_data = list(terminal_session.get())
            session_data.append({
                "prompt": "",
                "command": "",
                "output": completions,
                "success": True
            })
            terminal_session.set(session_data)
            print("Added completions to terminal session")  # Debug print

    @render.ui
    def terminal_display():
        session_data = terminal_session.get()
        elements = []

        print(f"Rendering terminal with {len(session_data)} entries")  # Debug print

        # Display all previous commands and outputs
        for i, entry in enumerate(session_data):
            print(f"Entry {i}: prompt='{entry['prompt']}', command='{entry['command']}', output='{entry['output'][:50]}...' if len > 50")  # Debug print

            # Show prompt + command
            if entry['prompt'] or entry['command']:
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

    @render.ui
    def completions_display():
        completions = current_completions.get()
        if completions:
            completions_text = "  ".join(completions)
            return ui.div(
                completions_text,
                class_="terminal-output success-output"
            )
        return ui.div()  # Empty div when no completions


app = App(app_ui, server)
