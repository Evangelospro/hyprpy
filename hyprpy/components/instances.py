"""The central :class:`Instance` class for interfacing with Hyprland.

This class acts as the root for accessing other components like workspaces, windows, and monitors,
and offers capabilities to listen to events and signals emitted by the underlying Hyprland system.
"""

from typing import List, Union
import json
import logging

from hyprpy.data.models import InstanceData
from hyprpy.components.windows import Window
from hyprpy.components.workspaces import Workspace
from hyprpy.components.monitors import Monitor
from hyprpy.utils import assertions, shell
from hyprpy.utils.sockets import CommandSocket, EventSocket
from hyprpy.utils.signals import DeprecatedSignal, Signal


log = logging.getLogger(__name__)


class SignalCollection:
    """A collection of signals belonging to an :class:`~Instance`."""

    def __init__(self):
        #: Emits the following Signal Data when a keyboard's layout is changed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================= ============ ===============================
        #:       Name              Type         Description
        #:       ================= ============ ===============================
        #:       ``keyboard_name`` :class:`str` Name of the keyboard
        #:       ``layout_name``   :class:`str` Name of the newly active layout
        #:       ================= ============ ===============================
        self.activelayout: Signal = Signal(self)

        #: Emits the following Signal Data when the special workspace on a monitor changes:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============ =====================================================================
        #:       Name               Type         Description
        #:       ================== ============ =====================================================================
        #:       ``workspace_name`` :class:`str` :attr:`~hyprpy.components.workspaces.Workspace.name` of the workspace
        #:       ``monitor_name``   :class:`str` :attr:`~hyprpy.components.monitors.Monitor.name` of the monitor
        #:       ================== ============ =====================================================================
        #:
        #: When the special workspace is closed, ``workspace_name`` is an empty string.
        self.activespecial: Signal = Signal(self)

        #: Emits the following Signal Data when the active window is changed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================ ============ =================================================================================
        #:       Name             Type         Description
        #:       ================ ============ =================================================================================
        #:       ``window_class`` :class:`str` The newly active window's :attr:`~hyprpy.components.windows.Window.wm_class`
        #:       ``window_title`` :class:`str` Name of the newly active window's :attr:`~hyprpy.components.windows.Window.title`
        #:       ================ ============ =================================================================================
        self.activewindow: Signal

        #: Emits the following Signal Data when the active window is changed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============ ===========================================================================
        #:       Name               Type         Description
        #:       ================== ============ ===========================================================================
        #:       ``window_address`` :class:`str` The newly active Window's :attr:`~hyprpy.components.windows.Window.address`
        #:       ================== ============ ===========================================================================
        self.activewindowv2: Signal = Signal(self)

        #: Emits the following Signal Data when a window's floating state changes:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= ===============================================================
        #:       Name               Type          Description
        #:       ================== ============= ===============================================================
        #:       ``window_address`` :class:`str`  :attr:`~hyprpy.components.windows.Window.address` of the window
        #:       ``is_floating``    :class:`bool` ``True`` if the window is floating, and ``False`` otherwise.
        #:       ================== ============= ===============================================================
        self.changefloatingmode: Signal = Signal(self)

        #: Emits the following Signal Data when a layerSurface is unmapped:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ============= ============= ===========
        #:       Name          Type          Description
        #:       ============= ============= ===========
        #:       ``namespace`` :class:`str`  `Unknown`
        #:       ============= ============= ===========
        self.closelayer: Signal = Signal(self)

        #: Emits the following Signal Data when a window is closed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= ======================================================================
        #:       Name               Type          Description
        #:       ================== ============= ======================================================================
        #:       ``window_address`` :class:`str`  :attr:`~hyprpy.components.windows.Window.address` of the closed window
        #:       ================== ============= ======================================================================
        self.closewindow: Signal = Signal(self)

        #: Emitted upon a completed config reload.
        #:
        #: Does not emit any Signal Data.
        self.configreloaded: Signal = Signal(self)

        #: Emits the following Signal Data when a workspace is created:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= =============================
        #:       Name               Type          Description
        #:       ================== ============= =============================
        #:       ``workspace_name`` :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.name` of the created workspace
        #:       ================== ============= =============================
        self.createworkspace: Signal = Signal(self)

        #: Emits the following Signal Data when a workspace is created:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= =============================================================================
        #:       Name               Type          Description
        #:       ================== ============= =============================================================================
        #:       ``workspace_id``   :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.id` of the created workspace
        #:       ``workspace_name`` :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.name` of the created workspace
        #:       ================== ============= =============================================================================
        self.createworkspacev2: Signal = Signal(self)

        #: Emits the following Signal Data when a workspace is destroyed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= ===============================================================================
        #:       Name               Type          Description
        #:       ================== ============= ===============================================================================
        #:       ``workspace_name`` :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.name` of the destroyed workspace
        #:       ================== ============= ===============================================================================
        self.destroyworkspace: Signal = Signal(self)

        #: Emits the following Signal Data when a workspace is destroyed:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= ===============================================================================
        #:       Name               Type          Description
        #:       ================== ============= ===============================================================================
        #:       ``workspace_id``   :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.id` of the destroyed workspace
        #:       ``workspace_name`` :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.name` of the destroyed workspace
        #:       ================== ============= ===============================================================================
        self.destroyworkspacev2: Signal = Signal(self)

        #: Emits the following Signal Data when the active monitor changes:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================== ============= ==================================================================================
        #:       Name               Type          Description
        #:       ================== ============= ==================================================================================
        #:       ``monitor_name``   :class:`str`  :attr:`~hyprpy.components.monitors.Monitor.name` of the newly active monitor
        #:       ``workspace_name`` :class:`str`  :attr:`~hyprpy.components.workspaces.Workspace.name` of the newly actove workspace
        #:       ================== ============= ==================================================================================
        self.focusedmon: Signal

        #: Emits the following Signal Data when the fullscreen state of any window changes:
        #:
        #:    .. table::
        #:       :widths: auto
        #:       :align: left
        #:
        #:       ================= ============= ============================================================================================
        #:       Name              Type          Description
        #:       ================= ============= ============================================================================================
        #:       ``is_fullscreen`` :class:`bool` ``True`` if fullscreen mode was activated, and ``False`` if fullscreen mode was deactivated.
        #:       ================= ============= ============================================================================================
        self.fullscreen: Signal = Signal(self)

        #: emitted when ignoregrouplock is toggled.	0/1
        self.ignoregrouplock: Signal = Signal(self)

        #: emitted when lockgroups is toggled.	0/1
        self.lockgroups: Signal = Signal(self)

        #: emitted when a window requests a change to its minimized state. MINIMIZED is either 0 or 1.	WINDOWADDRESS,MINIMIZED
        self.minimize: Signal = Signal(self)

        #: emitted when a monitor is added (connected)	MONITORNAME
        self.monitoradded: Signal = Signal(self)

        #: emitted when a monitor is added (connected)	MONITORID,MONITORNAME,MONITORDESCRIPTION
        self.monitoraddedv2: Signal = Signal(self)

        #: emitted when a monitor is removed (disconnected)	MONITORNAME
        self.monitorremoved: Signal = Signal(self)

        #: emitted when the window is merged into a group. returns the address of a merged window	WINDOWADDRESS
        self.moveintogroup: Signal = Signal(self)

        #: emitted when the window is removed from a group. returns the address of a removed window	WINDOWADDRESS
        self.moveoutofgroup: Signal = Signal(self)

        #: emitted when a window is moved to a workspace	WINDOWADDRESS,WORKSPACENAME
        self.movewindow: Signal = Signal(self)

        #: emitted when a window is moved to a workspace	WINDOWADDRESS,WORKSPACEID,WORKSPACENAME
        self.movewindowv2: Signal = Signal(self)
        
        #: emitted when a workspace is moved to a different monitor	WORKSPACENAME,MONNAME
        self.moveworkspace: Signal = Signal(self)

        #: emitted when a workspace is moved to a different monitor	WORKSPACEID,WORKSPACENAME,MONNAME
        self.moveworkspacev2: Signal = Signal(self)

        #: emitted when a layerSurface is mapped	NAMESPACE
        self.openlayer: Signal = Signal(self)

        #: emitted when a window is opened	WINDOWADDRESS,WORKSPACENAME,WINDOWCLASS,WINDOWTITLE
        self.openwindow: Signal = Signal(self)

        #: emitted when a window is pinned or unpinned	WINDOWADDRESS,PINSTATE
        self.pin: Signal = Signal(self)

        #: emitted when a workspace is renamed	WORKSPACEID,NEWNAME
        self.renameworkspace: Signal = Signal(self)

        #: state,handle where the state is a toggle status and the handle is one or more window addresses separated by a comma e.g. 0,0x64cea2525760,0x64cea2522380 where 0 means that a group has been destroyed and the rest informs which windows were part of it	0/1,WINDOWADDRESS(ES)
        self.returns: Signal = Signal(self)

        #: emitted when a screencopy state of a client changes. Keep in mind there might be multiple separate clients. State is 0/1, owner is 0 - monitor share, 1 - window share	STATE,OWNER
        self.screencast: Signal = Signal(self)

        #: emitted when a keybind submap changes. Empty means default.	SUBMAPNAME
        self.submap: Signal = Signal(self)

        #: emitted when togglegroup command is used.
        self.togglegroup: Signal = Signal(self)

        #: emitted when a window requests an urgent state	WINDOWADDRESS
        self.urgent: Signal = Signal(self)

        #: emitted when a window title changes.	WINDOWADDRESS
        self.windowtitle: Signal = Signal(self)

        #: emitted on workspace change. Is emitted ONLY when a user requests a workspace change, and is not emitted on mouse movements (see activemon)	WORKSPACENAME
        self.workspace: Signal = Signal(self)

        #: emitted on workspace change. Is emitted ONLY when a user requests a workspace change, and is not emitted on mouse movements (see activemon)	WORKSPACEID,WORKSPACENAME
        self.workspacev2 : Signal = Signal(self)


