#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for setting up config arguments."""
import os
from typing import Any, Dict, Iterable, List, Mapping, Tuple
import argparse
import configargparse


def check_file(file: str, perms: int = None) -> bool:
    """
    Check that the given file exists and has the given minimum permissions.

    Essentially just a wrapper around ``os.access(os.path.abspath(file), perms)``.

    Parameters
    ----------
    file : str
        Path of file to check, can be relative or absolute.
    perms : int, optional
        Logical OR-ed Combination of ``os.R_OK``, ``os.W_OK`` and ``os.X_OK``. By default, will check
        if file is readable. For instance, to check if a file is readable and writeable, set perms to
        ``os.R_OK | os.W_OK``.

    Returns
    -------
    bool
        ``True`` if the given file exists and has the given perms, else ``False``
    """

    if perms is None:
        perms = os.R_OK
    perms |= os.F_OK
    return os.access(os.path.abspath(file), perms)


class FuncAction(argparse.Action):
    """
    argparse Action allowing for a function on an arg before storing it.

    To use, subclass override the ``func`` method, and then pass your class into ``add_argument`` under
    the ``action`` kwarg.

    Examples
    --------
    >>> from snafu.config import FuncAction
    >>> class AppendStr(FuncAction):
    ...     def func(self, arg: Any) -> str:
    ...         return str(arg) + "_this_is_my_string"
    >>> import argparse
    >>> p = argparse.ArgumentParser()
    >>> p.add_argument("value", type=str, action=AppendStr)
    >>> p.parse_args(["my_input"]).value
    'my_input_this_is_my_string'
    """

    def func(self, arg: Any) -> Any:
        """Overwrite me."""

    def __call__(
        self,
        parser: configargparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string=None,
    ):
        setattr(namespace, self.dest, self.func(values))


class ConfigArgument:
    """
    Store arguments that can be passed to ``argparse.add_argument``.

    Please see the :py:class:`~snafu.benchmarks.Benchmark base class and
    :py:meth:`~snafu.config.Config.populate_parser` for more information on specific usage within
    benchmark-wrapper.

    Attributes
    ----------
    args : tuple
        Stored positional arguments passed to class during instantiation
    kwargs : dict
        Stored keyword arguments passed to class during instantiation

    Examples
    --------
    >>> from snafu.config import ConfigArgument
    >>> c = ConfigArgument("one", 2, "three", a="b", c="d")
    >>> c.args
    ('one', 2, 'three')
    >>> c.kwargs
    {"a": "b", "c": "d"}
    """

    def __init__(self, *args, **kwargs):
        self.args: Tuple[Any] = args
        self.kwargs: Dict[str, Any] = kwargs


class Config:
    """
    Class for managing parsable configuration parameters.

    Essentially a helpful wrapper around :py:mod:`argparse` and :py:mod:`configargparse`. Configuration
    paramemters can be accessed as attributes of this class (for instance ``config.my_param`` points to
    ``config.params.my_param``).

    Parameters
    ----------
    tool_name : str
        Name of the tool that this instance will load params for.

    Attributes
    ----------
    params : :py:class:`argparse.Namespace`
        Instance of a :py:class:`argparse.Namespace` which holds the parsed params. Same usage as what
        is returned from :py:meth:`argparse.ArgumentParser.parse_args`.
    parser : :py:class:`configargparse.ArgumentParser`
        The singleton instance of a parser that `configargparse` provides through
        :py:func:`~configargparse.get_argument_parser`
    group
        Argument group specific to the config instance where arguments will be placed.
    env_to_params : dict
        Maps environment variable names to their param names.
    """

    def __init__(self, tool_name: str):
        self.params: argparse.Namespace = argparse.Namespace()
        self.parser: configargparse.ArgumentParser = configargparse.get_argument_parser()
        self.group = self.parser.add_argument_group(tool_name)
        self.env_to_params: Mapping[str, str] = dict()

    def __getattr__(self, attr):
        return getattr(self.params, attr, None)

    def get_env(self) -> Mapping[str, str]:
        """
        Return already-parsed environment variables and their values within a dictionary.

        Will add in environment variables from the OS environment.
        """

        env = {env_var: str(getattr(self.params, dest)) for env_var, dest in self.env_to_params.items()}
        env.update(os.environ)
        return env

    def add_argument(self, *args, **kwargs) -> None:
        """
        Add an argument into the config. Will pass given arguments along to the param group unmodified.

        Has the same usage as :py:meth:`argparse.ArgumentParser.add_argument`
        """

        action = self.group.add_argument(*args, **kwargs)
        env_var = getattr(action, "env_var", None)
        if env_var is not None:
            self.env_to_params[env_var] = action.dest

    def populate_parser(self, args: Iterable[ConfigArgument]) -> None:
        """
        Populate args into the parser from the given list of config arguments.

        Parameters
        -----------
        args : list of :py:class:`~snafu.config.ConfigArgument`
        """

        for arg in args:
            self.add_argument(*arg.args, **arg.kwargs)

    def parse_args(self, args: List[str] = None) -> None:
        """
        Parse arguments and store them in the ``params`` attribute.

        Parameters
        -----------
        args : list of str, optional
            List of arguments to be passed manually to the parser for parsing.
        """

        self.parser.parse_known_args(args=args, namespace=self.params)
