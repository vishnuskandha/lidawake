import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const APP_ID = 'io.github.vishnuskandha.Lidawake';
const APP_PATH = '/io/github/vishnuskandha/Lidawake';
const ON_STYLE = 'color: #ff9a1a;';
const THRESHOLDS = [0, 10, 20, 30];
const SESSIONS = [
    ['Until lid is reopened', -1],
    ['15 minutes', 15],
    ['30 minutes', 30],
    ['1 hour', 60],
    ['2 hours', 120],
    ['Indefinitely', 0],
];

const LidawakeButton = GObject.registerClass(
class LidawakeButton extends PanelMenu.Button {
    _init(ext) {
        super._init(0.5, 'Lidawake');
        const userBin = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'lidawake']);
        this._launchCmd = GLib.file_test(userBin, GLib.FileTest.EXISTS) ? userBin : '/usr/bin/lidawake';
        this._group = Gio.DBusActionGroup.get(Gio.DBus.session, APP_ID, APP_PATH);
        this._running = false;
        this._pendingOn = false;

        this._iconOn = Gio.icon_new_for_string(`${ext.path}/icons/lidawake-symbolic.svg`);
        this._iconOff = Gio.icon_new_for_string(`${ext.path}/icons/lidawake-off-symbolic.svg`);
        this._icon = new St.Icon({
            gicon: this._iconOff,
            style_class: 'system-status-icon',
        });
        this.add_child(this._icon);

        this._switch = new PopupMenu.PopupSwitchMenuItem('Lidawake', false);
        this._switch.connect('toggled', () => this._onToggle());
        this.menu.addMenuItem(this._switch);

        this._status = new PopupMenu.PopupMenuItem('Not running', {reactive: false});
        this.menu.addMenuItem(this._status);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._sessionItems = new Map();
        for (const [label, minutes] of SESSIONS) {
            const item = new PopupMenu.PopupMenuItem(label);
            item.connect('activate', () => this._keepFor(minutes));
            this.menu.addMenuItem(item);
            this._sessionItems.set(minutes, item);
        }

        this._auto = new PopupMenu.PopupSubMenuMenuItem('Auto-off on low battery');
        this._autoItems = new Map();
        for (const v of THRESHOLDS) {
            const item = new PopupMenu.PopupMenuItem(v === 0 ? 'Off' : `At ${v}%`);
            item.connect('activate', () => {
                if (this._ensureRunning(false))
                    this._group.activate_action('auto-off', new GLib.Variant('i', v));
            });
            this._auto.menu.addMenuItem(item);
            this._autoItems.set(v, item);
        }
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this.menu.addMenuItem(this._auto);

        this._signals = [
            this._group.connect('action-state-changed', () => this._sync()),
            this._group.connect('action-added', () => this._sync()),
        ];
        this._watch = Gio.bus_watch_name(Gio.BusType.SESSION, APP_ID, Gio.BusNameWatcherFlags.NONE,
            () => this._onAppeared(), () => this._onVanished());
    }

    _onAppeared() {
        this._running = true;
        this._spawning = false;
        this._group.list_actions();
        this._sync();
        if (this._pendingOn) {
            this._pendingOn = false;
            this._timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 300, () => {
                this._timeoutId = 0;
                if (!this._isActive())
                    this._group.activate_action('active', null);
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    _onVanished() {
        this._running = false;
        this._setUi(false, 'Not running');
        for (const item of this._sessionItems.values())
            item.setOrnament(PopupMenu.Ornament.NONE);
    }

    _isActive() {
        const v = this._group.get_action_state('active');
        return v ? v.get_boolean() : false;
    }

    _setUi(active, text) {
        this._switch.setToggleState(active);
        this._status.label.text = text;
        this._icon.gicon = active ? this._iconOn : this._iconOff;
        this._icon.set_style(active ? ON_STYLE : null);
    }

    _sync() {
        if (!this._running)
            return;
        const s = this._group.get_action_state('status');
        this._setUi(this._isActive(), s ? s.get_string()[0] : '');
        const m = this._group.get_action_state('mode');
        const mode = m ? m.get_string()[0] : 'off';
        for (const [minutes, item] of this._sessionItems) {
            const current = minutes === -1 ? mode === 'lid'
                : minutes === 0 ? mode === 'indefinite'
                : mode === `timer:${minutes}`;
            item.setOrnament(current ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
        }
        const t = this._group.get_action_state('auto-off');
        const cur = t ? t.get_int32() : 0;
        for (const [v, item] of this._autoItems)
            item.setOrnament(v === cur ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
        this._auto.label.text = cur > 0 ? `Auto-off on low battery (${cur}%)` : 'Auto-off on low battery';
    }

    _ensureRunning(thenOn) {
        if (this._running)
            return true;
        this._pendingOn = this._pendingOn || thenOn;
        if (this._spawning)
            return false;
        this._spawning = true;
        GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 10, () => {
            this._spawning = false;
            return GLib.SOURCE_REMOVE;
        });
        try {
            GLib.spawn_command_line_async(this._launchCmd);
        } catch (e) {
            Main.notify('Lidawake', `Could not start Lidawake: ${e.message}`);
            this._pendingOn = false;
            this._spawning = false;
        }
        return false;
    }

    _onToggle() {
        if (!this._ensureRunning(true))
            return;
        // The switch flips itself; only act if it disagrees with the app.
        if (this._switch.state !== this._isActive())
            this._group.activate_action('active', null);
    }

    _keepFor(minutes) {
        if (!this._ensureRunning(false))
            return;
        this._group.activate_action('keep-for', new GLib.Variant('i', minutes));
    }

    destroy() {
        if (this._timeoutId)
            GLib.source_remove(this._timeoutId);
        if (this._watch)
            Gio.bus_unwatch_name(this._watch);
        for (const id of this._signals ?? [])
            this._group.disconnect(id);
        super.destroy();
    }
});

export default class LidawakeExtension extends Extension {
    enable() {
        this._button = new LidawakeButton(this);
        // Sit immediately left of the Quick Settings (control centre) pill.
        const box = Main.panel._rightBox;
        const qs = Main.panel.statusArea.quickSettings?.container;
        const idx = qs ? box.get_children().indexOf(qs) : -1;
        Main.panel.addToStatusArea(this.uuid, this._button, idx >= 0 ? idx : 0, 'right');
    }

    disable() {
        this._button?.destroy();
        this._button = null;
    }
}
