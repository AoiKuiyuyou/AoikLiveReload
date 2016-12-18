# coding: utf-8
"""
Live reloader that detects module file changes and reloads the program.
"""
from __future__ import absolute_import

# Standard imports
import os
import subprocess
import sys
import threading
import time

# External imports
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


try:
    # Python 3
    from _thread import interrupt_main
except ImportError:
    # Python 2
    from thread import interrupt_main


# Version
__version__ = '0.1.0'


# Public attributes
__all__ = (
    'LiveReloader',
)


class LiveReloader(FileSystemEventHandler):
    """
    Live reloader that detects module file changes and reloads the program.
    """

    # Reload mode constants
    RELOAD_MODE_V_EXEC = 'exec'

    RELOAD_MODE_V_SPAWN_EXIT = 'spawn_exit'

    RELOAD_MODE_V_SPAWN_WAIT = 'spawn_wait'

    RELOAD_MODE_VALUES = (
        RELOAD_MODE_V_EXEC,
        RELOAD_MODE_V_SPAWN_EXIT,
        RELOAD_MODE_V_SPAWN_WAIT,
    )

    def __init__(
        self,
        reload_mode=None,
        force_exit=False,
        extra_paths=None,
        interval=1,
    ):
        """
        Constructor.

        :param reload_mode:
            Reload mode.

            Default is 'spawn_wait' for Windows and 'exec' otherwise.
            Notice `exec` reload mode will crash on Windows.

            Allowed values:
                - 'exec': Replace the current process with a new process.
                - 'spawn_exit': Spawn a subprocess, the current process exits.
                - 'spawn_wait': Spawn a subprocess, the current process waits.

        :param force_exit:
            In `spawn_exit` mode, whether call `os._exit` to force the \
            current process to terminate immediately. Default is not.

        :param extra_paths:
            Extra file paths to watch for changes.

        :param interval:
            Sleep interval between two change checks, in seconds.

        :return:
            None.
        """
        # If reload mode is not given
        if reload_mode is None:
            # If in Windows
            if sys.platform == 'win32':
                # Use default `spawn_wait`
                reload_mode = self.RELOAD_MODE_V_SPAWN_WAIT

            # If not in Windows
            else:
                # Use default `exec`
                reload_mode = self.RELOAD_MODE_V_EXEC

        # If reload mode is not valid
        if reload_mode not in self.RELOAD_MODE_VALUES:
            # Get error message
            error_msg = 'Invalid reload mode: {}.'.format(repr(reload_mode))

            # Raise error
            raise ValueError(error_msg)

        # Store reload mode
        self._reload_mode = reload_mode

        # Store whether force exit
        self._force_exit = bool(force_exit)

        # Convert given extra paths to absolute
        self._extra_paths = set(
            os.path.abspath(x) for x in (extra_paths or ())
        )

        # Store check interval
        self._interval = interval

        # Set of watch paths
        self._watch_paths = set()

        # Whether the watcher thread should stop
        self._watcher_to_stop = False

    def start_watcher_thread(self):
        """
        Start watcher thread.

        :return:
            Watcher thread object.
        """
        # Create watcher thread
        watcher_thread = threading.Thread(target=self.run_watcher)

        # If the reload mode is `spawn_wait`
        if self._reload_mode == self.RELOAD_MODE_V_SPAWN_WAIT:
            # Use non-daemon thread
            daemon = False

        # If the reload mode is not `spawn_wait`
        else:
            # Use daemon thread
            daemon = True

        # Set whether the thread is daemon
        watcher_thread.setDaemon(daemon)

        # Start watcher thread
        watcher_thread.start()

        # Return watcher thread
        return watcher_thread

    def run_watcher(self):
        """
        Watcher thread's function.

        :return:
            None.
        """
        # Create observer
        observer = Observer()

        # Start observer
        observer.start()

        # Dict that maps file path to `watch object`
        watche_obj_map = {}

        # Run change check in a loop
        while not self._watcher_to_stop:
            # Get current watch paths
            old_watch_path_s = set(watche_obj_map)

            # Get new watch paths
            new_watch_path_s = self._find_watch_paths()

            # For each new watch path
            for new_watch_path in new_watch_path_s:
                # Remove from the old watch paths if exists
                old_watch_path_s.discard(new_watch_path)

                # If the new watch path was not watched
                if new_watch_path not in watche_obj_map:
                    try:
                        # Schedule a watch
                        watch_obj = observer.schedule(
                            # 2KGRW
                            # `FileSystemEventHandler` instance
                            self,
                            # File path to watch
                            new_watch_path,
                            # Whether recursive
                            recursive=True,
                        )

                        # Store the watch obj
                        watche_obj_map[new_watch_path] = watch_obj

                    # If have error
                    except OSError:
                        # Set the watch object be None
                        watche_obj_map[new_watch_path] = None

            # For each old watch path that is not in the new watch paths
            for old_watch_path in old_watch_path_s:
                # Get watch object
                watch_obj = watche_obj_map.pop(old_watch_path, None)

                # If have watch object
                if watch_obj is not None:
                    # Unschedule the watch
                    observer.unschedule(watch_obj)

            # Store new watch paths
            self._watch_paths = new_watch_path_s

            # Sleep before next check
            time.sleep(self._interval)

    def _find_watch_paths(self):
        """
        Find paths to watch.

        :return:
            Paths to watch.
        """
        # Add directory paths in `sys.path` to watch paths
        watch_path_s = set(os.path.abspath(x) for x in sys.path)

        # For each extra path
        for extra_path in self._extra_paths or ():
            # Get the extra path's directory path
            extra_dir_path = os.path.dirname(os.path.abspath(extra_path))

            # Add to watch paths
            watch_path_s.add(extra_dir_path)

        # For each module in `sys.modules`
        for module in list(sys.modules.values()):
            # Get module file path
            module_path = getattr(module, '__file__', None)

            # If have module file path
            if module_path is not None:
                # Get module directory path
                module_dir_path = os.path.dirname(os.path.abspath(module_path))

                # Add to watch paths
                watch_path_s.add(module_dir_path)

        # Find short paths of these watch paths.
        # E.g. if both `/home` and `/home/aoik` exist, only keep `/home`.
        watch_path_s = self._find_short_paths(watch_path_s)

        # Return the watch paths
        return watch_path_s

    def _find_short_paths(self, paths):
        """
        Find short paths of given paths.

        E.g. if both `/home` and `/home/aoik` exist, only keep `/home`.

        :param paths:
            Paths.

        :return:
            Set of short paths.
        """
        # Split each path to parts.
        # E.g. '/home/aoik' to ['', 'home', 'aoik']
        path_parts_s = [path.split(os.path.sep) for path in paths]

        # Root node
        root_node = {}

        # Sort these path parts by length, with the longest being the first.
        #
        # Longer paths appear first so that their extra parts are discarded
        # when a shorter path is found at 5TQ8L.
        #
        # Then for each path's parts.
        for parts in sorted(path_parts_s, key=len, reverse=True):
            # Start from the root node
            node = root_node

            # For each part of the path
            for part in parts:
                # Create node of the path
                node = node.setdefault(part, {})

            # 5TQ8L
            # Clear the last path part's node's child nodes.
            #
            # This aims to keep only the shortest path that needs be watched.
            #
            node.clear()

        # Short paths
        short_path_s = set()

        # Collect leaf paths
        self._collect_leaf_paths(
            node=root_node,
            path_parts=(),
            leaf_paths=short_path_s,
        )

        # Return short paths
        return short_path_s

    def _collect_leaf_paths(self, node, path_parts, leaf_paths):
        """
        Collect paths of leaf nodes.

        :param node:
            Starting node. Type is dict.

            Key is child node's path part. Value is child node.

        :param path_parts:
            The starting node's path parts. Type is tuple.

        :param leaf_paths:
            Leaf path list.

        :return:
            None.
        """
        # If the node is leaf node
        if not node:
            # Get node path
            node_path = '/'.join(path_parts)

            # Add to list
            leaf_paths.add(node_path)

        # If the node is not leaf node
        else:
            # For each child node
            for child_path_part, child_node in node.items():
                # Get the child node's path parts
                child_path_part_s = path_parts + (child_path_part,)

                # Visit the child node
                self._collect_leaf_paths(
                    node=child_node,
                    path_parts=child_path_part_s,
                    leaf_paths=leaf_paths,
                )

    def dispatch(self, event):
        """
        Dispatch file system event.

        Callback called when there is a file system event. Hooked at 2KGRW.

        This function overrides `FileSystemEventHandler.dispatch`.

        :param event:
            File system event object.

        :return:
            None.
        """
        # Get file path
        file_path = event.src_path

        # If the file path is in extra paths
        if file_path in self._extra_paths:
            # Call `reload`
            self.reload()

        # If the file path ends with `.pyc` or `.pyo`
        if file_path.endswith(('.pyc', '.pyo')):
            # Get `.py` file path
            file_path = file_path[:-1]

        # If the file path ends with `.py`
        if file_path.endswith('.py'):
            # Get the file's directory path
            file_dir = os.path.dirname(file_path)

            # If the file's directory path starts with any of the watch paths
            if file_dir.startswith(tuple(self._watch_paths)):
                # Call `reload`
                self.reload()

    def reload(self):
        """
        Reload the program.

        :return:
            None.
        """
        # Get reload mode
        reload_mode = self._reload_mode

        # If reload mode is `exec`
        if self._reload_mode == self.RELOAD_MODE_V_EXEC:
            # Call `reload_using_exec`
            self.reload_using_exec()

        # If reload mode is `spawn_exit`
        elif self._reload_mode == self.RELOAD_MODE_V_SPAWN_EXIT:
            # Call `reload_using_spawn_exit`
            self.reload_using_spawn_exit()

        # If reload mode is `spawn_wait`
        elif self._reload_mode == self.RELOAD_MODE_V_SPAWN_WAIT:
            # Call `reload_using_spawn_wait`
            self.reload_using_spawn_wait()

        # If reload mode is none of above
        else:
            # Get error message
            error_msg = 'Invalid reload mode: {}.'.format(repr(reload_mode))

            # Raise error
            raise ValueError(error_msg)

    def reload_using_exec(self):
        """
        Reload the program process.

        :return:
            None.
        """
        # Create command parts
        cmd_parts = [sys.executable] + sys.argv

        # Get env dict copy
        env_copy = os.environ.copy()

        # Reload the program process
        os.execvpe(
            # Program file path
            sys.executable,
            # Command parts
            cmd_parts,
            # Env dict
            env_copy,
        )

    def reload_using_spawn_exit(self):
        """
        Spawn a subprocess and exit the current process.

        :return:
            None.
        """
        # Create command parts
        cmd_parts = [sys.executable] + sys.argv

        # Get env dict copy
        env_copy = os.environ.copy()

        # Spawn subprocess
        subprocess.Popen(cmd_parts, env=env_copy, close_fds=True)

        # If need force exit
        if self._force_exit:
            # Force exit
            os._exit(0)  # pylint: disable=protected-access

        # If not need force exit
        else:
            # Send interrupt to main thread
            interrupt_main()

        # Set the flag
        self._watcher_to_stop = True

        # Exit the watcher thread
        sys.exit(0)

    def reload_using_spawn_wait(self):
        """
        Spawn a subprocess and wait until it finishes.

        :return:
            None.
        """
        # Create command parts
        cmd_parts = [sys.executable] + sys.argv

        # Get env dict copy
        env_copy = os.environ.copy()

        # Send interrupt to main thread
        interrupt_main()

        # Spawn subprocess and wait until it finishes
        subprocess.call(cmd_parts, env=env_copy, close_fds=True)

        # Exit the watcher thread
        sys.exit(0)
