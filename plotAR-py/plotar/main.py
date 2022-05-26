import click

from .server import start_server
from .export.__main__ import main as export

@click.group()
def main():
    pass

main.add_command(export, name='export')
main.add_command(start_server, name='server')

if __name__ == '__main__':
    main()
