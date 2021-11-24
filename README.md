# Toggl to ERPnext

## Usage

First, install the project, using the venv, install the requirements, and create a `.env` file based on the example.

Use the command `python main.py 2021-07-01 2021-07-31` where the two dates are the Toggl interval to import.

## Export failing?


If some entries are overlapping, ERPnext will refuse the timesheet. Please be check that no other timesheet already have entries for the same dates and times.

Note: in order to avoid tasks overlapping (ie: ending the same minute as the start of the next one), the beginning of some entries are automatically adjusted, while keeping the same duration.

## License

```
        DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
```