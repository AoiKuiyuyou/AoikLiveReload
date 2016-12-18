# coding: utf-8
# -----
# Ignore import error for `waflib`:
# pylint: disable=F0401
# =====
"""
Waf utility module.
"""
from __future__ import absolute_import

# Standard-library imports
from datetime import datetime
from functools import wraps
import inspect
import os
from pprint import pformat
import struct
import subprocess
import sys

# Third-party imports
from waflib.Build import BuildContext
from waflib.Configure import ConfigurationContext
from waflib.Errors import ConfigurationError
from waflib.Node import Node
from waflib.Task import Task


# Version
__version__ = '0.1.0'


# File object to which to write printed text
_PRINT_FILE = sys.stderr


def print_file_set(file):
    """
    Set file object to which to write printed text.

    :param file: File object to which to write printed text.

    :return: None.
    """
    # Use global variable
    global _PRINT_FILE

    # Set print file be given file object
    _PRINT_FILE = file


def print_text(obj=None):
    """
    Print given object's string, plus a trailing newline.

    :param obj: Object to print.

    :return: None.
    """
    # If given object is not None
    if obj is not None:
        # Print given object's string
        _PRINT_FILE.write(str(obj))

    # Print a newline
    _PRINT_FILE.write('\n')


def print_title(title, is_end=False):
    """
    Print title like ``----- {title} -----`` or ``===== {title} =====``.

    :param title: Title.

    :param is_end: Whether is end title. End title use ``=`` instead of ``-``.

    :return: None.
    """
    # If is end title
    if is_end:
        # Use `=`
        sep = '====='

    # If is not end title
    else:
        # Use `-`
        sep = '-----'

    # If is not end title
    if not is_end:
        # Print an empty line for visual comfort
        print_text()

    # Print the title, e.g. `----- {title} -----`
    print_text('# {sep} {title} {sep}'.format(title=title, sep=sep))


def get_full_python_version():
    """
    Get full Python version.

    E.g.
        - `2.7.11.final.0.32bit`
        - `3.5.1.final.0.64bit`

    :return: Full Python version.
    """
    # Get version part, e.g. `3.5.1.final.0`
    version_part = '.'.join(str(x) for x in sys.version_info)

    # Get integer width, e.g. 32 or 64
    int_width = struct.calcsize('P') * 8

    # Get integer width part, e.g. `64bit` or `32bit`
    int_width_part = str(int_width) + 'bit'

    # Return full Python version
    return version_part + '.' + int_width_part


def get_bin_path(venv_path):
    """
    Get given virtual environment's `bin` directory path.

    :param venv_path: Virtual environment directory path.

    :return: `bin` directory path.
    """
    # If the platform is Windows
    if sys.platform.startswith('win'):
        # Return `Scripts` directory path
        return venv_path + '/Scripts'

    # If the platform is not Windows
    else:
        # Return `bin` directory path
        return venv_path + '/bin'


def get_python_path(venv_path):
    """
    Get given virtual environment's `python` program path.

    :param venv_path: Virtual environment directory path.

    :return: `python` program path.
    """
    # Get `bin` directory path
    bin_path = get_bin_path(venv_path)

    # Get `python` program path
    program_path = os.path.join(bin_path, 'python')

    # If the platform is Windows
    if sys.platform.startswith('win'):
        # Add `.exe` suffix to the `python` program path
        program_path = program_path + '.exe'

    # Return the `python` program path
    return program_path


def get_pip_path(venv_path):
    """
    Get given virtual environment's `pip` program path.

    :param venv_path: Virtual environment directory path.

    :return: `pip` program path.
    """
    # Get `bin` directory path
    bin_path = get_bin_path(venv_path)

    # Get `pip` program path
    program_path = os.path.join(bin_path, 'pip')

    # If the platform is Windows
    if sys.platform.startswith('win'):
        # Add `.exe` suffix to the `pip` program path
        program_path = program_path + '.exe'

    # Return the `pip` program path
    return program_path


def add_options(ctx):
    """
    Add command line options.

    :return: None.
    """
    # Add option
    ctx.add_option(
        '--always',
        action='store_true',
        default=False,
        dest='always',
        help='whether always run tasks.',
    )

    # Add option
    ctx.add_option(
        '--check-import',
        action='store_true',
        default=False,
        dest='check_import',
        help='whether import module for dirty checking.',
    )

    # Add option
    ctx.add_option(
        '--venv',
        dest='venv',
        help=(
            'virtual environment directory relative path relative to top'
            ' directory.'
        ),
    )

    # Add option
    ctx.add_option(
        '--venv-add-version',
        default='1',
        dest='venv_add_version',
        # Convert to int so that the value can be used as boolean
        type=int,
        metavar='0|1',
        help=(
            'whether add full Python version to virtual environment directory'
            ' name. E.g. `.py3.5.1.final.0.64bit`. Default is add.'
        ),
    )

    # Add option
    ctx.add_option(
        '--req',
        default=None,
        dest='req_path',
        help='requirements file relative path relative to top directory.',
    )


def add_pythonpath(path):
    """
    Prepend given path to environment variable PYTHONPATH.

    :param path: Path to add to PYTHONPATH.

    :return: New PYTHONPATH value.
    """
    # Get PYTHONPATH value. Default is empty string.
    pythonpath = os.environ.setdefault('PYTHONPATH', '')

    # If given path is not in PYTHONPATH
    if path not in pythonpath.split(os.pathsep):
        # Prepend given path to PYTHONPATH
        pythonpath = os.environ['PYTHONPATH'] = \
            (path + os.pathsep + pythonpath) if pythonpath else path

    # Return new PYTHONPATH value
    return pythonpath


