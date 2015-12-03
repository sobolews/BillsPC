from itertools import izip_longest
from tabulate import tabulate

def multitabulate(tables, tablefmt='psql'):
    """
    Return a string representing multiple tables, printed side-by-side.

    `tables` is a list of lists of lists; each list of lists should contain headers as the first
    list, followed by zero or more rows.

    example:
    tables = [[ ['Move', '%'], ['outrage', '100%'], ['roost', '70%'], ['firepunch', '54%'] ],
              [ ['Item', '%'], ['Lum Berry', '94%'], ['Choice Band', '6%'] ],
              [ ['Ability', '%'], ['Multiscale', None] ]]
    """
    tabulated = [tabulate(table[1:], table[0], tablefmt=tablefmt).splitlines() for table in tables]
    total_lines = len(max(tabulated, key=len))
    for table in tabulated:
        for _ in range(total_lines - len(table)):
            table.append(' ' * len(table[0]))
    return '\n'.join('  '.join(line) for line in zip(*tabulated))

