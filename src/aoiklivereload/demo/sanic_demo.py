# coding: utf-8
"""
Demo for the live reloading of Sanic server.
"""
from __future__ import absolute_import

# Standard imports
import os
import sys

# External imports
from sanic import Sanic
from sanic.response import text


def main():
    """
    Main function.

    :return:
        None.
    """
    try:
        # Get the `src` directory's absolute path
        src_path = os.path.dirname(
            # `aoiklivereload` directory's absolute path
            os.path.dirname(
                # `demo` directory's absolute path
                os.path.dirname(
                    # This file's absolute path
                    os.path.abspath(__file__)
                )
            )
        )

        # If the `src` directory path is not in `sys.path`
        if src_path not in sys.path:
            # Add to `sys.path`.
            #
            # This aims to save user setting PYTHONPATH when running this demo.
            #
            sys.path.append(src_path)

        # Import reloader class
        from aoiklivereload import LiveReloader

        # Create reloader
        reloader = LiveReloader()

        # Start watcher thread
        reloader.start_watcher_thread()

        # Server host
        server_host = '0.0.0.0'

        # Server port
        server_port = 8000

        # Get message
        msg = '# ----- Run server -----\nHost: {}\nPort: {}'.format(
            server_host, server_port
        )

        # Print message
        print(msg)

        # Create Sanic app
        sanic_app = Sanic()

        # Create request handler
        @sanic_app.route('/')
        async def hello_handler(request):  # pylint: disable=unused-variable
            """
            Request handler.

            :return:
                Response body.
            """
            # Return response body
            return text('hello')

        # Run server.
        #
        # Notice `KeyboardInterrupt` will be caught inside `sanic_app.run`.
        #
        sanic_app.run(
            host=server_host,
            port=server_port,
        )

    # If have `KeyboardInterrupt`
    except KeyboardInterrupt:
        # Not treat as error
        pass


# If is run as main module
if __name__ == '__main__':
    # Call main function
    exit(main())