class _ItemWrapper(object):
    """
    Wrap given item for special handling later.
    """

    def __init__(self, type, item):
        """
        Constructor.

        :param type: Wrapper type.

            Allowed values:
                - 'path': Given item is relative path relative to top
                  directory.

                - 'input': Given item should be added to task as input target.

                - 'output': Given item should be added to task as output
                  target.

        :param item: Item to wrap.

        :return: None.
        """
        # If given type is not valid
        if type not in ('path', 'input', 'output'):
            # Get error message
            msg = 'Error (6VYQM): Type is not valid: {0}.'.format(type)

            # Raise error
            raise ValueError(msg)

        # If given type is valid.

        # Store wrapper type
        self._type = type

        # Store given item
        self._item = item

    def type(self):
        """
        Get wrapper type.

        :return: Wrapper type.
        """
        # Return wrapper type
        return self._type

    def item(self):
        """
        Get wrapped item.

        :return: Wrapped item.
        """
        # Return wrapped item
        return self._item


def mark_path(path):
    """
    Wrap given path as relative path relative to top directory.

    Wrapper object will be handled specially in \
    :paramref:`create_cmd_task.parts`.

    :param path: Relative path relative to top directory.

    :return: Wrapper object.
    """
    # If given path is not string,
    # or given path is absolute path.
    if not isinstance(path, str) or os.path.isabs(path):
        # Get error message
        msg = 'Error (2D9ZA): Given path is not relative path: {0}.'.format(
            path
        )

        # Raise error
        raise ValueError(msg)

    # If given path is string,
    # and given path is not absolute path.

    # Wrap given path
    return _ItemWrapper(type='path', item=path)


def _mark_target(type, item):
    """
    Wrap given item as input or output target that should be added to task.

    Wrapper object will be handled specially in \
    :paramref:`create_cmd_task.parts`.

    :param type: Target type.

        Allowed values:
            - 'input'
            - 'output'

    :param item: Item to mark as input or output target.

        Allowed values:
            - Relative path relative to top directory.
            - Node object.
            - List of these.

    :return: Wrapper object.
    """
    # If given type is not valid
    if type not in ('input', 'output'):
        # Get error message
        msg = 'Error (7D74X): Type is not valid: {0}'.format(type)

        # Raise error
        raise ValueError(msg)

    # If given type is valid.

    # Store given item
    orig_item = item

    # If given path is list
    if isinstance(item, list):
        # Use it as items list
        item_s = item

    # If given path is not list
    else:
        # Create items list containing given path
        item_s = [item]

    # For the items list's each item
    for item in item_s:
        # If the item is string,
        # and the item is absolute path.
        if isinstance(item, str) and os.path.isabs(item):
            # Get error message
            msg = (
                'Error (5VWOZ): Given path is not relative path: {0}.'
            ).format(item)

            # Raise error
            raise ValueError(msg)

    # Wrap given item
    return _ItemWrapper(type=type, item=orig_item)


def mark_input(item):
    """
    Wrap given item as input target that should be added to task.

    Wrapper object will be handled specially in \
    :paramref:`create_cmd_task.parts`.

    :param item: Item to mark as input target.

        Allowed values:
            - Relative path relative to top directory.
            - Node object.
            - List of these.

    :return: Wrapper object.
    """
    # Delegate call to `_mark_target`, with wrapper type set to `input`
    return _mark_target(type='input', item=item)


def mark_output(item):
    """
    Wrap given item as output target that should be added to task.

    Wrapper object will be handled specially in \
    :paramref:`create_cmd_task.parts`.

    :param item: Item to mark as output target.

        Allowed values:
            - Relative path relative to top directory.
            - Node object.
            - List of these.

    :return: Wrapper object.
    """
    # Delegate call to `_mark_target`, with wrapper type set to `output`
    return _mark_target(type='output', item=item)


def _ensure_build_context(ctx):
    """
    Ensure given context object is BuildContext object. Raise ValueError if \
    not BuildContext.

    :return: None.
    """
    # If given context is not BuildContext object
    if not isinstance(ctx, BuildContext):
        # Raise error
        raise ValueError(
            'Error (5AXWV): Given context is not BuildContext object: {0}.'
            .format(ctx)
        )


