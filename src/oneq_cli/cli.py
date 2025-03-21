import argparse

def main():
    parser = argparse.ArgumentParser(description="1Q - The right one-liner is just one query away.")
    parser.add_argument("query", nargs="?", help="The natural language query for generating commands.")
    parser.add_argument("--show-config-path", action="store_true", help="Print the path to the configuration file and exit.")
    parser.add_argument("--clear-config", action="store_true", help="Remove the configuration file (prompts for confirmation).")
    parser.add_argument("--set-default-output", choices=["auto", "tui", "inline"], help="Set and save the default output style in the config file (auto, tui, inline).")
    parser.add_argument("-v", "--version", action="version", version="1Q 1.0.0")

    args = parser.parse_args()

    if args.show_config_path:
        print("Showing config path is a stub.") # TODO
        return

    if args.clear_config:
        print("Clearing config is a stub.") # TODO
        return

    if args.set_default_output:
        print("Setting default output is a stub.") # TODO
        return


    if args.query:
        print(f"You asked: {args.query}")
    else:
        print("Hello, world! No query provided.")

if __name__ == "__main__":
    main()