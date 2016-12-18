# coding: utf-8
"""
Demo for the live reloading of Tornado server.
"""
from __future__ import absolute_import

# Standard imports
import os
import sys

# External imports
import tornado.ioloop
import tornado.web


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
        reloader = LiveReloader(
            # Reload mode.
            #
            # In windows, have to use `spawn_exit` reload mode and force the
            # current process to exit immediately, otherwise will get the
            # error:
            # ```
            # OSError: [WinError 10048] Only one usage of each socket address
            # (protocol/network address/port) is normally permitted
            # ```
            #
            # Notice in `spawn_exit` reload mode, the user will not be able
            # to kill the new process using Ctrl-c.
            #
            reload_mode=('spawn_exit' if sys.platform == 'win32' else 'exec'),
            force_exit=True,
        )

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

        # Create request handler
        class HelloHandler(tornado.web.RequestHandler):
            """
            Request handler class.
            """

            def get(self):
                """
                Request handler.

                :return:
                    None.
                """
                # Write response body
                self.write('hello')

        # List of tuples that maps URL pattern to handler
        handler_tuples = [
            ('/', HelloHandler),
        ]

        # Create Tornado app
        tornado_app = tornado.web.Application(
            handler_tuples,
            # Disable Tornado's reloader
            debug=False,
        )

        # Start listening
        tornado_app.listen(server_port, address=server_host)

        # Get event loop
        io_loop = tornado.ioloop.IOLoop.current()

        # Run event loop
        io_loop.start()

    # If have `KeyboardInterrupt`
    except KeyboardInterrupt:
        # Not treat as error
        pass


# If is run as main module
if __name__ == '__main__':
    # Call main function
    exit(main())