def create_node(ctx, path):
    """
    Create node for given relative path.

    :param ctx: BuildContext object.

    :param path: Relative path relative to top directory.

    :return: Created Node.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # Get top directory's relative path relative to `wscript` directory
    top_dir_relpath = os.path.relpath(
        # Top directory's absolute path
        ctx.top_dir,
        # `wscript` directory's absolute path
        ctx.run_dir,
    )

    # Convert given relative path to be relative to `wscript` directory
    node_path = os.path.join(top_dir_relpath, path)

    # Create node using the relative path relative to `wscript` directory
    node = ctx.path.make_node(node_path)

    # Return the created node
    return node


def _normalize_items(
    ctx,
    items,
    str_to_node=False,
    node_to_str=False,
    allow_task=False,
):
    """
    Normalize given items.

    Do several things:
        - Ignore None.
        - Flatten list.
        - Unwrap wrapped item in `_ItemWrapper`.

    :param ctx: BuildContext object.

    :param items: Items list to normalize.

    :param str_to_node: Convert string to node.

    :param node_to_str: Convert node to absolute path.

    :param allow_task: Whether allow task item.

    :return: Normalized tuples list.

        Tuple format is:
        ::

            (
                normalized_item,        # Normalized item.
                wrapper_type,           # Original `_ItemWrapper` type.
            )
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # Normalized tuples list
    norm_tuple_s = []

    # If given items list is empty
    if not items:
        # Return empty list
        return norm_tuple_s

    # If given items list is not empty.

    # For given items list's each item
    for item in items:
        # If the item is item wrapper
        if isinstance(item, _ItemWrapper):
            # Get wrapper type
            wrapper_type = item.type()

            # Get real item
            item = item.item()

        # If the item is not item wrapper
        else:
            # Set wrapper type be None
            wrapper_type = None

            # Use the item as real item
            item = item

        # If the real item is list
        if isinstance(item, list):
            # Use the real item as real items list
            real_item_s = item

        # If the real item is not list
        else:
            # Create real items list containing the real item
            real_item_s = [item]

        # For each real item
        for real_item in real_item_s:
            # If the real item is None
            if real_item is None:
                # Ignore None
                continue

            # If the real item is not None.

            # If the real item is string
            elif isinstance(real_item, str):
                # If need convert string to node
                if (wrapper_type is not None) or str_to_node:
                    # If the path string is absolute path
                    if os.path.isabs(real_item):
                        # Get error message
                        msg = (
                            'Error (7MWU9): Given path is not relative path:'
                            ' {0}.'
                        ).format(real_item)

                        # Raise error
                        raise ValueError(msg)

                    # If the path string is not absolute path.

                    # Create node as normalized item
                    norm_item = create_node(ctx, real_item)

                    # If need convert node to absolute path
                    if node_to_str:
                        # Convert the node to absolute path
                        norm_item = norm_item.abspath()

                # If not need convert string to node
                else:
                    # Use the string as normalized item
                    norm_item = real_item

                # Create normalized tuple
                norm_tuple = (norm_item, wrapper_type)

            # If the real item is not string.

            # If the real item is node
            elif isinstance(real_item, Node):
                # If need convert node to absolute path
                if node_to_str:
                    # Convert the node to absolute path
                    real_item = real_item.abspath()

                # Create normalized tuple
                norm_tuple = (real_item, wrapper_type)

            # If the real item is not node.

            # If the real item is task
            elif isinstance(real_item, Task):
                # If allow task item
                if allow_task:
                    # Create normalized tuple
                    norm_tuple = (real_item, wrapper_type)

                # If not allow task item
                else:
                    # Get error message
                    msg = 'Error (6PVMG): Item type is not valid: {0}.'.format(
                        real_item
                    )

                    # Raise error
                    raise ValueError(msg)

            # If the real item is not task.

            # If the real item is not None, string, node, or task
            else:
                # Get error message
                msg = 'Error (63KUG): Item type is not valid: {0}.'.format(
                    real_item
                )

                # Raise error
                raise ValueError(msg)

            # Add the normalized tuple to list
            norm_tuple_s.append(norm_tuple)

    # Return the normalized tuples list
    return norm_tuple_s


def _format_multi_line_command(parts):
    """
    Format given command parts to multi-line command text.

    :param parts: Command parts list.

    :return: Multi-line command text.
    """
    # Get multi-line command text separator.
    # Windows uses `^`. Linux uses `\`.
    cmd_parts_sep = ' ^\n' if sys.platform.startswith('win') else ' \\\n'

    # Return the multi-line command text
    return cmd_parts_sep.join(parts)


