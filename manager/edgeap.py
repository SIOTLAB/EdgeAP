import manager
import sys
import signal
import time
import argparse

def main():
    # CLI options
    argparser = argparse.ArgumentParser(description='EdgeAP management server')
    argparser.add_argument('-c', '--config', type=str,
                           default="manager.conf",
                           help='configuration file (default is "manager.conf")')
    args = argparser.parse_args()
    config_file = args.config

    # Create manager object
    man_obj = manager.Manager(config_file)

    # Signal handler
    def handler(signal, frame):
        print("Error: received signal ", signal, file=sys.stderr)
        print("Shutting down...", file=sys.stderr)
        man_obj.shutdown()
        sys.exit(0)

    # Register all catchable signals
    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP, signal.SIGWINCH}
    for sig in catchable_sigs:
        signal.signal(sig, handler)

    # Start the manager servers
    man_obj.start_request_server()
    man_obj.start_shutdown_server()

    # Join threads
    for _, thread in man_obj.threads.items():
        thread.join()
    
if __name__ == "__main__":
    main()
