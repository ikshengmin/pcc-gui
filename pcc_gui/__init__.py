"""pcc_gui: a declarative desktop GUI framework compiled by pcc.

`import pcc_gui` pulls every framework module into the program closure so the
C-ABI symbols (`pcc_kit_*`, `pcc_gui_*`) that applications declare with
`pcc.extern` resolve inside the same pcc1 link.
"""

from . import pcc_gui_app  # noqa: F401
from . import pcc_gui_app_lifecycle  # noqa: F401
from . import pcc_gui_binding  # noqa: F401
from . import pcc_gui_cg  # noqa: F401
from . import pcc_gui_clipboard  # noqa: F401
from . import pcc_gui_commands  # noqa: F401
from . import pcc_gui_components  # noqa: F401
from . import pcc_gui_controls  # noqa: F401
from . import pcc_gui_elements  # noqa: F401
from . import pcc_gui_events  # noqa: F401
from . import pcc_gui_image  # noqa: F401
from . import pcc_gui_ipc  # noqa: F401
from . import pcc_gui_kit  # noqa: F401
from . import pcc_gui_layout  # noqa: F401
from . import pcc_gui_scheduler  # noqa: F401
from . import pcc_gui_style  # noqa: F401
from . import pcc_gui_text  # noqa: F401
from . import pcc_gui_theme_anim  # noqa: F401
from . import pcc_gui_window  # noqa: F401

from .pcc_gui_dialog import *