def update_touch_file(
    ctx,
    path,
    check_import=False,
    check_import_module=None,
    check_import_python=None,
    always=False,
):
    """
    Update touch file at given path.

    Do two things:
        - Create touch file if it not exists.
        - Update touch file if import checking fails.

    The returned touch file node is used as task's output target for dirty
    checking. Task will run if the touch file changes.

    :param ctx: BuildContext instance.

    :param path: Touch file relative path relative to top directory.

    :param check_import: Whether import module for dirty checking.

    :param check_import_module: Module name to import for dirty checking.

    :param check_import_python: Python program to use for dirty checking.

    :param always: Whether always run.

    :return: A two-item tuple.

        Tuple format is:
        ::

            (
                touch_file_node,        # Touch file node.
                task_needs_run,         # Whether task needs run.
            )
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # Print title
    print_title('Update touch file: {}'.format(path))

    # Create touch node
    touch_node = create_node(ctx, path)

    # Whether task needs run
    need_run = False

    # If the touch file not exists,
    # or `always` flag is on.
    if not touch_node.exists() or always:
        # Set `need_run` flag on
        need_run = True

    # If the touch file exists,
    # and `always` flag is off.
    else:
        # If need import module for dirty checking,
        # and module name to import is given.
        if check_import and check_import_module:
            # Get import statement.
            # Notice `from` import ensures the imported module is not imported
            # as `__main__` module. And `__name__` exists in any module.
            import_stmt = 'from {} import __name__'.format(check_import_module)

            # Print info
            print_text('Check import: {}'.format(import_stmt))

            # If Python program to check import is not given
            if check_import_python is None:
                # Get error message
                msg = (
                    'Error (3BKFW): Python program to check import is not'
                    ' given.'
                )

                # Raise error
                raise ValueError(msg)

            # If Python program to check import is given.

            # Normalize given Python program path
            check_import_python, _ = _normalize_items(
                ctx=ctx,
                items=[check_import_python],
                # Convert node to absolute path
                node_to_str=True,
            )[0]

            # If the Python program path is not string
            if not isinstance(check_import_python, str):
                # Get error message
                msg = (
                    'Error (39FQE): Given Python program to check import is'
                    ' not string or node: {0}.'
                ).format(check_import_python)

                # Raise error
                raise ValueError(msg)

            # If the Python program path is string.

            # If the Python program path is not absolute path
            if not os.path.isabs(check_import_python):
                # Convert the Python program path to absolute path
                check_import_python = \
                    create_node(ctx, check_import_python).abspath()

            # The Python program path is absolute path now.

            # Get command parts
            cmd_part_s = [
                # Python program absolute path
                check_import_python,

                # Run code
                '-c',

                # Code to run
                import_stmt
            ]

            # Print the command in multi-line format
            print_text(_format_multi_line_command(cmd_part_s))

            #
            try:
                # Run the command
                subprocess.check_output(cmd_part_s)

                # If not have error,
                # it means the module can be imported.
                #     Set `need_run` flag off.
                need_run = False

            # If have error,
            # it means the module can not be imported.
            #
            # Notice the program may not exist. So catch general exception.
            except Exception:  # pylint: disable=W0703
                # Set `need_run` flag on
                need_run = True

    # If task needs run
    if need_run:
        # If the touch file's parent directory not exists
        if not touch_node.parent.exists():
            # Create the touch file's parent directory
            touch_node.parent.mkdir()

        # Write current time to the touch file to force content change.
        # This will fail dirty-checking and cause task to run.
        touch_node.write('{0}\n'.format(datetime.utcnow()))

        # Print info
        print_text('Updated.')

    # If task not needs run
    else:
        # Print info
        print_text('Skipped.')

    # Print end title
    print_title('Update touch file: {}'.format(path), is_end=True)

    # Return a two-item tuple
    return touch_node, need_run


class CmdTask(Task):
    """
    Task that runs command.
    """

    def __init__(
        self,
        ctx,
        parts,
        task_name=None,
        *args,
        **kwargs
    ):
        """
        Constructor.

        :param ctx: BuildContext object.

        :param parts: Command parts list.

        :param task_name: Task name for display purpose.

        :param \\*args: Other arguments passed to parent constructor.

        :param \\*\\*kwargs: Other keyword arguments passed to parent
            constructor.

        :return: None.
        """
        # Call parent constructor
        Task.__init__(self, *args, **kwargs)

        # Ensure given context object is BuildContext object
        _ensure_build_context(ctx)

        # Store context object
        self._ctx = ctx

        # Store command parts
        self._parts = parts

        # Store task name
        self._task_name = task_name

        # Get task title for display purpose
        self._task_name_title = 'CmdTask: {}'.format(self._task_name) \
            if self._task_name else 'CmdTask'

        # Get working directory. Default is current Python's working directory.
        self._cwd = kwargs.get('cwd', os.getcwd())

    def run(self):
        """
        Run command.

        :return: Command exit code.
        """
        # Print task title
        print_title(self._task_name_title)

        # Get context object
        ctx = self._ctx

        # Get command parts
        cmd_part_s = self._parts

        # Print title
        print_title('Find program')

        # Get program path from command parts
        program_path = cmd_part_s[0]

        # If the program path ends with one of the file extensions below
        if program_path.endswith(('.exe', '.com', '.bat', '.cmd')):
            # Remove the file extension.
            # This is because `Waf`'s `find_binary` function adds each of the
            # file extensions when finding the program.
            program_path = program_path[:-4]

        # Print info
        print_text('Find program: {0}'.format(program_path))

        #
        try:
            # Find program
            found_program_path_s = ctx.find_program(program_path, quiet=True)

        # If program paths are not found
        except ConfigurationError:
            # Get error message
            msg = 'Error (2D7VS): Program is not found: {0}'.format(
                program_path
            )

            # Raise error
            raise ValueError(msg)

        # If program paths are found.

        # If program paths are found.
        #     Use the first program path found.
        # If program paths are not found. (Should not happen.)
        #     Use given program path.
        found_program_path = found_program_path_s[0] \
            if found_program_path_s else program_path

        # Use the program path found as the first command part
        cmd_part_s[0] = found_program_path

        # Print info
        print_text('Use program: {0}'.format(found_program_path))

        # Print end title
        print_title('Find program', is_end=True)

        # Print title
        print_title('PATH')

        # Print environment variable PATH's value, one part per line
        print_text('\n'.join(os.environ.get('PATH', '').split(os.pathsep)))

        # Print end title
        print_title('PATH', is_end=True)

        # Print title
        print_title('PYTHONPATH')

        # Print environment variable PYTHONPATH's value, one part per line
        print_text(
            '\n'.join(os.environ.get('PYTHONPATH', '').split(os.pathsep))
        )

        # Print end title
        print_title('PYTHONPATH', is_end=True)

        # Print title
        print_title('DIR')

        # Print working directory
        print_text(self._cwd)

        # Print end title
        print_title('DIR', is_end=True)

        # Print title
        print_title('CMD')

        # Print the command in multi-line format
        print_text(_format_multi_line_command(cmd_part_s))

        # Print end title
        print_title('CMD', is_end=True)

        # Print title
        print_title('RUN')

        # Run the command in the working directory
        exit_code = self.exec_command(cmd_part_s, cwd=self._cwd)

        # Print the command's exit code
        print_text('Exit code: {0}'.format(exit_code))

        # Print end title
        print_title('RUN', is_end=True)

        # Print task end title
        print_title(self._task_name_title, True)

        # Return the exit code
        return exit_code


def chain_tasks(tasks):
    """
    Chain given tasks. Set each task to run after its previous task.

    :param tasks: Tasks list.

    :return: Given tasks list.
    """
    # If given tasks list is not empty
    if tasks:
        # Previous task
        previous_task = None

        # For given tasks list's each task
        for task in tasks:
            # If the task is not None.
            # Task can be None to allow code like ``task if _PY2 else None``.
            if task is not None:
                # If previous task is not None
                if previous_task is not None:
                    # Set the task to run after the previous task
                    task.set_run_after(previous_task)

                # Set the task as previous task for the next task
                previous_task = task

    # Return given tasks list.
    return tasks


# Tasks cache dict to avoid creating a common task multiple times.
# Key is cache key given to function `create_cmd_task` below.
# Value is task created in function `create_cmd_task` below.
_TASKS_CACHE = {}


def create_cmd_task(
    ctx,
    parts,
    inputs=None,
    outputs=None,
    env=None,
    cwd=None,
    task_name=None,
    cache_key=None,
    always=False,
    add_to_group=True,
):
    """
    Create task that runs given command.

    :param ctx: BuildContext object.

    :param parts: Command parts list.

        Each part can be:
            - **None**: Will be ignored.
            - **String**: Will be used as-is.
            - **Node object**: Will be converted to absolute path.
            - **List of these**: Will be flattened.
            - **Item wrapper of these**: Will be unwrapped. Item marked as
              input or output target will be added to created task.

    :param inputs: Input items list to add to created task.

        Each item can be:
            - **None**: Will be ignored.
            - **Path**: Relative path relative to top directory. Will be
              converted to node.
            - **Node object**: Will be used as-is.
            - **Task object**: Will set created task to run after the task.
            - **List of these**: Will be flattened.
            - **Item wrapper of these**: Will be unwrapped.

    :param outputs: Outputs items list to add to created task.

        Each item can be:
            - **None**: Will be ignored.
            - **Path**: Relative path relative to top directory. Will be
              converted to node.
            - **Node object**: Will be used as-is.
            - **Task object**: Will set the task to run after created task.
            - **List of these**: Will be flattened.
            - **Item wrapper of these**: Will be unwrapped.

    :param env: Environment dict.

        Default is use given context object's environment dict.

    :param cwd: Working directory in which to run given command.

        Default is top directory.

    :param task_name: Task name for display purpose.

        Default is use the caller function's name.

    :param cache_key: Task cache key.

    :param always: Whether mark created task as always run.

    :param add_to_group: Whether add created task to given context.

    :return: Created task.

    :notes:
        It is recommended to refer to files inside project using relative
        paths. This is even required if the files are used as task's input or
        output targets.

        It is not ideal to make relative paths relative to current working
        directory, or relative to `wscript` file, because neither of the two
        choices guarantee a fixed start directory.

        It is not ideal to let `Waf` resolve relative paths neither, because
        the start directory used for resolving relative paths varies with
        different types of command context (i.e. OptionsContext,
        ConfigurationContext, BuildContext, and Context).

        It is best to make relative paths relative to project's top directory.
        To do so, first use `Waf`'s pre-defined path variable `top` to locate
        project's top directory (Notice path variable `top`'s value is relative
        to `wscript` file.). Then `aoikwafutil`'s functions like
        `create_cmd_task` will use path variable `top`'s value to resolve other
        relative paths.

        `create_cmd_task` handles relative paths using rules below:

            - Relative paths marked by `mark_path`, `mark_input`, or
              `mark_output` are relative to top directory.

            - Relative paths passed to argument `parts` are used as-is. They
              are relative to the working directory in which to run the
              command. However, they can be marked to be relative to top
              directory instead.

            - Relative paths passed to argument `inputs` or `outputs` are
              relative to top directory. They need not be marked.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # If task name is not given
    if not task_name:
        # Get the caller function's name
        task_name = inspect.stack()[1][3]

    # Print title
    print_title('Create task: {}'.format(task_name))

    # If cache key is given
    if cache_key:
        # Find cached task
        cached_task = _TASKS_CACHE.get(cache_key, None)

        # If have found cached task
        if cached_task is not None:
            # Print info
            print_text('Use cached task `{}`.'.format(cache_key))

            # Print end title
            print_title('Create task: {}'.format(task_name), is_end=True)

            # Return the cached task
            return cached_task

        # If have not found cached task.
        #     Continue to create task.

    # If cache key is not given.
    #     Continue to create task.

    # Normalized command parts list
    norm_part_s = []

    # Input nodes list
    input_node_s = []

    # Output nodes list
    output_node_s = []

    # Get the first command part that is program path
    first_part = parts[0]

    # If the first command part is list.
    # Notice the first command part can be list if the value is from `ctx.env`,
    # e.g `ctx.env.PYTHON`.
    if isinstance(first_part, list):
        # Use the first item in the list as the first command part
        parts[0] = first_part[0]

    # For given command parts list's each command part
    for part, wrapper_type in _normalize_items(ctx=ctx, items=parts):
        # If the command part is string
        if isinstance(part, str):
            # Add the string to the normalized list
            norm_part_s.append(part)

        # If the command part is node
        elif isinstance(part, Node):
            # Add the node's absolute path to the normalized list
            norm_part_s.append(part.abspath())

            # If the wrapper type is `input`
            if wrapper_type == 'input':
                # Add the node to the input nodes list
                input_node_s.append(part)

            # If the wrapper type is `output`
            elif wrapper_type == 'output':
                # Add the node to the output nodes list
                output_node_s.append(part)

            # If the wrapper type is not `input` or `output`
            else:
                # Do nothing
                pass

        # If the command part is not string or node
        else:
            # Get error message
            msg = 'Error (2W9YD): Command part is not valid: {0}.'.format(part)

            # Raise error
            raise ValueError(msg)

    # If environment dict is not given
    if env is None:
        # Use given context object's environment dict
        env = ctx.env

    # If working directory path is not given
    if cwd is None:
        # Set working directory path be top directory absolute path
        cwd = ctx.top_dir

    # If the working directory path is not absolute path.
    if not os.path.isabs(cwd):
        # Convert the working directory path to absolute path
        cwd = create_node(ctx, cwd).abspath()

    # Create task that runs command
    task = CmdTask(
        # Context object
        ctx=ctx,

        # Command parts list
        parts=norm_part_s,

        # Environment dict
        env=env,

        # Working directory
        cwd=cwd,

        # Task name
        task_name=task_name,
    )

    # For each input or output item.
    # Notice the code structure for handling input and output items are the
    # same so use the same code with different variables to avoid duplicate
    # code.
    for wrapper_type, item_s, node_s, nodes_set_func in [
        ('input', inputs, input_node_s, task.set_inputs),
        ('output', outputs, output_node_s, task.set_outputs),
    ]:
        # For each normalized item
        for item, _ in _normalize_items(
            # Context
            ctx=ctx,

            # Items to normalize
            items=item_s,

            # Convert string to node
            str_to_node=True,

            # Allow task item
            allow_task=True,
        ):
            # If the item is node
            if isinstance(item, Node):
                # Add the node to the nodes list
                node_s.append(item)

            # If the item is task
            elif isinstance(item, Task):
                # If the wrapper type is `input`
                if wrapper_type == 'input':
                    # Set the created task to run after the task
                    task.set_run_after(item)

                # If the wrapper type is `output`
                elif wrapper_type == 'output':
                    # Set the task to run after the created task
                    item.set_run_after(task)

                # If the wrapper type is not `input` or `output`
                else:
                    # Get error message
                    msg = (
                        'Error (3ZLGJ): Wrapper type is not valid: {0}.'
                    ).format(wrapper_type)

                    # Raise error
                    raise ValueError(msg)

            # If the item is not node or task
            else:
                # Get error message
                msg = 'Error (5H4GC): Item type is not valid: {0}.'.format(
                    item
                )

                # Raise error
                raise ValueError(msg)

        # Add these nodes to the created task as input or output targets
        nodes_set_func(node_s)

    # If need mark the created task as always run
    if always:
        # Mark the created task as always run
        task.always_run = True  # pylint: disable=W0201

    # If need add the created task to given context
    if add_to_group:
        # Add the created task to given context
        ctx.add_to_group(task)

    # If cache key is given
    if cache_key:
        # Add the created task to the cache
        _TASKS_CACHE[cache_key] = task

    # Print end title
    print_title('Create task: {}'.format(task_name), is_end=True)

    # Return the task
    return task


