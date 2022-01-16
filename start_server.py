import argparse

from src.server import Server

if __name__ == "__main__":
    """
    Accepts the following optional arguments:
    --host "your.new.host.ip" (default="0.0.0.0")
    --port port_number (default=8080)
    --http (boolean that determines if server is started using HTTP or HTTPS)
    --debug (boolean that determines if logging level is INFO or DEBUG) 

    Run this script as follows:
    `python start_server.py OPTIONS"`
    """
    parser = argparse.ArgumentParser(description="Start the server")
    # parser.add_argument("config", metavar="C", help="path to the config file")
    parser.add_argument(
        "--host", dest="host", action="store", default="0.0.0.0", help="The host (default: 127.0.0.1)"
    )
    parser.add_argument("--port", dest="port", action="store", default=8080, help="The port (default: 8080)")
    parser.add_argument("--http", action=argparse.BooleanOptionalAction, help="Start HTTP server instead of HTTPS")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction, help="Debug mode")

    args = parser.parse_args()
    Server(host=args.host, port=args.port, http=args.http, debug=args.debug).start()
