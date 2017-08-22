import click

VERBOSE = False


def configure(verbose):
    global VERBOSE
    VERBOSE = verbose


def info(msg):
    print msg
    if VERBOSE: click.secho(msg, fg='green')


def warn(msg):
    click.secho(msg, fg="yellow")


def banner_warn(msg, data):
    click.secho(msg, fg="yellow")
    click.secho(data, fg="yellow", bg='blue')


def error(err_msg,raise_exception=False):
    click.secho(err_msg,fg="red")
    if raise_exception:
        raise click.UsageError(err_msg)