def build_ctx(pythonpath=None):
    """
    Decorator that makes decorated function use BuildContext instead of \
    Context instance. BuildContext instance has more methods.

    :param pythonpath: Path or list of paths to add to environment variable
        PYTHONPATH. Each path can be absolute path, or relative path relative
        to top directory.

        Notice if this decorator is used without arguments, argument
        `pythonpath` is the decorated function.

    :return: Two situations:

        - If decorator arguments are given, return no-argument decorator.
        - If decorator arguments are not given, return wrapper function.
    """
    # If argument `pythonpath` is string
    if isinstance(pythonpath, str):
        # Create paths list containing the string
        path_s = [pythonpath]

    # If argument `pythonpath` is list
    elif isinstance(pythonpath, list):
        # Use the list as paths list
        path_s = pythonpath

    # If argument `pythonpath` is not string or list,
    # it means the decorator is used without arguments.
    else:
        # Set paths list be None
        path_s = None

    # Create no-argument decorator
    def _noarg_decorator(func):
        """
        No-argument decorator.

        :param func: Decorated function.

        :return: Wrapper function.
        """
        # Create BuildContext subclass
        class _BuildContext(BuildContext):
            # Set command name for the context class
            cmd = func.__name__

            # Set function name for the context class
            fun = func.__name__

        # Create wrapper function
        @wraps(func)
        def _new_func(ctx, *args, **kwargs):
            """
            Wrapper function.

            :param ctx: BuildContext object.

            :param \\*args: Other arguments passed to decorated function.

            :param \\*\\*kwargs: Other keyword arguments passed to decorated
            function.

            :return: Decorated function's call result.
            """
            # If paths list is not empty
            if path_s:
                # For each path
                for path in path_s:
                    # If the path is absolute path
                    if os.path.isabs(path):
                        # Use the path as absolute path
                        abs_path = path

                    # If the path is not absolute path,
                    # it means relative path relative to top directory.
                    else:
                        # Create path node
                        path_node = create_node(ctx, path)

                        # Get absolute path
                        abs_path = path_node.abspath()

                    # Add the absolute path to environment variable PYTHONPATH
                    add_pythonpath(abs_path)

            # Call the decorated function
            result = func(ctx, *args, **kwargs)

            # Return the call result
            return result

        # Store the created context class with the wrapper function
        _new_func._context_class = _BuildContext  # pylint: disable=W0212

        # Return the wrapper function
        return _new_func

    # If decorator arguments are given
    if path_s is not None:
        # Return no-argument decorator
        return _noarg_decorator

    # If decorator arguments are not given
    else:
        # Argument `pythonpath` is the decorated function
        _func = pythonpath

        # Call the no-argument decorator to create wrapper function
        wrapper_func = _noarg_decorator(_func)

        # Return the wrapper function
        return wrapper_func


