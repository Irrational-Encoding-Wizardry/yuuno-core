import sys
from yuuno.autodiscover import discover_commands


def main():
    if len(sys.argv) == 1:
        print("You must enter a command. Use yuuno --help to see all available commands.")
        sys.exit(1)

    commands = discover_commands()
    if sys.argv[1] == "--help":
        print("Yuuno - Your library for your frame-server")
        print("Usage:")
        print("\tyuuno --help\t\tShows this help message.")
        for name, cmd in commands.items():
            doc = cmd.__doc__ or 'A lonely command. It refused to tell me something about it.'
            print(f"\tyuuno {name} [...]", doc, sep="\t")
        return
    
    command = sys.argv[1]
    if command not in commands:
        print("Sub-Command not found.")
        print("Use yuuno --help to get a list of commands.")
        sys.exit(1)

    del sys.argv[0]

    commands[command]()


if __name__ == '__main__':
    main()