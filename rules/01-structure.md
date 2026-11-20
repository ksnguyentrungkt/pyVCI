# pyVCI — Tool Build Rules

This file is what Claude reads before writing any pyVCI tool. pyVCI is a
separate pyRevit extension from pyNBT (NBT's personal tab) - this one
distributes tools to the whole VCI team. Same author (NBT) and the same
build conventions as pyNBT's own `rules/01-structure.md`, copied here so
pyVCI stays maintainable on its own without depending on the pyNBT repo.

## 1. Folder & naming

- Extension root: `pyVCI.extension\`
  - `pyVCI.tab\` — production tab, tools the VCI team actually uses day to
    day
  - `pyVCI Dev.tab\` — staging tab for tools not yet confirmed working in a
    real Revit test (create this tab only once there is a first tool to
    stage in it)
  - `lib\pyVCI\` — shared code (`compat.py`, `theme.py`). Import it, never
    copy-paste its contents into a tool.
- One tool = one `{ToolName}.pushbutton\` folder, containing at minimum:
  - `script.py` (required)
  - `bundle.yaml` (required — `title` + `tooltip`, optionally `author`)
  - `icon.png` (required — 96×96, drawn at 384×384 and downsampled with
    LANCZOS for crisp anti-aliasing, per pyNBT's icon-guide)
  - optionally a second `.py` file when the tool has a large standalone
    data table or logic block worth editing on its own
- Panel = a group of related tools. Only `Update` exists so far. Pick the
  closest existing panel first when adding a new tool; only propose a new
  one when nothing fits.

## 2. Script header (every `script.py`)

```python
# -*- coding: utf-8 -*-
"""<Tool Name>

<what it does, how to select/run it, edge cases — plain language, this is
what NBT and future-you read to remember what the tool does>
"""

__title__ = 'Tool\nName'   # matches the button label, \n where it wraps
__author__ = 'NBT'
```

`TOOL_NAME = '...'` is declared as a constant near the top of the file and
reused in every `forms.alert(..., title=TOOL_NAME)` call.

## 3. Shared lib import (mandatory bootstrap block)

Every tool that needs `pyVCI.compat` or `pyVCI.theme` starts with this exact
block (copy it, never re-derive the path or re-declare a color/helper
locally):

```python
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))   # ...\{Tool}.pushbutton
PANEL_DIR = os.path.dirname(SCRIPT_DIR)                    # ...\{Panel}.panel
TAB_DIR = os.path.dirname(PANEL_DIR)                       # ...\pyVCI.tab (or pyVCI Dev.tab)
EXTENSION_DIR = os.path.dirname(TAB_DIR)                   # ...\pyVCI.extension
LIB_DIR = os.path.join(EXTENSION_DIR, 'lib')

if LIB_DIR not in sys.path:
    sys.path.append(LIB_DIR)

from pyVCI.compat import eid_int          # only what's actually used
from pyVCI.theme import CLR_HEADER, brush  # only if the tool has a WPF window
```

## 4. Safe-Stack (allowed imports)

Same as pyNBT (IronPython 2.7 engine, same Revit API surface):

**Always OK:** `os`, `sys`, `math`, `json`, `csv`, `re`, `datetime`, `clr`,
`System.Windows.*` (WPF, only after the matching `clr.AddReference`),
`Autodesk.Revit.DB` / `.UI` / `.DB.Structure` / `.Exceptions`,
`pyrevit.revit` / `.forms` / `.script`.

**Ask NBT before using:** any DLL not already vendored in pyRevit or the
Revit API; any Python-3-only library (pandas, numpy, openpyxl) — IronPython
2.7 cannot run these; a library suggested by another AI/tool that needs a
separate pip install into IronPython.

**Never:** COM automation (`System.Activator.CreateInstance`, Excel COM —
known to break in pyRevit's IronPython, use paste-based input instead);
unlicensed/copyleft code pasted from the internet; `System.Windows.Forms`
dialogs inside a modeless WPF window (use `Microsoft.Win32.OpenFileDialog`
instead).

## 5. Transactions & safety

- Every model write is wrapped in `Transaction(doc, 'pyVCI - {Tool Name}')`
  with `try/except` + `RollBack()` on error.
- A modeless WPF window uses `ExternalEvent`/`IExternalEventHandler`; any UI
  update coming from an event handler goes through
  `window.Dispatcher.Invoke(System.Action(...))`.
- Read `RebarBarType.Name` (or any `ElementType.Name`) via
  `Element.Name.GetValue(el)`, never plain `.Name` — direct attribute read
  throws in this IronPython engine even though writing to it works fine.
- **3-step test before a tool ever touches a real project:** (1) run on a
  detached/test file, (2) NBT (or the team member testing it) confirms the
  result visually in Revit, (3) only then use it on a live project. No tool
  goes near a real deliverable model on its first run.

## 6. UI (when the tool has a window)

- Colors: import from `lib/pyVCI/theme.py` (`CLR_HEADER`, `CLR_APPLY`,
  `CLR_BG`, `CLR_BORDER`, ...) — never declare a new palette in a tool.
- Layout: header (title + version/date) / body (left = selection controls,
  right = preview or results) / footer (status text + primary action button
  in `CLR_APPLY`, secondary buttons neutral).
- WPF gotchas: `clr.AddReference` for `PresentationFramework`,
  `PresentationCore`, `WindowsBase`, `System.Xaml` must all come before any
  `System.Windows` import; `GridLength` needs `float()` conversion
  (`GridLength(float("60"))`, not `GridLength("60")`).

## 7. Versioning & the Update mechanism

- `VERSION` file at the extension root plus a matching GitHub **Release**
  tag (not just a commit on `main`) — bump on a meaningfully-tested batch
  of changes, not on every draft.
- **Pushing to `main` never affects the team.** The `Update` tool checks
  the repo's latest published Release, not the latest commit — so NBT can
  push and test work-in-progress commits on `main` freely. A team member's
  machine only sees "a new version is available" once a Release is
  explicitly published on GitHub.
- `Update` asks Yes/No before downloading or changing anything, then
  performs a full **mirror sync** (copies everything new/changed, deletes
  anything locally present that's no longer in the release) rather than a
  copy-only update — so a tool removed on GitHub actually disappears from
  every machine on the next Update instead of lingering forever.
- **NBT must not click Update on his own dev/test machine** unless he is
  certain everything currently on disk has already been committed and
  pushed — mirror sync will delete any local uncommitted work. Use
  pyRevit's own "Reload" instead when iterating locally. (Same standing
  rule as pyNBT's Update tool.)
- `pyVCI Dev.tab` (once created) holds tools not yet confirmed working in a
  real Revit test. Once confirmed, the tool moves into `pyVCI.tab` (correct
  panel) in the same step that marks it `active` in `TOOL_REGISTER.md`.

## 8. Before writing anything

Check `TOOL_REGISTER.md` first. If a tool close to the request already
exists, extend it instead of creating a near-duplicate.