def config_ctx(func):
    """
    Decorator that makes decorated function use ConfigurationContext instead \
    of Context instance.

    :param func: Decorated function.

    :return: Decorated function.
    """
    # Create ConfigurationContext subclass
    class _ConfigurationContext(ConfigurationContext):
        # Set command name for the context class
        cmd = func.__name__

        # Set function name for the context class
        fun = func.__name__

    # Store the created context class with the decorated function
    func._context_class = _ConfigurationContext  # pylint: disable=W0212

    # Return the decorated function
    return func


def print_ctx(ctx):
    """
    Print given context's info.

    :param ctx: Context object.

    :return: None.
    """
    # Print title
    print_title('ctx attributes')

    # Print context object's attributes
    print_text(dir(ctx))

    # Print end title
    print_title('ctx attributes', is_end=True)

    # Print title
    print_title('ctx.options')

    # Print context options dict
    print_text(pformat(vars(ctx.options), indent=4, width=1))

    # Print end title
    print_title('ctx.options', is_end=True)

    # If the context object has `env` attribute.
    # Notice plain context object not has `env` attribute.
    if hasattr(ctx, 'env'):
        # Print title
        print_title('ctx.env')

        # Print context environment variables dict
        print_text(pformat(dict(ctx.env), indent=4, width=1))

        # Print end title
        print_title('ctx.env', is_end=True)