class Instance:
    """Represents an active Hyprland instance.

    The Instance class is a primary interface for interacting with the Hyprland system. It provides methods
    for accessing windows, workspaces, and monitors, as well as emitting signals based on events in the
    Hyprland environment.

    :seealso: :ref:`Components: The Instance <guide-instance>`
    """

    def __init__(self, signature: str = shell.get_env_var_or_fail('HYPRLAND_INSTANCE_SIGNATURE')):
        data = InstanceData(signature=signature)

        #: `Instance signature <https://wiki.hyprland.org/IPC/#hyprland-instance-signature-his>`_ of the Hyprland instance.
        self.signature: str = data.signature

        #: The Hyprland event socket for this instance.
        self.event_socket: EventSocket = EventSocket(signature)
        #: The Hyprland command socket for this instance.
        self.command_socket: CommandSocket = CommandSocket(signature)

        #: .. admonition:: |:no_entry_sign:| **Deprecated since v0.1.7**
        #:
        #:    This signal has been renamed to :attr:`~signal_workspace` and will be removed in future versions.
        #:
        #: Signal emitted when a new workspace gets created.
        #: Sends ``created_workspace_id``, the :attr:`~hyprpy.components.workspaces.Workspace.id` of the created workspace, as signal data.
        self.signal_workspace_created: Signal = DeprecatedSignal(
            self, "The 'signal_workspace_created' Signal is deprecated. You should use 'Instance.signals.workspace' instead."
        )
        #: Signal emitted when an existing workspace gets destroyed.
        #: Sends ``destroyed_workspace_id``, the :attr:`~hyprpy.components.workspaces.Workspace.id` of the destroyed workspace, as signal data
        self.signal_workspace_destroyed: Signal = DeprecatedSignal(self)
        #: Signal emitted when the focus changes to another workspace.
        #: Sends ``active_workspace_id``, the :attr:`~hyprpy.components.workspaces.Workspace.id` of the now active workspace, as signal data.
        self.signal_active_workspace_changed: Signal = DeprecatedSignal(self)
        #: Signal emitted when a new window gets created.
        #: Sends ``created_window_address``, the :attr:`~hyprpy.components.windows.Window.address` of the newly created window, as signal data.
        self.signal_window_created: Signal = DeprecatedSignal(self)
        #: Signal emitted when an existing window gets destroyed.
        #: Sends ``destroyed_window_address``, the :attr:`~hyprpy.components.windows.Window.address` of the destroyed window, as signal data.
        self.signal_window_destroyed: Signal = DeprecatedSignal(self)
        #: Signal emitted when the focus changes to another window.
        #: Sends ``active_window_address``, the :attr:`~hyprpy.components.windows.Window.address` of the now active window, as signal data.
        self.signal_active_window_changed: Signal = DeprecatedSignal(self)


    def __repr__(self):
        return f"<Instance(signature={self.signature!r})>"

    def dispatch(self, arguments: list[str]) -> Union[str, None]:
        """Runs a generic dispatcher command with the given arguments and returns ``None`` on success or a string indicating errors.

        See the `Hyprland Wiki <https://wiki.hyprland.org/Configuring/Dispatchers/>`_ for a list
        of available commands.

        Example:

        .. code-block:: python

            from hyprpy import Hyprland

            instance = Hyprland()
            instance.dispatch(["cyclenext", "prev"])

        :param arguments: A list of strings containing the arguments of the dispatch command.
        :type arguments: list[str]
        :return: `None` if the command succeeded, otherwise a string indicating errors.
        :rtype: str or None
        """

        dispatch_response = self.command_socket.send_command('dispatch', flags=['-j'], args=arguments)
        dispatch_error = dispatch_response if dispatch_response != 'ok' else None
        return dispatch_error


    def get_windows(self) -> List['Window']:
        """Returns all :class:`~hyprpy.components.windows.Window`\\ s currently managed by the instance.

        :return: A list containing :class:`~hyprpy.components.windows.Window` objects.
        """

        windows_data = json.loads(self.command_socket.send_command('clients', flags=['-j']))
        return [Window(window_data, self) for window_data in windows_data]

    def get_window_by_address(self, address: str) -> Union['Window', None]:
        """Retrieves the :class:`~hyprpy.components.windows.Window` with the specified ``address``.

        The ``address`` must be a valid hexadecimal string.

        :return: The :class:`~hyprpy.components.windows.Window` if it exists, or ``None`` otherwise.
        :raises: :class:`TypeError` if ``address`` is not a string.
        :raises: :class:`ValueError` if ``address`` is not a valid hexadecimal string.
        """

        assertions.assert_is_hexadecimal_string(address)
        for window in self.get_windows():
            if window.address_as_int == int(address, 16):
                return window

    def get_active_window(self) -> 'Window':
        """Returns the currently active :class:`~hyprpy.components.windows.Window`.

        :return: The currently active :class:`~hyprpy.components.windows.Window`.
        """

        window_data = json.loads(self.command_socket.send_command('activewindow', flags=['-j']))
        return Window(window_data, self)


    def get_workspaces(self) -> List['Workspace']:
        """Returns all :class:`~hyprpy.components.workspaces.Workspace`\\ s currently managed by the instance.

        :return: A list containing :class:`~hyprpy.components.workspaces.Workspace`\\ s.
        """

        workspaces_data = json.loads(self.command_socket.send_command('workspaces', flags=['-j']))
        return [Workspace(workspace_data, self) for workspace_data in workspaces_data]

    def get_workspace_by_id(self, id: int) -> Union['Workspace', None]:
        """Retrieves the :class:`~hyprpy.components.workspaces.Workspace` with the specified ``id``.

        :return: The :class:`~hyprpy.components.workspaces.Workspace` if it exists, or ``None`` otherwise.
        :raises: :class:`TypeError` if ``id`` is not an integer.
        """

        assertions.assert_is_int(id)
        for workspace in self.get_workspaces():
            if workspace.id == id:
                return workspace

    def get_active_workspace(self) -> 'Workspace':
        """Retrieves the currently active :class:`~hyprpy.components.workspaces.Workspace`.

        :return: The currently active :class:`~hyprpy.components.workspaces.Workspace`.
        """

        workspace_data = json.loads(self.command_socket.send_command('activeworkspace', flags=['-j']))
        return Workspace(workspace_data, self)

    def get_workspace_by_name(self, name: int) -> Union['Workspace', None]:
        """Retrieves the :class:`~hyprpy.components.workspaces.Workspace` with the specified ``name``.

        :return: The :class:`~hyprpy.components.workspaces.Workspace` if it exists, or ``None`` otherwise.
        :raises: :class:`TypeError` if ``name`` is not a string.
        """

        assertions.assert_is_string(name)
        for workspace in self.get_workspaces():
            if workspace.name == name:
                return workspace


    def get_monitors(self) -> List['Monitor']:
        """Returns all :class:`~hyprpy.components.monitors.Monitor`\\ s currently managed by the instance.

        :return: A list containing :class:`~hyprpy.components.monitors.Monitor`\\ s.
        """

        monitors_data = json.loads(self.command_socket.send_command('monitors', flags=['-j']))
        return [Monitor(monitor_data, self) for monitor_data in monitors_data]

    def get_monitor_by_id(self, id: int) -> Union['Monitor', None]:
        """Retrieves the :class:`~hyprpy.components.monitors.Monitor` with the specified ``id``.

        :return: The :class:`~hyprpy.components.monitors.Monitor` if it exists, or ``None`` otherwise.
        :raises: :class:`TypeError` if ``id`` is not an integer.
        """

        assertions.assert_is_int(id)
        for monitor in self.get_monitors():
            if monitor.id == id:
                return monitor

    def get_monitor_by_name(self, name: str) -> Union['Monitor', None]:
        """Retrieves the :class:`~hyprpy.components.monitors.Monitor` with the specified ``name``.

        :return: The :class:`~hyprpy.components.monitors.Monitor` if it exists, or ``None`` otherwise.
        :raises: :class:`TypeError` if ``name`` is not a string.
        :raises: :class:`ValueError` if ``name`` is an empty string.
        """

        assertions.assert_is_nonempty_string(name)
        for monitor in self.get_monitors():
            if monitor.name == name:
                return monitor


    def watch(self) -> None:
        """Continuosly monitors the :class:`~hyprpy.utils.sockets.EventSocket` and emits appropriate :class:`~hyprpy.utils.signals.Signal`\\ s when events are detected.

        This is a blocking method which runs indefinitely.
        Signals are continuosly emitted, as soon as Hyprland events are detected.

        :seealso: :ref:`Components: Reacting to events <guide-events>`
        """

        def _handle_socket_data(data: str):
            signal_for_event = {
                'openwindow': self.signal_window_created,
                'closewindow': self.signal_window_destroyed,
                'activewindowv2': self.signal_active_window_changed,

                'createworkspace': self.signal_workspace_created,
                'destroyworkspace': self.signal_workspace_destroyed,
                'workspace': self.signal_active_workspace_changed,
            }

            lines = list(filter(lambda line: len(line) > 0, data.split('\n')))
            for line in lines:
                event_name, event_data = line.split('>>', maxsplit=1)

                # Pick the signal to emit based on the event's name
                if event_name not in signal_for_event:
                    continue
                signal = signal_for_event[event_name]
                if not signal._observers:
                    # If the signal has no observers, just exit
                    continue

                # We send specific data along with the signal, depending on the event
                if event_name == 'openwindow':
                    signal.emit(created_window_address=event_data.split(',')[0])
                elif event_name == 'closewindow':
                    signal.emit(destroyed_window_address=event_data)
                elif event_name == 'activewindowv2':
                    signal.emit(active_window_address=(None if event_data == ',' else event_data))

                elif event_name == 'createworkspace':
                    signal.emit(created_workspace_id=(int(event_data) if event_data != 'special' else -99))
                elif event_name == 'destroyworkspace':
                    signal.emit(destroyed_workspace_id=(int(event_data) if event_data != 'special' else -99))
                elif event_name == 'workspace':
                    signal.emit(active_workspace_id=(int(event_data) if event_data != 'special' else -99))


        try:
            self.event_socket.connect()

            while True:
                self.event_socket.wait()
                data = self.event_socket.read()
                _handle_socket_data(data)
        finally:
            self.event_socket.close()
