# XiPrtScr

A screenshot capturer with grid history viewer, can use XInput controller to issue commands.

## How use

1. Clone the project
1. `pipenv install`
1. Get the xbox controller
1. Configure the constants at around the top of `main.pyw` file
1. Run `main.pyw` with pipenv (`pipenv run python main.pyw`)
1. Enable 'LT/RT take' in menu 'Option'
1. Run your game
1. You can take a screenshot by holding Left Trigger and Right Trigger on the xbox controller to the very back (255/255 value, or max gas, first player controller only)

## What can do

- Issue screenshot capture with your xinput controller (xbox controller)
- View captured screenshots with a grid view
- Rotate (deque-wise) history
- Delete all/Save all history
- Some simple options such as xinput pool interval, history limit, on/off xinput
- With each screenshot:
    - Copy to clipboard
    - Save/Save as individual file
    - Delete from history
    - Pin (skip it when user issues 'delete all')

> **_NOTE:_**  There are better screenshot capturing tools, this is only made because I couldn't find one that I can use with by xbox controller

> **_note:_**  I can't find a way to capture the Print Screen key

> **_note:_**  It will only check state of the first player controller (the first player xbox controller will show the 9-12 o'clock ring as first player)

## Requirements

### Required

- pipenv
- Python 3.12

### Windows

- It is not cross-platform due to these problems:
    - pywin32 (for clipboard reading, couldn't find one cross platform that supports copy as bitmap)
    - tkinter (xpnative theme)

## TODO

- Maybe save files in another thread so that it will not block the tkinter mainloop

## License

MIT

## Contribution

Feel free