def pip_setup(
    ctx,
    python,
    setup_file,
    inputs=None,
    outputs=None,
    touch=None,
    check_import=False,
    cache_key=None,
    always=False,
):
    """
    Create task that sets up `pip`.

    :param ctx: BuildContext object.

    :param python: Python program path.

    :param setup_file: `get-pip.py` file relative path relative to top
        directory.

    :param inputs: Input items list to add to created task.

        See :paramref:`create_cmd_task.inputs` for allowed item types.

    :param outputs: Output items list to add to created task.

        See :paramref:`create_cmd_task.outputs` for allowed item types.

    :param touch: Touch file path for dirty checking.

    :param check_import: Whether import module for dirty checking.

    :param cache_key: Task cache key.

    :param always: Whether always run.

    :return: Created task.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # If touch file path is not given
    if touch is None:
        # Not update touch file
        touch_node = None

    # If touch file path is given
    else:
        # Update touch file
        touch_node, always = update_touch_file(
            # Context
            ctx=ctx,

            # Touch file path
            path=touch,

            # Whether import module for dirty checking
            check_import=check_import,

            # Module name to import for dirty checking
            check_import_module='pip',

            # Python program path for dirty checking
            check_import_python=python,

            # Whether always run
            always=always,
        )

    # Create task that runs `get-pip.py`
    task = create_cmd_task(
        # Context
        ctx=ctx,

        # Command parts
        parts=[
            # Python program path
            python,

            # Mark `get-pip.py` file as input target for dirty checking
            mark_input(setup_file),
        ],

        # Input items list
        inputs=inputs,

        # Output items list
        outputs=[
            # Use the touch node as output target for dirty checking
            touch_node,

            # Given output items list
            outputs,
        ],

        # Whether always run
        always=always,

        # Task cache key
        cache_key=cache_key or (python, 'pip_setup'),
    )

    # Return the created task
    return task


def virtualenv_setup(
    ctx,
    python,
    inputs=None,
    outputs=None,
    touch=None,
    check_import=False,
    pip_setup_file=None,
    pip_setup_touch=None,
    cache_key=None,
    always=False,
):
    """
    Create task that sets up `virtualenv` package.

    :param ctx: BuildContext object.

    :param python: Python program path.

    :param inputs: Input items list to add to created task.

        See :paramref:`create_cmd_task.inputs` for allowed item types.

    :param outputs: Output items list to add to created task.

        See :paramref:`create_cmd_task.outputs` for allowed item types.

    :param touch: Touch file path for dirty checking.

    :param check_import: Whether import module for dirty checking.

    :param pip_setup_file: `get-pip.py` file path for `pip_setup` task.

    :param pip_setup_touch: Touch file path for `pip_setup` task.

    :param cache_key: Task cache key.

    :param always: Whether always run.

    :return: Created task.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # If `get-pip.py` file path is not given
    if pip_setup_file is None:
        # Not create task that sets up `pip`
        pip_setup_task = None

    # If `get-pip.py` file path is given
    else:
        # Create task that sets up `pip`
        pip_setup_task = pip_setup(
            # Context
            ctx=ctx,

            # Python program path
            python=python,

            # `get-pip.py` file path
            setup_file=pip_setup_file,

            # Touch file path
            touch=pip_setup_touch,

            # Whether import module for dirty checking
            check_import=check_import,

            # Whether always run
            always=always,
        )

    # If touch file path is not given
    if touch is None:
        # Not update touch file
        touch_node = None
    else:
        # Update touch file
        touch_node, always = update_touch_file(
            # Context
            ctx=ctx,

            # Touch file path
            path=touch,

            # Whether import module for dirty checking
            check_import=check_import,

            # Module name to import for dirty checking
            check_import_module='virtualenv',

            # Python program path for dirty checking
            check_import_python=python,

            # Whether always run
            always=always,
        )

    # Create task that sets up `virtualenv` package
    task = create_cmd_task(
        # Context
        ctx=ctx,

        # Command parts
        parts=[
            # Python program path
            python,

            # Run module
            '-m',

            # Module name
            'pip',

            # Install package
            'install',

            # Package name
            'virtualenv',
        ],

        # Input items list
        inputs=[
            # Run after the task that sets up `pip`
            pip_setup_task,

            # Given input items list
            inputs,
        ],

        # Output items list
        outputs=[
            # Use the touch node as output target for dirty checking
            touch_node,

            # Given output items list
            outputs,
        ],

        # Whether always run
        always=always,

        # Task cache key
        cache_key=cache_key or (python, 'virtualenv'),
    )

    # Return the created task
    return task


