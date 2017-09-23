from datetime import timedelta

import click

VERBOSE = False


def configure(verbose):
    global VERBOSE
    VERBOSE = verbose


def info(msg):
    if VERBOSE: click.secho(msg, fg='green')


def warn(msg):
    click.secho(msg, fg="yellow")


def progress(msg):
    click.secho(msg, fg='blue')


def banner_warn(msg, data):
    banner(msg)
    info_banner(data)


def error(err_msg, raise_exception=False):
    click.secho(err_msg, fg="red")
    if raise_exception:
        raise click.UsageError(err_msg)


def banner(data):
    click.secho(data, fg="yellow")

def info_banner(data):
    click.secho(data, fg='green')

def print_time_delta(tdelta):
    # type: (timedelta) -> object
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    format_ = "{minutes}m {seconds}s"
    if d['days'] > 0:
        format_ = "{days} days " + format_
    if d['hours'] > 0:
        format_ = "{hours}h " + format_
    return format_.format(**d)