def create_venv(
    ctx,
    python,
    venv_path,
    inputs=None,
    outputs=None,
    pip_setup_file=None,
    pip_setup_touch=None,
    virtualenv_setup_touch=None,
    task_name=None,
    cache_key=None,
    always=False,
):
    """
    Create task that sets up virtual environment.

    :param ctx: BuildContext object.

    :param python: Python program path.

    :param venv_path: Virtual environment directory relative path relative to
        top directory.

    :param inputs: Input items list to add to created task.

        See :paramref:`create_cmd_task.inputs` for allowed item types.

    :param outputs: Output items list to add to created task.

        See :paramref:`create_cmd_task.outputs` for allowed item types.

    :param pip_setup_file: `get-pip.py` file path for `pip_setup` task.

    :param pip_setup_touch: Touch file path for `pip_setup` task.

    :param virtualenv_setup_touch: Touch file path for `virtualenv_setup` task.

    :param task_name: Task name for display purpose.

    :param cache_key: Task cache key.

    :param always: Whether always run.

    :return: Created task.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # Create task that sets up `virtualenv` package
    virtualenv_setup_task = virtualenv_setup(
        # Context
        ctx=ctx,

        # Python program path
        python=python,

        # Touch file path
        touch=virtualenv_setup_touch,

        # `get-pip.py` file path for `pip_setup` task.
        pip_setup_file=pip_setup_file,

        # Touch file path for `pip_setup` task.
        pip_setup_touch=pip_setup_touch,
    )

    # Get virtual environment directory path node
    venv_path_node, _ = _normalize_items(
        ctx=ctx,
        items=[venv_path],
        # Convert path string to node
        str_to_node=True
    )[0]

    # Create task that sets up virtual environment.
    task = create_cmd_task(
        # Context
        ctx=ctx,

        # Command parts
        parts=[
            # Python program path
            python,

            # Run module
            '-m',

            # Module name
            'virtualenv',

            # Virtual environment directory absolute path
            venv_path_node.abspath(),
        ],

        # Input items list
        inputs=[
            # Run after the task that sets up `virtualenv` package
            virtualenv_setup_task,

            # Given input items list
            inputs,
        ],

        # Output items list
        outputs=[
            # Add the virtual environment's `python` program path as output
            # target for dirty checking
            get_python_path(venv_path),

            # Add the virtual environment's `pip` program path as output target
            # for dirty checking
            get_pip_path(venv_path),

            # Given output items list
            outputs,
        ],

        # Whether always run
        always=always,

        # Task name
        task_name=task_name,

        # Task cache key
        cache_key=cache_key or (python, venv_path),
    )

    # Return the created task
    return task


def pip_ins_req(
    ctx,
    python,
    req_path,
    venv_path=None,
    inputs=None,
    outputs=None,
    touch=None,
    check_import=False,
    check_import_module=None,
    pip_setup_file=None,
    pip_setup_touch=None,
    virtualenv_setup_touch=None,
    always=False,
):
    """
    Create task that uses given virtual environment's `pip` to sets up \
    packages listed in given requirements file.

    :param ctx: BuildContext object.

    :param python: Python program path used to set up `pip` and `virtualenv`.

    :param req_path: Requirements file relative path relative to top directory.

    :param venv_path: Virtual environment directory relative path relative to
        top directory.

        If given, will create the virtual environment and set up packages
        listed in given requirements file in the virtual environment.

        If not given, will set up packages listed in given requirements file in
        given Python program's environment.

    :param inputs: Input items list to add to created task.

        See :paramref:`create_cmd_task.inputs` for allowed item types.

    :param outputs: Output items list to add to created task.

        See :paramref:`create_cmd_task.outputs` for allowed item types.

    :param touch: Touch file path for dirty checking.

    :param check_import: Whether import module for dirty checking.

    :param check_import_module: Module name to import for dirty checking.

    :param pip_setup_file: `get-pip.py` file path for `pip_setup` task.

    :param pip_setup_touch: Touch file path for `pip_setup` task.

    :param virtualenv_setup_touch: Touch file path for `virtualenv_setup` task.

    :param always: Whether always run.

    :return: Created task.
    """
    # Ensure given context object is BuildContext object
    _ensure_build_context(ctx)

    # If virtual environment directory path is not given
    if venv_path is None:
        # Use given Python program path
        venv_python = python

    # If virtual environment directory path is given
    else:
        # Get Python program path in the virtual environment
        venv_python = get_python_path(venv_path)

        # Mark the path as input target
        venv_python = mark_input(venv_python)

    # If virtual environment directory path is not given,
    # it means not create virtual environment.
    if venv_path is None:
        # Create task that sets up `pip`
        pip_setup_task = pip_setup(
            # Context
            ctx=ctx,

            # Python program path
            python=python,

            # `get-pip.py` file path
            setup_file=pip_setup_file,

            # Touch file path
            touch=pip_setup_touch,

            # Whether import module for dirty checking
            always=always,
        )

        # Not create virtual environment
        venv_task = None

    # If virtual environment directory path is given
    else:
        # Not create task that sets up `pip` here because `create_venv`
        # function below will do
        pip_setup_task = None

        # Create task that sets up virtual environment
        venv_task = create_venv(
            # Context
            ctx=ctx,

            # Python program path
            python=python,

            # Virtual environment directory path
            venv_path=venv_path,

            # Output items list
            outputs=[
                # Add the virtual environment's `python` program path as output
                # target for dirty checking
                get_python_path(venv_path),

                # Add the virtual environment's `pip` program path as output
                # target for dirty checking
                get_pip_path(venv_path),
            ],

            # Whether always run
            always=always,

            # Task name
            task_name='Create venv `{}`'.format(venv_path),

            # `get-pip.py` file path for `pip_setup` task
            pip_setup_file=pip_setup_file,

            # Touch file path for `pip_setup` task
            pip_setup_touch=pip_setup_touch,

            # Touch file path for `virtualenv_setup` task
            virtualenv_setup_touch=virtualenv_setup_touch,
        )

    # If touch file path is not given
    if not touch:
        # Not update touch file
        touch_node = None

    # If touch file path is given
    else:
        # Update touch file
        touch_node, always = update_touch_file(
            # Context
            ctx=ctx,

            # Touch file path
            path=touch,

            # Whether import module for dirty checking
            check_import=check_import,

            # Module name to import for dirty checking
            check_import_module=check_import_module,

            # Python program path for dirty checking
            check_import_python=venv_python,

            # Whether always run
            always=always,
        )

    # Create task that sets up packages
    task = create_cmd_task(
        # Context
        ctx=ctx,

        # Command parts
        parts=[
            # Python program path
            venv_python,

            # Run module
            '-m',

            # Module name
            'pip',

            # Install package
            'install',

            # Read package names from requirements file
            '-r',

            # Requirements file path. Mark as input target.
            mark_input(req_path),
        ],

        # Input items list
        inputs=inputs,

        # Output items list
        outputs=[
            # Use the touch node as output target for dirty checking
            touch_node,

            # Given output items list
            outputs,
        ],

        # Whether always run
        always=always,
    )

    # Chain these tasks to run one after another
    chain_tasks([
        pip_setup_task,
        venv_task,
        task,
    ])

    # Return the created task
    return task


def git_clean(ctx):
    """
    Delete all files untracked by git.

    :param ctx: Context object.

    :return: None.
    """
    # Get command parts
    cmd_part_s = [
        # Program path
        'git',

        # Clean untracked files
        'clean',

        # Remove all untracked files
        '-x',

        # Remove untracked directories too
        '-d',

        # Force to remove
        '-f',

        # Give two `-f` flags to remove sub-repositories too
        '-f',
    ]

    # Print title
    print_title('git_clean')

    # Print the command in multi-line format
    print_text(_format_multi_line_command(cmd_part_s))

    # Create subprocess to run the command in top directory
    proc = subprocess.Popen(cmd_part_s, cwd=ctx.top_dir)

    # Wait the subprocess to finish
    proc.wait()

    # Print end title
    print_title('git_clean', is_end=True)
